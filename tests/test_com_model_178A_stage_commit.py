"""Sampling-search, selected-phase ownership and atomic commit checks."""

from dataclasses import fields

from types import SimpleNamespace

import numpy as np
import pytest

from serdes_coding.models.com_model_178A import (
    COM,
    COMEqChannelStatus,
    COMImpairmentStatus,
    COMImpStageStatus,
    COMMainCursorError,
    COMPostFFEEqChannelStatus,
    COMPreDTEEqChannelStatus,
    COMRunStatus,
    COMStatus,
)
from serdes_coding.utilities.link import LinkConfig, SampledResponse


def _selected_phase(pos: int = 3):
    grid = LinkConfig.from_Nfft(8.0, 1, 16)
    response = SampledResponse.from_ir(np.array([1.0, 0.25]), grid)
    eq_ch = COMEqChannelStatus(
        phase_index=pos,
        pre_dte=COMPreDTEEqChannelStatus(h_dsamp=response),
    )
    imp = COMImpairmentStatus(pre_dte=COMImpStageStatus())
    dte = SimpleNamespace(pos=pos, H_rxffe=response)
    return eq_ch, imp, dte


def _sampling_search_model(*, per_ui, method, stride, mse_by_pos, rejected=()):
    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(
        exe=SimpleNamespace(target="mse"),
        mlsd=SimpleNamespace(enable=False),
        dte=SimpleNamespace(N_b=1),
        link=SimpleNamespace(per_ui=per_ui),
        srch=SimpleNamespace(pos_sweep_method=method, pos_coarse_stride=stride),
        num=SimpleNamespace(pmf_grid_quality="fine", pmf_keep_mass=0.99),
    )
    model.status = None
    victim = SimpleNamespace(pulse=SimpleNamespace(ir=np.array([1.0])))
    visited = []

    model.build_all_paths = lambda: [victim]
    model._validate_victim_time_alignment = lambda _victim: None
    model.calculate_pre_dte_imp_common = lambda *, victim: SimpleNamespace()
    model.prepare_pre_dte_phase_inputs = (
        lambda *, common, h_XTs: (common, [])
    )

    def calculate_pre_dte(*, victim, pos, common, h_XTs_dsamp):
        del victim, common, h_XTs_dsamp
        visited.append(pos)
        eq_ch, imp, _ = _selected_phase(pos)
        return eq_ch, imp

    def calculate_dte(*, victim, eq_ch, imp_pre, pos):
        del victim, eq_ch, imp_pre
        if pos in rejected:
            raise COMMainCursorError("invalid cursor")
        _, _, dte = _selected_phase(pos)
        dte.mse = mse_by_pos[pos]
        return dte

    model.calculate_pre_dte_imp_at_pos = calculate_pre_dte
    model.calculate_MMSE_DTE = calculate_dte
    return model, visited


def test_run_status_contains_only_stage_3_sampling_trace() -> None:
    assert {field.name for field in fields(COMRunStatus)} == {
        "mse_by_pos",
        "main_cursor_error_by_pos",
        "coarse_pos",
        "fine_pos",
    }


def test_selected_phase_mismatch_does_not_partially_update_status() -> None:
    model = COM.__new__(COM)
    original = COMStatus(paths=[SimpleNamespace(name="existing")])
    model.status = original
    eq_ch, imp, dte = _selected_phase(pos=3)
    dte.pos = 4

    with pytest.raises(ValueError, match="phase status mismatch"):
        model._assign_selected_phase(eq_ch, imp, dte)

    assert model.status is original
    assert model.status.eq_ch is None
    assert model.status.imp is None
    assert model.status.dte is None


def test_post_ffe_commit_preserves_selected_phase_objects() -> None:
    model = COM.__new__(COM)
    model.status = COMStatus()
    eq_ch, imp, dte = _selected_phase(pos=5)
    model._assign_selected_phase(eq_ch, imp, dte)
    selected = model.status
    eq_post = COMPostFFEEqChannelStatus(h_w=eq_ch.h_dsamp)
    imp_post = COMImpairmentStatus(post_ffe=COMImpStageStatus())

    model._assign_post_ffe(5, eq_post, imp_post)

    assert model.status is not selected
    assert model.status.eq_ch.phase_index == 5
    assert model.status.eq_ch.pre_dte is eq_ch.pre_dte
    assert model.status.eq_ch.post_ffe is eq_post
    assert model.status.imp.pre_dte is imp.pre_dte
    assert model.status.imp.post_ffe is imp_post.post_ffe
    assert model.status.dte is dte


def test_post_ffe_phase_mismatch_does_not_partially_update_status() -> None:
    model = COM.__new__(COM)
    model.status = COMStatus()
    eq_ch, imp, dte = _selected_phase(pos=2)
    model._assign_selected_phase(eq_ch, imp, dte)
    selected = model.status

    with pytest.raises(ValueError, match="does not match"):
        model._assign_post_ffe(
            1,
            COMPostFFEEqChannelStatus(h_w=eq_ch.h_dsamp),
            COMImpairmentStatus(post_ffe=COMImpStageStatus()),
        )

    assert model.status is selected
    assert model.status.eq_ch.post_ffe is None
    assert model.status.imp.post_ffe is None


def test_post_ffe_status_requires_one_shared_response_grid() -> None:
    first_grid = LinkConfig.from_Nfft(8.0, 1, 16)
    second_grid = LinkConfig.from_Nfft(8.0, 1, 18)
    victim = SampledResponse.from_ir(np.array([1.0, 0.25]), first_grid)
    xtalk = SampledResponse.from_ir(np.array([0.5]), second_grid)

    with pytest.raises(ValueError, match="must share response_cfg"):
        COMPostFFEEqChannelStatus(
            response_cfg=first_grid,
            h_w=victim,
            h_XTs_w=[xtalk],
        )


def test_sampling_phase_owner_resolves_coarse_fine_and_keeps_complete_bundle() -> None:
    mse_by_pos = {0: 5.0, 4: 1.0, 2: 3.0, 3: 0.5, 5: 2.0, 6: 4.0}
    model, visited = _sampling_search_model(
        per_ui=8,
        method="coarse_fine",
        stride=4,
        mse_by_pos=mse_by_pos,
    )
    status = model._run_once()

    assert visited == [0, 4, 2, 3, 5, 6]
    assert (status.eq_ch.phase_index, status.dte.pos) == (3, 3)
    assert status.run.coarse_pos == [0, 4]
    assert status.run.fine_pos == [2, 3, 5, 6]
    assert status.run.mse_by_pos == [5.0, None, 3.0, 0.5, 1.0, 2.0, 4.0, None]


def test_sampling_phase_index_helpers_receive_concrete_choice() -> None:
    assert COM._initial_pos_sweep_indices(
        per_ui=8, method="each_phase", coarse_stride=4
    ) == list(range(8))
    assert COM._initial_pos_sweep_indices(
        per_ui=8, method="coarse_fine", coarse_stride=4
    ) == [0, 4]
    assert COM._fine_pos_sweep_indices(
        per_ui=8,
        coarse_stride=4,
        coarse_best_pos=0,
        evaluated_indices={0, 4},
    ) == [6, 7, 1, 2]

    with pytest.raises(ValueError, match="must not exceed"):
        COM._initial_pos_sweep_indices(
            per_ui=8, method="coarse_fine", coarse_stride=9
        )


def test_sampling_phase_owner_skips_cursor_error_and_keeps_earlier_tie() -> None:
    model, visited = _sampling_search_model(
        per_ui=4,
        method="each_phase",
        stride=2,
        mse_by_pos={0: 1.0, 2: 1.0, 3: 2.0},
        rejected={1},
    )
    status = model._run_once()

    assert visited == [0, 1, 2, 3]
    assert (status.eq_ch.phase_index, status.dte.pos) == (0, 0)
    assert status.run.main_cursor_error_by_pos == [
        None, "invalid cursor", None, None
    ]
    assert status.run.mse_by_pos == [1.0, None, 1.0, 2.0]
