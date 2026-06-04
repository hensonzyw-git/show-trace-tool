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
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from app.paths import DB_PATH

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

CREATE TABLE IF NOT EXISTS subscriptions (
    id              TEXT PRIMARY KEY,
    artists         TEXT NOT NULL,
    local_city      TEXT,
    local_keywords  TEXT NOT NULL,
    sources         TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger                 TEXT NOT NULL,
    fixture                 INTEGER NOT NULL DEFAULT 0,
    notify                  INTEGER NOT NULL DEFAULT 1,
    started_at              TEXT NOT NULL,
    finished_at             TEXT,
    status                  TEXT NOT NULL,
    total_raw_captures      INTEGER NOT NULL DEFAULT 0,
    total_extracted_events  INTEGER NOT NULL DEFAULT 0,
    new_events              INTEGER NOT NULL DEFAULT 0,
    notified_events         INTEGER NOT NULL DEFAULT 0,
    error_summary           TEXT
);

CREATE INDEX IF NOT EXISTS idx_runs_started_at ON runs(started_at);

CREATE TABLE IF NOT EXISTS interest_profiles (
    id              TEXT PRIMARY KEY,
    profile_json    TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS event_interest_scores (
    event_id          TEXT PRIMARY KEY,
    profile_id        TEXT NOT NULL,
    decision          TEXT NOT NULL,
    match_score       INTEGER NOT NULL,
    interest_category TEXT,
    reason            TEXT,
    uncertainty       TEXT,
    scored_at         TEXT NOT NULL,
    FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_event_interest_scores_decision
ON event_interest_scores(decision, match_score);
"""

DEFAULT_SUBSCRIPTION_ID = "default"
DEFAULT_INTEREST_PROFILE_ID = "default"
DEFAULT_INTEREST_PROFILE = {
    "city": "上海",
    "include_categories": ["体育比赛", "演唱会", "音乐会", "话剧"],
    "exclude_categories": ["曲艺杂谈", "亲子", "儿童剧"],
    "ranking_preferences": ["未来三个月优先", "可购票优先", "上海优先"],
    "negative_signals": [],
    "positive_signals": [],
}
DATE_PATTERN = re.compile(r"(\d{4})[-./年](\d{1,2})[-./月](\d{1,2})")
DATE_RANGE_TAIL_PATTERN = re.compile(
    r"\s*(?:-|~|至|到)\s*(?:(\d{4})[-./年])?(\d{1,2})[-./月](\d{1,2})"
)


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


def normalize_event_date(value: Any) -> str | None:
    """Normalize common ticket-site date text into YYYY-MM-DD or a date range."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    match = DATE_PATTERN.search(text)
    if not match:
        return text

    year, month, day = (int(part) for part in match.groups())
    start = f"{year:04d}-{month:02d}-{day:02d}"

    tail = text[match.end() :]
    range_match = DATE_RANGE_TAIL_PATTERN.search(tail)
    if not range_match:
        return start

    end_year_text, end_month_text, end_day_text = range_match.groups()
    end_month = int(end_month_text)
    end_day = int(end_day_text)
    end_year = int(end_year_text) if end_year_text else year
    if not end_year_text and end_month < month:
        end_year += 1
    end = f"{end_year:04d}-{end_month:02d}-{end_day:02d}"
    return f"{start} ~ {end}"


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(event)
    normalized["event_date"] = normalize_event_date(normalized.get("event_date"))
    return normalized


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


def subscription_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize config.yaml shape into the subscription API shape."""
    local = config.get("local") or {}
    return {
        "id": DEFAULT_SUBSCRIPTION_ID,
        "artists": config.get("artists") or [],
        "local": {
            "city": local.get("city"),
            "keywords": local.get("keywords") or [],
        },
        "sources": config.get("sources") or {},
    }


def ensure_subscription_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Create the default subscription from config.yaml if it does not exist."""
    init_db()
    current = get_subscription()
    if current:
        return current
    sub = subscription_from_config(config)
    save_subscription(sub)
    return sub


def get_subscription() -> dict[str, Any] | None:
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM subscriptions WHERE id = ?",
            (DEFAULT_SUBSCRIPTION_ID,),
        ).fetchone()
    if not row:
        return None
    return {
        "id": row["id"],
        "artists": json.loads(row["artists"]),
        "local": {
            "city": row["local_city"],
            "keywords": json.loads(row["local_keywords"]),
        },
        "sources": json.loads(row["sources"]),
        "updated_at": row["updated_at"],
    }


def save_subscription(subscription: dict[str, Any]) -> dict[str, Any]:
    """Upsert the single-user subscription record."""
    init_db()
    local = subscription.get("local") or {}
    normalized = {
        "id": DEFAULT_SUBSCRIPTION_ID,
        "artists": list(subscription.get("artists") or []),
        "local": {
            "city": local.get("city"),
            "keywords": list(local.get("keywords") or []),
        },
        "sources": dict(subscription.get("sources") or {}),
    }
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute(
            """
            INSERT INTO subscriptions
            (id, artists, local_city, local_keywords, sources, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                artists = excluded.artists,
                local_city = excluded.local_city,
                local_keywords = excluded.local_keywords,
                sources = excluded.sources,
                updated_at = excluded.updated_at
            """,
            (
                normalized["id"],
                json.dumps(normalized["artists"], ensure_ascii=False),
                normalized["local"]["city"],
                json.dumps(normalized["local"]["keywords"], ensure_ascii=False),
                json.dumps(normalized["sources"], ensure_ascii=False),
                now,
            ),
        )
    saved = get_subscription()
    if saved is None:
        raise RuntimeError("subscription save failed")
    return saved


def get_interest_profile(profile_id: str = DEFAULT_INTEREST_PROFILE_ID) -> dict[str, Any] | None:
    init_db()
    with _conn() as c:
        row = c.execute(
            "SELECT * FROM interest_profiles WHERE id = ?",
            (profile_id,),
        ).fetchone()
    if not row:
        return None
    profile = json.loads(row["profile_json"])
    profile["id"] = row["id"]
    profile["updated_at"] = row["updated_at"]
    return profile


def save_interest_profile(
    profile: dict[str, Any],
    profile_id: str = DEFAULT_INTEREST_PROFILE_ID,
) -> dict[str, Any]:
    init_db()
    normalized = {
        **DEFAULT_INTEREST_PROFILE,
        **{k: v for k, v in profile.items() if k not in {"id", "updated_at"}},
    }
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute(
            """
            INSERT INTO interest_profiles (id, profile_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                profile_json = excluded.profile_json,
                updated_at = excluded.updated_at
            """,
            (
                profile_id,
                json.dumps(normalized, ensure_ascii=False),
                now,
            ),
        )
    saved = get_interest_profile(profile_id)
    if saved is None:
        raise RuntimeError("interest profile save failed")
    return saved


def ensure_interest_profile() -> dict[str, Any]:
    current = get_interest_profile()
    if current:
        return current
    return save_interest_profile(DEFAULT_INTEREST_PROFILE)


def save_event_interest_score(
    event_id: str,
    score: dict[str, Any],
    profile_id: str = DEFAULT_INTEREST_PROFILE_ID,
) -> dict[str, Any]:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")
    normalized = {
        "event_id": event_id,
        "profile_id": profile_id,
        "decision": score.get("decision") or "maybe",
        "match_score": int(score.get("match_score") or 0),
        "interest_category": score.get("interest_category"),
        "reason": score.get("reason"),
        "uncertainty": score.get("uncertainty") or "medium",
        "scored_at": now,
    }
    with _conn() as c:
        c.execute(
            """
            INSERT INTO event_interest_scores
            (event_id, profile_id, decision, match_score, interest_category,
             reason, uncertainty, scored_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                profile_id = excluded.profile_id,
                decision = excluded.decision,
                match_score = excluded.match_score,
                interest_category = excluded.interest_category,
                reason = excluded.reason,
                uncertainty = excluded.uncertainty,
                scored_at = excluded.scored_at
            """,
            (
                normalized["event_id"],
                normalized["profile_id"],
                normalized["decision"],
                normalized["match_score"],
                normalized["interest_category"],
                normalized["reason"],
                normalized["uncertainty"],
                normalized["scored_at"],
            ),
        )
    return normalized


def upsert_event(event: dict[str, Any]) -> tuple[str, bool]:
    """插入 event，返回 (event_id, is_new)。

    已存在则只更新易变字段（price_info、on_sale_time、purchase_url、status），
    不动 first_seen 和 notified_at。
    """
    event = normalize_event(event)
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


def get_events_by_ids(event_ids: list[str]) -> list[dict[str, Any]]:
    if not event_ids:
        return []
    placeholders = ",".join("?" * len(event_ids))
    ordering = {event_id: idx for idx, event_id in enumerate(event_ids)}
    with _conn() as c:
        rows = c.execute(
            f"SELECT * FROM events WHERE id IN ({placeholders})",
            event_ids,
        ).fetchall()
    return sorted([dict(r) for r in rows], key=lambda event: ordering.get(event["id"], 0))


def get_events_missing_interest_scores(
    *,
    profile_id: str = DEFAULT_INTEREST_PROFILE_ID,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Return events that do not have an interest score for the profile yet."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            """
            SELECT events.*
            FROM events
            LEFT JOIN event_interest_scores scores
                ON scores.event_id = events.id
                AND scores.profile_id = ?
            WHERE scores.event_id IS NULL
            ORDER BY events.event_date IS NULL, events.event_date ASC, events.first_seen DESC
            LIMIT ?
            """,
            (profile_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def get_events_for_interest_scoring(*, limit: int = 500) -> list[dict[str, Any]]:
    """Return existing events in the same order used by the public list API."""
    init_db()
    with _conn() as c:
        rows = c.execute(
            """
            SELECT *
            FROM events
            ORDER BY event_date IS NULL, event_date ASC, first_seen DESC
            LIMIT ?
            """,
            (limit,),
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


def create_run(*, trigger: str, fixture: bool, notify: bool) -> int:
    init_db()
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        cur = c.execute(
            """
            INSERT INTO runs (trigger, fixture, notify, started_at, status)
            VALUES (?, ?, ?, ?, 'running')
            """,
            (trigger, int(fixture), int(notify), now),
        )
        return int(cur.lastrowid)


def finish_run(
    run_id: int,
    *,
    status: str,
    total_raw_captures: int,
    total_extracted_events: int,
    new_events: int,
    notified_events: int,
    error_summary: str | None = None,
) -> None:
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as c:
        c.execute(
            """
            UPDATE runs SET
                finished_at = ?,
                status = ?,
                total_raw_captures = ?,
                total_extracted_events = ?,
                new_events = ?,
                notified_events = ?,
                error_summary = ?
            WHERE id = ?
            """,
            (
                now,
                status,
                total_raw_captures,
                total_extracted_events,
                new_events,
                notified_events,
                error_summary,
                run_id,
            ),
        )


def list_runs(limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    init_db()
    with _conn() as c:
        rows = c.execute(
            """
            SELECT *
            FROM runs
            ORDER BY started_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        ).fetchall()
    return [_run_to_dict(row) for row in rows]


def get_run(run_id: int) -> dict[str, Any] | None:
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return _run_to_dict(row) if row else None


def _run_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "trigger": row["trigger"],
        "fixture": bool(row["fixture"]),
        "notify": bool(row["notify"]),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "status": row["status"],
        "total_raw_captures": row["total_raw_captures"],
        "total_extracted_events": row["total_extracted_events"],
        "new_events": row["new_events"],
        "notified_events": row["notified_events"],
        "error_summary": row["error_summary"],
    }
