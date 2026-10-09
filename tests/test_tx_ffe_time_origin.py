"""Equation-level checks for the TX FFE main-cursor time origin."""

import numpy as np
import pytest

from serdes_coding.models.com_model_93A import IEEECOMFilter
from serdes_coding.utilities.link import LinkConfig


@pytest.fixture
def cfg() -> LinkConfig:
    return LinkConfig.from_Nfft(fb=8.0, per_ui=4, Nfft=64)


@pytest.mark.parametrize(
    ("taps", "num_pre"),
    [
        (np.array([0.0, 0.0, 0.0, 1.0, 0.0]), 3),
        (np.array([0.0, 1.0, 0.0]), 1),
    ],
)
def test_main_cursor_only_is_unit_transfer(
    cfg: LinkConfig, taps: np.ndarray, num_pre: int
) -> None:
    response = IEEECOMFilter.tx_ffe_93A(cfg, taps, num_pre)
    np.testing.assert_allclose(response.tf, 1.0, rtol=0, atol=1e-14)


def test_symmetric_pre_and_post_taps_have_zero_phase(cfg: LinkConfig) -> None:
    taps = np.array([0.125, 0.75, 0.125])
    response = IEEECOMFilter.tx_ffe_93A(cfg, taps, num_pre=1)
    expected = 0.75 + 0.25 * np.cos(2 * np.pi * cfg.freqs / cfg.fb)
    np.testing.assert_allclose(response.tf, expected, rtol=0, atol=1e-14)


def test_main_cursor_validation_is_preserved(cfg: LinkConfig) -> None:
    with pytest.raises(ValueError, match="main cursor index"):
        IEEECOMFilter.tx_ffe_93A(cfg, np.array([0.0, 1.0, 0.0]), num_pre=0)
