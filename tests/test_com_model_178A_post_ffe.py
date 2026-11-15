from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np

from serdes_coding.io.com_excel_io import excel_to_config_178A
from serdes_coding.models.com_model_178A import COM
from serdes_coding.utilities.psd import SampledPSD
from serdes_coding.utilities.pmf import Pmf1D


class TestPostFFEImpairment178A(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = excel_to_config_178A(
            str(root / "cases" / "case_260915_full" / "178A" / "config.xlsx"),
            run_mode="single_run",
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
        self.assertTrue(np.isfinite(status.dte.mse))
        post = status.imp.post_ffe.psd
        for name in ("S_rn", "S_xn", "S_tn", "S_jn", "S_qn", "S_total"):
            value = getattr(post, name)
            self.assertIs(value.cfg, status.imp.pre_dte.record_cfg, name)

    def test_xtalk_psd_is_power_sum_of_post_ffe_paths(self) -> None:
        status = self.status
        post = status.imp.post_ffe.psd
        direct = status.imp.pre_dte.psd.S_xn.filtered_by(status.dte.H_rxffe)
        np.testing.assert_allclose(post.S_xn.psd, direct.psd, rtol=1e-12, atol=1e-24)

    def test_response_grid_does_not_change_stage5_psd_record(self) -> None:
        full_cfg = replace(
            self.cfg,
            num=replace(
                self.cfg.num,
                eq_ch_imp_len="full",
                num_trunc_ui=None,
            ),
        )
        model = COM(full_cfg)
        status = model.run(progress=False)
        record_cfg = status.imp.post_ffe.record_cfg
        self.assertIs(record_cfg, status.imp.pre_dte.record_cfg)
        self.assertIs(record_cfg, full_cfg.link)
        for response in (
            status.eq_ch.h_w,
            status.eq_ch.h_ISI,
            status.eq_ch.h_w_J,
            *status.eq_ch.h_XTs_w,
        ):
            self.assertIs(response.cfg, full_cfg.link)
        for name in ("S_rn", "S_xn", "S_tn", "S_jn", "S_qn", "S_total"):
            self.assertIs(getattr(status.imp.post_ffe.psd, name).cfg, record_cfg)

    def test_quantization_psd_matches_final_pmf_rms(self) -> None:
        status = self.status
        expected = status.imp.pre_dte.psd.S_qn.filtered_by(status.dte.H_rxffe)
        np.testing.assert_allclose(
            status.imp.post_ffe.psd.S_qn.psd,
            expected.psd,
            rtol=1e-12,
            atol=1e-24,
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

    def test_reference_quantization_skips_compressed_tap_position(self) -> None:
        cfg = replace(
            self.cfg,
            alg=replace(self.cfg.alg, final_com_vqc_convention="sicopr_final_reconstruction"),
            num=replace(self.cfg.num, final_pmf_grid=replace(
                self.cfg.num.final_pmf_grid, dy_override=1e-3,
            )),
        )
        main = cfg.dte.d_w
        original_fir = Pmf1D.fir_filter
        for case in ("no_preceding_zero", "preceding_zero", "short_nonzero"):
            with self.subTest(case=case):
                taps = np.zeros(cfg.dte.N_max)
                taps[main] = 1.0
                if case != "short_nonzero":
                    taps[:main] = 0.2
                    taps[main + 1] = 0.3
                if case == "preceding_zero":
                    taps[0] = 0.0
                expected = taps.copy()
                indices = np.flatnonzero(taps != 0.0)
                if main < len(indices):
                    expected[indices[main]] = 0.0
                captured = []

                def recording_fir(pmf, fir, **kwargs):
                    if kwargs.get("name") == "ADC_QN":
                        captured.append(np.asarray(fir).copy())
                    return original_fir(pmf, fir, **kwargs)

                with patch.object(Pmf1D, "fir_filter", recording_fir):
                    COM(cfg).calculate_COM_DFE(
                        self.status.imp, self.status.eq_ch,
                        replace(self.status.dte, w_lim=taps),
                    )
                self.assertEqual(len(captured), 1)
                np.testing.assert_array_equal(captured[0], expected)

        # The D3.2 path retains all taps, including the physical main tap.
        spec_cfg = replace(cfg, alg=replace(cfg.alg, final_com_vqc_convention="selected_phase_adc_input"))
        taps = np.zeros(cfg.dte.N_max)
        taps[main] = 1.0
        captured = []
        def recording_spec(pmf, fir, **kwargs):
            if kwargs.get("name") == "ADC_QN":
                captured.append(np.asarray(fir).copy())
            return original_fir(pmf, fir, **kwargs)
        with patch.object(Pmf1D, "fir_filter", recording_spec):
            COM(spec_cfg).calculate_COM_DFE(self.status.imp, self.status.eq_ch,
                                           replace(self.status.dte, w_lim=taps))
        np.testing.assert_array_equal(captured[0], taps)


if __name__ == "__main__":
    unittest.main()
