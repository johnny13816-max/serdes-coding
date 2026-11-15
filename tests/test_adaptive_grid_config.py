from dataclasses import replace
from pathlib import Path
import pytest
from serdes_coding.models.com_178a.config import COMAlgorithmPolicyConfig, COMNumericalControlConfig, COMRunProfiles
from serdes_coding.io.com_excel_io_178A import _read_project_numerical_control_178A, _resolve_project_profile_178A, excel_to_config_178A


def test_adaptive_grid_threshold_defaults():
    cfg = COMNumericalControlConfig()
    assert cfg.fine_grid_df == 1e6
    assert cfg.relative_threshold == 1e-3
    assert cfg.absolute_threshold is None


def test_adaptive_requires_a_threshold_but_fixed_does_not():
    root = Path(__file__).resolve().parents[1]
    cfg = excel_to_config_178A(str(root / "cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx"))
    num = replace(cfg.num, relative_threshold=None, absolute_threshold=None)
    with pytest.raises(ValueError, match="at least one threshold"):
        replace(cfg, alg=replace(cfg.alg, path_grid_mode="adaptive"), num=num)
    replace(cfg, alg=replace(cfg.alg, path_grid_mode="fixed"), num=num)
    replace(cfg, alg=replace(cfg.alg, path_grid_mode="adaptive"),
            num=replace(num, absolute_threshold=1e-6))


@pytest.mark.parametrize("name,value", [
    ("fine_grid_df", 0),
    ("fine_grid_df", float("nan")), ("relative_threshold", -1),
    ("absolute_threshold", float("inf")),
])
def test_invalid_grid_settings_are_rejected(name, value):
    with pytest.raises(ValueError, match=name):
        COMNumericalControlConfig(**{name: value})


def test_invalid_path_grid_mode_is_rejected():
    with pytest.raises(ValueError, match="path_grid_mode"):
        COMAlgorithmPolicyConfig(path_grid_mode="invalid")


def test_project_adapter_reads_adaptive_controls():
    fixed = {
        "dy_rel_As": 0.01, "dy_abs_max": 0.001,
        "path_grid_mode": "adaptive", "fine_grid_df": 2e6,
        "relative_threshold": 2e-3, "absolute_threshold": None,
    }
    cfg, _ = _read_project_numerical_control_178A(fixed)
    assert not hasattr(cfg, "path_grid_mode")
    assert cfg.fine_grid_df == 2e6
    assert cfg.relative_threshold == 2e-3
    assert cfg.absolute_threshold is None


@pytest.mark.parametrize("profile", ["project_standard", "sicopr_reference_v1"])
@pytest.mark.parametrize("mode", ["fixed", "adaptive"])
def test_execution_profiles_preserve_path_grid_mode(profile, mode):
    methods, _, _, _, overrides = _resolve_project_profile_178A(
        {"path_grid_mode": mode}, COMRunProfiles(), COMNumericalControlConfig(),
        True, 1e-4, profile,
    )
    assert methods.path_grid_mode == mode
    assert "alg.path_grid_mode" not in overrides
