import logging

from telethon import events
from telethon.errors import ChannelPrivateError, UserAlreadyParticipantError
from telethon.tl.functions.channels import JoinChannelRequest

from app.config import Settings
from app.discover import extract_hashtags, extract_usernames
from app.search_index import index_messages, message_doc
from app.state_db import add_channel, list_channels, mark_status, update_last_message_id

log = logging.getLogger(__name__)


async def _resolve_readable(client, username: str):
    """Return an entity we can read history from, joining only if required."""
    entity = await client.get_entity(username)
    try:
        async for _ in client.iter_messages(entity, limit=1):
            pass
        return entity
    except ChannelPrivateError:
        try:
            await client(JoinChannelRequest(entity))
        except UserAlreadyParticipantError:
            pass
        return entity


def _is_excluded(chat_id: int, settings: Settings) -> bool:
    return chat_id in settings.exclude_chat_ids


async def backfill(client, index, settings: Settings, username: str) -> int:
    """Crawl full history of one channel/group. Returns number of messages indexed."""
    entity = await _resolve_readable(client, username)
    chat_id = entity.id
    if _is_excluded(chat_id, settings):
        log.info("skipping excluded chat %s", username)
        return 0

    count = 0
    batch = []
    max_id = 0
    async for message in client.iter_messages(entity):
        if not message.text:
            continue
        batch.append(
            message_doc(
                message_id=message.id,
                channel_id=chat_id,
                channel_username=username.lower(),
                sender_id=message.sender_id,
                text=message.text,
                hashtags=sorted(extract_hashtags(message.text)),
                date=int(message.date.timestamp()),
            )
        )
        max_id = max(max_id, message.id)
        for found in extract_usernames(message.text):
            add_channel(settings.state_db_path, found, discovered_from=username)
        if len(batch) >= 500:
            index_messages(index, batch)
            count += len(batch)
            batch = []

    index_messages(index, batch)
    count += len(batch)
    mark_status(settings.state_db_path, username, "active", chat_id=chat_id)
    if max_id:
        update_last_message_id(settings.state_db_path, username, max_id)
    return count


async def listen_live(client, index, settings: Settings) -> None:
    """Attach a single NewMessage handler and index messages as they arrive."""

    @client.on(events.NewMessage)
    async def _handler(event):
        message = event.message
        if not message.text or _is_excluded(event.chat_id, settings):
            return
        chat = await event.get_chat()
        username = (getattr(chat, "username", None) or "").lower()
        index_messages(
            index,
            [
                message_doc(
                    message_id=message.id,
                    channel_id=event.chat_id,
                    channel_username=username,
                    sender_id=message.sender_id,
                    text=message.text,
                    hashtags=sorted(extract_hashtags(message.text)),
                    date=int(message.date.timestamp()),
                )
            ],
        )
        if username:
            for found in extract_usernames(message.text):
                add_channel(settings.state_db_path, found, discovered_from=username)

    await client.run_until_disconnected()


async def discovery_loop(client, index, settings: Settings) -> None:
    """Backfill any channel discovered but not yet crawled."""
    for row in list_channels(settings.state_db_path, status="discovered"):
        try:
            await backfill(client, index, settings, row["username"])
        except Exception:
            log.exception("failed to backfill discovered channel %s", row["username"])
            mark_status(settings.state_db_path, row["username"], "failed")
