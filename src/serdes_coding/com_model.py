from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
import sys
from typing import Literal, Optional, Sequence
import numpy as np

try:
    from .link_segment import LinkConfig, LinkSegment, OneSidePSD, SparamModel
    from .pmf_handler import Pmf1D
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serdes_coding.link_segment import LinkConfig, LinkSegment, OneSidePSD, SparamModel
    from serdes_coding.pmf_handler import Pmf1D


class _PrettyDataclass:
    """Readable print/repr for COM config and status dataclasses."""

    _FREQUENCY_FIELD_NAMES = {
        "fb",
        "target_df",
        "df",
        "f_nyq",
        "fr",
        "f_z",
        "f_LF",
        "f_p1",
        "f_p2",
        "f_min",
        "f_max",
        "delta_f",
    }

    def __repr__(self) -> str:
        return self._pretty()

    def __str__(self) -> str:
        return self._pretty()

    def _pretty(self, indent: int = 0) -> str:
        pad = " " * indent
        inner_pad = " " * (indent + 2)
        lines = [f"{pad}{type(self).__name__}("]
        for item in fields(self):
            value = getattr(self, item.name)
            lines.append(f"{inner_pad}{item.name}={self._format_value(value, indent + 2, item.name)},")
        lines.append(f"{pad})")
        return "\n".join(lines)

    @classmethod
    def _format_value(cls, value: object, indent: int, name: str = "") -> str:
        if isinstance(value, _PrettyDataclass):
            return value._pretty(indent).lstrip()

        if is_dataclass(value) and isinstance(value, LinkConfig):
            return (
                "LinkConfig("
                f"fb={cls._format_frequency(value.fb)}, "
                f"per_ui={value.per_ui}, "
                f"target_df={cls._format_frequency(value.target_df)}, "
                f"Nfft={value.Nfft}, "
                f"df={cls._format_frequency(value.df)}, "
                f"f_nyq={cls._format_frequency(value.f_nyq)}"
                ")"
            )

        if isinstance(value, SparamModel):
            df = value.freqs[1] - value.freqs[0] if len(value.freqs) > 1 else float("nan")
            return (
                f"{type(value).__name__}("
                f"n={len(value.freqs)}, "
                f"f_min={cls._format_frequency(value.freqs[0])}, "
                f"f_max={cls._format_frequency(value.freqs[-1])}, "
                f"df={cls._format_frequency(df)}, "
                f"sdd={value.sdd.shape})"
            )

        if isinstance(value, LinkSegment):
            raw_ir_shape = None if value._raw_ir is None else value._raw_ir.shape
            aligned_ir_shape = None if value._aligned_ir is None else value._aligned_ir.shape
            sr_shape = None if value._sr is None else value._sr.shape
            sbr_shape = None if value._sbr is None else value._sbr.shape
            return (
                f"{type(value).__name__}("
                f"tf={value.tf.shape}, raw_ir={raw_ir_shape}, "
                f"aligned_ir={aligned_ir_shape}, sr={sr_shape}, sbr={sbr_shape}"
                ")"
            )

        if isinstance(value, np.ndarray):
            if value.size == 0:
                return f"ndarray(shape={value.shape}, dtype={value.dtype})"
            if value.ndim == 1 and value.size <= 8:
                return repr(value)
            return (
                f"ndarray(shape={value.shape}, dtype={value.dtype}, "
                f"min={np.min(np.abs(value)):.3e}, max={np.max(np.abs(value)):.3e})"
            )

        if isinstance(value, list):
            if len(value) == 0:
                return "[]"
            item_pad = " " * (indent + 2)
            close_pad = " " * indent
            items = [
                f"{item_pad}{cls._format_value(item, indent + 2)},"
                for item in value
            ]
            return "[\n" + "\n".join(items) + f"\n{close_pad}]"

        if isinstance(value, tuple):
            return repr(value)

        if isinstance(value, (float, np.floating)) and name in cls._FREQUENCY_FIELD_NAMES:
            return cls._format_frequency(float(value))

        return repr(value)

    @staticmethod
    def _format_frequency(value: float) -> str:
        return f"{float(value):.6e}"

def excel_to_config(excel_path: str) -> COMConfig:
    """
    Build COMConfig from one Excel row by direct field assignment.

    Expected Excel format:
    - first sheet
    - one header row
    - first data row contains values

    Column names intentionally match the current COMConfig dataclass fields so
    this function stays simple and easy to edit. This helper is the unit
    boundary: Excel/spec-style values are converted here into the internal
    units documented by each config class.

    Required LinkConfig columns:
    - fb in GBd/GHz-equivalent, per_ui, target_df in GHz

    Required COMFilterConfig columns:
    - c_m3, c_m2, c_m1, c_1, num_pre
    - Tr in ns, fr in GHz, g_DC, g_DC2, f_z/f_LF/f_p1/f_p2 in GHz
    - A_v, A_fe, A_ne

    Required COMChannelConfig columns:
    - victim_s4p_path, next_s4p_paths, fext_s4p_paths
    - port_order, R0, gamma_src, gamma_load

    Required COMPkgConfig columns:
    - C_d/C_b/C_p in nF, L_s in nH, z_p in mm, C_p in nF, pkg_enable
    - R0, Z_c, z_p2, Z_c2
    """
    import ast
    import pandas as pd

    row = pd.read_excel(excel_path).iloc[0]

    next_s4p_paths = row["next_s4p_paths"]
    if pd.isna(next_s4p_paths):
        next_s4p_paths = ()
    elif isinstance(next_s4p_paths, str):
        next_s4p_paths = tuple(ast.literal_eval(next_s4p_paths))
    else:
        next_s4p_paths = tuple(next_s4p_paths)

    fext_s4p_paths = row["fext_s4p_paths"]
    if pd.isna(fext_s4p_paths):
        fext_s4p_paths = ()
    elif isinstance(fext_s4p_paths, str):
        fext_s4p_paths = tuple(ast.literal_eval(fext_s4p_paths))
    else:
        fext_s4p_paths = tuple(fext_s4p_paths)

    port_order = row["port_order"]
    if isinstance(port_order, str):
        port_order = tuple(ast.literal_eval(port_order))
    else:
        port_order = tuple(port_order)

    z_p2 = row["z_p2"]
    if pd.isna(z_p2):
        z_p2 = None

    return COMConfig(
        link=LinkConfig(
            fb=row["fb"] * 1e9,
            per_ui=row["per_ui"],
            target_df=row["target_df"] * 1e9,
        ),
        filter=COMFilterConfig(
            c_m3=row["c_m3"],
            c_m2=row["c_m2"],
            c_m1=row["c_m1"],
            c_1=row["c_1"],
            num_pre=row["num_pre"],
            Tr=row["Tr"] * 1e-9,
            fr=row["fr"] * 1e9,
            g_DC=row["g_DC"],
            g_DC2=row["g_DC2"],
            f_z=row["f_z"] * 1e9,
            f_LF=row["f_LF"] * 1e9,
            f_p1=row["f_p1"] * 1e9,
            f_p2=row["f_p2"] * 1e9,
            A_v=row["A_v"],
            A_fe=row["A_fe"],
            A_ne=row["A_ne"],
        ),
        channel=COMChannelConfig(
            victim_s4p_path=row["victim_s4p_path"],
            next_s4p_paths=next_s4p_paths,
            fext_s4p_paths=fext_s4p_paths,
            port_order=port_order,
            R0=row["R0"],
            gamma_src=complex(row["gamma_src"]),
            gamma_load=complex(row["gamma_load"]),
        ),
        pkg=COMPkgConfig(
            C_d=row["C_d"] * 1e-9,
            L_s=row["L_s"] * 1e-9,
            C_b=row["C_b"] * 1e-9,
            z_p=row["z_p"],
            C_p=row["C_p"] * 1e-9,
            enable=row["pkg_enable"],
            R0=row["R0"],
            Z_c=row["Z_c"],
            z_p2=z_p2,
            Z_c2=row["Z_c2"],
        ),
    )

def IEEECOM_cascade_sdd(sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
    """
    Cascade two Sdd arrays using IEEE COM equations.

    Reference:
    - IEEE 802.3 Annex 93A.1.2.1, Eq. 93A-4 through Eq. 93A-7.

    Parameters
    ----------
    sx:
        First Sdd two-port in physical order, shape (N, 2, 2).
    sy:
        Second Sdd two-port in physical order, shape (N, 2, 2).
    """
    sx = np.asarray(sx, dtype=complex)
    sy = np.asarray(sy, dtype=complex)

    if sx.shape != sy.shape or sx.ndim != 3 or sx.shape[1:] != (2, 2):
        raise ValueError("sx and sy must both have shape (N, 2, 2).")

    x11, x12 = sx[:, 0, 0], sx[:, 0, 1]
    x21, x22 = sx[:, 1, 0], sx[:, 1, 1]
    y11, y12 = sy[:, 0, 0], sy[:, 0, 1]
    y21, y22 = sy[:, 1, 0], sy[:, 1, 1]

    denom = 1 - x22 * y11
    if np.any(np.isclose(denom, 0.0)):
        raise ZeroDivisionError("S-parameter cascade denominator is close to zero.")

    z11 = x11 + (x12 * y11 * x21) / denom
    z12 = (x12 * y12) / denom
    z21 = (y21 * x21) / denom
    z22 = y22 + (y21 * x22 * y12) / denom

    return np.stack([
        np.stack([z11, z12], axis=-1),
        np.stack([z21, z22], axis=-1),
    ], axis=-2)

class IEEECOMsparam(SparamModel):
    """
    IEEE 802.3 Annex 93A COM-specific S-parameter model builder.

    Class boundary
    --------------
    IEEECOMsparam owns S-parameter networks generated from IEEE COM equations:
    - shunt capacitance model
    - series inductance model
    - package transmission-line model
    - COM-defined Sdd cascade equations

    Generic S-parameter ingestion, storage, and scikit-rf operations remain in
    SparamModel. This class only adds spec-defined COM construction behavior.
    """

    @classmethod
    def shunt_capacitance(
        cls,
        freqs: np.ndarray,
        capacitance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the COM shunt capacitance Sdd two-port on freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.2, Eq. 93A-8.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        capacitance:
            Shunt capacitance in F.
        R0:
            Single-ended reference resistance used by Eq. 93A-8. The internal
            differential-mode Sdd Network uses z0 = 2 * R0.
        """
        C = float(capacitance)
        R0 = float(R0)
        freqs = LinkConfig.validate_freqs(freqs)

        if C < 0.0:
            raise ValueError("capacitance must be non-negative.")

        y = 1j * 2 * np.pi * freqs * C
        denom = 2 + y * R0

        s11 = -(y * R0) / denom
        s21 = 2 / denom

        sdd = np.stack([
            np.stack([s11, s21], axis=-1),
            np.stack([s21, s11], axis=-1),
        ], axis=-2)
        return cls.from_sdd_array(freqs, sdd, z0=2 * R0)

    @classmethod
    def series_inductance(
        cls,
        freqs: np.ndarray,
        inductance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the COM series inductance Sdd two-port on freqs.

        Reference:
        - IEEE 802.3ck Annex 93A.1.2.2a, Eq. 93A-9a.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        inductance:
            Series inductance in H.
        R0:
            Single-ended reference resistance used by Eq. 93A-9a. The internal
            differential-mode Sdd Network uses z0 = 2 * R0.
        """
        L = float(inductance)
        R0 = float(R0)
        freqs = LinkConfig.validate_freqs(freqs)

        if L < 0.0:
            raise ValueError("inductance must be non-negative.")

        y = 1j * 2 * np.pi * freqs * L
        denom = 2 + y / R0
        s11 = (y / R0) / denom
        s21 = 2 / denom
        sdd = np.stack([
            np.stack([s11, s21], axis=-1),
            np.stack([s21, s11], axis=-1),
        ], axis=-2)

        return cls.from_sdd_array(freqs, sdd, z0=2 * R0)

    @classmethod
    def pkg_trans_line(
        cls,
        freqs: np.ndarray,
        R0: float,
        zp: float,
        *,
        gamma0: float = 0.0,
        a1: float = float(1.734e-3),
        a2: float = float(1.455e-4),
        tau: float = float(6.141e-3),
        Zc: float = 78.2,
    ) -> 'IEEECOMsparam':
        """
        Build the COM package transmission-line Sdd two-port on freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.3, Eq. 93A-9 through Eq. 93A-14.
        - IEEE 802.3ck Annex 93A.1.2.3 clarifies that formula frequency f is
          in GHz.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance.
        zp:
            Package line length in millimeters.
        gamma0, a1, a2, tau:
            COM propagation-coefficient model parameters. The formula uses
            f in GHz internally after converting from freqs in Hz; gamma0,
            a1, a2, and tau keep the 93A units associated with Table 93A-3.
        Zc:
            Package differential characteristic impedance in ohm.
        """
        f_hz = LinkConfig.validate_freqs(freqs)
        if np.any(f_hz < 0):
            raise ValueError("The package transmission-line model does not include f < 0.")

        R0 = float(R0)
        zp = float(zp)
        Zc = float(Zc)

        if R0 <= 0.0:
            raise ValueError("R0 must be positive.")
        if zp < 0.0:
            raise ValueError("zp must be non-negative.")
        if Zc <= 0.0:
            raise ValueError("Zc must be positive.")

        f = f_hz / 1e9
        gamma = np.full_like(f, complex(gamma0), dtype=complex)
        gamma1 = a1 * (1 + 1j)
        positive = f > 0.0
        gamma2 = (
            a2 * (1 - (1j * (2 / np.pi) * np.log(f[positive])))
            + 1j * 2 * np.pi * tau
        )
        gamma[positive] = gamma0 + gamma1 * np.sqrt(f[positive]) + gamma2 * f[positive]
        rho = (Zc - 2 * R0) / (Zc + 2 * R0)

        y = np.exp(-(gamma * 2 * zp))
        y1 = np.exp(-(gamma * zp))
        denom = 1 - rho**2 * y
        s11 = (rho * (1 - y)) / denom
        s21 = (1 - rho**2) * y1 / denom

        sdd = np.stack([
            np.stack([s11, s21], axis=-1),
            np.stack([s21, s11], axis=-1),
        ], axis=-2)

        return cls.from_sdd_array(f_hz, sdd, z0=2 * R0)

    def cascade_com(self, other: SparamModel) -> 'IEEECOMsparam':
        """
        Cascade two Sdd two-port networks using IEEE COM equations.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.1, Eq. 93A-4 through Eq. 93A-7.

        Parameters
        ----------
        other:
            Sdd two-port physically following self.

        Frequency-grid rule
        -------------------
        If the two models do not already share an identical frequency grid,
        both are resampled onto the overlapping subset of self.freqs. This keeps
        cascade in the measured/common S-parameter band and avoids high-frequency
        S-parameter extrapolation.
        """
        if not isinstance(other, SparamModel):
            raise TypeError("other must be an SparamModel.")

        if self.sdd.shape[1:] != (2, 2) or other.sdd.shape[1:] != (2, 2):
            raise ValueError("Both models must contain 2-port Sdd networks.")

        f_start = max(self.freqs[0], other.freqs[0])
        f_stop = min(self.freqs[-1], other.freqs[-1])
        common_freqs = self.freqs[(self.freqs >= f_start) & (self.freqs <= f_stop)]
        if len(common_freqs) < 2:
            raise ValueError("No overlapping frequency grid for COM S-parameter cascade.")

        left = self.resampled(common_freqs)
        right = other.resampled(common_freqs)
        left.validate_compatible_sparam(right)

        cascaded_sdd = IEEECOM_cascade_sdd(left.sdd, right.sdd)
        return type(self).from_sdd_array(common_freqs, cascaded_sdd, z0=left.network.z0)

class IEEECOMFilter(LinkSegment):
    """
    IEEE 802.3 Annex 93A COM-specific scalar filter builders.

    Class boundary
    --------------
    IEEECOMFilter owns scalar transfer-function blocks defined by COM equations.
    The FFT/grid convention and scalar response conversion remain in
    LinkSegment.
    """

    @classmethod
    def rx_noise_filter(cls, cfg: LinkConfig, fr: float) -> 'IEEECOMFilter':
        """
        Build the receiver noise filter.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-20.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        fr:
            Receiver noise-filter bandwidth in Hz.
        """
        p1 = 3.414214
        p2 = 2.613126
        f = cfg.freqs
        H_r = 1.0 / (1.0 - p1 * (f / fr)**2 + (f / fr)**4 + 1j * p2 * (f / fr - (f / fr)**3))
        return cls.from_tf(f_meas=f, H_meas=H_r, cfg=cfg)

    @classmethod
    def tx_ffe(cls, cfg: LinkConfig, txfir: np.ndarray, num_pre: int) -> 'IEEECOMFilter':
        """
        Build the TX FFE transfer function.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-21.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        txfir:
            TX FFE tap coefficients, dimensionless.
        num_pre:
            Number of pre-cursor taps before the main cursor, in taps.
        """
        if np.argmax(np.abs(txfir)) != num_pre:
            raise ValueError("TX FFE main cursor index must equal num_pre.")

        f = cfg.freqs
        H_ffe = np.zeros_like(f, dtype=complex)
        for idx, c_i in enumerate(txfir):
            H_ffe += c_i * np.exp(-1j * 2 * np.pi * idx * f / cfg.fb)

        return cls.from_tf(f_meas=f, H_meas=H_ffe, cfg=cfg)

    @classmethod
    def rx_equalizer(
        cls,
        cfg: LinkConfig,
        g_DC: float,
        g_DC2: float,
        f_z: float,
        f_LF: float,
        f_p1: float,
        f_p2: float,
    ) -> 'IEEECOMFilter':
        """
        Build the receiver equalizer transfer function.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-22.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        g_DC:
            First DC gain term in dB.
        g_DC2:
            Second DC gain term in dB.
        f_z, f_LF, f_p1, f_p2:
            Equalizer pole/zero frequencies in Hz.
        """
        f = cfg.freqs
        denom = (1 + 1j * f / f_p1) * (1 + 1j * f / f_p2) * (1 + 1j * f / f_LF)
        H_ctf = (10**(g_DC / 20) + 1j * f / f_z) * (10**(g_DC2 / 20) + 1j * f / f_LF) / denom
        return cls.from_tf(f, H_ctf, cfg)

    @classmethod
    def rect_pulse(cls, cfg: LinkConfig, At: float) -> 'IEEECOMFilter':
        """
        Build the rectangular transmit pulse transfer function.

        Reference:
        - IEEE 802.3 Annex 93A.1.4, Eq. 93A-23.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        At:
            Rectangular pulse amplitude in V.
        """
        f = cfg.freqs
        X_f = At * cfg.bt * np.sinc(f * cfg.bt)
        return cls.from_tf(f, X_f, cfg)

    @classmethod
    def transition_time_filter(cls, cfg: LinkConfig, Tr: float) -> 'IEEECOMFilter':
        """
        Build the transmitter transition-time filter.

        Reference:
        - IEEE 802.3 Annex 93A, Eq. 93A-46.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        Tr:
            20%-80% transition time in seconds.
        """
        p1 = 1.6832
        f = cfg.freqs
        Tr = float(Tr)
        H_t = np.exp(-2 * (np.pi * f * Tr / p1)**2)
        return cls.from_tf(f, H_t, cfg=cfg)

# ========================================
# Configs (all integrated in COMConfig)
# ========================================

@dataclass(repr=False)
class COMPkgConfig(_PrettyDataclass):
    """
    COM package configuration using internal formula units.

    Unit contract:
    - capacitance values are stored in F
    - inductance values are stored in H
    - package transmission-line lengths remain in mm because 93A TL equations
      use mm with propagation coefficients defined per mm
    - resistance/impedance values are stored in ohm
    """
    C_d: float = 0.0                 # unit: F, single-ended device capacitance
    L_s: float = 0.0                 # unit: H, single-ended device series inductance
    C_b: float = 0.0                 # unit: F, single-ended bump/interface capacitance
    z_p: float = 0.0                 # unit: mm, package TL segment 1 length
    C_p: float = 0.0                 # unit: F, single-ended package-to-board capacitance
    enable: bool = True              # unit: boolean
    R0: float = 50.0                 # unit: ohm, single-ended reference resistance
    Z_c: float = 78.2                # unit: ohm, differential TL characteristic impedance
    z_p2: Optional[float] = None     # unit: mm, optional package TL segment 2 length
    Z_c2: float = 78.2               # unit: ohm, optional segment 2 differential impedance

    def __post_init__(self) -> None:
        if self.C_d < 0.0 or self.L_s < 0.0 or self.C_b < 0.0 or self.C_p < 0.0:
            raise ValueError("Package capacitance and inductance values must be non-negative.")
        if self.z_p < 0.0:
            raise ValueError("z_p must be non-negative.")
        if self.R0 <= 0.0 or self.Z_c <= 0.0:
            raise ValueError("R0 and Z_c must be positive.")
        if self.z_p2 is not None and self.z_p2 < 0.0:
            raise ValueError("z_p2 must be non-negative when provided.")
        if self.Z_c2 <= 0.0:
            raise ValueError("Z_c2 must be positive.")

@dataclass(repr=False)
class COMChannelConfig(_PrettyDataclass):
    """
    Victim and crosstalk channel configuration using internal formula units.

    freqs and s4p are populated after Touchstone loading. Excel can directly
    provide the path fields first.
    """
    victim_s4p_path: Optional[str] = None                   # unit: filesystem path
    next_s4p_paths: Sequence[str] = ()                      # unit: filesystem paths
    fext_s4p_paths: Sequence[str] = ()                      # unit: filesystem paths
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3)    # unit: zero-based S4P port order
    R0: float = 50.0                                        # unit: ohm, single-ended reference resistance
    gamma_src: complex | np.ndarray = 0.0                   # unit: dimensionless source reflection coefficient
    gamma_load: complex | np.ndarray = 0.0                  # unit: dimensionless load reflection coefficient

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
                    mode="s4p",
                    port_order=self.port_order,
                    z0=2.0 * self.R0,
                )
                freqs = channel.freqs
                delta_f = float(freqs[1] - freqs[0]) if len(freqs) > 1 else float("nan")
                summary.append({
                    "kind": kind,
                    "path": str(path),
                    "n": len(freqs),
                    "f_min": float(freqs[0]),
                    "f_max": float(freqs[-1]),
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
                    mode="s4p",
                    port_order=self.port_order,
                    z0=2.0 * self.R0,
                )
                for path in [
                    self.victim_s4p_path,
                    *self.next_s4p_paths,
                    *self.fext_s4p_paths,
                ]
                if path is not None
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
class COMFilterConfig(_PrettyDataclass):
    """
    COM filter configuration using internal formula units.

    This groups parameters used to build H_txffe, H_t, H_r, and H_ctf.
    """
    c_m3: float = 0.0                 # unit: dimensionless, TX FFE tap c(-3)
    c_m2: float = 0.0                 # unit: dimensionless, TX FFE tap c(-2)
    c_m1: float = 0.0                 # unit: dimensionless, TX FFE tap c(-1)
    c_1: float = 0.0                  # unit: dimensionless, TX FFE tap c(1)
    num_pre: int = 3                  # unit: samples/taps, main cursor index in txfir
    Tr: Optional[float] = None        # unit: s, 20%-80% transition time
    fr: Optional[float] = None        # unit: Hz, receiver noise-filter 3 dB bandwidth
    g_DC: Optional[float] = None      # unit: dB, receiver equalizer DC gain term
    g_DC2: Optional[float] = None     # unit: dB, receiver equalizer second DC gain term
    f_z: Optional[float] = None       # unit: Hz, receiver equalizer zero frequency
    f_LF: Optional[float] = None      # unit: Hz, receiver equalizer low-frequency pole/zero term
    f_p1: Optional[float] = None      # unit: Hz, receiver equalizer pole 1
    f_p2: Optional[float] = None      # unit: Hz, receiver equalizer pole 2
    A_v: float = 1.0                  # unit: V, victim rectangular pulse amplitude
    A_fe: float = 1.0                 # unit: V, FEXT rectangular pulse amplitude
    A_ne: float = 1.0                 # unit: V, NEXT rectangular pulse amplitude

    # derived attributes
    c_0: float = field(init=False)    # unit: dimensionless, TX FFE main cursor tap
    txfir: np.ndarray = field(init=False) # unit: dimensionless tap vector [c(-3), c(-2), c(-1), c(0), c(1)]

    def __post_init__(self):
        self.c_0 = 1.0 - abs(self.c_m3) - abs(self.c_m2) - abs(self.c_m1) - abs(self.c_1)
        self.txfir = np.r_[self.c_m3, self.c_m2, self.c_m1, self.c_0, self.c_1]

@dataclass(repr=False)
class COMDFEConfig(_PrettyDataclass):
    N_b: int                         # unit: taps, fixed DFE tap count
    b_max: float | np.ndarray        # unit: dimensionless, normalized fixed DFE coefficient limit

    # 802.3ck floating DFE optional
    N_bg: int = 0                     # unit: banks, number of DFE floating tap banks
    N_bf: int = 0                     # unit: taps/bank, number of floating taps per bank
    N_ts: Optional[int] = None        # unit: taps, floating tap tail starting position
    N_f: Optional[int] = None         # unit: taps, DFE maximum span including floating bank
    bb_max: Optional[float | np.ndarray] = None # unit: dimensionless, per-tap upper coefficient limit
    bb_min: Optional[float | np.ndarray] = None # unit: dimensionless, per-tap lower coefficient limit
    b_gmax: Optional[float | np.ndarray] = None # unit: dimensionless, floating tap magnitude limit
    sigma_tmax: Optional[float] = None # unit: dimensionless, floating tap tail RSS limit
    
    # derived attribution (not in spec)
    fixed_upper: np.ndarray = field(init=False)
    fixed_lower: np.ndarray = field(init=False)
    float_upper: np.ndarray = field(init=False)
    float_lower: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        "define the indicator mask of dfe coeff" 
        if (self.N_b < 0):
            raise ValueError("COMDFEConfig.N_b must be non-negative")

        if (self.N_bg == 0):
            self.N_ts = None
        elif (self.N_ts is None):
            self.N_ts = self.N_b + 1
        elif (self.N_ts <= self.N_b): 
            raise ValueError("COMDFEConfig.N_ts has setup error")
        
        if (self.N_f is None): 
            self.N_f = self.N_b
        elif (self.N_f < self.N_b+self.N_bg*self.N_bf):
            raise ValueError("COMDFEConfig.N_f/N_bg/N_bf has setup error")
        if (self.N_bg > 0):
            if (self.N_bf <= 0):
                raise ValueError("COMDFEConfig.N_bf has setup error")
            if (self.N_ts is None) or (self.N_ts > self.N_f):
                raise ValueError("COMDFEConfig.N_ts/N_f has setup error")
            if (self.sigma_tmax is None):
                raise ValueError("COMDFEConfig.sigma_tmax is required when floating DFE is enabled")

        # all bounds will be normalized to np.ndarray with len = N_f
        if (self.N_f == 0):
            self.fixed_upper = np.zeros(0)
            self.fixed_lower = np.zeros(0)
            self.float_upper = np.zeros(0)
            self.float_lower = np.zeros(0)
            return

        if (self.bb_max is None):
            self.fixed_upper = self.b_max * np.ones(self.N_f)
        elif isinstance(self.bb_max, np.ndarray):
            self.fixed_upper = np.r_[self.bb_max, np.zeros(self.N_f - len(self.bb_max))]
        else:
            self.fixed_upper = self.bb_max * np.ones(self.N_f)

        if (self.bb_min is None):
            self.fixed_lower = - self.b_max * np.ones(self.N_f)
        elif isinstance(self.bb_min, np.ndarray):
            self.fixed_lower = np.r_[self.bb_min, np.zeros(self.N_f - len(self.bb_min))]
        else:
            self.fixed_lower = self.bb_min * np.ones(self.N_f)

        if (self.b_gmax is None):
            self.float_upper = self.fixed_upper
            self.float_lower = self.fixed_lower
        elif isinstance(self.b_gmax, np.ndarray):
            self.float_upper = np.minimum(
                self.fixed_upper, 
                np.r_[np.zeros(self.N_f - len(self.b_gmax)), +self.b_gmax]
            )
            self.float_lower = np.maximum(
                self.fixed_lower,
                np.r_[np.zeros(self.N_f - len(self.b_gmax)), -self.b_gmax]
            )
        else:
            self.float_upper = +self.b_gmax * np.ones(self.N_f)
            self.float_lower = -self.b_gmax * np.ones(self.N_f)

@dataclass(repr=False)
class COMImpairmentConfig(_PrettyDataclass):
    R_LM: float                     # unit: dimensionless, level separation mismatch ratio
    SNR_TX: float                   # unit: dB, transmitter signal-to-noise ratio
    sigma_RJ: float                 # unit: UI, random jitter RMS
    A_DD: float                     # unit: UI, dual-Dirac jitter amplitude
    eta_0: float                    # unit: V^2/Hz, one-sided noise spectral density

@dataclass(repr=False)
class COMPMFConfig(_PrettyDataclass):
    """
    PMF-domain configuration for 93A.1.7 interference/noise distributions.

    This config owns only amplitude-axis and PMF numerical controls. It does
    not own channel construction, DFE selection, or impairment statistics.
    """
    dy_override: Optional[float] = None # unit: V, explicit PMF amplitude grid step; if None derive from As
    dy_rel_As: float = 1e-3           # unit: dimensionless, default dy limit = 0.1% of As (from spec)
    dy_abs_max: float = 0.01e-3       # unit: V, default dy absolute limit = 0.01 mV (from spec)
    tap_abs_th_override: Optional[float] = None # unit: V, explicit tap threshold; if None derive from As
    tap_rel_As: float = 1e-3          # unit: dimensionless, ignore pulse terms below 0.1% of As (from spec)
    keep_mass: float = 1.0            # unit: probability, optional PMF truncation target
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

    def resolve(self, As: float) -> 'COMPMFRuntimeConfig':
        As_abs = abs(float(As))
        if not np.isfinite(As_abs) or As_abs <= 0.0:
            raise ValueError("As must be finite and positive to resolve COMPMFConfig.")

        dy = self.dy_override if self.dy_override is not None else min(self.dy_abs_max, self.dy_rel_As * As_abs)
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
class COMPMFRuntimeConfig(_PrettyDataclass):
    """Resolved PMF numerical settings for one COM run."""
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
class COMConfig(_PrettyDataclass):
    """Top-level COM configuration grouped by function."""
    link: LinkConfig                  # unit contract: Hz/s grid owned by LinkConfig
    filter: COMFilterConfig           # unit contract: internal filter units
    channel: COMChannelConfig         # unit contract: paths, ohm, dimensionless reflection coefficients
    pkg: COMPkgConfig                 # unit contract: F/H/mm/ohm package parameters

    dfe: COMDFEConfig                 # unit contract: tap counts and normalized coefficients
    impairment: COMImpairmentConfig   # unit contract: voltage/noise/jitter settings
    L: int                            # unit: count, number of signal levels
    DER_0: float                    # unit: dimensionless, target detector error ratio
    pmf: COMPMFConfig = field(default_factory=COMPMFConfig) # unit contract: PMF amplitude grid and numerical controls

# ========================================
# Status (all integrated in COMStatus)
# ========================================

@dataclass(repr=False)
class COMSharedPath(_PrettyDataclass):
    H_ffe: IEEECOMFilter
    H_ffe_next: IEEECOMFilter
    H_t: IEEECOMFilter
    S_rx: IEEECOMsparam
    H_r: IEEECOMFilter
    H_ctf: IEEECOMFilter

@dataclass(repr=False)
class COMPath(_PrettyDataclass):
    kind: Literal["victim", "next", "fext"]
    shared: COMSharedPath   # all paths point to same object

    # the following are non-shared (path-specific)
    S_tx: SparamModel
    S_ch: SparamModel
    S_all: SparamModel      # augmented signal path
    H_21: LinkSegment
    H_all: LinkSegment      # voltage transfer function with filters
    X: IEEECOMFilter
    pulse: LinkSegment      # H_all(f) * X(f), used for h^(k)(t)

    # proxy of shared object
    @property
    def H_ffe(self) -> IEEECOMFilter:
        if (self.kind == "next"):
            return self.shared.H_ffe_next
        else:
            return self.shared.H_ffe

    @property
    def H_t(self) -> IEEECOMFilter:
        return self.shared.H_t
    @property
    def S_rx(self) -> SparamModel:
        return self.shared.S_rx
    @property
    def H_r(self) -> IEEECOMFilter:
        return self.shared.H_r
    @property
    def H_ctf(self) -> IEEECOMFilter:
        return self.shared.H_ctf

@dataclass(repr=False)
class COMDFEStatus(_PrettyDataclass):
    ts: int                         # unit: sample index on cfg.times
    pos: int                        # unit: sample phase index, 0 <= pos < per_ui
    dfe_coeff: np.ndarray           # unit: dimensionless, b(1)..b(N)
    h_ISI: np.ndarray               # unit: V, sampled residual ISI response

@dataclass(repr=False)
class COMImpairmentStatus(_PrettyDataclass):
    As: float                       # unit: V, signal amplitude
    sigma_X: float                  # unit: dimensionless, normalized symbol standard deviation
    sigma_TX: float                 # unit: V, TX noise amplitude standard deviation
    h_ISI: np.ndarray               # unit: V, residual ISI pulse samples
    sigma_ISI: float                # unit: V, ISI amplitude standard deviation
    h_J: np.ndarray
    sigma_J: float                  # unit: V, jitter-induced amplitude standard deviation
    h_XTs_dsamp: list[np.ndarray]
    sigma_XT: float                 # unit: V, crosstalk amplitude standard deviation
    sigma_N: float                  # unit: V, receiver noise amplitude standard deviation

@dataclass(repr=False)
class COMPMFStatus(_PrettyDataclass):
    """
    PMF-domain intermediate and final results for 93A.1.7.

    Each PMF is represented on a quantized amplitude axis by Pmf1D. Fields may
    stay None while the PMF pipeline is being built step by step.
    """
    dy: float                          # unit: V, amplitude grid step used for PMF quantization
    tap_abs_th: float                   # unit: V, absolute tap threshold used for PMF construction
    p_ISI: Optional[Pmf1D] = None      # ISI distribution from h_ISI(n), Eq. 93A-40
    p_G: Optional[Pmf1D] = None # Gaussian noise distribution, Eq. 93A-42
    p_DD: Optional[Pmf1D] = None # dual-Dirac jitter distribution
    p_XT: Optional[Pmf1D] = None # combined crosstalk distribution, Eq. 93A-44
    p_combined: Optional[Pmf1D] = None # combined interference and noise distribution, Eq. 93A-45
    y0: Optional[float] = None         # unit: V, CDF inverse at DER_0
    A_ni: Optional[float] = None       # unit: V, noise/interference amplitude = abs(y0)
    COM: Optional[float] = None        # unit: dB, final COM = 20log10(As/A_ni)
    
@dataclass(repr=False)
class COMStatus(_PrettyDataclass):
    paths: list[COMPath]
    dfe: Optional['COMDFEStatus'] = None
    impairment: Optional['COMImpairmentStatus'] = None
    pmf: Optional['COMPMFStatus'] = None

    @property
    def victim(self) -> COMPath:
        return self.paths[0]

    @property
    def xtalks(self) -> list[COMPath]:
        return self.paths[1:]

# ======================================
# class helpers
# ======================================

def _build_txpkg(freqs: np.ndarray, txpkg_cfg: COMPkgConfig, *, isNext: bool = False) -> IEEECOMsparam:
    """
    Build the 93A TX package S-parameter model.

    Reference:
    - IEEE 802.3 Annex 93A.1.2.4, Eq. 93A-15 and Eq. 93A-15a.
    - IEEE 802.3ck Annex 93A adds optional second TL segment Eq. 93A-16b.

    Parameters
    ----------
    freqs:
        Frequency axis in Hz.
    txpkg_cfg:
        Package config with C_d/C_b/C_p in F, L_s in H, z_p/z_p2 in mm,
        and R0/Z_c/Z_c2 in ohm.
    isNext:
        Path flag for NEXT package construction. Current 93A package primitive
        construction uses the same fields; invoking clauses may later select
        different package parameters for NEXT.
    """
    freqs = LinkConfig.validate_freqs(freqs)
    C_d = txpkg_cfg.C_d
    L_s = txpkg_cfg.L_s
    C_b = txpkg_cfg.C_b
    C_p = txpkg_cfg.C_p

    S_d = IEEECOMsparam.shunt_capacitance(freqs, C_d, txpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance(freqs, L_s, txpkg_cfg.R0)
    S_b = IEEECOMsparam.shunt_capacitance(freqs, C_b, txpkg_cfg.R0)
    S_l = IEEECOMsparam.pkg_trans_line(freqs, txpkg_cfg.R0, txpkg_cfg.z_p, Zc=txpkg_cfg.Z_c)
    if (txpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line(freqs, txpkg_cfg.R0, txpkg_cfg.z_p2, Zc=txpkg_cfg.Z_c2)
    S_p = IEEECOMsparam.shunt_capacitance(freqs, C_p, txpkg_cfg.R0)

    # cascade
    S_td = (S_d.cascade_com(S_s)).cascade_com(S_b)
    if (txpkg_cfg.z_p2 is not None):
        S_tp = ((S_td.cascade_com(S_l)).cascade_com(S_l2)).cascade_com(S_p)
    else:
        S_tp = (S_td.cascade_com(S_l)).cascade_com(S_p)
    return S_tp

def _build_rxpkg(freqs: np.ndarray, rxpkg_cfg: COMPkgConfig) -> IEEECOMsparam:
    """
    Build the 93A RX package S-parameter model.

    Reference:
    - IEEE 802.3 Annex 93A.1.2.4, Eq. 93A-16 and Eq. 93A-16a.
    - IEEE 802.3ck Annex 93A adds optional second TL segment Eq. 93A-16c.

    Parameters
    ----------
    freqs:
        Frequency axis in Hz.
    rxpkg_cfg:
        Package config with C_d/C_b/C_p in F, L_s in H, z_p/z_p2 in mm,
        and R0/Z_c/Z_c2 in ohm.
    """
    freqs = LinkConfig.validate_freqs(freqs)
    C_d = rxpkg_cfg.C_d
    L_s = rxpkg_cfg.L_s
    C_b = rxpkg_cfg.C_b
    C_p = rxpkg_cfg.C_p

    S_p = IEEECOMsparam.shunt_capacitance(freqs, C_p, rxpkg_cfg.R0)
    if (rxpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line(freqs, rxpkg_cfg.R0, rxpkg_cfg.z_p2, Zc=rxpkg_cfg.Z_c2)
    S_l = IEEECOMsparam.pkg_trans_line(freqs, rxpkg_cfg.R0, rxpkg_cfg.z_p, Zc=rxpkg_cfg.Z_c)
    S_b = IEEECOMsparam.shunt_capacitance(freqs, C_b, rxpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance(freqs, L_s, rxpkg_cfg.R0)
    S_d = IEEECOMsparam.shunt_capacitance(freqs, C_d, rxpkg_cfg.R0)
    
    # cascade
    S_rd = (S_b.cascade_com(S_s)).cascade_com(S_d)
    if (rxpkg_cfg.z_p2 is not None):
        S_rp = ((S_p.cascade_com(S_l2)).cascade_com(S_l)).cascade_com(S_rd)
    else:
        S_rp = (S_p.cascade_com(S_l)).cascade_com(S_rd)
    return S_rp

def _build_H_ffe(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build victim/FEXT TX FFE filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with dimensionless TX FFE taps.
    """
    return IEEECOMFilter.tx_ffe(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)

def _build_H_ffe_next(link_cfg: LinkConfig) -> IEEECOMFilter:
    """
    Build NEXT TX FFE filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.

    NEXT uses only the main cursor per 93A.1.4.2.
    """
    ffe_next = np.array([0,1,0])
    return IEEECOMFilter.tx_ffe(link_cfg, ffe_next, num_pre=1)

def _build_H_t(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build transmitter transition-time filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with Tr in seconds.
    """
    return IEEECOMFilter.transition_time_filter(link_cfg, ft_cfg.Tr)

def _build_H_r(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build receiver noise filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with fr in Hz.
    """
    return IEEECOMFilter.rx_noise_filter(link_cfg, ft_cfg.fr)

def _build_H_ctf(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build receiver equalizer / CTF filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with gains in dB and pole/zero frequencies in Hz.
    """

    return IEEECOMFilter.rx_equalizer(
        link_cfg, 
        ft_cfg.g_DC,
        ft_cfg.g_DC2,
        ft_cfg.f_z,
        ft_cfg.f_LF,
        ft_cfg.f_p1,
        ft_cfg.f_p2
    )

def _build_channel_under_test(channel_cfg: COMChannelConfig) -> list[SparamModel]:
    """
    Build measured-domain channel-under-test S-parameter models.

    Output order:
    - index 0: victim channel
    - following indices: NEXT channels, then FEXT channels, in config order

    If channel grids differ, all returned models are resampled onto a common
    measured-domain intersection grid:
        f_min = max(raw f_min)
        f_max = min(raw f_max)
        df = min(raw df)

    This performs only in-band interpolation. S-parameter extrapolation is not
    allowed here. Conversion to LinkConfig's FFT grid happens only after H21(f)
    is computed.
    """
    if channel_cfg.victim_s4p_path is None:
        raise ValueError("channel_cfg.victim_s4p_path must be provided.")

    paths = [
        channel_cfg.victim_s4p_path,
        *channel_cfg.next_s4p_paths,
        *channel_cfg.fext_s4p_paths,
    ]

    channel_models = [
        IEEECOMsparam.from_touchstone(
            path,
            mode="s4p",
            port_order=channel_cfg.port_order,
            z0=2.0 * channel_cfg.R0,
        )
        for path in paths
    ]

    common_freqs = channel_cfg.align_grid(channel_models)
    return [channel.resampled(common_freqs) for channel in channel_models]

def _build_path(
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig,
    pkg_cfg: COMPkgConfig,
    shared: COMSharedPath,
    kind: Literal["victim", "next", "fext"],
    S_ch: SparamModel,
) -> COMPath:
    """
    Build one COM signal path from a measured-domain channel-under-test model.

    Parameters
    ----------
    link_cfg:
        LinkConfig that defines the scalar response FFT/time grid.
    channel_cfg:
        Channel configuration containing source/load reflection coefficients.
    ft_cfg:
        Filter configuration containing victim/FEXT/NEXT pulse amplitudes.
    pkg_cfg:
        Package configuration used to build Tx/Rx package models on S_ch.freqs.
    shared:
        Shared COM path blocks built on this run's common measured frequency
        grid and LinkConfig scalar grid.
    kind:
        Path type: victim, next, or fext.
    S_ch:
        Measured-domain channel-under-test Sdd model for this path. Tx/Rx
        package models are sampled on this same frequency axis before cascade.
    """
    if not np.allclose(S_ch.freqs, shared.S_rx.freqs):
        raise ValueError("S_ch.freqs must match shared.S_rx.freqs for measured-domain cascade.")

    if kind == "next":
        S_tx = _build_txpkg(S_ch.freqs, pkg_cfg, isNext=True)
        H_ffe = shared.H_ffe_next
        X = IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_ne)
    elif kind == "fext":
        S_tx = _build_txpkg(S_ch.freqs, pkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_fe)
    elif kind == "victim":
        S_tx = _build_txpkg(S_ch.freqs, pkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_v)
    else:
        raise ValueError(f"Unsupported COM path kind: {kind}")

    S_all = S_tx.cascade_com(S_ch).cascade_com(shared.S_rx)
    H_21 = S_all.to_LinkSegment(
        link_cfg,
        gamma_src=channel_cfg.gamma_src,
        gamma_load=channel_cfg.gamma_load,
    )
    H_all = (
        H_ffe
        .cascade_tf(shared.H_t)
        .cascade_tf(H_21)
        .cascade_tf(shared.H_r)
        .cascade_tf(shared.H_ctf)
    )
    pulse = H_all.cascade_tf(X)

    return COMPath(
        kind=kind,
        shared=shared,
        S_tx=S_tx,
        S_ch=S_ch,
        S_all=S_all,
        H_21=H_21,
        H_all=H_all,
        X=X,
        pulse=pulse,
    )

def _build_shared_path(cfg: COMConfig, freqs: np.ndarray) -> COMSharedPath:
    """
    Build path-shared COM models.

    This is a LV-2 COM path-generation helper. It builds the shared receiver
    package model on the measured-domain channel grid and the shared scalar
    filters on the LinkConfig FFT grid.
    """
    link_cfg = cfg.link
    pkg_cfg = cfg.pkg
    ft_cfg = cfg.filter
    return COMSharedPath(
        H_ffe=_build_H_ffe(link_cfg, ft_cfg),
        H_ffe_next=_build_H_ffe_next(link_cfg),
        H_t=_build_H_t(link_cfg, ft_cfg),
        S_rx=_build_rxpkg(freqs, pkg_cfg),
        H_r=_build_H_r(link_cfg, ft_cfg),
        H_ctf=_build_H_ctf(link_cfg, ft_cfg),
    )

def _build_paths(
    cfg: COMConfig,
    shared: COMSharedPath,
    channels: list[SparamModel],
) -> list[COMPath]:
    """
    Build path-specific COM models from aligned channel-under-test models.

    Contract:
    channels must come directly from _build_channel_under_test(), so the order is:
        index 0: victim channel
        following indices: NEXT channels, then FEXT channels, in config order
    """
    link_cfg = cfg.link
    ch_cfg = cfg.channel
    ft_cfg = cfg.filter
    pkg_cfg = cfg.pkg

    expected_count = 1 + len(ch_cfg.next_s4p_paths) + len(ch_cfg.fext_s4p_paths)
    if len(channels) != expected_count:
        raise ValueError(
            "channels length must match victim + NEXT + FEXT path count. "
            f"Expected {expected_count}, got {len(channels)}."
        )

    paths = [
        _build_path(
            link_cfg=link_cfg,
            channel_cfg=ch_cfg,
            ft_cfg=ft_cfg,
            pkg_cfg=pkg_cfg,
            shared=shared,
            kind="victim",
            S_ch=channels[0],
        )
    ]

    next_count = len(ch_cfg.next_s4p_paths)
    next_channels = channels[1 : 1 + next_count]
    fext_channels = channels[1 + next_count :]

    for S_ch in next_channels:
        paths.append(
            _build_path(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                pkg_cfg=pkg_cfg,
                shared=shared,
                kind="next",
                S_ch=S_ch,
            )
        )

    for S_ch in fext_channels:
        paths.append(
            _build_path(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                pkg_cfg=pkg_cfg,
                shared=shared,
                kind="fext",
                S_ch=S_ch,
            )
        )

    return paths

def _calculate_float_dfe(h_dsamp:np.ndarray, dfe_cfg: COMDFEConfig) -> np.ndarray:
    "post-(N_b+1) ~ post-(N_f)"
    num_pre = np.argmax(np.abs(h_dsamp))
    dfe_raw_float = h_dsamp[num_pre+dfe_cfg.N_b+1: num_pre+dfe_cfg.N_f+1] / h_dsamp[num_pre]
    dfe_coeff_float = np.clip(
        dfe_raw_float, 
        dfe_cfg.float_lower[dfe_cfg.N_b: dfe_cfg.N_f], 
        dfe_cfg.float_upper[dfe_cfg.N_b: dfe_cfg.N_f]
    )

    num_candid = (dfe_cfg.N_f-dfe_cfg.N_bf+1) - (dfe_cfg.N_b)     # post7~38, 4taps/bank => (38-4+1)-7+1
    candidates = np.zeros((num_candid, dfe_cfg.N_bf))
    RSS_candid = np.zeros(num_candid)
    for c_idx in range(num_candid):
        candidates[c_idx, :] = c_idx + np.arange(dfe_cfg.N_b+1, dfe_cfg.N_b+1 + dfe_cfg.N_bf)
        RSS_candid[c_idx] = np.sum(dfe_coeff_float[c_idx: c_idx+dfe_cfg.N_bf]**2)

    taps_selected = []
    for _ in range(dfe_cfg.N_bg):
        c_idx = np.argmax(RSS_candid)                   # choose current maximum RSS
        taps_selected.extend(candidates[c_idx,:])
        lo = max(0, c_idx-dfe_cfg.N_bf+1)
        hi = min(num_candid, c_idx+dfe_cfg.N_bf)
        RSS_candid[lo:hi] = -1                          # remove overlapped candidates
    taps_selected = np.sort(taps_selected)
    dfe_float_mask = np.zeros(dfe_cfg.N_f - dfe_cfg.N_b)
    dfe_float_mask[(taps_selected-dfe_cfg.N_b-1).astype(int)] = 1
    dfe_coeff_float = dfe_coeff_float * dfe_float_mask

    dfe_coeff_float_tail = dfe_coeff_float[dfe_cfg.N_ts-dfe_cfg.N_b-1:]
    sigma_t = np.sqrt(np.sum(dfe_coeff_float_tail**2))
    if (sigma_t > dfe_cfg.sigma_tmax):
        dfe_coeff_float_tail = dfe_coeff_float_tail * (dfe_cfg.sigma_tmax / sigma_t)
        dfe_coeff_float[dfe_cfg.N_ts-dfe_cfg.N_b-1:] = dfe_coeff_float_tail.copy()

    return dfe_coeff_float

def _calculate_h_ISI(h_dsamp: np.ndarray, dfe_coeff: np.ndarray) -> np.ndarray:
    num_pre = np.argmax(np.abs(h_dsamp))
    h_ISI = h_dsamp.copy()
    h_ISI[num_pre] = 0
    h_ISI[num_pre+1: num_pre+len(dfe_coeff)+1] -= dfe_coeff * h_dsamp[num_pre]
    return h_ISI

def _find_sampling_phase_93a(
    h: np.ndarray,
    link_cfg: LinkConfig,
    dfe_cfg: COMDFEConfig,
) -> tuple[int, int]:
    """
    Find sampling instant and phase by IEEE 802.3 Annex 93A Eq. 93A-25.

    Returns
    -------
    tuple[int, int]
        (ts, pos), where ts is the sample index on link_cfg.times and pos is
        the sample phase index in [0, link_cfg.per_ui).
    """
    def is_h_dsmp_valid(h_dsamp: np.ndarray) -> int:
        num_pre = np.argmax(np.abs(h_dsamp))
        if (h_dsamp[num_pre] < 0):
            raise Exception("Polarity issue @ _find_sampling_phase_93a()")
        if (num_pre == 0 or num_pre + dfe_cfg.N_f >= len(h_dsamp)):
            raise Exception("Main cursor too close to boundary @ _find_sampling_phase_93a()")
        return num_pre

    M = link_cfg.per_ui
    errs = np.zeros(M)
    ts_candidates = np.zeros(M, dtype=int)

    for pos in range(M):
        h_dsamp = h[pos::M]
        num_pre = is_h_dsmp_valid(h_dsamp)
        h_0 = h_dsamp[num_pre]
        ts_candidates[pos] = pos + num_pre * M
        if (dfe_cfg.N_b == 0):
            dfe_post1 = 0.0
        else:
            dfe_post1 = np.clip(
                h_dsamp[num_pre+1] / h_0,
                dfe_cfg.fixed_lower[0],
                dfe_cfg.fixed_upper[0],
            )
        errs[pos] = h_dsamp[num_pre-1] - h_dsamp[num_pre+1] + h_dsamp[num_pre] * dfe_post1

    min_err = np.min(abs(errs))
    tol = max(1e-12, 1e-9 * np.max(np.abs(errs)))   # allow numerical error
    pos_candid = np.where(np.abs(errs) <= min_err + tol)[0]
    peak_idx = int(np.argmax(np.abs(h)))
    prior_pos_candid = pos_candid[ts_candidates[pos_candid] < peak_idx]
    if len(prior_pos_candid) > 0:
        pos = int(prior_pos_candid[np.argmax(ts_candidates[prior_pos_candid])])
    else:
        pos = int(pos_candid[np.argmin(np.abs(ts_candidates[pos_candid] - peak_idx))])
    ts = int(ts_candidates[pos])
    return ts, pos

def _calculate_h_J(h: np.ndarray, ts: int, per_ui: int) -> np.ndarray:
    """
    Calculate sampled jitter sensitivity using the selected sampling instant.

    The finite difference is evaluated at samples with the same phase as ts:
        h_J[n] = (h[t_s+nT_b+dt] - h[t_s+nT_b-dt]) / (2/M)

    Boundary samples that cannot provide both +/- one oversampled point are
    skipped instead of relying on Python negative indexing.
    """
    pos = int(ts) % per_ui
    center_idx = np.arange(pos, len(h), per_ui)
    valid = (center_idx > 0) & (center_idx < len(h) - 1)
    center_idx = center_idx[valid]
    if len(center_idx) == 0:
        raise ValueError("No valid samples for h_J finite difference.")

    h_m1 = h[center_idx - 1]
    h_p1 = h[center_idx + 1]
    h_J = (h_p1 - h_m1) / (2/per_ui)
    return h_J

def _find_pos_xtalk(h_XT: np.ndarray, per_ui: int) -> tuple[int, np.ndarray]:
    RSS = np.zeros(per_ui)
    for m in np.arange(per_ui):
        RSS[m] = np.sum(h_XT[m:: per_ui]**2)
    i = np.argmax(RSS)
    h_XT_dsamp = h_XT[i:: per_ui]
    return i, h_XT_dsamp

def _build_pmf_interference(
    p_sig: Pmf1D, 
    h: np.ndarray, 
    pmf_cfg: COMPMFRuntimeConfig, 
    name: Optional[str] = None
) -> Pmf1D:
    "Eq. 93A-39"
    return p_sig.copy().fir_filter(
        fir = h,
        keep_mass = pmf_cfg.keep_mass,
        dx_ref = pmf_cfg.dy,
        tap_abs_th = pmf_cfg.tap_abs_th,
        max_taps = None,
        name = name
    )

def _build_pmf_G(imp_stat: COMImpairmentStatus, imp_cfg: COMImpairmentConfig, pmf_cfg: COMPMFRuntimeConfig) -> Pmf1D:
    "Eq. 93A-41 and 93A-42"
    sigma_G = np.sqrt( 
        imp_stat.sigma_TX**2 + imp_stat.sigma_N**2 +
        imp_cfg.sigma_RJ**2 * imp_stat.sigma_X**2 * np.sum(imp_stat.h_J**2) 
    )
    return Pmf1D.gaussian(
        mu=0,
        sigma=sigma_G,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Noise"
    )

def _build_pmf_XT_all(
    p_sig: Pmf1D, 
    h_XTs: list[np.ndarray], 
    pmf_cfg: COMPMFRuntimeConfig, 
) -> Pmf1D:
    p_XT = Pmf1D.multi_dirac(np.array([0.0]), np.array([1.0]), dx=pmf_cfg.dy, unit="volt", name="XT_all")
    for h_XT in h_XTs:
        p_XT_new = _build_pmf_interference(
            p_sig, 
            h_XT, 
            pmf_cfg,
            name="XT",
        )
        p_XT = p_XT.combine(p_XT_new, name="XT_all")
    p_XT.name = "XT_all"
    return p_XT

#%% conduct search in this class
class COM:
    def __init__(self, cfg: COMConfig):
        self.cfg = cfg
        self.status: Optional[COMStatus] = None

    def run(self) -> COMStatus:
        """
        Run COM for the current scalar configuration.

        This method is intentionally kept as the public entry point. Today it
        runs one concrete COMConfig point. When the COM search space is added,
        run() should own the sweep and delegate each candidate to _run_once().
        """
        self.status = self._run_once()
        return self.status

    def _run_once(self) -> COMStatus:
        """
        Run one concrete COMConfig point without sweeping tunable parameters.

        This is the debug-friendly single-candidate pipeline:
        paths -> DFE/sample phase -> impairments -> PMF/COM.
        """
        paths = self.build_all_paths()
        dfe_status = self.find_pos_and_dfe(h=paths[0].pulse.ir)
        imp_status = self.calculate_impairments(
            h=paths[0].pulse.ir,
            dfe_status=dfe_status,
            h_XTs=[path.pulse.ir for path in paths[1:]],
        )
        pmf_status = self.calculate_COM(imp_status)
        return COMStatus(paths=paths, dfe=dfe_status, impairment=imp_status, pmf=pmf_status)

    # ------------------
    # proxy
    # ------------------
    def _require_status(self) -> COMStatus:
        if self.status is None:
            raise RuntimeError("COM status is not available. Run COM.run() first.")
        return self.status

    @property
    def per_ui(self) -> int:
        return self.cfg.link.per_ui

    @property
    def paths(self) -> list[COMPath]:
        return self._require_status().paths

    @property
    def victim(self) -> COMPath:
        return self._require_status().victim

    @property
    def xtalks(self) -> list[COMPath]:
        return self._require_status().xtalks

    @property
    def h(self) -> np.ndarray:
        """Victim pulse response h^(0)(t), as status.victim.pulse.ir."""
        return self.victim.pulse.ir

    @property
    def h_XT(self) -> list[np.ndarray]:
        """Crosstalk pulse responses h^(k)(t), k > 0."""
        return [path.pulse.ir for path in self.xtalks]

    @property
    def dfe_status(self) -> Optional[COMDFEStatus]:
        return self._require_status().dfe

    @property
    def impairment_status(self) -> Optional[COMImpairmentStatus]:
        return self._require_status().impairment

    @property
    def pmf_status(self) -> Optional[COMPMFStatus]:
        return self._require_status().pmf

    # LV-1 methods
    def build_all_paths(self) -> list[COMPath]:
        """
        Build all COM paths.

        LV-1 hierarchy:
        1. build channel-under-test models
        2. build path-shared models
        3. build every path-specific model
        """
        channels = _build_channel_under_test(self.cfg.channel)
        shared = _build_shared_path(self.cfg, channels[0].freqs)
        return _build_paths(self.cfg, shared, channels)

    def find_pos_and_dfe(self, h: np.ndarray) -> COMDFEStatus:
        """
        Find sampling phase and DFE coefficients.

        Reference:
        - IEEE 802.3 Annex 93A.1.6, Eq. 93A-25 and Eq. 93A-26.

        Parameters
        ----------
        h:
            Victim pulse response in V, sampled on self.cfg.link time grid.

        Uses
        ----
        self.cfg.link:
            LinkConfig with per_ui samples/UI and time/frequency grid in SI units.
        self.cfg.dfe:
            DFE config with tap counts and dimensionless normalized coefficient limits.
        """
        link_cfg = self.cfg.link
        dfe_cfg = self.cfg.dfe

        M = link_cfg.per_ui

        # step 1: find sample phase by Eq. 93A-25
        ts, pos = _find_sampling_phase_93a(h, link_cfg, dfe_cfg)

        # step 2: determine fixed taps
        h_dsamp = h[pos::M]
        num_pre = (ts - pos) // M
        dfe_raw_fixed = h_dsamp[num_pre+1: num_pre+dfe_cfg.N_b+1] / h_dsamp[num_pre]
        dfe_coeff_fixed = np.clip(
            dfe_raw_fixed, 
            dfe_cfg.fixed_lower[0:dfe_cfg.N_b], 
            dfe_cfg.fixed_upper[0:dfe_cfg.N_b]
        )

        # step 3: determine float taps, and combine all dfe coeff as an array: (N_f,)
        if (dfe_cfg.N_bg==0):
            dfe_coeff = dfe_coeff_fixed
        else:
            dfe_coeff_float = _calculate_float_dfe(h_dsamp, dfe_cfg)    
            dfe_coeff = np.r_[
                dfe_coeff_fixed, 
                np.zeros(dfe_cfg.N_b-len(dfe_coeff_fixed)),
                dfe_coeff_float
            ]

        # step 4: calculate h_ISI
        h_ISI = _calculate_h_ISI(h_dsamp, dfe_coeff)

        return COMDFEStatus(ts=ts, pos=pos, dfe_coeff=dfe_coeff, h_ISI=h_ISI)

    def calculate_impairments(
        self,
        h: np.ndarray,
        dfe_status: COMDFEStatus,
        h_XTs: list[np.ndarray],
    ) -> COMImpairmentStatus:

        L = self.cfg.L
        link_cfg = self.cfg.link
        imp_cfg = self.cfg.impairment
        ft_cfg = self.cfg.filter
        
        ts = dfe_status.ts
        pos = dfe_status.pos
        h_ISI = dfe_status.h_ISI
        h_dsamp = h[pos:: self.per_ui]
        num_pre = (ts - pos) // self.per_ui
        h_main = h_dsamp[num_pre]

        # As
        As = imp_cfg.R_LM * h_main / (L - 1)

        # sigma_x
        sigma_X = np.sqrt( (L**2 - 1) / (3 * (L-1)**2) )

        # sigma_TX
        sigma_TX = np.sqrt(h_main**2 * 10**(-imp_cfg.SNR_TX / 10))

        # sigma_ISI
        sigma_ISI = np.sqrt( sigma_X**2 * np.sum(h_ISI**2) )

        # sigma_J
        h_J = _calculate_h_J(h, ts, self.per_ui)
        sigma_J = np.sqrt( (imp_cfg.A_DD**2+imp_cfg.sigma_RJ**2) * sigma_X**2 * np.sum(h_J**2) )

        # sigma_XT
        var_XT = 0
        h_XTs_dsamp = []
        for h_XT in h_XTs:
            i, h_XT_dsamp = _find_pos_xtalk(h_XT, self.per_ui) 
            var_XT += sigma_X**2 * np.sum(h_XT_dsamp**2)
            h_XTs_dsamp.append(h_XT_dsamp)
        sigma_XT = np.sqrt( var_XT )

        # sigma_N
        noise_psd = OneSidePSD.from_constant(link_cfg.freqs, imp_cfg.eta_0)
        noise_filter = (
            _build_H_r(link_cfg, ft_cfg)
            .cascade_tf(_build_H_ctf(link_cfg, ft_cfg))
        )
        sigma_N = noise_psd.filtered_by(noise_filter).to_sigma()

        return COMImpairmentStatus(
            As=As,
            sigma_X=sigma_X,
            sigma_TX=sigma_TX,
            h_ISI=h_ISI,
            sigma_ISI=sigma_ISI,
            h_J=h_J,
            sigma_J=sigma_J,
            h_XTs_dsamp=h_XTs_dsamp,
            sigma_XT=sigma_XT,
            sigma_N=sigma_N,
        )

    def calculate_COM(self, imp_status: COMImpairmentStatus) -> COMPMFStatus:
        L = self.cfg.L
        As = imp_status.As
        imp_cfg = self.cfg.impairment

        # Resolve PMF runtime config after As is known.
        pmf_cfg = self.cfg.pmf.resolve(As)

        # tx signal pmf
        p_sig = Pmf1D.multi_dirac(
            values = np.array([2*l/(L-1)-1 for l in range(L)]),
            probs = 1/L * np.ones(L),
            dx = pmf_cfg.dy,
            unit = "",
            name = "ideal_signal"
        )

        # ISI pmf
        p_ISI = _build_pmf_interference(
            p_sig, 
            imp_status.h_ISI, 
            pmf_cfg,
            name="ISI"
        )

        # Gaussian Noise pmf
        p_G = _build_pmf_G(imp_status, imp_cfg, pmf_cfg)

        # Dual-Dirac jitter pmf
        p_DD = _build_pmf_interference(
            p_sig, 
            imp_cfg.A_DD*imp_status.h_J, 
            pmf_cfg,
            name="Dual-Dirac"
        )

        # Xtalk pmf
        p_XT = _build_pmf_XT_all(p_sig, imp_status.h_XTs_dsamp, pmf_cfg)
        
        # combined pmf, A_ni
        p_combined = p_ISI.combine(p_G).combine(p_DD).combine(p_XT)
        y0 = p_combined.quantile(self.cfg.DER_0)
        A_ni = abs(y0)

        # COM
        COM = 20 * np.log10( As / A_ni )

        return COMPMFStatus(
            dy=pmf_cfg.dy,
            tap_abs_th=pmf_cfg.tap_abs_th,
            p_ISI=p_ISI,
            p_G=p_G,
            p_DD=p_DD,
            p_XT=p_XT,
            p_combined=p_combined,
            y0=y0,
            A_ni=A_ni,
            COM=COM
        )


def _smoke_test_com_path() -> COMStatus:
    """
    Run a small end-to-end COMPath smoke test with bundled reference channels.

    This is not a COM-correlation test. It only checks that the current pipeline
    can build channel-under-test S-parameters, package/filter blocks, per-path
    voltage transfer functions, and pulse responses without shape/contract
    errors.
    """
    project_root = Path(__file__).resolve().parents[2]
    chnl_dir = project_root / "reference_data" / "pychopmarg_example2" / "chnl_data"

    cfg = COMConfig(
        link=LinkConfig(fb=53.125e9, per_ui=64, target_df=1e7),
        filter=COMFilterConfig(
            c_m3=0.0,
            c_m2=0.0,
            c_m1=0.0,
            c_1=0.0,
            num_pre=3,
            Tr=1e-12,
            fr=40e9,
            g_DC=0.0,
            g_DC2=0.0,
            f_z=10e9,
            f_LF=1e9,
            f_p1=30e9,
            f_p2=80e9,
            A_v=1.0,
            A_fe=0.5,
            A_ne=0.25,
        ),
        channel=COMChannelConfig(
            victim_s4p_path=str(chnl_dir / "example2_THRU.s4p"),
            next_s4p_paths=(str(chnl_dir / "example2_NEXT1.s4p"),),
            fext_s4p_paths=(str(chnl_dir / "example2_FEXT1.s4p"),),
            port_order=(0, 2, 1, 3),
            R0=50.0,
            gamma_src=0.0,
            gamma_load=0.0,
        ),
        pkg=COMPkgConfig(
            C_d=0.0,
            L_s=0.0,
            C_b=0.0,
            z_p=0.0,
            C_p=0.0,
            enable=True,
            R0=50.0,
            Z_c=78.2,
            z_p2=None,
            Z_c2=78.2,
        ),
        dfe=COMDFEConfig(
            N_b=5,
            b_max=0.5,
        ),
        impairment=COMImpairmentConfig(
            R_LM=0.95,
            SNR_TX=30.0,
            sigma_RJ=0.01,
            A_DD=0.01,
            eta_0=1e-18,
        ),
        L=4,
        DER_0=1e-5,
    )

    status = COM(cfg).run()

    print("COMPath smoke test passed")
    print(f"path_count = {len(status.paths)}")
    for idx, path in enumerate(status.paths):
        delay = path.pulse.find_main_delay()
        print(
            f"[{idx}] kind={path.kind}, "
            f"S_all={path.S_all.sdd.shape}, "
            f"H_21={path.H_21.tf.shape}, "
            f"H_all={path.H_all.tf.shape}, "
            f"pulse_ir={path.pulse.ir.shape}, "
            f"peak_ui={delay['peak_time_ui']:.3f}"
        )

    return cfg, status

if __name__ == "__main__":
    cfg, status =  _smoke_test_com_path()
