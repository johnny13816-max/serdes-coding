from __future__ import annotations

from pathlib import Path

from ..utilities.link import LinkConfig
from ..models.com_model_93A import COMPMFConfig
from ..models.com_model_178A import (
    COMDevicePackageConfig,
    COMDeviceTermConfig,
    COMConfig as COMConfig_178A,
    COMDTEConfig,
    COMExecutionConfig,
    COMFilterConfig as COMFilterConfig_178A,
    COMImpairmentConfig as COMImpairmentConfig_178A,
    COMMLSDConfig,
    COMPartialHostConfig,
    COMPkgConfig as COMPkgConfig_178A,
    COMRunConfig,
    COMSearchConfig as COMSearchConfig_178A,
)
from .com_excel_common import (
    _coerce_bool,
    _excel_sheet_names,
    _fixed_bool,
    _fixed_float,
    _fixed_optional_float,
    _fixed_optional_int,
    _fixed_sequence,
    _fixed_str,
    _first_setting,
    _is_blank,
    _matrix_setting,
    _read_excel_parameter_table,
    _read_project_channels,
    _read_project_fixed_config,
    _read_project_search_config,
    _run_str,
    _run_value,
    _scalar_setting,
    _sequence_setting,
    _vector_setting,
)


def excel_to_config_178A(excel_path: str) -> COMConfig:
    """Build native 178A COMConfig from a project-owned workbook."""
    path = Path(excel_path)
    sheets = _excel_sheet_names(path)
    if {"fixed_config", "run_config", "channels"}.issubset(sheets):
        return _project_excel_to_config_178A(path)
    raise ValueError(
        "excel_to_config_178A supports only project-owned workbooks with "
        "fixed_config/run_config/channels sheets."
    )


def excel_to_search_config_178A(excel_path: str) -> COMSearchConfig:
    """Build native 178A COMSearchConfig from a project-owned workbook."""
    path = Path(excel_path)
    if "search_config" not in _excel_sheet_names(path):
        raise ValueError("178A workbook must contain a search_config sheet.")
    return _project_excel_to_search_config_178A(path)

def _project_excel_to_config_178A(excel_path: Path) -> COMConfig_178A:
    fixed = _read_project_fixed_config(excel_path)
    channel = _read_project_channels(excel_path)

    link_cfg = LinkConfig(
        fb=_fixed_float(fixed, "fb"),
        per_ui=int(_fixed_float(fixed, "per_ui")),
        target_df=_fixed_float(fixed, "target_df"),
    )

    return COMConfig_178A(
        L=int(_fixed_float(fixed, "L")),
        link=link_cfg,
        filter=COMFilterConfig_178A(
            c_m3=_fixed_float(fixed, "c_m3"),
            c_m2=_fixed_float(fixed, "c_m2"),
            c_m1=_fixed_float(fixed, "c_m1"),
            c_1=_fixed_float(fixed, "c_1"),
            c_0_min=_fixed_float(fixed, "c_0_min"),
            num_pre=int(_fixed_float(fixed, "num_pre")),
            Tr=_fixed_optional_float(fixed, "Tr"),
            fr=_fixed_optional_float(fixed, "fr"),
            g_1=_fixed_float(fixed, "g_1"),
            g_2=_fixed_float(fixed, "g_2"),
            f_z1=_fixed_float(fixed, "f_z1"),
            f_z2=_fixed_float(fixed, "f_z2"),
            f_p1=_fixed_float(fixed, "f_p1"),
            f_p2=_fixed_float(fixed, "f_p2"),
            f_p3=_fixed_optional_float(fixed, "f_p3"),
            A_v=_fixed_float(fixed, "A_v"),
            A_fe=_fixed_float(fixed, "A_fe"),
            A_ne=_fixed_float(fixed, "A_ne"),
        ),
        channel=channel,
        txpkg_victim=_fixed_pkg_config_178A(fixed, "txpkg_victim"),
        txpkg_fext=_fixed_pkg_config_178A(fixed, "txpkg_fext"),
        txpkg_next=_fixed_pkg_config_178A(fixed, "txpkg_next"),
        rxpkg=_fixed_pkg_config_178A(fixed, "rxpkg"),
        dte=COMDTEConfig(
            w_pre1_max=_fixed_float(fixed, "w_pre1_max"),
            w_post1_max=_fixed_float(fixed, "w_post1_max"),
            w_fixed_rest_max=_fixed_float(fixed, "w_fixed_rest_max"),
            w_float_max=_fixed_float(fixed, "w_float_max"),
            w_float_min=_fixed_float(fixed, "w_float_min"),
            b_first_max=_fixed_float(fixed, "b_first_max"),
            b_first_min=_fixed_float(fixed, "b_first_min"),
            b_rest_max=_fixed_float(fixed, "b_rest_max"),
            b_rest_min=_fixed_float(fixed, "b_rest_min"),
            d_w=int(_fixed_float(fixed, "d_w")),
            N_fix=int(_fixed_float(fixed, "N_fix")),
            N_wg=int(_fixed_float(fixed, "N_wg")),
            N_wf=int(_fixed_float(fixed, "N_wf")),
            N_max=int(_fixed_float(fixed, "N_max")),
            N_b=int(_fixed_float(fixed, "N_b")),
        ),
        imp=COMImpairmentConfig_178A(
            R_LM=_fixed_float(fixed, "R_LM"),
            SNR_TX=_fixed_float(fixed, "SNR_TX"),
            sigma_RJ=_fixed_float(fixed, "sigma_RJ"),
            A_DD=_fixed_float(fixed, "A_DD"),
            eta_0=_fixed_float(fixed, "eta_0"),
            N_qb=_fixed_optional_int(fixed, "N_qb"),
            P_qc=_fixed_optional_float(fixed, "P_qc"),
        ),
        DER_0=_fixed_float(fixed, "DER_0"),
        pmf=COMPMFConfig(
            dy_override=_fixed_optional_float(fixed, "dy_override"),
            dy_rel_As=_fixed_float(fixed, "dy_rel_As"),
            dy_abs_max=_fixed_float(fixed, "dy_abs_max"),
            tap_abs_th_override=_fixed_optional_float(fixed, "tap_abs_th_override"),
            tap_rel_As=_fixed_float(fixed, "tap_rel_As"),
            keep_mass=_fixed_float(fixed, "keep_mass"),
            gaussian_n_sigma=_fixed_float(fixed, "gaussian_n_sigma"),
        ),
        execution=_read_project_execution_config(excel_path),
        mlsd=COMMLSDConfig(
            enable=_coerce_bool(fixed.get("mlsd_enable", False)),
            trunc_len=_fixed_optional_int(fixed, "mlsd_trunc_len") or 0,
            delta_com_an=_fixed_optional_float(fixed, "delta_com_an"),
            minimum_com_limit=_fixed_optional_float(fixed, "minimum_com_limit"),
        ),
    )


def _project_excel_to_search_config_178A(excel_path: Path) -> COMSearchConfig_178A:
    search_params, search_settings = _read_project_search_config(excel_path)
    return COMSearchConfig_178A(
        c_m2_values=search_params.get("c_m2"),
        c_m1_values=search_params.get("c_m1"),
        c_1_values=search_params.get("c_1"),
        g_DC_values=search_params.get("g_1"),
        g_DC2_values=search_params.get("g_2"),
        keep_top_n=int(search_settings.get("keep_top_n", 10)),
        keep_all_rows=_coerce_bool(search_settings.get("keep_all_rows", False)),
        continue_on_error=_coerce_bool(search_settings.get("continue_on_error", False)),
    )


def _read_project_execution_config(excel_path: Path) -> COMExecutionConfig:
    """Read 178A execution profiles from the project-owned ``run_config`` sheet."""
    import pandas as pd

    df = pd.read_excel(excel_path, sheet_name="run_config", header=2)
    required_cols = {"Profile", "Parameter", "Value"}
    if not required_cols.issubset(df.columns):
        raise ValueError("run_config must contain Profile, Parameter, and Value columns.")

    profiles: dict[str, dict[str, object]] = {}
    for _, row in df.iterrows():
        profile = row.get("Profile")
        parameter = row.get("Parameter")
        if _is_blank(profile) or _is_blank(parameter):
            continue
        profiles.setdefault(str(profile).strip(), {})[str(parameter).strip()] = row.get("Value")

    def run_profile(name: str) -> COMRunConfig:
        values = profiles.get(name, {})
        return COMRunConfig(
            target=_run_str(values, name, "target"),
            pre_dte_pmf_method=_run_str(values, name, "pre_dte_pmf_method"),
            pmf_grid_quality=_run_str(values, name, "pmf_grid_quality"),
            floating_mode=_run_str(values, name, "floating_mode"),
            pos_sweep_method=_run_str(values, name, "pos_sweep_method"),
            pos_coarse_stride=int(_run_value(values, name, "pos_coarse_stride")),
        )

    search_values = profiles.get("search", {})
    return COMExecutionConfig(
        single_run=run_profile("single_run"),
        search_sweep=run_profile("search_sweep"),
        search_final=run_profile("search_final"),
        search_group_size=int(_run_value(search_values, "search", "group_size")),
        search_top_k=int(_run_value(search_values, "search", "top_k")),
    )


def _fixed_pkg_config_178A(fixed: dict[str, object], prefix: str) -> COMPkgConfig_178A:
    return COMPkgConfig_178A(
        device_term=COMDeviceTermConfig(
            C_d_seq=_fixed_sequence(fixed, f"{prefix}.device_term.C_d_seq"),
            L_s_seq=_fixed_sequence(fixed, f"{prefix}.device_term.L_s_seq"),
            C_b=_fixed_float(fixed, f"{prefix}.device_term.C_b"),
        ),
        device_pkg=COMDevicePackageConfig(
            z_p_seq=_fixed_sequence(fixed, f"{prefix}.device_pkg.z_p_seq"),
            Z_c_seq=_fixed_sequence(fixed, f"{prefix}.device_pkg.Z_c_seq"),
            gamma_0=_fixed_float(fixed, f"{prefix}.device_pkg.gamma_0"),
            a1=_fixed_float(fixed, f"{prefix}.device_pkg.a1"),
            a2=_fixed_float(fixed, f"{prefix}.device_pkg.a2"),
            tau=_fixed_float(fixed, f"{prefix}.device_pkg.tau"),
            C_p=_fixed_float(fixed, f"{prefix}.device_pkg.C_p"),
        ),
        partial_host=COMPartialHostConfig(
            enable=_fixed_bool(fixed, f"{prefix}.partial_host.enable"),
            C_0=_fixed_float(fixed, f"{prefix}.partial_host.C_0"),
            C_1=_fixed_float(fixed, f"{prefix}.partial_host.C_1"),
            z_h=_fixed_float(fixed, f"{prefix}.partial_host.z_h"),
            Z_h=_fixed_float(fixed, f"{prefix}.partial_host.Z_h"),
            gamma_0=_fixed_float(fixed, f"{prefix}.partial_host.gamma_0"),
            a1=_fixed_float(fixed, f"{prefix}.partial_host.a1"),
            a2=_fixed_float(fixed, f"{prefix}.partial_host.a2"),
            tau=_fixed_float(fixed, f"{prefix}.partial_host.tau"),
        ),
        R0=_fixed_float(fixed, f"{prefix}.R0"),
    )

__all__ = ["excel_to_config_178A", "excel_to_search_config_178A"]
