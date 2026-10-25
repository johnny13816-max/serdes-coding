"""Numerical ownership boundary for the final 178A-local helper migration."""

import hashlib

import numpy as np

from serdes_coding.models import com_model_178A as model
from serdes_coding.models.com_178a import COMPMFRuntimeConfig
from serdes_coding.utilities.pmf import Pmf1D


def _pmf_config() -> COMPMFRuntimeConfig:
    return COMPMFRuntimeConfig(
        dy=0.05,
        tap_abs_th=0.0,
        keep_mass=1.0,
        gaussian_n_sigma=8.0,
    )


def _quantized_digest(values: np.ndarray) -> str:
    frozen = np.ascontiguousarray(np.round(np.asarray(values, dtype=float), 12))
    return hashlib.sha256(frozen.tobytes()).hexdigest()


def test_178a_owns_crosstalk_worst_phase_search() -> None:
    response = np.array(
        [0.1, -0.2, 0.7, 0.3, -0.4, 0.05, 0.2, -0.1, 0.6, 0.4, -0.3, 0.02]
    )

    phase, sampled = model._find_pos_xtalk(response, 4)

    assert phase == 2
    np.testing.assert_array_equal(sampled, np.array([0.7, 0.2, -0.3]))


def test_178a_signal_fir_pmf_preserves_frozen_output() -> None:
    cfg = _pmf_config()
    signal = Pmf1D.multi_dirac(np.array([-1.0, 1.0]), dx=cfg.dy)

    result = model._build_pmf_interference_178A(
        signal,
        np.array([0.25, -0.1, 0.05]),
        cfg,
        4,
        method="signal_fir",
        name="a",
    )

    assert result.st_idx == -8
    assert _quantized_digest(result.pmf) == (
        "f6f21514d7171464bd71a7d1249261f864b68d71ae124f11cc10a993f7b4ed4e"
    )


def test_178a_signal_fir_xtalk_accumulation_preserves_frozen_output() -> None:
    cfg = _pmf_config()
    signal = Pmf1D.multi_dirac(np.array([-1.0, 1.0]), dx=cfg.dy)

    result = model._build_pmf_w_XT_all(
        signal,
        [np.array([0.2, -0.05]), np.array([0.1, 0.03])],
        cfg,
        L=4,
    )

    assert result.st_idx == -8
    assert _quantized_digest(result.pmf) == (
        "fee7348b92674e9b8096d634fc1894a531764a64392f9c501ee9e902cb2c2f56"
    )
