"""Validate the repository document lifecycle registry."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_REL = "docs/document_registry.md"
ACTIVE_REL = "docs/planning/active_contracts.md"
LIFECYCLES = {
    "live",
    "active-temporary",
    "paused-temporary",
    "historical-frozen",
    "migration-inventory",
    "retire-pending",
}
AUTHORITIES = {
    "rule",
    "architecture",
    "model",
    "evidence",
    "operations",
    "state",
    "working",
    "index",
}


@dataclass(frozen=True)
class Entry:
    path: str
    authority: str
    lifecycle: str
    owner: str
    update_trigger: str
    disposition: str


def _git_document_paths() -> set[str]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = set()
    for raw in result.stdout.splitlines():
        path = raw.replace("\\", "/")
        if path in {"AGENTS.md", "README.md"}:
            paths.add(path)
        elif path.startswith("docs/") and Path(path).suffix.lower() in {".md", ".xlsx"}:
            paths.add(path)
    return paths


def _parse_registry() -> tuple[dict[str, Entry], list[str]]:
    entries: dict[str, Entry] = {}
    errors: list[str] = []
    for line_number, line in enumerate((ROOT / REGISTRY_REL).read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            errors.append(f"{REGISTRY_REL}:{line_number}: expected 6 columns")
            continue
        values = [cell.removeprefix("`").removesuffix("`") for cell in cells]
        entry = Entry(*values)
        if entry.path in entries:
            errors.append(f"{REGISTRY_REL}:{line_number}: duplicate path {entry.path}")
        entries[entry.path] = entry
    return entries, errors


def validate() -> list[str]:
    entries, errors = _parse_registry()
    observed = _git_document_paths()
    registered = set(entries)

    for path in sorted(observed - registered):
        errors.append(f"unregistered document: {path}")
    for path in sorted(registered - observed):
        if entries[path].lifecycle != "retire-pending":
            errors.append(f"registry path does not exist: {path}")

    active_text = (ROOT / ACTIVE_REL).read_text(encoding="utf-8")
    active_entries = []
    for entry in entries.values():
        if entry.authority not in AUTHORITIES:
            errors.append(f"{entry.path}: invalid authority {entry.authority}")
        if entry.lifecycle not in LIFECYCLES:
            errors.append(f"{entry.path}: invalid lifecycle {entry.lifecycle}")
        if not entry.update_trigger:
            errors.append(f"{entry.path}: empty update trigger")
        if not entry.disposition:
            errors.append(f"{entry.path}: empty disposition")

        if entry.owner != "self" and entry.owner not in entries and entry.owner not in observed:
            errors.append(f"{entry.path}: missing content owner {entry.owner}")
        if entry.lifecycle == "active-temporary":
            active_entries.append(entry.path)
            active_link = Path(entry.path).relative_to(Path(ACTIVE_REL).parent).as_posix()
            if entry.path not in active_text and active_link not in active_text:
                errors.append(f"{entry.path}: active temporary contract is not linked by {ACTIVE_REL}")
        if (
            entry.lifecycle == "historical-frozen"
            and entry.authority == "working"
            and entry.owner == "self"
        ):
            errors.append(f"{entry.path}: historical working document needs a current content owner")
        if entry.lifecycle == "historical-frozen" and entry.authority == "working":
            owner_entry = entries.get(entry.owner)
            if owner_entry is not None and owner_entry.lifecycle != "live":
                errors.append(
                    f"{entry.path}: historical working document owner {entry.owner} is not live"
                )
        if entry.lifecycle == "retire-pending" and "delete" not in entry.disposition:
            errors.append(f"{entry.path}: retire-pending entry needs an explicit delete disposition")

    if len(active_entries) > 1:
        errors.append("multiple active-temporary documents: " + ", ".join(sorted(active_entries)))
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Document lifecycle validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Document lifecycle validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
