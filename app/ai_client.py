import json
import urllib.request

from app.config import Settings

MAX_HITS_IN_PROMPT = 30
MAX_CHARS_PER_HIT = 300
MAX_HITS_PER_TOOL_CALL = 15

SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "search",
        "description": (
            "Full-text search across public Telegram channels/groups. "
            "Use hashtag for an exact #tag match, query for free text. "
            "Call multiple times with different terms to explore before answering."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Free-text search terms"},
                "hashtag": {"type": "string", "description": "Exact hashtag, no #"},
            },
        },
    },
}


def _chat(settings: Settings, messages: list[dict], tools: list[dict] | None = None) -> dict:
    if not settings.ai_api_key:
        raise RuntimeError("AI_API_KEY not set")
    payload = {"model": settings.ai_model, "messages": messages, "stream": False}
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        settings.ai_base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {settings.ai_api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def test_connection(settings: Settings) -> str:
    """Send a trivial prompt to confirm base URL/key/model actually work. Returns the model's reply."""
    data = _chat(settings, [{"role": "user", "content": "Reply with exactly: ok"}])
    return data["choices"][0]["message"]["content"]


def summarize_hits(settings: Settings, query: str, hits: list[dict]) -> str:
    snippets = "\n".join(
        f"- (@{h.get('channel_username', '?')}) {h.get('text', '')[:MAX_CHARS_PER_HIT]}"
        for h in hits[:MAX_HITS_IN_PROMPT]
    )
    prompt = (
        f'Search query: "{query}"\n\n'
        f"Results from public Telegram channels:\n{snippets}\n\n"
        "Summarize the key themes, sentiment, and any notable patterns across "
        "these results in a few short paragraphs."
    )
    data = _chat(settings, [{"role": "user", "content": prompt}])
    return data["choices"][0]["message"]["content"]


def agentic_search(settings: Settings, question: str, search_fn, max_rounds: int | None = None) -> dict:
    """Let the model call `search_fn(query, hashtag)` up to max_rounds times, then answer.

    search_fn must return a list of hit dicts (channel_username, text, ...).
    Returns {"answer": str, "searches": [{"query", "hashtag", "hit_count"}]}.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "You search public Telegram channels/groups on the user's behalf. "
                "Use the search tool to explore, refining your terms across multiple "
                "calls if the first results are thin or off-target. When you have "
                "enough, answer the user's question directly, citing channel handles."
            ),
        },
        {"role": "user", "content": question},
    ]
    searches = []
    max_rounds = max_rounds or settings.ai_max_rounds

    for _ in range(max_rounds):
        data = _chat(settings, messages, tools=[SEARCH_TOOL])
        message = data["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []
        if not tool_calls:
            return {"answer": message.get("content", ""), "searches": searches}

        messages.append(message)
        for call in tool_calls:
            args = json.loads(call["function"]["arguments"] or "{}")
            query, hashtag = args.get("query", ""), args.get("hashtag")
            hits = search_fn(query, hashtag)
            searches.append({"query": query, "hashtag": hashtag, "hit_count": len(hits)})
            snippets = "\n".join(
                f"(@{h.get('channel_username', '?')}) {h.get('text', '')[:MAX_CHARS_PER_HIT]}"
                for h in hits[:MAX_HITS_PER_TOOL_CALL]
            ) or "(no results)"
            messages.append(
                {"role": "tool", "tool_call_id": call["id"], "content": snippets}
            )

    data = _chat(settings, messages)
    return {"answer": data["choices"][0]["message"].get("content", ""), "searches": searches}
