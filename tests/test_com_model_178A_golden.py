"""Production-path regression anchor for the maintained 178A reference case."""

from dataclasses import replace
import hashlib
from pathlib import Path

import numpy as np

from serdes_coding.io.com_excel_io_178A import excel_to_config_178A
from serdes_coding.models.com_model_178A import COM


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "cases" / "sicopr_akinwale_vendorx_22db" / "178A" / "config.xlsx"


def _quantized_digest(values: np.ndarray, *, decimals: int = 12) -> str:
    """Return a platform-tolerant digest for a fixed numerical stage vector."""
    array = np.ascontiguousarray(np.round(np.asarray(values, dtype=np.float64), decimals))
    return hashlib.sha256(array.tobytes()).hexdigest()


def test_sicopr_akinwale_178a_production_golden() -> None:
    cfg = excel_to_config_178A(str(CONFIG))
    run_cfg = replace(cfg.execution.single_run, target="full")

    assert cfg.policy.applied_config_profile == "sicopr_reference_v1"

    status = COM(cfg)._run_once(run_cfg=run_cfg, progress=False)

    assert len(status.paths) == 6
    assert status.dte.pos == 5
    assert status.dte.ts == 38_149
    assert status.dte.w.shape == (87,)
    assert status.dte.b.shape == (1,)
    assert status.imp.h_dsamp.ir.shape == (10_626,)
    assert status.imp.R_n.shape == (4_096,)

    np.testing.assert_allclose(status.dte.mse, 0.0061912610245255335, rtol=0.0, atol=1e-14)
    np.testing.assert_allclose(status.dte.b, [0.8420106292760028], rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(status.imp.As, 0.31666666666666665, rtol=0.0, atol=1e-15)
    np.testing.assert_allclose(status.pmf.A_ni, 0.2656833333333335, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(status.pmf.COM, 1.5247607834259893, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(status.mlsd.delta_COM, 1.3711379014472564, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(status.mlsd.COM_MLSD, 2.895898684873246, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(status.final_COM, 2.895898684873246, rtol=0.0, atol=1e-12)

    assert _quantized_digest(status.dte.w) == (
        "aedef2cbd02deb6cdd0868c60c8ce46fe927867fcc8a3d5429dc6802e74241f1"
    )
    assert _quantized_digest(status.imp.h_dsamp.ir) == (
        "8ebb13b0646c7b83fc39e93a3b36b9cf3758825e0316619beca9b1a204d26971"
    )
    assert _quantized_digest(status.imp.R_n) == (
        "5aef52dee259d6b94fd6ccda4d738a4a299527b1157220e1620b750d45c55871"
    )
