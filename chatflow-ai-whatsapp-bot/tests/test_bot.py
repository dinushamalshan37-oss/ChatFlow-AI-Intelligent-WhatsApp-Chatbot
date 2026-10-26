import time
from app.config import Settings
from app.storage import Storage
from app.bot import generate_reply
from app.main import process_job


def make_store(tmp_path):
    store = Storage(str(tmp_path / 'test.db'))
    store.initialize()
    return store


def test_echo_human_stop_resume(tmp_path):
    store = make_store(tmp_path)
    settings = Settings(bot_mode='echo', human_support_contact='+94 77 123 4567')
    sender = '94770001122'
    assert 'received your message' in generate_reply(sender, 'Hi', settings, store)
    assert '+94 77 123 4567' in generate_reply(sender, 'HUMAN', settings, store)
    assert generate_reply(sender, 'still there?', settings, store) is None
    assert 'active again' in generate_reply(sender, 'BOT', settings, store)
    assert 'stopped' in generate_reply(sender, 'STOP', settings, store)
    assert generate_reply(sender, 'Please reply', settings, store) is None
    assert 'active again' in generate_reply(sender, 'START', settings, store)


def test_history_stored(tmp_path):
    store = make_store(tmp_path)
    store.append_exchange('1', 'hello', 'Hi there')
    assert store.history('1') == [{'role':'user','content':'hello'}, {'role':'assistant','content':'Hi there'}]
    assert store.history('2') == []


def test_expired_message_not_sent(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    store.enqueue('expired', '94770001122', 'hi', int(time.time()) - 86400)
    job = store.claim_next()
    def must_not_send(*args, **kwargs):
        raise AssertionError('Should never send outside service window')
    monkeypatch.setattr('app.main.send_text', must_not_send)
    process_job(job, Settings(bot_mode='echo'), store)
    assert store.claim_next() is None
    with store.connect() as db:
        assert db.execute('SELECT status FROM inbox WHERE id=?', ('expired',)).fetchone()['status'] == 'skipped'


def test_echo_worker_with_mock_send(tmp_path, monkeypatch):
    store = make_store(tmp_path)
    store.enqueue('fresh', '94770001122', 'Hi!', int(time.time()))
    calls = []
    monkeypatch.setattr('app.main.send_text', lambda recipient, reply, settings: calls.append((recipient, reply)))
    process_job(store.claim_next(), Settings(bot_mode='echo'), store)
    assert len(calls) == 1
    assert calls[0][0] == '94770001122'
    assert len(store.history('94770001122')) == 2
    with store.connect() as db:
        assert db.execute('SELECT status FROM inbox WHERE id=?', ('fresh',)).fetchone()['status'] == 'done'


def test_ai_mode_responses_api_with_mock(tmp_path, monkeypatch):
    """Exercises OpenAI request/response parsing without making external HTTP calls."""
    store = make_store(tmp_path)
    info = tmp_path / 'business_info.txt'
    info.write_text('Business name: Test Shop. Services: Phone repairs.', encoding='utf-8')
    settings = Settings(
        bot_mode='ai', openai_api_key='dummy-key-do-not-use',
        business_info_file=str(info), human_support_contact='support@example.com'
    )
    requests = []

    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {'output': [{'type': 'message', 'content': [
                {'type': 'output_text', 'text': 'We repair phones.'}
            ]}]}

    class FakeClient:
        def __init__(self, timeout):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def post(self, url, headers, json):
            requests.append({'url': url, 'headers': headers, 'body': json})
            return FakeResponse()

    monkeypatch.setattr('app.bot.httpx.Client', FakeClient)
    reply = generate_reply('94770001122', 'What services?', settings, store)
    assert reply == 'We repair phones.'
    assert requests[0]['url'] == 'https://api.openai.com/v1/responses'
    assert requests[0]['body']['model'] == 'gpt-6-luna'
    assert requests[0]['body']['store'] is False
    assert requests[0]['body']['input'][-1]['content'] == 'What services?'
