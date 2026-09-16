from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from ..models.com_model_93A import COMChannelConfig

def _excel_sheet_names(excel_path: Path) -> set[str]:
    import pandas as pd

    return set(pd.ExcelFile(excel_path).sheet_names)


def _read_project_fixed_config(excel_path: Path) -> dict[str, object]:
    import pandas as pd

    df = pd.read_excel(excel_path, sheet_name="fixed_config", header=2)
    required_cols = {"Parameter", "Value"}
    if not required_cols.issubset(df.columns):
        raise ValueError("fixed_config must contain Parameter and Value columns.")

    if "Parameter Class" in df.columns:
        allowed_classes = {"intrinsic", "policy", "derived", "runtime", "compatibility"}
        invalid = {str(v).strip() for v in df["Parameter Class"].dropna()} - allowed_classes
        if invalid:
            raise ValueError(f"fixed_config contains unsupported Parameter Class values: {sorted(invalid)}")

    fixed: dict[str, object] = {}
    for _, row in df.iterrows():
        name = row.get("Parameter")
        if _is_blank(name):
            continue
        fixed[str(name).strip()] = row.get("Value")
    return fixed


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

    fixed = _read_project_fixed_config(excel_path)
    missing_dc_policy = str(fixed.get("missing_dc_policy", "error")).strip().lower()
    return COMChannelConfig(
        victim_s4p_path=victim_paths[0],
        next_s4p_paths=tuple(next_paths),
        fext_s4p_paths=tuple(fext_paths),
        port_order=common_port_order,
        R0=common_R0,
        gamma_src=common_gamma_src,
        gamma_load=common_gamma_load,
        missing_dc_policy=missing_dc_policy,
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

__all__ = [
    "_coerce_bool", "_excel_sheet_names", "_fixed_bool", "_fixed_float",
    "_fixed_optional_float", "_fixed_optional_int", "_fixed_sequence",
    "_fixed_str", "_fixed_value", "_first_setting", "_is_blank",
    "_matrix_setting", "_parse_port_order", "_read_excel_parameter_table",
    "_read_project_channels", "_read_project_fixed_config",
    "_read_project_search_config", "_resolve_channel_path", "_run_str",
    "_run_value", "_scalar_setting", "_sequence_setting", "_vector_setting",
]
