"""Eq. 178A-47 uses the signal amplitude in the MLSD COM increment."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from serdes_coding.models.com_model_178A import (
    COM,
    COMAddedNoiseStatus,
    COMDTEStatus,
    COMImpairmentStatus,
    COMImpStageStatus,
    COMMLSDConfig,
    COMPolicyConfig,
    COMMLSDNoiseStatus,
    COMPMFStatus,
    COMPSDStatus,
    COMRunConfig,
    COMStatus,
)
from serdes_coding.utilities.pmf import Pmf1D
from serdes_coding.utilities.psd import SampledPSD


class TestMLSDCOMEquation178A47(unittest.TestCase):
    def test_signal_amplitude_denominator_and_dfe_floor(self) -> None:
        As = 0.3
        A_ni = 0.25
        COM_DFE = float(20.0 * np.log10(As / A_ni))
        der = 0.02

        for tail_amplitude in (0.2, 0.5):
            with self.subTest(tail_amplitude=tail_amplitude):
                p_an = Pmf1D.multi_dirac(
                    np.array([-tail_amplitude, 0.0, tail_amplitude]),
                    np.array([0.03, 0.94, 0.03]),
                    dx=0.001,
                )
                theta = np.linspace(0.0, np.pi, 5)
                S_an = SampledPSD.from_constant(theta, 0.0, 8.0)
                added_noise = COMAddedNoiseStatus(
                    g_an=0.0,
                    S_an=S_an,
                    sigma_an=0.0,
                    p_an=p_an,
                    delta_com_an_temp=0.0,
                )
                noise = COMMLSDNoiseStatus(
                    S_isi=S_an,
                    sigma_isi=0.0,
                    S_ni=S_an,
                    sigma_ni=0.0,
                    R_ni=np.array([1.0, 0.0]),
                )
                dte = COMDTEStatus.__new__(COMDTEStatus)
                dte.b_lim = np.array([0.5])
                imp = COMImpairmentStatus(
                    post_ffe=COMImpStageStatus(psd=COMPSDStatus(As=As))
                )
                pmf = COMPMFStatus(
                    dy=0.001,
                    tap_abs_th=0.0,
                    A_ni=A_ni,
                    COM=COM_DFE,
                )
                model = COM.__new__(COM)
                model.cfg = SimpleNamespace(
                    mlsd=COMMLSDConfig(enable=True, trunc_len=1, delta_com_an=0.0),
                    dte=SimpleNamespace(N_b=1),
                    pmf=SimpleNamespace(),
                    execution=SimpleNamespace(single_run=COMRunConfig()),
                    resolve_run_cfg=lambda run_cfg: run_cfg,
                    policy=COMPolicyConfig(),
                    DER_0=1e-6,
                    L=4,
                )
                model.status = COMStatus(imp=imp, dte=dte, pmf=pmf)

                with (
                    patch(
                        "serdes_coding.models.com_model_178A._resolve_final_com_pmf_config",
                        return_value=object(),
                    ),
                    patch(
                        "serdes_coding.models.com_model_178A.solve_g_an",
                        return_value=added_noise,
                    ),
                    patch.object(model, "build_mlsd_noise", return_value=noise) as build_noise,
                    patch(
                        "serdes_coding.models.com_model_178A.calculate_der_mlsd",
                        return_value=(der, np.array([der])),
                    ) as solve_der,
                ):
                    result = model.calculate_COM_MLSD()

                build_noise.assert_called_once_with(imp, added_noise)
                solve_der.assert_called_once_with(
                    p_an,
                    noise.R_ni,
                    L=4,
                    As=As,
                    b_lim_1=0.5,
                    trunc_len=1,
                    pmf_scaling_method="mass_deposit",
                    sequence_termination="fixed_length_sum",
                )

                A_MLSD = -float(p_an.quantile(der))
                expected_increment = float(20.0 * np.log10(A_MLSD / As))
                self.assertAlmostEqual(result.A_MLSD, A_MLSD, places=12)
                self.assertAlmostEqual(result.delta_COM, expected_increment, places=12)
                self.assertAlmostEqual(
                    result.COM_MLSD_raw - COM_DFE, expected_increment, places=12
                )
                self.assertAlmostEqual(
                    result.COM_MLSD, max(COM_DFE, COM_DFE + expected_increment), places=12
                )
                self.assertEqual(model.status.mlsd, result)
                self.assertIs(result.added_noise, added_noise)
                self.assertIs(result.S_ni, noise.S_ni)
                self.assertAlmostEqual(model.status.pmf.A_ni, A_ni, places=12)
                self.assertAlmostEqual(model.status.pmf.COM, COM_DFE, places=12)


if __name__ == "__main__":
    unittest.main()
