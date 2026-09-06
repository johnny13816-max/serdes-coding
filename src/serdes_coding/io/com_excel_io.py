from __future__ import annotations

from pathlib import Path
from typing import Optional
import numpy as np

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

from ..models.com_model_178A import (
    COMDevicePackageConfig,
    COMDeviceTermConfig,
    COMConfig as COMConfig_178A,
    COMDTEConfig,
    COMExecutionConfig,
    COMFilterConfig as COMFilterConfig_178A,
    COMImpairmentConfig as COMImpairmentConfig_178A,
    COMPartialHostConfig,
    COMPkgConfig as COMPkgConfig_178A,
    COMRunConfig,
    COMSearchConfig as COMSearchConfig_178A,
)


def excel_to_config(excel_path: str) -> COMConfig:
    """
    Build COMConfig from a COM Excel workbook.

    Primary contract:
    - project-owned workbook with fixed_config / search_config / channels sheets

    Fallback adapter:
    - legacy PyChOpMarg-style workbook
    """
    excel_path_obj = Path(excel_path)
    sheet_names = _excel_sheet_names(excel_path_obj)
    if {"fixed_config", "channels"}.issubset(sheet_names):
        return _project_excel_to_config(excel_path_obj)
    return _pychopmarg_excel_to_config(excel_path_obj)


def excel_to_config_93A(excel_path: str) -> COMConfig:
    """
    Build COMConfig for the IEEE 802.3 Annex 93A model.

    This is the version-explicit name for ``excel_to_config()``.
    """
    return excel_to_config(excel_path)


def excel_to_config_178A(excel_path: str) -> COMConfig_178A:
    """
    Build COMConfig_178A from the project-owned COM workbook.

    Contract:
    - supported input is a 178A project workbook with fixed_config/run_config/channels sheets
    - fixed_config uses the native COMConfig / nested COMPkgConfig field names
    - no 93A field fallback or runtime config conversion is performed

    Raw COM ad hoc workbooks are intentionally not parsed directly here yet.
    They should first be converted into the project workbook shape.
    """
    excel_path_obj = Path(excel_path)
    sheet_names = _excel_sheet_names(excel_path_obj)
    if {"fixed_config", "run_config", "channels"}.issubset(sheet_names):
        return _project_excel_to_config_178A(excel_path_obj)
    raise ValueError(
        "excel_to_config_178A currently supports only project-owned workbooks "
        "with fixed_config/run_config/channels sheets."
    )


def excel_to_search_config_178A(excel_path: str) -> COMSearchConfig_178A:
    """Build native 178A COMSearchConfig from a project-owned workbook."""
    excel_path_obj = Path(excel_path)
    if "search_config" not in _excel_sheet_names(excel_path_obj):
        raise ValueError("178A workbook must contain a search_config sheet.")
    return _project_excel_to_search_config_178A(excel_path_obj)


def excel_to_search_config(excel_path: str) -> COMSearchConfig:
    """
    Build COMSearchConfig from a COM Excel workbook.

    Project-owned workbooks read the search_config sheet. Legacy PyChOpMarg-style
    workbooks read the range-valued equalizer fields from COM_Settings.
    """
    excel_path_obj = Path(excel_path)
    sheet_names = _excel_sheet_names(excel_path_obj)
    if {"search_config"}.issubset(sheet_names):
        return _project_excel_to_search_config(excel_path_obj)
    return _pychopmarg_excel_to_search_config(excel_path_obj)


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


def _pychopmarg_excel_to_search_config(excel_path: Path) -> COMSearchConfig:
    table = _read_excel_parameter_table(excel_path)
    return COMSearchConfig(
        c_m2_values=_sequence_setting(table, "c(-2)"),
        c_m1_values=_sequence_setting(table, "c(-1)"),
        c_1_values=_sequence_setting(table, "c(1)"),
        g_DC_values=_sequence_setting(table, "g_DC"),
        g_DC2_values=_sequence_setting(table, "g_DC_HP"),
    )


def _excel_sheet_names(excel_path: Path) -> set[str]:
    import pandas as pd

    return set(pd.ExcelFile(excel_path).sheet_names)


def _read_project_fixed_config(excel_path: Path) -> dict[str, object]:
    import pandas as pd

    df = pd.read_excel(excel_path, sheet_name="fixed_config", header=2)
    required_cols = {"Parameter", "Value"}
    if not required_cols.issubset(df.columns):
        raise ValueError("fixed_config must contain Parameter and Value columns.")

    fixed: dict[str, object] = {}
    for _, row in df.iterrows():
        name = row.get("Parameter")
        if _is_blank(name):
            continue
        fixed[str(name).strip()] = row.get("Value")
    return fixed


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


def _read_project_channels(excel_path: Path) -> COMChannelConfig:
    import pandas as pd

    df = pd.read_excel(excel_path, sheet_name="channels", header=2)
    required_cols = {"Kind", "S4P Path", "Port Order", "R0 Ohm", "Gamma Source", "Gamma Load", "Use"}
    if not required_cols.issubset(df.columns):
        raise ValueError("channels sheet is missing required columns.")

    rows = []
    for _, row in df.iterrows():
        kind = row.get("Kind")
        path_value = row.get("S4P Path")
        if _is_blank(kind) or _is_blank(path_value):
            continue
        if not _coerce_bool(row.get("Use", True)):
            continue
        rows.append(row)

    victim_paths: list[str] = []
    next_paths: list[str] = []
    fext_paths: list[str] = []
    common_port_order: Optional[tuple[int, int, int, int]] = None
    common_R0: Optional[float] = None
    common_gamma_src: Optional[complex] = None
    common_gamma_load: Optional[complex] = None

    for row in rows:
        kind = str(row["Kind"]).strip().lower()
        path_str = _resolve_channel_path(excel_path, str(row["S4P Path"]).strip())
        port_order = _parse_port_order(row["Port Order"])
        R0 = float(row["R0 Ohm"])
        gamma_src = complex(row["Gamma Source"])
        gamma_load = complex(row["Gamma Load"])

        if common_port_order is None:
            common_port_order = port_order
            common_R0 = R0
            common_gamma_src = gamma_src
            common_gamma_load = gamma_load
        elif (
            port_order != common_port_order
            or not np.isclose(R0, common_R0)
            or gamma_src != common_gamma_src
            or gamma_load != common_gamma_load
        ):
            raise ValueError(
                "COMChannelConfig currently supports one common port_order/R0/"
                "gamma_src/gamma_load across all enabled channel rows."
            )

        if kind == "victim":
            victim_paths.append(path_str)
        elif kind == "next":
            next_paths.append(path_str)
        elif kind == "fext":
            fext_paths.append(path_str)
        else:
            raise ValueError(f"Unsupported channel kind: {kind!r}.")

    if len(victim_paths) != 1:
        raise ValueError(f"channels sheet must contain exactly one enabled victim row, got {len(victim_paths)}.")
    if common_port_order is None or common_R0 is None or common_gamma_src is None or common_gamma_load is None:
        raise ValueError("channels sheet has no enabled channel rows.")

    return COMChannelConfig(
        victim_s4p_path=victim_paths[0],
        next_s4p_paths=tuple(next_paths),
        fext_s4p_paths=tuple(fext_paths),
        port_order=common_port_order,
        R0=common_R0,
        gamma_src=common_gamma_src,
        gamma_load=common_gamma_load,
    )


def _read_project_search_config(excel_path: Path) -> tuple[dict[str, Optional[np.ndarray]], dict[str, object]]:
    import pandas as pd

    df = pd.read_excel(excel_path, sheet_name="search_config", header=2)
    required_cols = {"Parameter", "Enabled", "Values"}
    if not required_cols.issubset(df.columns):
        raise ValueError("search_config must contain Parameter, Enabled, and Values columns.")

    search_param_names = {"c_m2", "c_m1", "c_1", "g_DC", "g_DC2", "g_1", "g_2"}
    setting_names = {"keep_top_n", "keep_all_rows", "continue_on_error"}
    search_params: dict[str, Optional[np.ndarray]] = {}
    settings: dict[str, object] = {}

    for _, row in df.iterrows():
        name = row.get("Parameter")
        if _is_blank(name):
            continue
        name = str(name).strip()
        enabled = _coerce_bool(row.get("Enabled", True))

        if name in search_param_names:
            search_params[name] = None if not enabled else _sequence_setting({"values": row.get("Values")}, "values")
        elif name in setting_names and enabled:
            settings[name] = row.get("Values")

    return search_params, settings


def _fixed_value(fixed: dict[str, object], name: str) -> object:
    if name not in fixed:
        raise KeyError(f"fixed_config is missing required parameter: {name}")
    return fixed[name]


def _fixed_float(fixed: dict[str, object], name: str) -> float:
    value = _fixed_value(fixed, name)
    if _is_blank(value):
        raise ValueError(f"fixed_config.{name} must not be blank.")
    return float(value)


def _fixed_optional_float(fixed: dict[str, object], name: str) -> Optional[float]:
    value = fixed.get(name)
    if _is_blank(value):
        return None
    return float(value)


def _fixed_optional_int(fixed: dict[str, object], name: str) -> Optional[int]:
    value = _fixed_optional_float(fixed, name)
    return None if value is None else int(value)


def _run_value(values: dict[str, object], profile: str, name: str) -> object:
    if name not in values:
        raise KeyError(f"run_config profile '{profile}' is missing required parameter: {name}")
    value = values[name]
    if _is_blank(value):
        raise ValueError(f"run_config.{profile}.{name} must not be blank.")
    return value


def _run_str(values: dict[str, object], profile: str, name: str) -> str:
    return str(_run_value(values, profile, name)).strip()


def _fixed_str(fixed: dict[str, object], name: str) -> str:
    value = _fixed_value(fixed, name)
    if _is_blank(value):
        raise ValueError(f"fixed_config.{name} must not be blank.")
    return str(value).strip()


def _fixed_bool(fixed: dict[str, object], name: str) -> bool:
    return _coerce_bool(_fixed_value(fixed, name))


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


def _fixed_sequence(fixed: dict[str, object], name: str) -> np.ndarray:
    return _sequence_setting({name: _fixed_value(fixed, name)}, name)


def _is_blank(value: object) -> bool:
    try:
        import pandas as pd

        if pd.isna(value):
            return True
    except Exception:
        pass
    return isinstance(value, str) and value.strip() == ""


def _coerce_bool(value: object) -> bool:
    if _is_blank(value):
        return False
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        return bool(value)
    text = str(value).strip().lower()
    if text.startswith("="):
        text = text[1:].strip()
    if text.endswith("()"):
        text = text[:-2].strip()
    if text in {"true", "yes", "y", "1"}:
        return True
    if text in {"false", "no", "n", "0"}:
        return False
    raise ValueError(f"Cannot parse boolean value: {value!r}")


def _parse_port_order(value: object) -> tuple[int, int, int, int]:
    arr = _sequence_setting({"port_order": value}, "port_order").astype(int)
    if len(arr) != 4:
        raise ValueError("Port Order must contain exactly four integers.")
    return tuple(int(x) for x in arr)


def _resolve_channel_path(excel_path: Path, value: str) -> str:
    path_value = Path(value)
    if path_value.is_absolute():
        return str(path_value)

    project_root = Path(__file__).resolve().parents[2]
    candidates = [
        excel_path.parent / path_value,
        excel_path.parent.parent / path_value,
        project_root / path_value,
        Path.cwd() / path_value,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return str((excel_path.parent / path_value).resolve())


def _read_excel_parameter_table(excel_path: Path) -> dict[str, object]:
    import pandas as pd

    df = pd.read_excel(excel_path, sheet_name="COM_Settings", header=None)
    table: dict[str, object] = {}
    for start_col in (0, 5, 9):
        block = df.iloc[:, start_col:start_col + 3]
        for _, row in block.iterrows():
            param = row.iloc[0]
            setting = row.iloc[1]
            if pd.isna(param) or str(param).strip() in {
                "Parameter",
                "Table 93A-1 parameters",
                "I/O control",
                "Table 93A?? parameters",
                "Table 92??2 parameters",
                "Operational control",
                "Receiver testing",
                "Non standard control options",
            }:
                continue
            table[str(param).strip()] = setting
    return table


def _matlab_array(value: object) -> np.ndarray:
    if isinstance(value, (int, float, np.integer, np.floating)):
        return np.asarray([float(value)], dtype=float)
    if not isinstance(value, str):
        return np.asarray(value, dtype=float)

    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1].strip()

    rows = []
    for row_text in text.split(";"):
        row_text = row_text.strip()
        if not row_text:
            continue
        parts = row_text.replace(",", " ").split()
        if len(parts) == 1 and ":" in parts[0]:
            lo, step, hi = [float(x) for x in parts[0].split(":")]
            n = int(round((hi - lo) / step)) + 1
            values = lo + step * np.arange(n)
            values[np.isclose(values, 0.0, atol=1e-15)] = 0.0
            rows.append(values)
        else:
            rows.append(np.asarray([float(x) for x in parts], dtype=float))

    if len(rows) == 0:
        raise ValueError(f"Cannot parse MATLAB-style array: {value!r}")
    if len(rows) == 1:
        return rows[0]
    return np.vstack(rows)


def _sequence_setting(table: dict[str, object], name: str) -> np.ndarray:
    return np.ravel(_matlab_array(table[name])).astype(float)


def _first_setting(table: dict[str, object], name: str) -> float:
    return float(_sequence_setting(table, name)[0])


def _scalar_setting(table: dict[str, object], name: str) -> float:
    arr = _sequence_setting(table, name)
    if len(arr) != 1:
        raise ValueError(f"{name} must be scalar, got {table[name]!r}.")
    return float(arr[0])


def _vector_setting(table: dict[str, object], name: str) -> np.ndarray:
    return _sequence_setting(table, name)


def _matrix_setting(table: dict[str, object], name: str) -> np.ndarray:
    arr = _matlab_array(table[name])
    if arr.ndim == 1:
        return arr
    return arr.astype(float)
