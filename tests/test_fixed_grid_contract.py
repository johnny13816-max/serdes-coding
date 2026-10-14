"""Fixed-grid convolution invariants and overflow classification."""

import numpy as np
import pytest

from serdes_coding.utilities.link import (
    GridOverflowError,
    LinkConfig,
    LinkSegment,
    SampledResponse,
)
from serdes_coding.utilities.psd import ContinuousPSD, SampledPSD


def test_sampled_tf_and_linear_ir_cascades_close_on_one_config():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=32)
    a = SampledResponse.from_ir(np.array([1.0, 0.25]), cfg)
    b = SampledResponse.from_ir(np.array([0.5, -0.1, 0.03]), cfg)
    ir_cascade = a.cascade_ir(b)
    tf_cascade = a.cascade_tf(b)
    assert ir_cascade.cfg is tf_cascade.cfg is cfg
    expected = np.zeros(cfg.sampled_nfft)
    expected[:4] = np.convolve(a.ir[:2], b.ir[:3])
    np.testing.assert_allclose(ir_cascade.ir, expected, atol=1e-14)
    np.testing.assert_allclose(ir_cascade.tf, tf_cascade.tf, atol=1e-14)


def test_sampled_overflow_rejects_circular_alias_and_diagnostic_keeps_full_result():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=8)
    first = np.zeros(8)
    first[0], first[-1] = 1.0, 0.5
    a = SampledResponse.from_ir(first, cfg)
    b = SampledResponse.from_ir(np.array([0.0, 1.0]), cfg)
    with pytest.raises(GridOverflowError) as caught:
        a.cascade_ir(b)
    error = caught.value
    assert error.grid_length == 8 and error.full_length == 9
    assert error.peak_ratio == pytest.approx(0.5)
    full = a.cascade_ir(b, force_grid=False)
    assert full.cfg is not cfg and full.ir[8] == pytest.approx(0.5)


def test_known_finite_taps_require_exact_capacity_even_for_a_small_tail():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=8)
    a = SampledResponse.from_ir(np.array([1.0, 0, 0, 0, 0, 0, 1e-6]), cfg)
    b = SampledResponse.from_ir(np.array([1.0, 0, 1.0]), cfg)
    with pytest.raises(GridOverflowError) as caught:
        a.cascade_ir(b)
    assert caught.value.exact_support_exceeded


def test_continuous_ir_cascade_keeps_config_and_dt_scaling():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=32)
    a = LinkSegment.from_ir(np.r_[1.0, 0.25, np.zeros(30)], cfg)
    b = LinkSegment.from_ir(np.r_[0.5, 0.1, np.zeros(30)], cfg)
    ir_cascade = a.cascade_ir(b)
    assert ir_cascade.cfg is cfg
    np.testing.assert_allclose(ir_cascade.ir[:3],
                               np.convolve(a.ir[:2], b.ir[:2]) * cfg.dt,
                               atol=1e-12)


def test_sampled_psd_requires_same_bound_config_and_preserves_parseval():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=16)
    other_cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=16)
    psd = SampledPSD.from_constant(cfg.theta, 0.2, cfg.fb, cfg=cfg)
    response = SampledResponse.from_ir(np.array([1.0, 0.5]), cfg)
    filtered = psd.filtered_by(response)
    assert filtered.cfg is cfg
    assert filtered.to_sigma() ** 2 == pytest.approx(filtered.to_autocorrelation()[0])
    with pytest.raises(ValueError, match="same LinkConfig reference"):
        psd.filtered_by(SampledResponse.from_ir(np.array([1.0]), other_cfg))


def test_continuous_psd_alignment_and_sampling_propagate_run_config():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=16)
    measured = ContinuousPSD.from_constant(np.array([0.0, 4.0]), 0.2)
    aligned = measured.aligned_to(cfg)
    assert aligned.cfg is cfg
    sampled = aligned.to_sampled(cfg.fb, cfg.theta)
    assert sampled.cfg is cfg
