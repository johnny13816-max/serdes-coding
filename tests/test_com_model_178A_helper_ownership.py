"""Numerical ownership boundary for the final 178A-local helper migration."""

import hashlib
import inspect

import numpy as np

from serdes_coding.models import com_model_178A as model
from serdes_coding.models.com_178a import COMPMFRuntimeConfig


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


def test_pmf_helpers_receive_concrete_methods_not_algorithm_config() -> None:
    helpers = (
        model._calculate_V_qc,
        model._build_psd_adc_qn,
        model._build_adc_input_pmf_exact,
        model._reconstruct_final_vqc_sicopr,
    )

    for helper in helpers:
        parameters = inspect.signature(helper).parameters
        assert "pmf_methods" not in parameters
        assert parameters["pmf_projection_method"].default == "linear"
        assert parameters["pdf_to_pmf_method"].default == "bin_integral"


def test_178a_owns_crosstalk_worst_phase_search() -> None:
    response = np.array(
        [0.1, -0.2, 0.7, 0.3, -0.4, 0.05, 0.2, -0.1, 0.6, 0.4, -0.3, 0.02]
    )

    phase, sampled = model._select_xtalk_path_phase(response, 4)

    assert phase == 2
    np.testing.assert_array_equal(sampled, np.array([0.7, 0.2, -0.3]))


def test_178a_pam4_source_preserves_exact_atoms_on_natural_grid() -> None:
    signal = model._build_pmf_pam_L(4)

    np.testing.assert_allclose(
        signal.x, np.arange(-3, 4) / 3.0, rtol=0.0, atol=2e-16,
    )
    np.testing.assert_allclose(
        signal.pmf, [0.25, 0.0, 0.25, 0.0, 0.25, 0.0, 0.25],
        rtol=0.0, atol=0.0,
    )
    assert signal.unit == "normalized symbol"
    assert not hasattr(signal, "placement")


def test_178a_exact_atom_fir_pmf_preserves_frozen_output() -> None:
    cfg = _pmf_config()
    signal = model._build_pmf_pam_L(4)

    result = model._build_pmf_interference_178A(
        signal,
        np.array([0.25, -0.1, 0.05]),
        cfg,
        projection_method="linear",
        name="a",
    )

    assert result.st_idx == -7
    assert _quantized_digest(result.pmf) == (
        "9cdc4d7c6cf9b99833bd4b02d8df3b0bee18806dcf1774aaba57b97010e3cb72"
    )


def test_178a_exact_atom_xtalk_accumulation_preserves_frozen_output() -> None:
    cfg = _pmf_config()
    signal = model._build_pmf_pam_L(4)

    result = model._build_pmf_w_XT_all(
        signal,
        [np.array([0.2, -0.05]), np.array([0.1, 0.03])],
        cfg,
        projection_method="linear",
    )

    assert result.st_idx == -6
    assert _quantized_digest(result.pmf) == (
        "78efbea8910a6819651a3c0869e570bcbf3d166bd0baf8d3761ab87bafebb6fd"
    )
