"""Shared environment bootstrap for scripts that hit external services.

Import this before any requests/urllib call:

    import _env  # noqa: F401  (loads .env from the repo root)
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # WSL system Python may not have python-dotenv installed.
    load_dotenv = None


def _load_plain_env(path: Path) -> None:
    """Load KEY=value lines when python-dotenv is not installed. Does not override."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
if load_dotenv is not None:
    load_dotenv(_ENV_FILE)
else:
    _load_plain_env(_ENV_FILE)


def resolve_existing_path(*candidates: Path) -> Path:
    """Return the first candidate path that exists, else the first candidate.

    Used for data that lives outside the repo on a path that differs between
    native Windows and WSL (e.g. a mapped network/external drive).
    """
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def windows_drive_to_wsl(windows_path: str) -> Path:
    """Translate a 'G:\\...' style path to its WSL mount, e.g. /mnt/g/...."""
    drive, _, rest = windows_path.partition(":")
    rest = rest.replace("\\", "/").lstrip("/")
    return Path(f"/mnt/{drive.lower()}/{rest}")
