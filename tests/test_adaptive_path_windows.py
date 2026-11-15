import pytest
import numpy as np
from dataclasses import dataclass
from types import SimpleNamespace

from serdes_coding.models.com_178a import path_stage
from serdes_coding.models.com_178a.path_stage import (
    _select_response_windows, _trim_response_to_window,
)
from serdes_coding.utilities.link import LinkConfig, LinkSegment


def test_victim_window_aligned_to_ui_and_covers_required_range():
    length_ui, windows = _select_response_windows(
        [(1000, 1404)], 4, 8192,
    )
    start, stop = windows[0]
    assert length_ui == 128
    assert start % 4 == stop % 4 == 0
    assert start <= 1003 < 1403 <= stop
    assert stop - start == length_ui * 4


def test_xt_ranges_use_same_length_but_independent_origins():
    length_ui, windows = _select_response_windows(
        [(8, 412), (5000, 5600)], 4, 8192,
    )
    assert length_ui == 256
    assert windows[0] != windows[1]
    assert windows == [(0, 1024), (4788, 5812)]
    for (start, stop), (required_start, required_stop) in zip(
        windows, [(8, 412), (5000, 5600)]
    ):
        assert start <= required_start < required_stop <= stop
        assert start % 4 == stop % 4 == 0
        assert stop - start == length_ui * 4


def test_ui_alignment_can_require_next_larger_candidate():
    length_ui, _ = _select_response_windows(
        [(0, 516)], 4, 4096,
    )
    assert length_ui == 256


@pytest.mark.parametrize("required", [[(-1, 10)], [(0, 9000)], [(5, 5)], []])
def test_rejects_ranges_outside_record_or_empty(required):
    with pytest.raises(ValueError):
        _select_response_windows(required, 4, 8192)


def test_rejects_range_larger_than_maximum_grid():
    with pytest.raises(ValueError, match="no supported grid"):
        _select_response_windows([(0, 65537)], 1, 131072)


def test_rejects_ideal_window_not_aligned_to_ui():
    with pytest.raises(ValueError, match="whole UIs"):
        _select_response_windows([(1, 512)], 4, 4096)


def test_trim_preserves_samples_without_retaining_fine_array():
    fine = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=256)
    output = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=128)
    ir = np.zeros(256)
    ir[40:43] = [0.2, 1.0, 0.1]
    source = LinkSegment.from_ir(ir, fine)
    result = _trim_response_to_window(source, 16, 144, output)
    assert result.cfg is output
    np.testing.assert_array_equal(result.ir, source.ir[16:144])
    assert not np.shares_memory(result.ir, source.ir)


def test_trim_rejects_wrong_window_size():
    fine = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=256)
    output = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=128)
    ir = np.zeros(256)
    ir[40] = 1.0
    source = LinkSegment.from_ir(ir, fine)
    with pytest.raises(ValueError, match="window length"):
        _trim_response_to_window(source, 0, 64, output)


@dataclass
class _FakePath:
    pulse: LinkSegment
    pulse_no_txffe: object = None
    H_21_measured_freqs: object = None
    H_21_measured_tf: object = None
    H_21: object = None
    H_all: object = None
    shared: object = None
    X: object = None


def test_adaptive_group_rebuilds_victim_and_preserves_cfg(monkeypatch):
    fine = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=1024)
    report = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=128)
    channel = SimpleNamespace(freqs=np.array([0.0, 1.0]))
    cfg = SimpleNamespace(
        dte=SimpleNamespace(d_w=2, N_max=5),
        num=SimpleNamespace(relative_threshold=1e-3, absolute_threshold=None),
        channel=None, filter=SimpleNamespace(A_v=1.0, A_ne=1.0, A_fe=1.0),
        alg=SimpleNamespace(missing_dc_policy="error", out_of_measured="zero_padding"),
    )
    calls = []

    def make_path(link_cfg, *args):
        calls.append(link_cfg)
        ir = np.zeros(link_cfg.Nfft)
        ir[200], ir[202] = 1.0, 0.2
        pulse = LinkSegment.from_ir(ir, link_cfg)
        pulse._causal_shift_samples = 7
        preset_raw = np.zeros(link_cfg.Nfft)
        preset_raw[193], preset_raw[194] = 1.0, 0.4
        return _FakePath(pulse, LinkSegment.from_ir(preset_raw, link_cfg))

    monkeypatch.setattr(path_stage, "_build_shared_path", lambda *args, **kw: object())
    monkeypatch.setattr(path_stage, "_build_path", make_path)
    filter_stub = SimpleNamespace()
    filter_stub.cascade_tf = lambda other: filter_stub
    report_shared = SimpleNamespace(H_ffe=filter_stub, H_ffe_next=filter_stub,
                                    H_t=filter_stub, H_r=filter_stub, H_ctf=filter_stub)
    monkeypatch.setattr(path_stage.LinkSegment, "from_tf", lambda *args, **kw: filter_stub)
    monkeypatch.setattr(path_stage.IEEECOMFilter, "rect_pulse", lambda *args, **kw: filter_stub)
    paths, output_cfg = path_stage._build_adaptive_group(
        cfg, [("victim", None, channel)], fine, report, report_shared, victim_group=True,
    )
    assert calls == [fine, fine]
    assert paths[0].pulse.cfg is paths[0].pulse_no_txffe.cfg is output_cfg
    actual = paths[0].pulse.ir
    preset = paths[0].pulse_no_txffe.ir
    main = int(np.argmax(actual))
    assert np.argmax(preset) == main
    assert actual[main + 2] == pytest.approx(0.2)
    assert preset[main + 1] == pytest.approx(0.4)


def test_xt_group_moves_time_origin_to_fit_pre_ffe_margin(monkeypatch):
    fine = LinkConfig.from_Nfft(fb=8.0, per_ui=4, Nfft=4096)
    report = LinkConfig.from_Nfft(fb=8.0, per_ui=4, Nfft=512)
    channel = SimpleNamespace(freqs=np.array([0.0, 1.0]))
    cfg = SimpleNamespace(
        dte=SimpleNamespace(d_w=6, N_max=10),
        num=SimpleNamespace(relative_threshold=1e-3, absolute_threshold=None),
        channel=None, filter=SimpleNamespace(A_v=1.0, A_ne=1.0, A_fe=1.0),
        alg=SimpleNamespace(missing_dc_policy="error", out_of_measured="zero_padding"),
    )
    def make_path(link_cfg, *args):
        ir = np.zeros(link_cfg.Nfft)
        ir[1] = 1.0
        return _FakePath(LinkSegment.from_ir(ir, link_cfg))

    monkeypatch.setattr(path_stage, "_build_shared_path", lambda *args, **kw: object())
    monkeypatch.setattr(path_stage, "_build_path", make_path)
    select_windows = path_stage._select_response_windows
    selected_windows = []
    ideal_ranges = []
    def capture_windows(*args, **kwargs):
        ideal_ranges.extend(args[0])
        length, windows = select_windows(*args, **kwargs)
        selected_windows.extend(windows)
        return length, windows
    monkeypatch.setattr(path_stage, "_select_response_windows", capture_windows)
    filter_stub = SimpleNamespace()
    filter_stub.cascade_tf = lambda other: filter_stub
    shared = SimpleNamespace(H_ffe=filter_stub, H_ffe_next=filter_stub,
                             H_t=filter_stub, H_r=filter_stub, H_ctf=filter_stub)
    monkeypatch.setattr(path_stage.LinkSegment, "from_tf", lambda *args, **kw: filter_stub)
    monkeypatch.setattr(path_stage.IEEECOMFilter, "rect_pulse", lambda *args, **kw: filter_stub)
    paths, output_cfg = path_stage._build_adaptive_group(
        cfg, [("next", None, channel)], fine, report, shared, victim_group=False,
    )
    assert paths[0].pulse.cfg is output_cfg
    assert np.argmax(paths[0].pulse.ir) >= cfg.dte.d_w * fine.per_ui
    # Effective [1, 2) samples becomes [0, 4), then gets an integral-UI
    # shift and the configured pre/post FFE margins.
    assert ideal_ranges == [(0, 40)]
    assert selected_windows and all(
        start % fine.per_ui == stop % fine.per_ui == 0
        for start, stop in selected_windows
    )
