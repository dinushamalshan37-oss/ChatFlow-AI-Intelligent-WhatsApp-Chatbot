import hashlib
import hmac
import json
import time
from fastapi.testclient import TestClient
from app.config import Settings
from app.main import create_app


def app_client(tmp_path):
    settings = Settings(
        verify_token='secret_verify_test',
        meta_app_secret='meta_secret_test',
        whatsapp_phone_number_id='123456',
        db_path=str(tmp_path / 'db.sqlite'),
        worker_enabled=False,
    )
    return TestClient(create_app(settings))


def signed_payload(payload: dict):
    raw = json.dumps(payload).encode()
    return raw, {'X-Hub-Signature-256': 'sha256=' + hmac.new(
        b'meta_secret_test', raw, hashlib.sha256).hexdigest(),
        'Content-Type': 'application/json'}


def sample_payload():
    return {'object': 'whatsapp_business_account', 'entry': [{'changes': [{
        'field': 'messages',
        'value': {'metadata': {'phone_number_id': '123456'}, 'messages': [
            {'id': 'wamid.test1', 'from': '94770001122', 'timestamp': str(int(time.time())),
             'type': 'text', 'text': {'body': 'Hello!'}}
        ]}
    }]}]}


def test_webhook_verification(tmp_path):
    with app_client(tmp_path) as client:
        params = {'hub.mode': 'subscribe', 'hub.verify_token': 'secret_verify_test', 'hub.challenge': '9988'}
        response = client.get('/webhook', params=params)
        assert response.status_code == 200
        assert response.text == '9988'
        params['hub.verify_token'] = 'wrong'
        assert client.get('/webhook', params=params).status_code == 403


def test_signed_message_queued_once(tmp_path):
    with app_client(tmp_path) as client:
        raw, headers = signed_payload(sample_payload())
        response = client.post('/webhook', content=raw, headers=headers)
        assert response.status_code == 200
        assert response.json() == {'status': 'accepted', 'queued': 1}
        response2 = client.post('/webhook', content=raw, headers=headers)
        assert response2.json()['queued'] == 0
        job = client.app.state.store.claim_next()
        assert job['id'] == 'wamid.test1'
        assert job['sender'] == '94770001122'


def test_unsigned_invalid_rejected(tmp_path):
    with app_client(tmp_path) as client:
        bad = client.post('/webhook', json=sample_payload())
        assert bad.status_code == 403
        wrong = client.post('/webhook', content=b'{}', headers={'x-hub-signature-256': 'sha256=no'})
        assert wrong.status_code == 403


def test_wrong_phone_ignored(tmp_path):
    with app_client(tmp_path) as client:
        payload = sample_payload()
        payload['entry'][0]['changes'][0]['value']['metadata']['phone_number_id'] = 'other'
        raw, headers = signed_payload(payload)
        response = client.post('/webhook', content=raw, headers=headers)
        assert response.status_code == 200
        assert response.json()['queued'] == 0


def test_delivery_receipt_doesnt_queue(tmp_path):
    with app_client(tmp_path) as client:
        payload = {'object': 'whatsapp_business_account', 'entry': [{'changes': [{
            'field': 'messages', 'value': {'statuses': [{'id': 'outgoing'}]}
        }]}]}
        raw, headers = signed_payload(payload)
        assert client.post('/webhook', content=raw, headers=headers).json()['queued'] == 0
