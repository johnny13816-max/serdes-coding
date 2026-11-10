from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from serdes_coding.io.com_excel_io_178A import excel_to_config_178A
from serdes_coding.models import com_model_178A as model_178a
from serdes_coding.search import com_search_178A as search_178a


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "cases" / "case_260915_ci_small" / "178A" / "config.xlsx"


def _configs():
    return (
        excel_to_config_178A(str(CONFIG), run_mode="single_run"),
        excel_to_config_178A(str(CONFIG), run_mode="search_sweep"),
        excel_to_config_178A(str(CONFIG), run_mode="search_final"),
    )


def test_scalar_and_length_one_axes_are_equivalent():
    single_cfg, _, _ = _configs()
    scalar = search_178a.COMSearchConfig(
        c_m2_values=0.1,
        c_m1_values=-0.2,
        c_1_values=0.03,
        g_DC_values=-16.0,
        g_DC2_values=-4.0,
    )
    vectors = replace(
        scalar,
        c_m2_values=[0.1],
        c_m1_values=np.array([-0.2]),
        c_1_values=(0.03,),
        g_DC_values=[-16.0],
        g_DC2_values=np.array([-4.0]),
    )
    assert scalar.candidates(single_cfg.filter) == vectors.candidates(single_cfg.filter)
    assert scalar.candidate_count(single_cfg.filter) == 1
    assert vectors.is_single_point(single_cfg.filter)


def test_mixed_axes_expand_as_one_cartesian_product():
    single_cfg, _, _ = _configs()
    search = search_178a.COMSearchConfig(
        c_m2_values=[0.0, 0.1],
        c_m1_values=-0.2,
        c_1_values=[0.0, 0.03, 0.06],
        g_DC_values=[-16.0, -12.0],
        g_DC2_values=-4.0,
    )
    candidates = search.candidates(single_cfg.filter)
    assert len(candidates) == 12
    assert len({
        (item.c_m2, item.c_m1, item.c_1, item.g_DC, item.g_DC2)
        for item in candidates
    }) == 12


@pytest.mark.parametrize(
    "values",
    [[], [[0.0, 0.1]], [0.0, np.nan], [np.inf]],
)
def test_search_axes_reject_empty_non_1d_or_nonfinite_values(values):
    single_cfg, _, _ = _configs()
    search = search_178a.COMSearchConfig(c_m2_values=values)
    with pytest.raises(ValueError, match="c_m2"):
        search.candidates(single_cfg.filter)


def test_adapter_places_phase_search_in_srch_and_scalarizes_single_run():
    single_cfg, sweep_cfg, final_cfg = _configs()
    assert single_cfg.srch.candidate_count(single_cfg.filter) == 1
    assert sweep_cfg.srch.candidate_count(sweep_cfg.filter) == 4
    assert single_cfg.srch.pos_sweep_method == "each_phase"
    assert sweep_cfg.srch.pos_sweep_method == "coarse_fine"
    assert final_cfg.srch.pos_sweep_method == "each_phase"
    assert not hasattr(single_cfg.exe, "pos_sweep_method")
    assert not hasattr(single_cfg.exe, "pos_coarse_stride")


def test_candidate_resolution_updates_filter_and_scalar_srch_together():
    _, sweep_cfg, _ = _configs()
    candidate = sweep_cfg.srch.candidates(sweep_cfg.filter)[-1]
    resolved = search_178a._config_with_candidate(sweep_cfg, candidate)
    assert resolved.srch.candidate_count(resolved.filter) == 1
    assert resolved.filter.c_m2 == candidate.c_m2
    assert resolved.filter.c_m1 == candidate.c_m1
    assert resolved.filter.c_1 == candidate.c_1
    assert resolved.filter.g_1 == candidate.g_DC
    assert resolved.filter.g_2 == candidate.g_DC2


def test_com_run_rejects_unresolved_vector_search_state():
    _, sweep_cfg, _ = _configs()
    with pytest.raises(ValueError, match="outer search dispatcher.*4 Cartesian"):
        model_178a.COM(sweep_cfg).run()


def test_configured_dispatch_runs_one_scalar_without_split_search(monkeypatch, tmp_path):
    single_cfg, sweep_cfg, final_cfg = _configs()
    candidate = sweep_cfg.srch.candidates(sweep_cfg.filter)[0]
    scalar_sweep = replace(sweep_cfg, srch=sweep_cfg.srch.with_candidate(candidate))
    sentinel = object()
    monkeypatch.setattr(model_178a.COM, "run", lambda self: sentinel)
    monkeypatch.setattr(
        search_178a,
        "run_full_search",
        lambda *args, **kwargs: pytest.fail("split search must not run for one point"),
    )
    assert search_178a.run_configured(
        single_cfg, scalar_sweep, final_cfg, tmp_path, include_plots=False
    ) is sentinel


def test_configured_dispatch_uses_split_search_for_multiple_points(monkeypatch, tmp_path):
    single_cfg, sweep_cfg, final_cfg = _configs()
    sentinel = object()
    calls = []

    def fake_full(sweep, final, report_dir, *, include_plots=True):
        calls.append((sweep, final, report_dir, include_plots))
        return sentinel

    monkeypatch.setattr(search_178a, "run_full_search", fake_full)
    assert search_178a.run_configured(
        single_cfg, sweep_cfg, final_cfg, tmp_path, include_plots=False
    ) is sentinel
    assert calls == [(sweep_cfg, final_cfg, tmp_path, False)]
