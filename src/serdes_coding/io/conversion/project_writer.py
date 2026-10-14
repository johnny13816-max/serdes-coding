"""Write an approved conversion draft into the fixed project workbook format."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

from openpyxl import load_workbook

from .draft import ConversionDraft


def write_project_config(
    draft: ConversionDraft,
    output_path: str | Path,
    *,
    allow_unreviewed: bool = False,
) -> Path:
    """Copy the base workbook and replace only its declared value cells."""
    if allow_unreviewed:
        raise ValueError('Unreviewed export is no longer supported; resolve validation errors first.')
    errors = draft.validation_errors()
    if errors:
        raise ValueError("Cannot export invalid mapping:\n- " + "\n- ".join(errors))

    destination = Path(output_path).expanduser().resolve()
    if destination.name != 'config.xlsx' or destination.parent.name != draft.target_version or destination.parent.parent.name != draft.get('fixed_config','case_id').value or destination.parent.parent.parent.name!='cases':
        raise ValueError('Destination must be cases/<case_id>/<version>/config.xlsx')
    from .existing_project import ExistingProjectDraft, validate_existing_project, _write_values
    check = ExistingProjectDraft(draft.base_project_path, draft.target_version,
                                 draft.get('fixed_config','case_id').value, draft.fields)
    errors = validate_existing_project(check, destination)
    if errors:
        raise ValueError('Runtime validation failed:\n'+'\n'.join(errors))
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.config_',suffix='.xlsx',dir=destination.parent)
    os.close(fd)
    temporary=Path(name)
    try:
        _write_values(draft.base_project_path, temporary, draft.fields)
        os.replace(temporary,destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def write_conversion_audit(draft: ConversionDraft, workbook_path: str | Path) -> tuple[Path, Path]:
    """Write provenance and field-level mapping records beside an export."""
    workbook_path = Path(workbook_path).expanduser().resolve()
    json_path = workbook_path.with_suffix(".conversion.json")
    csv_path = workbook_path.with_suffix(".mapping.csv")
    metadata = {
        "source_id": draft.source.source_path.parent.name,
        "format_id": draft.source.descriptor.format_id,
        "display_name": draft.source.descriptor.display_name,
        "parser_revision": draft.source.descriptor.parser_revision,
        "parser_selection": draft.parser_selection,
        "detection_status": draft.detection_status,
        "source_path": str(draft.source.source_path),
        "source_sha256": draft.source.source_sha256,
        "target_version": draft.target_version,
        "base_project_path": str(draft.base_project_path),
        "output_path": str(workbook_path),
        "status_counts": draft.status_counts(),
        "package_selection": draft.package_selection,
        "tx_profile": draft.tx_profile,
        "rx_profile": draft.rx_profile,
        "source_issues": draft.source_issues,
    }
    json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    columns = (
        "sheet", "group", "parameter", "parameter_class", "status", "original_status", "value", "unit",
        "source_key", "source_block", "source_cell", "source_value", "base_value", "note",
        "source_unit", "converted_value", "method", "condition_key", "condition_cell",
        "condition_value",
    )
    with csv_path.open("w", newline="", encoding="utf-8-sig") as target:
        writer = csv.DictWriter(target, fieldnames=columns)
        writer.writeheader()
        for field in draft.fields:
            writer.writerow({name: getattr(getattr(field,name),'value',getattr(field,name)) for name in columns})
    return json_path, csv_path


__all__ = ["write_conversion_audit", "write_project_config"]
