"""Shared naming for persisted workstation-script reports."""

from __future__ import annotations

import getpass
import re
from datetime import datetime


def filename_component(value: str) -> str:
    """Return one portable filename component derived from a display value."""
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip(".-") or "unknown"


def report_filename(
    command: str,
    format_: str,
    machine: str,
    user: str | None = None,
    timestamp: datetime | None = None,
) -> str:
    """Name a report by command, machine, user, local timestamp, and format."""
    extension = {"json": "json", "csv": "csv"}.get(format_, "md")
    current = timestamp or datetime.now().astimezone()
    return (
        f"{filename_component(command)}-{filename_component(machine)}-"
        f"{filename_component(user or getpass.getuser())}-"
        f"{current:%Y%m%dT%H%M%S%z}.{extension}"
    )
