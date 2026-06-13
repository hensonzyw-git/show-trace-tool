import app.api as api
import db
from fastapi import BackgroundTasks


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "events.db")
    db.init_db()


def test_feedback_schedules_rescore_in_background(monkeypatch):
    monkeypatch.setattr(
        api,
        "parse_preference_feedback",
        lambda feedback: {"profile": {}, "updates": {}, "parser": "test"},
    )

    inline_calls = []

    def fake_rescore(*, limit: int, enabled: bool) -> int:
        inline_calls.append({"limit": limit, "enabled": enabled})
        return 0

    monkeypatch.setattr(api, "_rescore_existing_events", fake_rescore)

    bg = BackgroundTasks()
    payload = api.PreferenceFeedbackRequest(feedback="多推荐演唱会")
    response = api.update_preferences_from_feedback(payload, background_tasks=bg, _=None)

    # Profile update returns immediately; the rescore is deferred to a background
    # task, not run inline, so the request can't block on 500 LLM calls.
    assert inline_calls == []
    assert response["rescored_events"] == 0
    assert response["rescore_scheduled"] is True
    assert len(bg.tasks) == 1
    assert bg.tasks[0].kwargs == {"limit": 500, "enabled": True}


def test_feedback_can_opt_out_of_rescore(monkeypatch):
    monkeypatch.setattr(
        api,
        "parse_preference_feedback",
        lambda feedback: {"profile": {}, "updates": {}, "parser": "test"},
    )

    bg = BackgroundTasks()
    payload = api.PreferenceFeedbackRequest(feedback="多推荐演唱会", rescore_existing=False)
    response = api.update_preferences_from_feedback(payload, background_tasks=bg, _=None)

    assert response["rescore_scheduled"] is False
    assert bg.tasks == []


def test_feedback_artist_updates_subscription(tmp_path, monkeypatch):
    _use_temp_db(tmp_path, monkeypatch)
    db.save_subscription(
        {
            "artists": ["周杰伦"],
            "local": {"city": "上海", "keywords": []},
            "sources": {},
        }
    )
    monkeypatch.setattr(
        api,
        "parse_preference_feedback",
        lambda feedback: {
            "profile": {},
            "updates": {
                "include_categories": [],
                "exclude_categories": [],
                "ranking_preferences": ["降低话剧优先级"],
                "artists": ["五月天"],
                "positive_signals": [],
                "negative_signals": [],
            },
            "parser": "test",
        },
    )

    bg = BackgroundTasks()
    payload = api.PreferenceFeedbackRequest(feedback="降低话剧优先级，增加艺人五月天")
    response = api.update_preferences_from_feedback(payload, background_tasks=bg, _=None)

    assert response["subscription"]["artists"] == ["周杰伦", "五月天"]
    assert db.get_subscription()["artists"] == ["周杰伦", "五月天"]
