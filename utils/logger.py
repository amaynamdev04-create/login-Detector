"""Logging configuration helpers."""

from __future__ import annotations

import logging
from pathlib import Path


def configure_logging(app) -> None:
    """Configure application logging."""
    log_dir = Path(app.root_path) / "exports"
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "application.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
