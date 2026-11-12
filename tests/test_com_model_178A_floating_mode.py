import ast
from inspect import getsource

import numpy as np
import pytest

from serdes_coding.models.com_178a.config import COMDTEConfig
from serdes_coding.models.com_178a.status import COMDTEStatus
from serdes_coding.models.com_model_178A import COM_MMSE_DTE


def test_alg010_operational_selector_read_is_confined_to_run() -> None:
    tree = ast.parse(getsource(COM_MMSE_DTE))
    class_node = tree.body[0]
    readers = {
        function.name
        for function in class_node.body
        if isinstance(function, ast.FunctionDef)
        and any(
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and node.attr == "floating_mode"
            for node in ast.walk(function)
        )
    }
    assert readers == {"run"}


def _dte_config(*, floating: bool) -> COMDTEConfig:
    return COMDTEConfig(
        d_w=1,
        N_fix=3,
        N_wg=1 if floating else 0,
        N_wf=1 if floating else 0,
        N_max=6 if floating else 3,
        N_b=1,
        w_pre1_max=2.0,
        w_post1_max=2.0,
        w_fixed_rest_max=2.0,
        w_float_max=2.0,
        w_float_min=-2.0,
        b_first_max=2.0,
        b_first_min=-2.0,
        b_rest_max=2.0,
        b_rest_min=-2.0,
    )


def _solver_input(cfg: COMDTEConfig) -> tuple[np.ndarray, np.ndarray]:
    h_dsamp = np.array([1.0, 0.2, 0.1, 0.05, 0.02, 0.01, 0.005, 0.002])
    R_n = np.zeros(cfg.N_max)
    R_n[0] = 1e-3
    return h_dsamp, R_n


def _assert_complete_status(status: COMDTEStatus, cfg: COMDTEConfig) -> None:
    assert isinstance(status, COMDTEStatus)
    assert status.w_lim.shape == (cfg.N_max,)
    assert status.w.shape == (cfg.N_max,)
    assert status.b_lim.shape == (cfg.N_b,)
    assert status.b.shape == (cfg.N_b,)
    assert status.H_all.shape[1] == cfg.N_max
    assert status.Rnn_all.shape == (cfg.N_max, cfg.N_max)
    assert status.H.shape[1] == len(status.pruned_index)
    assert status.R_nn.shape == (len(status.pruned_index), len(status.pruned_index))
    assert status.H_b.shape == (cfg.N_b, len(status.pruned_index))
    assert np.isfinite(status.mse)
    assert status.H_rxffe is None


@pytest.mark.parametrize(
    ("floating_mode", "expected_helper"),
    [
        ("heuristic", "_select_floating_tap_by_isi"),
        ("simplified", "_select_floating_tap_onetime"),
        ("spec-defined", "_calculate_float_ffe_178A"),
    ],
)
def test_alg010_owner_dispatches_each_floating_strategy_once(
    floating_mode: str,
    expected_helper: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _dte_config(floating=True)
    solver = COM_MMSE_DTE(cfg, floating_mode)
    calls: list[str] = []

    for helper_name in (
        "_select_floating_tap_by_isi",
        "_select_floating_tap_onetime",
        "_calculate_float_ffe_178A",
    ):
        original = getattr(solver, helper_name)

        def traced(*args, _name=helper_name, _original=original, **kwargs):
            calls.append(_name)
            return _original(*args, **kwargs)

        monkeypatch.setattr(solver, helper_name, traced)

    h_dsamp, R_n = _solver_input(cfg)
    status = solver.run(h_dsamp, R_n, sigma_x=1.0, pos=0, per_ui=1)

    assert calls == [expected_helper]
    assert np.array_equal(status.pruned_index[: cfg.N_fix], np.arange(cfg.N_fix))
    assert len(status.pruned_index) == cfg.N_fix + cfg.N_wg * cfg.N_wf
    _assert_complete_status(status, cfg)


@pytest.mark.parametrize("floating_mode", ["heuristic", "simplified", "spec-defined"])
def test_alg010_n_wg_zero_bypasses_floating_strategy(
    floating_mode: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = _dte_config(floating=False)
    solver = COM_MMSE_DTE(cfg, floating_mode)

    def unexpected_selector(*args, **kwargs):
        raise AssertionError("N_wg=0 must bypass every floating strategy")

    for helper_name in (
        "_select_floating_tap_by_isi",
        "_select_floating_tap_onetime",
        "_calculate_float_ffe_178A",
    ):
        monkeypatch.setattr(solver, helper_name, unexpected_selector)

    h_dsamp, R_n = _solver_input(cfg)
    status = solver.run(h_dsamp, R_n, sigma_x=1.0, pos=0, per_ui=1)

    assert np.array_equal(status.pruned_index, np.arange(cfg.N_fix))
    _assert_complete_status(status, cfg)
