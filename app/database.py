from __future__ import annotations

import time
from dataclasses import dataclass

import aiosqlite

_SCHEMA = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    entry_min REAL NOT NULL,
    entry_max REAL NOT NULL,
    sl REAL NOT NULL,
    tp1 REAL,
    tp2 REAL,
    tp3 REAL,
    tp4 REAL,
    tp5 REAL,
    tp1_hit INTEGER NOT NULL DEFAULT 0,
    tp2_hit INTEGER NOT NULL DEFAULT 0,
    tp3_hit INTEGER NOT NULL DEFAULT 0,
    tp4_hit INTEGER NOT NULL DEFAULT 0,
    tp5_hit INTEGER NOT NULL DEFAULT 0,
    sl_hit INTEGER NOT NULL DEFAULT 0,
    be_hit INTEGER NOT NULL DEFAULT 0,
    sl_moved_to_be INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    channel_type TEXT NOT NULL,
    telegram_message_id INTEGER NOT NULL,
    telegram_chat_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals(status);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id INTEGER NOT NULL,
    kind TEXT NOT NULL,                 -- tp1..tp5 or sl
    status TEXT NOT NULL DEFAULT 'pending',  -- pending/sent/cancelled
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(signal_id, kind, status) ON CONFLICT IGNORE
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);
"""


# Idempotent column additions for existing DBs. SQLite has no ADD COLUMN
# IF NOT EXISTS, so the runner swallows "duplicate column" failures.
_MIGRATIONS: tuple[str, ...] = (
    "ALTER TABLE signals ADD COLUMN be_hit INTEGER NOT NULL DEFAULT 0",
)


@dataclass(frozen=True)
class SignalRecord:
    id: int
    symbol: str
    direction: str
    entry_min: float
    entry_max: float
    sl: float
    tp1: float | None
    tp2: float | None
    tp3: float | None
    tp4: float | None
    tp5: float | None
    tp1_hit: bool
    tp2_hit: bool
    tp3_hit: bool
    tp4_hit: bool
    tp5_hit: bool
    sl_hit: bool
    be_hit: bool
    sl_moved_to_be: bool
    status: str
    channel_type: str
    telegram_message_id: int
    telegram_chat_id: str
    created_at: float
    updated_at: float


@dataclass(frozen=True)
class AlertRecord:
    id: int
    signal_id: int
    kind: str
    status: str
    created_at: float
    updated_at: float


class Database:
    def __init__(self, path: str) -> None:
        self._path = path

    async def init_schema(self) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(_SCHEMA)
            for stmt in _MIGRATIONS:
                try:
                    await db.execute(stmt)
                except Exception:
                    # column already exists on this DB
                    pass
            await db.commit()

    async def insert_signal(
        self,
        *,
        symbol: str,
        direction: str,
        entry_min: float,
        entry_max: float,
        sl: float,
        tp1: float | None,
        tp2: float | None,
        tp3: float | None,
        tp4: float | None,
        tp5: float | None,
        channel_type: str,
        telegram_message_id: int,
        telegram_chat_id: str,
    ) -> int:
        now = time.time()
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute(
                """
                INSERT INTO signals (
                    symbol, direction, entry_min, entry_max, sl,
                    tp1, tp2, tp3, tp4, tp5,
                    channel_type, telegram_message_id, telegram_chat_id,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    direction,
                    entry_min,
                    entry_max,
                    sl,
                    tp1,
                    tp2,
                    tp3,
                    tp4,
                    tp5,
                    channel_type,
                    telegram_message_id,
                    telegram_chat_id,
                    now,
                    now,
                ),
            )
            await db.commit()
            return int(cursor.lastrowid)

    async def _fetchall(self, sql: str, params: tuple[object, ...] = ()) -> list[SignalRecord]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [_row_to_record(r) for r in rows]

    async def fetch_active_signals(self) -> list[SignalRecord]:
        return await self._fetchall(
            "SELECT * FROM signals WHERE status = 'active' ORDER BY id ASC"
        )

    async def fetch_signal_by_id(self, sid: int) -> SignalRecord | None:
        rows = await self._fetchall("SELECT * FROM signals WHERE id = ? LIMIT 1", (sid,))
        return rows[0] if rows else None

    async def fetch_recent_signals(self, limit: int = 50) -> list[SignalRecord]:
        return await self._fetchall(
            """
            SELECT * FROM signals
            ORDER BY id DESC LIMIT ?
            """,
            (limit,),
        )

    async def update_hits_and_status(
        self,
        sid: int,
        *,
        tp1_hit: bool | None = None,
        tp2_hit: bool | None = None,
        tp3_hit: bool | None = None,
        tp4_hit: bool | None = None,
        tp5_hit: bool | None = None,
        sl_hit: bool | None = None,
        be_hit: bool | None = None,
        sl_moved_to_be: bool | None = None,
        status: str | None = None,
    ) -> None:
        parts: list[str] = []
        args: list[object] = []
        mapping = [
            ("tp1_hit", tp1_hit),
            ("tp2_hit", tp2_hit),
            ("tp3_hit", tp3_hit),
            ("tp4_hit", tp4_hit),
            ("tp5_hit", tp5_hit),
            ("sl_hit", sl_hit),
            ("be_hit", be_hit),
            ("sl_moved_to_be", sl_moved_to_be),
            ("status", status),
        ]
        for col, val in mapping:
            if val is None:
                continue
            parts.append(f"{col} = ?")
            if col == "status":
                args.append(str(val))
            else:
                args.append(int(bool(val)))

        if not parts:
            return

        now = time.time()
        parts.append("updated_at = ?")
        args.append(now)
        args.append(sid)

        sql = f"UPDATE signals SET {', '.join(parts)} WHERE id = ?"
        async with aiosqlite.connect(self._path) as db:
            await db.execute(sql, args)
            await db.commit()

    async def create_pending_alert(self, signal_id: int, kind: str) -> int | None:
        """
        Create a pending alert if none exists already for this signal/kind in pending state.
        Returns new alert id, or None if it already existed.
        """
        now = time.time()
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                """
                INSERT INTO alerts (signal_id, kind, status, created_at, updated_at)
                VALUES (?, ?, 'pending', ?, ?)
                """,
                (signal_id, kind, now, now),
            )
            await db.commit()
            rid = int(cur.lastrowid or 0)
            return rid or None

    async def fetch_alert_by_id(self, alert_id: int) -> AlertRecord | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM alerts WHERE id = ? LIMIT 1", (alert_id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        return _row_to_alert(row)

    async def fetch_pending_alert_for_signal(self, signal_id: int, kind: str) -> AlertRecord | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM alerts
                WHERE signal_id = ? AND kind = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
                """,
                (signal_id, kind),
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        return _row_to_alert(row)

    async def set_alert_status(self, alert_id: int, status: str) -> None:
        now = time.time()
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "UPDATE alerts SET status = ?, updated_at = ? WHERE id = ?",
                (status, now, alert_id),
            )
            await db.commit()


def _row_to_record(r: aiosqlite.Row) -> SignalRecord:
    return SignalRecord(
        id=int(r["id"]),
        symbol=str(r["symbol"]),
        direction=str(r["direction"]).upper(),
        entry_min=float(r["entry_min"]),
        entry_max=float(r["entry_max"]),
        sl=float(r["sl"]),
        tp1=float(r["tp1"]) if r["tp1"] is not None else None,
        tp2=float(r["tp2"]) if r["tp2"] is not None else None,
        tp3=float(r["tp3"]) if r["tp3"] is not None else None,
        tp4=float(r["tp4"]) if r["tp4"] is not None else None,
        tp5=float(r["tp5"]) if r["tp5"] is not None else None,
        tp1_hit=bool(r["tp1_hit"]),
        tp2_hit=bool(r["tp2_hit"]),
        tp3_hit=bool(r["tp3_hit"]),
        tp4_hit=bool(r["tp4_hit"]),
        tp5_hit=bool(r["tp5_hit"]),
        sl_hit=bool(r["sl_hit"]),
        be_hit=bool(r["be_hit"]),
        sl_moved_to_be=bool(r["sl_moved_to_be"]),
        status=str(r["status"]),
        channel_type=str(r["channel_type"]),
        telegram_message_id=int(r["telegram_message_id"]),
        telegram_chat_id=str(r["telegram_chat_id"]),
        created_at=float(r["created_at"]),
        updated_at=float(r["updated_at"]),
    )


def _row_to_alert(r: aiosqlite.Row) -> AlertRecord:
    return AlertRecord(
        id=int(r["id"]),
        signal_id=int(r["signal_id"]),
        kind=str(r["kind"]),
        status=str(r["status"]),
        created_at=float(r["created_at"]),
        updated_at=float(r["updated_at"]),
    )
