"""Tests for notifier helpers (no network)."""

from notifiers.feishu_card import build_card, build_card_lines
from notifiers.markdown import NO_DATE_KEY, MarkdownNotifier


class TestDateKey:
    def test_iso(self):
        assert MarkdownNotifier._date_key("2026-06-20") == "2026-06-20"

    def test_chinese(self):
        assert MarkdownNotifier._date_key("2026年5月3日") == "2026-05-03"

    def test_missing(self):
        assert MarkdownNotifier._date_key(None) == NO_DATE_KEY
        assert MarkdownNotifier._date_key("待定") == NO_DATE_KEY


class TestFeishuCard:
    def _events(self, n):
        return [
            {"title": f"演出{i}", "event_date": f"2099-01-{i + 1:02d}"} for i in range(n)
        ]

    def test_wording_is_pending_not_new(self):
        lines, _ = build_card_lines(self._events(2), "2026-01-01")
        header = lines[0]
        assert "待通知事件" in header
        assert "新事件" not in header

    def test_caps_at_top_n(self):
        lines, upcoming = build_card_lines(self._events(7), "2026-01-01")
        assert len(upcoming) == 5  # TOP_N
        assert "共 **7**" in lines[0]

    def test_build_card_shape(self):
        card, _ = build_card(self._events(1), "2026-01-01")
        assert card["elements"][0]["tag"] == "markdown"
        assert "演出活动监控" in card["header"]["title"]["content"]
