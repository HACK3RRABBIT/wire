import sqlite3
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    chat_id INTEGER,
    title TEXT,
    status TEXT NOT NULL DEFAULT 'discovered',  -- discovered|active|failed
    last_message_id INTEGER DEFAULT 0,
    discovered_from TEXT
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


@contextmanager
def connect(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def add_channel(db_path: str, username: str, discovered_from: str | None = None) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO channels (username, discovered_from) VALUES (?, ?)",
            (username.lower(), discovered_from),
        )


def list_channels(db_path: str, status: str | None = None) -> list[sqlite3.Row]:
    with connect(db_path) as conn:
        if status:
            return conn.execute(
                "SELECT * FROM channels WHERE status = ?", (status,)
            ).fetchall()
        return conn.execute("SELECT * FROM channels").fetchall()


def mark_status(db_path: str, username: str, status: str, chat_id: int | None = None) -> None:
    with connect(db_path) as conn:
        if chat_id is not None:
            conn.execute(
                "UPDATE channels SET status = ?, chat_id = ? WHERE username = ?",
                (status, chat_id, username.lower()),
            )
        else:
            conn.execute(
                "UPDATE channels SET status = ? WHERE username = ?",
                (status, username.lower()),
            )


def update_last_message_id(db_path: str, username: str, message_id: int) -> None:
    with connect(db_path) as conn:
        conn.execute(
            "UPDATE channels SET last_message_id = ? WHERE username = ? AND last_message_id < ?",
            (message_id, username.lower(), message_id),
        )


def get_settings(db_path: str, keys: list[str]) -> dict[str, str]:
    with connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT key, value FROM settings WHERE key IN ({','.join('?' * len(keys))})",
            keys,
        ).fetchall()
        return {row["key"]: row["value"] for row in rows}


def set_settings(db_path: str, values: dict[str, str]) -> None:
    with connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            list(values.items()),
        )
