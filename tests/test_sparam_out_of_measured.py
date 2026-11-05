import numpy as np
import pytest

from serdes_coding.utilities.link import LinkConfig
from serdes_coding.utilities.sparam import SparamModel


def test_sparam_to_linksegment_owns_measured_band_extension():
    cfg = LinkConfig(fb=2.0, per_ui=2, target_df=0.1)
    measured_freqs = np.array([0.0, 0.5, 1.0])
    sdd = np.zeros((measured_freqs.size, 2, 2), dtype=complex)
    sdd[:, 1, 0] = [0.8, 0.7 - 0.1j, 0.6 - 0.2j]
    model = SparamModel.from_sdd_array(measured_freqs, sdd, z0=100.0)

    cosine = model.to_LinkSegment(cfg, out_of_measured="cosine_decay")
    zero = model.to_LinkSegment(cfg, out_of_measured="zero_padding")
    default = model.to_LinkSegment(cfg)
    in_band = cfg.freqs <= measured_freqs[-1]
    beyond = ~in_band

    np.testing.assert_array_equal(cosine.tf, default.tf)
    np.testing.assert_array_equal(zero.tf[in_band], cosine.tf[in_band])
    np.testing.assert_array_equal(zero.tf[beyond], 0.0)
    assert np.any(np.abs(cosine.tf[beyond]) > 0.0)
    np.testing.assert_array_equal(model.sdd, sdd)

    with pytest.raises(ValueError, match="out_of_measured"):
        model.to_LinkSegment(cfg, out_of_measured="invalid")


def _scalar_sparam(freqs, response):
    sdd = np.zeros((len(freqs), 2, 2), dtype=complex)
    sdd[:, 1, 0] = response
    return SparamModel.from_sdd_array(np.asarray(freqs), sdd, z0=100.0)


def test_completed_voltage_transfer_function_missing_dc_policies():
    freqs = np.arange(1.0, 13.0) * 1e9
    magnitude = 0.9 - 0.01 * (freqs / 1e9)
    delay = 18e-12
    response = magnitude * np.exp(-1j * 2.0 * np.pi * freqs * delay)
    model = _scalar_sparam(freqs, response)

    with pytest.raises(ValueError, match="must include DC"):
        model.completed_voltage_transfer_function(dc="error")

    hold_freqs, hold = model.completed_voltage_transfer_function(dc="hold")
    np.testing.assert_array_equal(hold_freqs, np.r_[0.0, freqs])
    np.testing.assert_array_equal(hold[1:], response)
    assert hold[0] == response[0]

    trend_freqs, trend = model.completed_voltage_transfer_function(
        dc="mag_phase_trend_to_dc"
    )
    np.testing.assert_array_equal(trend_freqs, np.r_[0.0, freqs])
    np.testing.assert_array_equal(trend[1:], response)
    np.testing.assert_allclose(trend[0], 0.9 + 0j, rtol=0.0, atol=2e-15)

    skrf_freqs, skrf_response = model.completed_voltage_transfer_function(dc="skrf")
    assert skrf_freqs[0] == 0.0
    assert skrf_response.shape == skrf_freqs.shape
    assert np.all(np.isfinite(skrf_response))

    with pytest.raises(ValueError, match="dc must be"):
        model.completed_voltage_transfer_function(dc="unknown")


def test_completed_voltage_transfer_function_preserves_existing_dc():
    freqs = np.arange(0.0, 5.0) * 1e9
    response = (0.8 - 0.02 * freqs / 1e9) * np.exp(-1j * freqs * 1e-11)
    model = _scalar_sparam(freqs, response)

    for method in ("error", "hold", "skrf", "mag_phase_trend_to_dc"):
        completed_freqs, completed = model.completed_voltage_transfer_function(dc=method)
        np.testing.assert_array_equal(completed_freqs, freqs)
        np.testing.assert_array_equal(completed, response)
