<p align="center"><img src="static/logo.svg" alt="Wire" width="96"></p>

# Wire

Open-source search engine for **public** Telegram channels and groups — search by
keyword/topic, by hashtag, see which channels a term shows up in, or which channels
a given user ID has posted in. Only public content is indexed; your own chats are
excluded by `EXCLUDE_CHAT_IDS`, checked at ingestion time so they never enter the index.

Telegram has no API for "list every group a user belongs to" — that's only visible
for chats the querying account already shares, by design. This tool instead answers
"which indexed channels has this user *posted a message* in," which is derivable from
crawled data.

Ships with a single-page web UI (no build step) for searching, asking an AI to search
on your behalf, and summarizing results — all themed as an old telegraph office.

## How it works

- **Telethon** talks to Telegram (MTProto) as a normal user account.
- **Meilisearch** stores and serves full-text search over indexed messages.
- A small **SQLite** file tracks crawl state (which channels are known/active/failed)
  and any AI settings saved from the web UI.
- Discovery starts from a seed list of channel usernames and expands by following
  `@mentions`, `t.me/<username>` links, and forwards found in indexed messages.
- An optional **OpenAI-compatible** AI backend (any provider with a `/chat/completions`
  endpoint — OpenAI, a local router, etc.) powers result summaries and an agentic
  search mode where the model runs its own searches before answering.

## Setup

```bash
cp .env.example .env
# fill in API_ID / API_HASH from https://my.telegram.org

docker compose up -d          # starts Meilisearch

pip install -e ".[dev]"

python -m app.cli login       # prints SESSION_STRING — paste into .env
```

## Usage

```bash
# one-off: backfill full history of a single public channel/group
python -m app.cli backfill telegram

# ongoing: discover + backfill new channels, then listen for live messages
python -m app.cli crawl

# start the search API + web UI at http://localhost:8000
python -m app.cli serve
```

Open `http://localhost:8000` for the search UI, or use the API directly:

- `GET /search?q=<text>` — keyword/topic search
- `GET /search?hashtag=<tag>` — hashtag search
- `GET /channels` — list known channels and their crawl status
- `GET /users/{sender_id}/channels` — channels where that sender has posted
- `GET /analyze?q=<text>` — AI summary of the top search results
- `GET /ask?q=<question>` — agentic search: the AI runs its own searches, then answers
- `GET /settings` / `POST /settings` — read/write the AI connection config
- `POST /settings/test` — send a trivial prompt to confirm the AI config works

## AI setup

AI features (`/analyze`, `/ask`) are optional and off until an API key is set. Two ways:

- **Web UI** — click "AI settings" in the header, fill in base URL / API key / model,
  pick a search depth (how many searches the AI can run before answering), save.
  Takes effect immediately, no restart. Settings persist in the SQLite state file.
- **.env** — set `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`, `AI_MAX_ROUNDS` before first run.

Web UI settings override `.env` values once saved.

## Tests

```bash
pytest
```

`tests/test_discover.py` covers username/hashtag extraction (pure, no network).
`tests/test_api.py` covers the API against a stubbed search index.

## License

MIT — see [LICENSE](LICENSE).
