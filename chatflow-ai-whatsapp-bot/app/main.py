"""FastAPI app with official signed Meta webhook and durable SQLite queue."""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import hmac
import json
import logging
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
import httpx

from .bot import generate_reply
from .config import Settings
from .storage import Storage
from .whatsapp import send_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('chatflow')


def process_job(job: dict, settings: Settings, store: Storage):
    """Executed serially by the worker, so customer chat context remains ordered."""
    try:
        # Free-form replies are allowed only inside Meta's 24-hour customer service window.
        # Leave a buffer for clock skew and networking delays.
        if time.time() - int(job['received_ts']) > 23 * 3600 + 55 * 60:
            logger.warning('Message %s expired; no free-form reply sent', job['id'])
            store.finish(job['id'], 'skipped')
            return
        reply = generate_reply(job['sender'], job['body'], settings, store)
        if reply is None:
            store.finish(job['id'], 'skipped')
            return
        send_text(job['sender'], reply, settings)
        store.append_exchange(job['sender'], job['body'], reply)
        store.finish(job['id'])
        logger.info('Message processed: %s', job['id'])
    except Exception as exc:
        # Never log tokens or full customer messages.
        status_code = getattr(getattr(exc, 'response', None), 'status_code', None)
        permanent = isinstance(exc, (ValueError, RuntimeError)) or (
            isinstance(exc, httpx.HTTPStatusError) and status_code is not None
            and 400 <= status_code < 500 and status_code != 429
        )
        logger.error('Processing error for message %s (%s)', job['id'], type(exc).__name__)
        store.fail(job['id'], job['attempts'], type(exc).__name__, permanent=permanent)


async def queue_worker(settings: Settings, store: Storage):
    last_prune = 0.0
    while True:
        try:
            if time.time() - last_prune > 86400:
                await asyncio.to_thread(store.prune, settings.retention_days)
                last_prune = time.time()
            job = await asyncio.to_thread(store.claim_next)
            if job:
                await asyncio.to_thread(process_job, job, settings, store)
            else:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Worker loop issue')
            await asyncio.sleep(2)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    store = Storage(settings.db_path)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store.initialize()
        task = asyncio.create_task(queue_worker(settings, store)) if settings.worker_enabled else None
        try:
            yield
        finally:
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    api = FastAPI(title='ChatFlow AI WhatsApp Business Bot', version='1.0.0', lifespan=lifespan)
    api.state.store = store
    api.state.settings = settings

    @api.get('/health')
    def health():
        return {'status': 'ok', 'mode': settings.bot_mode, 'worker_enabled': settings.worker_enabled,
                'meta_configured': bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id)}

    @api.get('/webhook', response_class=PlainTextResponse)
    def verify_webhook(request: Request):
        params = request.query_params
        if not settings.verify_token:
            raise HTTPException(status_code=503, detail='Verify token not configured')
        verified = (params.get('hub.mode') == 'subscribe' and
                    hmac.compare_digest(params.get('hub.verify_token', ''), settings.verify_token))
        if not verified:
            raise HTTPException(status_code=403, detail='Webhook verification failed')
        return params.get('hub.challenge', '')

    @api.post('/webhook')
    async def webhook(request: Request):
        if not settings.meta_app_secret:
            raise HTTPException(status_code=503, detail='Meta app secret not configured')
        raw = await request.body()
        if len(raw) > 1_000_000:
            raise HTTPException(status_code=413, detail='Payload too large')
        expected = 'sha256=' + hmac.new(
            settings.meta_app_secret.encode(), raw, hashlib.sha256
        ).hexdigest()
        signature = request.headers.get('x-hub-signature-256', '')
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=403, detail='Invalid Meta signature')
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, ValueError):
            raise HTTPException(status_code=400, detail='Invalid JSON')
        if not isinstance(payload, dict) or payload.get('object') != 'whatsapp_business_account':
            return {'status': 'ignored', 'queued': 0}

        queued = 0
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                if change.get('field') != 'messages':
                    continue
                value = change.get('value') or {}
                metadata = value.get('metadata') or {}
                if (settings.whatsapp_phone_number_id and metadata.get('phone_number_id')
                        and str(metadata['phone_number_id']) != settings.whatsapp_phone_number_id):
                    continue
                for message in value.get('messages', []):
                    if message.get('type') != 'text':
                        continue  # Media and status updates are not handled in this version.
                    message_id = message.get('id', '')
                    sender = message.get('from', '')
                    body = ((message.get('text') or {}).get('body') or '').strip()
                    try:
                        timestamp = int(message['timestamp'])
                    except (KeyError, ValueError, TypeError):
                        continue
                    if not (message_id and sender.isdigit() and body):
                        continue
                    if store.enqueue(message_id, sender, body[:2000], timestamp):
                        queued += 1
        return {'status': 'accepted', 'queued': queued}

    return api


app = create_app()
