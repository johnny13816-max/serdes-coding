"""Stage 3-5 selected-phase ownership and atomic commit checks."""

from types import SimpleNamespace

import numpy as np
import pytest

from serdes_coding.models.com_model_178A import (
    COM,
    COMEqChannelStatus,
    COMImpairmentStatus,
    COMImpStageStatus,
    COMPostFFEEqChannelStatus,
    COMPreDTEEqChannelStatus,
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
