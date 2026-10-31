from __future__ import annotations

import os
from collections.abc import Iterator, MutableMapping
from threading import RLock
from typing import Any, Callable


class MemoryTable(dict[str, dict[str, Any]]):
    """Development/test table. Live deployments use PostgreSQL."""

    def put_if_absent(self, key: str, value: dict[str, Any]) -> bool:
        if key in self:
            return False
        self[key] = value
        return True

    def consume_nonce(self, key: str, nonce: str, role: str) -> bool:
        current = self.get(key)
        if not current or current.get("nonce") != nonce or current.get("role") != role:
            return False
        del self[key]
        return True

    def mutate(self, key: str, updater: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
        current = self.get(key)
        if current is None:
            return None
        updated = updater(current)
        self[key] = updated
        return updated


class JsonTable(MutableMapping[str, dict[str, Any]]):
    """A small JSONB-backed mapping for the API's prototype-shaped records."""

    def __init__(self, database_url: str, collection: str) -> None:
        self.database_url = database_url
        self.collection = collection

    def _connect(self):
        import psycopg

        return psycopg.connect(self.database_url, connect_timeout=5)

    def __getitem__(self, key: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM trustgraph_store WHERE collection = %s AND key = %s",
                (self.collection, key),
            ).fetchone()
        if row is None:
            raise KeyError(key)
        return row[0]

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: str, value: dict[str, Any]) -> None:
        from psycopg.types.json import Jsonb

        with self._connect() as connection:
            connection.execute(
                """INSERT INTO trustgraph_store (collection, key, value) VALUES (%s, %s, %s)
                   ON CONFLICT (collection, key) DO UPDATE SET value = EXCLUDED.value""",
                (self.collection, key, Jsonb(value)),
            )

    def put_if_absent(self, key: str, value: dict[str, Any]) -> bool:
        from psycopg.types.json import Jsonb

        with self._connect() as connection:
            row = connection.execute(
                """INSERT INTO trustgraph_store (collection, key, value) VALUES (%s, %s, %s)
                   ON CONFLICT (collection, key) DO NOTHING RETURNING key""",
                (self.collection, key, Jsonb(value)),
            ).fetchone()
        return row is not None

    def consume_nonce(self, key: str, nonce: str, role: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """DELETE FROM trustgraph_store WHERE collection = %s AND key = %s
                   AND value->>'nonce' = %s AND value->>'role' = %s RETURNING key""",
                (self.collection, key, nonce, role),
            ).fetchone()
        return row is not None

    def mutate(self, key: str, updater: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any] | None:
        from psycopg.types.json import Jsonb

        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM trustgraph_store WHERE collection = %s AND key = %s FOR UPDATE",
                (self.collection, key),
            ).fetchone()
            if row is None:
                return None
            updated = updater(row[0])
            connection.execute(
                "UPDATE trustgraph_store SET value = %s WHERE collection = %s AND key = %s",
                (Jsonb(updated), self.collection, key),
            )
        return updated

    def __delitem__(self, key: str) -> None:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM trustgraph_store WHERE collection = %s AND key = %s",
                (self.collection, key),
            )
            if cursor.rowcount == 0:
                raise KeyError(key)

    def pop(self, key: str, default: Any = None) -> Any:
        with self._connect() as connection:
            row = connection.execute(
                "DELETE FROM trustgraph_store WHERE collection = %s AND key = %s RETURNING value",
                (self.collection, key),
            ).fetchone()
        return row[0] if row else default

    def __iter__(self) -> Iterator[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT key FROM trustgraph_store WHERE collection = %s", (self.collection,)
            ).fetchall()
        return iter(row[0] for row in rows)

    def __len__(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT count(*) FROM trustgraph_store WHERE collection = %s", (self.collection,)
            ).fetchone()
        return int(row[0])

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM trustgraph_store WHERE collection = %s", (self.collection,))


class MemoryStore:
    def __init__(self) -> None:
        self.persons: MutableMapping[str, dict[str, Any]] = MemoryTable()
        self.credentials: MutableMapping[str, dict[str, Any]] = MemoryTable()
        self.payments: MutableMapping[str, dict[str, Any]] = MemoryTable()
        self.ngo_applications: MutableMapping[str, dict[str, Any]] = MemoryTable()
        self.nonces: MutableMapping[str, dict[str, Any]] = MemoryTable()
        self.sessions: MutableMapping[str, dict[str, Any]] = MemoryTable()
        self.lock = RLock()


class PostgresStore(MemoryStore):
    def __init__(self, database_url: str) -> None:
        import psycopg

        self.database_url = database_url.replace("postgres://", "postgresql://", 1)
        with psycopg.connect(self.database_url, connect_timeout=5) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS trustgraph_store (
                    collection TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value JSONB NOT NULL,
                    PRIMARY KEY (collection, key)
                )"""
            )
        self.persons = JsonTable(self.database_url, "persons")
        self.credentials = JsonTable(self.database_url, "credentials")
        self.payments = JsonTable(self.database_url, "payments")
        self.ngo_applications = JsonTable(self.database_url, "ngo_applications")
        self.nonces = JsonTable(self.database_url, "nonces")
        self.sessions = JsonTable(self.database_url, "sessions")
        self.lock = RLock()


def create_store() -> MemoryStore:
    database_url = os.getenv("DATABASE_URL", "").strip()
    app_env = os.getenv("APP_ENV", "development").lower()
    if database_url:
        return PostgresStore(database_url)
    if app_env == "production" or os.getenv("VERCEL") == "1":
        raise RuntimeError("DATABASE_URL is required when APP_ENV=production")
    return MemoryStore()


store = create_store()
