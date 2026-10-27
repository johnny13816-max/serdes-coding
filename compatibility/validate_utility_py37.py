"""Validate syntax and representative behavior of the Python 3.7 export."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
EXPORT = Path(__file__).with_name("utility_py37.py")
sys.path.insert(0, str(ROOT / "src"))

if sys.version_info >= (3, 8):
    from serdes_coding.utilities import LinkConfig as SourceLinkConfig
    from serdes_coding.utilities import LinkSegment as SourceLinkSegment
    from serdes_coding.utilities import SparamModel as SourceSparamModel
else:
    SourceLinkConfig = SourceLinkSegment = SourceSparamModel = None


def _load_export():
    spec = importlib.util.spec_from_file_location("utility_py37_validation", EXPORT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load utility_py37.py.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _assert_eye_matches(module) -> None:
    kwargs = dict(fb=53.125e9, per_ui=8, target_df=53.125e9 / 32)
    export_cfg = module.LinkConfig(**kwargs)
    ir = np.zeros(export_cfg.Nfft)
    ir[7:11] = [0.1, 0.6, 0.25, 0.05]
    exported = module.LinkSegment.from_ir(ir, export_cfg)
    symbols = np.asarray([1.0, -1.0, 1.0, 1.0, -1.0])
    export_time, export_traces = exported.eye_traces(symbols, alignment="main_cursor")
    assert export_time.shape == (2 * export_cfg.per_ui + 1,)
    assert export_traces.shape == (len(symbols), len(export_time))
    if SourceLinkConfig is not None:
        source_cfg = SourceLinkConfig(**kwargs)
        source = SourceLinkSegment.from_ir(ir, source_cfg)
        source_time, source_traces = source.eye_traces(symbols, alignment="main_cursor")
        np.testing.assert_array_equal(export_time, source_time)
        np.testing.assert_allclose(export_traces, source_traces, rtol=0.0, atol=0.0)


def _assert_sparam_matches(module) -> None:
    freqs = np.asarray([0.0, 1.0e9, 2.0e9])
    sdd = np.zeros((len(freqs), 2, 2), dtype=complex)
    sdd[:, 1, 0] = [1.0, 0.8 - 0.1j, 0.6 - 0.2j]
    sdd[:, 0, 1] = sdd[:, 1, 0]
    exported = module.SparamModel.from_sdd_array(freqs, sdd, z0=92.5)
    order = (0, 2, 1, 3)
    export_roundtrip = exported.s2p_to_synthetic_s4p(port_order=order, z0_diff=92.5).s4p_to_s2p()
    np.testing.assert_allclose(export_roundtrip.sdd, sdd, rtol=1e-13, atol=1e-13)
    if SourceSparamModel is not None:
        source = SourceSparamModel.from_sdd_array(freqs, sdd, z0=92.5)
        source_roundtrip = source.s2p_to_synthetic_s4p(port_order=order, z0_diff=92.5).s4p_to_s2p()
        np.testing.assert_allclose(export_roundtrip.sdd, source_roundtrip.sdd, rtol=0.0, atol=0.0)


def main() -> None:
    source = EXPORT.read_text(encoding="utf-8")
    if sys.version_info >= (3, 8):
        ast.parse(source, filename=str(EXPORT), feature_version=(3, 7))
    else:
        compile(source, str(EXPORT), "exec")
    if "np.trapezoid(" in source:
        raise AssertionError("Python 3.7 NumPy compatibility rewrite was not applied.")
    module = _load_export()
    _assert_eye_matches(module)
    _assert_sparam_matches(module)
    print("utility_py37 validation passed")


if __name__ == "__main__":
    main()
