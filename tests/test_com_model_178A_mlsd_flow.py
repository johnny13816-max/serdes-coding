"""MLSD block boundaries keep the DER calculation free of status mutation."""

from __future__ import annotations

import unittest

import numpy as np

from serdes_coding.models.com_model_178A import (
    _build_mlsd_sequence_vector,
    _reference_cdf_ev,
    calculate_der_mlsd,
)
from serdes_coding.utilities.pmf import Pmf1D


class TestMLSDFlow178A(unittest.TestCase):
    def test_reference_cdf_uses_first_grid_point_above_negative_threshold(self) -> None:
        pmf = Pmf1D.multi_dirac(
            np.array([-0.2, -0.1, 0.0]),
            np.array([0.2, 0.3, 0.5]),
            dx=0.1,
            placement="nearest",
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


if __name__ == "__main__":
    unittest.main()
