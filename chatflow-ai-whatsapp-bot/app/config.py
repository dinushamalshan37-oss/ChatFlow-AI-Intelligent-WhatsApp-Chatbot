"""Read bot configuration from .env / environment variables."""
from dataclasses import dataclass
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


@dataclass(frozen=True)
class Settings:
    verify_token: str = ''
    meta_app_secret: str = ''
    whatsapp_access_token: str = ''
    whatsapp_phone_number_id: str = ''
    graph_api_version: str = 'v26.0'
    bot_mode: str = 'echo'
    openai_api_key: str = ''
    openai_model: str = 'gpt-6-luna'
    db_path: str = str(ROOT / 'data' / 'chatflow.db')
    business_info_file: str = str(ROOT / 'business_info.txt')
    human_support_contact: str = ''
    worker_enabled: bool = True
    retention_days: int = 30

    @classmethod
    def from_env(cls):
        return cls(
            verify_token=os.getenv('VERIFY_TOKEN', '').strip(),
            meta_app_secret=os.getenv('META_APP_SECRET', '').strip(),
            whatsapp_access_token=os.getenv('WHATSAPP_ACCESS_TOKEN', '').strip(),
            whatsapp_phone_number_id=os.getenv('WHATSAPP_PHONE_NUMBER_ID', '').strip(),
            graph_api_version=os.getenv('GRAPH_API_VERSION', 'v26.0').strip(),
            bot_mode=os.getenv('BOT_MODE', 'echo').strip().lower(),
            openai_api_key=os.getenv('OPENAI_API_KEY', '').strip(),
            openai_model=os.getenv('OPENAI_MODEL', 'gpt-6-luna').strip(),
            db_path=os.getenv('DATABASE_PATH', str(ROOT / 'data' / 'chatflow.db')).strip(),
            business_info_file=os.getenv('BUSINESS_INFO_FILE', str(ROOT / 'business_info.txt')).strip(),
            human_support_contact=os.getenv('HUMAN_SUPPORT_CONTACT', '').strip(),
            worker_enabled=os.getenv('WORKER_ENABLED', 'true').strip().lower() in {'true', '1', 'yes'},
            retention_days=int(os.getenv('RETENTION_DAYS', '30')),
        )
