from dataclasses import replace
from pathlib import Path

import numpy as np
from scipy.signal import freqz, lfilter

from serdes_coding.io.com_excel_io import excel_to_config_178A
from serdes_coding.models.com_model_178A import (
    COMBilinearCTLE,
    IEEECOMFilter,
    _apply_fir_finite_record,
    _build_channel_under_test,
    _apply_rectangular_unit_pulse,
    _build_paths,
    _build_psd_tx_noise,
    _build_shared_path,
    _reference_fd_to_td_record,
    _realize_ctle_response,
)
from serdes_coding.utilities.link import LinkConfig, LinkSegment


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


def test_ctle_realization_is_separate_from_common_unit_pulse_application():
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
    continuous_ctle, continuous_domain = _realize_ctle_response(
        H_pre, H_ctf, cfg, "continuous_tf", None
    )
    continuous = _apply_rectangular_unit_pulse(
        continuous_ctle, X, cfg, 0.4, continuous_domain
    )
    np.testing.assert_array_equal(continuous.tf, H_pre.cascade_tf(H_ctf).cascade_tf(X).tf)

    bilinear_ctle, bilinear_domain = _realize_ctle_response(
        H_pre, H_ctf, cfg, "bilinear_iir", ctle_iir,
        measured_freqs=cfg.freqs,
        measured_tf=H_pre.tf,
    )
    bilinear = _apply_rectangular_unit_pulse(
        bilinear_ctle, X, cfg, 0.4, bilinear_domain
    )
    discrete_kernel = _reference_fd_to_td_record(cfg.freqs, H_pre.tf, cfg)
    expected_ctle = ctle_iir.filtered(discrete_kernel)
    expected = lfilter(np.ones(cfg.per_ui), [1.0], expected_ctle) * 0.4
    expected_record = np.zeros(cfg.Nfft)
    expected_record[:len(expected)] = expected
    np.testing.assert_allclose(bilinear.ir, expected_record, rtol=1e-13, atol=1e-15)


def test_reference_ctle_changes_only_six_path_pulses_and_tx_noise():
    root = Path(__file__).resolve().parents[1]
    cfg = excel_to_config_178A(
        str(root / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx")
    )
    channels = _build_channel_under_test(cfg.channel, cfg.policy.channel_renormalization_order)
    continuous_cfg = replace(
        cfg, policy=replace(cfg.policy, ctle_pulse_realization="continuous_tf")
    )
    bilinear_cfg = replace(
        cfg, policy=replace(cfg.policy, ctle_pulse_realization="bilinear_iir")
    )
    continuous_shared = _build_shared_path(continuous_cfg, channels[0].freqs)
    bilinear_shared = _build_shared_path(bilinear_cfg, channels[0].freqs)
    assert continuous_shared.ctle_iir is None
    assert isinstance(bilinear_shared.ctle_iir, COMBilinearCTLE)
    continuous = _build_paths(continuous_cfg, continuous_shared, channels)
    bilinear = _build_paths(bilinear_cfg, bilinear_shared, channels)
    assert len(continuous) == len(bilinear) == 6
    assert all(path.shared.ctle_iir is bilinear_shared.ctle_iir for path in bilinear)

    for lhs, rhs in zip(continuous, bilinear):
        np.testing.assert_array_equal(lhs.S_tx.sdd, rhs.S_tx.sdd)
        np.testing.assert_array_equal(lhs.S_ch.sdd, rhs.S_ch.sdd)
        np.testing.assert_array_equal(lhs.S_all.sdd, rhs.S_all.sdd)
        np.testing.assert_array_equal(lhs.H_21.tf, rhs.H_21.tf)
        np.testing.assert_array_equal(lhs.H_all.tf, rhs.H_all.tf)
        assert np.max(np.abs(lhs.pulse.ir - rhs.pulse.ir)) > 0.0

    pos = int(np.argmax(bilinear[0].pulse.ir)) % cfg.link.per_ui
    S_cont, h_cont = _build_psd_tx_noise(
        continuous[0], cfg.link, cfg.channel, cfg.filter, cfg.imp, pos, "continuous_tf"
    )
    S_bilin, h_bilin = _build_psd_tx_noise(
        bilinear[0], cfg.link, cfg.channel, cfg.filter, cfg.imp, pos, "bilinear_iir"
    )
    assert np.max(np.abs(h_cont - h_bilin)) > 0.0
    assert np.max(np.abs(S_cont.psd - S_bilin.psd)) > 0.0
