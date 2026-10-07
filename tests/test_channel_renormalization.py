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
    raw = SparamModel.from_touchstone(cfg.channel.victim_s4p_path,
                                    mode="s4p", port_order=cfg.channel.port_order)
    channels = m178._build_channel_under_test(cfg.channel)
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
