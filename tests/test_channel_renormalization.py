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
def test_differential_domain_renormalization_is_explicit_and_preserves_raw_s4p(representation):
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


def test_single_ended_domain_renormalization_matches_four_port_oracle_without_mutation():
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
        raw.s2p_to_synthetic_s4p(
            target_z0_diff=100.0, reader_port_order=ORDER,
        )


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


def test_93a_channel_builder_keeps_differential_domain_equation(tmp_path):
    source = measurement()
    source.write_touchstone(str(tmp_path / "victim"))
    cfg = m93.COMChannelConfig(
        victim_s4p_path=str(tmp_path / "victim.s4p"), port_order=ORDER,
        R0=46.25, R_d_tx=46.25, R_d_rx=46.25,
    )
    channels = m93._build_channel_under_test_93A(cfg)
    measured_sdd = SparamModel.from_network(source, port_order=ORDER).s4p_to_s2p()
    np.testing.assert_allclose(channels[0].sdd, equation(measured_sdd.sdd), atol=1e-12, rtol=0)


def test_178a_s4p_input_uses_d3p2_single_ended_first_order(tmp_path):
    source = measurement()
    source.write_touchstone(str(tmp_path / "victim"))
    cfg = m178.COMChannelConfig(
        victim_s4p_path=str(tmp_path / "victim.s4p"), port_order=ORDER,
        R0=46.25, R_d_tx=46.25, R_d_rx=46.25,
    )
    expected = (
        SparamModel.from_network(source, representation="s4p")
        .renormalized(46.25)
        .s4p_to_s2p(ORDER)
    )
    actual = m178._build_channel_under_test(cfg)[0]
    np.testing.assert_allclose(actual.sdd, expected.sdd, atol=1e-12, rtol=0)


def test_178a_native_s2p_input_renormalizes_in_differential_domain(tmp_path):
    source = SparamModel.from_network(measurement(), port_order=ORDER).s4p_to_s2p()
    source.network.write_touchstone(str(tmp_path / "victim"))
    cfg = m178.COMChannelConfig(
        victim_s4p_path=str(tmp_path / "victim.s2p"), port_order=ORDER,
        R0=46.25, R_d_tx=46.25, R_d_rx=46.25,
    )
    actual = m178._build_channel_under_test(cfg)[0]
    expected = SparamModel.from_network(source.network).renormalized(92.5)
    np.testing.assert_allclose(actual.sdd, expected.sdd, atol=1e-12, rtol=0)
    assert [operation.name for operation in actual.history] == [
        "renormalized", "resampled",
    ]


def test_178a_dispatches_mixed_s4p_and_s2p_collection_per_file(tmp_path):
    four_port = measurement()
    four_port.write_touchstone(str(tmp_path / "victim"))
    two_port = SparamModel.from_network(four_port, port_order=ORDER).s4p_to_s2p()
    two_port.network.write_touchstone(str(tmp_path / "next"))
    cfg = m178.COMChannelConfig(
        victim_s4p_path=str(tmp_path / "victim.s4p"),
        next_s4p_paths=(str(tmp_path / "next.s2p"),),
        port_order=ORDER, R0=46.25, R_d_tx=46.25, R_d_rx=46.25,
    )
    victim, next_channel = m178._build_channel_under_test(cfg)
    expected_victim = (
        SparamModel.from_network(four_port).renormalized(46.25).s4p_to_s2p(ORDER)
    )
    expected_next = SparamModel.from_network(two_port.network).renormalized(92.5)
    np.testing.assert_allclose(victim.sdd, expected_victim.sdd, atol=1e-12, rtol=0)
    np.testing.assert_allclose(next_channel.sdd, expected_next.sdd, atol=1e-12, rtol=0)


def test_178a_rejects_unsupported_touchstone_without_fallback(tmp_path):
    source = rf.Network(
        f=[0, 1e9, 2e9], s=np.zeros((3, 3, 3), dtype=complex), z0=50.0,
    )
    source.write_touchstone(str(tmp_path / "victim"))
    cfg = m178.COMChannelConfig(
        victim_s4p_path=str(tmp_path / "victim.s3p"),
        R0=46.25, R_d_tx=46.25, R_d_rx=46.25,
    )
    with pytest.raises(ValueError, match="Only differential two-port and single-ended four-port"):
        m178._build_channel_under_test(cfg)


def test_fixed_sicopr_case_d3p2_order_closes_all_channel_matrices():
    cfg = excel_to_config_178A(str(ROOT / "cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx"))
    channels = m178._build_channel_under_test(cfg.channel)
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
