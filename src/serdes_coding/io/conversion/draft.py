"""Editable mapping draft shared by programmatic conversion and the GUI."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from ..adhoc.schema import AdhocConfigSnapshot
from .paths import validate_case_id


class MappingStatus(str, Enum):
    EXACT = "exact"
    CONVERTED = "converted"
    DERIVED = "derived"
    FALLBACK = "fallback"
    EMPTY = "empty"
    MANUAL = "manual"
    MISSING = "missing"
    UNSUPPORTED = "unsupported"
    OVERRIDE = "override"


@dataclass
class ProjectFieldDraft:
    sheet: str
    row: int
    value_column: int
    group: str
    parameter: str
    parameter_class: str
    value: Any
    unit: Any
    description: Any
    base_value: Any
    status: MappingStatus
    source_key: Optional[str] = None
    source_block: Optional[str] = None
    source_cell: Optional[str] = None
    source_value: Any = None
    note: str = ""
    original_status: Optional[MappingStatus] = None
    source_unit: Any = None
    converted_value: Any = None
    method: str = ""
    condition_key: Optional[str] = None
    condition_cell: Optional[str] = None
    condition_value: Any = None

    @property
    def identity(self) -> tuple[str, str]:
        return self.sheet, self.parameter


@dataclass
class ConversionDraft:
    source: AdhocConfigSnapshot
    target_version: str
    base_project_path: Path
    fields: list[ProjectFieldDraft]
    parser_selection: str
    detection_status: str
    package_selection: Optional[int] = None
    tx_profile: Optional[str] = None
    rx_profile: Optional[str] = None
    source_issues: list[str] = field(default_factory=list)
    changed: set[tuple[str, str]] = field(default_factory=set)

    def get(self, sheet: str, parameter: str) -> ProjectFieldDraft:
        matches = [field for field in self.fields if field.identity == (sheet, parameter)]
        if len(matches) != 1:
            raise KeyError(f"Expected one draft field {sheet}.{parameter}, got {len(matches)}.")
        return matches[0]

    def set_override(self, sheet: str, parameter: str, value: Any) -> None:
        field = self.get(sheet, parameter)
        if field.status is not MappingStatus.OVERRIDE:
            field.original_status = field.status
        field.value = value
        field.status = MappingStatus.OVERRIDE
        self.changed.add(field.identity)

    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for field in self.fields:
            counts[field.status.value] = counts.get(field.status.value, 0) + 1
        return counts

    def validation_errors(self) -> tuple[str, ...]:
        from .mapping_rules import area_for, outcome
        values = {f.identity: f.value for f in self.fields}
        errors = list(self.source_issues)
        for item in self.fields:
            area = area_for(item, self.target_version)
            if area in {"mapping", "policy", "baseline", "unregistered"}:
                if area == "unregistered" or outcome(item, self.target_version, values) == "fail":
                    errors.append(f"{item.sheet}.{item.parameter}: {item.status.value}: {item.note or 'missing/invalid value'}")
        try:
            validate_case_id(self.get("fixed_config", "case_id").value)
        except (KeyError, ValueError) as error:
            errors.append(str(error))
        from .channels import channel_errors
        errors.extend(channel_errors(self.fields))
        return tuple(dict.fromkeys(errors))



__all__ = ["ConversionDraft", "MappingStatus", "ProjectFieldDraft"]
