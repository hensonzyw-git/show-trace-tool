"""Trigger a cloud worker run through the deployed API.

Render cron jobs cannot share the web service's persistent disk, so the cron
job calls the web API and the web process runs the pipeline against its own
disk-backed SQLite database.
"""

import json
import os
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def main() -> int:
    base_url = os.environ.get("SHOW_TRACE_API_BASE_URL", "").rstrip("/")
    token = os.environ.get("API_TOKEN")
    if not base_url:
        print("SHOW_TRACE_API_BASE_URL is required", file=sys.stderr)
        return 2
    if not token:
        print("API_TOKEN is required", file=sys.stderr)
        return 2

    fixture = _env_bool("SHOW_TRACE_RUN_FIXTURE", default=False)
    notify = _env_bool("SHOW_TRACE_RUN_NOTIFY", default=True)
    body = json.dumps({"fixture": fixture, "notify": notify}).encode("utf-8")
    req = Request(f"{base_url}/api/runs", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {token}")

    try:
        payload = _send_json(req)
    except HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        if e.code != 504:
            print(body_text, file=sys.stderr)
            return 1
        # Defensive fallback: the API now returns 202 immediately, so a 504 from
        # POST should be rare. We can't learn the run_id here, so poll the most
        # recent run as a best effort (see _poll_run's run_id=None branch).
        print("POST /api/runs returned 504; polling /api/runs for completion...", file=sys.stderr)
        payload = _poll_run(base_url, token)

    if payload.get("status") == "running":
        payload = _poll_run(base_url, token, run_id=payload.get("run_id") or payload.get("id"))

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"success", "partial_success"} else 1


def _send_json(req: Request) -> dict:
    with urlopen(req, timeout=900) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _poll_run(base_url: str, token: str, run_id: int | None = None) -> dict:
    timeout_seconds = int(os.environ.get("SHOW_TRACE_RUN_POLL_TIMEOUT", "900"))
    interval_seconds = int(os.environ.get("SHOW_TRACE_RUN_POLL_INTERVAL", "5"))
    deadline = time.monotonic() + timeout_seconds
    last_payload: dict | None = None

    while time.monotonic() < deadline:
        req = Request(f"{base_url}/api/runs?limit=20", method="GET")
        req.add_header("Authorization", f"Bearer {token}")
        payload = _send_json(req)
        items = payload.get("items") or []
        if run_id is not None:
            items = [item for item in items if item.get("id") == run_id]
        elif items:
            items = [items[0]]
        if items:
            last_payload = items[0]
            if last_payload.get("status") != "running":
                return last_payload
        time.sleep(interval_seconds)

    if last_payload:
        return last_payload
    return {"status": "failed", "errors": ["timed out waiting for run completion"]}


def _env_bool(key: str, *, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
