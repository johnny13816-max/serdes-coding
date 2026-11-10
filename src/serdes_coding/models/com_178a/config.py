"""Version-owned Annex 178A configuration contracts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, fields, replace
from pathlib import Path
from typing import Any, Literal, Optional, Sequence

import numpy as np

from ...utilities.link import LinkConfig
from ...utilities.sparam import SparamModel
from ...search.com_search_178A import COMSearchConfig
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


# Gaussian PMFs use a fixed support large enough that omitted two-sided mass is
# at floating-point scale.  This is an internal numerical invariant, not a
# project-config branch.
GAUSSIAN_SUPPORT_N_SIGMA = 8.0


@dataclass(repr=False)
class COMChannelConfig(_LeafConfigText):
    """Physical channel conditions and measured-record boundary."""
    _FIELD_UNITS = {
        "R0": "ohm",
        "R_d_tx": "ohm",
        "R_d_rx": "ohm",
        "gamma_src": "dimensionless",
        "gamma_load": "dimensionless",
        "sparam_frequency_limit_Hz": "Hz",
    }
    R0: float                                               # unit: ohm, single-ended reference resistance
    R_d_tx: float                                           # unit: ohm, TX die termination resistance
    R_d_rx: float                                           # unit: ohm, RX die termination resistance
    gamma_src: complex = field(init=False)                  # unit: dimensionless, derived from R_d_tx and R0
    gamma_load: complex = field(init=False)                 # unit: dimensionless, derived from R_d_rx and R0
    sparam_frequency_limit_Hz: Optional[float] = None       # unit: Hz; measured-record boundary

    def __post_init__(self) -> None:
        for name in ("R0", "R_d_tx", "R_d_rx"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive.")
            setattr(self, name, value)

        self.gamma_src = complex((self.R_d_tx - self.R0) / (self.R_d_tx + self.R0))
        self.gamma_load = complex((self.R_d_rx - self.R0) / (self.R_d_rx + self.R0))
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



@dataclass(repr=False)
class COMSourceConfig(COMDataclassText):
    """Block-source bindings; future source families may sit beside channel."""

    @dataclass(frozen=True, repr=False)
    class ChannelBinding(_LeafConfigText):
        """One Touchstone artifact and the metadata required to interpret it."""

        _FIELD_UNITS = {
            "path": "filesystem path",
            "representation": "input representation",
            "port_order": "zero-based port indices",
        }
        path: str
        representation: Literal["auto", "s2p", "s4p"] = "auto"
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3)

        def _text_sections(self) -> tuple[TextSection, ...]:
            return (
                TextSection("Channel artifact", (
                    self._field("path", "path", stored_unit="filesystem path"),
                    self._field(
                        "representation", "representation",
                        stored_unit="input representation",
                    ),
                    self._field(
                        "port_order", "port order",
                        stored_unit="zero-based port indices",
                    ),
                )),
            )

        def _repr_fields(self) -> tuple[TextField, ...]:
            return (
                self._field("path", "path", stored_unit="filesystem path"),
                self._field(
                    "representation", "representation",
                    stored_unit="input representation",
                ),
            )

        def __post_init__(self) -> None:
            path = str(self.path).strip()
            if not path:
                raise ValueError("COMSourceConfig.ChannelBinding.path must not be blank.")
            object.__setattr__(self, "path", path)
            if self.representation not in {"auto", "s2p", "s4p"}:
                raise ValueError(
                    "COMSourceConfig.ChannelBinding.representation must be "
                    "'auto', 's2p', or 's4p'."
                )
            port_order = tuple(int(value) for value in self.port_order)
            if len(port_order) != 4 or set(port_order) != {0, 1, 2, 3}:
                raise ValueError(
                    "COMSourceConfig.ChannelBinding.port_order must be a "
                    "permutation of (0, 1, 2, 3)."
                )
            object.__setattr__(self, "port_order", port_order)

        def load(self) -> SparamModel:
            """Load and validate one supported differential or single-ended artifact."""
            measured = SparamModel.from_touchstone(
                self.path,
                representation=self.representation,
            )
            if measured.representation not in {"s2p", "s4p"}:
                raise ValueError(
                    f"Unsupported channel representation for {self.path!r}: "
                    f"{measured.representation!r}."
                )
            return measured

    @dataclass(frozen=True, repr=False)
    class Channel(COMDataclassText):
        """Victim/NEXT/FEXT source bindings in COM path order."""

        victim: "COMSourceConfig.ChannelBinding"
        next: Sequence["COMSourceConfig.ChannelBinding"] = ()
        fext: Sequence["COMSourceConfig.ChannelBinding"] = ()

        def __post_init__(self) -> None:
            if not isinstance(self.victim, COMSourceConfig.ChannelBinding):
                raise TypeError("COMSourceConfig.Channel.victim must be a ChannelBinding.")
            next_bindings = tuple(self.next)
            fext_bindings = tuple(self.fext)
            for name, bindings in (("next", next_bindings), ("fext", fext_bindings)):
                if not all(
                    isinstance(binding, COMSourceConfig.ChannelBinding)
                    for binding in bindings
                ):
                    raise TypeError(
                        f"COMSourceConfig.Channel.{name} must contain only ChannelBinding values."
                    )
            object.__setattr__(self, "next", next_bindings)
            object.__setattr__(self, "fext", fext_bindings)

        def _text_sections(self) -> tuple[TextSection, ...]:
            return (
                TextSection("Channel artifacts", (
                    self._field("victim", "victim", stored_unit="source binding"),
                    self._field("next", "NEXT", stored_unit="source bindings"),
                    self._field("fext", "FEXT", stored_unit="source bindings"),
                )),
            )

        def _repr_fields(self) -> tuple[TextField, ...]:
            return (
                self._field("victim", "victim", stored_unit="source binding"),
                self._field("next", "NEXT", stored_unit="source bindings", summary="shape"),
                self._field("fext", "FEXT", stored_unit="source bindings", summary="shape"),
            )

        def ordered(self) -> tuple["COMSourceConfig.ChannelBinding", ...]:
            return (self.victim, *self.next, *self.fext)

        def measured_grid_summary(
            self,
            frequency_limit_Hz: Optional[float],
        ) -> list[dict[str, object]]:
            rows = (
                (("victim", self.victim),)
                + tuple(("next", binding) for binding in self.next)
                + tuple(("fext", binding) for binding in self.fext)
            )
            summary: list[dict[str, object]] = []
            for kind, binding in rows:
                try:
                    measured = binding.load()
                    raw_f_max = float(measured.freqs[-1])
                    effective = (
                        measured
                        if frequency_limit_Hz is None
                        else measured.limited_to_frequency(frequency_limit_Hz)
                    )
                    freqs = effective.freqs
                    summary.append({
                        "kind": kind,
                        "path": binding.path,
                        "representation": measured.representation,
                        "n": len(freqs),
                        "f_min": float(freqs[0]),
                        "f_max": float(freqs[-1]),
                        "raw_f_max": raw_f_max,
                        "requested_frequency_limit_Hz": frequency_limit_Hz,
                        "effective_f_max": float(freqs[-1]),
                        "delta_f": (
                            float(freqs[1] - freqs[0])
                            if len(freqs) > 1 else float("nan")
                        ),
                    })
                except Exception as exc:
                    summary.append({
                        "kind": kind,
                        "path": binding.path,
                        "status": f"unreadable: {exc}",
                    })
            return summary

        def aligned_grid_summary(
            self,
            channel_cfg: COMChannelConfig,
        ) -> dict[str, object]:
            try:
                channels = [binding.load() for binding in self.ordered()]
                if channel_cfg.sparam_frequency_limit_Hz is not None:
                    channels = [
                        channel.limited_to_frequency(
                            channel_cfg.sparam_frequency_limit_Hz
                        )
                        for channel in channels
                    ]
                freqs = channel_cfg.align_grid(channels)
                return {
                    "status": "ok",
                    "n": len(freqs),
                    "f_min": float(freqs[0]),
                    "f_max": float(freqs[-1]),
                    "delta_f": float(freqs[1] - freqs[0]),
                }
            except Exception as exc:
                return {"status": f"unavailable: {exc}"}

    channel: Channel

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Block sources", (
                self._field("channel", "channel", stored_unit="source configuration"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (self._field("channel", "channel", stored_unit="source configuration"),)

    def __post_init__(self) -> None:
        if not isinstance(self.channel, COMSourceConfig.Channel):
            raise TypeError("COMSourceConfig.channel must be a COMSourceConfig.Channel.")

@dataclass(repr=False)
class COMPMFGridControl(_LeafConfigText):
    """One voltage-domain PMF grid numerical-control family."""

    _FIELD_UNITS = {
        "rule": "policy",
        "dy_rel_As": "relative amplitude",
        "dy_abs_max": "V",
        "dy_override": "V",
    }
    rule: Literal["relative_As", "relative_As_with_cap"] = "relative_As_with_cap"
    dy_rel_As: float = 1e-3
    dy_abs_max: float = 0.01e-3
    dy_override: Optional[float] = None

    def __post_init__(self) -> None:
        if self.rule not in {"relative_As", "relative_As_with_cap"}:
            raise ValueError(
                "COMPMFGridControl.rule must be 'relative_As' or "
                "'relative_As_with_cap'."
            )
        for name in ("dy_rel_As", "dy_abs_max"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(
                    f"COMPMFGridControl.{name} must be finite and positive."
                )
            setattr(self, name, value)
        if self.dy_override is not None:
            self.dy_override = float(self.dy_override)
            if not np.isfinite(self.dy_override) or self.dy_override <= 0.0:
                raise ValueError(
                    "COMPMFGridControl.dy_override must be finite and positive."
                )

    def resolve_dy(self, As: float) -> float:
        """Resolve ``dy`` in this control's declared voltage domain."""
        As_abs = abs(float(As))
        if not np.isfinite(As_abs) or As_abs <= 0.0:
            raise ValueError("As must be finite and positive to resolve a PMF grid.")
        if self.dy_override is not None:
            return self.dy_override
        relative_dy = self.dy_rel_As * As_abs
        if self.rule == "relative_As":
            return relative_dy
        return min(relative_dy, self.dy_abs_max)


@dataclass(repr=False)
class COMNumericalControlConfig(COMDataclassText):
    """Resolved 178A numerical controls for one simulator instance."""

    adc_input_pmf_grid: COMPMFGridControl = field(default_factory=COMPMFGridControl)
    final_pmf_grid: COMPMFGridControl = field(default_factory=COMPMFGridControl)
    eq_ch_imp_len: Literal["full", "truncated"] = "full"
    num_trunc_ui: Optional[int] = None
    pmf_grid_quality: Literal["coarse", "fine"] = "fine"
    pmf_keep_mass: float = float(1 - 1e-5)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("PMF voltage grids", (
                self._field(
                    "adc_input_pmf_grid", "ADC-input PMF grid", stored_unit="configuration"
                ),
                self._field(
                    "final_pmf_grid", "final PMF grid", stored_unit="configuration"
                ),
            )),
            TextSection("Record and convergence", (
                self._field("eq_ch_imp_len", "impairment eq-channel record length", stored_unit="policy"),
                self._field("num_trunc_ui", "truncated record length", stored_unit="UI count"),
                self._field("pmf_grid_quality", "legacy PMF grid quality", stored_unit="policy"),
                self._field("pmf_keep_mass", "retained PMF mass", stored_unit="dimensionless probability"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field(
                "adc_input_pmf_grid", "ADC-input PMF grid", stored_unit="configuration"
            ),
            self._field(
                "final_pmf_grid", "final PMF grid", stored_unit="configuration"
            ),
            self._field("eq_ch_imp_len", "impairment record length", stored_unit="policy"),
        )

    def __post_init__(self) -> None:
        for name in ("adc_input_pmf_grid", "final_pmf_grid"):
            if not isinstance(getattr(self, name), COMPMFGridControl):
                raise TypeError(
                    f"COMNumericalControlConfig.{name} must be a COMPMFGridControl."
                )
        if self.eq_ch_imp_len not in {"full", "truncated"}:
            raise ValueError(
                "COMNumericalControlConfig.eq_ch_imp_len must be 'full' or 'truncated'."
            )
        if self.eq_ch_imp_len == "full":
            if self.num_trunc_ui is not None:
                raise ValueError("eq_ch_imp_len='full' requires num_trunc_ui=None.")
        else:
            if (
                self.num_trunc_ui is None
                or int(self.num_trunc_ui) != self.num_trunc_ui
                or int(self.num_trunc_ui) < 2
            ):
                raise ValueError(
                    "eq_ch_imp_len='truncated' requires an integer num_trunc_ui >= 2."
                )
            if int(self.num_trunc_ui) % 2 != 0:
                raise ValueError(
                    "eq_ch_imp_len='truncated' requires even num_trunc_ui so the PSD includes Nyquist."
                )
            self.num_trunc_ui = int(self.num_trunc_ui)
        if self.pmf_grid_quality not in {"coarse", "fine"}:
            raise ValueError(
                "COMNumericalControlConfig.pmf_grid_quality must be 'coarse' or 'fine'."
            )
        self.pmf_keep_mass = float(self.pmf_keep_mass)
        if not np.isfinite(self.pmf_keep_mass) or not 0.0 < self.pmf_keep_mass <= 1.0:
            raise ValueError(
                "COMNumericalControlConfig.pmf_keep_mass must be finite and in (0, 1]."
            )


@dataclass(repr=False)
class COMPMFConfig(_LeafConfigText):
    """
    PMF-domain configuration for Annex 178A interference/noise distributions.

    This legacy-compatible config owns PMF support, tap threshold, and mass
    controls. New voltage-grid selection is owned by ``COMPMFGridControl``.
    """
    _FIELD_UNITS = {
        "dy_override": "V",
        "dy_rel_As": "relative amplitude",
        "dy_abs_max": "V",
        "tap_abs_th_override": "V",
        "tap_rel_As": "relative amplitude",
        "keep_mass": "probability",
    }
    dy_override: Optional[float] = None # unit: V, explicit PMF amplitude grid step; if None derive from As
    dy_rel_As: float = 1e-3           # unit: dimensionless, default dy limit = 0.1% of As (from spec)
    dy_abs_max: float = 0.01e-3       # unit: V, default dy absolute limit = 0.01 mV (from spec)
    tap_abs_th_override: Optional[float] = None # unit: V, explicit tap threshold; if None derive from As
    tap_rel_As: float = 1e-3          # unit: dimensionless, ignore pulse terms below 0.1% of As (from spec)
    keep_mass: float = float(1 - 1e-5) # unit: probability, optional PMF truncation target

    def __post_init__(self) -> None:
        if self.dy_override is not None:
            self.dy_override = float(self.dy_override)
            if not np.isfinite(self.dy_override) or self.dy_override <= 0.0:
                raise ValueError("COMPMFConfig.dy_override must be finite and positive.")

        if self.tap_abs_th_override is not None:
            self.tap_abs_th_override = float(self.tap_abs_th_override)
            if not np.isfinite(self.tap_abs_th_override) or self.tap_abs_th_override < 0.0:
                raise ValueError("COMPMFConfig.tap_abs_th_override must be finite and non-negative.")

        for name in ("dy_rel_As", "dy_abs_max", "tap_rel_As"):
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
            gaussian_n_sigma=GAUSSIAN_SUPPORT_N_SIGMA,
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
    """Stage target and numerical controls for one 178A execution profile."""
    target: Literal["mse", "dfe", "mlsd", "all_enabled"] = "dfe"
    pmf_grid_quality: Literal["coarse", "fine"] = "fine"
    pmf_keep_mass: float = float(1 - 1e-5)
    pmf_dy_override: Optional[float] = None  # V; bypass derived PMF grid step when set
    adc_input_pmf_grid: Optional[COMPMFGridControl] = None
    final_pmf_grid: Optional[COMPMFGridControl] = None
    floating_mode: Literal["heuristic", "simplified", "spec-defined"] = "heuristic"
    pos_sweep_method: Literal["each_phase", "coarse_fine"] = "each_phase"
    pos_coarse_stride: int = 4

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Execution target", (
                self._field("target", "terminal calculation target", stored_unit="policy"),
                self._field("floating_mode", "floating-tap mode", stored_unit="policy"),
                self._field("pos_sweep_method", "sampling-position sweep", stored_unit="policy"),
                self._field("pos_coarse_stride", "coarse sampling stride", stored_unit="sample count"),
            )),
            TextSection("PMF precision", (
                self._field("pmf_grid_quality", "PMF grid quality", stored_unit="policy"),
                self._field("pmf_keep_mass", "retained PMF mass", stored_unit="dimensionless probability"),
                self._field("pmf_dy_override", "PMF voltage-grid spacing override", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("adc_input_pmf_grid", "effective ADC-input PMF grid", stored_unit="configuration"),
                self._field("final_pmf_grid", "effective final PMF grid", stored_unit="configuration"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("target", "terminal calculation target", stored_unit="policy"),
            self._field("pmf_grid_quality", "PMF grid quality", stored_unit="policy"),
        )

    def __post_init__(self) -> None:
        if self.target not in {"mse", "dfe", "mlsd", "all_enabled"}:
            raise ValueError(
                "COMRunConfig.target must be 'mse', 'dfe', 'mlsd', or 'all_enabled'."
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
        for name in ("adc_input_pmf_grid", "final_pmf_grid"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, COMPMFGridControl):
                raise TypeError(f"COMRunConfig.{name} must be a COMPMFGridControl or None.")
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
class COMRunProfiles(COMDataclassText):
    """Adapter-only workbook profiles; never stored in runtime COMConfig."""
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
            raise ValueError("COMRunProfiles.search_sweep.target must be 'mse'.")
        if self.search_final.target not in {"dfe", "all_enabled"}:
            raise ValueError(
                "COMRunProfiles.search_final.target must be 'dfe' or 'all_enabled'."
            )
        for name in ("search_group_size", "search_top_k"):
            value = int(getattr(self, name))
            if value <= 0:
                raise ValueError(f"COMRunProfiles.{name} must be positive.")
            setattr(self, name, value)


@dataclass(repr=False)
class COMExecutionConfig(COMDataclassText):
    """Resolved run extent for one simulator instance."""

    target: Literal["mse", "dfe", "mlsd", "all_enabled"] = "dfe"

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Execution", (
                self._field("target", "terminal calculation target", stored_unit="policy"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (self._field("target", "terminal calculation target", stored_unit="policy"),)

    def __post_init__(self) -> None:
        if self.target not in {"mse", "dfe", "mlsd", "all_enabled"}:
            raise ValueError(
                "COMExecutionConfig.target must be 'mse', 'dfe', 'mlsd', or 'all_enabled'."
            )

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
class COMAlgorithmPolicyConfig(COMDataclassText):
    """One-level collection of resolved 178A algorithm selectors."""

    missing_dc_policy: Literal[
        "error", "hold", "skrf", "mag_phase_trend_to_dc"
    ] = "error"
    out_of_measured: Literal["cosine_decay", "zero_padding"] = "cosine_decay"
    pre_dte_adc_clipping_convention: Literal[
        "full_jitter_half_tail", "rj_only_full_tail_reference"
    ] = "full_jitter_half_tail"
    final_com_vqc_convention: Literal[
        "selected_phase_adc_input", "sicopr_final_reconstruction"
    ] = "selected_phase_adc_input"
    ctle_pulse_realization: Literal["continuous_tf", "bilinear_iir"] = "continuous_tf"
    rxffe_record_realization: Literal[
        "linear_fixed_grid", "linear_expanded_grid", "finite_record_circshift"
    ] = "linear_fixed_grid"
    floating_mode: Literal["heuristic", "simplified", "spec-defined"] = "heuristic"
    pmf_projection_method: Literal["linear", "nearest"] = "linear"
    xtalk_pmf_accumulation: Literal["pathwise_convolution"] = "pathwise_convolution"
    pdf_to_pmf_method: Literal["bin_integral", "pmf_sample"] = "bin_integral"
    pmf_scaling_method: Literal["mass_deposit", "interpolate_ordinates"] = "mass_deposit"
    final_adc_pmf_projection: Literal["annex_d3", "reference_support"] = "annex_d3"
    added_noise_pdf: Literal["gaussian_addition", "scaled_total_pdf"] = "gaussian_addition"
    mlsd_quantization_psd: Literal[
        "pre_dte_filtered", "main_tap_white"
    ] = "pre_dte_filtered"
    sequence_termination: Literal["fixed_length_sum", "matlab_relative_tail"] = "fixed_length_sum"
    reported_der: Literal["raw_sequence_sum", "baseline_pdf_re_evaluation"] = "raw_sequence_sum"
    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Channel and pulse", (
                self._field("missing_dc_policy", "missing-DC completion", stored_unit="policy"),
                self._field("out_of_measured", "out-of-measured-band behavior", stored_unit="policy"),
                self._field("ctle_pulse_realization", "CTLE pulse realization", stored_unit="policy"),
                self._field("rxffe_record_realization", "RX FFE record realization", stored_unit="policy"),
            )),
            TextSection("Noise and ADC", (
                self._field("pre_dte_adc_clipping_convention", "pre-DTE ADC clipping", stored_unit="policy"),
                self._field("final_com_vqc_convention", "final COM V_qc convention", stored_unit="policy"),
                self._field("final_adc_pmf_projection", "final ADC PMF projection", stored_unit="policy"),
            )),
            TextSection("Receiver solver", (
                self._field("floating_mode", "floating-tap mode", stored_unit="policy"),
            )),
            TextSection("PMF methods", (
                self._field("pmf_projection_method", "PMF projection method", stored_unit="policy"),
                self._field("xtalk_pmf_accumulation", "crosstalk accumulation", stored_unit="policy"),
                self._field("pdf_to_pmf_method", "PDF-to-PMF discretization", stored_unit="policy"),
                self._field("pmf_scaling_method", "PMF scaling", stored_unit="policy"),
            )),
            TextSection("MLSD methods", (
                self._field("added_noise_pdf", "added-noise PDF", stored_unit="policy"),
                self._field("mlsd_quantization_psd", "MLSD quantization PSD", stored_unit="policy"),
                self._field("sequence_termination", "sequence termination", stored_unit="policy"),
                self._field("reported_der", "reported DER", stored_unit="policy"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("ctle_pulse_realization", "CTLE pulse realization", stored_unit="policy"),
        )

    def __post_init__(self) -> None:
        allowed = {
            "missing_dc_policy": {
                "error", "hold", "skrf", "mag_phase_trend_to_dc"
            },
            "out_of_measured": {"cosine_decay", "zero_padding"},
            "pre_dte_adc_clipping_convention": {"full_jitter_half_tail", "rj_only_full_tail_reference"},
            "final_com_vqc_convention": {
                "selected_phase_adc_input", "sicopr_final_reconstruction"
            },
            "ctle_pulse_realization": {"continuous_tf", "bilinear_iir"},
            "rxffe_record_realization": {
                "linear_fixed_grid", "linear_expanded_grid", "finite_record_circshift"
            },
            "floating_mode": {"heuristic", "simplified", "spec-defined"},
            "pmf_projection_method": {"linear", "nearest"},
            "xtalk_pmf_accumulation": {"pathwise_convolution"},
            "pdf_to_pmf_method": {"bin_integral", "pmf_sample"},
            "pmf_scaling_method": {"mass_deposit", "interpolate_ordinates"},
            "final_adc_pmf_projection": {"annex_d3", "reference_support"},
            "added_noise_pdf": {"gaussian_addition", "scaled_total_pdf"},
            "mlsd_quantization_psd": {"pre_dte_filtered", "main_tap_white"},
            "sequence_termination": {"fixed_length_sum", "matlab_relative_tail"},
            "reported_der": {"raw_sequence_sum", "baseline_pdf_re_evaluation"},
        }
        for name, choices in allowed.items():
            if getattr(self, name) not in choices:
                raise ValueError(
                    f"COMAlgorithmPolicyConfig.{name} must be one of {sorted(choices)}."
                )
        if (
            self.final_adc_pmf_projection == "reference_support"
            and self.final_com_vqc_convention != "sicopr_final_reconstruction"
        ):
            raise ValueError(
                "final_adc_pmf_projection='reference_support' requires "
                "final_com_vqc_convention='sicopr_final_reconstruction'."
            )
@dataclass(repr=False)
class COMConfig(COMDataclassText):
    """Top-level 178A COM configuration grouped by function."""
    L: int                            # unit: levels, PAM order
    link: LinkConfig                  # unit contract: SI grid, Hz/s
    filter: COMFilterConfig       # unit contract: SI filter frequencies and 178A CTF terms
    channel: COMChannelConfig         # physical terminations and measured-record boundary
    txpkg_victim: COMPkgConfig    # unit contract: 178A victim TX package
    txpkg_fext: COMPkgConfig      # unit contract: 178A FEXT aggressor TX package
    txpkg_next: COMPkgConfig      # unit contract: 178A NEXT aggressor TX package
    rxpkg: COMPkgConfig           # unit contract: 178A shared RX package
    dte: COMDTEConfig                 # unit contract: 178A receiver discrete-time equalizer search/limits
    imp: COMImpairmentConfig          # unit contract: V/UI/noise PSD units
    DER_0: float                      # unit: dimensionless, target detector error ratio
    src: COMSourceConfig              # block-source artifact bindings and interpretation metadata
    pmf: COMPMFConfig = field(default_factory=COMPMFConfig) # unit contract: PMF amplitude grid and numerical controls
    mlsd: COMMLSDConfig = field(default_factory=COMMLSDConfig)
    alg: COMAlgorithmPolicyConfig = field(default_factory=COMAlgorithmPolicyConfig)
    num: COMNumericalControlConfig = field(default_factory=COMNumericalControlConfig)
    srch: COMSearchConfig = field(default_factory=COMSearchConfig)
    exe: COMExecutionConfig = field(default_factory=COMExecutionConfig)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Signal and grid", (
                self._field("L", "PAM order", stored_unit="level count"),
                self._field("DER_0", "target detector error ratio", stored_unit="dimensionless probability"),
                self._field("link", "analysis grid", stored_unit="configuration"),
            )),
            TextSection("Channel and packages", (
                self._field("channel", "physical channel", stored_unit="configuration"),
                self._field("src", "block sources", stored_unit="configuration"),
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
                self._field("num", "numerical controls", stored_unit="configuration"),
                self._field("srch", "search controls", stored_unit="configuration"),
                self._field("mlsd", "MLSD", stored_unit="configuration"),
            )),
            TextSection("Execution", (
                self._field("exe", "execution", stored_unit="configuration"),
                self._field("alg", "algorithm policy", stored_unit="configuration"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("L", "PAM order", stored_unit="level count"),
            self._field("DER_0", "target detector error ratio", stored_unit="dimensionless probability"),
            self._field("alg", "algorithm policy", stored_unit="configuration"),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.src, COMSourceConfig):
            raise TypeError("src must be a COMSourceConfig.")
        if not isinstance(self.alg, COMAlgorithmPolicyConfig):
            raise TypeError("alg must be a COMAlgorithmPolicyConfig.")
        if not isinstance(self.num, COMNumericalControlConfig):
            raise TypeError("num must be a COMNumericalControlConfig.")
        if not isinstance(self.exe, COMExecutionConfig):
            raise TypeError("exe must be a COMExecutionConfig.")
        if not isinstance(self.srch, COMSearchConfig):
            raise TypeError("srch must be a COMSearchConfig.")
        if (
            self.num.eq_ch_imp_len == "truncated"
            and int(self.num.num_trunc_ui) < int(self.dte.N_max)
        ):
            raise ValueError("num.num_trunc_ui must cover COMDTEConfig.N_max lags.")

    def _set_adapter_resolution(
        self,
        *,
        applied_profile: Optional[str],
        profile_overrides: dict[str, object],
    ) -> None:
        """Attach non-runtime workbook resolution metadata for export only."""
        self._adapter_resolution = {
            "applied_config_profile": (
                None if applied_profile is None else str(applied_profile)
            ),
            "config_profile_overrides": deepcopy(profile_overrides),
        }

    def _resolved_copy(self, **changes: object) -> "COMConfig":
        """Return a dataclass copy while preserving adapter-only export metadata."""
        copied = replace(self, **changes)
        if hasattr(self, "_adapter_resolution"):
            copied._adapter_resolution = deepcopy(self._adapter_resolution)
        return copied

    def to_export_dict(self) -> dict[str, object]:
        """
        Return a JSON-friendly COMConfig178A snapshot.

        The snapshot records only configuration and derived configuration
        metadata. It does not include COMStatus run results.
        """
        exported = {
            "type": type(self).__name__,
            "config": self._json_value(self),
            "derived": {
                "alg": self._json_value(self.alg),
                "num": self._json_value(self.num),
                "srch": self._json_value(self.srch),
                "exe": self._json_value(self.exe),
                "link": self._json_value(self.link),
                "channel_measured_grid": self._json_value(
                    self.src.channel.measured_grid_summary(
                        self.channel.sparam_frequency_limit_Hz
                    )
                ),
                "channel_aligned_grid": self._json_value(
                    self.src.channel.aligned_grid_summary(self.channel)
                ),
                "txfir": self._json_value(self.filter.txfir),
                "c_0": self._json_scalar(self.filter.c_0),
            },
        }
        if hasattr(self, "_adapter_resolution"):
            exported["adapter_resolution"] = self._json_value(
                self._adapter_resolution
            )
        return exported

    def export(self, save_path: str) -> dict[str, str]:
        """Export this COMConfig178A as a human-readable summary."""
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        txt_path = out_dir / "config_summary.txt"
        txt_path.write_text(str(self), encoding="utf-8")

        return {
            "config_summary_txt": str(txt_path),
        }
