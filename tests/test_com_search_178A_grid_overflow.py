"""A grid overflow excludes one final candidate without ending the search."""

import csv
from pathlib import Path
from types import SimpleNamespace

import pytest

from serdes_coding.io.com_excel_io_178A import excel_to_config_178A
from serdes_coding.models import com_model_178A as model_178a
from serdes_coding.search import com_search_178A as search_178a
from serdes_coding.utilities.link import GridOverflowError


ROOT = Path(__file__).resolve().parents[1]


class _FinalStatus:
    pmf = SimpleNamespace(COM=1.25)
    imp = None
    final_COM = 1.25

    def export(self, path):
        target = Path(path) / "status_summary.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("test status", encoding="utf-8")
        return {"status_summary_txt": str(target)}


def _rows():
    candidates = [
        model_178a.COMSearchCandidate(0.0, -0.1, 0.0, gain, -4.0)
        for gain in (-16.0, -12.0, -8.0)
    ]
    return [
        search_178a.COMSearchRow(idx=i, candidate=candidate, mse=0.01 + i * 0.001)
        for i, candidate in enumerate(candidates, start=1)
    ]


def _config():
    cfg = excel_to_config_178A(str(ROOT / "cases/case_260915_ci_small/178A/config.xlsx"))
    cfg.execution.search_top_k = 1
    return cfg


def test_final_search_backfills_after_grid_overflow(monkeypatch, tmp_path):
    monkeypatch.setattr(search_178a, "merge_partial_results", lambda path: _rows())

    def run(self, *, run_cfg):
        if self.cfg.filter.g_1 == -16.0:
            raise GridOverflowError(100, 128, 0.004, 5e-6)
        return _FinalStatus()

    monkeypatch.setattr(model_178a.COM, "_run_once", run)
    result = search_178a.finalize_search(_config(), model_178a.COMSearchConfig(), tmp_path,
                                         include_plots=False)
    assert result.best_row.idx == 2
    assert result.num_grid_overflow == 1
    with (tmp_path / "full_search_results.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["final_status"] == "grid_overflow"
    assert rows[0]["tail_peak_ratio"] == "0.004"
    assert rows[0]["COM_dB"] == ""
    assert rows[1]["final_status"] == "ok"


def test_final_search_fails_only_when_no_candidate_fits(monkeypatch, tmp_path):
    monkeypatch.setattr(search_178a, "merge_partial_results", lambda path: _rows())

    def run(self, *, run_cfg):
        raise GridOverflowError(100, 128, 0.004, 5e-6)

    monkeypatch.setattr(model_178a.COM, "_run_once", run)
    with pytest.raises(RuntimeError, match="No final candidate fits the fixed grid"):
        search_178a.finalize_search(_config(), model_178a.COMSearchConfig(), tmp_path,
                                    include_plots=False)


def test_non_grid_final_failure_keeps_existing_error_policy(monkeypatch, tmp_path):
    monkeypatch.setattr(search_178a, "merge_partial_results", lambda path: _rows())

    def run(self, *, run_cfg):
        if self.cfg.filter.g_1 == -16.0:
            raise ArithmeticError("unrelated solver failure")
        return _FinalStatus()

    monkeypatch.setattr(model_178a.COM, "_run_once", run)
    with pytest.raises(RuntimeError, match="non-grid reasons"):
        search_178a.finalize_search(_config(), model_178a.COMSearchConfig(), tmp_path,
                                    include_plots=False)
