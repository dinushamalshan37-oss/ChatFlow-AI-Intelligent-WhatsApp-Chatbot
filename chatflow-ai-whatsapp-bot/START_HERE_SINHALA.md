# ChatFlow AI — Quick Start (Singlish)

Me project eka **WhatsApp Business Cloud API test number / business number** ekakata reply dena **business customer-support AI bot** ekak. **Personal WhatsApp account eken messages auto-send karanne nehe.** Oyage normal WhatsApp eka test recipient widihata use karanna puluwan.

## VS Code terminal eke

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

1. `https://developers.facebook.com/` -> Meta App -> WhatsApp API Setup.
2. Test Phone Number ID, test Access Token saha App Secret copy karanna.
3. Oyage normal WhatsApp number eka Meta test recipient widihata add karala verify karanna.
4. `.env` file eka edit karanna:
   - `WHATSAPP_ACCESS_TOKEN` = Meta token
   - `WHATSAPP_PHONE_NUMBER_ID` = Meta test phone number ID
   - `META_APP_SECRET` = Meta app secret
   - `VERIFY_TOKEN` = oyama hadana secret string ekak
   - mulin `BOT_MODE=echo` thiyanna
5. `business_info.txt` eke oyage business details type karanna.
6. Server start: `uvicorn app.main:app --port 8000`
7. Thawa terminal ekak: `ngrok http 8000`
8. Ngrok public URL + `/webhook` Meta webhook **Callback URL** ekata add karanna.
9. Meta verify token ekath `.env` eke verify token ekath same wenna ona.
10. Meta `messages` webhook subscribe karanna.
11. Personal WhatsApp eken **Meta test number ekata** `Hi` yawala reply eka balanna.
12. AI replies ganna one nam `OPENAI_API_KEY=...` set karala `BOT_MODE=ai` kiyala wenas karala server restart karanna.

## Important

- Secret keys GitHub ekata upload karanna epa. `.env` Git-ignored.
- `BOT_MODE=echo` OpenAI credits consume karanne nehe. Meta charges / messaging rules venama adala wenna puluwan.
- `HUMAN` kiyala ewwama support contact denawa, bot pause wenawa; **human agent kenek automatically connect wenne nehe**.
- `BOT` reply kalama bot active. `STOP` opt out. `START` opt in.
- Live customer service ekakata deploy karanna kalin full `README.md` kiyawanna.

Meta: https://developers.facebook.com/
OpenAI API key: https://platform.openai.com/api-keys
