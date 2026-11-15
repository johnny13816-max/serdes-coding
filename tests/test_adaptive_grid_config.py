import pytest
from serdes_coding.models.com_178a.config import COMNumericalControlConfig
from serdes_coding.io.com_excel_io_178A import _read_project_numerical_control_178A


def test_adaptive_grid_threshold_defaults():
    cfg = COMNumericalControlConfig(path_grid_mode="adaptive")
    assert cfg.fine_grid_df == 1e6
    assert cfg.relative_threshold == 1e-3
    assert cfg.absolute_threshold is None


def test_adaptive_requires_a_threshold_but_fixed_does_not():
    with pytest.raises(ValueError, match="at least one threshold"):
        COMNumericalControlConfig(path_grid_mode="adaptive", relative_threshold=None)
    COMNumericalControlConfig(path_grid_mode="fixed", relative_threshold=None)
    COMNumericalControlConfig(path_grid_mode="adaptive", relative_threshold=None,
                              absolute_threshold=1e-6)


@pytest.mark.parametrize("name,value", [
    ("path_grid_mode", "invalid"), ("fine_grid_df", 0),
    ("fine_grid_df", float("nan")), ("relative_threshold", -1),
    ("absolute_threshold", float("inf")),
])
def test_invalid_grid_settings_are_rejected(name, value):
    with pytest.raises(ValueError, match=name):
        COMNumericalControlConfig(**{name: value})


def test_project_adapter_reads_adaptive_controls():
    fixed = {
        "dy_rel_As": 0.01, "dy_abs_max": 0.001,
        "path_grid_mode": "adaptive", "fine_grid_df": 2e6,
        "relative_threshold": 2e-3, "absolute_threshold": None,
    }
    cfg, _ = _read_project_numerical_control_178A(fixed)
    assert cfg.path_grid_mode == "adaptive"
    assert cfg.fine_grid_df == 2e6
    assert cfg.relative_threshold == 2e-3
    assert cfg.absolute_threshold is None
