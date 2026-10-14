"""Equation-level validation of the measured Sdd normalization boundary."""
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


@pytest.mark.parametrize("mode", ["auto", "s4p"])
def test_s4p_ingestion_matches_178a_equation_and_preserves_source(mode):
    source = measurement()
    before_s, before_z0 = source.s.copy(), source.z0.copy()
    raw = SparamModel.from_network(source, mode="s4p", port_order=ORDER)
    actual = m178.IEEECOMSparam.from_network(source, mode=mode, port_order=ORDER, z0=92.5)
    np.testing.assert_allclose(actual.sdd, equation(raw.sdd), atol=1e-12, rtol=0)
    np.testing.assert_array_equal(source.s, before_s)
    np.testing.assert_array_equal(source.z0, before_z0)
    np.testing.assert_array_equal(actual.freqs, source.f)
    assert isinstance(actual, m178.IEEECOMSparam)
    assert actual.source_type == "s4p" and actual.port_order == ORDER
    np.testing.assert_array_equal(actual.network.z0, np.full((3, 2), 92.5))
    # Four-port normalization is a different common-mode boundary.
    four = source.copy()
    four.renormalize(46.25)
    four_sdd = SparamModel.from_network(four, mode="s4p", port_order=ORDER)
    assert np.max(abs(actual.sdd - four_sdd.sdd)) > 1e-6


def test_equal_impedance_and_array_constructors_keep_values():
    source = measurement()
    raw = SparamModel.from_network(source, port_order=ORDER)
    matched = SparamModel.from_network(source, port_order=ORDER, z0=100.0)
    np.testing.assert_array_equal(matched.sdd, raw.sdd)
    assigned = SparamModel.from_s4p_array(source.f, source.s, port_order=ORDER, z0=92.5)
    np.testing.assert_array_equal(assigned.sdd, raw.sdd)
    assigned_sdd = SparamModel.from_network(raw.network, mode="sdd", z0=92.5)
    np.testing.assert_array_equal(assigned_sdd.sdd, raw.sdd)


def test_s4p_first_matches_full_four_port_oracle_without_mutating_source():
    source = measurement()
    before_s, before_z0 = source.s.copy(), source.z0.copy()
    four = source.copy()
    four.renormalize(46.25)
    expected = SparamModel.from_network(four, mode="s4p", port_order=ORDER)
    actual = SparamModel.from_network(
        source, mode="s4p", port_order=ORDER, z0=92.5,
        renormalization_order="s4p_first",
    )
    np.testing.assert_allclose(actual.sdd, expected.sdd, atol=1e-12, rtol=0)
    np.testing.assert_array_equal(actual.network.z0, np.full((3, 2), 92.5))
    np.testing.assert_array_equal(source.s, before_s)
    np.testing.assert_array_equal(source.z0, before_z0)
    assert actual.source_type == "s4p" and actual.port_order == ORDER


def test_s4p_first_rejects_unsupported_impedance_and_mode():
    source = measurement()
    with pytest.raises(ValueError, match="scalar target"):
        SparamModel.from_network(source, mode="s4p", renormalization_order="s4p_first")
    with pytest.raises(ValueError, match="single-ended four-port"):
        SparamModel.from_network(
            SparamModel.from_network(source).network, mode="sdd", z0=92.5,
            renormalization_order="s4p_first",
        )
    nonuniform = source.copy()
    nonuniform.z0[:, 2] = 55.0
    with pytest.raises(ValueError, match="common positive real"):
        SparamModel.from_network(
            nonuniform, mode="s4p", z0=92.5,
            renormalization_order="s4p_first",
        )
    with pytest.raises(ValueError, match="renormalization_order"):
        SparamModel.from_network(source, renormalization_order="unknown")


def test_frequency_limit_keeps_first_measured_point_at_or_above_limit(tmp_path):
    freqs = np.arange(5, dtype=float) * 1e9
    s = np.zeros((len(freqs), 4, 4), dtype=complex)
    source = rf.Network(f=freqs, s=s, z0=50.0)
    source.write_touchstone(str(tmp_path / "limited"))

    limited = SparamModel.from_touchstone(
        str(tmp_path / "limited.s4p"),
        mode="s4p",
        frequency_limit_Hz=2.5e9,
    )
    np.testing.assert_array_equal(limited.freqs, freqs[:4])
    assert limited.freqs[-1] == pytest.approx(3e9)

    complete = SparamModel.from_touchstone(
        str(tmp_path / "limited.s4p"),
        mode="s4p",
        frequency_limit_Hz=10e9,
    )
    np.testing.assert_array_equal(complete.freqs, freqs)

    with pytest.raises(ValueError, match="finite and positive"):
        SparamModel.from_touchstone(
            str(tmp_path / "limited.s4p"), mode="s4p", frequency_limit_Hz=0.0,
        )


@pytest.mark.parametrize("module", [m93, m178])
def test_both_channel_builders_apply_equation(tmp_path, module):
    source = measurement()
    source.write_touchstone(str(tmp_path / "victim"))
    cfg = m93.COMChannelConfig(victim_s4p_path=str(tmp_path / "victim.s4p"),
                              port_order=ORDER, R0=46.25, R_d_tx=46.25, R_d_rx=46.25)
    channels = (module._build_channel_under_test_93A(cfg) if module is m93
                else module._build_channel_under_test(cfg))
    raw = SparamModel.from_network(source, port_order=ORDER)
    np.testing.assert_allclose(channels[0].sdd, equation(raw.sdd), atol=1e-12, rtol=0)


def test_fixed_sicopr_case_equation_and_vtf():
    cfg = excel_to_config_178A(str(ROOT / "cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx"))
    assert cfg.policy.channel_renormalization_order == "s4p_first"
    raw = SparamModel.from_touchstone(cfg.channel.victim_s4p_path,
                                    mode="s4p", port_order=cfg.channel.port_order,
                                    frequency_limit_Hz=cfg.channel.sparam_frequency_limit_Hz)
    channels = m178._build_channel_under_test(cfg.channel, "sdd_first")
    ch = channels[0]
    np.testing.assert_allclose(ch.sdd, equation(raw.sdd), atol=1e-10, rtol=0)
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
    assert cfg.channel.sparam_frequency_limit_Hz == pytest.approx(67e9)
    channels = m178._build_channel_under_test(
        cfg.channel, cfg.policy.channel_renormalization_order,
    )
    paths = [
        cfg.channel.victim_s4p_path,
        *cfg.channel.next_s4p_paths,
        *cfg.channel.fext_s4p_paths,
    ]
    assert len(channels) == len(paths) == 6
    for path, channel in zip(paths, channels):
        assert len(channel.freqs) == 6701
        assert channel.freqs[-1] == pytest.approx(67e9)
        four = rf.Network(path)
        four.renormalize(cfg.channel.R0)
        expected = SparamModel.from_network(
            four, mode="s4p", port_order=cfg.channel.port_order,
        ).limited_to_frequency(cfg.channel.sparam_frequency_limit_Hz)
        np.testing.assert_allclose(channel.sdd, expected.sdd, atol=1e-12, rtol=0)
