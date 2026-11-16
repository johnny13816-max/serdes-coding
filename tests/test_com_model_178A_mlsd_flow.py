"""MLSD block boundaries keep the DER calculation free of status mutation."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

from serdes_coding.models.com_model_178A import (
    COM,
    COMPMFStatus,
    COMPMFRuntimeConfig,
    _build_scaled_total_pdf_added_noise,
    solve_g_an,
    _build_mlsd_sequence_vector,
    _reference_cdf_ev,
    calculate_der_mlsd,
)
from serdes_coding.utilities.pmf import Pmf1D
from serdes_coding.utilities.psd import SampledPSD


def test_reference_added_noise_uses_raw_second_moment_for_nonzero_mean():
    source = Pmf1D(dx=1.0, st_idx=-2, pmf=np.array([0.05, 0.1, 0.15, 0.3, 0.4]))
    receiver = SampledPSD.from_constant(np.linspace(0, np.pi, 5), 0.1, 8.0)
    post = SimpleNamespace(psd=SimpleNamespace(S_rn=receiver, sigma_G=0.1))
    result = _build_scaled_total_pdf_added_noise(
        20 * np.log10(2.0), post, COMPMFStatus(dy=1.0, tap_abs_th=0.0, p_combined=source), 0.05,
        scaling_method="interpolate_ordinates", projection_method="linear",
    )
    expected = 4.985714285714285 / receiver.to_sigma() ** 2
    np.testing.assert_allclose(result.g_an, expected, rtol=0, atol=1e-12)
    assert not np.isclose(result.g_an, 3.875510204081632 / receiver.to_sigma() ** 2)


def test_added_noise_owner_selects_both_complete_results():
    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(
        mlsd=SimpleNamespace(resolved_delta_com_an=lambda: 1.0), DER_0=0.001,
        alg=SimpleNamespace(added_noise_pdf="gaussian_addition", pmf_scaling_method="mass_deposit",
                            pmf_projection_method="linear", pdf_to_pmf_method="bin_integral"),
    )
    post, pmf, cfg = object(), object(), object()
    with patch("serdes_coding.models.com_model_178A.solve_g_an") as solve, patch(
        "serdes_coding.models.com_model_178A._build_scaled_total_pdf_added_noise"
    ) as scale:
        assert model._build_mlsd_added_noise(post, pmf, cfg) is solve.return_value
        solve.assert_called_once_with(1.0, post, pmf, cfg, 0.001, pdf_to_pmf_method="bin_integral")
        scale.assert_not_called()
        model.cfg.alg.added_noise_pdf = "scaled_total_pdf"
        assert model._build_mlsd_added_noise(post, pmf, cfg) is scale.return_value
        scale.assert_called_once_with(1.0, post, pmf, 0.001,
                                      scaling_method="mass_deposit", projection_method="linear")
        model.cfg.alg.added_noise_pdf = "invalid"
        with np.testing.assert_raises_regex(ValueError, "added_noise_pdf"):
            model._build_mlsd_added_noise(post, pmf, cfg)


def test_gaussian_owner_matches_existing_solver():
    receiver = SampledPSD.from_constant(np.linspace(0, np.pi, 5), 0.1, 8.0)
    post = SimpleNamespace(psd=SimpleNamespace(S_rn=receiver, sigma_G=0.1))
    cfg = COMPMFRuntimeConfig(dy=0.01, tap_abs_th=0.0, keep_mass=1.0, gaussian_n_sigma=8.0)
    impulse = Pmf1D(dx=0.01, st_idx=0, pmf=np.array([1.0]))
    gaussian = Pmf1D.gaussian(mu=0.0, sigma=0.1, dx=0.01, n_sigma=8.0, unit="volt")
    pmf = COMPMFStatus(dy=0.01, tap_abs_th=0.0, p_ISI=impulse, p_XT=impulse,
                       p_DD=impulse, p_qn=impulse, p_combined=gaussian)
    model = COM.__new__(COM)
    model.cfg = SimpleNamespace(
        mlsd=SimpleNamespace(resolved_delta_com_an=lambda: 0.0), DER_0=0.01,
        alg=SimpleNamespace(added_noise_pdf="gaussian_addition", pdf_to_pmf_method="bin_integral"),
    )
    baseline = solve_g_an(0.0, post, pmf, cfg, 0.01)
    result = model._build_mlsd_added_noise(post, pmf, cfg)
    assert result.g_an == baseline.g_an
    assert result.delta_com_an_temp == baseline.delta_com_an_temp
    np.testing.assert_array_equal(result.p_an.pmf, baseline.p_an.pmf)


class TestMLSDFlow178A(unittest.TestCase):
    def test_reference_cdf_uses_first_grid_point_above_negative_threshold(self) -> None:
        pmf = Pmf1D.multi_dirac(
            np.array([-0.2, -0.1, 0.0]),
            np.array([0.2, 0.3, 0.5]),
            dx=0.1,
        )
        self.assertAlmostEqual(_reference_cdf_ev(pmf, 0.15), 0.5, places=15)

    def test_eq178a49_uses_one_based_last_element_index(self) -> None:
        b_1 = 0.25
        np.testing.assert_allclose(
            _build_mlsd_sequence_vector(1, b_1),
            np.array([1.0, b_1]),
        )
        np.testing.assert_allclose(
            _build_mlsd_sequence_vector(2, b_1),
            np.array([1.0, -(1.0 - b_1), -b_1]),
        )
        np.testing.assert_allclose(
            _build_mlsd_sequence_vector(3, b_1),
            np.array([1.0, -(1.0 - b_1), 1.0 - b_1, b_1]),
        )

    def test_der_block_reads_only_pdf_and_autocorrelation(self) -> None:
        p_an = Pmf1D.gaussian(mu=0.0, sigma=0.1, dx=0.01, n_sigma=5)
        R_ni = np.array([0.04, 0.004, 0.001], dtype=float)
        pmf_before = p_an.pmf.copy()
        R_before = R_ni.copy()

        der, terms = calculate_der_mlsd(
            p_an, R_ni, L=4, As=0.3, b_lim_1=0.5, trunc_len=2
        )

        self.assertEqual(terms.shape, (2,))
        self.assertAlmostEqual(der, float(np.sum(terms)), places=15)
        np.testing.assert_array_equal(p_an.pmf, pmf_before)
        np.testing.assert_array_equal(R_ni, R_before)
        self.assertFalse(hasattr(p_an, "DER_MLSD"))

    def test_eq52_positive_feedback_scaling_with_asymmetric_pdf(self) -> None:
        # An asymmetric PDF exposes the sign in Eq. 178A-52. With V_1=I,
        # choosing A_s this way makes the j=1 CDF threshold exactly -0.3.
        p_an = Pmf1D.multi_dirac(
            np.array([-0.2, 0.4]), np.array([0.9, 0.1]), dx=0.001
        )
        b_1 = 0.84
        As = 0.3 / (1.0 + b_1**2)
        R_ni = np.array([1.0, 0.0])

        der, terms = calculate_der_mlsd(
            p_an, R_ni, L=4, As=As, b_lim_1=b_1, trunc_len=1
        )
        p_1_spec = p_an.combine(
            p_an.scale_x(b_1, keep_dx=True, dx_ref=p_an.dx)
        )
        expected = float(p_1_spec.cdf_at(-0.3))
        self.assertAlmostEqual(expected, 0.81, places=12)
        self.assertAlmostEqual(der, expected, places=12)
        self.assertAlmostEqual(terms[0], expected, places=12)

    def test_der_block_accepts_negative_feedback_with_ordinate_scaling(self) -> None:
        p_an = Pmf1D(
            dx=0.1,
            st_idx=-2,
            pmf=np.array([0.05, 0.15, 0.5, 0.2, 0.1]),
        )
        der, terms = calculate_der_mlsd(
            p_an,
            np.array([1.0, 0.0]),
            L=4,
            As=0.1,
            b_lim_1=-0.5,
            trunc_len=1,
            pmf_scaling_method="interpolate_ordinates",
        )

        self.assertAlmostEqual(der, 1.0 / 12.0, places=15)
        np.testing.assert_allclose(terms, np.array([der]), rtol=0.0, atol=1e-15)


if __name__ == "__main__":
    unittest.main()
