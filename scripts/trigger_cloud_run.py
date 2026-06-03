"""Trigger a cloud worker run through the deployed API.

Render cron jobs cannot share the web service's persistent disk, so the cron
job calls the web API and the web process runs the pipeline against its own
disk-backed SQLite database.
"""

import json
import os
import sys
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
        with urlopen(req, timeout=900) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        print(e.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 1

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"success", "partial_success"} else 1


def _env_bool(key: str, *, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


if __name__ == "__main__":
    raise SystemExit(main())
