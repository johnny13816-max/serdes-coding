"""Run workbook-defined 93A search through prepare, worker, finalize and verify."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

from PIL import Image

from serdes_coding.io.com_excel_io import excel_to_config_93A, excel_to_search_config_93A
from serdes_coding.search.com_search_93A import (
    FINAL_RESULT_FIELDS,
    GROUP_PLAN_FIELDS,
    _read_csv,
    create_search_plan,
    finalize_search,
    merge_partial_results,
    run_partial_group,
)


GROUP_SIZE = 100
GROUPS_PER_WORKER = 10
MAX_WORKERS = 256


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(_project_root())).replace("\\", "/")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(case_root: Path):
    path = case_root / "config.xlsx"
    return excel_to_config_93A(str(path)), excel_to_search_config_93A(str(path))


def _fingerprint(case_root: Path, cfg) -> dict[str, str]:
    paths = [case_root / "config.xlsx", Path(cfg.channel.victim_s4p_path)]
    paths.extend(Path(path) for path in cfg.channel.next_s4p_paths)
    paths.extend(Path(path) for path in cfg.channel.fext_s4p_paths)
    return {_relative(path): _sha256(path) for path in paths}


def _check_inputs(case_root: Path, cfg, output: Path) -> dict:
    plan = json.loads((output / "execution_plan.json").read_text(encoding="utf-8"))
    if plan["inputs"] != _fingerprint(case_root, cfg):
        raise ValueError("Workbook/channel inputs differ from prepare stage.")
    return plan


def prepare(case_root: Path, output: Path, matrix_output: Path) -> None:
    cfg, search = _load(case_root)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"Search output must be fresh: {output}")
    count = len(search.candidates(cfg.filter))
    group_size = min(GROUP_SIZE, max(1, count // 2))
    artifacts = create_search_plan(cfg, search, output, group_size=group_size)
    groups = _read_csv(artifacts.group_plan_path, GROUP_PLAN_FIELDS)
    groups_per_worker = max(GROUPS_PER_WORKER, math.ceil(len(groups) / MAX_WORKERS))
    if count <= 1000:
        groups_per_worker = 1
    workers = [
        [int(group["group_id"]) for group in groups[i:i + groups_per_worker]]
        for i in range(0, len(groups), groups_per_worker)
    ]
    plan = {
        "candidates": count,
        "group_size": group_size,
        "workers": workers,
        "inputs": _fingerprint(case_root, cfg),
    }
    (output / "execution_plan.json").write_text(
        json.dumps(plan, indent=2), encoding="utf-8"
    )
    matrix_output.parent.mkdir(parents=True, exist_ok=True)
    with matrix_output.open("a", encoding="utf-8") as handle:
        handle.write("worker_ids=" + json.dumps(list(range(len(workers)))) + "\n")
    print(
        f"Prepared {count} candidates, {len(groups)} groups, {len(workers)} workers",
        flush=True,
    )


def partial(case_root: Path, output: Path, worker_id: int) -> None:
    cfg, search = _load(case_root)
    plan = _check_inputs(case_root, cfg, output)
    for group_id in plan["workers"][worker_id]:
        print(f"Worker {worker_id}: group {group_id} start", flush=True)
        run_partial_group(cfg, search, output, group_id)


def _plot_manifest(output: Path) -> dict[str, object]:
    files = []
    for path in sorted(output.rglob("*.png")):
        with Image.open(path) as image:
            image.verify()
        files.append({
            "path": str(path.relative_to(output)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        })
    if not files:
        raise RuntimeError("93A finalization produced no PNG plots.")
    return {"count": len(files), "files": files}


def verify_outputs(output: Path) -> None:
    plan = json.loads((output / "execution_plan.json").read_text(encoding="utf-8"))
    merged = merge_partial_results(output)
    if len(merged) != plan["candidates"]:
        raise RuntimeError("Merged rows do not match planned candidate count.")

    summary = json.loads((output / "search_summary.json").read_text(encoding="utf-8"))
    if summary["num_candidates"] != plan["candidates"]:
        raise RuntimeError("Search summary candidate count is inconsistent.")
    if summary["num_success"] < 1 or summary["num_error"] != (
        plan["candidates"] - summary["num_success"]
    ):
        raise RuntimeError("Search summary success/error counts are inconsistent.")

    rows = _read_csv(output / "full_search_results.csv", FINAL_RESULT_FIELDS)
    finalized = [row for row in rows if row["final_status"]]
    if len(finalized) != 1 or finalized[0]["final_status"] != "ok":
        raise RuntimeError("93A final results must contain exactly one successful winner.")
    expected = max((row for row in merged if row.status == "ok"), key=lambda row: row.FOM)
    if int(finalized[0]["search_index"]) != expected.idx:
        raise RuntimeError("Finalized candidate is not the highest-FOM partial result.")

    manifest_path = output / "plot_manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest["files"]:
            path = output / item["path"]
            if path.stat().st_size != item["bytes"] or _sha256(path) != item["sha256"]:
                raise RuntimeError("93A report artifact hash mismatch.")
    else:
        manifest = _plot_manifest(output)
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    validation = {
        "candidates": plan["candidates"],
        "num_success": summary["num_success"],
        "num_error": summary["num_error"],
        "best_row_idx": summary["best_row_idx"],
        "best_FOM": summary["best_row_FOM"],
        "best_COM": summary["COM"],
        "verified_pngs": manifest["count"],
    }
    (output / "validation_summary.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print(json.dumps(validation, indent=2), flush=True)


def finalize(case_root: Path, output: Path) -> None:
    cfg, search = _load(case_root)
    _check_inputs(case_root, cfg, output)
    finalize_search(cfg, search, output, include_plots=True)
    manifest = _plot_manifest(output)
    (output / "plot_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    verify_outputs(output)


def main() -> None:
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
