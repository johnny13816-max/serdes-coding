import numpy as np
import pytest

from serdes_coding.utilities.link import LinkConfig, LinkSegment


@pytest.fixture
def segment():
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=32)
    ir = np.zeros(cfg.Nfft)
    ir[3], ir[5], ir[8], ir[12] = 0.01, -1.0, 0.1, 0.02
    return LinkSegment.from_ir(ir, cfg)


def test_effective_range_is_half_open_and_bilateral(segment):
    assert segment.effective_range(relative_threshold=0.05) == (5, 9)
    assert segment.effective_length(relative_threshold=0.05) == 4


def test_effective_thresholds_use_or_and_strict_comparison(segment):
    assert segment.effective_range(relative_threshold=0.2, absolute_threshold=0.015) == (5, 13)
    assert segment.effective_range(absolute_threshold=1.0) == (0, 0)
    assert segment.effective_length(absolute_threshold=1.0) == 0


def test_no_threshold_keeps_entire_record(segment):
    assert segment.effective_range() == (0, segment.cfg.Nfft)
    assert segment.effective_length() == segment.cfg.Nfft


@pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
@pytest.mark.parametrize("name", ["relative_threshold", "absolute_threshold"])
def test_effective_threshold_rejects_invalid_values(segment, name, value):
    with pytest.raises(ValueError, match=name):
        segment.effective_range(**{name: value})


def test_raw_ir_does_not_choose_a_separate_causal_shift(monkeypatch):
    cfg = LinkConfig.from_Nfft(fb=8.0, per_ui=1, Nfft=32)
    tf = np.ones(len(cfg.freqs), dtype=complex)
    segment = LinkSegment.from_tf(cfg.freqs, tf, cfg)
    def forbidden(*args, **kwargs):
        raise AssertionError("raw access must not choose causal alignment")
    monkeypatch.setattr(segment, "causalize_ir", forbidden)
    expected = np.fft.irfft(tf, n=cfg.Nfft) * cfg.Fs
    np.testing.assert_array_equal(segment.raw_ir, expected)
    with pytest.raises(AssertionError, match="causal alignment"):
        _ = segment.ir
