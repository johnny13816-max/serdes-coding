"""Stable data boundary between external workbook readers and project mapping."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Protocol


class ProbeStatus(str, Enum):
    """Confidence assigned while identifying an external workbook format."""

    EXACT = "exact"
    COMPATIBLE = "compatible"
    AMBIGUOUS = "ambiguous"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AdhocFormatDescriptor:
    """Identity of one fixed external workbook schema."""

    format_id: str
    display_name: str
    source_family: str
    source_revision: str
    profile: str
    parser_revision: int
    required_sheets: tuple[str, ...]
    signature_keys: tuple[str, ...]
    signature_blocks: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProbeResult:
    """Result of matching a workbook against one or more known schemas."""

    status: ProbeStatus
    descriptor: Optional[AdhocFormatDescriptor]
    matched_signatures: tuple[str, ...]
    missing_signatures: tuple[str, ...]
    candidates: tuple[str, ...] = ()

    @property
    def match_ratio(self) -> float:
        total = len(self.matched_signatures) + len(self.missing_signatures)
        return 0.0 if total == 0 else len(self.matched_signatures) / total


@dataclass(frozen=True)
class AdhocSetting:
    """One value read from the source workbook without project interpretation."""

    key: str
    raw_value: Any
    evaluated_value: Any
    unit: Any
    information: Any
    section: str
    block: Optional[str]
    sheet: str
    key_cell: str
    value_cell: str

    @property
    def value(self) -> Any:
        """Return Excel's cached result when available, else the raw value."""
        return self.raw_value if self.evaluated_value is None else self.evaluated_value


@dataclass(frozen=True)
class AdhocConfigSnapshot:
    """Lossless-enough source snapshot used by mapping review and the GUI."""

    descriptor: AdhocFormatDescriptor
    source_path: Path
    source_sha256: str
    settings: tuple[AdhocSetting, ...]
    sheet_names: tuple[str, ...]

    def find_all(self, key: str, *, block: Optional[str] = None) -> tuple[AdhocSetting, ...]:
        return tuple(
            item
            for item in self.settings
            if item.key == key and (block is None or item.block == block)
        )

    def require_one(self, key: str, *, block: Optional[str] = None) -> AdhocSetting:
        matches = self.find_all(key, block=block)
        if len(matches) != 1:
            location = "" if block is None else f" in block {block!r}"
            raise KeyError(f"Expected one source setting {key!r}{location}, got {len(matches)}.")
        return matches[0]


class AdhocParser(Protocol):
    """Protocol implemented by every source-format-specific reader."""

    descriptor: AdhocFormatDescriptor

    def probe(self, workbook_path: str | Path) -> ProbeResult:
        ...

    def parse(self, workbook_path: str | Path) -> AdhocConfigSnapshot:
        ...


__all__ = [
    "AdhocConfigSnapshot",
    "AdhocFormatDescriptor",
    "AdhocParser",
    "AdhocSetting",
    "ProbeResult",
    "ProbeStatus",
]
