"""Build helpers for Vercel deployments."""

from __future__ import annotations

import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
PUBLIC_STATIC_DIR = ROOT / "public" / "static"


def main() -> None:
    PUBLIC_STATIC_DIR.mkdir(parents=True, exist_ok=True)
    if STATIC_DIR.exists():
        shutil.copytree(STATIC_DIR, PUBLIC_STATIC_DIR, dirs_exist_ok=True)


if __name__ == "__main__":
    main()
