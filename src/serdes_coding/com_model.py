from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
import sys
from typing import Literal, Optional, Sequence
import numpy as np

try:
    from .link_segment import LinkConfig, LinkSegment, SparamModel
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serdes_coding.link_segment import LinkConfig, LinkSegment, SparamModel


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
    this function stays simple and easy to edit. Values are expected to already
    use the spec/Excel-domain units documented by each config class.

    Required LinkConfig columns:
    - fb, per_ui, target_df

    Required COMFilterConfig columns:
    - c_m3, c_m2, c_m1, c_1, num_pre
    - Tr, fr, g_DC, g_DC2, f_z, f_LF, f_p1, f_p2
    - A_v, A_fe, A_ne

    Required COMChannelConfig columns:
    - victim_s4p_path, next_s4p_paths, fext_s4p_paths
    - port_order, R0, gamma_src, gamma_load

    Required COMPkgConfig columns:
    - C_d, L_s, C_b, z_p, C_p, pkg_enable
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
            fb=row["fb"],
            per_ui=row["per_ui"],
            target_df=row["target_df"],
        ),
        filter=COMFilterConfig(
            c_m3=row["c_m3"],
            c_m2=row["c_m2"],
            c_m1=row["c_m1"],
            c_1=row["c_1"],
            num_pre=row["num_pre"],
            Tr=row["Tr"],
            fr=row["fr"],
            g_DC=row["g_DC"],
            g_DC2=row["g_DC2"],
            f_z=row["f_z"],
            f_LF=row["f_LF"],
            f_p1=row["f_p1"],
            f_p2=row["f_p2"],
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
            C_d=row["C_d"],
            L_s=row["L_s"],
            C_b=row["C_b"],
            z_p=row["z_p"],
            C_p=row["C_p"],
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
        cfg: LinkConfig,
        capacitance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the COM shunt capacitance Sdd two-port on cfg.freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.2, Eq. 93A-8.

        Parameters
        ----------
        cfg:
            LinkConfig that defines frequencies in Hz.
        capacitance:
            Shunt capacitance in farads.
        R0:
            Single-ended reference resistance used by Eq. 93A-8. The internal
            differential-mode Sdd Network uses z0 = 2 * R0.
        """
        return cls.shunt_capacitance_at_freqs(cfg.freqs, capacitance, R0)

    @classmethod
    def shunt_capacitance_at_freqs(
        cls,
        freqs: np.ndarray,
        capacitance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the COM shunt capacitance Sdd two-port on an explicit frequency axis.

        This is used for measured-domain S-parameter cascade, where package
        models should be sampled on the channel-under-test frequency grid.
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
        cfg: LinkConfig,
        inductance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the COM series inductance Sdd two-port on cfg.freqs.

        Reference:
        - IEEE 802.3ck Annex 93A.1.2.2a, Eq. 93A-9a.

        Parameters
        ----------
        cfg:
            LinkConfig that defines frequencies in Hz.
        inductance:
            Series inductance in henries.
        R0:
            Single-ended reference resistance used by Eq. 93A-9a. The internal
            differential-mode Sdd Network uses z0 = 2 * R0.
        """
        return cls.series_inductance_at_freqs(cfg.freqs, inductance, R0)

    @classmethod
    def series_inductance_at_freqs(
        cls,
        freqs: np.ndarray,
        inductance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the COM series inductance Sdd two-port on an explicit frequency axis.
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
        cfg: LinkConfig,
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
        Build the COM package transmission-line Sdd two-port on cfg.freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.3, Eq. 93A-9 through Eq. 93A-14.
        - IEEE 802.3ck Annex 93A.1.2.3 clarifies that formula frequency f is
          in GHz.

        Parameters
        ----------
        cfg:
            LinkConfig. cfg.freqs is in Hz.
        R0:
            Single-ended reference resistance.
        zp:
            Package line length in millimeters.
        gamma0, a1, a2, tau:
            COM propagation-coefficient model parameters used with formula
            frequency f in GHz.
        Zc:
            Package differential characteristic impedance.
        """
        return cls.pkg_trans_line_at_freqs(
            cfg.freqs,
            R0,
            zp,
            gamma0=gamma0,
            a1=a1,
            a2=a2,
            tau=tau,
            Zc=Zc,
        )

    @classmethod
    def pkg_trans_line_at_freqs(
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
        Build the COM package transmission-line Sdd two-port on an explicit frequency axis.

        Formula frequency is converted from Hz to GHz before applying Annex 93A.
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
            LinkConfig that defines the frequency grid.
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
            LinkConfig that defines the frequency grid.
        txfir:
            TX FFE tap coefficients.
        num_pre:
            Number of pre-cursor taps before the main cursor.
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
            LinkConfig that defines the frequency grid.
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
            LinkConfig that defines the frequency grid.
        At:
            Rectangular pulse amplitude.
        """
        f = cfg.freqs
        X_f = At * cfg.bt * np.sinc(f * cfg.bt)
        return cls.from_tf(f, X_f, cfg)

    @classmethod
    def transition_time_filter(cls, cfg: LinkConfig, Tr: float) -> 'IEEECOMFilter':
        "Eq. 93A-46"
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
    COM package configuration using spec/Excel-domain units.

    Units:
    - C_d, C_b, C_p: pF
    - L_s: nH
    - z_p, z_p2: millimeters
    - R0, Z_c, Z_c2: ohms
    """
    C_d: float = 0.0      # unit: pF
    L_s: float = 0.0      # unit: nH
    C_b: float = 0.0      # unit: pF
    z_p: float = 0.0      # unit: mm
    C_p: float = 0.0      # unit: pF
    enable: bool = True
    R0: float = 50.0
    Z_c: float = 78.2   # unit: ohm
    z_p2: Optional[float] = None # unit: mm
    Z_c2: float = 78.2  # unit: ohm

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
    Victim and crosstalk channel configuration using spec/Excel-domain units.

    freqs and s4p are populated after Touchstone loading. Excel can directly
    provide the path fields first.
    """
    victim_s4p_path: Optional[str] = None
    next_s4p_paths: Sequence[str] = ()
    fext_s4p_paths: Sequence[str] = ()
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3)    # assume all channels shared
    R0: float = 50.0                                        # assume all channels shared
    gamma_src: complex | np.ndarray = 0.0                   # assume all channels shared
    gamma_load: complex | np.ndarray = 0.0                  # assume all channels shared

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
    COM filter configuration using spec/Excel-domain units.

    This groups parameters used to build H_txffe, H_t, H_r, and H_ctf.
    """
    c_m3: float = 0.0
    c_m2: float = 0.0
    c_m1: float = 0.0
    c_1: float = 0.0
    num_pre: int = 3
    Tr: Optional[float] = None
    fr: Optional[float] = None
    g_DC: Optional[float] = None
    g_DC2: Optional[float] = None
    f_z: Optional[float] = None
    f_LF: Optional[float] = None
    f_p1: Optional[float] = None
    f_p2: Optional[float] = None
    A_v: float = 1.0
    A_fe: float = 1.0
    A_ne: float = 1.0

    # derived attributes
    c_0: float = field(init=False)
    txfir: np.ndarray = field(init=False)

    def __post_init__(self):
        self.c_0 = 1.0 - abs(self.c_m3) - abs(self.c_m2) - abs(self.c_m1) - abs(self.c_1)
        self.txfir = np.r_[self.c_m3, self.c_m2, self.c_m1, self.c_0, self.c_1]

@dataclass(repr=False)
class COMConfig(_PrettyDataclass):
    """Top-level COM configuration grouped by function."""
    link: LinkConfig
    filter: COMFilterConfig
    channel: COMChannelConfig
    pkg: COMPkgConfig

    dfe: COMDFEConfig
    impairment: COMImpairmentConfig
    L: int  # number of signal level

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
class COMStatus(_PrettyDataclass):
    paths: list[COMPath]

    @property
    def victim(self) -> COMPath:
        return self.paths[0]

    @property
    def xtalks(self) -> list[COMPath]:
        return self.paths[1:]

# helpers
def _build_txpkg(freqs: np.ndarray, txpkg_cfg: COMPkgConfig, *, isNext: bool = False) -> IEEECOMsparam:
    "Eq. 93A-15 and 93A-15a, 93A-16b"
    freqs = LinkConfig.validate_freqs(freqs)
    C_d = txpkg_cfg.C_d * 1e-12
    L_s = txpkg_cfg.L_s * 1e-9
    C_b = txpkg_cfg.C_b * 1e-12
    C_p = txpkg_cfg.C_p * 1e-12

    S_d = IEEECOMsparam.shunt_capacitance_at_freqs(freqs, C_d, txpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance_at_freqs(freqs, L_s, txpkg_cfg.R0)
    S_b = IEEECOMsparam.shunt_capacitance_at_freqs(freqs, C_b, txpkg_cfg.R0)
    S_l = IEEECOMsparam.pkg_trans_line_at_freqs(freqs, txpkg_cfg.R0, txpkg_cfg.z_p, Zc=txpkg_cfg.Z_c)
    if (txpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line_at_freqs(freqs, txpkg_cfg.R0, txpkg_cfg.z_p2, Zc=txpkg_cfg.Z_c2)
    S_p = IEEECOMsparam.shunt_capacitance_at_freqs(freqs, C_p, txpkg_cfg.R0)

    # cascade
    S_td = (S_d.cascade_com(S_s)).cascade_com(S_b)
    if (txpkg_cfg.z_p2 is not None):
        S_tp = ((S_td.cascade_com(S_l)).cascade_com(S_l2)).cascade_com(S_p)
    else:
        S_tp = (S_td.cascade_com(S_l)).cascade_com(S_p)
    return S_tp

def _build_rxpkg(freqs: np.ndarray, rxpkg_cfg: COMPkgConfig) -> IEEECOMsparam:
    "Eq. 93A-16 and 93A-16a, 93A-16c"
    freqs = LinkConfig.validate_freqs(freqs)
    C_d = rxpkg_cfg.C_d * 1e-12
    L_s = rxpkg_cfg.L_s * 1e-9
    C_b = rxpkg_cfg.C_b * 1e-12
    C_p = rxpkg_cfg.C_p * 1e-12

    S_p = IEEECOMsparam.shunt_capacitance_at_freqs(freqs, C_p, rxpkg_cfg.R0)
    if (rxpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line_at_freqs(freqs, rxpkg_cfg.R0, rxpkg_cfg.z_p2, Zc=rxpkg_cfg.Z_c2)
    S_l = IEEECOMsparam.pkg_trans_line_at_freqs(freqs, rxpkg_cfg.R0, rxpkg_cfg.z_p, Zc=rxpkg_cfg.Z_c)
    S_b = IEEECOMsparam.shunt_capacitance_at_freqs(freqs, C_b, rxpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance_at_freqs(freqs, L_s, rxpkg_cfg.R0)
    S_d = IEEECOMsparam.shunt_capacitance_at_freqs(freqs, C_d, rxpkg_cfg.R0)
    
    # cascade
    S_rd = (S_b.cascade_com(S_s)).cascade_com(S_d)
    if (rxpkg_cfg.z_p2 is not None):
        S_rp = ((S_p.cascade_com(S_l2)).cascade_com(S_l)).cascade_com(S_rd)
    else:
        S_rp = (S_p.cascade_com(S_l)).cascade_com(S_rd)
    return S_rp

def _build_H_ffe(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    return IEEECOMFilter.tx_ffe(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)

def _build_H_ffe_next(link_cfg: LinkConfig) -> IEEECOMFilter:
    ffe_next = np.array([0,1,0])
    return IEEECOMFilter.tx_ffe(link_cfg, ffe_next, num_pre=1)

def _build_H_t(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    return IEEECOMFilter.transition_time_filter(link_cfg, ft_cfg.Tr)

def _build_H_r(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    return IEEECOMFilter.rx_noise_filter(link_cfg, ft_cfg.fr)

def _build_H_ctf(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:

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

# 93A.1.6 & 93A.1.7
@dataclass
class COMDFEConfig:
    N_b: int
    b_max: float | np.ndarray

    # 802.3ck floating DFE optional
    N_bg: int = 0               # number of DFE floating tap banks
    N_bf: int = 0               # number of DFE floating taps per bank
    N_f: Optional[int]          # DFE maximum span (including floating bank)
    bb_max: Optional[float, np.ndarray] = None
    bb_min: Optional[float, np.ndarray] = None
    b_gmax: Optional[float, np.ndarray] = None
    sigma_tmax: Optional[float] = None
    N_ts: Optional[int] = None

    dfe_mask: np.ndarray = field(init=None)

    def __post_init__(self) -> None:
        "define the indicator mask of dfe coeff" 
        num_fbf_taps = self.N_b if self.N_f is None else self.N_f

        self.dfe_mask = np.zeros(num_fbf_taps)
        self.dfe_mask[:self.N_b] = 1  # fix tap
        if (self.N_ts is not None):
            float_st_idx = self.N_ts - 1     # if N_ts: post 10 => idx = 9
        else:
            float_st_idx = self.N_b          # if N_b: post 1~8 => idx = 8
        num_fbf_float_taps = self.N_bg * self.N_bf
        self.dfe_mask[float_st_idx: float_st_idx+num_fbf_float_taps] = 1

def _find_pos_and_dfe(
    h: np.ndarray, 
    link_cfg: LinkConfig, 
    dfe_cfg: COMDFEConfig
) -> tuple[int, np.ndarray]:
    "Eq. 93A-25, 93A-26"

    M = link_cfg.per_ui
    num_fbf_taps = dfe_cfg.N_b if dfe_cfg.N_f is None else dfe_cfg.N_f

    errs = np.zeros(M)
    for pos in range(M):
        h_dsamp = h[pos::M]
        h_main = h_dsamp.max()
        num_pre = h_dsamp.argmax()
        dfe_post1 = h_dsamp[num_pre+1] / h_main
        errs[pos] = h_dsamp[num_pre-1] - h_dsamp[num_pre+1] + h_dsamp[num_pre]*dfe_post1

    ts = np.argmin(abs(errs))
    h_dsamp = h[ts::M]
    num_pre = h_dsamp.argmax()
    dfe_coeff = h_dsamp[num_pre+1: num_pre+num_fbf_taps+1] / h_dsamp[num_pre]
    dfe_coeff = dfe_coeff * dfe_cfg.dfe_mask

    return ts, dfe_coeff

@dataclass
class COMImpairmentConfig:
    R_LM: float
    SNR_TX: float       # dB
    sigma_RJ: float     # UI
    A_DD: float         # UI
    eta_0: float        # V^2/GHz, one-sided spectral density
    DER_0: float

@dataclass
class COMImpairmentStatus:
    As: float
    sigma_X: float
    sigma_TX: float
    h_ISI: np.ndarray
    sigma_ISI: float
    sigma_J: float
    sigma_XT: float
    sigma_N: float

def _calculate_h_ISI(h_dsamp: np.ndarray, dfe_coeff: np.ndarray) -> np.ndarray:
    num_pre = np.argmax(h_dsamp)
    h_ISI = h_dsamp.copy()
    h_ISI[num_pre] = 0
    h_ISI[num_pre+1: num_pre+len(dfe_coeff)+1] -= dfe_coeff * h_dsamp[num_pre]
    return h_ISI

def _calculate_h_J(h: np.ndarray, ts: int, per_ui: int):
    h_m1 = h[ts-1:: per_ui]
    h_p1 = h[ts+1:: per_ui]
    h_J = (h_p1 - h_m1) / (2/per_ui)
    return h_J

def _find_pos_xtalk(h_XT: np.ndarray, per_ui: int) -> tuple[int, np.ndarray]:
    RSS = np.zeros(per_ui)
    for m in np.arange(per_ui):
        RSS[m] = np.sum(h_XT[m:: per_ui]**2)
    i = np.argmax(RSS)
    h_XT_dsamp = h_XT[i:: per_ui]
    return i, h_XT_dsamp

def _calculate_impairments(h: np.ndarray, ts: int, dfe_coeff: np.ndarray, h_XTs: list[np.ndarray], cfg: COMConfig) -> COMImpairmentStatus:

    L = cfg.L
    h_dsamp = h[ts:: cfg.link.per_ui]
    num_pre = np.argmax(h_dsamp)
    h_main = h_dsamp[num_pre]
    imp = cfg.impairment

    # As
    As = imp.R_LM * h_main / (L - 1)

    # sigma_x
    sigma_X = np.sqrt( (L**2 - 1) / (3 * (L-1)**2) )

    # sigma_TX
    sigma_TX = np.sqrt( h_main**2 * 10*np.log10(imp.SNR_TX/10) )

    # sigma_ISI
    h_ISI = _calculate_h_ISI(h_dsamp, dfe_coeff)
    sigma_ISI = np.sqrt( sigma_X**2 * np.sum(h_ISI**2) )

    # sigma_J
    h_J = _calculate_h_J(h, ts, cfg.link.per_ui)
    sigma_J = np.sqrt( (imp.A_DD**2+imp.sigma_RJ**2) * sigma_X**2 * np.sum(h_J**2) )

    # sigma_XT
    var_XT = 0
    for h_XT in h_XTs:
        i, h_XT_dsamp = _find_pos_xtalk(h_XT, cfg.link.per_ui) 
        var_XT += sigma_X**2 * np.sum(h_XT_dsamp**2)
    sigma_XT = np.sqrt( var_XT )

    # sigma_N
    

@dataclass
class COMPMFConfig:
    pass

#%% conduct search in this class
class COM:
    def __init__(self, cfg: COMConfig):
        self.cfg = cfg

    def run(self) -> COMStatus:
        return COMStatus(paths=self.build_all_paths())

    # LV-1
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

