from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import unittest

import numpy as np

from serdes_coding.io.com_excel_io import excel_to_config_178A
from serdes_coding.models.com_model_178A import COM
from serdes_coding.utilities.pmf import Pmf1D
from serdes_coding.utilities.psd import SampledPSD


class TestPostFFEImpairment178A(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        root = Path(__file__).resolve().parents[1]
        cfg = excel_to_config_178A(
            str(root / "cases" / "case_260915_full" / "178A" / "config.xlsx")
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
        cls.status = cls.model._run_once(
            run_cfg=cls.cfg.execution.search_final,
            progress=False,
        )

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

    def test_final_adc_all_taps_matches_reference_seeded_main_accumulation(self) -> None:
        base = Pmf1D.multi_dirac(
            np.array([-1.0, 0.0, 1.0]),
            np.array([0.25, 0.5, 0.25]),
            dx=0.25,
            unit="volt",
        )
        taps = np.array([0.5, 1.0, 0.25])

        # Project method: Dirac seed inside fir_filter(), then every tap.
        all_taps = base.fir_filter(
            taps,
            keep_mass=1.0,
            dx_ref=base.dx,
            tap_abs_th=0.0,
        )

        # Reference loop: the initial PMF already represents the unit main
        # tap, so the loop adds only the non-main tap contributions.
        seeded_main = base.copy()
        for tap in (taps[0], taps[2]):
            seeded_main = seeded_main.combine(
                base.copy().scale_x(tap, keep_dx=True, dx_ref=base.dx)
            )

        np.testing.assert_allclose(all_taps.x, seeded_main.x, rtol=0.0, atol=0.0)
        np.testing.assert_allclose(
            all_taps.pmf, seeded_main.pmf, rtol=1e-13, atol=1e-15
        )


if __name__ == "__main__":
    unittest.main()
