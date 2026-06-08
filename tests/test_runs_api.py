from fastapi import BackgroundTasks

import app.api as api
import app.pipeline as pipeline
import db
from app.api import ImportEvent, ImportEventsRequest, RunRequest


def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "events.db")
    db.init_db()


class TestRunTriggerAPI:
    def test_create_manual_run_returns_running_without_executing_worker(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", tmp_path)
        monkeypatch.setattr(db, "DB_PATH", tmp_path / "events.db")
        db.init_db()

        background_tasks = BackgroundTasks()
        response = api.create_manual_run(
            RunRequest(fixture=False, notify=True),
            background_tasks,
            _=None,
        )

        assert response["status"] == "running"
        assert response["run_id"] == 1
        assert response["total_extracted_events"] == 0
        assert len(background_tasks.tasks) == 1

        [run] = db.list_runs()
        assert run["id"] == 1
        assert run["status"] == "running"
        assert run["finished_at"] is None

    def test_create_manual_run_skips_when_lock_is_held(self, tmp_path, monkeypatch):
        monkeypatch.setattr(db, "DATA_DIR", tmp_path)
        monkeypatch.setattr(db, "DB_PATH", tmp_path / "events.db")
        db.init_db()

        with db.try_acquire_run_lock() as acquired:
            assert acquired is True
            response = api.create_manual_run(
                RunRequest(fixture=False, notify=True),
                BackgroundTasks(),
                _=None,
            )

        assert response["status"] == "skipped"
        assert response["run_id"] is None
        assert db.list_runs() == []

    def test_create_manual_run_skips_when_a_run_is_already_active(self, tmp_path, monkeypatch):
        _use_temp_db(tmp_path, monkeypatch)
        # An earlier run is still "running" but the lock is free (e.g. the worker
        # released it between requests). The durable guard must still reject.
        db.create_run(trigger="api", fixture=False, notify=True)

        response = api.create_manual_run(
            RunRequest(fixture=False, notify=True),
            BackgroundTasks(),
            _=None,
        )

        assert response["status"] == "skipped"
        assert response["run_id"] is None
        # No second row was created.
        assert len(db.list_runs()) == 1


class TestImportEventsAPI:
    def test_import_skips_when_a_run_is_already_active(self, tmp_path, monkeypatch):
        _use_temp_db(tmp_path, monkeypatch)
        db.create_run(trigger="api", fixture=False, notify=True)

        response = api.import_events(
            ImportEventsRequest(
                events=[
                    ImportEvent(
                        type="concert",
                        title="示例演出",
                        source="local-test",
                    )
                ],
                notify=False,
                trigger="local-sync",
            ),
            _=None,
        )

        assert response["status"] == "skipped"
        assert response["run_id"] is None
        assert response["imported_events"] == 0
        assert len(db.list_runs()) == 1


class TestRunWorker:
    def test_worker_finishes_an_existing_run(self, tmp_path, monkeypatch):
        _use_temp_db(tmp_path, monkeypatch)
        monkeypatch.setattr(pipeline, "bootstrap_subscription", lambda: {})

        def fake_body(subscription, *, use_fixture, notify, stats):
            stats.total_raw_captures = 3
            stats.total_extracted_events = 2
            stats.new_events = 1

        monkeypatch.setattr(pipeline, "_run_pipeline_body", fake_body)

        run_id = db.create_run(trigger="api", fixture=False, notify=False)
        result = pipeline.run_pipeline_for_existing_run(run_id, use_fixture=False, notify=False)

        assert result["status"] == "success"
        assert result["run_id"] == run_id
        [run] = db.list_runs()
        assert run["status"] == "success"
        assert run["finished_at"] is not None
        assert run["total_extracted_events"] == 2

    def test_worker_skips_existing_run_when_lock_is_held(self, tmp_path, monkeypatch):
        _use_temp_db(tmp_path, monkeypatch)
        run_id = db.create_run(trigger="api", fixture=False, notify=False)

        with db.try_acquire_run_lock() as acquired:
            assert acquired is True
            result = pipeline.run_pipeline_for_existing_run(run_id, use_fixture=False, notify=False)

        assert result["status"] == "skipped"
        [run] = db.list_runs()
        assert run["status"] == "skipped"
        assert run["finished_at"] is not None


class TestStaleRunReaping:
    def test_reset_stale_runs_marks_running_rows_failed(self, tmp_path, monkeypatch):
        _use_temp_db(tmp_path, monkeypatch)
        run_id = db.create_run(trigger="api", fixture=False, notify=False)
        assert db.has_active_run() is True

        reaped = db.reset_stale_runs()

        assert reaped == 1
        assert db.has_active_run() is False
        [run] = db.list_runs()
        assert run["status"] == "failed"
        assert run["finished_at"] is not None
        assert run["id"] == run_id
