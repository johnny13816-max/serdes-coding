from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from scipy.signal import freqz, lfilter

from serdes_coding.io.com_excel_io import excel_to_config_178A
from serdes_coding.models.com_model_178A import (
    COM,
    COMBilinearCTLE,
    IEEECOMFilter,
    _apply_fir_finite_record,
    _apply_rxffe_response,
    _build_channel_under_test,
    _build_paths,
    _calculate_tx_noise_eq_ch,
    _build_shared_path,
)
from serdes_coding.models.com_178a.path_stage import (
    _apply_rectangular_unit_pulse,
    _reference_fd_to_td_record,
)
from serdes_coding.utilities.link import LinkConfig, LinkSegment, SampledResponse, resample_tf


def _small_cfg() -> LinkConfig:
    return LinkConfig(fb=100e9, per_ui=8, target_df=1e9)


def test_bilinear_ctle_sections_have_expected_gain_and_stable_poles():
    cfg = _small_cfg()
    b1, a1 = IEEECOMFilter._bilinear_section_coefficients(
        cfg, f_z=40e9, f_p1=40e9, f_p2=100e9, g_dc=-20.0
    )
    b2, a2 = IEEECOMFilter._bilinear_section_coefficients(
        cfg, f_z=1.25e9, f_p1=1.25e9, g_dc=-2.0
    )

    assert np.max(np.abs(np.roots(a1))) < 1.0
    assert np.max(np.abs(np.roots(a2))) < 1.0
    np.testing.assert_allclose(np.sum(b1) / np.sum(a1), 10 ** (-20.0 / 20.0), rtol=1e-13)
    np.testing.assert_allclose(np.sum(b2) / np.sum(a2), 10 ** (-2.0 / 20.0), rtol=1e-13)
    np.testing.assert_allclose(np.polyval(b1, -1.0), 0.0, atol=1e-15)


def test_first_order_bilinear_section_matches_infinite_second_pole_limit():
    cfg = _small_cfg()
    fz = fp1 = 1.25e9
    gain_db = -2.0
    b, a = IEEECOMFilter._bilinear_section_coefficients(
        cfg, f_z=fz, f_p1=fp1, g_dc=gain_db
    )

    K = 2.0 * cfg.Fs
    p1 = -2.0 * np.pi * fp1
    p2 = -2.0 * np.pi * 1e24
    zero = -2.0 * np.pi * fz * 10 ** (gain_db / 20.0)
    p1d = (K + p1) / (K - p1)
    p2d = (K + p2) / (K - p2)
    zd = (K + zero) / (K - zero)
    kd = (K - zero) / ((K - p1) * (K - p2)) * fp1 / fz
    b_limit = (-p2) * kd * np.poly([zd, -1.0])
    a_limit = np.poly([p1d, p2d])
    omega = np.array([0.0, 0.2, 1.0, 2.5])
    np.testing.assert_allclose(
        freqz(b, a, worN=omega)[1],
        freqz(b_limit, a_limit, worN=omega)[1],
        rtol=1e-12,
        atol=2e-15,
    )


def test_bilinear_ctle_application_is_two_causal_sections():
    cfg = _small_cfg()
    ir = np.zeros(cfg.Nfft)
    ir[7] = 1.0
    ir[9] = -0.2
    kwargs = dict(
        g_1=-20.0,
        g_2=-2.0,
        f_z1=40e9,
        f_z2=1.25e9,
        f_p1=40e9,
        f_p2=100e9,
        f_p3=1.25e9,
    )
    actual = IEEECOMFilter.apply_rx_equalizer_bilinear(ir, cfg, **kwargs)
    b1, a1 = IEEECOMFilter._bilinear_section_coefficients(
        cfg, f_z=kwargs["f_z1"], f_p1=kwargs["f_p1"],
        f_p2=kwargs["f_p2"], g_dc=kwargs["g_1"],
    )
    b2, a2 = IEEECOMFilter._bilinear_section_coefficients(
        cfg, f_z=kwargs["f_z2"], f_p1=kwargs["f_p3"], g_dc=kwargs["g_2"],
    )
    expected = lfilter(b2, a2, lfilter(b1, a1, ir))
    np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=1e-15)
    np.testing.assert_array_equal(actual[:7], np.zeros(7))


def test_finite_record_rxffe_is_circular_shift_sum():
    response = np.array([1.0, 2.0, 3.0, 4.0])
    taps = np.array([0.5, -0.25])
    expected = 0.5 * response - 0.25 * np.roll(response, 1)
    np.testing.assert_array_equal(_apply_fir_finite_record(response, taps), expected)


def test_rxffe_owner_covers_fixed_expanded_and_circular_records():
    cfg = LinkConfig.from_Nfft(8.0, 1, 8)
    expanded = LinkConfig.from_Nfft(8.0, 1, 10)
    response = SampledResponse.from_ir(np.array([1.0, 2.0, 3.0, 4.0]), cfg)
    taps = np.array([0.5, -0.25])

    fixed = _apply_rxffe_response(
        response, taps, cfg, "linear_fixed_grid", "fixed test"
    )
    full = _apply_rxffe_response(
        response, taps, expanded, "linear_expanded_grid", "expanded test"
    )
    circular = _apply_rxffe_response(
        response, taps, cfg, "finite_record_circshift", "circular test"
    )

    expected_linear = np.convolve(np.array([1.0, 2.0, 3.0, 4.0]), taps)
    np.testing.assert_allclose(fixed.ir[:5], expected_linear)
    np.testing.assert_allclose(full.ir[:5], expected_linear)
    assert full.cfg is expanded
    np.testing.assert_allclose(
        circular.ir,
        0.5 * response.ir - 0.25 * np.roll(response.ir, 1),
    )


def test_common_unit_pulse_application_preserves_each_realization_domain():
    cfg = _small_cfg()
    pre_ir = np.zeros(cfg.Nfft)
    pre_ir[10:26] = np.exp(-np.arange(16) / 3.0)
    H_pre = LinkSegment.from_ir(pre_ir, cfg)
    ft = type("Filter", (), dict(
        g_1=-20.0, g_2=-2.0, f_z1=40e9, f_z2=1.25e9,
        f_p1=40e9, f_p2=100e9, f_p3=1.25e9,
    ))()
    H_ctf = IEEECOMFilter.rx_equalizer(
        cfg, ft.g_1, ft.g_2, ft.f_z1, ft.f_z2, ft.f_p1, ft.f_p2, ft.f_p3
    )
    ctle_iir = IEEECOMFilter.build_rx_equalizer_bilinear(
        cfg,
        g_1=ft.g_1, g_2=ft.g_2, f_z1=ft.f_z1, f_z2=ft.f_z2,
        f_p1=ft.f_p1, f_p2=ft.f_p2, f_p3=ft.f_p3,
    )
    assert isinstance(ctle_iir, COMBilinearCTLE)
    X = IEEECOMFilter.rect_pulse_93A(cfg, 0.4)
    continuous = _apply_rectangular_unit_pulse(
        H_pre.cascade_tf(H_ctf), X, cfg, 0.4, "frequency_tf"
    )
    np.testing.assert_array_equal(continuous.tf, H_pre.cascade_tf(H_ctf).cascade_tf(X).tf)

    discrete_kernel = _reference_fd_to_td_record(
        cfg.freqs, H_pre.tf, cfg, out_of_measured="zero_padding"
    )
    expected_ctle = ctle_iir.filtered(discrete_kernel)
    ctle_record = np.zeros(cfg.Nfft)
    ctle_record[:len(expected_ctle)] = expected_ctle * cfg.Fs
    bilinear_ctle = IEEECOMFilter._from_finite_record_ir(ctle_record, cfg)
    bilinear = _apply_rectangular_unit_pulse(
        bilinear_ctle, X, cfg, 0.4, "finite_record_ir"
    )
    expected = lfilter(np.ones(cfg.per_ui), [1.0], expected_ctle) * 0.4
    expected_record = np.zeros(cfg.Nfft)
    expected_record[:len(expected)] = expected
    np.testing.assert_allclose(bilinear.ir, expected_record, rtol=1e-13, atol=1e-15)


def test_reference_fd_to_td_requires_alg001_completed_dc_input():
    cfg = _small_cfg()
    freqs = cfg.freqs[1:20]
    response = np.exp(-1j * 2.0 * np.pi * freqs * 15e-12)

    with pytest.raises(ValueError, match="ALG-001 completed input with DC"):
        _reference_fd_to_td_record(
            freqs, response, cfg, out_of_measured="zero_padding"
        )


def test_reference_fd_to_td_uses_alg006_out_of_measured_policy():
    cfg = _small_cfg()
    measured_freqs = cfg.freqs[:101]
    delay = 12e-12
    measured_tf = (
        0.9 - 0.2 * measured_freqs / measured_freqs[-1]
    ) * np.exp(-1j * 2.0 * np.pi * measured_freqs * delay)

    def expected_record(method):
        measured_df = float(measured_freqs[2] - measured_freqs[1])
        n_steps = max(1, int(np.floor(cfg.f_nyq / measured_df + 0.5)))
        output_freqs = np.arange(n_steps + 1) * (cfg.f_nyq / n_steps)
        extended = resample_tf(
            measured_tf,
            measured_freqs,
            output_freqs,
            out_of_measured=method,
        )
        raw = np.fft.irfft(extended, n=2 * n_steps)
        retained = np.flatnonzero(np.abs(raw) > np.max(np.abs(raw)) * 0.001)
        return raw[:int(retained[-1]) + 1]

    zero = _reference_fd_to_td_record(
        measured_freqs,
        measured_tf,
        cfg,
        out_of_measured="zero_padding",
    )
    cosine = _reference_fd_to_td_record(
        measured_freqs,
        measured_tf,
        cfg,
        out_of_measured="cosine_decay",
    )

    np.testing.assert_allclose(
        zero, expected_record("zero_padding"), rtol=0.0, atol=1e-15
    )
    np.testing.assert_allclose(
        cosine, expected_record("cosine_decay"), rtol=0.0, atol=1e-15
    )
    assert zero.shape != cosine.shape or np.max(np.abs(zero - cosine)) > 0.0


def test_reference_ctle_changes_only_six_path_pulses_and_tx_noise():
    root = Path(__file__).resolve().parents[1]
    cfg = excel_to_config_178A(
        str(root / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx")
    )
    channels = _build_channel_under_test(cfg.channel)
    continuous_cfg = replace(
        cfg, policy=replace(cfg.policy, ctle_pulse_realization="continuous_tf")
    )
    bilinear_cfg = replace(
        cfg, policy=replace(cfg.policy, ctle_pulse_realization="bilinear_iir")
    )
    bilinear_cosine_cfg = replace(
        bilinear_cfg,
        policy=replace(bilinear_cfg.policy, out_of_measured="cosine_decay"),
    )
    continuous_shared = _build_shared_path(continuous_cfg, channels[0].freqs)
    bilinear_shared = _build_shared_path(bilinear_cfg, channels[0].freqs)
    assert continuous_shared.ctle_pulse_realization == "continuous_tf"
    assert bilinear_shared.ctle_pulse_realization == "bilinear_iir"
    assert continuous_shared.ctle_iir is None
    assert isinstance(bilinear_shared.ctle_iir, COMBilinearCTLE)
    with pytest.raises(ValueError, match="continuous_tf realization must not store"):
        replace(continuous_shared, ctle_iir=bilinear_shared.ctle_iir)
    with pytest.raises(ValueError, match="bilinear_iir realization requires"):
        replace(bilinear_shared, ctle_iir=None)
    continuous = _build_paths(continuous_cfg, continuous_shared, channels)
    bilinear = _build_paths(bilinear_cfg, bilinear_shared, channels)
    bilinear_cosine = _build_paths(
        bilinear_cosine_cfg,
        _build_shared_path(bilinear_cosine_cfg, channels[0].freqs),
        channels,
    )
    assert len(continuous) == len(bilinear) == 6
    assert all(path.shared.ctle_pulse_realization == "continuous_tf" for path in continuous)
    assert all(path.shared.ctle_pulse_realization == "bilinear_iir" for path in bilinear)
    assert all(path.shared.ctle_iir is bilinear_shared.ctle_iir for path in bilinear)
    assert continuous[0].pulse_no_txffe is not None
    assert bilinear[0].pulse_no_txffe is not None
    assert bilinear_cosine[0].pulse_no_txffe is not None
    assert all(path.pulse_no_txffe is None for path in continuous[1:])
    assert all(path.pulse_no_txffe is None for path in bilinear[1:])
    expected_continuous_no_txffe = (
        continuous[0].H_t
        .cascade_tf(continuous[0].H_21)
        .cascade_tf(continuous[0].H_r)
        .cascade_tf(continuous[0].H_ctf)
        .cascade_tf(continuous[0].X)
    )
    np.testing.assert_array_equal(
        continuous[0].pulse_no_txffe.tf,
        expected_continuous_no_txffe.tf,
    )

    for lhs, rhs in zip(continuous, bilinear):
        np.testing.assert_array_equal(lhs.S_tx.sdd, rhs.S_tx.sdd)
        np.testing.assert_array_equal(lhs.S_ch.sdd, rhs.S_ch.sdd)
        np.testing.assert_array_equal(lhs.S_all.sdd, rhs.S_all.sdd)
        np.testing.assert_array_equal(lhs.H_21_measured_freqs, rhs.H_21_measured_freqs)
        np.testing.assert_array_equal(lhs.H_21_measured_tf, rhs.H_21_measured_tf)
        np.testing.assert_array_equal(lhs.H_21.tf, rhs.H_21.tf)
        np.testing.assert_array_equal(lhs.H_all.tf, rhs.H_all.tf)
        assert np.max(np.abs(lhs.pulse.ir - rhs.pulse.ir)) > 0.0

    pos = int(np.argmax(bilinear[0].pulse.ir)) % cfg.link.per_ui
    h_cont, variance_cont = _calculate_tx_noise_eq_ch(
        continuous[0], cfg.link, cfg.imp, pos,
    )
    h_bilin, variance_bilin = _calculate_tx_noise_eq_ch(
        bilinear[0], cfg.link, cfg.imp, pos,
    )
    h_bilin_cosine, variance_bilin_cosine = _calculate_tx_noise_eq_ch(
        bilinear_cosine[0], cfg.link, cfg.imp, pos,
    )
    np.testing.assert_array_equal(
        h_cont,
        continuous[0].pulse_no_txffe.ir[pos::cfg.link.per_ui],
    )
    np.testing.assert_array_equal(
        h_bilin,
        bilinear[0].pulse_no_txffe.ir[pos::cfg.link.per_ui],
    )
    np.testing.assert_array_equal(
        h_bilin_cosine,
        bilinear_cosine[0].pulse_no_txffe.ir[pos::cfg.link.per_ui],
    )
    S_cont = COM(continuous_cfg)._build_eq_ch_imp_psd(
        h_cont, variance_cont, source_name="continuous TX-noise eq-channel"
    )
    S_bilin = COM(bilinear_cfg)._build_eq_ch_imp_psd(
        h_bilin, variance_bilin, source_name="bilinear TX-noise eq-channel"
    )
    assert np.max(np.abs(h_cont - h_bilin)) > 0.0
    assert np.max(np.abs(S_cont.psd - S_bilin.psd)) > 0.0
    assert variance_bilin_cosine == variance_bilin
    assert np.max(np.abs(h_bilin_cosine - h_bilin)) > 0.0
