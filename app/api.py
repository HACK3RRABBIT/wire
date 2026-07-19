from pydantic import BaseModel

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app.ai_client import agentic_search, summarize_hits, test_connection
from app.config import settings
from app.search_index import get_index, search as run_search
from app.state_db import get_settings as get_ai_settings, list_channels, set_settings as set_ai_settings

app = FastAPI(title="Telegram Search Engine")
_index = None

_AI_KEYS = ["ai_base_url", "ai_api_key", "ai_model", "ai_max_rounds"]


def _load_ai_settings() -> None:
    """Apply any AI config saved via the web UI over the .env defaults, on startup."""
    stored = get_ai_settings(settings.state_db_path, _AI_KEYS)
    for key, value in stored.items():
        if key == "ai_max_rounds":
            value = int(value)
        object.__setattr__(settings, key, value)


_load_ai_settings()


def get_search_index():
    global _index
    if _index is None:
        _index = get_index(settings)
    return _index


class AIConfig(BaseModel):
    ai_base_url: str
    ai_api_key: str
    ai_model: str
    ai_max_rounds: int = 5


@app.get("/search")
def search(q: str = "", hashtag: str | None = None, limit: int = 20):
    result = run_search(
        get_search_index(),
        q,
        hashtag=hashtag,
        facets=["channel_username"],
        limit=limit,
    )
    return {
        "hits": result["hits"],
        "channels": result.get("facetDistribution", {}).get("channel_username", {}),
    }


@app.get("/analyze")
def analyze(q: str = "", hashtag: str | None = None, limit: int = 20):
    if not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI_API_KEY not configured")
    result = run_search(get_search_index(), q, hashtag=hashtag, limit=limit)
    hits = result["hits"]
    if not hits:
        return {"summary": "No results to analyze.", "hit_count": 0}
    try:
        summary = summarize_hits(settings, hashtag and f"#{hashtag}" or q, hits)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI request failed: {e}")
    return {"summary": summary, "hit_count": len(hits)}


@app.get("/ask")
def ask(q: str):
    if not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI_API_KEY not configured")

    def search_fn(query, hashtag):
        result = run_search(get_search_index(), query or "", hashtag=hashtag, limit=15)
        return result["hits"]

    try:
        return agentic_search(settings, q, search_fn)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI request failed: {e}")


@app.get("/channels")
def channels():
    rows = list_channels(settings.state_db_path)
    return [dict(row) for row in rows]


@app.get("/users/{sender_id}/channels")
def user_channels(sender_id: int, limit: int = 50):
    result = run_search(
        get_search_index(),
        "",
        sender_id=sender_id,
        facets=["channel_username"],
        limit=limit,
    )
    return {"channels": result.get("facetDistribution", {}).get("channel_username", {})}


@app.get("/settings")
def get_settings_route():
    return {
        "ai_base_url": settings.ai_base_url,
        "ai_model": settings.ai_model,
        "ai_max_rounds": settings.ai_max_rounds,
        "ai_api_key_set": bool(settings.ai_api_key),
    }


@app.post("/settings")
def post_settings_route(config: AIConfig):
    values = config.model_dump()
    if not values["ai_api_key"]:
        values["ai_api_key"] = settings.ai_api_key
    for key, value in values.items():
        object.__setattr__(settings, key, value)
    set_ai_settings(settings.state_db_path, {k: str(v) for k, v in values.items()})
    return {"ok": True}


@app.post("/settings/test")
def test_settings_route():
    if not settings.ai_api_key:
        raise HTTPException(status_code=503, detail="AI_API_KEY not configured")
    try:
        return {"ok": True, "reply": test_connection(settings)}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"connection test failed: {e}")


app.mount("/", StaticFiles(directory="static", html=True), name="static")
