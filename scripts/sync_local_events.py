"""Sync locally collected hard-source events into the cloud API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    load_dotenv(ROOT / ".env")
    args = _parse_args()
    payload = _load_payload(args.file)
    if args.notify:
        payload["notify"] = True
    if args.trigger:
        payload["trigger"] = args.trigger

    base_url = (args.api_base_url or os.environ.get("SHOW_TRACE_API_BASE_URL") or "").rstrip("/")
    token = (
        args.api_token
        or os.environ.get("SHOW_TRACE_CLOUD_API_TOKEN")
        or os.environ.get("API_TOKEN")
    )
    if not base_url:
        raise SystemExit("Missing SHOW_TRACE_API_BASE_URL or --api-base-url")
    if not token:
        raise SystemExit("Missing API_TOKEN or --api-token")

    response = requests.post(
        f"{base_url}/api/events/import",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=args.timeout,
    )
    try:
        data = response.json()
    except ValueError:
        data = {"text": response.text}
    if response.status_code >= 400:
        raise SystemExit(f"Import failed: HTTP {response.status_code} {data}")

    print(
        "Import OK: "
        f"{data['imported_events']} events, "
        f"{data['new_events']} new, "
        f"{data['updated_events']} updated, "
        f"run_id={data['run_id']}"
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload structured local events to the cloud show trace API."
    )
    parser.add_argument("file", type=Path, help="JSON file containing events or {events: [...]}")
    parser.add_argument("--api-base-url", help="Cloud API base URL, e.g. http://8.153.84.10")
    parser.add_argument("--api-token", help="Bearer token for /api/*")
    parser.add_argument("--notify", action="store_true", help="Notify after import")
    parser.add_argument("--trigger", default="local-sync", help="Run trigger label")
    parser.add_argument("--timeout", type=int, default=60, help="HTTP timeout in seconds")
    return parser.parse_args()


def _load_payload(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"events": data, "notify": False, "trigger": "local-sync"}
    if isinstance(data, dict) and isinstance(data.get("events"), list):
        return {
            "events": data["events"],
            "notify": bool(data.get("notify", False)),
            "trigger": data.get("trigger") or "local-sync",
        }
    raise SystemExit("Input JSON must be an event list or an object with an events list")


if __name__ == "__main__":
    main()
