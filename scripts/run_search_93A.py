"""Run and verify one workbook-defined IEEE 802.3 Annex 93A search."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time

from PIL import Image

from serdes_coding.io.com_excel_io import excel_to_config_93A, excel_to_search_config_93A
from serdes_coding.models.com_model_93A import COM, COMReport


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _relative(path: Path) -> str:
    return str(path.resolve().relative_to(_project_root())).replace("\\", "/")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _input_manifest(config_path: Path, cfg) -> dict[str, str]:
    paths = [config_path]
    paths.append(Path(cfg.channel.victim_s4p_path))
    paths.extend(Path(path) for path in cfg.channel.next_s4p_paths)
    paths.extend(Path(path) for path in cfg.channel.fext_s4p_paths)
    return {_relative(path): _sha256(path) for path in paths}


def _verify_pngs(output_root: Path) -> dict[str, object]:
    pngs = sorted(output_root.rglob("*.png"))
    if not pngs:
        raise RuntimeError("93A search produced no PNG plots.")

    files = []
    for path in pngs:
        with Image.open(path) as image:
            image.verify()
        files.append(
            {
                "path": str(path.relative_to(output_root)).replace("\\", "/"),
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {"count": len(files), "files": files}


def run(case_root: Path, output_root: Path) -> None:
    config_path = case_root / "config.xlsx"
    if not config_path.is_file():
        raise FileNotFoundError(f"93A project workbook not found: {config_path}")
    if output_root.exists():
        shutil.rmtree(output_root)

    cfg = excel_to_config_93A(str(config_path))
    search = excel_to_search_config_93A(str(config_path))
    candidate_count = len(search.candidates(cfg.filter))
    if candidate_count < 2:
        raise ValueError("93A search smoke test requires at least two workbook candidates.")

    inputs = _input_manifest(config_path, cfg)
    print(f"93A workbook search: {candidate_count} candidates", flush=True)
    started = time.perf_counter()
    status = COM(cfg).run(search)
    elapsed_s = time.perf_counter() - started

    cfg.export(str(output_root))
    status.export(str(output_root), include_plots=False)
    status.best.export_report_summary(str(output_root / "best"))
    COMReport(cfg, status).plot_search_run(str(output_root / "plots"))

    summary_path = output_root / "search_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary["num_candidates"] != candidate_count:
        raise RuntimeError("Exported candidate count does not match the workbook search.")
    if summary["num_success"] < 1 or summary["best_row_idx"] is None:
        raise RuntimeError("93A search did not produce a valid best candidate.")
    if status.best.pmf is None or status.best.pmf.COM is None:
        raise RuntimeError("93A best candidate did not complete final PMF/COM.")

    plot_manifest = _verify_pngs(output_root)
    (output_root / "plot_manifest.json").write_text(
        json.dumps(plot_manifest, indent=2), encoding="utf-8"
    )
    validation = {
        "candidate_count": candidate_count,
        "num_success": summary["num_success"],
        "num_error": summary["num_error"],
        "best_row_idx": summary["best_row_idx"],
        "best_FOM": summary["best_row_FOM"],
        "best_COM": status.best.pmf.COM,
        "elapsed_seconds": elapsed_s,
        "verified_pngs": plot_manifest["count"],
        "inputs": inputs,
    }
    (output_root / "validation_summary.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    print(json.dumps(validation, indent=2), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    run(args.case_root, args.output_root)


if __name__ == "__main__":
    main()
