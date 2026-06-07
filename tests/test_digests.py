from app import database


def write_digest(directory, day: str, count: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"digest_{day}.md").write_text(
        f"# 演出活动监控摘要 - {day}\n\n共 **{count}** 条\n",
        encoding="utf-8",
    )


class TestListDigests:
    def test_lists_history_newest_first(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "DIGEST_DIR", tmp_path)
        write_digest(tmp_path, "2026-06-01", 1)
        write_digest(tmp_path, "2026-06-03", 3)
        write_digest(tmp_path, "2026-06-02", 2)

        digests = database.list_digests(limit=2, before_or_on="2026-06-03")

        assert [digest["date"] for digest in digests] == ["2026-06-03", "2026-06-02"]
        assert [digest["event_count"] for digest in digests] == [3, 2]

    def test_skips_future_digest_when_today_is_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(database, "DIGEST_DIR", tmp_path)
        write_digest(tmp_path, "2026-06-07", 7)
        write_digest(tmp_path, "2026-06-09", 9)

        digests = database.list_digests(limit=1, before_or_on="2026-06-08")

        assert [digest["date"] for digest in digests] == ["2026-06-07"]
