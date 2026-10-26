"""Equation-level validation of the explicit S4P/Sdd ingestion boundary."""
from pathlib import Path

import numpy as np
import pytest
import skrf as rf

from serdes_coding.utilities.sparam import SparamModel
from serdes_coding.models import com_model_93A as m93
from serdes_coding.models import com_model_178A as m178
from serdes_coding.io.com_excel_io_178A import excel_to_config_178A

ROOT = Path(__file__).resolve().parents[1]
ORDER = (0, 2, 1, 3)


def measurement():
    rng = np.random.default_rng(178)
    s = (rng.normal(size=(3, 4, 4)) + 1j * rng.normal(size=(3, 4, 4))) * 0.08
    return rf.Network(f=[0, 1e9, 2e9], s=s, z0=50.0)


def equation(s, target=92.5):
    rho = (target - 100.0) / (target + 100.0)
    eye = np.eye(2)
    return (s - rho * eye) @ np.linalg.inv(eye - rho * s)


@pytest.mark.parametrize("representation", ["auto", "s4p"])
def test_sdd_first_is_explicit_and_preserves_raw_s4p(representation):
    source = measurement()
    before_s, before_z0 = source.s.copy(), source.z0.copy()
    raw = SparamModel.from_network(source, representation=representation, port_order=ORDER)
    measured_sdd = raw.s4p_to_s2p()
    actual = measured_sdd.renormalized(92.5)
    assert raw.representation == "s4p" and raw.nports == 4
    assert actual.representation == "s2p" and actual.nports == 2
    np.testing.assert_allclose(actual.sdd, equation(measured_sdd.sdd), atol=1e-12, rtol=0)
    np.testing.assert_array_equal(source.s, before_s)
    np.testing.assert_array_equal(source.z0, before_z0)
    np.testing.assert_array_equal(actual.network.z0, np.full((3, 2), 92.5))


def test_array_constructors_preserve_the_declared_representation():
    source = measurement()
    raw = SparamModel.from_network(source, port_order=ORDER)
    assigned = SparamModel.from_s4p_array(
        source.f, source.s, port_order=ORDER, z0=source.z0,
    )
    np.testing.assert_array_equal(assigned.s, raw.s)
    assert assigned.representation == "s4p"
    with pytest.raises(ValueError, match="call s4p_to_s2p"):
        _ = assigned.sdd
    converted = raw.s4p_to_s2p()
    copied = SparamModel.from_network(converted.network, representation="s2p")
    np.testing.assert_array_equal(copied.sdd, converted.sdd)


def test_s4p_first_matches_full_four_port_oracle_without_mutating_source():
    source = measurement()
    before_s, before_z0 = source.s.copy(), source.z0.copy()
    four = source.copy()
    four.renormalize(46.25)
    expected = SparamModel.from_network(four, representation="s4p", port_order=ORDER).s4p_to_s2p()
    actual = (
        SparamModel.from_network(source, representation="s4p", port_order=ORDER)
        .renormalized(46.25)
        .s4p_to_s2p()
    )
    np.testing.assert_allclose(actual.sdd, expected.sdd, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(actual.network.z0, np.full((3, 2), 92.5))
    np.testing.assert_array_equal(source.s, before_s)
    np.testing.assert_array_equal(source.z0, before_z0)


def test_representation_operations_reject_wrong_domain():
    raw = SparamModel.from_network(measurement(), representation="s4p", port_order=ORDER)
    sdd = raw.s4p_to_s2p()
    with pytest.raises(ValueError, match="does not match"):
        SparamModel.from_network(measurement(), representation="s2p")
    with pytest.raises(ValueError, match="requires an s4p"):
        sdd.s4p_to_s2p()
    with pytest.raises(ValueError, match="requires an s2p"):
        raw.s2p_to_synthetic_s4p(port_order=ORDER, z0_diff=100.0)


def test_frequency_limit_keeps_first_measured_point_at_or_above_limit(tmp_path):
    freqs = np.arange(5, dtype=float) * 1e9
    source = rf.Network(f=freqs, s=np.zeros((len(freqs), 4, 4), complex), z0=50.0)
    source.write_touchstone(str(tmp_path / "limited"))
    raw = SparamModel.from_touchstone(tmp_path / "limited.s4p", representation="s4p")
    limited = raw.limited_to_frequency(2.5e9)
    np.testing.assert_array_equal(limited.freqs, freqs[:4])
    assert limited.freqs[-1] == pytest.approx(3e9)
    np.testing.assert_array_equal(raw.limited_to_frequency(10e9).freqs, freqs)
    with pytest.raises(ValueError, match="finite and positive"):
        raw.limited_to_frequency(0.0)


@pytest.mark.parametrize("module", [m93, m178])
def test_both_channel_builders_apply_sdd_first_equation(tmp_path, module):
    source = measurement()
    source.write_touchstone(str(tmp_path / "victim"))
    cfg = m93.COMChannelConfig(
        victim_s4p_path=str(tmp_path / "victim.s4p"), port_order=ORDER,
        R0=46.25, R_d_tx=46.25, R_d_rx=46.25,
    )
    channels = (
        module._build_channel_under_test_93A(cfg)
        if module is m93 else module._build_channel_under_test(cfg)
    )
    measured_sdd = SparamModel.from_network(source, port_order=ORDER).s4p_to_s2p()
    np.testing.assert_allclose(channels[0].sdd, equation(measured_sdd.sdd), atol=1e-12, rtol=0)


def test_fixed_sicopr_case_equation_and_vtf():
    cfg = excel_to_config_178A(str(ROOT / "cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx"))
    raw = SparamModel.from_touchstone(
        cfg.channel.victim_s4p_path, representation="s4p", port_order=cfg.channel.port_order,
    ).limited_to_frequency(cfg.channel.sparam_frequency_limit_Hz)
    ch = m178._build_channel_under_test(cfg.channel, "sdd_first")[0]
    np.testing.assert_allclose(ch.sdd, equation(raw.s4p_to_s2p().sdd), atol=1e-10, rtol=0)
    f = ch.freqs
    tx = m178._build_txpkg(f, cfg.txpkg_victim)
    rx = m178._build_rxpkg(f, cfg.rxpkg)
    all_s = tx.cascade_com_93A(ch).cascade_com_93A(rx)
    h = all_s.voltage_transfer_function(cfg.channel.gamma_src, cfg.channel.gamma_load)
    ht = np.exp(-2 * (np.pi * f * cfg.filter.Tr / 1.6832) ** 2)
    hr = 1 / np.polyval([1, 2.613126, 3.414214, 2.613126, 1], 1j * f / cfg.filter.fr)
    loss = np.interp(53.125e9, f, -20 * np.log10(abs(h * ht * hr)))
    assert loss == pytest.approx(37.667089589791686, abs=1e-6)


def test_fixed_sicopr_case_s4p_first_closes_all_channel_matrices():
    cfg = excel_to_config_178A(str(ROOT / "cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx"))
    channels = m178._build_channel_under_test(cfg.channel, "s4p_first")
    paths = [cfg.channel.victim_s4p_path, *cfg.channel.next_s4p_paths, *cfg.channel.fext_s4p_paths]
    for path, channel in zip(paths, channels):
        expected = (
            SparamModel.from_touchstone(
                path, representation="s4p", port_order=cfg.channel.port_order,
            )
            .renormalized(cfg.channel.R0)
            .limited_to_frequency(cfg.channel.sparam_frequency_limit_Hz)
            .s4p_to_s2p()
        )
        np.testing.assert_allclose(channel.sdd, expected.sdd, atol=1e-12, rtol=0)
