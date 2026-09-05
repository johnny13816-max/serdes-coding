"""Orchestrate the 178A search plan, matrix groups, and final merge."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

import numpy as np

from serdes_coding.com_excel_io import excel_to_config_178A, excel_to_search_config_178A
from serdes_coding.com_search_178A import (
    _read_csv,
    create_search_plan,
    finalize_search,
    merge_partial_results,
    run_partial_group,
)


def _dry_run_search(search: COMSearchConfig) -> COMSearchConfig:
    """Keep two near-zero candidates so workflow wiring can be tested safely."""
    def closest(values: object) -> tuple[float, ...] | None:
        if values is None:
            return None
        array = np.asarray(values, dtype=float).reshape(-1)
        if len(array) == 0:
            return None
        return (float(array[np.argmin(np.abs(array))]),)

    values = np.asarray(search.c_m2_values, dtype=float).reshape(-1)
    if len(values) == 0:
        raise ValueError("Dry-run requires c_m2_values in search_config.")
    order = np.argsort(np.abs(values))
    c_m2 = tuple(float(values[index]) for index in order[: min(2, len(order))])
    return replace(
        search,
        c_m2_values=c_m2,
        c_m1_values=closest(search.c_m1_values),
        c_1_values=closest(search.c_1_values),
        g_DC_values=closest(search.g_DC_values),
        g_DC2_values=closest(search.g_DC2_values),
        keep_top_n=2,
        keep_all_rows=True,
        continue_on_error=True,
    )


def _load(case_root: Path):
    config_path = case_root / "config" / "config_178A.xlsx"
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    return (
        excel_to_config_178A(str(config_path)),
        excel_to_search_config_178A(str(config_path)),
    )


def prepare(case_root: Path, output_root: Path, group_size: int, matrix_output: Path, mode: str) -> None:
    if group_size <= 0:
        raise ValueError("group_size must be positive.")
    cfg, search = _load(case_root)
    if mode == "dry-run":
        search = _dry_run_search(search)
    elif mode != "full":
        raise ValueError("mode must be 'dry-run' or 'full'.")
    cfg = replace(cfg, execution=replace(cfg.execution, search_group_size=group_size))
    artifacts = create_search_plan(cfg, search, output_root)
    groups = _read_csv(artifacts.group_plan_path, ("group_id",))
    matrix = [int(row["group_id"]) for row in groups]
    matrix_output.parent.mkdir(parents=True, exist_ok=True)
    with matrix_output.open("a", encoding="utf-8") as file:
        file.write(f"group_ids={json.dumps(matrix, separators=(',', ':'))}\n")
    print(f"Prepared {len(matrix)} groups for {sum(int(row['candidate_count']) for row in groups)} candidates.")


def partial(case_root: Path, output_root: Path, group_id: int, group_size: int) -> None:
    cfg, search = _load(case_root)
    cfg = replace(cfg, execution=replace(cfg.execution, search_group_size=group_size))
    output_path = run_partial_group(cfg, search, output_root, group_id)
    print(f"Wrote {output_path}")


def finalize(case_root: Path, output_root: Path, mode: str) -> None:
    cfg, search = _load(case_root)
    rows = merge_partial_results(output_root)
    print(f"Merged {len(rows)} partial-search rows.")
    if mode == "dry-run":
        print("Dry-run complete; search_final was intentionally skipped.")
        return
    if mode != "full":
        raise ValueError("mode must be 'dry-run' or 'full'.")
    status = finalize_search(cfg, search, output_root, include_plots=False)
    print(f"Finalized best candidate {status.best_row.idx}; COM={status.COM}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "partial", "finalize"))
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--group-size", type=int, default=1000)
    parser.add_argument("--group-id", type=int)
    parser.add_argument("--matrix-output", type=Path)
    parser.add_argument("--mode", choices=("dry-run", "full"), default="dry-run")
    args = parser.parse_args()

    if args.command == "prepare":
        if args.matrix_output is None:
            raise ValueError("prepare requires --matrix-output.")
        prepare(args.case_root, args.output_root, args.group_size, args.matrix_output, args.mode)
    elif args.command == "partial":
        if args.group_id is None:
            raise ValueError("partial requires --group-id.")
        partial(args.case_root, args.output_root, args.group_id, args.group_size)
    else:
        finalize(args.case_root, args.output_root, args.mode)


if __name__ == "__main__":
    main()
