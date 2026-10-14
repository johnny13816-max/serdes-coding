"""Equation-level checks for the Annex 178A MLSD input noise spectrum."""

from __future__ import annotations

import unittest

import numpy as np

from serdes_coding.models.com_model_178A import (
    COM,
    COMAddedNoiseStatus,
    COMEqChannelStatus,
    COMImpairmentStatus,
    COMImpStageStatus,
    COMPSDStatus,
)
from serdes_coding.utilities.link import LinkConfig, SampledResponse
from serdes_coding.utilities.pmf import Pmf1D
from serdes_coding.utilities.psd import SampledPSD


class TestMLSDNoise178A(unittest.TestCase):
    def setUp(self) -> None:
        self.fb = 8.0
        self.grid = LinkConfig.from_Nfft(self.fb, 1, 16)
        self.S_n = SampledPSD.from_constant(self.grid.theta, 0.4 / self.fb, self.fb, cfg=self.grid)
        self.H_rxffe = SampledResponse.from_ir(np.array([1.0, 0.5]), self.grid)
        self.h_ISI = SampledResponse.from_ir(np.array([0.0, 0.2, -0.1]), self.grid)
        self.sigma_X = 0.3
        self.imp = COMImpairmentStatus(
            pre_dte=COMImpStageStatus(
                psd=COMPSDStatus(S_total=self.S_n, sigma_X=self.sigma_X)
            ),
            # Give reporting a deliberately different receiver PSD. Eq. 178A-54
            # must still use the complete pre-FFE S_n.
            post_ffe=COMImpStageStatus(
                psd=COMPSDStatus(
                    S_rn=SampledPSD.from_constant(self.grid.theta, 0.01, self.fb, cfg=self.grid)
                )
            ),
            eq_ch=COMEqChannelStatus(h_ISI=self.h_ISI),
            H_rxffe=self.H_rxffe,
        )
        self.S_an = SampledPSD.from_constant(self.grid.theta, 0.02 / self.fb, self.fb, cfg=self.grid)
        self.added_noise = COMAddedNoiseStatus(
            g_an=0.0,
            S_an=self.S_an,
            sigma_an=0.0,
            p_an=Pmf1D.gaussian(mu=0.0, sigma=0.1, dx=0.01, n_sigma=4),
            delta_com_an_temp=0.0,
        )

    def test_eq54_source_folding_and_parseval(self) -> None:
        result = COM.__new__(COM).build_mlsd_noise(self.imp, self.added_noise)

        # Eq. 178A-54 specifies a two-sided density. Only interior rFFT bins
        # double when represented by SampledPSD's one-sided samples.
        expected_isi = (
            self.sigma_X**2 / self.fb * self.h_ISI.magnitude_squared()
        )
        expected_isi[1:-1] *= 2.0
        np.testing.assert_allclose(result.S_isi.psd, expected_isi, rtol=1e-12, atol=1e-15)
        expected_isi_variance = self.sigma_X**2 * np.sum(self.h_ISI.ir**2)
        self.assertAlmostEqual(result.sigma_isi**2, expected_isi_variance, places=14)
        self.assertAlmostEqual(result.S_isi.to_autocorrelation()[0], expected_isi_variance, places=14)

        expected_n = self.S_n.psd * self.H_rxffe.magnitude_squared()
        np.testing.assert_allclose(
            result.S_ni.psd,
            expected_n + self.S_an.psd + expected_isi,
            rtol=1e-12,
            atol=1e-15,
        )
        np.testing.assert_allclose(result.R_ni, result.S_ni.to_autocorrelation(), rtol=1e-12, atol=1e-15)

    def test_pre_ffe_source_must_cover_post_ffe_grid(self) -> None:
        shifted = SampledPSD(
            theta=self.S_n.theta[1:],
            psd=self.S_n.psd[1:],
            fb=self.fb,
        )
        self.imp.pre_dte.psd.S_total = shifted
        with self.assertRaisesRegex(ValueError, "pre-FFE S_n must share"):
            COM.__new__(COM).build_mlsd_noise(self.imp, self.added_noise)

    def test_added_noise_must_share_post_ffe_grid(self) -> None:
        other_grid = LinkConfig.from_Nfft(self.fb, 1, 8)
        self.added_noise.S_an = SampledPSD.from_constant(other_grid.theta, 0.02 / self.fb, self.fb)
        with self.assertRaisesRegex(ValueError, "added_noise.S_an must share"):
            COM.__new__(COM).build_mlsd_noise(self.imp, self.added_noise)


if __name__ == "__main__":
    unittest.main()
