"""Meta WhatsApp Cloud API send message helper."""
import httpx
from .config import Settings


def send_text(recipient: str, message: str, settings: Settings):
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        raise RuntimeError('Missing WhatsApp API token or phone number ID')
    if not recipient.isdigit():
        raise ValueError('Recipient WhatsApp ID must contain digits only')
    url = (f'https://graph.facebook.com/{settings.graph_api_version}/'
           f'{settings.whatsapp_phone_number_id}/messages')
    payload = {
        'messaging_product': 'whatsapp',
        'recipient_type': 'individual',
        'to': recipient,
        'type': 'text',
        'text': {'preview_url': False, 'body': message[:4096]},
    }
    with httpx.Client(timeout=25.0) as client:
        response = client.post(url, json=payload, headers={
            'Authorization': f'Bearer {settings.whatsapp_access_token}',
            'Content-Type': 'application/json',
        })
        response.raise_for_status()
        return response.json()
