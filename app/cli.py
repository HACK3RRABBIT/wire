import argparse
import asyncio
import logging

from telethon import TelegramClient
from telethon.sessions import StringSession

from app.config import settings
from app.crawler import backfill, discovery_loop, listen_live
from app.search_index import get_index
from app.state_db import add_channel

logging.basicConfig(level=logging.INFO)


async def cmd_login() -> None:
    async with TelegramClient(StringSession(), settings.api_id, settings.api_hash) as client:
        print("SESSION_STRING=" + client.session.save())


async def cmd_backfill(username: str) -> None:
    index = get_index(settings)
    async with _client() as client:
        count = await backfill(client, index, settings, username)
        print(f"indexed {count} messages from @{username}")


async def cmd_crawl() -> None:
    index = get_index(settings)
    for name in settings.seed_channels:
        add_channel(settings.state_db_path, name, discovered_from="seed")
    async with _client() as client:
        await discovery_loop(client, index, settings)
        await listen_live(client, index, settings)


def _client() -> TelegramClient:
    return TelegramClient(StringSession(settings.session_string), settings.api_id, settings.api_hash)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("login", help="generate a SESSION_STRING for .env")

    p_backfill = sub.add_parser("backfill", help="crawl full history of one channel/group")
    p_backfill.add_argument("username")

    sub.add_parser("crawl", help="run discovery + live indexing loop")
    sub.add_parser("serve", help="run the search API + web UI")

    args = parser.parse_args()
    if args.command == "login":
        asyncio.run(cmd_login())
    elif args.command == "backfill":
        asyncio.run(cmd_backfill(args.username))
    elif args.command == "crawl":
        asyncio.run(cmd_crawl())
    elif args.command == "serve":
        import uvicorn

        uvicorn.run("app.api:app", host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
