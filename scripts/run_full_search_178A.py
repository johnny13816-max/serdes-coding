"""Run workbook-defined 178A search through prepare, worker and finalize stages."""
from __future__ import annotations
import argparse
from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from serdes_coding.io.com_excel_io import excel_to_config_178A, excel_to_search_config_178A
from serdes_coding.search.com_search_178A import (
    _read_csv, create_search_plan, finalize_search, merge_partial_results, run_partial_group,
)

# Infrastructure batching does not alter workbook candidates or run policies.
GROUP_SIZE = 100
GROUPS_PER_WORKER = 10
MAX_WORKERS = 256


def _load(case_root: Path):
    path = case_root / "config.xlsx"
    return excel_to_config_178A(str(path)), excel_to_search_config_178A(str(path))


def _fingerprint(case_root: Path, cfg):
    root = Path(__file__).resolve().parents[1]
    files = [case_root / "config.xlsx"]
    for name in ("victim_s4p_path", "next_s4p_paths", "fext_s4p_paths"):
        value = getattr(cfg.channel, name, None)
        if value:
            files.extend(Path(x) for x in ([value] if isinstance(value, str) else value))
    return {str(p.resolve().relative_to(root)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def _check_inputs(case_root, cfg, output):
    plan = json.loads((output / "execution_plan.json").read_text(encoding="utf-8"))
    if plan["inputs"] != _fingerprint(case_root, cfg):
        raise ValueError("Workbook/channel inputs differ from prepare stage.")
    return plan


def prepare(case_root, output, matrix_output):
    cfg, search = _load(case_root)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Search output must be fresh: {output}")
    count = len(search.candidates(cfg.filter))
    # Small verification cases exercise more than one artifact/merge group.
    group_size = min(GROUP_SIZE, max(1, count // 2))
    cfg = replace(cfg, execution=replace(cfg.execution, search_group_size=group_size))
    artifacts = create_search_plan(cfg, search, output)
    groups = _read_csv(artifacts.group_plan_path, ("group_id",))
    groups_per_worker = max(GROUPS_PER_WORKER, math.ceil(len(groups) / MAX_WORKERS))
    if count <= 4:
        groups_per_worker = 1
    workers = [[int(g["group_id"]) for g in groups[i:i+groups_per_worker]]
               for i in range(0, len(groups), groups_per_worker)]
    plan = {"candidates": count, "top_k": cfg.execution.search_top_k, "workers": workers, "inputs": _fingerprint(case_root, cfg)}
    (output / "execution_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    matrix_output.parent.mkdir(parents=True, exist_ok=True)
    with matrix_output.open("a", encoding="utf-8") as f:
        f.write("worker_ids=" + json.dumps(list(range(len(workers)))) + "\n")
    print(f"Prepared {count} candidates, {len(groups)} groups, {len(workers)} workers", flush=True)


def partial(case_root, output, worker_id):
    cfg, search = _load(case_root)
    plan = _check_inputs(case_root, cfg, output)
    for group_id in plan["workers"][worker_id]:
        print(f"Worker {worker_id}: group {group_id} start", flush=True)
        run_partial_group(cfg, search, output, group_id)


def verify_outputs(output):
    plan = json.loads((output / "execution_plan.json").read_text(encoding="utf-8"))
    rows = _read_csv(output / "full_search_results.csv", ("final_status",))
    evaluated = [r for r in rows if r["final_status"]]
    if not evaluated or any(r["final_status"] != "ok" for r in evaluated):
        raise RuntimeError("Final results contain missing or failed evaluations.")
    merged = merge_partial_results(output)
    if len(merged) != plan["candidates"]:
        raise RuntimeError("Downloaded partial rows do not match planned candidate count.")
    expected = sorted((r for r in merged if r.status == "ok"), key=lambda r: r.mse)[:plan["top_k"]]
    if {int(r["search_index"]) for r in evaluated} != {r.idx for r in expected}:
        raise RuntimeError("Final results do not cover the selected top-K candidates exactly.")
    count = 0
    for row in evaluated:
        directory = output / "top_K" / f"{int(row['search_index']):06d}"
        manifest = json.loads((directory / "plot_manifest.json").read_text(encoding="utf-8"))
        if not manifest["files"] or manifest["count"] != len(manifest["files"]):
            raise RuntimeError("Empty or inconsistent plot manifest")
        for item in manifest["files"]:
            data = (directory / item["path"]).read_bytes()
            if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
                raise RuntimeError("Report artifact hash mismatch")
        count += manifest["count"]
    summary = {"candidates": plan["candidates"], "final_candidates": len(evaluated), "verified_pngs": count}
    (output / "validation_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(summary, flush=True)


def finalize(case_root, output):
    cfg, search = _load(case_root)
    _check_inputs(case_root, cfg, output)
    status = finalize_search(cfg, search, output, include_plots=True)
    verify_outputs(output)
    print(f"Finalized best candidate {status.best_row.idx}; COM={status.COM}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("prepare", "partial", "finalize", "verify"))
    parser.add_argument("--case-root", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--matrix-output", type=Path)
    parser.add_argument("--worker-id", type=int)
    args = parser.parse_args()
    if args.command == "verify":
        verify_outputs(args.output_root)
        return
    if args.case_root is None:
        parser.error("--case-root is required")
    if args.command == "prepare":
        if args.matrix_output is None:
            parser.error("--matrix-output is required")
        prepare(args.case_root, args.output_root, args.matrix_output)
    elif args.command == "partial":
        if args.worker_id is None or args.worker_id < 0:
            parser.error("--worker-id must be non-negative")
        partial(args.case_root, args.output_root, args.worker_id)
    else:
        finalize(args.case_root, args.output_root)


if __name__ == "__main__":
    main()
