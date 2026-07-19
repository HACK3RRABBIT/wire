<p align="center"><img src="static/logo.svg" alt="Wire" width="96"></p>

# Wire

Search engine for **public** Telegram channels and groups — search by keyword/topic,
by hashtag, see which channels a term shows up in, or which channels a given user ID
has posted in. Only public content is indexed; your own chats are excluded by
`EXCLUDE_CHAT_IDS`.

Telegram has no API for "list every group a user belongs to" — that's only visible
for chats the querying account already shares, by design. This tool instead answers
"which indexed channels has this user *posted a message* in," which is derivable from
crawled data.

## How it works

- **Telethon** talks to Telegram (MTProto) as a normal user account.
- **Meilisearch** stores and serves full-text search over indexed messages.
- A small **SQLite** file tracks crawl state (which channels are known/active/failed).
- Discovery starts from a seed list of channel usernames and expands by following
  `@mentions`, `t.me/<username>` links, and forwards found in indexed messages.

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

API:

- `GET /search?q=<text>` — keyword/topic search
- `GET /search?hashtag=<tag>` — hashtag search
- `GET /channels` — list known channels and their crawl status
- `GET /users/{sender_id}/channels` — channels where that sender has posted

## Tests

```bash
pytest
```

`tests/test_discover.py` covers username/hashtag extraction (pure, no network).
`tests/test_api.py` covers the API against a stubbed search index.
