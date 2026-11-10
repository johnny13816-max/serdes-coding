from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import numpy as np

from serdes_coding.io.com_excel_io import excel_to_config_178A
from serdes_coding.models.com_model_178A import COM
from serdes_coding.utilities.psd import SampledPSD


class TestPostFFEImpairment178A(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = excel_to_config_178A(
            str(root / "cases" / "case_260915_full" / "178A" / "config.xlsx"),
            run_mode="search_final",
        )
        cls.cfg = replace(
            cfg,
            filter=replace(
                cfg.filter,
                c_m2=0.06,
                c_m1=-0.26,
                c_1=0.0,
                g_1=-16.0,
                g_2=-4.0,
            ),
        )
        cls.model = COM(cls.cfg)
        cls.status = cls.model.run(progress=False)

    def test_mse_and_post_grid_contract(self) -> None:
        status = self.status
        # Golden value after measured Sdd renormalization (178A-4).
        self.assertAlmostEqual(status.dte.mse, 0.006203013107434269, places=14)
        post = status.imp.post_ffe.psd
        for name in ("S_rn", "S_xn", "S_tn", "S_jn", "S_qn", "S_total"):
            value = getattr(post, name)
            self.assertTrue(np.isclose(value.fb, status.eq_ch.h_w.fb), name)
            np.testing.assert_allclose(value.theta, status.eq_ch.h_w.theta, rtol=1e-12, atol=1e-15)

    def test_xtalk_psd_is_power_sum_of_post_ffe_paths(self) -> None:
        status = self.status
        post = status.imp.post_ffe.psd
        direct = SampledPSD.from_constant(post.S_xn.theta, 0.0, post.S_xn.fb)
        for response in status.eq_ch.h_XTs_w:
            source = SampledPSD.from_constant(
                response.theta,
                status.imp.sigma_X**2 / response.fb,
                response.fb,
            )
            direct = direct.add(source.filtered_by(response))
        np.testing.assert_allclose(post.S_xn.psd, direct.psd, rtol=1e-12, atol=1e-24)

    def test_expanded_record_uses_one_stage5_grid_for_responses_and_psds(self) -> None:
        expanded_cfg = replace(
            self.cfg,
            alg=replace(
                self.cfg.alg,
                rxffe_record_realization="linear_expanded_grid",
            ),
            num=replace(
                self.cfg.num,
                eq_ch_imp_len="full",
                num_trunc_ui=None,
            ),
        )
        model = COM(expanded_cfg)
        status = model.run(progress=False)
        response_cfg = status.eq_ch.post_ffe.response_cfg
        record_cfg = status.imp.post_ffe.record_cfg
        expected = expanded_cfg.link.sampled_nfft + expanded_cfg.dte.N_max - 1
        if expected % 2:
            expected += 1
        self.assertEqual(response_cfg.sampled_nfft, expected)
        self.assertIs(record_cfg, response_cfg)
        for response in (
            status.eq_ch.h_w,
            status.eq_ch.h_ISI,
            status.eq_ch.h_w_J,
            *status.eq_ch.h_XTs_w,
        ):
            self.assertIs(response.cfg, response_cfg)
        for name in ("S_rn", "S_xn", "S_tn", "S_jn", "S_qn", "S_total"):
            self.assertIs(getattr(status.imp.post_ffe.psd, name).cfg, record_cfg)

    def test_quantization_psd_matches_final_pmf_rms(self) -> None:
        status = self.status
        p_qn = status.pmf.p_qn
        mean = float(np.sum(p_qn.x * p_qn.pmf))
        pmf_sigma = float(np.sqrt(np.sum((p_qn.x - mean) ** 2 * p_qn.pmf)))
        self.assertTrue(
            np.isclose(status.imp.post_ffe.psd.sigma_qn, pmf_sigma, rtol=5e-4, atol=1e-8),
            (status.imp.post_ffe.psd.sigma_qn, pmf_sigma),
        )

    def test_display_psds_do_not_change_dfe_com(self) -> None:
        status = self.status
        post = status.imp.post_ffe.psd
        names = ("S_rn", "S_xn", "S_tn", "S_jn", "S_qn", "S_total")
        saved = {name: getattr(post, name) for name in names}
        try:
            for name in names:
                original = saved[name]
                setattr(
                    post,
                    name,
                    SampledPSD.from_constant(original.theta, 0.0, original.fb),
                )
            repeated = self.model.calculate_COM_DFE(status.imp, status.eq_ch, status.dte)
            self.assertAlmostEqual(repeated.COM, status.pmf.COM, places=12)
        finally:
            for name, value in saved.items():
                setattr(post, name, value)

    def test_final_com_vqc_policy_is_isolated_from_selected_mmse(self) -> None:
        status = self.status
        original_mse = status.dte.mse
        original_delta = status.imp.post_ffe.adc_input.delta
        reference_cfg = replace(
            self.cfg,
            alg=replace(
                self.cfg.alg,
                final_com_vqc_convention="sicopr_final_reconstruction",
            ),
        )
        # The reference branch is tested here for stage isolation; a coarse
        # final grid keeps this generic integration fixture inexpensive.
        num_cfg = replace(
            reference_cfg.num,
            final_pmf_grid=replace(
                reference_cfg.num.final_pmf_grid,
                dy_override=1e-3,
            ),
        )
        annex = COM(replace(self.cfg, num=num_cfg)).calculate_COM_DFE(
            status.imp, status.eq_ch, status.dte
        )
        alternate = COM(replace(reference_cfg, num=num_cfg)).calculate_COM_DFE(
            status.imp, status.eq_ch, status.dte
        )
        self.assertTrue(np.isfinite(alternate.COM))
        self.assertNotAlmostEqual(alternate.COM, annex.COM, places=4)
        self.assertEqual(annex.final_vqc_convention, "selected_phase_adc_input")
        self.assertEqual(annex.final_V_qc, status.imp.post_ffe.adc_input.V_qc)
        self.assertEqual(annex.final_delta, original_delta)
        self.assertEqual(alternate.final_vqc_convention, "sicopr_final_reconstruction")
        self.assertIsNotNone(alternate.final_V_qc)
        self.assertIsNotNone(alternate.final_delta)
        self.assertEqual(status.dte.mse, original_mse)
        self.assertEqual(status.imp.post_ffe.adc_input.delta, original_delta)


if __name__ == "__main__":
    unittest.main()
