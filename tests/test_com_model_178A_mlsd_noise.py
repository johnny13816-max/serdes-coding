"""Equation-level checks for the Annex 178A MLSD PSD owner."""

from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np
from unittest.mock import patch

from serdes_coding.models import com_model_178A as model_module

from serdes_coding.models.com_model_178A import (
    COM,
    COMAdcInputPMF,
    COMAddedNoiseStatus,
    COMAlgorithmPolicyConfig,
    COMEqChannelStatus,
    COMImpStageStatus,
    COMImpairmentStatus,
    COMNumericalControlConfig,
    COMPostFFEEqChannelStatus,
    COMPreDTEEqChannelStatus,
    COMPSDStatus,
)
from serdes_coding.utilities.link import LinkConfig, SampledResponse
from serdes_coding.utilities.pmf import Pmf1D
from serdes_coding.utilities.psd import SampledPSD


class TestMLSDNoise178A(unittest.TestCase):
    def setUp(self) -> None:
        self.fb = 8.0
        self.grid = LinkConfig.from_Nfft(self.fb, 1, 16)
        self.sigma_X = 0.3
        self.h_rxffe = SampledResponse.from_ir(np.array([1.0, 0.5]), self.grid)
        self.h_isi = SampledResponse.from_ir(np.array([0.0, 0.2, -0.1]), self.grid)
        self.eq_ch = COMEqChannelStatus(
            phase_index=0,
            pre_dte=COMPreDTEEqChannelStatus(
                h_dsamp=SampledResponse.from_ir(np.array([1.0, 0.2]), self.grid),
                h_XTs_dsamp=[SampledResponse.from_ir(np.array([0.1, -0.05]), self.grid)],
                h_tn=SampledResponse.from_ir(np.array([0.2, 0.1]), self.grid),
                h_J=SampledResponse.from_ir(np.array([0.3, -0.1]), self.grid),
            ),
            post_ffe=COMPostFFEEqChannelStatus(
                h_ISI=self.h_isi,
            ),
        )
        self.imp = COMImpairmentStatus(
            pre_dte=COMImpStageStatus(
                record_cfg=self.grid,
                psd=COMPSDStatus(sigma_X=self.sigma_X),
                adc_input=COMAdcInputPMF(delta=0.2, method="pmf_exact"),
            ),
        )
        arbitrary_s_an = SampledPSD.from_constant(
            self.grid.theta, 0.02 / self.fb, self.fb, cfg=self.grid
        )
        self.added_noise = COMAddedNoiseStatus(
            g_an=0.5,
            S_an=arbitrary_s_an,
            sigma_an=0.0,
            p_an=Pmf1D.gaussian(mu=0.0, sigma=0.1, dx=0.01, n_sigma=4),
            delta_com_an_temp=0.0,
        )
        self.dte = SimpleNamespace(
            H_rxffe=self.h_rxffe,
            w_lim=np.array([1.0, 0.5]),
        )
        self.model = COM.__new__(COM)
        self.model.cfg = SimpleNamespace(
            link=self.grid,
            L=4,
            alg=COMAlgorithmPolicyConfig(),
            num=COMNumericalControlConfig(),
            dte=SimpleNamespace(d_w=0),
            imp=SimpleNamespace(
                eta_0=0.0,
                SNR_TX=20.0,
                A_DD=0.1,
                sigma_RJ=0.02,
                R_LM=0.6,
                N_qb=6,
                P_qc=0.01,
            ),
            filter=SimpleNamespace(
                fr=4.0,
                g_1=0.0,
                g_2=0.0,
                f_z1=1.0,
                f_z2=2.0,
                f_p1=1.0,
                f_p2=2.0,
                f_p3=3.0,
            ),
        )

    def test_eq54_uses_one_full_record_and_preserves_parseval(self) -> None:
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        self.assertIs(result.record_cfg, self.grid)
        self.assertIs(result.S_isi.cfg, self.grid)
        self.assertIs(result.S_ni.cfg, self.grid)
        expected_isi_variance = self.sigma_X**2 * np.sum(self.h_isi.ir**2)
        self.assertAlmostEqual(result.sigma_isi**2, expected_isi_variance, places=14)
        np.testing.assert_allclose(
            result.R_ni, result.S_ni.to_autocorrelation(), rtol=1e-12, atol=1e-15
        )

    def test_reference_quantization_recomputes_white_noise(self) -> None:
        self.model.cfg.alg = COMAlgorithmPolicyConfig(
            mlsd_quantization_psd="main_tap_white"
        )
        self.model.cfg.num.adc_input_pmf_grid.dy_override = 0.02
        self.eq_ch.pre_dte.h_dsamp = SampledResponse.from_ir(np.array([1.0]), self.grid)
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        # Independent signal-PDF and SiCoPR slow-clipping calculation.
        sigma_x2 = self.sigma_X**2
        s_xt = model_module._build_psd_from_DFT_response(
            self.eq_ch.pre_dte.h_XTs_dsamp[0].ir, self.grid, sigma_x2)
        s_tx = model_module._build_psd_from_DFT_response(
            self.eq_ch.pre_dte.h_tn.ir, self.grid, 10**(-self.model.cfg.imp.SNR_TX / 10))
        s_rj = model_module._build_psd_from_DFT_response(
            self.eq_ch.pre_dte.h_J.ir, self.grid, sigma_x2 * self.model.cfg.imp.sigma_RJ**2)
        s_rx = model_module._build_psd_rx_noise(self.grid, self.model.cfg.imp, self.model.cfg.filter)
        sigma = s_rx.add(s_xt).add(s_tx).add(s_rj).filtered_by(self.h_rxffe).to_sigma()
        indices = np.array([-50, -17, 17, 50])
        signal = np.zeros(101)
        signal[indices + 50] = 0.25
        axis = np.arange(-50, 51) * 0.02
        gaussian = np.exp(-0.5 * (axis / sigma)**2) * 0.02 / (np.sqrt(2 * np.pi) * sigma)
        cdf = np.cumsum(np.convolve(signal, gaussian))
        clip = -(-100 + np.searchsorted(cdf, 0.01)) * 0.02
        delta = 2 * clip / (2**6 - 1)
        density = (delta**2 / 12.0) / self.fb
        expected = SampledPSD.from_constant(
            self.grid.theta, density, self.fb, cfg=self.grid
        ).psd
        np.testing.assert_allclose(result.S_qn.psd, expected, rtol=1e-12, atol=1e-15)

    def test_reference_clipping_preserves_unnormalized_gaussian(self) -> None:
        self.model.cfg.alg = COMAlgorithmPolicyConfig(
            mlsd_quantization_psd="main_tap_white"
        )
        self.model.cfg.num.adc_input_pmf_grid.dy_override = 0.02
        self.model.cfg.imp.SNR_TX = -20.0
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        # SiCoPR common-input oracle: Gaussian mass 0.32642328575429935,
        # unnormalized lower-tail clipping value 1.9 V.
        delta = 2 * 1.9 / 63
        expected = SampledPSD.from_constant(
            self.grid.theta, delta**2 / 12 / self.fb, self.fb, cfg=self.grid
        )
        np.testing.assert_allclose(result.S_qn.psd, expected.psd, rtol=1e-12, atol=1e-15)

    def test_reference_quantization_disabled(self) -> None:
        self.model.cfg.alg = COMAlgorithmPolicyConfig(
            mlsd_quantization_psd="main_tap_white"
        )
        self.imp.pre_dte.adc_input.delta = None
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        np.testing.assert_array_equal(result.S_qn.psd, np.zeros_like(result.S_qn.psd))

    def test_reference_quantization_scales_with_ffe_gain(self) -> None:
        self.model.cfg.alg = COMAlgorithmPolicyConfig(
            mlsd_quantization_psd="main_tap_white"
        )
        self.model.cfg.num.adc_input_pmf_grid.dy_override = 0.02
        baseline = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        self.dte.w_lim = self.dte.w_lim * 2.0
        scaled = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        np.testing.assert_allclose(scaled.S_qn.psd, 4 * baseline.S_qn.psd, rtol=1e-12, atol=1e-15)

    def test_reference_quantization_rejects_zero_main_gain(self) -> None:
        self.model.cfg.alg = COMAlgorithmPolicyConfig(
            mlsd_quantization_psd="main_tap_white"
        )
        self.dte.w_lim[0] = 0.0
        with self.assertRaisesRegex(ValueError, "nonzero finite FFE main tap"):
            self.model.build_mlsd_noise(self.imp, self.eq_ch, self.dte, self.added_noise)

    def test_added_noise_uses_g_an_not_stored_s_an_grid(self) -> None:
        baseline = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        other_grid = LinkConfig.from_Nfft(self.fb, 1, 8)
        self.added_noise.S_an = SampledPSD.from_constant(
            other_grid.theta, 123.0, self.fb, cfg=other_grid
        )
        repeated = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        np.testing.assert_array_equal(repeated.S_ni.psd, baseline.S_ni.psd)

    def test_full_mlsd_uses_expanded_post_ffe_response_grid(self) -> None:
        expanded = LinkConfig.from_Nfft(self.fb, 1, 18)
        self.eq_ch.post_ffe = COMPostFFEEqChannelStatus(
            h_ISI=SampledResponse.from_ir(np.array([0.0, 0.2, -0.1]), expanded),
        )
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        self.assertIs(result.record_cfg, expanded)
        self.assertIs(result.S_isi.cfg, expanded)
        self.assertIs(result.S_ni.cfg, expanded)

    def test_full_mlsd_selects_longest_xt_grid_and_keeps_inputs(self) -> None:
        xt_cfg = LinkConfig.from_Nfft(self.fb, 1, 32)
        xt = SampledResponse.from_ir(np.array([0.1, -0.05]), xt_cfg)
        self.eq_ch.pre_dte.h_XTs_dsamp = [xt]
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        self.assertIs(result.record_cfg, xt_cfg)
        self.assertIs(self.eq_ch.post_ffe.h_ISI.cfg, self.grid)
        self.assertIs(self.eq_ch.pre_dte.h_XTs_dsamp[0].cfg, xt_cfg)

    def test_truncated_mlsd_changes_only_psd_record(self) -> None:
        self.model.cfg.num = COMNumericalControlConfig(
            eq_ch_imp_len="truncated", num_trunc_ui=8
        )
        original_h_isi = self.eq_ch.post_ffe.h_ISI.ir.copy()
        result = self.model.build_mlsd_noise(
            self.imp, self.eq_ch, self.dte, self.added_noise
        )
        self.assertEqual(result.record_cfg.sampled_nfft, 8)
        self.assertEqual(result.R_ni.shape, (8,))
        np.testing.assert_array_equal(self.eq_ch.post_ffe.h_ISI.ir, original_h_isi)

    def test_truncated_mlsd_xt_keeps_max_energy_window(self) -> None:
        self.model.cfg.num = COMNumericalControlConfig(
            eq_ch_imp_len="truncated", num_trunc_ui=8
        )
        xt_ir = np.zeros(16)
        xt_ir[12:14] = [1.0, 0.5]
        xt = SampledResponse.from_ir(xt_ir.copy(), self.grid)
        self.eq_ch.pre_dte.h_XTs_dsamp = [xt]
        original_builder = model_module._build_psd_from_DFT_response
        with patch.object(model_module, "_build_psd_from_DFT_response", wraps=original_builder) as builder:
            self.model.build_mlsd_noise(self.imp, self.eq_ch, self.dte, self.added_noise)
        xt_record = builder.call_args_list[0].args[0]
        self.assertAlmostEqual(float(np.sum(xt_record**2)), 1.25)
        np.testing.assert_array_equal(xt.ir, xt_ir)


if __name__ == "__main__":
    unittest.main()
