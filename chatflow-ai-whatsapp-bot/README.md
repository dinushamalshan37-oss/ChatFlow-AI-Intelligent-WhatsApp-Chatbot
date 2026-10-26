# ChatFlow AI — WhatsApp Business Customer-Support Bot 🤖

A complete, editable **Python + FastAPI + Meta WhatsApp Cloud API + OpenAI Responses API** starter project for WhatsApp **business customer support**. Supports Sinhala / English / Singlish replies through the AI model, plus a zero-AI-cost echo mode for initial testing.

> ⚠️ **Important:** This does **not** connect directly to a normal personal WhatsApp account. Use Meta's official **WhatsApp Business Platform test number**, then a registered business number for production. You can use your existing personal WhatsApp as a **test recipient**, without moving/deleting your personal account. The API account is separate.
>
> This bot is scoped to a business's customer support, **not** a standalone general-purpose AI assistant on WhatsApp. Check current Meta policies before deployment. Never use unofficial WhatsApp Web automation for a production business account.

## Features

- ✅ Official WhatsApp Cloud API webhook **verification** (GET) and **signature validation** (POST)
- ✅ Handles incoming **text messages**, ignores other event types and delivery statuses
- ✅ Responds using `gpt-6-luna` on OpenAI Responses API via HTTPS (`BOT_MODE=ai`)
- ✅ Free-for-AI-testing `BOT_MODE=echo` (Meta API fees/conditions may still apply)
- ✅ Business info via `business_info.txt`
- ✅ Chat context (last 10 stored messages) and incoming-message duplicate detection via SQLite
- ✅ Durable SQLite job queue, retries on transient errors, sequential processing for MVP
- ✅ `STOP` opt-out, `START` / `BOT` to resume, `HUMAN` for **contact details** and pause
- ✅ 24-hour service-window check; no unsolicited marketing or messaging outside the window
- ✅ Basic health endpoint, tests, Dockerfile

**Limits:** No media/voice messages, no live human inbox transfer, no booking/order tool, no admin dashboard. `HUMAN` shares contact details — **it does not automatically transfer to a live agent**. For production scale, use a dedicated job queue, monitoring, secure admin tools and managed persistent storage.

## Project structure

```text
chatflow-ai-whatsapp-bot/
├── app/
│   ├── __init__.py
│   ├── config.py          # Reads .env settings
│   ├── main.py            # FastAPI + signed webhook + worker
│   ├── bot.py             # AI/echo customer support logic
│   ├── whatsapp.py        # Sends replies via Meta Graph API
│   └── storage.py         # SQLite chat history & message queue
├── tests/
│   ├── test_webhook.py
│   └── test_bot.py
├── scripts/
│   └── send_test_webhook.py
├── START_HERE_SINHALA.md  # Quick-start guide in Singlish
├── business_info.txt      # Replace with actual business details
├── .env.example           # Safe placeholder configuration
├── .gitignore
├── Dockerfile
├── .dockerignore
├── requirements.txt
├── requirements-dev.txt
└── README.md
```

## Requirements

- Python 3.11+ and VS Code / terminal
- Meta Developer account: https://developers.facebook.com/
- Meta WhatsApp Business Platform app with test number / registered business number
- For AI replies: OpenAI API key from https://platform.openai.com/api-keys (API billing is separate from ChatGPT plans)
- Public HTTPS webhook URL, e.g. ngrok: https://ngrok.com/

## Step 1 — Install Python packages

Open the folder in VS Code, then in the integrated terminal:

### Windows PowerShell

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use `.venv\Scripts\python.exe -m pip install -r requirements.txt` and `.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000` instead, or use Command Prompt's `.venv\Scripts\activate.bat`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Step 2 — Get Meta WhatsApp API test credentials

1. Sign in at **https://developers.facebook.com/**.
2. Create a Meta app and add the **WhatsApp** use case / product (the interface names may vary).
3. Open **WhatsApp → API Setup**.
4. Record the **temporary access token** and **Phone Number ID** of the **test sender**.
5. Add your **normal personal WhatsApp number** under **test recipient numbers**, then complete Meta's verification. This does not convert your personal account into a bot.
6. Get your **App Secret** from the app's **Settings → Basic** area.
7. Choose your own strong, random webhook **Verify Token** (e.g. a randomly generated 32+ character string).

**Keep Meta tokens, App Secret and OpenAI API keys private.** Temporary test tokens expire. For production, follow Meta instructions for a valid long-lived token, permissions, business verification where applicable and a business phone number. API terms and availability may change.

## Step 3 — Create `.env`

Copy `.env.example` to `.env`.

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Edit `.env` (sample; **do not copy example credentials literally**):

```dotenv
VERIFY_TOKEN=your_own_very_long_random_verify_token
META_APP_SECRET=your_actual_meta_app_secret
WHATSAPP_ACCESS_TOKEN=your_actual_access_token
WHATSAPP_PHONE_NUMBER_ID=your_actual_phone_number_id
GRAPH_API_VERSION=v26.0
BOT_MODE=echo
OPENAI_API_KEY=
OPENAI_MODEL=gpt-6-luna
HUMAN_SUPPORT_CONTACT=your_public_support_phone_or_email
DATABASE_PATH=data/chatflow.db
RETENTION_DAYS=30
WORKER_ENABLED=true
```

`BOT_MODE=echo` sends a simple auto-response and requires **no OpenAI key**. To turn on AI, set `BOT_MODE=ai`, fill `OPENAI_API_KEY`, and edit `business_info.txt` with accurate business details. Restart the server after changing the file.

**Security:** `.env` is Git-ignored. Never commit it or paste tokens into GitHub issues, screenshots or chat conversations.

## Step 4 — Start the Python bot

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In browser open: **http://127.0.0.1:8000/health**

Expected example:

```json
{"status":"ok","mode":"echo","worker_enabled":true,"meta_configured":true}
```

This confirms the local server is running; **it does not mean Meta or OpenAI credentials work**.

## Step 5 — Expose a public HTTPS webhook using ngrok

In a **second terminal**:

```bash
ngrok http 8000
```

Copy the public HTTPS forwarding address, for example:

```text
https://YOUR-URL.ngrok-free.app
```

The actual webhook **Callback URL** is:

```text
https://YOUR-URL.ngrok-free.app/webhook
```

In the Meta Developer App, go to the **WhatsApp webhook configuration**, paste that callback URL and the **exact same Verify Token** from `.env`. Press Verify/Save. Then subscribe to the **messages** webhook field. You might need to use the app's webhook management page, depending on Meta's UI.

> If verification fails: use `https://.../webhook` (not `/health`); make sure the FastAPI server is running; compare Verify Token values; check ngrok HTTPS requests. If signature check fails on actual POSTs, verify `META_APP_SECRET` is the exact secret of the correct Meta app.

## Step 6 — Test with your personal WhatsApp

1. Verify **your personal WhatsApp** as an allowed test recipient (from Step 2).
2. Send `Hi` **from your personal WhatsApp to the Meta test sender number** in the developer console.
3. Check the VS Code terminal for messages being processed.
4. In `echo` mode you should receive an acknowledgement through the test sender number.
5. To test AI replies, set `BOT_MODE=ai` and a valid `OPENAI_API_KEY`, restart, then ask a **business-related question**.

Try these commands:

- `HUMAN` — get configured human contact info, pause automated replies (manual contact required)
- `BOT` or `START` — resume automated replies
- `STOP` — opt out of automated replies

The bot **does not send WhatsApp messages from your personal account**. It sends them from the Meta test/business sender, and your personal phone **receives** those messages as a test recipient.

## How the code works

```text
Personal WhatsApp (test recipient)
        |
        | customer sends a message to the API test/business number
        v
Meta WhatsApp Cloud API
        |
        | signed webhook (POST /webhook)
        v
FastAPI > verify signature > SQLite queue > sequential background worker
        |
        v
Echo reply OR OpenAI Responses API using business_info.txt + recent history
        |
        v
Meta Cloud API POST /{phone_number_id}/messages
        |
        v
WhatsApp receives the business support reply
```

## Automated tests (safe: no real Meta/OpenAI calls)

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

Tests verify Meta webhook signatures and verification token, duplicate protection, queue behavior, command replies, and response behavior using mocks / echo mode.

For test-only local simulated webhooks, set `WORKER_ENABLED=false` first and restart, then run:

```bash
python scripts/send_test_webhook.py
```

This queues a simulated signed message without letting the worker send a real WhatsApp message. **Do not send simulated data while `WORKER_ENABLED=true`**, because a configured bot may attempt to send a response to the test number in the script.

## Docker (optional)

```bash
docker build -t chatflow-ai .
docker run --env-file .env -v "$(pwd)/data:/app/data" -p 8000:8000 chatflow-ai
```

On Windows PowerShell, use `${PWD}/data:/app/data` instead of `$(pwd)/data:/app/data` if necessary. Mount `data/` to preserve SQLite queue/history across container restarts. Only **one server worker** is supported with this SQLite queue design.

## Troubleshooting

| Issue | What to check |
|---|---|
| `403` on GET `/webhook` | Wrong Verify Token or hub.mode |
| `403` on POST `/webhook` | Wrong `META_APP_SECRET` or invalid signature |
| No message queued | Meta webhook subscription `messages`; correct API number; only text messages handled |
| No WhatsApp reply | Test recipient allowlist, token expiry, phone number ID, API permissions |
| AI fails | `BOT_MODE=ai`, correct OpenAI API key, API credit, supported model |
| Replies disappear after `HUMAN` | Bot paused intentionally; send `BOT` to resume |
| `STOP` | Opted out; send `START` to resume |
| Local works, deployed fails | Configure actual public HTTPS webhook, persistent disk, environment variables, logs |

SQLite `inbox` stores statuses like `pending`, `retry`, `done`, `failed`; inspect with a SQLite viewer if debugging. The app intentionally doesn't expose customer logs or histories over a public HTTP endpoint.

## Before real production use

- Comply with the [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/). Automation may reply **within 24 hours** of an inbound customer message; after that you may only send approved templates. **This code intentionally has no unsolicited outbound/template feature.**
- WhatsApp Business Platform API messages can incur charges (and OpenAI is separately billed). See current Meta and OpenAI pricing.
- Provide a **clear real human escalation path** (inbox, phone, etc.). This project only provides contact details.
- Obtain appropriate consent and disclose chatbot use and data handling.
- Use production-safe secret management, monitoring and rate limits. Restrict log access.
- SQLite queue is appropriate for demo / small single-worker prototype, **not high-scale production**. A crash between API send and marking a job done may send a duplicate on retry (at-least-once behavior). Use a properly coordinated persistent queue and operational procedures for high scale.
- Configure retention and review data protection obligations before collecting real customer data.
- Voice messages, media, templates, live agent handoff, and order-management integrations need additional work.

## Official documentation

- Meta Cloud API: https://developers.facebook.com/docs/whatsapp/cloud-api/
- Meta developer platform: https://developers.facebook.com/
- Meta policy: https://whatsappbusiness.com/policy/
- OpenAI Responses API: https://developers.openai.com/api/reference/resources/responses/methods/create
- GPT-6 Luna model: https://developers.openai.com/api/docs/models/gpt-6-luna

---

**Made for a business support chatbot portfolio project.** Modify the business name, knowledge, support contact and README before publishing a client-specific deployment.
