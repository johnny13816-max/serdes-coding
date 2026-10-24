"""Production-path regression anchor for the maintained 93A case."""

from pathlib import Path

import numpy as np

from serdes_coding.io.com_excel_io_93A import (
    excel_to_config_93A,
    excel_to_search_config_93A,
)
from serdes_coding.models.com_model_93A import COM


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "cases" / "case_260915_report" / "93A" / "config.xlsx"


def test_case_260915_report_93a_production_golden() -> None:
    cfg = excel_to_config_93A(str(CONFIG))
    search_cfg = excel_to_search_config_93A(str(CONFIG))

    assert cfg.dfe.N_b == 1
    assert cfg.dfe.bb_min == 0.0
    assert len(search_cfg.candidates(cfg.filter)) == 232_848

    status = COM(cfg).run()

    assert len(status.paths) == 3
    assert status.dfe.ts == 79_356
    assert status.dfe.pos == 28
    np.testing.assert_allclose(status.dfe.dfe_coeff, [0.85], rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(status.FOM, 0.4603512834103074, rtol=0.0, atol=1e-14)
    np.testing.assert_allclose(status.pmf.dy, 4.658291240062964e-06, rtol=0.0, atol=1e-18)
    np.testing.assert_allclose(status.pmf.A_ni, 0.013807175235546622, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(status.pmf.COM, -9.43756398614581, rtol=0.0, atol=1e-12)

