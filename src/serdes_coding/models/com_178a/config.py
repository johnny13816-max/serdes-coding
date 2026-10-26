"""Version-owned Annex 178A configuration contracts."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Literal, Optional, Sequence

import numpy as np

from ...utilities.link import LinkConfig
from ...utilities.sparam import SparamModel
from ..com_dataclass_text import COMDataclassText, TextField, TextSection
from .errors import COMLengthMismatchError, COMTxfirMainCursorError


class _LeafConfigText(COMDataclassText):
    """Semantic text fallback for version-owned leaf configuration."""

    _FIELD_UNITS: dict[str, str] = {}

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection(
                "Configuration",
                tuple(
                    self._field(item.name, item.name, stored_unit=self._FIELD_UNITS.get(item.name))
                    for item in fields(self)
                ),
            ),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        selected = tuple(item for item in fields(self) if item.init)[:3]
        return tuple(
            self._field(item.name, item.name, stored_unit=self._FIELD_UNITS.get(item.name))
            for item in selected
        )


@dataclass(repr=False)
class COMChannelConfig(_LeafConfigText):
    """
    Victim and crosstalk channel configuration using internal formula units.

    freqs and s4p are populated after Touchstone loading. Excel can directly
    provide the path fields first.
    """
    _FIELD_UNITS = {
        "R0": "ohm",
        "R_d_tx": "ohm",
        "R_d_rx": "ohm",
        "victim_s4p_path": "filesystem path",
        "next_s4p_paths": "filesystem paths",
        "fext_s4p_paths": "filesystem paths",
        "port_order": "zero-based port indices",
        "gamma_src": "dimensionless",
        "gamma_load": "dimensionless",
        "missing_dc_policy": "policy",
        "sparam_frequency_limit_Hz": "Hz",
    }
    R0: float                                               # unit: ohm, single-ended reference resistance
    R_d_tx: float                                           # unit: ohm, TX die termination resistance
    R_d_rx: float                                           # unit: ohm, RX die termination resistance
    victim_s4p_path: Optional[str] = None                   # unit: filesystem path
    next_s4p_paths: Sequence[str] = ()                      # unit: filesystem paths
    fext_s4p_paths: Sequence[str] = ()                      # unit: filesystem paths
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3)    # unit: zero-based S4P port order
    gamma_src: complex = field(init=False)                  # unit: dimensionless, derived from R_d_tx and R0
    gamma_load: complex = field(init=False)                 # unit: dimensionless, derived from R_d_rx and R0
    missing_dc_policy: Literal["error", "hold", "skrf"] = "error"
    sparam_frequency_limit_Hz: Optional[float] = None       # unit: Hz; measured-record boundary

    def __post_init__(self) -> None:
        for name in ("R0", "R_d_tx", "R_d_rx"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive.")
            setattr(self, name, value)

        self.gamma_src = complex((self.R_d_tx - self.R0) / (self.R_d_tx + self.R0))
        self.gamma_load = complex((self.R_d_rx - self.R0) / (self.R_d_rx + self.R0))
        if self.missing_dc_policy not in {"error", "hold", "skrf"}:
            raise ValueError("missing_dc_policy must be error, hold, or skrf.")
        if self.sparam_frequency_limit_Hz is not None:
            value = float(self.sparam_frequency_limit_Hz)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError("sparam_frequency_limit_Hz must be finite and positive.")
            self.sparam_frequency_limit_Hz = value

    def align_grid(self, channels: list[SparamModel]) -> np.ndarray:
        """
        Build the channel alignment grid for channel-under-test models.

        Contract:
        - f_min = max(channel f_min), so no low-frequency extrapolation is needed
        - f_max = min(channel f_max), so no high-frequency extrapolation is needed
        - df = min(channel df), preserving the finest measured resolution
        """
        if len(channels) == 0:
            raise ValueError("At least one channel-under-test is required.")

        f_min = max(float(channel.freqs[0]) for channel in channels)
        f_max = min(float(channel.freqs[-1]) for channel in channels)
        dfs = []
        for channel in channels:
            if len(channel.freqs) < 2:
                raise ValueError("Each channel frequency grid must contain at least two points.")
            dfs.append(float(channel.freqs[1] - channel.freqs[0]))

        df = min(dfs)
        if not np.isfinite(df) or df <= 0.0:
            raise ValueError("Measured channel df must be finite and positive.")
        if f_max <= f_min:
            raise ValueError("No overlapping measured frequency band across channel-under-test models.")

        n = int(np.floor((f_max - f_min) / df)) + 1
        if n < 2:
            raise ValueError("Common measured frequency grid must contain at least two points.")

        return f_min + np.arange(n) * df

    def measured_grid_summary(self) -> list[dict[str, object]]:
        """
        Return measured frequency-grid summaries for configured channel files.

        The summary is for configuration/debug visibility only. It reads each
        Touchstone file and reports the raw measured f_min, f_max, and delta_f.
        """
        rows: list[tuple[str, Optional[str]]] = [
            ("victim", self.victim_s4p_path),
            *[("next", path) for path in self.next_s4p_paths],
            *[("fext", path) for path in self.fext_s4p_paths],
        ]

        summary: list[dict[str, object]] = []
        for kind, path in rows:
            if path is None:
                summary.append({"kind": kind, "path": None, "status": "missing path"})
                continue

            try:
                channel = SparamModel.from_touchstone(
                    path,
                    representation="s4p",
                    port_order=self.port_order,
                )
                raw_f_max = float(channel.freqs[-1])
                channel = (
                    channel
                    if self.sparam_frequency_limit_Hz is None
                    else channel.limited_to_frequency(self.sparam_frequency_limit_Hz)
                )
                freqs = channel.freqs
                delta_f = float(freqs[1] - freqs[0]) if len(freqs) > 1 else float("nan")
                summary.append({
                    "kind": kind,
                    "path": str(path),
                    "n": len(freqs),
                    "f_min": float(freqs[0]),
                    "f_max": float(freqs[-1]),
                    "raw_f_max": raw_f_max,
                    "requested_frequency_limit_Hz": self.sparam_frequency_limit_Hz,
                    "effective_f_max": float(freqs[-1]),
                    "delta_f": delta_f,
                })
            except Exception as exc:
                summary.append({
                    "kind": kind,
                    "path": str(path),
                    "status": f"unreadable: {exc}",
                })

        return summary

    def aligned_grid_summary(self) -> dict[str, object]:
        """
        Return the planned common measured-domain grid for channel processing.

        Contract:
        - use only the overlapping measured frequency band
        - choose the smallest measured df among all channels
        - do not extrapolate any channel in S-parameter domain
        """
        try:
            channels = [
                SparamModel.from_touchstone(
                    path,
                    representation="s4p",
                    port_order=self.port_order,
                )
                for path in [
                    self.victim_s4p_path,
                    *self.next_s4p_paths,
                    *self.fext_s4p_paths,
                ]
                if path is not None
            ]
            if self.sparam_frequency_limit_Hz is not None:
                channels = [
                    channel.limited_to_frequency(self.sparam_frequency_limit_Hz)
                    for channel in channels
                ]
            freqs = self.align_grid(channels)
            return {
                "status": "ok",
                "n": len(freqs),
                "f_min": float(freqs[0]),
                "f_max": float(freqs[-1]),
                "delta_f": float(freqs[1] - freqs[0]),
            }
        except Exception as exc:
            return {"status": f"unavailable: {exc}"}

    def _pretty(self, indent: int = 0) -> str:
        pad = " " * indent
        inner_pad = " " * (indent + 2)
        lines = [f"{pad}{type(self).__name__}("]
        for item in fields(self):
            value = getattr(self, item.name)
            lines.append(f"{inner_pad}{item.name}={self._format_value(value, indent + 2, item.name)},")

        lines.append(f"{inner_pad}measured_channels=[")
        for row in self.measured_grid_summary():
            if "f_min" in row:
                lines.append(
                    f"{inner_pad}  "
                    f"{{kind={row['kind']!r}, n={row['n']}, "
                    f"f_min={self._format_frequency(row['f_min'])}, "
                    f"f_max={self._format_frequency(row['f_max'])}, "
                    f"delta_f={self._format_frequency(row['delta_f'])}, "
                    f"path={row['path']!r}}},"
                )
            else:
                lines.append(
                    f"{inner_pad}  "
                    f"{{kind={row['kind']!r}, status={row['status']!r}, path={row['path']!r}}},"
                )
        lines.append(f"{inner_pad}],")

        aligned = self.aligned_grid_summary()
        if aligned.get("status") == "ok":
            lines.append(
                f"{inner_pad}aligned_measured_grid="
                f"{{n={aligned['n']}, "
                f"f_min={self._format_frequency(aligned['f_min'])}, "
                f"f_max={self._format_frequency(aligned['f_max'])}, "
                f"delta_f={self._format_frequency(aligned['delta_f'])}}},"
            )
        else:
            lines.append(f"{inner_pad}aligned_measured_grid={aligned},")
        lines.append(f"{pad})")
        return "\n".join(lines)

@dataclass(repr=False)
class COMPMFConfig(_LeafConfigText):
    """
    PMF-domain configuration for Annex 178A interference/noise distributions.

    This config owns only amplitude-axis and PMF numerical controls. It does
    not own channel construction, DFE selection, or imp statistics.
    """
    _FIELD_UNITS = {
        "dy_override": "V",
        "dy_rel_As": "relative amplitude",
        "dy_abs_max": "V",
        "tap_abs_th_override": "V",
        "tap_rel_As": "relative amplitude",
        "keep_mass": "probability",
        "gaussian_n_sigma": "sigma count",
    }
    dy_override: Optional[float] = None # unit: V, explicit PMF amplitude grid step; if None derive from As
    dy_rel_As: float = 1e-3           # unit: dimensionless, default dy limit = 0.1% of As (from spec)
    dy_abs_max: float = 0.01e-3       # unit: V, default dy absolute limit = 0.01 mV (from spec)
    tap_abs_th_override: Optional[float] = None # unit: V, explicit tap threshold; if None derive from As
    tap_rel_As: float = 1e-3          # unit: dimensionless, ignore pulse terms below 0.1% of As (from spec)
    keep_mass: float = float(1 - 1e-5) # unit: probability, optional PMF truncation target
    gaussian_n_sigma: float = 8.0     # unit: sigma, half span for Gaussian PMF construction

    def __post_init__(self) -> None:
        if self.dy_override is not None:
            self.dy_override = float(self.dy_override)
            if not np.isfinite(self.dy_override) or self.dy_override <= 0.0:
                raise ValueError("COMPMFConfig.dy_override must be finite and positive.")

        if self.tap_abs_th_override is not None:
            self.tap_abs_th_override = float(self.tap_abs_th_override)
            if not np.isfinite(self.tap_abs_th_override) or self.tap_abs_th_override < 0.0:
                raise ValueError("COMPMFConfig.tap_abs_th_override must be finite and non-negative.")

        for name in ("dy_rel_As", "dy_abs_max", "tap_rel_As", "gaussian_n_sigma"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"COMPMFConfig.{name} must be finite and positive.")
            setattr(self, name, value)

        self.keep_mass = float(self.keep_mass)
        if not np.isfinite(self.keep_mass) or self.keep_mass <= 0.0 or self.keep_mass > 1.0:
            raise ValueError("COMPMFConfig.keep_mass must be finite and in (0, 1].")

    def resolve(
        self,
        As: float,
        grid_quality: Literal["coarse", "fine"] = "fine",
    ) -> 'COMPMFRuntimeConfig':
        As_abs = abs(float(As))
        if not np.isfinite(As_abs) or As_abs <= 0.0:
            raise ValueError("As must be finite and positive to resolve COMPMFConfig.")
        if grid_quality not in {"coarse", "fine"}:
            raise ValueError("grid_quality must be 'coarse' or 'fine'.")

        if self.dy_override is not None:
            dy = self.dy_override
        elif grid_quality == "coarse":
            dy = self.dy_rel_As * As_abs
        else:
            dy = min(self.dy_abs_max, self.dy_rel_As * As_abs)
        tap_abs_th = (
            self.tap_abs_th_override
            if self.tap_abs_th_override is not None
            else self.tap_rel_As * As_abs
        )
        return COMPMFRuntimeConfig(
            dy=dy,
            tap_abs_th=tap_abs_th,
            keep_mass=self.keep_mass,
            gaussian_n_sigma=self.gaussian_n_sigma,
        )

@dataclass(repr=False)
class COMPMFRuntimeConfig(_LeafConfigText):
    """Resolved PMF numerical settings for one COM run."""
    _FIELD_UNITS = {
        "dy": "V",
        "tap_abs_th": "V",
        "keep_mass": "probability",
        "gaussian_n_sigma": "sigma count",
    }
    dy: float                         # unit: V, resolved PMF amplitude grid step
    tap_abs_th: float                 # unit: V, resolved absolute tap threshold
    keep_mass: float                  # unit: probability
    gaussian_n_sigma: float           # unit: sigma

    def __post_init__(self) -> None:
        for name in ("dy", "gaussian_n_sigma"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"COMPMFRuntimeConfig.{name} must be finite and positive.")
            setattr(self, name, value)

        self.tap_abs_th = float(self.tap_abs_th)
        if not np.isfinite(self.tap_abs_th) or self.tap_abs_th < 0.0:
            raise ValueError("COMPMFRuntimeConfig.tap_abs_th must be finite and non-negative.")

        self.keep_mass = float(self.keep_mass)
        if not np.isfinite(self.keep_mass) or self.keep_mass <= 0.0 or self.keep_mass > 1.0:
            raise ValueError("COMPMFRuntimeConfig.keep_mass must be finite and in (0, 1].")

@dataclass(repr=False)
class COMDeviceTermConfig(COMDataclassText):
    C_d_seq: Sequence[float] | np.ndarray = ()     # unit: F, device termination shunt-capacitance vector
    L_s_seq: Sequence[float] | np.ndarray = ()     # unit: H, device termination series-inductance vector
    C_b: float = 0.0                               # unit: F, bump/interface capacitance

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Device termination", (
                self._field("C_d_seq", "device shunt capacitances", stored_unit="F", display_unit="fF", scale=1e15),
                self._field("L_s_seq", "device series inductances", stored_unit="H", display_unit="pH", scale=1e12),
                self._field("C_b", "bump capacitance", stored_unit="F", display_unit="fF", scale=1e15),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("C_d_seq", "device shunt capacitances", stored_unit="F", display_unit="fF", scale=1e15, summary="shape"),
            self._field("C_b", "bump capacitance", stored_unit="F", display_unit="fF", scale=1e15),
        )

    def __post_init__(self) -> None:
        self.C_d_seq = np.asarray(self.C_d_seq, dtype=float)
        self.L_s_seq = np.asarray(self.L_s_seq, dtype=float)

        if self.C_d_seq.ndim != 1 or self.L_s_seq.ndim != 1:
            raise ValueError("C_d_seq and L_s_seq must be 1-D arrays.")
        if len(self.C_d_seq) != len(self.L_s_seq):
            raise COMLengthMismatchError(
                "C_d_seq and L_s_seq must have the same length. "
                f"Got len(C_d_seq)={len(self.C_d_seq)}, len(L_s_seq)={len(self.L_s_seq)}."
            )
        if len(self.C_d_seq) == 0:
            raise ValueError("C_d_seq and L_s_seq must contain at least one stage.")
        if not np.all(np.isfinite(self.C_d_seq)) or not np.all(np.isfinite(self.L_s_seq)):
            raise ValueError("C_d_seq and L_s_seq must contain finite values.")
        if np.any(self.C_d_seq < 0.0) or np.any(self.L_s_seq < 0.0):
            raise ValueError("C_d_seq and L_s_seq values must be non-negative.")

        self.C_b = float(self.C_b)
        if not np.isfinite(self.C_b) or self.C_b < 0.0:
            raise ValueError("C_b must be finite and non-negative.")

@dataclass(repr=False)
class COMDevicePackageConfig(COMDataclassText):
    z_p_seq: Sequence[float] | np.ndarray = ()      # unit: mm, package TL stage lengths
    Z_c_seq: Sequence[float] | np.ndarray = ()      # unit: ohm, package TL stage differential impedances
    gamma_0: Sequence[float] | float = 0.0          # unit: 1/mm, package propagation coefficient term
    a1: Sequence[float] | float = float(1.734e-3)   # unit: 93A package TL model coefficient
    a2: Sequence[float] | float = float(1.455e-4)   # unit: 93A package TL model coefficient
    tau: Sequence[float] | float = float(6.141e-3)  # unit: ns/mm, package TL delay coefficient
    C_p: float = 0.0                                # unit: F, package-to-board capacitance

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Device package", (
                self._field("z_p_seq", "transmission-line lengths", stored_unit="mm"),
                self._field("Z_c_seq", "differential impedances", stored_unit="ohm"),
                self._field("gamma_0", "propagation gamma coefficients", stored_unit="1/mm"),
                self._field("a1", "loss coefficient a1", stored_unit="model coefficient"),
                self._field("a2", "loss coefficient a2", stored_unit="model coefficient"),
                self._field("tau", "delay coefficient", stored_unit="ns/mm"),
                self._field("C_p", "package-to-board capacitance", stored_unit="F", display_unit="fF", scale=1e15),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("z_p_seq", "transmission-line lengths", stored_unit="mm", summary="shape"),
            self._field("Z_c_seq", "differential impedances", stored_unit="ohm", summary="shape"),
        )

    def __post_init__(self) -> None:
        self.z_p_seq = np.asarray(self.z_p_seq, dtype=float)
        self.Z_c_seq = np.asarray(self.Z_c_seq, dtype=float)

        if self.z_p_seq.ndim != 1 or self.Z_c_seq.ndim != 1:
            raise ValueError("z_p_seq and Z_c_seq must be 1-D arrays.")
        if len(self.z_p_seq) != len(self.Z_c_seq):
            raise COMLengthMismatchError(
                "z_p_seq and Z_c_seq must have the same length. "
                f"Got len(z_p_seq)={len(self.z_p_seq)}, len(Z_c_seq)={len(self.Z_c_seq)}."
            )
        if len(self.z_p_seq) == 0:
            raise ValueError("z_p_seq and Z_c_seq must contain at least one stage.")
        if not np.all(np.isfinite(self.z_p_seq)) or not np.all(np.isfinite(self.Z_c_seq)):
            raise ValueError("z_p_seq and Z_c_seq must contain finite values.")
        if np.any(self.z_p_seq < 0.0) or np.any(self.Z_c_seq <= 0.0):
            raise ValueError("z_p_seq must be non-negative and Z_c_seq must be positive.")

        num_stages = len(self.z_p_seq)

        def _stage_values(value: Sequence[float] | float, name: str) -> np.ndarray:
            values = np.asarray(value, dtype=float)
            if values.ndim == 0:
                values = np.full(num_stages, float(values), dtype=float)
            elif values.ndim != 1:
                raise ValueError(f"{name} must be a scalar or a 1-D array.")
            elif len(values) != num_stages:
                raise COMLengthMismatchError(
                    f"{name} must have {num_stages} values to match z_p_seq; got {len(values)}."
                )
            if not np.all(np.isfinite(values)):
                raise ValueError(f"{name} must contain finite values.")
            return values

        self.gamma_0 = _stage_values(self.gamma_0, "gamma_0")
        self.a1 = _stage_values(self.a1, "a1")
        self.a2 = _stage_values(self.a2, "a2")
        self.tau = _stage_values(self.tau, "tau")

@dataclass(repr=False)
class COMPartialHostConfig(COMDataclassText):
    enable: bool = False                         # unit: boolean, include partial host channel
    C_0: float = 0.0                             # unit: F, package-to-board interface capacitance
    C_1: float = 0.0                             # unit: F, model-to-measurement interface capacitance
    z_h: float = 0.0                             # unit: mm, host transmission-line length
    Z_h: float = 78.2                            # unit: ohm, host differential characteristic impedance
    gamma_0: float = 0.0                         # unit: 1/mm, host propagation coefficient term
    a1: float = float(1.734e-3)                  # unit: host transmission-line loss coefficient
    a2: float = float(1.455e-4)                  # unit: host transmission-line loss coefficient
    tau: float = float(6.141e-3)                 # unit: ns/mm, host transmission-line delay coefficient

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Partial host", (
                self._field("enable", "enabled", stored_unit="status"),
                self._field("C_0", "package-side capacitance", stored_unit="F", display_unit="fF", scale=1e15),
                self._field("C_1", "measurement-side capacitance", stored_unit="F", display_unit="fF", scale=1e15),
                self._field("z_h", "host length", stored_unit="mm"),
                self._field("Z_h", "differential impedance", stored_unit="ohm"),
                self._field("gamma_0", "propagation gamma coefficient", stored_unit="1/mm"),
                self._field("a1", "loss coefficient a1", stored_unit="model coefficient"),
                self._field("a2", "loss coefficient a2", stored_unit="model coefficient"),
                self._field("tau", "delay coefficient", stored_unit="ns/mm"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("enable", "enabled", stored_unit="status"),
            self._field("z_h", "host length", stored_unit="mm"),
        )

    def __post_init__(self) -> None:
        self.enable = bool(self.enable)

        for name in ("C_0", "C_1", "z_h", "Z_h", "gamma_0", "a1", "a2", "tau"):
            value = float(getattr(self, name))
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite.")
            setattr(self, name, value)

        if self.C_0 < 0.0 or self.C_1 < 0.0:
            raise ValueError("C_0 and C_1 must be non-negative.")
        if self.z_h < 0.0:
            raise ValueError("z_h must be non-negative.")
        if self.Z_h <= 0.0:
            raise ValueError("Z_h must be positive.")

@dataclass(repr=False)
class COMPkgConfig(COMDataclassText):
    """
    178A package configuration using internal formula units.

    Unit contract:
    - L_s_seq values are stored in H
    - C_d_seq, C_b, and C_p values are stored in F
    - z_p_seq values are stored in mm
    - R0 and Z_c_seq values are stored in ohm
    - gamma0/a1/a2/tau use the same package propagation model units as the
      underlying 93A transmission-line primitive
    """
    device_term: COMDeviceTermConfig
    device_pkg: COMDevicePackageConfig
    partial_host: COMPartialHostConfig
    R0: float = 50.0                               # unit: ohm, single-ended reference resistance

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Reference", (
                self._field("R0", "single-ended reference resistance", stored_unit="ohm"),
            )),
            TextSection("Package blocks", (
                self._field("device_term", "device termination", stored_unit="configuration"),
                self._field("device_pkg", "device package", stored_unit="configuration"),
                self._field("partial_host", "partial host", stored_unit="configuration"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (self._field("R0", "single-ended reference resistance", stored_unit="ohm"),)

    def __post_init__(self) -> None:
        if not isinstance(self.device_term, COMDeviceTermConfig):
            raise TypeError("device_term must be a COMDeviceTermConfig.")
        if not isinstance(self.device_pkg, COMDevicePackageConfig):
            raise TypeError("device_pkg must be a COMDevicePackageConfig.")
        if not isinstance(self.partial_host, COMPartialHostConfig):
            raise TypeError("partial_host must be a COMPartialHostConfig.")
        self.R0 = float(self.R0)
        if not np.isfinite(self.R0) or self.R0 <= 0.0:
            raise ValueError("R0 must be finite and positive.")

@dataclass(repr=False)
class COMFilterConfig(COMDataclassText):
    """
    178A filter configuration using internal formula units.

    TX FFE, transition-time filter, and receiver noise-filter fields intentionally
    keep the same names as the 93A config when the same helper contract is used.
    CTF fields use the 178A spec-facing two-zero / three-pole naming.
    """
    c_m3: float = 0.0                # unit: dimensionless, TX FFE tap c(-3)
    c_m2: float = 0.0                # unit: dimensionless, TX FFE tap c(-2)
    c_m1: float = 0.0                # unit: dimensionless, TX FFE tap c(-1)
    c_1: float = 0.0                 # unit: dimensionless, TX FFE tap c(1)
    c_0_min: float = 0.0             # unit: dimensionless, minimum allowed TX FFE main tap c(0)
    num_pre: int = 3                 # unit: taps, main cursor index in txfir
    Tr: Optional[float] = None       # unit: s, 20%-80% transition time
    fr: Optional[float] = None       # unit: Hz, receiver noise-filter bandwidth
    g_1: Optional[float] = None      # unit: dB, 178A CTF gain term 1
    g_2: Optional[float] = None      # unit: dB, 178A CTF gain term 2
    f_z1: Optional[float] = None     # unit: Hz, 178A CTF zero 1
    f_z2: Optional[float] = None     # unit: Hz, 178A CTF zero 2
    f_p1: Optional[float] = None     # unit: Hz, 178A CTF pole 1
    f_p2: Optional[float] = None     # unit: Hz, 178A CTF pole 2
    f_p3: Optional[float] = None     # unit: Hz, 178A CTF pole 3
    A_v: float = 1.0                 # unit: V, victim rectangular pulse amplitude
    A_fe: float = 1.0                # unit: V, FEXT rectangular pulse amplitude
    A_ne: float = 1.0                # unit: V, NEXT rectangular pulse amplitude

    # derived attributes
    c_0: float = field(init=False)   # unit: dimensionless, TX FFE main cursor tap
    txfir: np.ndarray = field(init=False) # unit: dimensionless tap vector [c(-3), c(-2), c(-1), c(0), c(1)]

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("TX FFE", (
                self._field("c_m3", "tap c(-3)", stored_unit="dimensionless"),
                self._field("c_m2", "tap c(-2)", stored_unit="dimensionless"),
                self._field("c_m1", "tap c(-1)", stored_unit="dimensionless"),
                self._field("c_1", "tap c(1)", stored_unit="dimensionless"),
                self._field("c_0", "derived main tap c(0)", stored_unit="dimensionless"),
                self._field("c_0_min", "minimum main tap", stored_unit="dimensionless"),
                self._field("num_pre", "main cursor location", stored_unit="tap index"),
                self._field("txfir", "TX FFE tap vector", stored_unit="dimensionless"),
            )),
            TextSection("Analog filters", (
                self._field("Tr", "20%-80% transition time", stored_unit="s", display_unit="ps", scale=1e12),
                self._field("fr", "receiver noise-filter bandwidth", stored_unit="Hz", display_unit="GHz", scale=1e-9),
                self._field("g_1", "CTLE gain g1", stored_unit="dB"),
                self._field("g_2", "CTLE gain g2", stored_unit="dB"),
                self._field("f_z1", "CTLE zero 1", stored_unit="Hz", display_unit="GHz", scale=1e-9),
                self._field("f_z2", "CTLE zero 2", stored_unit="Hz", display_unit="GHz", scale=1e-9),
                self._field("f_p1", "CTLE pole 1", stored_unit="Hz", display_unit="GHz", scale=1e-9),
                self._field("f_p2", "CTLE pole 2", stored_unit="Hz", display_unit="GHz", scale=1e-9),
                self._field("f_p3", "CTLE pole 3", stored_unit="Hz", display_unit="GHz", scale=1e-9),
            )),
            TextSection("Path amplitudes", (
                self._field("A_v", "victim pulse amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("A_fe", "FEXT pulse amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("A_ne", "NEXT pulse amplitude", stored_unit="V", display_unit="mV", scale=1e3),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("txfir", "TX FFE tap vector", stored_unit="dimensionless", summary="shape"),
            self._field("g_1", "CTLE gain g1", stored_unit="dB"),
            self._field("g_2", "CTLE gain g2", stored_unit="dB"),
        )

    def __post_init__(self):
        self.c_0 = 1.0 - abs(self.c_m3) - abs(self.c_m2) - abs(self.c_m1) - abs(self.c_1)
        self.txfir = np.r_[self.c_m3, self.c_m2, self.c_m1, self.c_0, self.c_1]
        if not np.isfinite(self.c_0_min) or self.c_0_min < 0.0:
            raise ValueError("c_0_min must be finite and non-negative.")

    def validate_txfir_main_cursor(self) -> None:
        """Raise when this TX FFE candidate cannot use c(0) as its main cursor."""
        if self.c_0 < self.c_0_min:
            raise COMTxfirMainCursorError(
                "TX FFE candidate is infeasible: "
                f"c(0)={self.c_0:.6g} is below c_0_min={self.c_0_min:.6g}."
            )
        if int(np.argmax(np.abs(self.txfir))) != self.num_pre:
            raise COMTxfirMainCursorError(
                "TX FFE candidate is infeasible: c(0) is not the largest-magnitude tap; "
                f"txfir={self.txfir.tolist()}."
            )

@dataclass(repr=False)
class COMDTEConfig(COMDataclassText):
    """
    178A receiver discrete-time equalizer configuration.

    This is the 178A replacement for using COMDFEConfig directly. It owns the
    receiver sampled-domain equalizer search/limit parameters for the MMSE
    feed-forward and feedback filter solve.
    """
    d_w: int                         # unit: taps, number of pre-cursor FFE taps
    N_fix: int                       # unit: taps, number of fixed-position FFE taps
    w_pre1_max: float                # unit: dimensionless, first precursor FFE upper limit
    w_post1_max: float               # unit: dimensionless, first postcursor FFE upper limit
    w_fixed_rest_max: float          # unit: dimensionless, all other fixed FFE upper limits
    w_float_max: float               # unit: dimensionless, floating FFE upper coefficient limit
    w_float_min: float               # unit: dimensionless, floating FFE lower coefficient limit
    b_first_max: float               # unit: dimensionless, first DFE feedback upper limit
    b_first_min: float               # unit: dimensionless, first DFE feedback lower limit
    b_rest_max: float                # unit: dimensionless, later DFE feedback upper limits
    b_rest_min: float                # unit: dimensionless, later DFE feedback lower limits
    N_wg: int = 0                    # unit: groups, number of floating FFE tap groups
    N_wf: int = 0                    # unit: taps/group, taps per floating group
    N_max: Optional[int] = None      # unit: taps, FFE vector length / exclusive index bound
    N_b: int = 0                     # unit: taps, number of DFE feedback taps

    # derived coefficient-limit arrays used by COM_MMSE_DTE
    w_upper: np.ndarray = field(init=False)
    w_lower: np.ndarray = field(init=False)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Tap layout", (
                self._field("d_w", "precursor FFE taps", stored_unit="tap count"),
                self._field("N_fix", "fixed FFE taps", stored_unit="tap count"),
                self._field("N_wg", "floating FFE groups", stored_unit="group count"),
                self._field("N_wf", "taps per floating group", stored_unit="tap/group"),
                self._field("N_max", "FFE vector length", stored_unit="tap count"),
                self._field("N_b", "DFE taps", stored_unit="tap count"),
            )),
            TextSection("FFE limits", (
                self._field("w_pre1_max", "first precursor upper limit", stored_unit="dimensionless"),
                self._field("w_post1_max", "first postcursor upper limit", stored_unit="dimensionless"),
                self._field("w_fixed_rest_max", "remaining fixed-tap upper limit", stored_unit="dimensionless"),
                self._field("w_float_max", "floating-tap upper limit", stored_unit="dimensionless"),
                self._field("w_float_min", "floating-tap lower limit", stored_unit="dimensionless"),
                self._field("w_upper", "derived upper-limit vector", stored_unit="dimensionless"),
                self._field("w_lower", "derived lower-limit vector", stored_unit="dimensionless"),
            )),
            TextSection("DFE limits", (
                self._field("b_first_max", "first tap upper limit", stored_unit="dimensionless"),
                self._field("b_first_min", "first tap lower limit", stored_unit="dimensionless"),
                self._field("b_rest_max", "remaining tap upper limit", stored_unit="dimensionless"),
                self._field("b_rest_min", "remaining tap lower limit", stored_unit="dimensionless"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("d_w", "precursor FFE taps", stored_unit="tap count"),
            self._field("N_max", "FFE vector length", stored_unit="tap count"),
            self._field("N_b", "DFE taps", stored_unit="tap count"),
        )

    def __post_init__(self) -> None:
        for name in ("d_w", "N_fix", "N_wg", "N_wf", "N_b"):
            value = int(getattr(self, name))
            if value < 0:
                raise ValueError(f"COMDTEConfig.{name} must be non-negative.")
            setattr(self, name, value)
        if self.N_fix <= 0:
            raise ValueError("COMDTEConfig.N_fix must be positive.")
        if self.d_w < 1 or self.d_w + 1 >= self.N_fix:
            raise ValueError(
                "COMDTEConfig.d_w must leave one fixed precursor and one fixed postcursor tap."
            )
        if self.N_max is None:
            self.N_max = self.N_fix
        self.N_max = int(self.N_max)
        if self.N_max < self.N_fix:
            raise ValueError("COMDTEConfig.N_max must be greater than or equal to N_fix.")
        if (self.N_wg == 0) != (self.N_wf == 0):
            raise ValueError("COMDTEConfig.N_wg and N_wf must both be zero or both be positive.")
        for name in (
            "w_pre1_max",
            "w_post1_max",
            "w_fixed_rest_max",
            "w_float_max",
            "w_float_min",
            "b_first_max",
            "b_first_min",
            "b_rest_max",
            "b_rest_min",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value):
                raise ValueError(f"COMDTEConfig.{name} must be finite.")
            setattr(self, name, value)
        if min(self.w_pre1_max, self.w_post1_max, self.w_fixed_rest_max) < 0.0:
            raise ValueError("COMDTEConfig fixed FFE upper limits must be non-negative.")
        if self.w_float_min > self.w_float_max:
            raise ValueError("COMDTEConfig.w_float_min must be <= w_float_max.")
        if self.b_first_min > self.b_first_max or self.b_rest_min > self.b_rest_max:
            raise ValueError("COMDTEConfig DFE lower limits must not exceed their upper limits.")

        # Full FFE-index-domain limiters.  A selected placement is obtained by
        # direct indexing: cfg.w_lower[pruned_index], cfg.w_upper[pruned_index].
        self.w_upper = np.full(self.N_max, self.w_float_max, dtype=float)
        self.w_lower = np.full(self.N_max, self.w_float_min, dtype=float)
        self.w_upper[:self.N_fix] = self.w_fixed_rest_max
        self.w_lower[:self.N_fix] = -self.w_fixed_rest_max
        self.w_upper[self.d_w - 1] = self.w_pre1_max
        self.w_lower[self.d_w - 1] = -self.w_pre1_max
        self.w_upper[self.d_w + 1] = self.w_post1_max
        self.w_lower[self.d_w + 1] = -self.w_post1_max
        self.w_upper[self.d_w] = 1.0
        self.w_lower[self.d_w] = 1.0
        self.b_upper = np.full(self.N_b, self.b_rest_max, dtype=float)
        self.b_lower = np.full(self.N_b, self.b_rest_min, dtype=float)
        if self.N_b:
            self.b_upper[0] = self.b_first_max
            self.b_lower[0] = self.b_first_min

@dataclass(repr=False)
class COMRunConfig(COMDataclassText):
    """Algorithm policy and stage target for one 178A execution profile."""
    target: Literal["mse", "dfe", "mlsd", "full"] = "dfe"
    pre_dte_pmf_method: Literal["gaussian_approx", "pmf_exact"] = "gaussian_approx"
    pmf_grid_quality: Literal["coarse", "fine"] = "fine"
    pmf_keep_mass: float = float(1 - 1e-5)
    pmf_dy_override: Optional[float] = None  # V; bypass derived PMF grid step when set
    floating_mode: Literal["heuristic", "simplified", "spec-defined"] = "heuristic"
    pos_sweep_method: Literal["each_phase", "coarse_fine"] = "each_phase"
    pos_coarse_stride: int = 4

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Execution target", (
                self._field("target", "terminal calculation target", stored_unit="policy"),
                self._field("pre_dte_pmf_method", "pre-DTE PMF method", stored_unit="policy"),
                self._field("floating_mode", "floating-tap mode", stored_unit="policy"),
                self._field("pos_sweep_method", "sampling-position sweep", stored_unit="policy"),
                self._field("pos_coarse_stride", "coarse sampling stride", stored_unit="sample count"),
            )),
            TextSection("PMF precision", (
                self._field("pmf_grid_quality", "PMF grid quality", stored_unit="policy"),
                self._field("pmf_keep_mass", "retained PMF mass", stored_unit="dimensionless probability"),
                self._field("pmf_dy_override", "PMF voltage-grid spacing override", stored_unit="V", display_unit="mV", scale=1e3),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("target", "terminal calculation target", stored_unit="policy"),
            self._field("pmf_grid_quality", "PMF grid quality", stored_unit="policy"),
        )

    def __post_init__(self) -> None:
        if self.target not in {"mse", "dfe", "mlsd", "full"}:
            raise ValueError("COMRunConfig.target must be 'mse', 'dfe', 'mlsd', or 'full'.")
        if self.pre_dte_pmf_method not in {"gaussian_approx", "pmf_exact"}:
            raise ValueError(
                "COMRunConfig.pre_dte_pmf_method must be "
                "'gaussian_approx' or 'pmf_exact'."
            )
        if self.pmf_grid_quality not in {"coarse", "fine"}:
            raise ValueError("COMRunConfig.pmf_grid_quality must be 'coarse' or 'fine'.")
        self.pmf_keep_mass = float(self.pmf_keep_mass)
        if not np.isfinite(self.pmf_keep_mass) or not 0.0 < self.pmf_keep_mass <= 1.0:
            raise ValueError("COMRunConfig.pmf_keep_mass must be finite and in (0, 1].")
        if self.pmf_dy_override is not None:
            self.pmf_dy_override = float(self.pmf_dy_override)
            if not np.isfinite(self.pmf_dy_override) or self.pmf_dy_override <= 0.0:
                raise ValueError("COMRunConfig.pmf_dy_override must be finite and positive.")
        if self.floating_mode not in {"heuristic", "simplified", "spec-defined"}:
            raise ValueError(
                "COMRunConfig.floating_mode must be 'heuristic', 'simplified', or 'spec-defined'."
            )
        if self.pos_sweep_method not in {"each_phase", "coarse_fine"}:
            raise ValueError(
                "COMRunConfig.pos_sweep_method must be 'each_phase' or 'coarse_fine'."
            )
        self.pos_coarse_stride = int(self.pos_coarse_stride)
        if self.pos_coarse_stride <= 0:
            raise ValueError("COMRunConfig.pos_coarse_stride must be a positive integer.")

@dataclass(repr=False)
class COMExecutionConfig(COMDataclassText):
    """Project-owned profiles for single run and split 178A search execution."""
    single_run: COMRunConfig = field(default_factory=COMRunConfig)
    search_sweep: COMRunConfig = field(
        default_factory=lambda: COMRunConfig(target="mse", pmf_grid_quality="coarse")
    )
    search_final: COMRunConfig = field(default_factory=COMRunConfig)
    search_group_size: int = 100
    search_top_k: int = 10

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Run profiles", (
                self._field("single_run", "single-run profile", stored_unit="configuration"),
                self._field("search_sweep", "search-sweep profile", stored_unit="configuration"),
                self._field("search_final", "search-final profile", stored_unit="configuration"),
            )),
            TextSection("Search orchestration", (
                self._field("search_group_size", "candidate group size", stored_unit="candidate count"),
                self._field("search_top_k", "finalized candidates", stored_unit="candidate count"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("search_group_size", "candidate group size", stored_unit="candidate count"),
            self._field("search_top_k", "finalized candidates", stored_unit="candidate count"),
        )

    def __post_init__(self) -> None:
        if self.search_sweep.target != "mse":
            raise ValueError("COMExecutionConfig.search_sweep.target must be 'mse'.")
        if self.search_final.target not in {"dfe", "full"}:
            raise ValueError(
                "COMExecutionConfig.search_final.target must be 'dfe' or 'full'."
            )
        for name in ("search_group_size", "search_top_k"):
            value = int(getattr(self, name))
            if value <= 0:
                raise ValueError(f"COMExecutionConfig.{name} must be positive.")
            setattr(self, name, value)

@dataclass(repr=False)
class COMImpairmentConfig(COMDataclassText):
    """178A physical impairment parameters, excluding numerical run policy."""
    R_LM: float                     # unit: dimensionless, level separation mismatch ratio
    SNR_TX: float                   # unit: dB, transmitter signal-to-noise ratio
    sigma_RJ: float                 # unit: UI, random jitter RMS
    A_DD: float                     # unit: UI, dual-Dirac jitter amplitude
    eta_0: float                    # unit: V^2/Hz, one-sided noise spectral density
    N_qb: Optional[int] = None      # unit: bits, None disables quantization noise
    P_qc: Optional[float] = None    # unit: probability, None disables quantization noise

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Transmitter and receiver noise", (
                self._field("R_LM", "level mismatch ratio", stored_unit="dimensionless"),
                self._field("SNR_TX", "transmitter SNR", stored_unit="dB"),
                self._field("eta_0", "receiver noise density", stored_unit="V^2/Hz"),
            )),
            TextSection("Jitter", (
                self._field("sigma_RJ", "random jitter sigma", stored_unit="UI"),
                self._field("A_DD", "deterministic jitter amplitude", stored_unit="UI"),
            )),
            TextSection("ADC", (
                self._field("N_qb", "ADC resolution", stored_unit="bit count"),
                self._field("P_qc", "clipping-tail probability", stored_unit="dimensionless probability"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("SNR_TX", "transmitter SNR", stored_unit="dB"),
            self._field("N_qb", "ADC resolution", stored_unit="bit count"),
        )

    def __post_init__(self) -> None:
        for name in ("R_LM", "SNR_TX", "sigma_RJ", "A_DD", "eta_0"):
            value = float(getattr(self, name))
            if not np.isfinite(value):
                raise ValueError(f"COMImpairmentConfig.{name} must be finite.")
            setattr(self, name, value)
        if self.R_LM <= 0.0:
            raise ValueError("COMImpairmentConfig.R_LM must be positive.")
        if self.sigma_RJ < 0.0 or self.A_DD < 0.0 or self.eta_0 < 0.0:
            raise ValueError("COMImpairmentConfig jitter and noise parameters must be non-negative.")
        if self.N_qb is not None:
            self.N_qb = int(self.N_qb)
            if self.N_qb <= 0:
                raise ValueError("COMImpairmentConfig.N_qb must be positive when provided.")
        if self.P_qc is not None:
            self.P_qc = float(self.P_qc)
            if not np.isfinite(self.P_qc) or self.P_qc <= 0.0 or self.P_qc >= 1.0:
                raise ValueError("COMImpairmentConfig.P_qc must be in (0, 1) when provided.")

@dataclass(repr=False)
class COMMLSDConfig(COMDataclassText):
    """Configuration required to enable the Annex 178A MLSD receiver."""
    enable: bool = False
    trunc_len: int = 0
    delta_com_an: Optional[float] = None
    minimum_com_limit: Optional[float] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("MLSD control", (
                self._field("enable", "enabled", stored_unit="status"),
                self._field("trunc_len", "sequence truncation length", stored_unit="symbol count"),
                self._field("delta_com_an", "added-noise calibration target", stored_unit="dB"),
                self._field("minimum_com_limit", "minimum reported COM", stored_unit="dB"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("enable", "enabled", stored_unit="status"),
            self._field("trunc_len", "sequence truncation length", stored_unit="symbol count"),
        )

    def __post_init__(self) -> None:
        self.enable = bool(self.enable)
        self.trunc_len = int(self.trunc_len)
        if self.trunc_len < 0 or (self.enable and self.trunc_len <= 0):
            raise ValueError(
                "COMMLSDConfig.trunc_len must be positive when MLSD is enabled."
            )
        for name in ("delta_com_an", "minimum_com_limit"):
            value = getattr(self, name)
            if value is None:
                continue
            value = float(value)
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(
                    f"COMMLSDConfig.{name} must be finite and non-negative when provided."
                )
            setattr(self, name, value)

    def resolved_delta_com_an(self) -> float:
        """Return the explicit MLSD penalty or its clause/annex fallback."""
        if self.delta_com_an is not None:
            return self.delta_com_an
        if self.minimum_com_limit is not None:
            return self.minimum_com_limit
        raise ValueError(
            "MLSD requires delta_com_an or minimum_com_limit; the added-noise "
            "target must not be guessed."
        )

@dataclass(frozen=True, repr=False)
class COMPolicyConfig(COMDataclassText):
    """One-level collection of 178A algorithm policy and its preset provenance."""

    out_of_measured: Literal["cosine_decay", "zero_padding"] = "cosine_decay"
    channel_renormalization_order: Literal["sdd_first", "s4p_first"] = "sdd_first"
    pre_dte_adc_clipping_convention: Literal[
        "annex_d3", "matlab_4_17_reference_only"
    ] = "annex_d3"
    final_adc_quantization_convention: Literal[
        "annex_d3", "matlab_4_17_reference_only"
    ] = "annex_d3"
    ctle_pulse_realization: Literal["continuous_tf", "bilinear_iir"] = "continuous_tf"
    rxffe_record_realization: Literal[
        "linear_convolution", "finite_record_circshift"
    ] = "linear_convolution"
    noise_grid_method: Literal["analysis_grid", "fixed_ui"] = "analysis_grid"
    noise_grid_num_ui: Optional[int] = None
    discrete_pmf_placement: Literal["linear", "nearest"] = "linear"
    interference_pmf_method: Literal["signal_fir", "pam_atoms"] = "signal_fir"
    xtalk_pmf_accumulation: Literal["pathwise_convolution"] = "pathwise_convolution"
    gaussian_pmf_method: Literal["bin_integral", "reference_sample"] = "bin_integral"
    uniform_pmf_method: Literal["bin_integral", "nearest_centers"] = "bin_integral"
    pmf_scaling_method: Literal["mass_deposit", "interpolate_ordinates"] = "mass_deposit"
    final_pmf_grid: Literal["fine", "relative_As"] = "fine"
    final_adc_pmf_projection: Literal["annex_d3", "reference_support"] = "annex_d3"
    gaussian_n_sigma_override: Optional[float] = None
    added_noise_pdf: Literal["gaussian_addition", "scaled_total_pdf"] = "gaussian_addition"
    mlsd_quantization_psd: Literal[
        "pre_dte_filtered", "main_tap_white"
    ] = "pre_dte_filtered"
    sequence_termination: Literal["fixed_length_sum", "matlab_relative_tail"] = "fixed_length_sum"
    reported_der: Literal["raw_sequence_sum", "baseline_pdf_re_evaluation"] = "raw_sequence_sum"
    applied_config_profile: Optional[str] = None
    config_profile_overrides: dict[str, object] = field(default_factory=dict)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Channel and pulse", (
                self._field("out_of_measured", "out-of-measured-band behavior", stored_unit="policy"),
                self._field("channel_renormalization_order", "channel renormalization order", stored_unit="policy"),
                self._field("ctle_pulse_realization", "CTLE pulse realization", stored_unit="policy"),
                self._field("rxffe_record_realization", "RX FFE record realization", stored_unit="policy"),
            )),
            TextSection("Noise and ADC", (
                self._field("pre_dte_adc_clipping_convention", "pre-DTE ADC clipping", stored_unit="policy"),
                self._field("final_adc_quantization_convention", "final ADC quantization", stored_unit="policy"),
                self._field("noise_grid_method", "noise grid method", stored_unit="policy"),
                self._field("noise_grid_num_ui", "noise grid length", stored_unit="UI count"),
                self._field("final_adc_pmf_projection", "final ADC PMF projection", stored_unit="policy"),
            )),
            TextSection("PMF methods", (
                self._field("discrete_pmf_placement", "discrete placement", stored_unit="policy"),
                self._field("interference_pmf_method", "interference PMF", stored_unit="policy"),
                self._field("xtalk_pmf_accumulation", "crosstalk accumulation", stored_unit="policy"),
                self._field("gaussian_pmf_method", "Gaussian PMF", stored_unit="policy"),
                self._field("uniform_pmf_method", "uniform PMF", stored_unit="policy"),
                self._field("pmf_scaling_method", "PMF scaling", stored_unit="policy"),
                self._field("final_pmf_grid", "final PMF grid", stored_unit="policy"),
                self._field("gaussian_n_sigma_override", "Gaussian support override", stored_unit="sigma count"),
            )),
            TextSection("MLSD methods", (
                self._field("added_noise_pdf", "added-noise PDF", stored_unit="policy"),
                self._field("mlsd_quantization_psd", "MLSD quantization PSD", stored_unit="policy"),
                self._field("sequence_termination", "sequence termination", stored_unit="policy"),
                self._field("reported_der", "reported DER", stored_unit="policy"),
            )),
            TextSection("Profile provenance", (
                self._field("applied_config_profile", "applied profile", stored_unit="profile name"),
                self._field("config_profile_overrides", "profile overrides", stored_unit="mapping"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("applied_config_profile", "applied profile", stored_unit="profile name"),
            self._field("channel_renormalization_order", "channel renormalization order", stored_unit="policy"),
            self._field("ctle_pulse_realization", "CTLE pulse realization", stored_unit="policy"),
        )

    def __post_init__(self) -> None:
        allowed = {
            "out_of_measured": {"cosine_decay", "zero_padding"},
            "channel_renormalization_order": {"sdd_first", "s4p_first"},
            "pre_dte_adc_clipping_convention": {"annex_d3", "matlab_4_17_reference_only"},
            "final_adc_quantization_convention": {"annex_d3", "matlab_4_17_reference_only"},
            "ctle_pulse_realization": {"continuous_tf", "bilinear_iir"},
            "rxffe_record_realization": {"linear_convolution", "finite_record_circshift"},
            "noise_grid_method": {"analysis_grid", "fixed_ui"},
            "discrete_pmf_placement": {"linear", "nearest"},
            "interference_pmf_method": {"signal_fir", "pam_atoms"},
            "xtalk_pmf_accumulation": {"pathwise_convolution"},
            "gaussian_pmf_method": {"bin_integral", "reference_sample"},
            "uniform_pmf_method": {"bin_integral", "nearest_centers"},
            "pmf_scaling_method": {"mass_deposit", "interpolate_ordinates"},
            "final_pmf_grid": {"fine", "relative_As"},
            "final_adc_pmf_projection": {"annex_d3", "reference_support"},
            "added_noise_pdf": {"gaussian_addition", "scaled_total_pdf"},
            "mlsd_quantization_psd": {"pre_dte_filtered", "main_tap_white"},
            "sequence_termination": {"fixed_length_sum", "matlab_relative_tail"},
            "reported_der": {"raw_sequence_sum", "baseline_pdf_re_evaluation"},
        }
        for name, choices in allowed.items():
            if getattr(self, name) not in choices:
                raise ValueError(f"COMPolicyConfig.{name} must be one of {sorted(choices)}.")
        if self.gaussian_n_sigma_override is not None:
            value = float(self.gaussian_n_sigma_override)
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(
                    "COMPolicyConfig.gaussian_n_sigma_override must be finite and positive."
                )
            object.__setattr__(self, "gaussian_n_sigma_override", value)
        if self.noise_grid_method == "analysis_grid":
            if self.noise_grid_num_ui is not None:
                raise ValueError("analysis_grid requires noise_grid_num_ui=None.")
        else:
            if (
                self.noise_grid_num_ui is None
                or int(self.noise_grid_num_ui) != self.noise_grid_num_ui
                or int(self.noise_grid_num_ui) < 2
            ):
                raise ValueError("fixed_ui requires an integer noise_grid_num_ui >= 2.")
            if int(self.noise_grid_num_ui) % 2 != 0:
                raise ValueError(
                    "fixed_ui requires even noise_grid_num_ui so the PSD includes Nyquist."
                )
            object.__setattr__(self, "noise_grid_num_ui", int(self.noise_grid_num_ui))
        if (
            self.final_adc_pmf_projection == "reference_support"
            and self.final_adc_quantization_convention != "matlab_4_17_reference_only"
        ):
            raise ValueError(
                "final_adc_pmf_projection='reference_support' requires "
                "final_adc_quantization_convention='matlab_4_17_reference_only'."
            )
        if self.applied_config_profile is not None:
            object.__setattr__(self, "applied_config_profile", str(self.applied_config_profile))
        object.__setattr__(self, "config_profile_overrides", dict(self.config_profile_overrides))

    def resolve_noise_grid(self, link_cfg: LinkConfig) -> LinkConfig:
        """Return the shared grid used by every MMSE noise PSD component."""
        if self.noise_grid_method == "analysis_grid":
            return link_cfg
        return LinkConfig.from_Nfft(
            fb=link_cfg.fb,
            per_ui=link_cfg.per_ui,
            Nfft=int(self.noise_grid_num_ui) * link_cfg.per_ui,
        )

    def fit_noise_response(self, response: np.ndarray) -> np.ndarray:
        """Apply the explicit finite record used before a noise DFT."""
        response = np.asarray(response, dtype=float)
        if response.ndim != 1:
            raise ValueError("noise-grid response must be one-dimensional.")
        if self.noise_grid_method == "analysis_grid":
            return response
        fitted = np.zeros(int(self.noise_grid_num_ui), dtype=float)
        count = min(len(response), len(fitted))
        fitted[:count] = response[:count]
        return fitted

@dataclass(repr=False)
class COMConfig(COMDataclassText):
    """Top-level 178A COM configuration grouped by function."""
    L: int                            # unit: levels, PAM order
    link: LinkConfig                  # unit contract: SI grid, Hz/s
    filter: COMFilterConfig       # unit contract: SI filter frequencies and 178A CTF terms
    channel: COMChannelConfig         # unit contract: Touchstone paths and S4P port order
    txpkg_victim: COMPkgConfig    # unit contract: 178A victim TX package
    txpkg_fext: COMPkgConfig      # unit contract: 178A FEXT aggressor TX package
    txpkg_next: COMPkgConfig      # unit contract: 178A NEXT aggressor TX package
    rxpkg: COMPkgConfig           # unit contract: 178A shared RX package
    dte: COMDTEConfig                 # unit contract: 178A receiver discrete-time equalizer search/limits
    imp: COMImpairmentConfig          # unit contract: V/UI/noise PSD units
    DER_0: float                      # unit: dimensionless, target detector error ratio
    pmf: COMPMFConfig = field(default_factory=COMPMFConfig) # unit contract: PMF amplitude grid and numerical controls
    execution: COMExecutionConfig = field(default_factory=COMExecutionConfig)
    mlsd: COMMLSDConfig = field(default_factory=COMMLSDConfig)
    policy: COMPolicyConfig = field(default_factory=COMPolicyConfig)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Signal and grid", (
                self._field("L", "PAM order", stored_unit="level count"),
                self._field("DER_0", "target detector error ratio", stored_unit="dimensionless probability"),
                self._field("link", "analysis grid", stored_unit="configuration"),
            )),
            TextSection("Channel and packages", (
                self._field("channel", "measured channel", stored_unit="configuration"),
                self._field("txpkg_victim", "victim TX package", stored_unit="configuration"),
                self._field("txpkg_fext", "FEXT TX package", stored_unit="configuration"),
                self._field("txpkg_next", "NEXT TX package", stored_unit="configuration"),
                self._field("rxpkg", "RX package", stored_unit="configuration"),
            )),
            TextSection("Model stages", (
                self._field("filter", "filters", stored_unit="configuration"),
                self._field("dte", "discrete-time equalizer", stored_unit="configuration"),
                self._field("imp", "impairments", stored_unit="configuration"),
                self._field("pmf", "PMF", stored_unit="configuration"),
                self._field("mlsd", "MLSD", stored_unit="configuration"),
            )),
            TextSection("Execution", (
                self._field("execution", "execution profiles", stored_unit="configuration"),
                self._field("policy", "algorithm policy", stored_unit="configuration"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("L", "PAM order", stored_unit="level count"),
            self._field("DER_0", "target detector error ratio", stored_unit="dimensionless probability"),
            self._field("policy", "algorithm policy", stored_unit="configuration"),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.policy, COMPolicyConfig):
            raise TypeError("policy must be a COMPolicyConfig.")
        if (
            self.policy.noise_grid_method == "fixed_ui"
            and int(self.policy.noise_grid_num_ui) < int(self.dte.N_max)
        ):
            raise ValueError("policy.noise_grid_num_ui must cover COMDTEConfig.N_max lags.")

    def resolve_run_cfg(self, run_cfg: COMRunConfig) -> COMRunConfig:
        """Compatibility identity: adapters now construct effective run profiles."""
        return run_cfg

    def to_export_dict(self) -> dict[str, object]:
        """
        Return a JSON-friendly COMConfig178A snapshot.

        The snapshot records only configuration and derived configuration
        metadata. It does not include COMStatus run results.
        """
        return {
            "type": type(self).__name__,
            "config": self._json_value(self),
            "derived": {
                "policy": self._json_value(self.policy),
                "effective_execution": {
                    "single_run": self._json_value(self.resolve_run_cfg(self.execution.single_run)),
                    "search_sweep": self._json_value(self.resolve_run_cfg(self.execution.search_sweep)),
                    "search_final": self._json_value(self.resolve_run_cfg(self.execution.search_final)),
                },
                "link": self._json_value(self.link),
                "channel_measured_grid": self._json_value(self.channel.measured_grid_summary()),
                "channel_aligned_grid": self._json_value(self.channel.aligned_grid_summary()),
                "txfir": self._json_value(self.filter.txfir),
                "c_0": self._json_scalar(self.filter.c_0),
            },
        }

    def export(self, save_path: str) -> dict[str, str]:
        """Export this COMConfig178A as a human-readable summary."""
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        txt_path = out_dir / "config_summary.txt"
        txt_path.write_text(str(self), encoding="utf-8")

        return {
            "config_summary_txt": str(txt_path),
        }
