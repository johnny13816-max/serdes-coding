"""IEEE 802.3 Annex 93A file-backed split-search orchestration."""
from __future__ import annotations

from dataclasses import dataclass, replace
import csv
from pathlib import Path
import time
from typing import Any, Iterable, Literal, Optional, TYPE_CHECKING

from ..models.com_model_93A import (
    COM,
    COMConfig,
    COMReport,
    COMSearchCandidate,
    COMSearchConfig,
    COMSearchRow,
    COMSearchStatus,
)

if TYPE_CHECKING:
    from ..models.com_model_93A import COMStatus


MANIFEST_FIELDS = ("search_index", "c_m2", "c_m1", "c_1", "g_DC", "g_DC2")
GROUP_PLAN_FIELDS = ("group_id", "start", "stop", "candidate_count")
PARTIAL_RESULT_FIELDS = MANIFEST_FIELDS + (
    "status", "error", "FOM", "As", "sigma_ISI", "sigma_J",
    "sigma_XT", "sigma_N", "sigma_TX", "ts", "pos",
)
FINAL_RESULT_FIELDS = PARTIAL_RESULT_FIELDS + ("final_status", "final_error", "COM_dB")


@dataclass(frozen=True)
class SearchArtifacts:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", Path(self.root))

    @property
    def manifest_path(self) -> Path:
        return self.root / "full_search_manifest.csv"

    @property
    def group_plan_path(self) -> Path:
        return self.root / "group_plan.csv"

    @property
    def group_results_dir(self) -> Path:
        return self.root / "group_results"

    @property
    def merged_results_path(self) -> Path:
        return self.root / "merged_partial_results.csv"

    @property
    def final_results_path(self) -> Path:
        return self.root / "full_search_results.csv"


def create_search_plan(
    cfg: COMConfig,
    search: COMSearchConfig,
    report_dir: str | Path,
    *,
    group_size: int,
) -> SearchArtifacts:
    if group_size <= 0:
        raise ValueError("group_size must be positive.")
    artifacts = SearchArtifacts(Path(report_dir))
    artifacts.root.mkdir(parents=True, exist_ok=True)
    artifacts.group_results_dir.mkdir(parents=True, exist_ok=True)

    candidates = search.candidates(cfg.filter)
    if not candidates:
        raise ValueError("93A search candidate list is empty.")
    manifest = [_manifest_dict(idx, candidate) for idx, candidate in enumerate(candidates)]
    _write_csv(artifacts.manifest_path, MANIFEST_FIELDS, manifest)

    groups = []
    for group_id, start in enumerate(range(0, len(manifest), group_size)):
        stop = min(start + group_size, len(manifest))
        groups.append({
            "group_id": group_id,
            "start": start,
            "stop": stop,
            "candidate_count": stop - start,
        })
    _write_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS, groups)
    return artifacts


def run_partial_group(
    cfg: COMConfig,
    search: COMSearchConfig,
    report_dir: str | Path,
    group_id: int,
) -> Path:
    artifacts = SearchArtifacts(Path(report_dir))
    manifest = _read_csv(artifacts.manifest_path, MANIFEST_FIELDS)
    group = _find_group(_read_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS), group_id)
    start, stop = int(group["start"]), int(group["stop"])
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for offset, entry in enumerate(manifest[start:stop], start=1):
        idx = int(entry["search_index"])
        candidate = _candidate_from_manifest(entry)
        try:
            candidate_cfg = _config_with_candidate(cfg, candidate)
            status = COM(candidate_cfg)._run_once(calculate_pmf=False)
            row = COM._search_row_from_status(idx, candidate, status)
            rows.append(_partial_dict(row))
        except Exception as exc:
            if not search.continue_on_error:
                raise
            rows.append(_error_dict(idx, candidate, exc))
        _print_progress(offset, stop - start, started, group_id)

    output = artifacts.group_results_dir / f"group_{int(group_id):04d}.csv"
    _write_csv(output, PARTIAL_RESULT_FIELDS, rows)
    return output


def merge_partial_results(report_dir: str | Path) -> list[COMSearchRow]:
    artifacts = SearchArtifacts(Path(report_dir))
    manifest = _read_csv(artifacts.manifest_path, MANIFEST_FIELDS)
    groups = _read_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS)
    merged: list[dict[str, str]] = []
    for group in groups:
        group_id = int(group["group_id"])
        path = artifacts.group_results_dir / f"group_{group_id:04d}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing partial result for group {group_id}: {path}")
        merged.extend(_read_csv(path, PARTIAL_RESULT_FIELDS))

    expected = {int(row["search_index"]) for row in manifest}
    actual = [int(row["search_index"]) for row in merged]
    if len(actual) != len(set(actual)):
        raise ValueError("Partial results contain duplicate search_index values.")
    if set(actual) != expected:
        raise ValueError("Partial results do not cover the manifest exactly.")

    merged.sort(key=lambda row: int(row["search_index"]))
    _write_csv(artifacts.merged_results_path, PARTIAL_RESULT_FIELDS, merged)
    return [_row_from_partial(row) for row in merged]


def finalize_search(
    cfg: COMConfig,
    search: COMSearchConfig,
    report_dir: str | Path,
    *,
    include_plots: bool = True,
) -> COMSearchStatus:
    artifacts = SearchArtifacts(Path(report_dir))
    rows = merge_partial_results(artifacts.root)
    successful = sorted(
        (row for row in rows if row.status == "ok"),
        key=lambda row: row.FOM,
        reverse=True,
    )
    if not successful:
        raise RuntimeError("No successful 93A partial-search candidate is available.")

    best_row = successful[0]
    print(
        f"93A search_final: candidate={best_row.idx}, FOM={best_row.FOM:.6f} dB",
        flush=True,
    )
    best_cfg = _config_with_candidate(cfg, best_row.candidate)
    best_status = COM(best_cfg)._run_once(calculate_pmf=True)
    if best_status.pmf is None or best_status.pmf.COM is None:
        raise RuntimeError("93A final candidate did not produce PMF/COM.")

    retained = rows if search.keep_all_rows else successful[:search.keep_top_n]
    status = COMSearchStatus(
        best=best_status,
        best_row=best_row,
        rows=retained,
        num_candidates=len(rows),
        num_success=sum(row.status == "ok" for row in rows),
        num_error=sum(row.status == "error" for row in rows),
    )

    cfg.export(str(artifacts.root))
    status.export(str(artifacts.root), include_plots=False)
    best_status.export_report_summary(str(artifacts.root / "best"))
    if include_plots:
        COMReport(cfg, status).plot_search_run(str(artifacts.root / "plots"))

    final_rows = []
    for row in successful[:search.keep_top_n]:
        item = _partial_dict(row)
        item.update({
            "final_status": "ok" if row.idx == best_row.idx else "",
            "final_error": "",
            "COM_dB": best_status.pmf.COM if row.idx == best_row.idx else "",
        })
        final_rows.append(item)
    _write_csv(artifacts.final_results_path, FINAL_RESULT_FIELDS, final_rows)
    print(
        f"93A search_final: complete, best={best_row.idx}, COM={best_status.pmf.COM}",
        flush=True,
    )
    return status


def _config_with_candidate(cfg: COMConfig, candidate: COMSearchCandidate) -> COMConfig:
    return replace(
        cfg,
        filter=replace(
            cfg.filter,
            c_m2=candidate.c_m2,
            c_m1=candidate.c_m1,
            c_1=candidate.c_1,
            g_DC=candidate.g_DC,
            g_DC2=candidate.g_DC2,
        ),
    )


def _manifest_dict(idx: int, candidate: COMSearchCandidate) -> dict[str, Any]:
    return {
        "search_index": idx,
        "c_m2": candidate.c_m2,
        "c_m1": candidate.c_m1,
        "c_1": candidate.c_1,
        "g_DC": candidate.g_DC,
        "g_DC2": candidate.g_DC2,
    }


def _candidate_from_manifest(row: dict[str, str]) -> COMSearchCandidate:
    return COMSearchCandidate(
        c_m2=float(row["c_m2"]),
        c_m1=float(row["c_m1"]),
        c_1=float(row["c_1"]),
        g_DC=float(row["g_DC"]),
        g_DC2=float(row["g_DC2"]),
    )


def _partial_dict(row: COMSearchRow) -> dict[str, Any]:
    return {
        **_manifest_dict(row.idx, row.candidate),
        "status": row.status,
        "error": row.error or "",
        "FOM": row.FOM,
        "As": "" if row.As is None else row.As,
        "sigma_ISI": "" if row.sigma_ISI is None else row.sigma_ISI,
        "sigma_J": "" if row.sigma_J is None else row.sigma_J,
        "sigma_XT": "" if row.sigma_XT is None else row.sigma_XT,
        "sigma_N": "" if row.sigma_N is None else row.sigma_N,
        "sigma_TX": "" if row.sigma_TX is None else row.sigma_TX,
        "ts": "" if row.ts is None else row.ts,
        "pos": "" if row.pos is None else row.pos,
    }


def _error_dict(idx: int, candidate: COMSearchCandidate, exc: Exception) -> dict[str, Any]:
    return {
        **_manifest_dict(idx, candidate),
        "status": "error",
        "error": f"{type(exc).__name__}: {exc}",
        "FOM": float("-inf"),
        "As": "",
        "sigma_ISI": "",
        "sigma_J": "",
        "sigma_XT": "",
        "sigma_N": "",
        "sigma_TX": "",
        "ts": "",
        "pos": "",
    }


def _row_from_partial(row: dict[str, str]) -> COMSearchRow:
    def optional_float(name: str) -> Optional[float]:
        return None if row[name] == "" else float(row[name])

    def optional_int(name: str) -> Optional[int]:
        return None if row[name] == "" else int(float(row[name]))

    return COMSearchRow(
        idx=int(row["search_index"]),
        candidate=_candidate_from_manifest(row),
        FOM=float(row["FOM"]),
        As=optional_float("As"),
        sigma_ISI=optional_float("sigma_ISI"),
        sigma_J=optional_float("sigma_J"),
        sigma_XT=optional_float("sigma_XT"),
        sigma_N=optional_float("sigma_N"),
        sigma_TX=optional_float("sigma_TX"),
        ts=optional_int("ts"),
        pos=optional_int("pos"),
        status=row["status"],
        error=row["error"] or None,
    )


def _find_group(groups: list[dict[str, str]], group_id: int) -> dict[str, str]:
    matches = [row for row in groups if int(row["group_id"]) == int(group_id)]
    if len(matches) != 1:
        raise ValueError(f"group_id {group_id} does not identify exactly one group.")
    return matches[0]


def _print_progress(done: int, total: int, started: float, group_id: int) -> None:
    now = time.perf_counter()
    if done != 1 and done != total and done % 10:
        return
    elapsed = now - started
    eta = elapsed / done * (total - done) if done else 0.0
    print(
        f"93A partial group={group_id}: {done}/{total}, "
        f"elapsed={elapsed:.1f}s, eta={eta:.1f}s",
        flush=True,
    )


def _write_csv(path: Path, fields: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _read_csv(path: Path, fields: Iterable[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    required = tuple(fields)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not set(required).issubset(reader.fieldnames):
            raise ValueError(f"{path} is missing required columns: {required}")
        return list(reader)


__all__ = [
    "FINAL_RESULT_FIELDS",
    "GROUP_PLAN_FIELDS",
    "MANIFEST_FIELDS",
    "PARTIAL_RESULT_FIELDS",
    "SearchArtifacts",
    "create_search_plan",
    "finalize_search",
    "merge_partial_results",
    "run_partial_group",
]
