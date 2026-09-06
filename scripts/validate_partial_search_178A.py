"""Validate 178A split-search results against direct single-candidate runs."""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np

from serdes_coding.io.com_excel_io import excel_to_config_178A, excel_to_search_config_178A
from serdes_coding.models.com_model_178A import COM
from serdes_coding.search.com_search_178A import (
    COMSearchConfig,
    _config_with_candidate,
    create_search_plan,
    _read_csv,
    merge_partial_results,
    run_partial_group,
)


def _smoke_search(search: COMSearchConfig) -> COMSearchConfig:
    """Create a two-candidate smoke space while preserving valid workbook values."""
    def closest_to_zero(values: object) -> tuple[float, ...] | None:
        if values is None:
            return None
        array = np.asarray(values, dtype=float).reshape(-1)
        if len(array) == 0:
            return None
        return (float(array[np.argmin(np.abs(array))]),)

    c_m2 = closest_to_zero(search.c_m2_values)
    if c_m2 is None:
        raise ValueError("Smoke validation requires c_m2_values in search_config.")
    if search.c_m2_values is not None and len(np.asarray(search.c_m2_values).reshape(-1)) > 1:
        values = np.asarray(search.c_m2_values, dtype=float).reshape(-1)
        second = values[np.argsort(np.abs(values))[1]]
        c_m2 = (c_m2[0], float(second))

    return replace(
        search,
        c_m2_values=c_m2,
        c_m1_values=closest_to_zero(search.c_m1_values),
        c_1_values=closest_to_zero(search.c_1_values),
        g_DC_values=closest_to_zero(search.g_DC_values),
        g_DC2_values=closest_to_zero(search.g_DC2_values),
        keep_top_n=2,
        keep_all_rows=True,
        continue_on_error=True,
    )


def validate(case_root: Path, mode: str, output_root: Path) -> None:
    config_path = case_root / "config" / "config_178A.xlsx"
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    cfg = excel_to_config_178A(str(config_path))
    search = excel_to_search_config_178A(str(config_path))
    if mode == "smoke":
        search = _smoke_search(search)
        cfg = replace(
            cfg,
            execution=replace(cfg.execution, search_group_size=1, search_top_k=2),
        )
    elif mode != "full":
        raise ValueError("mode must be 'smoke' or 'full'.")

    if output_root.exists() and any(output_root.iterdir()):
        raise FileExistsError(
            f"Output directory must be empty for validation: {output_root}"
        )
    output_root.mkdir(parents=True, exist_ok=True)

    artifacts = create_search_plan(cfg, search, output_root)
    for group in _read_csv(artifacts.group_plan_path, ("group_id",)):
        run_partial_group(cfg, search, artifacts.root, int(group["group_id"]))
    rows = merge_partial_results(output_root)
    candidates = search.candidates(cfg.filter)
    if len(rows) != len(candidates):
        raise AssertionError(f"row count mismatch: {len(rows)} != {len(candidates)}")

    manifest = _read_csv(output_root / "full_search_manifest.csv", ("search_index",))
    manifest_indices = {int(row["search_index"]) for row in manifest}
    result_indices = {row.idx for row in rows}
    if manifest_indices != result_indices:
        raise AssertionError("partial results do not cover manifest exactly")

    baseline_mse: dict[int, float] = {}
    for index, candidate in enumerate(candidates):
        candidate_cfg = _config_with_candidate(cfg, candidate)
        direct = COM(candidate_cfg)._run_once(run_cfg=cfg.execution.search_sweep)
        if direct.dfe is not None:
            baseline_mse[index] = float(direct.dfe.mse)

    for row in rows:
        if row.status != "ok":
            continue
        if row.idx not in baseline_mse:
            raise AssertionError(f"missing direct baseline for candidate {row.idx}")
        if not np.isclose(row.mse, baseline_mse[row.idx], rtol=1e-9, atol=1e-15):
            raise AssertionError(
                f"MSE mismatch at candidate {row.idx}: partial={row.mse}, "
                f"direct={baseline_mse[row.idx]}"
            )

    best_index = min(baseline_mse, key=baseline_mse.get)
    successful_rows = [row for row in rows if row.status == "ok"]
    if not successful_rows:
        raise AssertionError("Smoke validation produced no successful partial result.")
    if min(successful_rows, key=lambda row: row.mse).idx != best_index:
        raise AssertionError("selected best candidate does not minimize direct baseline MSE")

    print(f"PASS: {mode} partial-search integration; candidates={len(candidates)}")
    print(f"best_index={best_index}, best_mse={baseline_mse[best_index]:.12g}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--mode", choices=("smoke", "full"), default="smoke")
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    validate(args.case_root, args.mode, args.output_root)


if __name__ == "__main__":
    main()
