import meilisearch

from app.config import Settings

INDEX_NAME = "messages"


def get_index(settings: Settings):
    client = meilisearch.Client(settings.meili_url, settings.meili_key)
    index = client.index(INDEX_NAME)
    client.create_index(INDEX_NAME, {"primaryKey": "id"})
    index.update_filterable_attributes(["channel_username", "sender_id", "hashtags"])
    index.update_sortable_attributes(["date"])
    return index


def message_doc(
    *,
    message_id: int,
    channel_id: int,
    channel_username: str,
    sender_id: int | None,
    text: str,
    hashtags: list[str],
    date: int,
) -> dict:
    return {
        "id": f"{channel_id}_{message_id}",
        "channel_id": channel_id,
        "channel_username": channel_username,
        "sender_id": sender_id,
        "text": text,
        "hashtags": hashtags,
        "date": date,
    }


def index_messages(index, docs: list[dict]) -> None:
    if docs:
        index.add_documents(docs)


def search(
    index,
    query: str = "",
    *,
    hashtag: str | None = None,
    sender_id: int | None = None,
    facets: list[str] | None = None,
    limit: int = 20,
):
    filters = []
    if hashtag:
        filters.append(f'hashtags = "{hashtag.lower()}"')
    if sender_id is not None:
        filters.append(f"sender_id = {sender_id}")
    opts = {"limit": limit}
    if filters:
        opts["filter"] = " AND ".join(filters)
    if facets:
        opts["facets"] = facets
    return index.search(query, opts)
