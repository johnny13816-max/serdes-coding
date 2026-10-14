"""User-facing grouping for detailed Ad Hoc conversion statuses."""

from __future__ import annotations

from typing import Any


_STATUS_GROUPS = {
    "exact": "success",
    "converted": "success",
    "derived": "success",
    "fallback": "success",
    "empty": "empty",
    "manual": "fail",
    "missing": "fail",
    "unsupported": "fail",
    "override": "success",
}


def status_group(status: Any) -> str:
    """Legacy code grouping; live GUI uses mapping_rules.outcome for value checks.

    Override is an audit attribute, not a fourth outcome. This compatibility
    helper alone cannot validate an adopted value or establish optionality.
    """
    value = getattr(status, "value", status)
    try:
        return _STATUS_GROUPS[str(value)]
    except KeyError as error:
        raise ValueError(f"Unknown conversion status: {value!r}") from error


__all__ = ["status_group"]
