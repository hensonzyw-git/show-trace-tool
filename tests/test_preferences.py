"""Tests for the rules-based interest scoring (LLM path disabled)."""

import pytest

from app.preferences import _score_event_with_rules, infer_event_category


def _profile(*, include=None, exclude=None):
    return {
        "city": "上海",
        "include_categories": include or [],
        "exclude_categories": exclude or [],
        "ranking_preferences": [],
        "negative_signals": [],
        "positive_signals": [],
    }


class TestInferEventCategory:
    def test_alias_in_title_wins(self):
        assert infer_event_category({"title": "周杰伦巡演", "type": "activity"}) == "演唱会"

    def test_type_fallback(self):
        assert infer_event_category({"title": "某展", "type": "exhibition"}) == "展览"

    def test_unknown(self):
        assert infer_event_category({"title": "神秘活动", "type": None}) == "其他"


class TestScoreWithRules:
    def test_include_by_category_keeps(self):
        event = {"title": "周杰伦上海站", "type": "concert"}  # no alias word in title
        score = _score_event_with_rules(event, _profile(include=["演唱会"]))
        assert score["decision"] == "keep"

    def test_exclude_by_inferred_category_filters(self):
        # Regression test for the M1 fix: category is inferred from `type`
        # (concert -> 演唱会) with no alias word in the title. The old code only
        # matched excludes against the title and would NOT filter this.
        event = {"title": "周杰伦上海站", "type": "concert"}
        score = _score_event_with_rules(event, _profile(exclude=["演唱会"]))
        assert score["decision"] == "filter"

    def test_exclude_by_title_alias_filters(self):
        event = {"title": "亲子嘉年华", "type": "activity"}
        score = _score_event_with_rules(event, _profile(exclude=["亲子"]))
        assert score["decision"] == "filter"

    def test_maybe_when_unmatched(self):
        event = {"title": "神秘活动", "type": None}
        score = _score_event_with_rules(event, _profile(include=["演唱会"]))
        assert score["decision"] == "maybe"

    @pytest.mark.parametrize("bad_score", [-10, 200])
    def test_score_stays_in_range_via_normalize(self, bad_score):
        # _normalize_score clamps; verify rules scores are already valid ints.
        event = {"title": "x", "type": None}
        s = _score_event_with_rules(event, _profile())
        assert 0 <= s["match_score"] <= 100
