"""General helper utilities."""

from __future__ import annotations

from pathlib import Path


def read_lines(path: Path) -> list[str]:
    """Read non-empty lines from a file."""
    with path.open("r", encoding="utf-8") as handle:
        return [line.rstrip("\n") for line in handle if line.strip()]


def parse_csv_list(raw_value: str) -> list[str]:
    """Convert comma-separated user input into a cleaned list."""
    return [item.strip() for item in raw_value.split(",") if item.strip()]
