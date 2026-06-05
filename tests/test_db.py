"""Tests for the pure helpers in db.py (no SQLite / network needed)."""

from db import make_event_id, normalize_event_date


class TestNormalizeEventDate:
    def test_none_and_blank(self):
        assert normalize_event_date(None) is None
        assert normalize_event_date("   ") is None

    def test_iso_date(self):
        assert normalize_event_date("2026-06-20") == "2026-06-20"

    def test_chinese_date(self):
        assert normalize_event_date("2026年5月3日 19:30") == "2026-05-03"

    def test_dotted_date(self):
        assert normalize_event_date("2026.05.16") == "2026-05-16"

    def test_range_same_year(self):
        assert normalize_event_date("2026.05.16-05.17") == "2026-05-16 ~ 2026-05-17"

    def test_range_year_rollover(self):
        # End month earlier than start month and no explicit end year -> +1 year.
        assert normalize_event_date("2026-12-30 ~ 01-02") == "2026-12-30 ~ 2027-01-02"

    def test_unparseable_passthrough(self):
        assert normalize_event_date("待定") == "待定"


class TestMakeEventId:
    def test_stable_and_16_chars(self):
        event = {
            "type": "concert",
            "artist": "周杰伦",
            "event_date": "2026-06-20",
            "venue": "梅赛德斯",
        }
        first = make_event_id(event)
        assert len(first) == 16
        assert first == make_event_id(dict(event))

    def test_artist_preferred_over_title(self):
        with_artist = {"type": "concert", "artist": "A", "title": "T", "event_date": "d", "venue": "v"}
        title_only = {"type": "concert", "artist": "A", "event_date": "d", "venue": "v"}
        assert make_event_id(with_artist) == make_event_id(title_only)

    def test_different_venue_different_id(self):
        base = {"type": "concert", "artist": "A", "event_date": "d", "venue": "v1"}
        other = {**base, "venue": "v2"}
        assert make_event_id(base) != make_event_id(other)
