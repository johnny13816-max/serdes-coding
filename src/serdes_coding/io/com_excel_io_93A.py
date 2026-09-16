from __future__ import annotations

from pathlib import Path

from ..utilities.link import LinkConfig
from ..models.com_model_93A import (
    COMChannelConfig,
    COMConfig,
    COMDFEConfig,
    COMFilterConfig,
    COMImpairmentConfig as COMImpairmentConfig_93A,
    COMPMFConfig,
    COMSearchConfig,
    COMPkgConfig,
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


def excel_to_config_93A(excel_path: str) -> COMConfig:
    """Build native 93A COMConfig from a project or legacy Ad Hoc workbook."""
    path = Path(excel_path)
    sheets = _excel_sheet_names(path)
    if {"fixed_config", "channels"}.issubset(sheets):
        return _project_excel_to_config(path)
    return _pychopmarg_excel_to_config(path)


def excel_to_search_config_93A(excel_path: str) -> COMSearchConfig:
    """Build native 93A COMSearchConfig from a supported workbook."""
    path = Path(excel_path)
    if "search_config" in _excel_sheet_names(path):
        return _project_excel_to_search_config(path)
    return _pychopmarg_excel_to_search_config(path)

def _project_excel_to_config(excel_path: Path) -> COMConfig:
    fixed = _read_project_fixed_config(excel_path)
    channel = _read_project_channels(excel_path)

    return COMConfig(
        link=LinkConfig(
            fb=_fixed_float(fixed, "fb"),
            per_ui=int(_fixed_float(fixed, "per_ui")),
            target_df=_fixed_float(fixed, "target_df"),
        ),
        filter=COMFilterConfig(
            c_m3=_fixed_float(fixed, "c_m3"),
            c_m2=_fixed_float(fixed, "c_m2"),
            c_m1=_fixed_float(fixed, "c_m1"),
            c_1=_fixed_float(fixed, "c_1"),
            num_pre=int(_fixed_float(fixed, "num_pre")),
            Tr=_fixed_float(fixed, "Tr"),
            fr=_fixed_float(fixed, "fr"),
            g_DC=_fixed_float(fixed, "g_DC"),
            g_DC2=_fixed_float(fixed, "g_DC2"),
            # 93A uses the Ad Hoc 93A names; these map to the native
            # runtime fields directly.  The 178A f_z1/f_z2/f_p3 schema does
            # not apply to this model.
            f_z=_fixed_float(fixed, "f_z"),
            f_LF=_fixed_float(fixed, "f_LF"),
            f_p1=_fixed_float(fixed, "f_p1"),
            f_p2=_fixed_float(fixed, "f_p2"),
            A_v=_fixed_float(fixed, "A_v"),
            A_fe=_fixed_float(fixed, "A_fe"),
            A_ne=_fixed_float(fixed, "A_ne"),
        ),
        channel=channel,
        txpkg_victim=_fixed_pkg_config(fixed, "txpkg_victim"),
        txpkg_fext=_fixed_pkg_config(fixed, "txpkg_fext"),
        txpkg_next=_fixed_pkg_config(fixed, "txpkg_next"),
        rxpkg=_fixed_pkg_config(fixed, "rxpkg"),
        dfe=COMDFEConfig(
            N_b=int(_fixed_float(fixed, "N_b")),
            b_max=_fixed_float(fixed, "b_max"),
        ),
        imp=COMImpairmentConfig_93A(
            R_LM=_fixed_float(fixed, "R_LM"),
            SNR_TX=_fixed_float(fixed, "SNR_TX"),
            sigma_RJ=_fixed_float(fixed, "sigma_RJ"),
            A_DD=_fixed_float(fixed, "A_DD"),
            eta_0=_fixed_float(fixed, "eta_0"),
        ),
        L=int(_fixed_float(fixed, "L")),
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
    )


def _pychopmarg_excel_to_config(excel_path: Path) -> COMConfig:
    """
    Build COMConfig from a PyChOpMarg-style Excel config table.

    This is a source-specific fallback adapter, not the primary v1.0 Excel
    contract. Project-owned workbooks should use fixed_config/search_config/
    channels instead.
    """
    table = _read_excel_parameter_table(excel_path)
    project_root = Path(__file__).resolve().parents[2]
    chnl_dir = project_root / "reference_data" / "pychopmarg_example2" / "chnl_data"

    f_b = _scalar_setting(table, "f_b") * 1e9
    per_ui = int(_scalar_setting(table, "M"))
    target_df = _scalar_setting(table, "Delta_f") * 1e9
    z_p_idx = int(_scalar_setting(table, "z_p select")) - 1

    C_d = _matrix_setting(table, "C_d") * 1e-9
    L_s = _matrix_setting(table, "L_s") * 1e-9
    C_b = _matrix_setting(table, "C_b") * 1e-9
    C_p = _matrix_setting(table, "C_p") * 1e-9
    z_p_tx = _vector_setting(table, "z_p (TX)")
    package_Z_c = _matrix_setting(table, "package_Z_c")
    legacy_pkg = COMPkgConfig(
        C_d=float(C_d[0, 0]),
        L_s=float(L_s[0, 0]),
        C_b=float(C_b[0]),
        z_p=float(z_p_tx[z_p_idx]),
        C_p=float(C_p[0]),
        enable=bool(_scalar_setting(table, "INC_PACKAGE")),
        R0=_scalar_setting(table, "R_0"),
        Z_c=float(package_Z_c[0, 0]),
        z_p2=None,
        Z_c2=float(package_Z_c[0, 1]) if package_Z_c.shape[1] > 1 else float(package_Z_c[0, 0]),
    )

    port_order = tuple(int(x) - 1 for x in _vector_setting(table, "Port Order"))
    if len(port_order) != 4:
        raise ValueError("Port Order must contain exactly four ports.")

    return COMConfig(
        link=LinkConfig(
            fb=f_b,
            per_ui=per_ui,
            target_df=target_df,
        ),
        filter=COMFilterConfig(
            c_m3=0.0,
            c_m2=0.0,
            c_m1=0.0,
            c_1=0.0,
            num_pre=int(_scalar_setting(table, "ffe_pre_tap_len")) - 2,
            Tr=_scalar_setting(table, "T_r") * 1e-9,
            fr=_scalar_setting(table, "f_r") * f_b,
            g_DC=_first_setting(table, "g_DC"),
            g_DC2=_first_setting(table, "g_DC_HP"),
            f_z=_scalar_setting(table, "f_z") * 1e9,
            f_LF=_scalar_setting(table, "f_HP_PZ") * 1e9,
            f_p1=_scalar_setting(table, "f_p1") * 1e9,
            f_p2=_scalar_setting(table, "f_p2") * 1e9,
            A_v=_scalar_setting(table, "A_v"),
            A_fe=_scalar_setting(table, "A_fe"),
            A_ne=_scalar_setting(table, "A_ne"),
        ),
        channel=COMChannelConfig(
            victim_s4p_path=str(chnl_dir / "example2_THRU.s4p"),
            next_s4p_paths=(
                str(chnl_dir / "example2_NEXT1.s4p"),
                str(chnl_dir / "example2_NEXT2.s4p"),
                str(chnl_dir / "example2_NEXT3.s4p"),
            ),
            fext_s4p_paths=(
                str(chnl_dir / "example2_FEXT1.s4p"),
                str(chnl_dir / "example2_FEXT2.s4p"),
            ),
            port_order=port_order,
            R0=_scalar_setting(table, "R_0"),
            gamma_src=0.0,
            gamma_load=0.0,
        ),
        txpkg_victim=legacy_pkg,
        txpkg_fext=legacy_pkg,
        txpkg_next=legacy_pkg,
        rxpkg=legacy_pkg,
        dfe=COMDFEConfig(
            N_b=int(_scalar_setting(table, "N_b")),
            b_max=_scalar_setting(table, "b_max(1)"),
        ),
        imp=COMImpairmentConfig_93A(
            R_LM=_scalar_setting(table, "R_LM"),
            SNR_TX=_scalar_setting(table, "SNR_TX"),
            sigma_RJ=_scalar_setting(table, "sigma_RJ"),
            A_DD=_scalar_setting(table, "A_DD"),
            eta_0=_scalar_setting(table, "eta_0") / 1e9,
        ),
        L=int(_scalar_setting(table, "L")),
        DER_0=_scalar_setting(table, "DER_0"),
    )


def _project_excel_to_search_config(excel_path: Path) -> COMSearchConfig:
    search_params, search_settings = _read_project_search_config(excel_path)
    return COMSearchConfig(
        c_m2_values=search_params.get("c_m2"),
        c_m1_values=search_params.get("c_m1"),
        c_1_values=search_params.get("c_1"),
        g_DC_values=search_params.get("g_DC"),
        g_DC2_values=search_params.get("g_DC2"),
        keep_top_n=int(search_settings.get("keep_top_n", 10)),
        keep_all_rows=_coerce_bool(search_settings.get("keep_all_rows", False)),
        continue_on_error=_coerce_bool(search_settings.get("continue_on_error", False)),
    )


def _pychopmarg_excel_to_search_config(excel_path: Path) -> COMSearchConfig:
    table = _read_excel_parameter_table(excel_path)
    return COMSearchConfig(
        c_m2_values=_sequence_setting(table, "c(-2)"),
        c_m1_values=_sequence_setting(table, "c(-1)"),
        c_1_values=_sequence_setting(table, "c(1)"),
        g_DC_values=_sequence_setting(table, "g_DC"),
        g_DC2_values=_sequence_setting(table, "g_DC_HP"),
    )


def _fixed_pkg_config(fixed: dict[str, object], prefix: str) -> COMPkgConfig:
    return COMPkgConfig(
        C_d=_fixed_float(fixed, f"{prefix}.C_d"),
        L_s=_fixed_float(fixed, f"{prefix}.L_s"),
        C_b=_fixed_float(fixed, f"{prefix}.C_b"),
        z_p=_fixed_float(fixed, f"{prefix}.z_p"),
        C_p=_fixed_float(fixed, f"{prefix}.C_p"),
        enable=_fixed_bool(fixed, f"{prefix}.enable"),
        R0=_fixed_float(fixed, f"{prefix}.R0"),
        Z_c=_fixed_float(fixed, f"{prefix}.Z_c"),
        z_p2=_fixed_optional_float(fixed, f"{prefix}.z_p2"),
        Z_c2=_fixed_float(fixed, f"{prefix}.Z_c2"),
    )

__all__ = ["excel_to_config_93A", "excel_to_search_config_93A"]
