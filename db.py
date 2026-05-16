"""SQLite 存储层：schema 定义、upsert、查询 helpers。

设计要点：
- events.id 是 sha256("类型|艺人或标题|日期|场馆")[:16]，按启动文档第五节
  的「类型 + 艺人/标题 + 日期 + 场馆」生成。两个维度抽到同一事件会得到
  相同 ID，自然去重。
- upsert 行为：已存在则不动 first_seen 和 notified_at，只更新可能变化的
  字段（如 price_info / on_sale_time，源站后续可能更新）。
- notified_at 为 NULL 即"未通知"，是「查未通知」的钩子。
"""

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).parent / "data" / "events.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id              TEXT PRIMARY KEY,
    type            TEXT,
    title           TEXT,
    artist          TEXT,
    city            TEXT,
    venue           TEXT,
    event_date      TEXT,
    on_sale_time    TEXT,
    price_info      TEXT,
    purchase_url    TEXT,
    source          TEXT,
    source_url      TEXT,
    raw_ref         TEXT,
    discovered_via  TEXT,
    status          TEXT DEFAULT 'rumored',
    first_seen      TEXT NOT NULL,
    notified_at     TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_notified_at ON events(notified_at);

CREATE TABLE IF NOT EXISTS raw_captures (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT,
    url             TEXT,
    fetched_at      TEXT NOT NULL,
    file_path       TEXT,
    processed       INTEGER NOT NULL DEFAULT 0
);
"""


def make_event_id(event: dict) -> str:
    """稳定 ID = sha256(type|artist或title|event_date|venue)[:16]。

    artist 优先；非艺人活动（展览/活动）落到 title。
    """
    key_parts = [
        (event.get("type") or "").strip(),
        (event.get("artist") or event.get("title") or "").strip(),
        (event.get("event_date") or "").strip(),
        (event.get("venue") or "").strip(),
    ]
    plain = "|".join(key_parts)
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()[:16]


@contextmanager
def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db() -> None:
    with _conn() as c:
        c.executescript(SCHEMA)
        # 兼容旧 DB：补 discovered_via 列（如果是旧 schema 升级上来）
        cols = {row[1] for row in c.execute("PRAGMA table_info(events)").fetchall()}
        if "discovered_via" not in cols:
            c.execute("ALTER TABLE events ADD COLUMN discovered_via TEXT")


def upsert_event(event: dict[str, Any]) -> tuple[str, bool]:
    """插入 event，返回 (event_id, is_new)。

    已存在则只更新易变字段（price_info、on_sale_time、purchase_url、status），
    不动 first_seen 和 notified_at。
    """
    event_id = make_event_id(event)
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        existing = c.execute("SELECT id FROM events WHERE id = ?", (event_id,)).fetchone()
        if existing:
            c.execute(
                """
                UPDATE events SET
                    price_info   = COALESCE(?, price_info),
                    on_sale_time = COALESCE(?, on_sale_time),
                    purchase_url = COALESCE(?, purchase_url),
                    status       = COALESCE(?, status)
                WHERE id = ?
                """,
                (
                    event.get("price_info"),
                    event.get("on_sale_time"),
                    event.get("purchase_url"),
                    event.get("status"),
                    event_id,
                ),
            )
            return event_id, False

        c.execute(
            """
            INSERT INTO events
            (id, type, title, artist, city, venue, event_date, on_sale_time,
             price_info, purchase_url, source, source_url, raw_ref,
             discovered_via, status, first_seen, notified_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            """,
            (
                event_id,
                event.get("type"),
                event.get("title"),
                event.get("artist"),
                event.get("city"),
                event.get("venue"),
                event.get("event_date"),
                event.get("on_sale_time"),
                event.get("price_info"),
                event.get("purchase_url"),
                event.get("source"),
                event.get("source_url"),
                event.get("raw_ref"),
                event.get("discovered_via"),
                event.get("status") or "rumored",
                now,
            ),
        )
    return event_id, True


def get_unnotified_events() -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events WHERE notified_at IS NULL ORDER BY first_seen DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def mark_notified(event_ids: list[str]) -> None:
    if not event_ids:
        return
    now = datetime.now().isoformat(timespec="seconds")
    placeholders = ",".join("?" * len(event_ids))
    with _conn() as c:
        c.execute(
            f"UPDATE events SET notified_at = ? WHERE id IN ({placeholders})",
            (now, *event_ids),
        )
