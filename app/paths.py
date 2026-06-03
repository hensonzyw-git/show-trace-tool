"""Shared filesystem paths with cloud-friendly environment overrides."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env_path(key: str, default: Path) -> Path:
    value = os.environ.get(key)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


DATA_DIR = _env_path("SHOW_TRACE_DATA_DIR", ROOT / "data")
DB_PATH = _env_path("SHOW_TRACE_DB_PATH", DATA_DIR / "events.db")
DIGEST_DIR = _env_path("SHOW_TRACE_DIGEST_DIR", DATA_DIR / "digests")
RAW_DIR = _env_path("SHOW_TRACE_RAW_DIR", DATA_DIR / "raw")
FIXTURE_DIR = ROOT / "data" / "fixtures"
CONFIG_PATH = _env_path("SHOW_TRACE_CONFIG_PATH", ROOT / "config.yaml")
