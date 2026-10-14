"""Project-owned paths used by the Ad Hoc conversion workflow."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


_CASE_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")


def validate_case_id(value: Any) -> str:
    """Return a safe case-folder name or raise a user-facing validation error."""
    if not isinstance(value, str) or not _CASE_ID_PATTERN.fullmatch(value):
        raise ValueError(
            "Case ID must start with a letter or number and contain only letters, numbers, '.', '_' or '-'."
        )
    if value in {".", ".."}:
        raise ValueError("Case ID cannot be a relative-path component.")
    if value.endswith("."):
        raise ValueError("Case ID cannot end with a period on Windows.")
    if value.split(".", 1)[0].upper() in {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }:
        raise ValueError("Case ID cannot use a reserved Windows device name.")
    return value


def case_config_path(project_root: str | Path, case_id: Any, version: str) -> Path:
    """Resolve the canonical config.xlsx path below cases/<case_id>/<version>."""
    safe_case_id = validate_case_id(case_id)
    if version not in {"93A", "178A"}:
        raise ValueError(f"Unsupported project version: {version!r}.")
    cases_root = (Path(project_root).expanduser().resolve() / "cases").resolve()
    destination = (cases_root / safe_case_id / version / "config.xlsx").resolve()
    try:
        destination.relative_to(cases_root)
    except ValueError as error:
        raise ValueError("Resolved case config path escapes the project cases folder.") from error
    return destination


__all__ = ["case_config_path", "validate_case_id"]
