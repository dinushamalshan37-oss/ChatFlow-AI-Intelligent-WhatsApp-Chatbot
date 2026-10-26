"""Dev-only simulated inbound webhook. NEVER use to fake real customer traffic."""
import hashlib
import hmac
import json
import os
import time
from pathlib import Path
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / '.env')
secret = os.getenv('META_APP_SECRET', '')
if not secret:
    raise SystemExit('Set META_APP_SECRET in .env first')
if os.getenv('WORKER_ENABLED', 'true').strip().lower() not in {'false', '0', 'no'}:
    raise SystemExit('For safety, set WORKER_ENABLED=false and restart server before simulating inbound traffic.')
payload = {
    'object': 'whatsapp_business_account',
    'entry': [{'changes': [{'field': 'messages', 'value': {
        'metadata': {'phone_number_id': os.getenv('WHATSAPP_PHONE_NUMBER_ID', '')},
        'messages': [{'id': f'test.{time.time_ns()}',
                      'from': '94770000000',
                      'timestamp': str(int(time.time())),
                      'type': 'text', 'text': {'body': 'Hi, what services do you offer?'}}]
    }}]}]
}
raw = json.dumps(payload).encode('utf-8')
signature = 'sha256=' + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
response = httpx.post('http://127.0.0.1:8000/webhook', content=raw,
                      headers={'X-Hub-Signature-256': signature,
                               'Content-Type': 'application/json'}, timeout=10)
print(response.status_code, response.text)
print('Safe simulation queued, assuming the server is also running WORKER_ENABLED=false.')
