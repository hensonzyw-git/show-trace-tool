import app.api as api


def test_feedback_does_not_rescore_by_default(monkeypatch):
    calls = []

    monkeypatch.setattr(
        api,
        "parse_preference_feedback",
        lambda feedback: {"profile": {}, "updates": {}, "parser": "test"},
    )

    def fake_rescore(*, limit: int, enabled: bool) -> int:
        calls.append({"limit": limit, "enabled": enabled})
        return 0

    monkeypatch.setattr(api, "_rescore_existing_events", fake_rescore)

    payload = api.PreferenceFeedbackRequest(feedback="多推荐演唱会")
    response = api.update_preferences_from_feedback(payload, _=None)

    assert response["rescored_events"] == 0
    assert calls == [{"limit": 500, "enabled": False}]
