import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


def _split_csv(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    api_id: int = int(os.environ.get("API_ID", "0") or "0")
    api_hash: str = os.environ.get("API_HASH", "")
    session_string: str = os.environ.get("SESSION_STRING", "")
    meili_url: str = os.environ.get("MEILI_URL", "http://localhost:7700")
    meili_key: str = os.environ.get("MEILI_KEY", "masterKey")
    seed_channels: list[str] = field(
        default_factory=lambda: _split_csv(os.environ.get("SEED_CHANNELS", ""))
    )
    exclude_chat_ids: set[int] = field(
        default_factory=lambda: {
            int(v) for v in _split_csv(os.environ.get("EXCLUDE_CHAT_IDS", ""))
        }
    )
    state_db_path: str = os.environ.get("STATE_DB_PATH", "state.db")
    ai_base_url: str = os.environ.get("AI_BASE_URL", "https://api.openai.com/v1")
    ai_api_key: str = os.environ.get("AI_API_KEY", "")
    ai_model: str = os.environ.get("AI_MODEL", "gpt-4o-mini")
    ai_max_rounds: int = int(os.environ.get("AI_MAX_ROUNDS", "5") or "5")


settings = Settings()
