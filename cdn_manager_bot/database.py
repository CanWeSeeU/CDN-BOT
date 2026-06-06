from __future__ import annotations

import json
import logging
from typing import Any

import aiosqlite

from config import DB_FILE

logger = logging.getLogger(__name__)


class Database:
    """
    Async SQLite wrapper.

    Obtain an instance once during bot startup and pass it around as
    application bot_data so all handlers share the same connection pool.
    """

    def __init__(self) -> None:
        self._db: aiosqlite.Connection | None = None

    # ── lifecycle ──────────────────────────────────────────────────────────

    async def connect(self) -> None:
        """Open the database connection and create tables if needed."""
        self._db = await aiosqlite.connect(DB_FILE)
        self._db.row_factory = aiosqlite.Row
        await self._create_tables()
        logger.info("Database connected: %s", DB_FILE)

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            logger.info("Database connection closed")

    # ── schema ─────────────────────────────────────────────────────────────

    async def _create_tables(self) -> None:
        assert self._db is not None
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS user_zones (
                user_id     INTEGER PRIMARY KEY,
                zone_id     TEXT    NOT NULL,
                zone_name   TEXT    NOT NULL,
                updated_at  TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS user_state (
                user_id     INTEGER PRIMARY KEY,
                state_key   TEXT    NOT NULL,
                state_data  TEXT    NOT NULL DEFAULT '{}',
                updated_at  TEXT    DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS dns_cache (
                zone_id     TEXT    PRIMARY KEY,
                records     TEXT    NOT NULL DEFAULT '[]',
                cached_at   TEXT    DEFAULT (datetime('now'))
            );
            """
        )
        await self._db.commit()

    # ── selected zone ──────────────────────────────────────────────────────

    async def set_selected_zone(
        self, user_id: int, zone_id: str, zone_name: str
    ) -> None:
        """Persist the zone that the user has currently selected."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO user_zones (user_id, zone_id, zone_name, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                zone_id   = excluded.zone_id,
                zone_name = excluded.zone_name,
                updated_at = excluded.updated_at
            """,
            (user_id, zone_id, zone_name),
        )
        await self._db.commit()

    async def get_selected_zone(self, user_id: int) -> dict | None:
        """Return ``{"zone_id": ..., "zone_name": ...}`` or *None*."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT zone_id, zone_name FROM user_zones WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return {"zone_id": row["zone_id"], "zone_name": row["zone_name"]}

    async def clear_selected_zone(self, user_id: int) -> None:
        """Remove the user's selected zone."""
        assert self._db is not None
        await self._db.execute(
            "DELETE FROM user_zones WHERE user_id = ?", (user_id,)
        )
        await self._db.commit()

    # ── conversation / wizard state ────────────────────────────────────────

    async def set_state(
        self, user_id: int, state_key: str, data: dict[str, Any]
    ) -> None:
        """Persist arbitrary wizard state for a user."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO user_state (user_id, state_key, state_data, updated_at)
            VALUES (?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                state_key  = excluded.state_key,
                state_data = excluded.state_data,
                updated_at = excluded.updated_at
            """,
            (user_id, state_key, json.dumps(data)),
        )
        await self._db.commit()

    async def get_state(self, user_id: int) -> tuple[str, dict[str, Any]] | None:
        """
        Return ``(state_key, data_dict)`` for the user, or *None* if absent.
        """
        assert self._db is not None
        async with self._db.execute(
            "SELECT state_key, state_data FROM user_state WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return row["state_key"], json.loads(row["state_data"])

    async def clear_state(self, user_id: int) -> None:
        """Remove any wizard state for the user."""
        assert self._db is not None
        await self._db.execute(
            "DELETE FROM user_state WHERE user_id = ?", (user_id,)
        )
        await self._db.commit()

    # ── DNS record cache ───────────────────────────────────────────────────

    async def cache_dns_records(self, zone_id: str, records: list[dict]) -> None:
        """Overwrite the cached records for *zone_id*."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO dns_cache (zone_id, records, cached_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(zone_id) DO UPDATE SET
                records   = excluded.records,
                cached_at = excluded.cached_at
            """,
            (zone_id, json.dumps(records)),
        )
        await self._db.commit()

    async def get_cached_dns_records(self, zone_id: str) -> list[dict] | None:
        """Return cached DNS records for *zone_id*, or *None* if missing."""
        assert self._db is not None
        async with self._db.execute(
            "SELECT records FROM dns_cache WHERE zone_id = ?", (zone_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row is None:
                return None
            return json.loads(row["records"])

    async def invalidate_dns_cache(self, zone_id: str) -> None:
        """Remove the cached DNS records so the next fetch is fresh."""
        assert self._db is not None
        await self._db.execute(
            "DELETE FROM dns_cache WHERE zone_id = ?", (zone_id,)
        )
        await self._db.commit()
