"""Validate syntax and representative behavior of the Python 3.7 export."""

from __future__ import annotations

import ast
import importlib.util
import inspect
from pathlib import Path
import sys

import numpy as np

from build_utility_py37 import build


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


def _assert_export_is_current(source: str) -> None:
    if source != build():
        raise AssertionError(
            "utility_py37.py is stale; rebuild it with build_utility_py37.py."
        )


def _assert_fir_scaling_boundary(module) -> None:
    signature = inspect.signature(module.Pmf1D.fir_filter)
    if "scaling_method" in signature.parameters:
        raise AssertionError(
            "Pmf1D.fir_filter() must not expose the direct scale_x scaling policy."
        )
    method_source = inspect.getsource(module.Pmf1D.fir_filter)
    if 'method="mass_deposit"' not in method_source:
        raise AssertionError(
            "Pmf1D.fir_filter() must keep its fixed mass_deposit scaling behavior."
        )


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
    order = (2, 0, 3, 1)
    export_roundtrip = exported.s2p_to_synthetic_s4p(
        target_z0_diff=100.0, reader_port_order=order,
    ).s4p_to_s2p()
    expected = exported.renormalized(100.0)
    np.testing.assert_allclose(export_roundtrip.sdd, expected.sdd, rtol=1e-13, atol=1e-13)
    if SourceSparamModel is not None:
        source = SourceSparamModel.from_sdd_array(freqs, sdd, z0=92.5)
        source_roundtrip = source.s2p_to_synthetic_s4p(
            target_z0_diff=100.0, reader_port_order=order,
        ).s4p_to_s2p()
        np.testing.assert_allclose(export_roundtrip.sdd, source_roundtrip.sdd, rtol=0.0, atol=0.0)

    missing_dc_freqs = np.arange(1.0, 13.0) * 1e9
    magnitude = 0.9 - 0.01 * missing_dc_freqs / 1e9
    response = magnitude * np.exp(-1j * 2.0 * np.pi * missing_dc_freqs * 18e-12)
    missing_dc_sdd = np.zeros((len(missing_dc_freqs), 2, 2), dtype=complex)
    missing_dc_sdd[:, 1, 0] = response
    exported_missing_dc = module.SparamModel.from_sdd_array(
        missing_dc_freqs, missing_dc_sdd, z0=100.0
    )
    export_freqs, export_response = (
        exported_missing_dc.completed_voltage_transfer_function(
            dc="mag_phase_trend_to_dc"
        )
    )
    np.testing.assert_array_equal(export_freqs, np.r_[0.0, missing_dc_freqs])
    np.testing.assert_allclose(export_response[0], 0.9 + 0j, rtol=0.0, atol=2e-15)
    if SourceSparamModel is not None:
        source_missing_dc = SourceSparamModel.from_sdd_array(
            missing_dc_freqs, missing_dc_sdd, z0=100.0
        )
        source_freqs, source_response = (
            source_missing_dc.completed_voltage_transfer_function(
                dc="mag_phase_trend_to_dc"
            )
        )
        np.testing.assert_array_equal(export_freqs, source_freqs)
        np.testing.assert_array_equal(export_response, source_response)


def main() -> None:
    source = EXPORT.read_text(encoding="utf-8")
    _assert_export_is_current(source)
    if sys.version_info >= (3, 8):
        ast.parse(source, filename=str(EXPORT), feature_version=(3, 7))
    else:
        compile(source, str(EXPORT), "exec")
    if "np.trapezoid(" in source:
        raise AssertionError("Python 3.7 NumPy compatibility rewrite was not applied.")
    module = _load_export()
    _assert_fir_scaling_boundary(module)
    _assert_eye_matches(module)
    _assert_sparam_matches(module)
    print("utility_py37 validation passed")


if __name__ == "__main__":
    main()
