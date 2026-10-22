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
from ..models.com_dataclass_text import COMDataclassText, TextField, TextSection
from ..utilities.link import GridOverflowError
if TYPE_CHECKING:
    from ..models.com_model_178A import COMConfig, COMStatus


COMSearchCandidate = com_93A.COMSearchCandidate
COMSearchConfig = com_93A.COMSearchConfig


MANIFEST_FIELDS = ("search_index", "c_m2", "c_m1", "c_1", "g_1", "g_2")
GROUP_PLAN_FIELDS = ("group_id", "start", "stop", "candidate_count")
PARTIAL_RESULT_FIELDS = (
    "search_index", "c_m2", "c_m1", "c_1", "g_1", "g_2",
    "status", "error", "mse", "mse_dB", "ts", "pos",
)
FINAL_RESULT_FIELDS = PARTIAL_RESULT_FIELDS + (
    "final_status",
    "final_error",
    "grid_length",
    "full_length",
    "tail_peak_ratio",
    "tail_energy_ratio",
    "COM_DFE_dB",
    "COM_dB",
    "post_ffe_As_V",
    "post_ffe_sigma_ISI_V",
    "post_ffe_sigma_tn_V",
    "post_ffe_sigma_rn_V",
    "post_ffe_sigma_xn_V",
    "post_ffe_sigma_jn_V",
    "post_ffe_sigma_qn_V",
    "post_ffe_sigma_total_V",
)
PARTIAL_RESULT_REPORT_MULTIPLIER = 10


@dataclass(repr=False)
class COMSearchRow(COMDataclassText):
    """One 178A TXFFE/CTLE candidate, ranked by its minimum DTE MSE."""

    idx: int
    candidate: COMSearchCandidate
    mse: float                       # unit: V^2, minimum valid MSE over pos
    ts: Optional[int] = None         # unit: sample index
    pos: Optional[int] = None        # unit: sample phase
    status: Literal["ok", "infeasible", "error"] = "ok"
    error: Optional[str] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        candidate = None if self.candidate is None else (
            f"c_m2={self.candidate.c_m2:.9g}, c_m1={self.candidate.c_m1:.9g}, "
            f"c_1={self.candidate.c_1:.9g}, g_1={self.candidate.g_DC:.9g} dB, "
            f"g_2={self.candidate.g_DC2:.9g} dB"
        )
        return (
            TextSection("Candidate", (
                self._field("idx", "search index", stored_unit="candidate index"),
                TextField("candidate", "TX FFE and CTLE candidate", candidate, "configuration"),
                self._field("status", "execution status", stored_unit="status"),
                self._field("error", "error", stored_unit="status"),
            )),
            TextSection("Ranking result", (
                self._field("mse", "minimum MSE", stored_unit="V^2", display_unit="mV^2", scale=1e6),
                self._field("ts", "main cursor location", stored_unit="sample index"),
                self._field("pos", "sampling phase", stored_unit="sample index"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("idx", "search index", stored_unit="candidate index"),
            self._field("mse", "minimum MSE", stored_unit="V^2"),
            self._field("status", "execution status", stored_unit="status"),
        )


@dataclass(repr=False)
class COMSearchStatus(COMDataclassText):
    """Merged 178A search result; selected candidate minimizes DTE MSE."""

    best: Any
    best_row: COMSearchRow
    rows: list[COMSearchRow]
    num_candidates: int
    num_success: int
    num_infeasible: int
    num_error: int
    num_grid_overflow: int = 0

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Search totals", (
                self._field("num_candidates", "candidates", stored_unit="candidate count"),
                self._field("num_success", "successful candidates", stored_unit="candidate count"),
                self._field("num_infeasible", "infeasible candidates", stored_unit="candidate count"),
                self._field("num_error", "error candidates", stored_unit="candidate count"),
                self._field("num_grid_overflow", "grid-overflow candidates", stored_unit="candidate count"),
                self._field("rows", "candidate rows", stored_unit="record count", summary="count"),
            )),
            TextSection("Selected candidate", (
                self._field("best_row", "best ranking row", stored_unit="status"),
                self._field("best", "best full COM status", stored_unit="status", summary="stage"),
                TextField("COM", "final COM", self.COM, "dB"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("num_candidates", "candidates", stored_unit="candidate count"),
            self._field("num_success", "successful candidates", stored_unit="candidate count"),
            TextField("COM", "final COM", self.COM, "dB"),
        )

    @property
    def COM(self) -> Optional[float]:
        return self.best.final_COM




    def export(self, save_path: str) -> dict[str, str]:
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
            "num_grid_overflow": self.num_grid_overflow,
            "COM": self._json_scalar(self.COM),
            "best_row_idx": self.best_row.idx,
            "best_row_mse": self._json_scalar(self.best_row.mse),
            "rows": [_row_to_dict(row) for row in self.rows],
        })
        best_outputs = self.best.export(str(out_dir / "best"))
        return {
            "search_summary": str(summary_path),
            "best_status_summary": best_outputs["status_summary_txt"],
        }


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
    signal_amplitude = _signal_amplitude(cfg)

    for offset, entry in enumerate(manifest[start:stop], start=1):
        search_index = int(entry["search_index"])
        candidate = _candidate_from_manifest(entry)
        try:
            from ..models.com_model_178A import COM, COMTxfirMainCursorError

            candidate_cfg = _config_with_candidate(cfg, candidate)
            status = COM(candidate_cfg)._run_once(
                run_cfg=candidate_cfg.execution.search_sweep,
            )
            rows.append(_partial_row_from_status(
                search_index, candidate, status, signal_amplitude=signal_amplitude
            ))
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
    report_limit = PARTIAL_RESULT_REPORT_MULTIPLIER * cfg.execution.search_top_k
    report_rows = successful[:report_limit]
    signal_amplitude = _signal_amplitude(cfg)
    final_rows_by_idx = {
        row.idx: _final_row(row, status="", signal_amplitude=signal_amplitude)
        for row in report_rows
    }
    finalized: list[tuple[COMSearchRow, Any]] = []
    grid_overflow_count = 0
    generic_error_count = 0
    attempted_count = 0
    final_started = time.perf_counter()
    target_final = min(cfg.execution.search_top_k, len(successful))
    print(f"178A search_final: start, target={target_final} valid candidates, include_plots={include_plots}", flush=True)
    for row in successful:
        if len(finalized) >= target_final:
            break
        attempted_count += 1
        candidate_started = time.perf_counter()
        label = f"178A search_final attempt={attempted_count} valid={len(finalized)}/{target_final} candidate={row.idx}"
        stage = "calculation"
        print(f"{label}: calculation start", flush=True)
        candidate_cfg = _config_with_candidate(cfg, row.candidate)
        try:
            from ..models.com_model_178A import COM

            status = COM(candidate_cfg)._run_once(
                run_cfg=candidate_cfg.execution.search_final,
            )
            print(f"{label}: calculation done in {time.perf_counter() - candidate_started:.1f}s", flush=True)
            stage = "report export"
            print(f"{label}: report export start, include_plots={include_plots}", flush=True)
            candidate_dir = artifacts.top_k_dir / f"{row.idx:06d}"
            status.export(str(candidate_dir))
            if include_plots:
                from serdes_coding.reporting.com_report_178A import COMReport178A

                COMReport178A(candidate_cfg, status).export_single_run(candidate_dir)
            print(f"{label}: report export done", flush=True)
            finalized.append((row, status))
            final_rows_by_idx[row.idx] = _final_row(
                row,
                status="ok",
                run_status=status,
                signal_amplitude=signal_amplitude,
            )
        except GridOverflowError as exc:
            grid_overflow_count += 1
            print(f"{label}: WARNING {exc}", flush=True)
            final_rows_by_idx[row.idx] = _final_row(
                row,
                status="grid_overflow",
                error=str(exc),
                overflow=exc,
                signal_amplitude=signal_amplitude,
            )
        except Exception as exc:
            generic_error_count += 1
            print(f"{label}: ERROR during {stage}: {type(exc).__name__}: {exc}", flush=True)
            # Finalization is an aggregation stage: preserve one candidate's
            # failure and continue so the remaining top-K candidates can be
            # evaluated and reported.
            final_rows_by_idx[row.idx] = (
                _final_row(
                    row,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                    signal_amplitude=signal_amplitude,
                )
            )

        print(
            f"{label}: {final_rows_by_idx[row.idx]['final_status']}, "
            f"candidate_elapsed={time.perf_counter() - candidate_started:.1f}s, "
            f"elapsed={time.perf_counter() - final_started:.1f}s", flush=True,
        )

    print("178A search_final: writing full_search_results.csv", flush=True)
    final_rows = [final_rows_by_idx[row.idx] for row in successful[:max(report_limit, attempted_count)]]
    _write_csv(artifacts.final_results_path, FINAL_RESULT_FIELDS, final_rows)
    if generic_error_count:
        raise RuntimeError(
            f"{generic_error_count} final candidates failed for non-grid reasons; "
            "see full_search_results.csv. Partial outputs have been preserved."
        )
    if not finalized:
        raise RuntimeError(
            "No final candidate fits the fixed grid; see full_search_results.csv "
            "and reduce target_df before rerunning from the source inputs."
        )

    print(
        f"178A search_final: complete, valid={len(finalized)}/{target_final}, "
        f"grid_overflow={grid_overflow_count}, "
        f"elapsed={time.perf_counter() - final_started:.1f}s", flush=True,
    )
    best_row, best_status = min(finalized, key=lambda item: item[0].mse)
    retained = _select_rows(partial_rows, search)
    search_status = COMSearchStatus(
        best=best_status,
        best_row=best_row,
        rows=retained,
        num_candidates=len(partial_rows),
        num_success=sum(row.status == "ok" for row in partial_rows),
        num_infeasible=sum(row.status == "infeasible" for row in partial_rows),
        num_error=sum(row.status == "error" for row in partial_rows),
        num_grid_overflow=grid_overflow_count,
    )
    cfg.export(str(artifacts.root))
    search_status.export(str(artifacts.root))
    if include_plots:
        from serdes_coding.reporting.com_report_178A import COMReport178A

        best_cfg = _config_with_candidate(cfg, best_row.candidate)
        COMReport178A(best_cfg, search_status).export_search_run(artifacts.root)
    return search_status


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


def _signal_amplitude(cfg: "COMConfig") -> float:
    """Return the 178A signal amplitude used to normalize DTE MSE."""
    L = int(cfg.L)
    if L <= 1:
        raise ValueError("COMConfig.L must be greater than 1 to define A_s.")
    amplitude = float(cfg.imp.R_LM) / (L - 1)
    if not np.isfinite(amplitude) or amplitude <= 0.0:
        raise ValueError("A_s = R_LM/(L-1) must be finite and positive.")
    return amplitude


def _mse_db(mse: float, signal_amplitude: float) -> float:
    """Return normalized MSE in dB: 10*log10(A_s^2 / MSE)."""
    if not np.isfinite(mse):
        return float("inf")
    if mse <= 0.0:
        return float("inf")
    return 10.0 * np.log10((signal_amplitude * signal_amplitude) / mse)


def _partial_row_from_status(
    idx: int,
    candidate: COMSearchCandidate,
    status: Any,
    *,
    signal_amplitude: float,
) -> dict[str, Any]:
    if status.dte is None:
        raise RuntimeError("search_sweep target must return COMDTEStatus with MSE.")
    mse = float(status.dte.mse)
    return {
        **_manifest_dict(idx, candidate),
        "status": "ok",
        "error": "",
        "mse": mse,
        "mse_dB": _mse_db(mse, signal_amplitude),
        "ts": int(status.dte.ts),
        "pos": int(status.dte.pos),
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
    status: Literal["", "ok", "error", "grid_overflow"],
    run_status: Optional[Any] = None,
    error: str = "",
    overflow: Optional[Any] = None,
    signal_amplitude: float,
) -> dict[str, Any]:
    partial = _partial_row_dict(row, signal_amplitude=signal_amplitude)
    metrics: dict[str, Any] = {
        "COM_DFE_dB": "",
        "COM_dB": "",
        "post_ffe_As_V": "",
        "post_ffe_sigma_ISI_V": "",
        "post_ffe_sigma_tn_V": "",
        "post_ffe_sigma_rn_V": "",
        "post_ffe_sigma_xn_V": "",
        "post_ffe_sigma_jn_V": "",
        "post_ffe_sigma_qn_V": "",
        "post_ffe_sigma_total_V": "",
    }
    if run_status is not None:
        pmf = getattr(run_status, "pmf", None)
        metrics["COM_DFE_dB"] = "" if pmf is None or pmf.COM is None else pmf.COM
        final_com = getattr(run_status, "final_COM", None)
        metrics["COM_dB"] = "" if final_com is None else final_com

        imp = getattr(run_status, "imp", None)
        post_ffe = None if imp is None else getattr(imp, "post_ffe", None)
        psd = None if post_ffe is None else getattr(post_ffe, "psd", None)
        if psd is not None:
            for column, attribute in (
                ("post_ffe_As_V", "As"),
                ("post_ffe_sigma_ISI_V", "sigma_ISI"),
                ("post_ffe_sigma_tn_V", "sigma_tn"),
                ("post_ffe_sigma_rn_V", "sigma_rn"),
                ("post_ffe_sigma_xn_V", "sigma_xn"),
                ("post_ffe_sigma_jn_V", "sigma_jn"),
                ("post_ffe_sigma_qn_V", "sigma_qn"),
                ("post_ffe_sigma_total_V", "sigma_total"),
            ):
                value = getattr(psd, attribute, None)
                metrics[column] = "" if value is None else value

    return {
        **partial,
        "final_status": status,
        "final_error": error,
        "grid_length": "" if overflow is None else overflow.grid_length,
        "full_length": "" if overflow is None else overflow.full_length,
        "tail_peak_ratio": "" if overflow is None else overflow.peak_ratio,
        "tail_energy_ratio": "" if overflow is None else overflow.energy_ratio,
        **metrics,
    }


def _partial_row_dict(row: COMSearchRow, *, signal_amplitude: float) -> dict[str, Any]:
    return {
        **_manifest_dict(row.idx, row.candidate),
        "status": row.status,
        "error": row.error or "",
        "mse": row.mse,
        "mse_dB": _mse_db(row.mse, signal_amplitude),
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
