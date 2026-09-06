"""IEEE 802.3 Annex 178A split-search orchestration.

This module owns manifest/group/result files and outer-search execution.  The
spec-defined 178A single-candidate pipeline remains in ``com_model_178A``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import csv
from pathlib import Path
import time
from typing import Any, Iterable, Literal, Optional, TYPE_CHECKING

import numpy as np

from ..models import com_model_93A as com_93A

if TYPE_CHECKING:
    from ..models.com_model_178A import COMConfig, COMStatus


_PrettyDataclass = com_93A._PrettyDataclass
COMReport = com_93A.COMReport
COMSearchCandidate = com_93A.COMSearchCandidate
COMSearchConfig = com_93A.COMSearchConfig


MANIFEST_FIELDS = ("search_index", "c_m2", "c_m1", "c_1", "g_1", "g_2")
GROUP_PLAN_FIELDS = ("group_id", "start", "stop", "candidate_count")
PARTIAL_RESULT_FIELDS = (
    "search_index", "c_m2", "c_m1", "c_1", "g_1", "g_2",
    "status", "error", "mse", "mse_dB", "ts", "pos",
)
FINAL_RESULT_FIELDS = PARTIAL_RESULT_FIELDS + ("final_status", "final_error", "COM_dB")
PARTIAL_RESULT_REPORT_MULTIPLIER = 10


@dataclass(repr=False)
class COMSearchRow(_PrettyDataclass):
    """One 178A TXFFE/CTLE candidate, ranked by its minimum DTE MSE."""

    idx: int
    candidate: COMSearchCandidate
    mse: float                       # unit: V^2, minimum valid MSE over pos
    ts: Optional[int] = None         # unit: sample index
    pos: Optional[int] = None        # unit: sample phase
    status: Literal["ok", "infeasible", "error"] = "ok"
    error: Optional[str] = None


@dataclass(repr=False)
class COMSearchStatus(_PrettyDataclass):
    """Merged 178A search result; selected candidate minimizes DTE MSE."""

    best: Any
    best_row: COMSearchRow
    rows: list[COMSearchRow]
    num_candidates: int
    num_success: int
    num_infeasible: int
    num_error: int

    @property
    def COM(self) -> Optional[float]:
        return None if self.best.pmf is None else self.best.pmf.COM

    def plot_mse_trace(self, save_path: str = "") -> Any:
        """Plot the minimum DTE MSE of each retained search candidate."""
        ok_rows = [row for row in self.rows if row.status == "ok"]
        if not ok_rows:
            raise ValueError("COMSearchStatus.rows contains no successful rows.")
        output_file = COMReport._plot_save_path(save_path, "search_mse_trace.png")
        fig, ax = COMReport._subplots(output_file)
        ax.plot([row.idx for row in ok_rows], [row.mse for row in ok_rows], marker="o", linewidth=1.0)
        ax.axhline(self.best_row.mse, linestyle="--", color="tab:red", label=f"best MSE={self.best_row.mse:.3e} V^2")
        ax.set_title("Search Minimum DTE MSE")
        ax.set_xlabel("Candidate index")
        ax.set_ylabel("MSE (V^2)")
        ax.grid(True)
        ax.legend()
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_top_candidates(self, save_path: str = "", top_n: int = 10) -> Any:
        """Plot the lowest-MSE search candidates."""
        ok_rows = [row for row in self.rows if row.status == "ok"]
        if not ok_rows:
            raise ValueError("COMSearchStatus.rows contains no successful rows.")
        if top_n <= 0:
            raise ValueError("top_n must be positive.")
        rows = sorted(ok_rows, key=lambda row: row.mse)[:int(top_n)]
        labels = [f"{row.idx}\n({row.candidate.g_DC:.1f},{row.candidate.g_DC2:.1f})" for row in rows]
        output_file = COMReport._plot_save_path(save_path, "search_top_candidates.png")
        fig, ax = COMReport._subplots(output_file, figsize=(max(7, 0.7 * len(rows)), 4))
        ax.bar(np.arange(len(rows)), [row.mse for row in rows])
        ax.set_xticks(np.arange(len(rows)))
        ax.set_xticklabels(labels)
        ax.set_title("Lowest-MSE Search Candidates")
        ax.set_xlabel("Candidate idx\n(g_1, g_2)")
        ax.set_ylabel("MSE (V^2)")
        ax.grid(True, axis="y")
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_summary(self, save_path: str = "") -> dict[str, Any]:
        """Plot 178A MSE-search summaries and the selected candidate status."""
        best_path = "" if not save_path else str(Path(save_path) / "best")
        return {
            "search_mse_trace": self.plot_mse_trace(save_path),
            "search_top_candidates": self.plot_top_candidates(save_path),
            "best": self.best.plot_summary(best_path),
        }

    def export(self, save_path: str, *, include_plots: bool = True) -> dict[str, str]:
        """Export MSE-ranked rows and the selected final candidate status."""
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = out_dir / "search_summary.json"
        self._write_json(summary_path, {
            "type": type(self).__name__,
            "num_candidates": self.num_candidates,
            "num_success": self.num_success,
            "num_infeasible": self.num_infeasible,
            "num_error": self.num_error,
            "COM": self._json_scalar(self.COM),
            "best_row_idx": self.best_row.idx,
            "best_row_mse": self._json_scalar(self.best_row.mse),
            "rows": [_row_to_dict(row) for row in self.rows],
        })
        best_outputs = self.best.export(str(out_dir / "best"), include_plots=include_plots)
        outputs = {"search_summary": str(summary_path), "best_arrays": best_outputs["arrays"]}
        if include_plots:
            self.plot_summary(str(out_dir / "plots"))
            outputs["plots"] = str(out_dir / "plots")
        return outputs


@dataclass(frozen=True)
class SearchArtifacts:
    """Stable filesystem locations for one case's 178A split search."""

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
    def top_k_dir(self) -> Path:
        return self.root / "top_K"

    @property
    def final_results_path(self) -> Path:
        return self.root / "full_search_results.csv"


def create_search_plan(
    cfg: "COMConfig",
    search: COMSearchConfig,
    report_dir: str | Path,
    *,
    candidate_limit: Optional[int] = None,
) -> SearchArtifacts:
    """Write the candidate manifest and contiguous partial-search group plan."""
    artifacts = SearchArtifacts(Path(report_dir))
    artifacts.root.mkdir(parents=True, exist_ok=True)
    artifacts.group_results_dir.mkdir(parents=True, exist_ok=True)

    candidates = search.candidates(cfg.filter)
    if candidate_limit is not None:
        if candidate_limit <= 0:
            raise ValueError("candidate_limit must be positive when specified.")
        candidates = candidates[:candidate_limit]
    if not candidates:
        raise ValueError("178A search candidate list is empty.")
    manifest = [_manifest_dict(idx, candidate) for idx, candidate in enumerate(candidates)]
    _write_csv(artifacts.manifest_path, MANIFEST_FIELDS, manifest)

    group_size = cfg.execution.search_group_size
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
    cfg: "COMConfig",
    search: COMSearchConfig,
    report_dir: str | Path,
    group_id: int,
) -> Path:
    """Evaluate one planned candidate interval using the `search_sweep` profile."""
    artifacts = SearchArtifacts(Path(report_dir))
    manifest = _read_csv(artifacts.manifest_path, MANIFEST_FIELDS)
    group = _find_group(_read_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS), group_id)
    start, stop = int(group["start"]), int(group["stop"])
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()

    for offset, entry in enumerate(manifest[start:stop], start=1):
        search_index = int(entry["search_index"])
        candidate = _candidate_from_manifest(entry)
        try:
            from ..models.com_model_178A import COM, COMTxfirMainCursorError

            candidate_cfg = _config_with_candidate(cfg, candidate)
            status = COM(candidate_cfg)._run_once(
                run_cfg=candidate_cfg.execution.search_sweep,
            )
            rows.append(_partial_row_from_status(search_index, candidate, status))
        except COMTxfirMainCursorError as exc:
            rows.append(_partial_infeasible_row(search_index, candidate, exc))
        except Exception as exc:
            if not search.continue_on_error:
                raise
            rows.append(_partial_error_row(search_index, candidate, exc))

        _print_progress("178A partial search", offset, stop - start, started, group_id)

    output_path = artifacts.group_results_dir / f"group_{int(group_id):03d}.csv"
    _write_csv(output_path, PARTIAL_RESULT_FIELDS, rows)
    return output_path


def merge_partial_results(report_dir: str | Path) -> list[COMSearchRow]:
    """Validate and merge all planned partial CSV files into one MSE-sorted source."""
    artifacts = SearchArtifacts(Path(report_dir))
    manifest = _read_csv(artifacts.manifest_path, MANIFEST_FIELDS)
    groups = _read_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS)
    merged: list[dict[str, Any]] = []
    for group in groups:
        group_id = int(group["group_id"])
        path = artifacts.group_results_dir / f"group_{group_id:03d}.csv"
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
    return [_search_row_from_partial(row) for row in merged]


def finalize_search(
    cfg: "COMConfig",
    search: COMSearchConfig,
    report_dir: str | Path,
    *,
    include_plots: bool = True,
) -> COMSearchStatus:
    """Re-run top-K candidates and export a wider partial-result ranking.

    ``search_top_k`` controls the expensive full COM reruns.  The CSV keeps
    ten times that many successful partial-search rows for diagnosis; rows
    beyond top-K have blank final-status and COM columns by design.
    """
    artifacts = SearchArtifacts(Path(report_dir))
    partial_rows = merge_partial_results(artifacts.root)
    successful = sorted(
        (row for row in partial_rows if row.status == "ok"),
        key=lambda row: row.mse,
    )
    if not successful:
        raise RuntimeError("No successful partial-search candidate is available for finalization.")

    artifacts.top_k_dir.mkdir(parents=True, exist_ok=True)
    full_com_rows = successful[:cfg.execution.search_top_k]
    report_limit = PARTIAL_RESULT_REPORT_MULTIPLIER * cfg.execution.search_top_k
    report_rows = successful[:report_limit]
    final_rows_by_idx = {
        row.idx: _final_row(row, status="")
        for row in report_rows
    }
    finalized: list[tuple[COMSearchRow, Any]] = []
    for row in full_com_rows:
        candidate_cfg = _config_with_candidate(cfg, row.candidate)
        try:
            from ..models.com_model_178A import COM

            status = COM(candidate_cfg)._run_once(
                run_cfg=candidate_cfg.execution.search_final,
            )
            # 178A plotting is owned by COMReport178A, which needs the
            # originating runtime/project config in addition to COMStatus.
            status._config_for_report = candidate_cfg
            status.export(
                str(artifacts.top_k_dir / f"{row.idx:06d}"),
                include_plots=include_plots,
            )
            finalized.append((row, status))
            final_rows_by_idx[row.idx] = _final_row(
                row,
                status="ok",
                com_value=status.pmf.COM if status.pmf else None,
            )
        except Exception as exc:
            # Finalization is an aggregation stage: preserve one candidate's
            # failure and continue so the remaining top-K candidates can be
            # evaluated and reported.
            final_rows_by_idx[row.idx] = (
                _final_row(
                    row,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

    final_rows = [final_rows_by_idx[row.idx] for row in report_rows]
    _write_csv(artifacts.final_results_path, FINAL_RESULT_FIELDS, final_rows)
    if not finalized:
        raise RuntimeError(
            "All top-K final candidates failed; see full_search_results.csv for details."
        )

    best_row, best_status = min(finalized, key=lambda item: item[0].mse)
    retained = _select_rows(partial_rows, search)
    return COMSearchStatus(
        best=best_status,
        best_row=best_row,
        rows=retained,
        num_candidates=len(partial_rows),
        num_success=sum(row.status == "ok" for row in partial_rows),
        num_infeasible=sum(row.status == "infeasible" for row in partial_rows),
        num_error=sum(row.status == "error" for row in partial_rows),
    )


def run_full_search(
    cfg: "COMConfig",
    search: COMSearchConfig,
    report_dir: str | Path,
    *,
    include_plots: bool = True,
) -> COMSearchStatus:
    """Execute manifest creation, every partial group, merge, and top-K finalization."""
    artifacts = create_search_plan(cfg, search, report_dir)
    for group in _read_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS):
        run_partial_group(cfg, search, artifacts.root, int(group["group_id"]))
    return finalize_search(cfg, search, artifacts.root, include_plots=include_plots)


def _config_with_candidate(cfg: "COMConfig", candidate: COMSearchCandidate) -> "COMConfig":
    """Apply shared candidate fields to the 178A two-gain CTF configuration."""
    filter_cfg = replace(
        cfg.filter,
        c_m2=candidate.c_m2,
        c_m1=candidate.c_m1,
        c_1=candidate.c_1,
        g_1=candidate.g_DC,
        g_2=candidate.g_DC2,
    )
    return replace(cfg, filter=filter_cfg)


def _manifest_dict(idx: int, candidate: COMSearchCandidate) -> dict[str, Any]:
    return {
        "search_index": idx,
        "c_m2": candidate.c_m2,
        "c_m1": candidate.c_m1,
        "c_1": candidate.c_1,
        "g_1": candidate.g_DC,
        "g_2": candidate.g_DC2,
    }


def _candidate_from_manifest(row: dict[str, str]) -> COMSearchCandidate:
    return COMSearchCandidate(
        c_m2=float(row["c_m2"]),
        c_m1=float(row["c_m1"]),
        c_1=float(row["c_1"]),
        g_DC=float(row["g_1"]),
        g_DC2=float(row["g_2"]),
    )


def _partial_row_from_status(idx: int, candidate: COMSearchCandidate, status: Any) -> dict[str, Any]:
    if status.dfe is None:
        raise RuntimeError("search_sweep target must return COMDTEStatus with MSE.")
    mse = float(status.dfe.mse)
    return {
        **_manifest_dict(idx, candidate),
        "status": "ok",
        "error": "",
        "mse": mse,
        "mse_dB": 10.0 * np.log10(mse) if mse > 0.0 else float("-inf"),
        "ts": int(status.dfe.ts),
        "pos": int(status.dfe.pos),
    }


def _partial_error_row(idx: int, candidate: COMSearchCandidate, error: Exception) -> dict[str, Any]:
    return {
        **_manifest_dict(idx, candidate),
        "status": "error",
        "error": str(error),
        "mse": float("inf"),
        "mse_dB": float("inf"),
        "ts": "",
        "pos": "",
    }


def _partial_infeasible_row(idx: int, candidate: COMSearchCandidate, error: Exception) -> dict[str, Any]:
    """Record a structurally invalid TX FFE candidate without aborting the search."""
    return {
        **_manifest_dict(idx, candidate),
        "status": "infeasible",
        "error": str(error),
        "mse": float("inf"),
        "mse_dB": float("inf"),
        "ts": "",
        "pos": "",
    }


def _search_row_from_partial(row: dict[str, str]) -> COMSearchRow:
    return COMSearchRow(
        idx=int(row["search_index"]),
        candidate=_candidate_from_manifest(row),
        mse=float(row["mse"]),
        ts=_optional_int(row["ts"]),
        pos=_optional_int(row["pos"]),
        status=row["status"],
        error=row["error"] or None,
    )


def _row_to_dict(row: COMSearchRow) -> dict[str, Any]:
    return {
        "idx": row.idx,
        "status": row.status,
        "error": row.error,
        "mse": row.mse,
        "ts": row.ts,
        "pos": row.pos,
        "candidate": {
            "c_m2": row.candidate.c_m2,
            "c_m1": row.candidate.c_m1,
            "c_1": row.candidate.c_1,
            "g_1": row.candidate.g_DC,
            "g_2": row.candidate.g_DC2,
        },
    }


def _final_row(
    row: COMSearchRow,
    *,
    status: Literal["", "ok", "error"],
    com_value: Optional[float] = None,
    error: str = "",
) -> dict[str, Any]:
    partial = _partial_row_dict(row)
    return {
        **partial,
        "final_status": status,
        "final_error": error,
        "COM_dB": "" if com_value is None else com_value,
    }


def _partial_row_dict(row: COMSearchRow) -> dict[str, Any]:
    return {
        **_manifest_dict(row.idx, row.candidate),
        "status": row.status,
        "error": row.error or "",
        "mse": row.mse,
        "mse_dB": 10.0 * np.log10(row.mse) if row.mse > 0.0 and np.isfinite(row.mse) else row.mse,
        "ts": "" if row.ts is None else row.ts,
        "pos": "" if row.pos is None else row.pos,
    }


def _select_rows(rows: list[COMSearchRow], search: COMSearchConfig) -> list[COMSearchRow]:
    if search.keep_all_rows:
        return rows
    return sorted((row for row in rows if row.status == "ok"), key=lambda row: row.mse)[:search.keep_top_n]


def _find_group(groups: Iterable[dict[str, str]], group_id: int) -> dict[str, str]:
    for group in groups:
        if int(group["group_id"]) == int(group_id):
            return group
    raise ValueError(f"Unknown group_id: {group_id}")


def _read_csv(path: Path, required_fields: Iterable[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fields = tuple(reader.fieldnames or ())
        missing = [field for field in required_fields if field not in fields]
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(missing)}")
        return list(reader)


def _write_csv(path: Path, fields: Iterable[str], rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(fields)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _optional_int(value: str) -> Optional[int]:
    return None if value == "" else int(value)


def _print_progress(label: str, done: int, total: int, started: float, group_id: int) -> None:
    if done != 1 and done != total and done % 10 != 0:
        return
    elapsed = time.perf_counter() - started
    rate = done / elapsed if elapsed > 0.0 else float("nan")
    eta = (total - done) / rate if np.isfinite(rate) and rate > 0.0 else float("nan")
    print(
        f"{label} group={group_id}: {done}/{total} "
        f"({100.0 * done / total:.1f}%), elapsed={elapsed:.1f}s, eta={eta:.1f}s"
    )


__all__ = [
    "COMSearchRow",
    "COMSearchStatus",
    "SearchArtifacts",
    "create_search_plan",
    "run_partial_group",
    "merge_partial_results",
    "finalize_search",
    "run_full_search",
]
