"""Tests for extractor HTML helpers (no LLM call)."""

from extractor import _resolve_detail_link, html_to_text


class TestResolveDetailLink:
    def test_damai_protocol_relative(self):
        assert _resolve_detail_link("//detail.damai.cn/item.htm?id=1") == (
            "https://detail.damai.cn/item.htm?id=1"
        )

    def test_damai_absolute(self):
        url = "https://detail.damai.cn/item.htm?id=2"
        assert _resolve_detail_link(url) == url

    def test_showstart_event(self):
        assert _resolve_detail_link("/event/123") == "https://www.showstart.com/event/123"

    def test_showstart_list_excluded(self):
        assert _resolve_detail_link("/event/list") is None

    def test_unknown(self):
        assert _resolve_detail_link("/foo/bar") is None


class TestHtmlToText:
    def test_strips_script_and_keeps_text(self):
        html = "<html><body><script>var x=1;</script><p>你好</p></body></html>"
        text = html_to_text(html)
        assert "你好" in text
        assert "var x" not in text

    def test_annotates_detail_link(self):
        html = '<a href="//detail.damai.cn/item.htm?id=9">演出</a>'
        text = html_to_text(html)
        assert "[link: https://detail.damai.cn/item.htm?id=9]" in text

    def test_truncates_to_limit(self):
        html = "<p>" + ("x" * 100) + "</p>"
        assert len(html_to_text(html, limit=10)) == 10
