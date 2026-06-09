import db
from app import api, database, summary
from app.api import SubscriptionPayload


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "events.db"
    digest_dir = tmp_path / "digests"
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", db_path)
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(database, "DIGEST_DIR", digest_dir)
    monkeypatch.setattr(summary, "DIGEST_DIR", digest_dir)
    db.init_db()


def _add_event(*, title, event_date, decision="keep", score=0):
    event_id, _ = db.upsert_event(
        {
            "type": "concert",
            "title": title,
            "city": "上海",
            "event_date": event_date,
            "venue": title,  # keep ids distinct
            "source": "damai",
            "purchase_url": "http://example.com/buy",
        }
    )
    db.save_event_interest_score(
        event_id,
        {"decision": decision, "match_score": score, "interest_category": "演唱会"},
    )
    return event_id


class TestDateFromFiltering:
    def test_date_from_keeps_future_and_undated_drops_expired(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _add_event(title="past", event_date="2020-01-01")
        _add_event(title="future", event_date="2999-01-01")
        _add_event(title="undated", event_date=None)

        titles = {e["title"] for e in database.list_events(date_from="2026-06-10", limit=100)}

        assert "future" in titles
        assert "undated" in titles  # 待定保留
        assert "past" not in titles  # 过期隐藏
        assert database.count_events(date_from="2026-06-10") == 2


class TestCitySync:
    def test_put_subscription_syncs_profile_city(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        payload = SubscriptionPayload(
            artists=["五月天"],
            local={"city": "北京", "keywords": ["livehouse"]},
            sources={"damai": {"enabled": True}},
        )

        saved = api.update_default_subscription(payload, _=None)

        assert saved["local"]["city"] == "北京"
        assert db.get_interest_profile()["city"] == "北京"


class TestDailySummarySnapshot:
    def test_build_ranks_keep_unexpired_by_score(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _add_event(title="hi", event_date="2026-12-31", decision="keep", score=90)
        _add_event(title="lo", event_date="2026-12-31", decision="keep", score=20)
        _add_event(title="mid", event_date=None, decision="keep", score=55)
        _add_event(title="maybe", event_date="2026-12-31", decision="maybe", score=99)
        _add_event(title="expired", event_date="2000-01-01", decision="keep", score=99)

        summary.build_daily_summary(day="2026-01-01")
        result = summary.read_daily_summary()

        titles = [e["title"] for e in result["events"]]
        assert titles == ["hi", "mid", "lo"]  # score desc, maybe/expired excluded
        assert result["event_count"] == 3

    def test_today_digest_endpoint_returns_structured_events(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        _add_event(title="solo", event_date="2026-12-31", decision="keep", score=70)
        summary.build_daily_summary(day="2026-01-01")

        response = api.get_today_digest(_=None)

        assert response["event_count"] == 1
        assert [e["title"] for e in response["events"]] == ["solo"]
        assert response["events"][0]["interest_decision"] == "keep"

    def test_snapshot_freezes_event_fields(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        event_id = _add_event(title="frozen", event_date="2026-12-31", decision="keep", score=70)
        summary.build_daily_summary(day="2026-01-01")
        db.save_event_interest_score(
            event_id,
            {"decision": "filter", "match_score": 1, "interest_category": "亲子"},
        )

        result = summary.read_daily_summary()

        assert result["events"][0]["interest_decision"] == "keep"
        assert result["events"][0]["interest_match_score"] == 70
        assert result["events"][0]["interest_category"] == "演唱会"
