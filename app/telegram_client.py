from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import Settings


def build_client(settings: Settings) -> TelegramClient:
    if not settings.session_string:
        raise RuntimeError(
            "SESSION_STRING not set. Run `python -m app.cli login` once to generate one."
        )
    return TelegramClient(
        StringSession(settings.session_string), settings.api_id, settings.api_hash
    )
