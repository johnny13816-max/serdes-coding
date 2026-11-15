import numpy as np
from types import SimpleNamespace
import ast
import inspect

from serdes_coding.models import com_model_178A as model_module
from serdes_coding.models.com_model_178A import (
    COM, COMImpStageStatus, COMImpairmentStatus, COMPSDStatus,
    COMPostFFEEqChannelStatus, COMPreDTEEqChannelStatus, _apply_rxffe_response,
)
from serdes_coding.utilities.link import LinkConfig, LinkSegment, SampledResponse
from serdes_coding.utilities.psd import SampledPSD


def test_xt_phase_selection_retains_each_input_grid():
    grids = [LinkConfig.from_Nfft(8.0, 2, n) for n in (256, 512)]
    pulses = []
    for grid in grids:
        ir = np.zeros(grid.Nfft)
        ir[10:13] = [0.1, 1.0, 0.2]
        pulses.append(LinkSegment.from_ir(ir, grid))
    common = COMImpairmentStatus(pre_dte=COMImpStageStatus(psd=COMPSDStatus(sigma_X=1.0)))
    _, outputs = COM.__new__(COM).prepare_pre_dte_phase_inputs(common, pulses)
    assert all(item.cfg is grid for item, grid in zip(outputs, grids))
    assert [len(item.ir) for item in outputs] == [128, 256]


def test_grid_mode_is_read_only_by_stage1_owner():
    tree = ast.parse(inspect.getsource(COM))
    owners = {
        function.name
        for function in tree.body[0].body
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef))
        and any(isinstance(node, ast.Attribute) and node.attr == "path_grid_mode"
                for node in ast.walk(function))
    }
    assert owners == {"build_all_paths"}


def test_adaptive_build_all_paths_without_xt_only_builds_victim(monkeypatch):
    channel = SimpleNamespace(freqs=np.array([0.0, 1.0]))
    victim = object()
    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(
        src=SimpleNamespace(channel=SimpleNamespace(next=[], fext=[])),
        channel=object(), num=SimpleNamespace(path_grid_mode="adaptive", fine_grid_df=1.0),
        link=SimpleNamespace(fb=8.0, per_ui=2), txpkg_victim=object(),
    )
    monkeypatch.setattr(model_module, "_build_channel_under_test", lambda *_: [channel])
    monkeypatch.setattr(model_module, "_build_shared_path", lambda *_, **__: object())
    calls = []
    def build_group(*args, **kwargs):
        calls.append((args[1], kwargs["victim_group"]))
        return [victim], object()
    monkeypatch.setattr(model_module, "_build_adaptive_group", build_group)
    assert model.build_all_paths() == [victim]
    assert len(calls) == 1 and calls[0][1] is True


def test_post_ffe_preserves_independent_grids_and_circular_wrap():
    victim_cfg = LinkConfig.from_Nfft(8.0, 1, 8)
    xt_cfg = LinkConfig.from_Nfft(8.0, 1, 16)
    victim = SampledResponse.from_ir(np.array([1.0, 0, 0, 0, 0, 0, 0, 0.5]), victim_cfg)
    xt = SampledResponse.from_ir(np.array([0.2, 0.1]), xt_cfg)
    taps = np.array([1.0, 0.25])
    h_w = _apply_rxffe_response(victim, taps)
    h_xt = _apply_rxffe_response(xt, taps)
    status = COMPostFFEEqChannelStatus(h_w=h_w, h_XTs_w=[h_xt])
    assert status.h_w.cfg is victim_cfg
    assert status.h_XTs_w[0].cfg is xt_cfg
    np.testing.assert_allclose(h_w.ir, victim.ir + 0.25 * np.roll(victim.ir, 1))


def test_pre_dte_full_psd_uses_longest_response_without_truncation(monkeypatch):
    victim_cfg = LinkConfig.from_Nfft(8.0, 1, 16)
    xt_cfg = LinkConfig.from_Nfft(8.0, 1, 32)
    victim = SampledResponse.from_ir(np.array([1.0, 0.2]), victim_cfg)
    xt_ir = np.zeros(32)
    xt_ir[2], xt_ir[20] = 0.5, 0.25
    xt = SampledResponse.from_ir(xt_ir, xt_cfg)
    eq = COMPreDTEEqChannelStatus(h_dsamp=victim, h_tn=victim, h_J=victim,
                                  h_XTs_dsamp=[xt])
    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(
        num=SimpleNamespace(eq_ch_imp_len="full"), link=victim_cfg,
        imp=SimpleNamespace(N_qb=None, P_qc=None), filter=None,
        alg=SimpleNamespace(pre_dte_adc_clipping_convention="full_jitter_half_tail"), L=4,
    )
    monkeypatch.setattr(model_module, "_build_psd_rx_noise",
                        lambda cfg, *_: SampledPSD.from_constant(cfg.theta, 0.0, cfg.fb, cfg=cfg))
    result = model._build_pre_dte_psd(eq_ch=eq, sigma_X=1.0,
                                      tx_noise_variance=0.0, jitter_variance=0.0)
    assert result.record_cfg is xt_cfg
    assert eq.h_tn.cfg is victim_cfg and eq.h_XTs_dsamp[0].cfg is xt_cfg
    np.testing.assert_allclose(result.psd.S_xn.to_autocorrelation()[0], np.sum(xt_ir**2))


def test_pre_dte_truncated_xt_keeps_max_energy_window(monkeypatch):
    grid = LinkConfig.from_Nfft(8.0, 1, 32)
    victim = SampledResponse.from_ir(np.array([1.0, 0.2]), grid)
    xt_ir = np.zeros(32)
    xt_ir[20:22] = [1.0, 0.5]
    xt = SampledResponse.from_ir(xt_ir.copy(), grid)
    eq = COMPreDTEEqChannelStatus(h_dsamp=victim, h_tn=victim, h_J=victim,
                                  h_XTs_dsamp=[xt])
    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(
        num=SimpleNamespace(eq_ch_imp_len="truncated", num_trunc_ui=8), link=grid,
        imp=SimpleNamespace(N_qb=None, P_qc=None), filter=None,
        alg=SimpleNamespace(pre_dte_adc_clipping_convention="full_jitter_half_tail"), L=4,
    )
    monkeypatch.setattr(model_module, "_build_psd_rx_noise",
                        lambda cfg, *_: SampledPSD.from_constant(cfg.theta, 0.0, cfg.fb, cfg=cfg))
    result = model._build_pre_dte_psd(eq_ch=eq, sigma_X=1.0,
                                      tx_noise_variance=0.0, jitter_variance=0.0)
    np.testing.assert_allclose(result.psd.S_xn.to_autocorrelation()[0], 1.25)
    np.testing.assert_array_equal(xt.ir, xt_ir)
