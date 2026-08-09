from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass, replace
from itertools import product
import json
from pathlib import Path
import sys
import time
from typing import Any, Literal, Optional, Sequence
import numpy as np

try:
    from .link_segment import ContinuousPSD, LinkConfig, LinkSegment, SampledPSD, SampledResponse, SparamModel
    from .pmf_handler import Pmf1D
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serdes_coding.link_segment import ContinuousPSD, LinkConfig, LinkSegment, SampledPSD, SampledResponse, SparamModel
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

    @staticmethod
    def _json_scalar(value: object) -> object:
        if value is None:
            return None
        if isinstance(value, (np.integer,)):
            return int(value)
        if isinstance(value, (np.floating,)):
            return float(value)
        if isinstance(value, (np.bool_,)):
            return bool(value)
        if isinstance(value, complex):
            return {"real": value.real, "imag": value.imag}
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @classmethod
    def _json_value(cls, value: object) -> object:
        if isinstance(value, LinkConfig):
            return {
                "fb": cls._json_scalar(value.fb),
                "per_ui": cls._json_scalar(value.per_ui),
                "target_df": cls._json_scalar(value.target_df),
                "Nfft": cls._json_scalar(value.Nfft),
                "df": cls._json_scalar(value.df),
                "f_nyq": cls._json_scalar(value.f_nyq),
                "dt": cls._json_scalar(value.dt),
                "bt": cls._json_scalar(value.bt),
                "T_max": cls._json_scalar(value.T_max),
            }

        if isinstance(value, np.ndarray):
            return [cls._json_value(item) for item in value.tolist()]

        if isinstance(value, (list, tuple)):
            return [cls._json_value(item) for item in value]

        if isinstance(value, dict):
            return {str(key): cls._json_value(item) for key, item in value.items()}

        if is_dataclass(value):
            return {
                item.name: cls._json_value(getattr(value, item.name))
                for item in fields(value)
                if item.init
            }

        return cls._json_scalar(value)

    @staticmethod
    def _write_json(path: Path, data: dict[str, object]) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

def excel_to_config(excel_path: str) -> COMConfig:
    """Backward-compatible wrapper for COM Excel input."""
    try:
        from .com_excel_io import excel_to_config as _excel_to_config
    except ImportError:
        from serdes_coding.com_excel_io import excel_to_config as _excel_to_config

    return _excel_to_config(excel_path)

def excel_to_search_config(excel_path: str) -> 'COMSearchConfig':
    """Backward-compatible wrapper for COM search Excel input."""
    try:
        from .com_excel_io import excel_to_search_config as _excel_to_search_config
    except ImportError:
        from serdes_coding.com_excel_io import excel_to_search_config as _excel_to_search_config

    return _excel_to_search_config(excel_path)

class IEEECOMsparam(SparamModel):
    """
    IEEE COM-specific S-parameter model builder.

    Class boundary
    --------------
    IEEECOMsparam owns S-parameter networks generated from IEEE COM equations.

    Versioned responsibilities:
    - 93A primitive Sdd models:
      shunt capacitance, series inductance, single package transmission line
    - 93A Sdd cascade:
      Eq. 93A-4 through Eq. 93A-7
    - 178A package/model composition:
      device termination LC ladder, N-stage package transmission line, and
      partial host channel

    Generic S-parameter ingestion, storage, and scikit-rf operations remain in
    SparamModel. This class only adds spec-defined COM construction behavior.
    Single-element 178A package primitives are intentionally not duplicated
    unless their formulas diverge from the 93A primitives.
    """

    @classmethod
    def shunt_capacitance_93A(
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
    def series_inductance_93A(
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
    def pkg_trans_line_93A(
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

    @staticmethod
    def _cascade_sdd_93A(sx: np.ndarray, sy: np.ndarray) -> np.ndarray:
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

    def cascade_com_93A(self, other: SparamModel) -> 'IEEECOMsparam':
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

        cascaded_sdd = self._cascade_sdd_93A(left.sdd, right.sdd)
        return type(self).from_sdd_array(common_freqs, cascaded_sdd, z0=left.network.z0)

    @classmethod
    def device_termination_178A(
        cls,
        freqs: np.ndarray,
        L_seq: Sequence[float] | np.ndarray,
        C_seq: Sequence[float] | np.ndarray,
        bump_capacitance: float,
        R0: float = 50.0,
    ) -> 'IEEECOMsparam':
        """
        Build the 178A device termination S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-7.

        Model convention
        ----------------
        The model is represented as an N-stage LC ladder plus the package bump
        capacitance. The L/C vectors describe per-stage device termination
        elements. The ladder is cascaded in reverse order so the returned
        two-port follows the physical order expected by the package/channel
        cascade.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        L_seq:
            Series-inductance vector in H. Must be a 1-D vector.
        C_seq:
            Shunt-capacitance vector in F. Must be a 1-D vector with the same
            length as L_seq.
        bump_capacitance:
            Bump/interface shunt capacitance in F.
        R0:
            Single-ended reference resistance in ohm.

        Returns
        -------
        IEEECOMsparam
            Cascaded N-stage LC ladder as a differential 2-port Sdd model.
        """
        def _validate_LC_seq(L_seq,C_seq) -> tuple[np.ndarray, np.ndarray]:
            L = np.asarray(L_seq, dtype=float)
            C = np.asarray(C_seq, dtype=float)

            if L.ndim != 1 or C.ndim != 1:
                raise ValueError("L and C must be 1-D arrays.")

            if len(L) != len(C):
                raise ValueError(
                    f"L and C must have the same length. Got len(L)={len(L)}, len(C)={len(C)}."
                )

            if len(L) == 0:
                raise ValueError("L and C must contain at least one stage.")

            if np.any(L < 0.0) or np.any(C < 0.0):
                raise ValueError("L and C values must be non-negative.")

            return L, C
        L, C = _validate_LC_seq(L_seq, C_seq)

        # initialized with C_b
        S_d = cls.shunt_capacitance_93A(freqs, bump_capacitance, R0)

        # build LC ladder in reverse order
        L_rev = L[::-1]
        C_rev = C[::-1]
        for l, c in zip(L_rev, C_rev):
            S_C_temp = cls.shunt_capacitance_93A(freqs, c, R0)
            S_L_temp = cls.series_inductance_93A(freqs, l, R0)
            S_temp = S_C_temp.cascade_com_93A(S_L_temp)
            S_d = S_temp.cascade_com_93A(S_d)
            
        return S_d

    @classmethod
    def device_package_178A(
        cls,
        freqs: np.ndarray,
        R0: float,
        package_capacitance: float,
        zp_seq: Sequence[float] | np.ndarray,
        *,
        Zc_seq: Sequence[float] | np.ndarray,
        gamma0: float = 0.0,
        a1: float = float(1.734e-3),
        a2: float = float(1.455e-4),
        tau: float = float(6.141e-3),
    ) -> 'IEEECOMsparam':
        """
        Build the 178A device package S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-9.

        Model convention
        ----------------
        The model is represented as a package-side shunt capacitance followed
        by N transmission-line stages. Based on the IEEE 802.3dj COM adhoc
        config/code convention, zp_seq and Zc_seq are stage-specific, while
        gamma0/a1/a2/tau are package-level propagation parameters shared by
        all stages. If a future config needs per-stage propagation coefficients,
        this interface should be generalized explicitly.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance in ohm.
        package_capacitance:
            Package-to-board shunt capacitance in F.
        zp_seq:
            Vector of package TL lengths in mm.
        Zc_seq:
            Vector of differential characteristic impedances in ohm. Must align
            with zp_seq.
        gamma0, a1, a2, tau:
            Package-level propagation-coefficient parameters shared by all TL
            stages. The underlying 93A primitive uses GHz internally.

        Returns
        -------
        IEEECOMsparam
            Cascaded N-stage package TL as a differential 2-port Sdd model.
        """
        def _validate_zp_Zc_seq(zp_seq, Zc_seq) -> tuple[np.ndarray, np.ndarray]:
            zp_seq = np.asarray(zp_seq, dtype=float)
            Zc_seq = np.asarray(Zc_seq, dtype=float)

            if zp_seq.ndim != 1 or Zc_seq.ndim != 1:
                raise ValueError("zp and Zc must be 1-D arrays.")

            if len(zp_seq) != len(Zc_seq):
                raise ValueError(
                    f"zp and Zc must have the same length. Got len(zp_seq)={len(zp_seq)}, len(Zc_seq)={len(Zc_seq)}."
                )

            if len(zp_seq) == 0:
                raise ValueError("zp and Zc must contain at least one stage.")

            if np.any(zp_seq < 0.0) or np.any(Zc_seq < 0.0):
                raise ValueError("zp and Zc values must be non-negative.")

            return zp_seq, Zc_seq
        zp, Zc = _validate_zp_Zc_seq(zp_seq, Zc_seq)

        # initialized with C_p
        S_p = cls.shunt_capacitance_93A(freqs, package_capacitance, R0)

        # build N-stage package transmission lines in reverse order
        zp_rev = zp[::-1]
        Zc_rev = Zc[::-1]
        for z1, z2 in zip(zp_rev, Zc_rev):
            S_temp = cls.pkg_trans_line_93A(freqs, R0, z1, Zc=z2, gamma0=gamma0, a1=a1, a2=a2, tau=tau)
            S_p = S_temp.cascade_com_93A(S_p)

        return S_p

    @classmethod
    def partial_host_channel_178A(
        cls,
        freqs: np.ndarray,
        R0: float,
        C0: float,
        C1: float,
        zp: float,
        *,
        Zc: float = 78.2,
        gamma0: float = 0.0,
        a1: float = float(1.734e-3),
        a2: float = float(1.455e-4),
        tau: float = float(6.141e-3),
    ) -> 'IEEECOMsparam':
        """
        Build the 178A partial host channel S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-10.

        Model convention
        ----------------
        The partial host channel is represented as:
            C0 shunt capacitance -> host TL segment -> C1 shunt capacitance.

        This helper builds the synthetic partial-host block itself; it does not
        consume an external measured host S-parameter model.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance in ohm.
        C0:
            Near-device shunt capacitance in F.
        C1:
            Connector-side shunt capacitance in F.
        zp:
            Partial-host TL length in mm.
        Zc:
            Partial-host differential characteristic impedance in ohm.
        gamma0, a1, a2, tau:
            Propagation-coefficient parameters for the partial-host TL.

        Returns
        -------
        IEEECOMsparam
            Synthetic partial host channel as a differential 2-port Sdd model.
        """
        S_0 = cls.shunt_capacitance_93A(freqs, C0, R0)
        S_h = cls.pkg_trans_line_93A(freqs, R0, zp, Zc=Zc, gamma0=gamma0, a1=a1, a2=a2, tau=tau)
        S_1 = cls.shunt_capacitance_93A(freqs, C1, R0)
        return (S_0.cascade_com_93A(S_h)).cascade_com_93A(S_1)

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
    def rx_noise_filter_93A(cls, cfg: LinkConfig, fr: float) -> 'IEEECOMFilter':
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
    def tx_ffe_93A(cls, cfg: LinkConfig, txfir: np.ndarray, num_pre: int) -> 'IEEECOMFilter':
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
    def rx_equalizer_93A(
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
    def rx_equalizer_178A(
        cls,
        cfg: LinkConfig,
        g_1: float,
        g_2: float,
        f_z1: float,
        f_z2: float,
        f_p1: float,
        f_p2: float,
        f_p3: float,
    ) -> 'IEEECOMFilter':
        """
        Build the 178A receiver equalizer transfer function.

        The IO follows the 178A CTF shape with two independent zeros and
        three independent poles.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        g_1, g_2:
            178A CTF gain terms in dB.
        f_z1, f_z2:
            178A CTF zero frequencies in Hz.
        f_p1, f_p2, f_p3:
            178A CTF pole frequencies in Hz.
        """
        f = cfg.freqs
        denom = (1 + 1j * f / f_p1) * (1 + 1j * f / f_p2) * (1 + 1j * f / f_p3)
        H_ctf = (10**(g_1 / 20) + 1j * f / f_z1) * (10**(g_2 / 20) + 1j * f / f_z2) / denom
        return cls.from_tf(f, H_ctf, cfg)

    @classmethod
    def rect_pulse_93A(cls, cfg: LinkConfig, At: float) -> 'IEEECOMFilter':
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
    def transition_time_filter_93A(cls, cfg: LinkConfig, Tr: float) -> 'IEEECOMFilter':
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
    not own channel construction, DFE selection, or imp statistics.
    """
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
    txpkg_victim: COMPkgConfig        # unit contract: F/H/mm/ohm victim TX package parameters
    txpkg_fext: COMPkgConfig          # unit contract: F/H/mm/ohm FEXT aggressor TX package parameters
    txpkg_next: COMPkgConfig          # unit contract: F/H/mm/ohm NEXT aggressor TX package parameters
    rxpkg: COMPkgConfig               # unit contract: F/H/mm/ohm shared RX package parameters

    dfe: COMDFEConfig                 # unit contract: tap counts and normalized coefficients
    imp: COMImpairmentConfig          # unit contract: voltage/noise/jitter settings
    L: int                            # unit: count, number of signal levels
    DER_0: float                    # unit: dimensionless, target detector error ratio
    pmf: COMPMFConfig = field(default_factory=COMPMFConfig) # unit contract: PMF amplitude grid and numerical controls

    def to_export_dict(self) -> dict[str, object]:
        """
        Return a JSON-friendly COMConfig snapshot.

        The snapshot records only configuration and derived configuration
        metadata. It does not include COMStatus run results.
        """
        return {
            "type": type(self).__name__,
            "config": self._json_value(self),
            "derived": {
                "link": self._json_value(self.link),
                "channel_measured_grid": self._json_value(self.channel.measured_grid_summary()),
                "channel_aligned_grid": self._json_value(self.channel.aligned_grid_summary()),
                "txfir": self._json_value(self.filter.txfir),
                "c_0": self._json_scalar(self.filter.c_0),
            },
        }

    def export(self, save_path: str) -> dict[str, str]:
        """
        Export this COMConfig as a human-readable summary.

        Parameters
        ----------
        save_path:
            Output directory. The method writes ``config_summary.txt``.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        txt_path = out_dir / "config_summary.txt"

        txt_path.write_text(str(self), encoding="utf-8")

        return {
            "config_summary_txt": str(txt_path),
        }

@dataclass(repr=False)
class COMSearchConfig(_PrettyDataclass):
    """
    Search-space configuration for 93A.1.6 variable equalizer parameters.

    None means "use the scalar value already stored in COMConfig.filter".
    Values are combined by Cartesian product in COM_93A.run(search=...).
    """
    c_m2_values: Optional[Sequence[float]] = None # unit: dimensionless, TX FFE tap c(-2)
    c_m1_values: Optional[Sequence[float]] = None # unit: dimensionless, TX FFE tap c(-1)
    c_1_values: Optional[Sequence[float]] = None  # unit: dimensionless, TX FFE tap c(1)
    g_DC_values: Optional[Sequence[float]] = None # unit: dB, CTLE DC gain
    g_DC2_values: Optional[Sequence[float]] = None # unit: dB, CTLE second DC gain
    keep_top_n: int = 10              # unit: count, number of successful summary rows to retain
    keep_all_rows: bool = False       # if True, retain every candidate summary row
    continue_on_error: bool = False   # if True, failed candidates become error rows

    def __post_init__(self) -> None:
        self.keep_top_n = int(self.keep_top_n)
        if self.keep_top_n <= 0:
            raise ValueError("COMSearchConfig.keep_top_n must be positive.")

    @staticmethod
    def _values_or_default(
        values: Optional[Sequence[float]],
        default: Optional[float],
        name: str,
    ) -> np.ndarray:
        if values is None:
            if default is None:
                raise ValueError(f"{name} has no search values and no COMConfig.filter default value.")
            values = (default,)

        arr = np.asarray(values, dtype=float)
        if arr.ndim != 1 or len(arr) == 0:
            raise ValueError(f"{name} search values must be a non-empty 1D sequence.")
        if not np.all(np.isfinite(arr)):
            raise ValueError(f"{name} search values must be finite.")
        return arr

    def candidates(self, ft_cfg: COMFilterConfig) -> list['COMSearchCandidate']:
        c_m2 = self._values_or_default(self.c_m2_values, ft_cfg.c_m2, "c_m2")
        c_m1 = self._values_or_default(self.c_m1_values, ft_cfg.c_m1, "c_m1")
        c_1 = self._values_or_default(self.c_1_values, ft_cfg.c_1, "c_1")
        g_DC = self._values_or_default(self.g_DC_values, ft_cfg.g_DC, "g_DC")
        g_DC2 = self._values_or_default(self.g_DC2_values, ft_cfg.g_DC2, "g_DC2")

        return [
            COMSearchCandidate(
                c_m2=float(items[0]),
                c_m1=float(items[1]),
                c_1=float(items[2]),
                g_DC=float(items[3]),
                g_DC2=float(items[4]),
            )
            for items in product(c_m2, c_m1, c_1, g_DC, g_DC2)
        ]

@dataclass(repr=False)
class COMSearchCandidate(_PrettyDataclass):
    """One concrete 93A.1.6 variable equalizer candidate."""
    c_m2: float                       # unit: dimensionless, TX FFE tap c(-2)
    c_m1: float                       # unit: dimensionless, TX FFE tap c(-1)
    c_1: float                        # unit: dimensionless, TX FFE tap c(1)
    g_DC: float                       # unit: dB, CTLE DC gain
    g_DC2: float                      # unit: dB, CTLE second DC gain

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
class COMImpairmentStatus_93A(_PrettyDataclass):
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
    imp: Optional['COMImpairmentStatus_93A'] = None
    pmf: Optional['COMPMFStatus'] = None
    FOM: Optional[float] = None        # unit: dB, 93A.1.6 figure of merit

    @property
    def victim(self) -> COMPath:
        return self.paths[0]

    @property
    def xtalks(self) -> list[COMPath]:
        return self.paths[1:]

    @staticmethod
    def _array_meta(arrays: dict[str, np.ndarray], key: str, value: np.ndarray) -> dict[str, object]:
        arr = np.asarray(value)
        arrays[key] = arr
        return {
            "array_key": key,
            "shape": list(arr.shape),
            "dtype": str(arr.dtype),
        }

    @classmethod
    def _sparam_export(
        cls,
        name: str,
        model: SparamModel,
        arrays: dict[str, np.ndarray],
    ) -> dict[str, object]:
        return {
            "type": type(model).__name__,
            "freqs": cls._array_meta(arrays, f"{name}.freqs", model.freqs),
            "sdd": cls._array_meta(arrays, f"{name}.sdd", model.sdd),
        }

    @classmethod
    def _segment_export(
        cls,
        name: str,
        segment: LinkSegment,
        arrays: dict[str, np.ndarray],
    ) -> dict[str, object]:
        return {
            "type": type(segment).__name__,
            "cfg": {
                "fb": segment.cfg.fb,
                "per_ui": segment.cfg.per_ui,
                "target_df": segment.cfg.target_df,
                "Nfft": segment.cfg.Nfft,
                "df": segment.cfg.df,
                "f_nyq": segment.cfg.f_nyq,
                "dt": segment.cfg.dt,
                "T_max": segment.cfg.T_max,
            },
            "freqs": cls._array_meta(arrays, f"{name}.freqs", segment.freqs),
            "times": cls._array_meta(arrays, f"{name}.times", segment.times),
            "tf": cls._array_meta(arrays, f"{name}.tf", segment.tf),
            "raw_ir": cls._array_meta(arrays, f"{name}.raw_ir", segment.raw_ir),
            "aligned_ir": cls._array_meta(arrays, f"{name}.aligned_ir", segment.aligned_ir),
            "sr": cls._array_meta(arrays, f"{name}.sr", segment.sr),
            "sbr": cls._array_meta(arrays, f"{name}.sbr", segment.sbr),
        }

    @classmethod
    def _pmf_export(
        cls,
        name: str,
        pmf: Optional[Pmf1D],
        arrays: dict[str, np.ndarray],
    ) -> Optional[dict[str, object]]:
        if pmf is None:
            return None
        return {
            "type": type(pmf).__name__,
            "dx": pmf.dx,
            "st_idx": pmf.st_idx,
            "unit": pmf.unit,
            "name": pmf.name,
            "pmf": cls._array_meta(arrays, f"{name}.pmf", pmf.pmf),
            "x": cls._array_meta(arrays, f"{name}.x", pmf.x),
            "cdf": cls._array_meta(arrays, f"{name}.cdf", pmf.cdf),
        }

    def plot_path_pulses(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        """
        Plot all path pulse impulse responses on one aligned UI axis.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``path_pulses.png``.
        xlim_ui:
            Optional x-axis limits in UI after each path main cursor is shifted
            to 0 UI.
        """
        output_file = COMReport._plot_save_path(save_path, "path_pulses.png")
        fig, ax = COMReport._subplots(output_file)
        for idx, path in enumerate(self.paths):
            ir = path.pulse.ir
            x = path.pulse.cfg.times_ui - path.pulse.cfg.times_ui[int(np.argmax(np.abs(ir)))]
            ax.plot(x, ir, label=COMReport._path_display_label(idx, path))

        ax.set_title("Path Pulse Responses")
        ax.set_xlabel("Time (UI)")
        ax.set_ylabel("h(t)")
        if xlim_ui is not None:
            ax.set_xlim(*xlim_ui)
        ax.grid(True)
        ax.legend()
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_path_sbr(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        normalize_main_cursor: bool = True,
    ) -> Any:
        """
        Plot all path single-bit responses on one aligned UI axis.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``path_sbr.png``.
        xlim_ui:
            Optional x-axis limits in UI after each SBR main cursor is shifted
            to 0 UI.
        normalize_main_cursor:
            If True, normalize each SBR by its own main cursor magnitude.
        """
        output_file = COMReport._plot_save_path(save_path, "path_sbr.png")
        fig, ax = COMReport._subplots(output_file)
        for idx, path in enumerate(self.paths):
            sbr = path.pulse.sbr.copy()
            main = float(np.max(np.abs(sbr)))
            if normalize_main_cursor and main > 0:
                sbr = sbr / main
            x = path.pulse.cfg.times_ui - path.pulse.cfg.times_ui[int(np.argmax(np.abs(sbr)))]
            ax.plot(x, sbr, label=COMReport._path_display_label(idx, path))

        ax.set_title("Path Single-Bit Responses")
        ax.set_xlabel("Time (UI)")
        ax.set_ylabel("SBR / main" if normalize_main_cursor else "SBR")
        if xlim_ui is not None:
            ax.set_xlim(*xlim_ui)
        ax.grid(True)
        ax.legend()
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_path_S_all_IL(
        self,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
    ) -> Any:
        """
        Plot augmented signal-path insertion loss for all paths.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``path_S_all_IL.png``.
        xlim:
            Optional frequency limits in Hz.
        """
        output_file = COMReport._plot_save_path(save_path, "path_S_all_IL.png")
        fig, ax = COMReport._subplots(output_file)
        if xlim is None:
            xlim = (0.0, float(self.victim.pulse.cfg.fb))
        for idx, path in enumerate(self.paths):
            path.S_all.plot_IL(
                ax=ax,
                xlim=xlim,
                label=COMReport._path_display_label(idx, path),
                auto_ylim=False,
            )

        ax.set_title("Augmented Signal Path IL, S_all")
        COMReport._apply_auto_ylim_from_lines(ax, xlim)
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_path_H21_tf(
        self,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
    ) -> Any:
        """
        Plot terminated voltage transfer function H21 for all paths.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``path_H21_tf.png``.
        xlim:
            Optional frequency limits in Hz. If None, LinkSegment uses 0 to fb.
        ylim:
            Optional y-axis limits in dB. If None, LinkSegment chooses y-limits
            from the plotted in-band samples and ignores numerical floor values.
        """
        output_file = COMReport._plot_save_path(save_path, "path_H21_tf.png")
        fig, ax = COMReport._subplots(output_file)
        if xlim is None:
            xlim = (0.0, float(self.victim.pulse.cfg.fb))
        for idx, path in enumerate(self.paths):
            path.H_21.plot_tf(
                ax=ax,
                xlim=xlim,
                ylim=ylim,
                auto_ylim=False,
                label=COMReport._path_display_label(idx, path),
            )

        ax.set_title("Voltage Transfer Function H21")
        if ylim is None:
            COMReport._apply_auto_ylim_from_lines(ax, xlim)
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_dfe_summary(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        """
        Plot DFE coefficients and residual ISI samples.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``dfe_summary.png``.
        xlim_ui:
            Optional residual-ISI x-axis limits in UI, with the main cursor at 0.
        """
        if self.dfe is None:
            raise ValueError("COMStatus.dfe is None; run DFE calculation first.")

        output_file = COMReport._plot_save_path(save_path, "dfe_summary.png")
        fig, axes = COMReport._subplots(output_file, 2, 1, figsize=(7, 6))
        tap_idx = np.arange(1, len(self.dfe.dfe_coeff) + 1)
        axes[0].bar(tap_idx, self.dfe.dfe_coeff)
        axes[0].set_title("DFE Coefficients")
        axes[0].set_xlabel("Tap index")
        axes[0].set_ylabel("Coefficient")
        axes[0].set_xlim(0.5, max(1.5, len(self.dfe.dfe_coeff) + 0.5))
        axes[0].grid(True)

        per_ui = self.victim.pulse.cfg.per_ui
        num_pre = (self.dfe.ts - self.dfe.pos) // per_ui
        isi_ui = np.arange(len(self.dfe.h_ISI), dtype=float) - float(num_pre)
        axes[1].bar(isi_ui, self.dfe.h_ISI, width=0.8)
        axes[1].set_title("Residual ISI Samples")
        axes[1].set_xlabel("Discrete time (UI, main cursor = 0)")
        axes[1].set_ylabel("Amplitude (V)")
        if xlim_ui is not None:
            axes[1].set_xlim(*xlim_ui)
        axes[1].grid(True)

        COMReport._finish_figure(fig, output_file)
        return axes

    def plot_imp_summary(self, save_path: str = "") -> Any:
        """
        Plot imp RMS components as a bar chart.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``imp_summary.png``.
        """
        if self.imp is None:
            raise ValueError("COMStatus.imp is None; run imp calculation first.")

        labels = ["TX", "ISI", "J", "XT", "N"]
        values = [
            self.imp.sigma_TX,
            self.imp.sigma_ISI,
            self.imp.sigma_J,
            self.imp.sigma_XT,
            self.imp.sigma_N,
        ]

        output_file = COMReport._plot_save_path(save_path, "imp_summary.png")
        fig, ax = COMReport._subplots(output_file)
        ax.bar(labels, values)
        ax.set_title("Imp RMS Breakdown")
        ax.set_ylabel("RMS amplitude (V)")
        ax.grid(True, axis="y")
        text = f"As={self.imp.As:.4e} V"
        if self.FOM is not None:
            text += f"\nFOM={self.FOM:.2f} dB"
        ax.text(0.98, 0.95, text, ha="right", va="top", transform=ax.transAxes)

        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_pmf_summary(self, save_path: str = "") -> Any:
        """
        Plot PMF components and the final combined CDF.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``pmf_summary.png``.
        """
        if self.pmf is None:
            raise ValueError("COMStatus.pmf is None; run PMF calculation first.")

        components = [
            ("ISI", self.pmf.p_ISI),
            ("G", self.pmf.p_G),
            ("DD", self.pmf.p_DD),
            ("XT", self.pmf.p_XT),
            ("combined", self.pmf.p_combined),
        ]

        output_file = COMReport._plot_save_path(save_path, "pmf_summary.png")
        fig, axes = COMReport._subplots(output_file, 2, 1, figsize=(7, 6))
        for label, p in components:
            if p is not None:
                axes[0].plot(p.x, p.pmf, label=label)
        axes[0].set_title("PMF Components")
        axes[0].set_xlabel("Amplitude (V)")
        axes[0].set_ylabel("Probability mass")
        axes[0].grid(True)
        axes[0].legend()

        if self.pmf.p_combined is not None:
            p = self.pmf.p_combined
            axes[1].plot(p.x, p.cdf, label="combined CDF")
            if self.pmf.y0 is not None:
                axes[1].axvline(self.pmf.y0, linestyle="--", color="tab:red", label=f"y0={self.pmf.y0:.3e} V")
            axes[1].legend()
        axes[1].set_title("Combined CDF")
        axes[1].set_xlabel("Amplitude (V)")
        axes[1].set_ylabel("CDF")
        axes[1].grid(True)

        title = []
        if self.pmf.COM is not None:
            title.append(f"COM={self.pmf.COM:.2f} dB")
        if self.pmf.A_ni is not None:
            title.append(f"A_ni={self.pmf.A_ni:.3e} V")
        if title:
            fig.suptitle(", ".join(title))

        COMReport._finish_figure(fig, output_file)
        return axes

    def plot_summary(self, save_path: str = "") -> dict[str, Any]:
        """
        Plot the standard COM single-run report set.

        Parameters
        ----------
        save_path:
            Optional output directory. If empty, figures are shown interactively.
            If provided, fixed filenames are written under this directory.
        """
        outputs: dict[str, Any] = {}
        outputs["path_pulses"] = self.plot_path_pulses(save_path)
        outputs["path_S_all_IL"] = self.plot_path_S_all_IL(save_path)
        outputs["path_H21_tf"] = self.plot_path_H21_tf(save_path)
        if self.dfe is not None:
            outputs["dfe_summary"] = self.plot_dfe_summary(save_path)
        if self.imp is not None:
            outputs["imp_summary"] = self.plot_imp_summary(save_path)
        if self.pmf is not None:
            outputs["pmf_summary"] = self.plot_pmf_summary(save_path)
        return outputs

    def to_report_summary_text(self) -> str:
        """Return a concise human-readable single-run summary."""
        lines: list[str] = []
        lines.append("COM Single-Run Report Summary")
        lines.append("=" * 29)
        lines.append("")
        lines.append(f"FOM_dB: {self.FOM:.6g}" if self.FOM is not None else "FOM_dB: None")
        if self.pmf is not None:
            lines.append(f"COM_dB: {self.pmf.COM:.6g}" if self.pmf.COM is not None else "COM_dB: None")
            lines.append(f"A_ni_V: {self.pmf.A_ni:.6e}" if self.pmf.A_ni is not None else "A_ni_V: None")
            lines.append(f"y0_V: {self.pmf.y0:.6e}" if self.pmf.y0 is not None else "y0_V: None")
            lines.append(f"pmf_dy_V: {self.pmf.dy:.6e}")
            lines.append(f"pmf_tap_abs_th_V: {self.pmf.tap_abs_th:.6e}")
        lines.append("")

        lines.append("Paths")
        lines.append("-" * 5)
        for idx, path in enumerate(self.paths):
            h21_dc = float(np.abs(path.H_21.tf[0])) if len(path.H_21.tf) else float("nan")
            pulse_peak = float(np.max(np.abs(path.pulse.ir))) if len(path.pulse.ir) else float("nan")
            lines.append(
                f"{idx}: kind={path.kind}, "
                f"H21_dc={h21_dc:.6e}, "
                f"pulse_peak={pulse_peak:.6e}"
            )
        lines.append("")

        if self.dfe is not None:
            lines.append("DFE")
            lines.append("---")
            lines.append(f"ts: {self.dfe.ts}")
            lines.append(f"pos: {self.dfe.pos}")
            lines.append(f"num_dfe_taps: {len(self.dfe.dfe_coeff)}")
            lines.append(f"dfe_coeff: {np.array2string(self.dfe.dfe_coeff, precision=6, separator=', ')}")
            lines.append(f"h_ISI_len: {len(self.dfe.h_ISI)}")
            lines.append("")

        if self.imp is not None:
            lines.append("Impairment RMS")
            lines.append("--------------")
            lines.append(f"As_V: {self.imp.As:.6e}")
            lines.append(f"sigma_X: {self.imp.sigma_X:.6e}")
            lines.append(f"sigma_TX_V: {self.imp.sigma_TX:.6e}")
            lines.append(f"sigma_ISI_V: {self.imp.sigma_ISI:.6e}")
            lines.append(f"sigma_J_V: {self.imp.sigma_J:.6e}")
            lines.append(f"sigma_XT_V: {self.imp.sigma_XT:.6e}")
            lines.append(f"sigma_N_V: {self.imp.sigma_N:.6e}")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"

    def export_report_summary(self, save_path: str) -> dict[str, str]:
        """
        Export a concise human-readable single-run report summary.

        Parameters
        ----------
        save_path:
            Output directory. The method writes ``report_summary.txt``.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / "report_summary.txt"
        path.write_text(self.to_report_summary_text(), encoding="utf-8")
        return {"report_summary_txt": str(path)}

    def export(self, save_path: str, *, include_plots: bool = False) -> dict[str, str]:
        """
        Export this single-run COMStatus numeric arrays.

        Parameters
        ----------
        save_path:
            Output directory. The method writes ``arrays.npz`` under this
            directory.
        include_plots:
            Backward-compatible compact plot option. New single-run report
            figures should use COMReport so all plots share one folder tree.

        Returns
        -------
        dict
            Paths of generated artifacts.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        arrays: dict[str, np.ndarray] = {}

        paths_meta = []
        for idx, path in enumerate(self.paths):
            prefix = f"paths.{idx}"
            paths_meta.append({
                "idx": idx,
                "kind": path.kind,
                "S_tx": self._sparam_export(f"{prefix}.S_tx", path.S_tx, arrays),
                "S_ch": self._sparam_export(f"{prefix}.S_ch", path.S_ch, arrays),
                "S_rx": self._sparam_export(f"{prefix}.S_rx", path.S_rx, arrays),
                "S_all": self._sparam_export(f"{prefix}.S_all", path.S_all, arrays),
                "H_ffe": self._segment_export(f"{prefix}.H_ffe", path.H_ffe, arrays),
                "H_t": self._segment_export(f"{prefix}.H_t", path.H_t, arrays),
                "H_21": self._segment_export(f"{prefix}.H_21", path.H_21, arrays),
                "H_r": self._segment_export(f"{prefix}.H_r", path.H_r, arrays),
                "H_ctf": self._segment_export(f"{prefix}.H_ctf", path.H_ctf, arrays),
                "H_all": self._segment_export(f"{prefix}.H_all", path.H_all, arrays),
                "X": self._segment_export(f"{prefix}.X", path.X, arrays),
                "pulse": self._segment_export(f"{prefix}.pulse", path.pulse, arrays),
            })

        summary: dict[str, object] = {
            "type": type(self).__name__,
            "FOM": self._json_scalar(self.FOM),
            "paths": paths_meta,
            "dfe": None,
            "imp": None,
            "pmf": None,
        }

        if self.dfe is not None:
            summary["dfe"] = {
                "ts": self.dfe.ts,
                "pos": self.dfe.pos,
                "dfe_coeff": self._array_meta(arrays, "dfe.dfe_coeff", self.dfe.dfe_coeff),
                "h_ISI": self._array_meta(arrays, "dfe.h_ISI", self.dfe.h_ISI),
            }

        if self.imp is not None:
            summary["imp"] = {
                "As": self.imp.As,
                "sigma_X": self.imp.sigma_X,
                "sigma_TX": self.imp.sigma_TX,
                "sigma_ISI": self.imp.sigma_ISI,
                "sigma_J": self.imp.sigma_J,
                "sigma_XT": self.imp.sigma_XT,
                "sigma_N": self.imp.sigma_N,
                "h_ISI": self._array_meta(arrays, "imp.h_ISI", self.imp.h_ISI),
                "h_J": self._array_meta(arrays, "imp.h_J", self.imp.h_J),
                "h_XTs_dsamp": [
                    self._array_meta(arrays, f"imp.h_XTs_dsamp.{idx}", h)
                    for idx, h in enumerate(self.imp.h_XTs_dsamp)
                ],
            }

        if self.pmf is not None:
            summary["pmf"] = {
                "dy": self.pmf.dy,
                "tap_abs_th": self.pmf.tap_abs_th,
                "y0": self._json_scalar(self.pmf.y0),
                "A_ni": self._json_scalar(self.pmf.A_ni),
                "COM": self._json_scalar(self.pmf.COM),
                "p_ISI": self._pmf_export("pmf.p_ISI", self.pmf.p_ISI, arrays),
                "p_G": self._pmf_export("pmf.p_G", self.pmf.p_G, arrays),
                "p_DD": self._pmf_export("pmf.p_DD", self.pmf.p_DD, arrays),
                "p_XT": self._pmf_export("pmf.p_XT", self.pmf.p_XT, arrays),
                "p_combined": self._pmf_export("pmf.p_combined", self.pmf.p_combined, arrays),
            }

        arrays_path = out_dir / "arrays.npz"
        np.savez_compressed(arrays_path, **arrays)

        outputs = {
            "arrays": str(arrays_path),
        }
        if include_plots:
            plot_dir = out_dir / "plots"
            self.plot_summary(str(plot_dir))
            outputs["plots"] = str(plot_dir)
        return outputs

@dataclass(repr=False)
class COMSearchRow(_PrettyDataclass):
    """Lightweight summary of one COM search candidate."""
    idx: int                          # unit: count, candidate index
    candidate: COMSearchCandidate
    FOM: float                        # unit: dB, 93A.1.6 figure of merit
    As: Optional[float] = None         # unit: V
    sigma_ISI: Optional[float] = None  # unit: V
    sigma_J: Optional[float] = None    # unit: V
    sigma_XT: Optional[float] = None   # unit: V
    sigma_N: Optional[float] = None    # unit: V
    sigma_TX: Optional[float] = None   # unit: V
    ts: Optional[int] = None           # unit: sample index
    pos: Optional[int] = None          # unit: sample phase
    status: Literal["ok", "error"] = "ok"
    error: Optional[str] = None

@dataclass(repr=False)
class COMSearchStatus(_PrettyDataclass):
    """
    Search result for COM_93A.run(search=...).

    Only the FOM winner is recomputed with the full PMF/COM pipeline. The rows
    field stores lightweight candidate summaries, not full COMStatus objects.
    """
    best: COMStatus
    best_row: COMSearchRow
    rows: list[COMSearchRow]
    num_candidates: int
    num_success: int
    num_error: int

    @property
    def COM(self) -> Optional[float]:
        return None if self.best.pmf is None else self.best.pmf.COM

    def plot_fom_trace(self, save_path: str = "") -> Any:
        """
        Plot FOM versus retained candidate index.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``search_fom_trace.png``.
        """
        ok_rows = [row for row in self.rows if row.status == "ok"]
        if len(ok_rows) == 0:
            raise ValueError("COMSearchStatus.rows contains no successful rows to plot.")

        output_file = COMReport._plot_save_path(save_path, "search_fom_trace.png")
        fig, ax = COMReport._subplots(output_file)
        ax.plot([row.idx for row in ok_rows], [row.FOM for row in ok_rows], marker="o", linewidth=1.0)
        ax.axhline(self.best_row.FOM, linestyle="--", color="tab:red", label=f"best FOM={self.best_row.FOM:.2f} dB")
        ax.set_title("Search FOM Trace")
        ax.set_xlabel("Candidate index")
        ax.set_ylabel("FOM (dB)")
        ax.grid(True)
        ax.legend()
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_top_candidates(self, save_path: str = "", top_n: int = 10) -> Any:
        """
        Plot top-N retained candidates sorted by FOM.

        Parameters
        ----------
        save_path:
            Optional file path or directory. Directory mode writes
            ``search_top_candidates.png``.
        top_n:
            Number of successful candidates to show.
        """
        ok_rows = [row for row in self.rows if row.status == "ok"]
        if len(ok_rows) == 0:
            raise ValueError("COMSearchStatus.rows contains no successful rows to plot.")

        top_n = int(top_n)
        if top_n <= 0:
            raise ValueError("top_n must be positive.")

        rows = sorted(ok_rows, key=lambda row: row.FOM, reverse=True)[:top_n]
        labels = [f"{row.idx}\n({row.candidate.g_DC:.1f},{row.candidate.g_DC2:.1f})" for row in rows]
        values = [row.FOM for row in rows]

        output_file = COMReport._plot_save_path(save_path, "search_top_candidates.png")
        fig, ax = COMReport._subplots(output_file, figsize=(max(7, 0.7 * len(rows)), 4))
        ax.bar(np.arange(len(rows)), values)
        ax.set_xticks(np.arange(len(rows)))
        ax.set_xticklabels(labels)
        ax.set_title("Top Search Candidates")
        ax.set_xlabel("Candidate idx\n(g_DC, g_DC2)")
        ax.set_ylabel("FOM (dB)")
        ax.grid(True, axis="y")
        COMReport._finish_figure(fig, output_file)
        return ax

    def plot_summary(self, save_path: str = "") -> dict[str, Any]:
        """
        Plot the standard COM search report set.

        Parameters
        ----------
        save_path:
            Optional output directory. If empty, figures are shown interactively.
            If provided, fixed filenames are written under this directory.
        """
        outputs: dict[str, Any] = {}
        outputs["search_fom_trace"] = self.plot_fom_trace(save_path)
        outputs["search_top_candidates"] = self.plot_top_candidates(save_path)
        best_path = "" if not save_path else str(Path(save_path) / "best")
        outputs["best"] = self.best.plot_summary(best_path)
        return outputs

    def export(self, save_path: str, *, include_plots: bool = True) -> dict[str, str]:
        """
        Export search summary plus the full best-candidate COMStatus.

        Parameters
        ----------
        save_path:
            Output directory. The method writes search_summary.json and exports
            the best full status under ``best/``.
        include_plots:
            If True, also write search plots and best-candidate plots.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        rows = []
        for row in self.rows:
            rows.append({
                "idx": row.idx,
                "status": row.status,
                "error": row.error,
                "FOM": self._json_scalar(row.FOM),
                "As": self._json_scalar(row.As),
                "sigma_ISI": self._json_scalar(row.sigma_ISI),
                "sigma_J": self._json_scalar(row.sigma_J),
                "sigma_XT": self._json_scalar(row.sigma_XT),
                "sigma_N": self._json_scalar(row.sigma_N),
                "sigma_TX": self._json_scalar(row.sigma_TX),
                "ts": self._json_scalar(row.ts),
                "pos": self._json_scalar(row.pos),
                "candidate": {
                    "c_m2": row.candidate.c_m2,
                    "c_m1": row.candidate.c_m1,
                    "c_1": row.candidate.c_1,
                    "g_DC": row.candidate.g_DC,
                    "g_DC2": row.candidate.g_DC2,
                },
            })

        summary = {
            "type": type(self).__name__,
            "num_candidates": self.num_candidates,
            "num_success": self.num_success,
            "num_error": self.num_error,
            "COM": self._json_scalar(self.COM),
            "best_row_idx": self.best_row.idx,
            "best_row_FOM": self.best_row.FOM,
            "rows": rows,
        }
        summary_path = out_dir / "search_summary.json"
        self._write_json(summary_path, summary)

        best_outputs = self.best.export(str(out_dir / "best"), include_plots=include_plots)
        outputs = {
            "search_summary": str(summary_path),
            "best_arrays": best_outputs["arrays"],
        }
        if include_plots:
            self.plot_summary(str(out_dir / "plots"))
            outputs["plots"] = str(out_dir / "plots")
        return outputs

class COMReport:
    """
    Plot/report orchestration for COM run results.

    Class boundary
    --------------
    COMReport owns presentation behavior that needs both COMConfig and
    COMStatus. COM and the 93A helper functions should stay focused on
    spec-defined computation; COMStatus remains the data container.
    """

    def __init__(self, cfg: COMConfig, status: COMStatus | COMSearchStatus):
        self.cfg = cfg
        self.search_status = status if isinstance(status, COMSearchStatus) else None
        self.status = status.best if isinstance(status, COMSearchStatus) else status

    @staticmethod
    def _plt() -> Any:
        """Import pyplot without changing the active Matplotlib backend."""
        import matplotlib.pyplot as plt

        return plt

    @staticmethod
    def _plot_save_path(save_path: str, filename: str) -> str:
        if not save_path:
            return ""

        path = Path(save_path)
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)

        path.mkdir(parents=True, exist_ok=True)
        return str(path / filename)

    @staticmethod
    def _subplots(save_path: str, *args: Any, **kwargs: Any) -> tuple[Any, Any]:
        """
        Create a figure without changing Matplotlib's global backend.

        If save_path is provided, use a local Agg canvas so batch export does
        not require a GUI backend and does not pollute an interactive debug
        session.
        """
        if save_path:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure

            figsize = kwargs.pop("figsize", None)
            fig = Figure(figsize=figsize)
            FigureCanvasAgg(fig)
            ax = fig.subplots(*args, **kwargs)
            return fig, ax

        plt = COMReport._plt()
        return plt.subplots(*args, **kwargs)

    @staticmethod
    def _finish_figure(fig: Any, save_path: str) -> None:
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
        else:
            plt = COMReport._plt()
            fig.canvas.draw_idle()
            plt.show()

    @staticmethod
    def _path_display_label(idx: int, path: COMPath) -> str:
        return f"{idx}:{path.kind}"

    def _config_note(self) -> str:
        return (
            f"fb={self.cfg.link.fb / 1e9:.3f} GHz, "
            f"OSR={self.cfg.link.per_ui}, "
            f"df={self.cfg.link.df / 1e6:.3f} MHz"
        )

    @staticmethod
    def _format_txfir(txfir: np.ndarray) -> str:
        values = [f"{float(x):.3g}" for x in np.asarray(txfir, dtype=float)]
        return "[" + ", ".join(values) + "]"

    @staticmethod
    def _format_freq_ghz(value: Optional[float]) -> str:
        return "None" if value is None else f"{float(value) / 1e9:.3g} GHz"

    def _set_plot_title(self, ax: Any, title: str, subtitle: str = "") -> None:
        if subtitle:
            ax.set_title(title, fontsize=15, pad=22)
        else:
            ax.set_title(title, fontsize=15)
        if subtitle:
            ax.text(
                0.5,
                1.01,
                subtitle,
                ha="center",
                va="bottom",
                transform=ax.transAxes,
                fontsize=10,
                color="0.25",
            )

    def _annotate_config(self, ax: Any) -> None:
        ax.text(
            0.01,
            0.01,
            self._config_note(),
            ha="left",
            va="bottom",
            transform=ax.transAxes,
            fontsize=8,
            bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "edgecolor": "0.7"},
        )

    def _path_label(self, path_idx: int) -> str:
        path = self.status.paths[path_idx]
        return f"{path_idx:02d}_{path.kind}"

    def _path_dir(self, save_path: str, path_idx: int) -> str:
        if not save_path:
            return ""
        if path_idx == 0 and self.status.paths[path_idx].kind == "victim":
            dirname = "victim_path"
        else:
            dirname = f"path_{self._path_label(path_idx)}"
        path = Path(save_path) / dirname
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _default_freq_xlim(self, freqs: np.ndarray) -> tuple[float, float]:
        freqs = np.asarray(freqs, dtype=float)
        if freqs.ndim != 1 or len(freqs) == 0:
            raise ValueError("Frequency grid must be a non-empty 1D array.")
        fb = float(self.cfg.link.fb)
        f_max = float(freqs[-1])
        if f_max >= 1.1 * fb:
            hi = 1.1 * fb
        elif f_max >= fb:
            hi = f_max
        else:
            hi = fb
        return (0.0, hi)

    @staticmethod
    def _apply_auto_ylim_from_lines(
        ax: Any,
        xlim_hz: tuple[float, float],
        *,
        x_scale: float = 1e-9,
        floor_db: float = -300.0,
        pad_ratio: float = 0.05,
    ) -> None:
        lo_x = float(xlim_hz[0]) * x_scale
        hi_x = float(xlim_hz[1]) * x_scale
        values: list[np.ndarray] = []
        for line in ax.lines:
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            if x.shape != y.shape:
                continue
            mask = (x >= lo_x) & (x <= hi_x)
            if np.any(mask):
                values.append(y[mask])
        if not values:
            return
        visible = np.concatenate(values)
        visible = visible[np.isfinite(visible)]
        above_floor = visible[visible > float(floor_db)]
        if above_floor.size > 0:
            visible = above_floor
        if visible.size == 0:
            return
        y_min = float(np.min(visible))
        y_max = float(np.max(visible))
        if np.isclose(y_min, y_max):
            pad = max(1.0, abs(y_min) * float(pad_ratio))
        else:
            pad = (y_max - y_min) * float(pad_ratio)
        ax.set_ylim(y_min - pad, y_max + pad)

    def _plot_sparam_sdd(
        self,
        model: SparamModel,
        title: str,
        filename: str,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        subtitle: str = "",
        annotate_3db: bool = False,
        annotate_fb: bool = False,
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        if xlim is None:
            xlim = self._default_freq_xlim(model.freqs)
        terms = [
            ("Sdd11", model.sdd11),
            ("Sdd12", model.sdd12),
            ("Sdd21", model.sdd21),
            ("Sdd22", model.sdd22),
        ]
        tiny = np.finfo(float).tiny
        for label, values in terms:
            ax.plot(model.freqs / 1e9, 20 * np.log10(np.maximum(np.abs(values), tiny)), label=label)
        self._set_plot_title(ax, title, subtitle)
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Magnitude (dB)")
        ax.set_xlim(xlim[0] / 1e9, xlim[1] / 1e9)
        self._apply_auto_ylim_from_lines(ax, xlim)
        if annotate_fb and self.cfg.link.fb <= float(model.freqs[-1]):
            model.annotate_IL(ax, self.cfg.link.fb, label="IL")
        elif annotate_fb:
            ax.text(
                0.99,
                0.08,
                "fb outside S-param measured band",
                ha="right",
                va="bottom",
                transform=ax.transAxes,
                fontsize=8,
                color="tab:red",
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "edgecolor": "0.7"},
            )
        if annotate_3db:
            f_3db = model.frequency_at_sdd21_gain(-3.0)
            if f_3db is not None and f_3db <= xlim[1]:
                model.annotate_f(ax, f_3db, label="Sdd21 -3dB")
        ax.grid(True)
        ax.legend()
        self._finish_figure(fig, output_file)
        return ax

    def _plot_sparam_il(
        self,
        model: SparamModel,
        title: str,
        filename: str,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        subtitle: str = "",
        annotate_3db: bool = False,
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        if xlim is None:
            xlim = self._default_freq_xlim(model.freqs)
        annotate_f = self.cfg.link.fb if self.cfg.link.fb <= float(model.freqs[-1]) else None
        model.plot_IL(ax=ax, xlim=xlim, annotate_f=annotate_f, annotate_label="IL")
        if annotate_f is None:
            ax.text(
                0.99,
                0.08,
                "fb outside S-param measured band",
                ha="right",
                va="bottom",
                transform=ax.transAxes,
                fontsize=8,
                color="tab:red",
                bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "alpha": 0.75, "edgecolor": "0.7"},
            )
        if annotate_3db:
            f_3db = model.frequency_at_sdd21_gain(-3.0)
            if f_3db is not None and f_3db <= xlim[1]:
                model.annotate_f(ax, f_3db, label="Sdd21 -3dB")
        self._set_plot_title(ax, title, subtitle)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_link_tf(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
        subtitle: str = "",
        annotate_3db: bool = False,
        annotate_fb: bool = False,
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        if xlim is None:
            xlim = self._default_freq_xlim(segment.freqs)
        segment.plot_tf(ax=ax, xlim=xlim, ylim=ylim)
        if annotate_fb and self.cfg.link.fb <= float(segment.freqs[-1]):
            segment.annotate_f(ax, self.cfg.link.fb)
        if annotate_3db:
            f_3db = segment.frequency_at_gain(-3.0)
            if f_3db is not None and f_3db <= xlim[1]:
                segment.annotate_f(ax, f_3db)
        self._set_plot_title(ax, title, subtitle)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_link_ir(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        segment.plot_ir(ax=ax, x_origin="max", x_unit="ui", xlim_ui=xlim_ui)
        ax.set_title(title)
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_pmf(
        self,
        pmf: Optional[Pmf1D],
        title: str,
        filename: str,
        save_path: str = "",
    ) -> Any:
        if pmf is None:
            raise ValueError(f"{title} PMF is not available.")
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        ax.plot(pmf.x, pmf.pmf)
        ax.set_title(title)
        ax.set_xlabel("Amplitude (V)")
        ax.set_ylabel("Probability mass")
        ax.grid(True)
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_discrete_time_response(
        self,
        x_ui: np.ndarray,
        y: np.ndarray,
        title: str,
        ylabel: str,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
        filename: str = "discrete_response.png",
    ) -> Any:
        x_ui = np.asarray(x_ui, dtype=float)
        y = np.asarray(y, dtype=float)
        if x_ui.shape != y.shape:
            raise ValueError("x_ui and y must have the same shape.")
        if not np.all(np.isfinite(x_ui)) or not np.all(np.isfinite(y)):
            raise ValueError("x_ui and y must contain only finite values.")

        output_file = self._plot_save_path(save_path, filename)
        created_ax = ax is None
        if created_ax:
            fig, ax = self._subplots(output_file)
        else:
            fig = ax.figure

        ax.plot(x_ui, y, marker="o", markersize=3, linewidth=1.0, label=label)
        if label is not None:
            ax.legend()
        ax.set_title(title)
        ax.set_xlabel("Discrete time (UI, main cursor = 0)")
        ax.set_ylabel(ylabel)
        if xlim_ui is not None:
            ax.set_xlim(*xlim_ui)
        ax.grid(True)
        self._annotate_config(ax)

        if output_file or created_ax:
            self._finish_figure(fig, output_file)
        return ax

    def _h_dsamp(self) -> np.ndarray:
        dfe = self.status.dfe
        if dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")
        return self.status.victim.pulse.ir[dfe.pos::self.cfg.link.per_ui]

    def _t_dsamp_ui(self) -> np.ndarray:
        dfe = self.status.dfe
        if dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")
        num_pre = (dfe.ts - dfe.pos) // self.cfg.link.per_ui
        return np.arange(len(self._h_dsamp()), dtype=float) - float(num_pre)

    def _h_j_ui_axis(self) -> np.ndarray:
        dfe = self.status.dfe
        if dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")

        h = self.status.victim.pulse.ir
        pos = int(dfe.ts) % self.cfg.link.per_ui
        center_idx = np.arange(pos, len(h), self.cfg.link.per_ui)
        valid = (center_idx > 0) & (center_idx < len(h) - 1)
        center_idx = center_idx[valid]
        return (center_idx.astype(float) - float(dfe.ts)) / float(self.cfg.link.per_ui)

    def plot_paths_pulses(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        output_file = self._plot_save_path(save_path, "path_pulses.png")
        fig, ax = self._subplots(output_file)
        for idx, path in enumerate(self.status.paths):
            ir = path.pulse.ir
            x = path.pulse.cfg.times_ui - path.pulse.cfg.times_ui[int(np.argmax(np.abs(ir)))]
            ax.plot(x, ir, label=self._path_display_label(idx, path))
        ax.set_title("Path Pulse Responses")
        ax.set_xlabel("Time (UI)")
        ax.set_ylabel("h(t)")
        if xlim_ui is not None:
            ax.set_xlim(*xlim_ui)
        ax.grid(True)
        ax.legend()
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def plot_paths_S_all_IL(
        self,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
    ) -> Any:
        output_file = self._plot_save_path(save_path, "path_S_all_IL.png")
        fig, ax = self._subplots(output_file)
        if xlim is None:
            xlim = (0.0, float(self.cfg.link.fb))
        for idx, path in enumerate(self.status.paths):
            path.S_all.plot_IL(
                ax=ax,
                xlim=xlim,
                label=self._path_display_label(idx, path),
                auto_ylim=False,
            )
        self._apply_auto_ylim_from_lines(ax, xlim)
        ax.set_title("Augmented Signal Path IL, S_all")
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_link_sbr(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-2.0, 4.0),
        subtitle: str = "",
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        segment.plot_sbr(ax=ax, x_origin="start", x_unit="ui", xlim_ui=xlim_ui)
        self._set_plot_title(ax, title, subtitle)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_link_sr(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-0.2, 1.2),
        subtitle: str = "",
        annotate_20_80: bool = False,
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        segment.plot_sr(ax=ax, x_origin="max", x_unit="ui", xlim_ui=xlim_ui)
        if annotate_20_80:
            self._annotate_step_transition(ax, segment)
        self._set_plot_title(ax, title, subtitle)
        self._finish_figure(fig, output_file)
        return ax

    def _annotate_step_transition(self, ax: Any, segment: LinkSegment) -> None:
        sr = np.asarray(segment.sr, dtype=float)
        x_ui = (segment.times - segment.times[int(np.argmax(np.abs(segment.ir)))]) * self.cfg.link.fb
        y0 = float(np.nanmin(sr))
        y1 = float(np.nanmax(sr))
        span = y1 - y0
        if not np.isfinite(span) or span <= 0.0:
            return

        y20 = y0 + 0.2 * span
        y80 = y0 + 0.8 * span

        def crossing(level: float) -> Optional[float]:
            above = np.flatnonzero(sr >= level)
            if above.size == 0:
                return None
            idx = int(above[0])
            if idx == 0:
                return float(x_ui[0])
            x0, x1 = float(x_ui[idx - 1]), float(x_ui[idx])
            v0, v1 = float(sr[idx - 1]), float(sr[idx])
            if np.isclose(v1, v0):
                return x1
            return x0 + (level - v0) * (x1 - x0) / (v1 - v0)

        x20 = crossing(y20)
        x80 = crossing(y80)
        if x20 is None or x80 is None:
            return

        ax.axhline(y20, linestyle=":", color="tab:gray", linewidth=1.0)
        ax.axhline(y80, linestyle=":", color="tab:gray", linewidth=1.0)
        ax.axvline(x20, linestyle="--", color="tab:red", linewidth=1.0)
        ax.axvline(x80, linestyle="--", color="tab:red", linewidth=1.0)
        ax.annotate(
            f"20%-80% = {x80 - x20:.3g} UI",
            xy=((x20 + x80) / 2.0, y80),
            xytext=(8, 8),
            textcoords="offset points",
            color="tab:red",
            fontsize=9,
        )

    def plot_paths_H21_tf(
        self,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
    ) -> Any:
        output_file = self._plot_save_path(save_path, "path_H21_tf.png")
        fig, ax = self._subplots(output_file)
        if xlim is None:
            xlim = (0.0, float(self.cfg.link.fb))
        for idx, path in enumerate(self.status.paths):
            path.H_21.plot_tf(
                ax=ax,
                xlim=xlim,
                ylim=ylim,
                auto_ylim=False,
                label=self._path_display_label(idx, path),
            )
        if ylim is None:
            self._apply_auto_ylim_from_lines(ax, xlim)
        ax.set_title("Voltage Transfer Function H21")
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def plot_COMPath(self, path_idx: int = 0, save_path: str = "") -> dict[str, Any]:
        """
        Plot detailed path-building results for one COMPath.

        Parameters
        ----------
        path_idx:
            Index in COMStatus.paths. Default 0 plots the victim path.
        save_path:
            Optional output directory. If provided, figures are written under a
            path-specific subdirectory.
        """
        path_idx = int(path_idx)
        if path_idx < 0 or path_idx >= len(self.status.paths):
            raise IndexError("path_idx is outside COMStatus.paths.")

        path = self.status.paths[path_idx]
        path_dir = self._path_dir(save_path, path_idx)
        outputs: dict[str, Any] = {}
        outputs["S_tx_sdd"] = self._plot_S_tx(path, path_dir)
        outputs["S_ch_sdd"] = self._plot_S_ch(path, path_dir)
        outputs["S_rx_sdd"] = self._plot_S_rx(path, path_dir)
        outputs["S_all_sdd"] = self._plot_S_all(path, path_dir)
        outputs["S_all_IL"] = self._plot_sparam_il(
            path.S_all,
            f"{self._path_label(path_idx)} S_all IL",
            "S_all_IL.png",
            path_dir,
            subtitle="Cascaded through-path IL; IL@fb is absolute when fb is inside measured band",
        )
        outputs["H_ffe_tf"] = self._plot_H_ffe(path, path_dir)
        outputs["H_t_tf"] = self._plot_H_t(path, path_dir)
        outputs["H_t_sr"] = self._plot_H_t_sr(path, path_dir)
        outputs["H_21_tf"] = self._plot_H_21(path, path_dir)
        outputs["H_21_ir"] = self._plot_link_ir(path.H_21, f"{self._path_label(path_idx)} H_21 IR", "H_21_ir.png", path_dir)
        outputs["H_r_tf"] = self._plot_H_r(path, path_dir)
        outputs["H_ctf_tf"] = self._plot_H_ctf(path, path_dir)
        outputs["H_all_tf"] = self._plot_link_tf(path.H_all, f"{self._path_label(path_idx)} H_all", "H_all_tf.png", path_dir)
        outputs["pulse_ir"] = self._plot_link_ir(path.pulse, f"{self._path_label(path_idx)} Pulse IR", "pulse_ir.png", path_dir)
        return outputs

    def _plot_S_tx(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_tx,
            f"{path.kind} S_tx",
            "S_tx_sdd.png",
            save_path,
            subtitle="TX package S-parameter",
        )

    def _plot_S_rx(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_rx,
            f"{path.kind} S_rx",
            "S_rx_sdd.png",
            save_path,
            subtitle="RX package S-parameter",
        )

    def _plot_S_ch(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_ch,
            f"{path.kind} S_ch",
            "S_ch_sdd.png",
            save_path,
            subtitle="Channel Sdd; IL@fb is absolute when fb is inside measured band",
            annotate_fb=True,
        )

    def _plot_S_all(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_all,
            f"{path.kind} S_all",
            "S_all_sdd.png",
            save_path,
            subtitle="Cascaded S_tx + S_ch + S_rx; IL@fb is absolute when fb is inside measured band",
            annotate_fb=True,
        )

    def _plot_H_ffe(self, path: COMPath, save_path: str = "") -> Any:
        if path.kind == "next":
            subtitle = "NEXT aggressor H_ffe = 1 by COM path convention"
        else:
            subtitle = f"txfir = {self._format_txfir(self.cfg.filter.txfir)}"
        return self._plot_link_tf(
            path.H_ffe,
            f"{path.kind} H_ffe",
            "H_ffe_tf.png",
            save_path,
            subtitle=subtitle,
        )

    def _plot_H_t(self, path: COMPath, save_path: str = "") -> Any:
        Tr = self.cfg.filter.Tr
        if Tr is None:
            subtitle = "Tr = None"
        else:
            subtitle = f"Tr = {Tr * 1e12:.3g} ps = {Tr * self.cfg.link.fb:.3g} UI"
        return self._plot_link_tf(
            path.H_t,
            f"{path.kind} H_t",
            "H_t_tf.png",
            save_path,
            subtitle=subtitle,
            annotate_fb=True,
        )

    def _plot_H_t_sr(self, path: COMPath, save_path: str = "") -> Any:
        Tr = self.cfg.filter.Tr
        if Tr is None:
            subtitle = "Tr = None"
        else:
            subtitle = f"Tr = {Tr * 1e12:.3g} ps = {Tr * self.cfg.link.fb:.3g} UI"
        return self._plot_link_sr(
            path.H_t,
            f"{path.kind} H_t Step Response",
            "H_t_sr.png",
            save_path,
            xlim_ui=(-0.4, 1.2),
            subtitle=subtitle,
            annotate_20_80=True,
        )

    def _plot_H_21(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_link_tf(
            path.H_21,
            f"{path.kind} H_21",
            "H_21_tf.png",
            save_path,
            subtitle="Terminated voltage transfer function; fb marker shows channel loss relative to DC",
            annotate_fb=True,
        )

    def _plot_H_r(self, path: COMPath, save_path: str = "") -> Any:
        fr = self.cfg.filter.fr
        subtitle = "fr = None" if fr is None else f"fr = {fr / 1e9:.3g} GHz"
        return self._plot_link_tf(
            path.H_r,
            f"{path.kind} H_r",
            "H_r_tf.png",
            save_path,
            subtitle=subtitle,
            annotate_3db=True,
            annotate_fb=True,
        )

    def _plot_H_ctf(self, path: COMPath, save_path: str = "") -> Any:
        subtitle = (
            f"g_DC={self.cfg.filter.g_DC} dB, g_DC2={self.cfg.filter.g_DC2} dB, "
            f"fz={self._format_freq_ghz(self.cfg.filter.f_z)}, "
            f"fp1={self._format_freq_ghz(self.cfg.filter.f_p1)}, "
            f"fp2={self._format_freq_ghz(self.cfg.filter.f_p2)}"
        )
        return self._plot_link_tf(
            path.H_ctf,
            f"{path.kind} H_ctf",
            "H_ctf_tf.png",
            save_path,
            subtitle=subtitle,
        )

    def plot_COMDFEStatus(self, save_path: str = "") -> dict[str, Any]:
        if self.status.dfe is None:
            raise ValueError("COMStatus.dfe is None; run DFE calculation first.")
        out_dir = "" if not save_path else str(Path(save_path) / "dfe")
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        outputs: dict[str, Any] = {}
        outputs["h"] = self._plot_link_ir(self.status.victim.pulse, "Victim Pulse h(t)", "h_ir.png", out_dir)
        outputs["h_dsamp"] = self.plot_h_dsamp(save_path=out_dir)
        outputs["h_ISI"] = self.plot_h_ISI(save_path=out_dir)
        outputs["dfe_summary"] = self._plot_dfe_summary(out_dir)
        return outputs

    def _plot_dfe_summary(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        if self.status.dfe is None:
            raise ValueError("COMStatus.dfe is None; run DFE calculation first.")

        output_file = self._plot_save_path(save_path, "dfe_summary.png")
        fig, axes = self._subplots(output_file, 2, 1, figsize=(7, 6))
        tap_idx = np.arange(1, len(self.status.dfe.dfe_coeff) + 1)
        axes[0].bar(tap_idx, self.status.dfe.dfe_coeff)
        axes[0].set_title("DFE Coefficients")
        axes[0].set_xlabel("Tap index")
        axes[0].set_ylabel("Coefficient")
        axes[0].set_xlim(0.5, max(1.5, len(self.status.dfe.dfe_coeff) + 0.5))
        axes[0].grid(True)

        axes[1].bar(self._t_dsamp_ui(), self.status.dfe.h_ISI, width=0.8)
        axes[1].set_title("Residual ISI Samples")
        axes[1].set_xlabel("Discrete time (UI, main cursor = 0)")
        axes[1].set_ylabel("Amplitude (V)")
        if xlim_ui is not None:
            axes[1].set_xlim(*xlim_ui)
        axes[1].grid(True)
        self._annotate_config(axes[1])
        self._finish_figure(fig, output_file)
        return axes

    def plot_h_dsamp(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        return self._plot_discrete_time_response(
            self._t_dsamp_ui(),
            self._h_dsamp(),
            title="Downsampled Victim Pulse",
            ylabel="h_dsamp (V)",
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
            filename="h_dsamp.png",
        )

    def plot_h_ISI(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        if self.status.dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")
        return self._plot_discrete_time_response(
            self._t_dsamp_ui(),
            self.status.dfe.h_ISI,
            title="Residual ISI Samples",
            ylabel="h_ISI (V)",
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
            filename="h_ISI.png",
        )

    def plot_h_J(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        if self.status.imp is None:
            raise RuntimeError("COMStatus.imp is not available.")
        return self._plot_discrete_time_response(
            self._h_j_ui_axis(),
            self.status.imp.h_J,
            title="Sampled Jitter Sensitivity",
            ylabel="h_J (V/UI)",
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
            filename="h_J.png",
        )

    def plot_COMImpairmentStatus(self, save_path: str = "") -> dict[str, Any]:
        if self.status.imp is None:
            raise ValueError("COMStatus.imp is None; run imp calculation first.")
        out_dir = "" if not save_path else str(Path(save_path) / "imp")
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        outputs: dict[str, Any] = {}
        outputs["imp_summary"] = self._plot_imp_summary(out_dir)
        outputs["h_J"] = self.plot_h_J(save_path=out_dir)
        outputs["noise_filter"] = self._plot_noise_filter(out_dir)
        return outputs

    def _plot_imp_summary(self, save_path: str = "") -> Any:
        if self.status.imp is None:
            raise ValueError("COMStatus.imp is None; run imp calculation first.")

        labels = ["TX", "ISI", "J", "XT", "N"]
        values = [
            self.status.imp.sigma_TX,
            self.status.imp.sigma_ISI,
            self.status.imp.sigma_J,
            self.status.imp.sigma_XT,
            self.status.imp.sigma_N,
        ]

        output_file = self._plot_save_path(save_path, "imp_summary.png")
        fig, ax = self._subplots(output_file)
        ax.bar(labels, values)
        ax.set_title("Imp RMS Breakdown")
        ax.set_ylabel("RMS amplitude (V)")
        ax.grid(True, axis="y")
        text = f"As={self.status.imp.As:.4e} V"
        if self.status.FOM is not None:
            text += f"\nFOM={self.status.FOM:.2f} dB"
        ax.text(0.98, 0.95, text, ha="right", va="top", transform=ax.transAxes)
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_noise_filter(self, save_path: str = "") -> Any:
        noise_filter = _build_H_r_93A(self.cfg.link, self.cfg.filter).cascade_tf(
            _build_H_ctf_93A(self.cfg.link, self.cfg.filter)
        )
        output_file = self._plot_save_path(save_path, "noise_filter_tf.png")
        fig, ax = self._subplots(output_file)
        noise_filter.plot_tf(ax=ax)
        if self.cfg.filter.fr is not None:
            fr_ghz = self.cfg.filter.fr / 1e9
            ax.axvline(fr_ghz, linestyle="--", color="tab:red", linewidth=1.0, label=f"fr={fr_ghz:.3f} GHz")
            ax.legend()
        ax.set_title("Receiver Noise Filter H_r * H_ctf")
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def plot_COMPMFStatus(self, save_path: str = "") -> dict[str, Any]:
        if self.status.pmf is None:
            raise ValueError("COMStatus.pmf is None; run PMF calculation first.")
        out_dir = "" if not save_path else str(Path(save_path) / "pmf")
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        pmf = self.status.pmf
        outputs: dict[str, Any] = {}
        outputs["p_ISI"] = self._plot_pmf(pmf.p_ISI, "PMF ISI", "p_ISI.png", out_dir)
        outputs["p_G"] = self._plot_pmf(pmf.p_G, "PMF Gaussian Noise", "p_G.png", out_dir)
        outputs["p_DD"] = self._plot_pmf(pmf.p_DD, "PMF Dual-Dirac Jitter", "p_DD.png", out_dir)
        outputs["p_XT"] = self._plot_pmf(pmf.p_XT, "PMF Crosstalk", "p_XT.png", out_dir)
        outputs["p_combined"] = self._plot_pmf(pmf.p_combined, "PMF Combined", "p_combined.png", out_dir)
        outputs["pmf_summary"] = self._plot_pmf_summary(out_dir)
        return outputs

    def _plot_pmf_summary(self, save_path: str = "") -> Any:
        if self.status.pmf is None:
            raise ValueError("COMStatus.pmf is None; run PMF calculation first.")

        components = [
            ("ISI", self.status.pmf.p_ISI),
            ("G", self.status.pmf.p_G),
            ("DD", self.status.pmf.p_DD),
            ("XT", self.status.pmf.p_XT),
            ("combined", self.status.pmf.p_combined),
        ]

        output_file = self._plot_save_path(save_path, "pmf_summary.png")
        fig, axes = self._subplots(output_file, 2, 1, figsize=(7, 6))
        for label, p in components:
            if p is not None:
                axes[0].plot(p.x, p.pmf, label=label)
        axes[0].set_title("PMF Components")
        axes[0].set_xlabel("Amplitude (V)")
        axes[0].set_ylabel("Probability mass")
        axes[0].grid(True)
        axes[0].legend()

        if self.status.pmf.p_combined is not None:
            p = self.status.pmf.p_combined
            axes[1].plot(p.x, p.cdf, label="combined CDF")
            if self.status.pmf.y0 is not None:
                axes[1].axvline(self.status.pmf.y0, linestyle="--", color="tab:red", label=f"y0={self.status.pmf.y0:.3e} V")
            axes[1].legend()
        axes[1].set_title("Combined CDF")
        axes[1].set_xlabel("Amplitude (V)")
        axes[1].set_ylabel("CDF")
        axes[1].grid(True)
        self._annotate_config(axes[1])

        title = []
        if self.status.pmf.COM is not None:
            title.append(f"COM={self.status.pmf.COM:.2f} dB")
        if self.status.pmf.A_ni is not None:
            title.append(f"A_ni={self.status.pmf.A_ni:.3e} V")
        if title:
            fig.suptitle(", ".join(title))

        self._finish_figure(fig, output_file)
        return axes

    def plot_single_run(self, save_path: str = "", path_idx: int = 0) -> dict[str, Any]:
        """
        Plot detailed single-run report figures.

        Parameters
        ----------
        save_path:
            Optional output directory.
        path_idx:
            Path index for the detailed COMPath plot. Default 0 is victim.
        """
        outputs: dict[str, Any] = {}
        if save_path:
            Path(save_path).mkdir(parents=True, exist_ok=True)

        outputs["paths_pulses"] = self.plot_paths_pulses(save_path)
        outputs["paths_S_all_IL"] = self.plot_paths_S_all_IL(save_path)
        outputs["paths_H21_tf"] = self.plot_paths_H21_tf(save_path)
        outputs["COMPath"] = self.plot_COMPath(path_idx=path_idx, save_path=save_path)
        if self.status.dfe is not None:
            outputs["COMDFEStatus"] = self.plot_COMDFEStatus(save_path)
        if self.status.imp is not None:
            outputs["COMImpairmentStatus"] = self.plot_COMImpairmentStatus(save_path)
        if self.status.pmf is not None:
            outputs["COMPMFStatus"] = self.plot_COMPMFStatus(save_path)
        return outputs

    def plot_search_run(self, save_path: str = "") -> dict[str, Any]:
        """
        Plot search-run report figures.

        The current search detail view keeps search-level summary figures and
        then plots the best candidate through the single-run report path.
        """
        if self.search_status is None:
            raise ValueError("COMReport was not initialized with COMSearchStatus.")
        outputs: dict[str, Any] = {}
        if save_path:
            Path(save_path).mkdir(parents=True, exist_ok=True)
        outputs["search_fom_trace"] = self.search_status.plot_fom_trace(save_path)
        outputs["search_top_candidates"] = self.search_status.plot_top_candidates(save_path)
        best_dir = "" if not save_path else str(Path(save_path) / "best")
        outputs["best"] = COMReport(self.cfg, self.search_status.best).plot_single_run(best_dir)
        return outputs

# ======================================
# class helpers
# ======================================

def _build_txpkg_93A(freqs: np.ndarray, txpkg_cfg: COMPkgConfig, *, isNext: bool = False) -> IEEECOMsparam:
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

    S_d = IEEECOMsparam.shunt_capacitance_93A(freqs, C_d, txpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance_93A(freqs, L_s, txpkg_cfg.R0)
    S_b = IEEECOMsparam.shunt_capacitance_93A(freqs, C_b, txpkg_cfg.R0)
    S_l = IEEECOMsparam.pkg_trans_line_93A(freqs, txpkg_cfg.R0, txpkg_cfg.z_p, Zc=txpkg_cfg.Z_c)
    if (txpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line_93A(freqs, txpkg_cfg.R0, txpkg_cfg.z_p2, Zc=txpkg_cfg.Z_c2)
    S_p = IEEECOMsparam.shunt_capacitance_93A(freqs, C_p, txpkg_cfg.R0)

    # cascade
    S_td = (S_d.cascade_com_93A(S_s)).cascade_com_93A(S_b)
    if (txpkg_cfg.z_p2 is not None):
        S_tp = ((S_td.cascade_com_93A(S_l)).cascade_com_93A(S_l2)).cascade_com_93A(S_p)
    else:
        S_tp = (S_td.cascade_com_93A(S_l)).cascade_com_93A(S_p)
    return S_tp

def _build_rxpkg_93A(freqs: np.ndarray, rxpkg_cfg: COMPkgConfig) -> IEEECOMsparam:
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

    S_p = IEEECOMsparam.shunt_capacitance_93A(freqs, C_p, rxpkg_cfg.R0)
    if (rxpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line_93A(freqs, rxpkg_cfg.R0, rxpkg_cfg.z_p2, Zc=rxpkg_cfg.Z_c2)
    S_l = IEEECOMsparam.pkg_trans_line_93A(freqs, rxpkg_cfg.R0, rxpkg_cfg.z_p, Zc=rxpkg_cfg.Z_c)
    S_b = IEEECOMsparam.shunt_capacitance_93A(freqs, C_b, rxpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance_93A(freqs, L_s, rxpkg_cfg.R0)
    S_d = IEEECOMsparam.shunt_capacitance_93A(freqs, C_d, rxpkg_cfg.R0)
    
    # cascade
    S_rd = (S_b.cascade_com_93A(S_s)).cascade_com_93A(S_d)
    if (rxpkg_cfg.z_p2 is not None):
        S_rp = ((S_p.cascade_com_93A(S_l2)).cascade_com_93A(S_l)).cascade_com_93A(S_rd)
    else:
        S_rp = (S_p.cascade_com_93A(S_l)).cascade_com_93A(S_rd)
    return S_rp

def _build_H_ffe_93A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build victim/FEXT TX FFE filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with dimensionless TX FFE taps.
    """
    return IEEECOMFilter.tx_ffe_93A(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)

def _build_H_ffe_next_93A(link_cfg: LinkConfig) -> IEEECOMFilter:
    """
    Build NEXT TX FFE filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.

    NEXT uses only the main cursor per 93A.1.4.2.
    """
    ffe_next = np.array([0,1,0])
    return IEEECOMFilter.tx_ffe_93A(link_cfg, ffe_next, num_pre=1)

def _build_H_t_93A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build transmitter transition-time filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with Tr in seconds.
    """
    return IEEECOMFilter.transition_time_filter_93A(link_cfg, ft_cfg.Tr)

def _build_H_r_93A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build receiver noise filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with fr in Hz.
    """
    return IEEECOMFilter.rx_noise_filter_93A(link_cfg, ft_cfg.fr)

def _build_H_ctf_93A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build receiver equalizer / CTF filter.

    Parameters
    ----------
    link_cfg:
        LinkConfig with frequency grid in Hz.
    ft_cfg:
        Filter config with gains in dB and pole/zero frequencies in Hz.
    """

    return IEEECOMFilter.rx_equalizer_93A(
        link_cfg, 
        ft_cfg.g_DC,
        ft_cfg.g_DC2,
        ft_cfg.f_z,
        ft_cfg.f_LF,
        ft_cfg.f_p1,
        ft_cfg.f_p2
    )

def _build_channel_under_test_93A(channel_cfg: COMChannelConfig) -> list[SparamModel]:
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

def _build_path_93A(
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig,
    txpkg_cfg: COMPkgConfig,
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
    txpkg_cfg:
        Path-specific TX package configuration used to build S_tx on S_ch.freqs.
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
        S_tx = _build_txpkg_93A(S_ch.freqs, txpkg_cfg, isNext=True)
        H_ffe = shared.H_ffe_next
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_ne)
    elif kind == "fext":
        S_tx = _build_txpkg_93A(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_fe)
    elif kind == "victim":
        S_tx = _build_txpkg_93A(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_v)
    else:
        raise ValueError(f"Unsupported COM path kind: {kind}")

    S_all = S_tx.cascade_com_93A(S_ch).cascade_com_93A(shared.S_rx)
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

def _build_shared_path_93A(cfg: COMConfig, freqs: np.ndarray) -> COMSharedPath:
    """
    Build path-shared COM models.

    This is a LV-2 COM path-generation helper. It builds the shared receiver
    package model on the measured-domain channel grid and the shared scalar
    filters on the LinkConfig FFT grid.
    """
    link_cfg = cfg.link
    ft_cfg = cfg.filter
    return COMSharedPath(
        H_ffe=_build_H_ffe_93A(link_cfg, ft_cfg),
        H_ffe_next=_build_H_ffe_next_93A(link_cfg),
        H_t=_build_H_t_93A(link_cfg, ft_cfg),
        S_rx=_build_rxpkg_93A(freqs, cfg.rxpkg),
        H_r=_build_H_r_93A(link_cfg, ft_cfg),
        H_ctf=_build_H_ctf_93A(link_cfg, ft_cfg),
    )

def _build_paths_93A(
    cfg: COMConfig,
    shared: COMSharedPath,
    channels: list[SparamModel],
) -> list[COMPath]:
    """
    Build path-specific COM models from aligned channel-under-test models.

    Contract:
    channels must come directly from _build_channel_under_test_93A(), so the order is:
        index 0: victim channel
        following indices: NEXT channels, then FEXT channels, in config order
    """
    link_cfg = cfg.link
    ch_cfg = cfg.channel
    ft_cfg = cfg.filter

    expected_count = 1 + len(ch_cfg.next_s4p_paths) + len(ch_cfg.fext_s4p_paths)
    if len(channels) != expected_count:
        raise ValueError(
            "channels length must match victim + NEXT + FEXT path count. "
            f"Expected {expected_count}, got {len(channels)}."
        )

    paths = [
        _build_path_93A(
            link_cfg=link_cfg,
            channel_cfg=ch_cfg,
            ft_cfg=ft_cfg,
            txpkg_cfg=cfg.txpkg_victim,
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
            _build_path_93A(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                txpkg_cfg=cfg.txpkg_next,
                shared=shared,
                kind="next",
                S_ch=S_ch,
            )
        )

    for S_ch in fext_channels:
        paths.append(
            _build_path_93A(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                txpkg_cfg=cfg.txpkg_fext,
                shared=shared,
                kind="fext",
                S_ch=S_ch,
            )
        )

    return paths

def _calculate_float_dfe_93A(h_dsamp:np.ndarray, dfe_cfg: COMDFEConfig) -> np.ndarray:
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

def _calculate_h_ISI_93A(h_dsamp: np.ndarray, dfe_coeff: np.ndarray) -> np.ndarray:
    num_pre = np.argmax(np.abs(h_dsamp))
    h_ISI = h_dsamp.copy()
    h_ISI[num_pre] = 0
    h_ISI[num_pre+1: num_pre+len(dfe_coeff)+1] -= dfe_coeff * h_dsamp[num_pre]
    return h_ISI

def _find_sampling_phase_93A(
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
            raise Exception("Polarity issue @ _find_sampling_phase_93A()")
        if (num_pre == 0 or num_pre + dfe_cfg.N_f >= len(h_dsamp)):
            raise Exception("Main cursor too close to boundary @ _find_sampling_phase_93A()")
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

def _calculate_h_J_93A(h: np.ndarray, ts: int, per_ui: int) -> np.ndarray:
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

def _find_pos_xtalk_93A(h_XT: np.ndarray, per_ui: int) -> tuple[int, np.ndarray]:
    RSS = np.zeros(per_ui)
    for m in np.arange(per_ui):
        RSS[m] = np.sum(h_XT[m:: per_ui]**2)
    i = np.argmax(RSS)
    h_XT_dsamp = h_XT[i:: per_ui]
    return i, h_XT_dsamp

def _build_pmf_interference_93A(
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

def _build_pmf_G_93A(imp_stat: COMImpairmentStatus_93A, imp_cfg: COMImpairmentConfig, pmf_cfg: COMPMFRuntimeConfig) -> Pmf1D:
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

def _build_pmf_XT_all_93A(
    p_sig: Pmf1D, 
    h_XTs: list[np.ndarray], 
    pmf_cfg: COMPMFRuntimeConfig, 
) -> Pmf1D:
    p_XT = Pmf1D.multi_dirac(np.array([0.0]), np.array([1.0]), dx=pmf_cfg.dy, unit="volt", name="XT_all")
    for h_XT in h_XTs:
        p_XT_new = _build_pmf_interference_93A(
            p_sig, 
            h_XT, 
            pmf_cfg,
            name="XT",
        )
        p_XT = p_XT.combine(p_XT_new, name="XT_all")
    p_XT.name = "XT_all"
    return p_XT

def _calculate_FOM_93A(imp_status: COMImpairmentStatus_93A) -> float:
    """
    Calculate the 93A.1.6 FOM from signal amplitude and RSS imp terms.

    This metric is used only to select the best variable equalizer candidate.
    The final COM still comes from the 93A.1.7 PMF calculation.
    """
    As = abs(float(imp_status.As))
    var_total = (
        imp_status.sigma_TX**2
        + imp_status.sigma_ISI**2
        + imp_status.sigma_J**2
        + imp_status.sigma_XT**2
        + imp_status.sigma_N**2
    )
    if As <= 0.0 or var_total <= 0.0:
        return float("-inf")
    return float(10 * np.log10(As**2 / var_total))


class COM_93A:
    """
    IEEE 802.3 Annex 93A COM calculator.

    Class boundary
    --------------
    COM_93A owns the versioned 93A algorithm pipeline:
    - build_all_paths_93A()
    - find_pos_and_dfe_93A()
    - calculate_imp_93A()
    - calculate_COM_93A()

    Shared data containers, plotting/reporting, Excel I/O, and generic signal
    processing utilities remain version-neutral.
    """

    def __init__(self, cfg: COMConfig):
        self.cfg = cfg
        self.status: Optional[COMStatus | COMSearchStatus] = None

    def run(self, search: Optional[COMSearchConfig] = None) -> COMStatus | COMSearchStatus:
        """
        Run COM for the current configuration.

        If search is None, run one concrete COMConfig point and return a full
        COMStatus. If search is provided, sweep the Cartesian product of the
        search values using 93A.1.6 FOM, then compute full PMF/COM only for the
        best-FOM candidate.
        """
        if search is None:
            self.status = self._run_once(calculate_pmf=True)
        else:
            self.status = self._run_search(search)
        return self.status

    def _run_once(self, *, calculate_pmf: bool = True) -> COMStatus:
        """
        Run one concrete COMConfig point without sweeping tunable parameters.

        This is the debug-friendly single-candidate pipeline:
        paths -> DFE/sample phase -> imp -> FOM -> optional PMF/COM.
        """
        paths = self.build_all_paths_93A()
        self._validate_victim_time_alignment(paths[0])
        dfe_status = self.find_pos_and_dfe_93A(h=paths[0].pulse.ir)
        imp_status = self.calculate_imp_93A(
            h=paths[0].pulse.ir,
            dfe_status=dfe_status,
            h_XTs=[path.pulse.ir for path in paths[1:]],
        )
        FOM = _calculate_FOM_93A(imp_status)
        pmf_status = self.calculate_COM_93A(imp_status) if calculate_pmf else None
        return COMStatus(paths=paths, dfe=dfe_status, imp=imp_status, pmf=pmf_status, FOM=FOM)

    def _run_search(self, search: COMSearchConfig) -> COMSearchStatus:
        candidates = search.candidates(self.cfg.filter)
        total = len(candidates)
        rows: list[COMSearchRow] = []
        best_row: Optional[COMSearchRow] = None
        best_cfg: Optional[COMConfig178A] = None
        num_error = 0
        start_time = time.perf_counter()
        last_print_time = start_time
        print(f"COM search started: {total} candidates")

        for idx, candidate in enumerate(candidates):
            candidate_cfg = self._config_with_search_candidate(candidate)
            try:
                candidate_status = COM_93A(candidate_cfg)._run_once(calculate_pmf=False)
                row = self._search_row_from_status(idx, candidate, candidate_status)
            except Exception as exc:
                if not search.continue_on_error:
                    raise
                num_error += 1
                row = COMSearchRow(
                    idx=idx,
                    candidate=candidate,
                    FOM=float("-inf"),
                    status="error",
                    error=str(exc),
                )
                rows.append(row)
                continue

            rows.append(row)
            if best_row is None or row.FOM > best_row.FOM:
                best_row = row
                best_cfg = candidate_cfg

            now = time.perf_counter()
            done = idx + 1
            should_print = done == total or done == 1 or done % 10 == 0 or (now - last_print_time) >= 5.0
            if should_print:
                elapsed = now - start_time
                rate = done / elapsed if elapsed > 0.0 else float("nan")
                remaining = (total - done) / rate if np.isfinite(rate) and rate > 0.0 else float("nan")
                percent = 100.0 * done / total if total > 0 else 100.0
                best_text = "n/a" if best_row is None else f"{best_row.FOM:.3f} dB @ {best_row.idx}"
                print(
                    "COM search progress: "
                    f"{done}/{total} ({percent:.1f}%), "
                    f"elapsed={self._format_duration(elapsed)}, "
                    f"eta={self._format_duration(remaining)}, "
                    f"best_FOM={best_text}"
                )
                last_print_time = now

        if best_row is None or best_cfg is None:
            raise RuntimeError("COM search did not produce any successful candidate.")

        print(f"COM search best candidate: idx={best_row.idx}, FOM={best_row.FOM:.3f} dB")
        print("Computing full PMF/COM for best candidate...")
        best_status = COM_93A(best_cfg)._run_once(calculate_pmf=True)
        elapsed_total = time.perf_counter() - start_time
        print(
            "COM search completed: "
            f"elapsed={self._format_duration(elapsed_total)}, "
            f"best_COM={best_status.pmf.COM if best_status.pmf is not None else 'n/a'}"
        )
        return COMSearchStatus(
            best=best_status,
            best_row=best_row,
            rows=self._select_search_rows(rows, search),
            num_candidates=len(candidates),
            num_success=len(candidates) - num_error,
            num_error=num_error,
        )

    def _config_with_search_candidate(self, candidate: COMSearchCandidate) -> COMConfig:
        """
        Return a COMConfig copy with one 93A search candidate applied.

        This is a calculator-private helper because candidate-to-config mapping
        is part of the COM search flow, not a public module-level utility.
        """
        ft_cfg = self.cfg.filter
        new_filter = replace(
            ft_cfg,
            c_m2=candidate.c_m2,
            c_m1=candidate.c_m1,
            c_1=candidate.c_1,
            g_DC=candidate.g_DC,
            g_DC2=candidate.g_DC2,
        )
        return replace(self.cfg, filter=new_filter)

    @staticmethod
    def _search_row_from_status(
        idx: int,
        candidate: COMSearchCandidate,
        status: COMStatus,
    ) -> COMSearchRow:
        """Compress one candidate COMStatus into one search summary row."""
        if status.dfe is None or status.imp is None or status.FOM is None:
            raise ValueError("Search candidate status must include DFE, imp, and FOM.")

        imp = status.imp
        dfe = status.dfe
        return COMSearchRow(
            idx=idx,
            candidate=candidate,
            FOM=status.FOM,
            As=imp.As,
            sigma_ISI=imp.sigma_ISI,
            sigma_J=imp.sigma_J,
            sigma_XT=imp.sigma_XT,
            sigma_N=imp.sigma_N,
            sigma_TX=imp.sigma_TX,
            ts=dfe.ts,
            pos=dfe.pos,
        )

    @staticmethod
    def _select_search_rows(rows: list[COMSearchRow], search: COMSearchConfig) -> list[COMSearchRow]:
        """Keep all rows or the top-N successful rows according to search config."""
        if search.keep_all_rows:
            return rows
        ok_rows = [row for row in rows if row.status == "ok"]
        ok_rows.sort(key=lambda row: row.FOM, reverse=True)
        return ok_rows[:search.keep_top_n]

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format search progress duration for console messages."""
        seconds = max(0.0, float(seconds))
        if seconds < 60.0:
            return f"{seconds:.1f}s"
        minutes, sec = divmod(seconds, 60.0)
        if minutes < 60.0:
            return f"{int(minutes)}m {sec:.0f}s"
        hours, minutes = divmod(minutes, 60.0)
        return f"{int(hours)}h {int(minutes)}m {sec:.0f}s"

    def _validate_victim_time_alignment(self, victim: COMPath) -> None:
        """
        Guard victim H21/pulse against precursor wrap into the IFFT record tail.

        This check is intentionally applied to the victim path only. ISI and DFE
        are defined from the victim pulse response, while crosstalk paths use
        separate phase selection and should not inherit the victim main-cursor
        alignment contract.
        """
        victim.H_21.validate_aligned_ir(victim.H_21.ir, source_name="victim H_21 aligned_ir")
        victim.pulse.validate_aligned_ir(victim.pulse.ir, source_name="victim pulse aligned_ir")

    # ------------------
    # proxy
    # ------------------
    def _require_status(self) -> COMStatus:
        if self.status is None:
            raise RuntimeError("COM_93A status is not available. Run COM_93A.run() first.")
        if isinstance(self.status, COMSearchStatus):
            return self.status.best
        return self.status

    @property
    def report(self) -> COMReport:
        """COMReport view for plotting/debugging the current COM status."""
        return COMReport(self.cfg, self._require_status())

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
    def h_dsamp(self) -> np.ndarray:
        """Victim pulse response sampled at the selected DFE sampling phase."""
        dfe = self.dfe_status
        if dfe is None:
            raise RuntimeError("COM_93A.dfe_status is not available. Run COM_93A.run() first.")
        return self.h[dfe.pos::self.per_ui]

    @property
    def t_dsamp_ui(self) -> np.ndarray:
        """Discrete UI axis for h_dsamp and h_ISI, with main cursor at 0."""
        dfe = self.dfe_status
        if dfe is None:
            raise RuntimeError("COM_93A.dfe_status is not available. Run COM_93A.run() first.")
        num_pre = (dfe.ts - dfe.pos) // self.per_ui
        return np.arange(len(self.h_dsamp), dtype=float) - float(num_pre)

    @property
    def h_XT(self) -> list[np.ndarray]:
        """Crosstalk pulse responses h^(k)(t), k > 0."""
        return [path.pulse.ir for path in self.xtalks]

    @property
    def dfe_status(self) -> Optional[COMDFEStatus]:
        return self._require_status().dfe

    @property
    def imp_status(self) -> Optional[COMImpairmentStatus_93A]:
        return self._require_status().imp

    @property
    def pmf_status(self) -> Optional[COMPMFStatus]:
        return self._require_status().pmf

    def _h_j_ui_axis(self) -> np.ndarray:
        dfe = self.dfe_status
        if dfe is None:
            raise RuntimeError("COM_93A.dfe_status is not available. Run COM_93A.run() first.")

        pos = int(dfe.ts) % self.per_ui
        center_idx = np.arange(pos, len(self.h), self.per_ui)
        valid = (center_idx > 0) & (center_idx < len(self.h) - 1)
        center_idx = center_idx[valid]
        return (center_idx.astype(float) - float(dfe.ts)) / float(self.per_ui)

    def _plot_discrete_time_response(
        self,
        x_ui: np.ndarray,
        y: np.ndarray,
        title: str,
        ylabel: str,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
        filename: str = "discrete_response.png",
    ) -> Any:
        x_ui = np.asarray(x_ui, dtype=float)
        y = np.asarray(y, dtype=float)
        if x_ui.shape != y.shape:
            raise ValueError("x_ui and y must have the same shape.")
        if not np.all(np.isfinite(x_ui)) or not np.all(np.isfinite(y)):
            raise ValueError("x_ui and y must contain only finite values.")

        output_file = COMReport._plot_save_path(save_path, filename)
        created_ax = ax is None
        if created_ax:
            fig, ax = COMReport._subplots(output_file)
        else:
            fig = ax.figure

        ax.plot(x_ui, y, marker="o", markersize=3, linewidth=1.0, label=label)
        if label is not None:
            ax.legend()
        ax.set_title(title)
        ax.set_xlabel("Discrete time (UI, main cursor = 0)")
        ax.set_ylabel(ylabel)
        if xlim_ui is not None:
            ax.set_xlim(*xlim_ui)
        ax.grid(True)

        if output_file or created_ax:
            COMReport._finish_figure(fig, output_file)
        return ax

    def plot_h_dsamp(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        """
        Plot victim pulse samples at the selected DFE sampling phase.

        Parameters follow the utility plot style:
        ax is optional, save_path may be a file or directory, xlim_ui is in UI,
        and label is used when overlaying multiple curves.
        """
        return self.report.plot_h_dsamp(
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
        )

    def plot_h_ISI(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        """
        Plot residual ISI samples after DFE cancellation.

        Uses the same discrete UI axis as h_dsamp, with the main cursor at 0.
        """
        return self.report.plot_h_ISI(
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
        )

    def plot_h_J(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        """
        Plot sampled jitter sensitivity h_J on its actual finite-difference axis.
        """
        return self.report.plot_h_J(
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
        )

    # class methods
    def build_all_paths_93A(self) -> list[COMPath]:
        """
        Build all COM paths.

        LV-1 hierarchy:
        1. build channel-under-test models
        2. build path-shared models
        3. build every path-specific model
        """
        channels = _build_channel_under_test_93A(self.cfg.channel)
        shared = _build_shared_path_93A(self.cfg, channels[0].freqs)
        return _build_paths_93A(self.cfg, shared, channels)

    def find_pos_and_dfe_93A(self, h: np.ndarray) -> COMDFEStatus:
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
        ts, pos = _find_sampling_phase_93A(h, link_cfg, dfe_cfg)

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
            dfe_coeff_float = _calculate_float_dfe_93A(h_dsamp, dfe_cfg)    
            dfe_coeff = np.r_[
                dfe_coeff_fixed, 
                np.zeros(dfe_cfg.N_b-len(dfe_coeff_fixed)),
                dfe_coeff_float
            ]

        # step 4: calculate h_ISI
        h_ISI = _calculate_h_ISI_93A(h_dsamp, dfe_coeff)

        return COMDFEStatus(ts=ts, pos=pos, dfe_coeff=dfe_coeff, h_ISI=h_ISI)

    def calculate_imp_93A(
        self,
        h: np.ndarray,
        dfe_status: COMDFEStatus,
        h_XTs: list[np.ndarray],
    ) -> COMImpairmentStatus_93A:

        L = self.cfg.L
        link_cfg = self.cfg.link
        imp_cfg = self.cfg.imp
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
        h_J = _calculate_h_J_93A(h, ts, self.per_ui)
        sigma_J = np.sqrt( (imp_cfg.A_DD**2+imp_cfg.sigma_RJ**2) * sigma_X**2 * np.sum(h_J**2) )

        # sigma_XT
        var_XT = 0
        h_XTs_dsamp = []
        for h_XT in h_XTs:
            i, h_XT_dsamp = _find_pos_xtalk_93A(h_XT, self.per_ui) 
            var_XT += sigma_X**2 * np.sum(h_XT_dsamp**2)
            h_XTs_dsamp.append(h_XT_dsamp)
        sigma_XT = np.sqrt( var_XT )

        # sigma_N
        noise_psd = ContinuousPSD.from_constant(link_cfg.freqs, imp_cfg.eta_0)
        noise_filter = (
            _build_H_r_93A(link_cfg, ft_cfg)
            .cascade_tf(_build_H_ctf_93A(link_cfg, ft_cfg))
        )
        sigma_N = noise_psd.filtered_by(noise_filter).to_sigma()

        return COMImpairmentStatus_93A(
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

    def calculate_COM_93A(self, imp_status: COMImpairmentStatus_93A) -> COMPMFStatus:
        L = self.cfg.L
        As = imp_status.As
        imp_cfg = self.cfg.imp

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
        p_ISI = _build_pmf_interference_93A(
            p_sig, 
            imp_status.h_ISI, 
            pmf_cfg,
            name="ISI"
        )

        # Gaussian Noise pmf
        p_G = _build_pmf_G_93A(imp_status, imp_cfg, pmf_cfg)

        # Dual-Dirac jitter pmf
        p_DD = _build_pmf_interference_93A(
            p_sig, 
            imp_cfg.A_DD*imp_status.h_J, 
            pmf_cfg,
            name="Dual-Dirac"
        )

        # Xtalk pmf
        p_XT = _build_pmf_XT_all_93A(p_sig, imp_status.h_XTs_dsamp, pmf_cfg)
        
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

#%% 178A
@dataclass(repr=False)
class COMPkgConfig178A(_PrettyDataclass):
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
    L_s_seq: Sequence[float] | np.ndarray = ()     # unit: H, device termination series-inductance vector
    C_d_seq: Sequence[float] | np.ndarray = ()     # unit: F, device termination shunt-capacitance vector
    C_b: float = 0.0                               # unit: F, bump/interface capacitance
    C_p: float = 0.0                               # unit: F, package-to-board capacitance
    z_p_seq: Sequence[float] | np.ndarray = ()     # unit: mm, package TL stage lengths
    Z_c_seq: Sequence[float] | np.ndarray = ()     # unit: ohm, package TL stage differential impedances
    enable: bool = True                            # unit: boolean
    R0: float = 50.0                               # unit: ohm, single-ended reference resistance
    gamma0: float = 0.0                            # unit: 1/mm, package propagation coefficient term
    a1: float = float(1.734e-3)                    # unit: 93A package TL model coefficient
    a2: float = float(1.455e-4)                    # unit: 93A package TL model coefficient
    tau: float = float(6.141e-3)                   # unit: ns/mm, package TL delay coefficient

    def __post_init__(self) -> None:
        L = np.asarray(self.L_s_seq, dtype=float)
        C = np.asarray(self.C_d_seq, dtype=float)
        zp = np.asarray(self.z_p_seq, dtype=float)
        Zc = np.asarray(self.Z_c_seq, dtype=float)

        if L.ndim != 1 or C.ndim != 1:
            raise ValueError("L_s_seq and C_d_seq must be 1-D arrays.")
        if len(L) != len(C):
            raise ValueError(
                "L_s_seq and C_d_seq must have the same length. "
                f"Got len(L_s_seq)={len(L)}, len(C_d_seq)={len(C)}."
            )
        if zp.ndim != 1 or Zc.ndim != 1:
            raise ValueError("z_p_seq and Z_c_seq must be 1-D arrays.")
        if len(zp) != len(Zc):
            raise ValueError(
                "z_p_seq and Z_c_seq must have the same length. "
                f"Got len(z_p_seq)={len(zp)}, len(Z_c_seq)={len(Zc)}."
            )
        if self.enable and (len(L) == 0 or len(zp) == 0):
            raise ValueError("Enabled 178A package config requires at least one LC stage and one TL stage.")
        if np.any(L < 0.0) or np.any(C < 0.0):
            raise ValueError("L_s_seq and C_d_seq values must be non-negative.")
        if np.any(zp < 0.0) or np.any(Zc <= 0.0):
            raise ValueError("z_p_seq must be non-negative and Z_c_seq must be positive.")
        if self.C_b < 0.0 or self.C_p < 0.0:
            raise ValueError("C_b and C_p must be non-negative.")
        if self.R0 <= 0.0:
            raise ValueError("R0 must be positive.")

@dataclass(repr=False)
class COMFilterConfig178A(_PrettyDataclass):
    """
    178A filter configuration using internal formula units.

    TX FFE, transition-time filter, and receiver noise-filter fields intentionally
    keep the same names as the 93A config when the same helper contract is used.
    CTF fields use the 178A two-zero / three-pole naming.
    """
    c_m3: float = 0.0                # unit: dimensionless, TX FFE tap c(-3)
    c_m2: float = 0.0                # unit: dimensionless, TX FFE tap c(-2)
    c_m1: float = 0.0                # unit: dimensionless, TX FFE tap c(-1)
    c_1: float = 0.0                 # unit: dimensionless, TX FFE tap c(1)
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

    def __post_init__(self):
        self.c_0 = 1.0 - abs(self.c_m3) - abs(self.c_m2) - abs(self.c_m1) - abs(self.c_1)
        self.txfir = np.r_[self.c_m3, self.c_m2, self.c_m1, self.c_0, self.c_1]

@dataclass(repr=False)
class COMConfig178A(_PrettyDataclass):
    """Top-level 178A COM configuration grouped by function."""
    L: int                            # unit: levels, PAM order
    link: LinkConfig                  # unit contract: SI grid, Hz/s
    filter: COMFilterConfig178A       # unit contract: SI filter frequencies and 178A CTF terms
    channel: COMChannelConfig         # unit contract: Touchstone paths and S4P port order
    txpkg_victim: COMPkgConfig178A    # unit contract: 178A victim TX package
    txpkg_fext: COMPkgConfig178A      # unit contract: 178A FEXT aggressor TX package
    txpkg_next: COMPkgConfig178A      # unit contract: 178A NEXT aggressor TX package
    rxpkg: COMPkgConfig178A           # unit contract: 178A shared RX package
    dfe: COMDFEConfig                 # unit contract: DFE tap limits and spans
    imp: COMImpairmentConfig          # unit contract: V/UI/noise PSD units
    DER_0: float                      # unit: dimensionless, target detector error ratio
    pmf: COMPMFConfig = field(default_factory=COMPMFConfig) # unit contract: PMF amplitude grid and numerical controls

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

@dataclass(repr=False)
class COMImpairmentStatus_178A(_PrettyDataclass):
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

def _build_txpkg_178A(freqs: np.ndarray, txpkg_cfg: COMPkgConfig178A, *, isNext: bool = False) -> IEEECOMsparam:
    """
    Build the 178A TX package S-parameter model.

    The current 178A package contract is:
        device termination -> device package
    """
    freqs = LinkConfig.validate_freqs(freqs)
    if not txpkg_cfg.enable:
        return IEEECOMsparam.shunt_capacitance_93A(freqs, 0.0, txpkg_cfg.R0)

    S_td = IEEECOMsparam.device_termination_178A(
        freqs=freqs,
        L_seq=txpkg_cfg.L_s_seq,
        C_seq=txpkg_cfg.C_d_seq,
        bump_capacitance=txpkg_cfg.C_b,
        R0=txpkg_cfg.R0,
    )
    S_tp = IEEECOMsparam.device_package_178A(
        freqs=freqs,
        R0=txpkg_cfg.R0,
        package_capacitance=txpkg_cfg.C_p,
        zp_seq=txpkg_cfg.z_p_seq,
        Zc_seq=txpkg_cfg.Z_c_seq,
        gamma0=txpkg_cfg.gamma0,
        a1=txpkg_cfg.a1,
        a2=txpkg_cfg.a2,
        tau=txpkg_cfg.tau,
    )
    return S_td.cascade_com_93A(S_tp)

def _build_rxpkg_178A(freqs: np.ndarray, rxpkg_cfg: COMPkgConfig178A) -> IEEECOMsparam:
    """
    Build the 178A RX package S-parameter model.

    The current 178A package contract is:
        device package -> device termination
    """
    freqs = LinkConfig.validate_freqs(freqs)
    if not rxpkg_cfg.enable:
        return IEEECOMsparam.shunt_capacitance_93A(freqs, 0.0, rxpkg_cfg.R0)

    S_rp = IEEECOMsparam.device_package_178A(
        freqs=freqs,
        R0=rxpkg_cfg.R0,
        package_capacitance=rxpkg_cfg.C_p,
        zp_seq=rxpkg_cfg.z_p_seq,
        Zc_seq=rxpkg_cfg.Z_c_seq,
        gamma0=rxpkg_cfg.gamma0,
        a1=rxpkg_cfg.a1,
        a2=rxpkg_cfg.a2,
        tau=rxpkg_cfg.tau,
    )
    S_rd = IEEECOMsparam.device_termination_178A(
        freqs=freqs,
        L_seq=rxpkg_cfg.L_s_seq,
        C_seq=rxpkg_cfg.C_d_seq,
        bump_capacitance=rxpkg_cfg.C_b,
        R0=rxpkg_cfg.R0,
    )
    return S_rp.cascade_com_93A(S_rd)

def _build_H_ffe_178A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig178A) -> IEEECOMFilter:
    """Build the 178A victim/FEXT TX FFE filter."""
    return IEEECOMFilter.tx_ffe_93A(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)

def _build_H_ffe_next_178A(link_cfg: LinkConfig) -> IEEECOMFilter:
    """Build the 178A NEXT TX FFE filter."""
    ffe_next = np.array([0, 1, 0])
    return IEEECOMFilter.tx_ffe_93A(link_cfg, ffe_next, num_pre=1)

def _build_H_t_178A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig178A) -> IEEECOMFilter:
    """Build the 178A transmitter transition-time filter."""
    return IEEECOMFilter.transition_time_filter_93A(link_cfg, ft_cfg.Tr)

def _build_H_r_178A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig178A) -> IEEECOMFilter:
    """Build the 178A receiver noise filter."""
    return IEEECOMFilter.rx_noise_filter_93A(link_cfg, ft_cfg.fr)

def _build_H_ctf_178A(link_cfg: LinkConfig, ft_cfg: COMFilterConfig178A) -> IEEECOMFilter:
    """
    Build the 178A receiver equalizer / CTF filter.

    Maps COMFilterConfig178A directly to IEEECOMFilter.rx_equalizer_178A().
    """
    required = {
        "g_1": ft_cfg.g_1,
        "g_2": ft_cfg.g_2,
        "f_z1": ft_cfg.f_z1,
        "f_z2": ft_cfg.f_z2,
        "f_p1": ft_cfg.f_p1,
        "f_p2": ft_cfg.f_p2,
        "f_p3": ft_cfg.f_p3,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(
            "COMFilterConfig178A is missing required CTF fields: "
            + ", ".join(missing)
        )

    return IEEECOMFilter.rx_equalizer_178A(
        link_cfg,
        required["g_1"],
        required["g_2"],
        required["f_z1"],
        required["f_z2"],
        required["f_p1"],
        required["f_p2"],
        required["f_p3"],
    )

def _build_channel_under_test_178A(channel_cfg: COMChannelConfig) -> list[SparamModel]:
    """
    Build 178A measured-domain channel-under-test S-parameter models.

    Output contract mirrors _build_channel_under_test_93A():
    - index 0: victim
    - following indices: NEXT channels, then FEXT channels
    """
    return _build_channel_under_test_93A(channel_cfg)

def _build_path_178A(
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig178A,
    txpkg_cfg: COMPkgConfig178A,
    shared: COMSharedPath,
    kind: Literal["victim", "next", "fext"],
    S_ch: SparamModel,
) -> COMPath:
    """
    Build one 178A COM signal path from a measured-domain channel-under-test model.

    IO contract mirrors _build_path_93A() so COM_178A can reuse COMPath and
    COMReport while the package and CTF equations remain version-specific.
    """
    if not np.allclose(S_ch.freqs, shared.S_rx.freqs):
        raise ValueError("S_ch.freqs must match shared.S_rx.freqs for measured-domain cascade.")

    if kind == "next":
        S_tx = _build_txpkg_178A(S_ch.freqs, txpkg_cfg, isNext=True)
        H_ffe = shared.H_ffe_next
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_ne)
    elif kind == "fext":
        S_tx = _build_txpkg_178A(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_fe)
    elif kind == "victim":
        S_tx = _build_txpkg_178A(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_v)
    else:
        raise ValueError(f"Unsupported COM path kind: {kind}")

    S_all = S_tx.cascade_com_93A(S_ch).cascade_com_93A(shared.S_rx)
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

def _build_shared_path_178A(cfg: COMConfig178A, freqs: np.ndarray) -> COMSharedPath:
    """
    Build 178A path-shared COM models.

    The returned COMSharedPath keeps the same fields as 93A:
    H_ffe, H_ffe_next, H_t, S_rx, H_r, H_ctf.
    """
    link_cfg = cfg.link
    ft_cfg = cfg.filter
    return COMSharedPath(
        H_ffe=_build_H_ffe_178A(link_cfg, ft_cfg),
        H_ffe_next=_build_H_ffe_next_178A(link_cfg),
        H_t=_build_H_t_178A(link_cfg, ft_cfg),
        S_rx=_build_rxpkg_178A(freqs, cfg.rxpkg),
        H_r=_build_H_r_178A(link_cfg, ft_cfg),
        H_ctf=_build_H_ctf_178A(link_cfg, ft_cfg),
    )

def _build_paths_178A(
    cfg: COMConfig178A,
    shared: COMSharedPath,
    channels: list[SparamModel],
) -> list[COMPath]:
    """
    Build 178A path-specific COM models from aligned channel-under-test models.

    IO contract mirrors _build_paths_93A().
    """
    link_cfg = cfg.link
    ch_cfg = cfg.channel
    ft_cfg = cfg.filter

    expected_count = 1 + len(ch_cfg.next_s4p_paths) + len(ch_cfg.fext_s4p_paths)
    if len(channels) != expected_count:
        raise ValueError(
            "channels length must match victim + NEXT + FEXT path count. "
            f"Expected {expected_count}, got {len(channels)}."
        )

    paths = [
        _build_path_178A(
            link_cfg=link_cfg,
            channel_cfg=ch_cfg,
            ft_cfg=ft_cfg,
            txpkg_cfg=cfg.txpkg_victim,
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
            _build_path_178A(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                txpkg_cfg=cfg.txpkg_next,
                shared=shared,
                kind="next",
                S_ch=S_ch,
            )
        )

    for S_ch in fext_channels:
        paths.append(
            _build_path_178A(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                txpkg_cfg=cfg.txpkg_fext,
                shared=shared,
                kind="fext",
                S_ch=S_ch,
            )
        )

    return paths

def _calculate_float_dfe_178A(h_dsamp: np.ndarray, dfe_cfg: COMDFEConfig) -> np.ndarray:
    """Calculate 178A floating DFE coefficients from downsampled victim pulse."""
    raise NotImplementedError("_calculate_float_dfe_178A() skeleton is defined; implement 178A floating DFE.")

def _calculate_h_ISI_178A(h_dsamp: np.ndarray, dfe_coeff: np.ndarray) -> np.ndarray:
    """Calculate 178A residual ISI vector."""
    raise NotImplementedError("_calculate_h_ISI_178A() skeleton is defined; implement 178A residual ISI.")

def _find_sampling_phase_178A(
    h: np.ndarray,
    link_cfg: LinkConfig,
    dfe_cfg: COMDFEConfig,
) -> tuple[int, int]:
    """
    Find 178A sampling instant and phase.

    Returns
    -------
    tuple[int, int]
        (ts, pos), where ts is the sample index on link_cfg.times and pos is
        the sample phase index in [0, link_cfg.per_ui).
    """
    raise NotImplementedError("_find_sampling_phase_178A() skeleton is defined; implement 178A sampling phase.")

def _build_rx_noise_psd_178A(link_cfg: LinkConfig, imp_cfg: COMImpairmentConfig, ft_cfg: COMFilterConfig178A) -> SampledPSD:
    S_rn_broadband = ContinuousPSD.from_constant(link_cfg.freqs, imp_cfg.eta_0)
    H_rn = _build_H_r_178A(link_cfg, ft_cfg).cascade_tf(_build_H_ctf_178A(link_cfg, ft_cfg))
    S_rn_filtered = S_rn_broadband.filtered_by(H_rn)
    return S_rn_filtered.to_sampled(link_cfg.fb, link_cfg.theta)

def _find_pos_xtalk_178A(h_XT: np.ndarray, per_ui: int) -> tuple[int, np.ndarray]:
    """Find 178A crosstalk sampling phase and downsampled crosstalk response."""
    return _find_pos_xtalk_93A(h_XT, per_ui)

def _build_xtalk_psd_178A(h_XTs: list[np.ndarray], link_cfg: LinkConfig, sigma_x: float) -> SampledPSD:

    # spec defined psd constant = sigma_x^2/fb in continuous-time two-sided domain
    # converting to discrete-time one-sided doamin: constant = sigma_x^2/fb * (fb/2*pi) * 2
    S_xn_base = SampledPSD.from_constant(link_cfg.theta, (sigma_x**2/np.pi), link_cfg.fb)

    # initialized with psd_constant = 0.0
    S_xn_all = SampledPSD.from_constant(link_cfg.theta, 0.0, link_cfg.fb)
    for h_XT in h_XTs:
        _, h_XT_dsamp = _find_pos_xtalk_178A(h_XT, link_cfg.per_ui)
        H_xn = SampledResponse.from_ir(h_XT_dsamp, link_cfg)
        S_xn_temp = S_xn_base.filtered_by(H_xn)
        S_xn_all = S_xn_all.add(S_xn_temp)

    return S_xn_all

def _calculate_h_J_178A(h: np.ndarray, ts: int, per_ui: int) -> np.ndarray:
    """Calculate 178A sampled jitter sensitivity."""
    raise NotImplementedError("_calculate_h_J_178A() skeleton is defined; implement 178A jitter sensitivity.")


def _build_pmf_interference_178A(
    p_sig: Pmf1D,
    h: np.ndarray,
    pmf_cfg: COMPMFRuntimeConfig,
    name: Optional[str] = None,
) -> Pmf1D:
    """Build one 178A interference PMF component."""
    raise NotImplementedError("_build_pmf_interference_178A() skeleton is defined; implement 178A PMF interference.")

def _build_pmf_G_178A(
    imp_stat: COMImpairmentStatus,
    imp_cfg: COMImpairmentConfig,
    pmf_cfg: COMPMFRuntimeConfig,
) -> Pmf1D:
    """Build the 178A Gaussian/noise PMF component."""
    raise NotImplementedError("_build_pmf_G_178A() skeleton is defined; implement 178A Gaussian/noise PMF.")

def _build_pmf_XT_all_178A(
    p_sig: Pmf1D,
    h_XTs: list[np.ndarray],
    pmf_cfg: COMPMFRuntimeConfig,
) -> Pmf1D:
    """Build combined 178A crosstalk PMF."""
    raise NotImplementedError("_build_pmf_XT_all_178A() skeleton is defined; implement 178A XT PMF.")

def _calculate_FOM_178A(imp_status: COMImpairmentStatus) -> float:
    """Calculate 178A FOM/search metric from impairment status."""
    raise NotImplementedError("_calculate_FOM_178A() skeleton is defined; implement 178A FOM/search metric.")

class COM_178A(COM_93A):
    """
    IEEE 802.3 Annex 178A COM calculator.

    Class boundary
    --------------
    COM_178A owns the versioned 178A algorithm pipeline:
    - build_all_paths_178A()
    - find_pos_and_dfe_178A()
    - calculate_imp_178A()
    - calculate_COM_178A()

    This class intentionally reuses COM_93A's shared proxy/report/search shell
    where possible, but all spec-defined calculation steps are routed to 178A
    method names. The path-building stage is wired; DFE, impairment, FOM, and
    PMF stages remain explicit skeletons until the 178A equations are filled in.
    """

    def __init__(self, cfg: COMConfig178A):
        self.cfg = cfg
        self.status: Optional[COMStatus | COMSearchStatus] = None

    def _run_once(self, *, calculate_pmf: bool = True) -> COMStatus:
        """
        Run one concrete 178A COMConfig point.

        Pipeline shape mirrors COM_93A:
        paths -> DFE/sample phase -> imp -> FOM -> optional PMF/COM.
        """
        paths = self.build_all_paths_178A()
        self._validate_victim_time_alignment(paths[0])
        dfe_status = self.find_pos_and_dfe_178A(h=paths[0].pulse.ir)
        imp_status = self.calculate_imp_178A(
            h=paths[0].pulse.ir,
            dfe_status=dfe_status,
            h_XTs=[path.pulse.ir for path in paths[1:]],
        )
        FOM = _calculate_FOM_178A(imp_status)
        pmf_status = self.calculate_COM_178A(imp_status) if calculate_pmf else None
        return COMStatus(paths=paths, dfe=dfe_status, imp=imp_status, pmf=pmf_status, FOM=FOM)

    def _require_status(self) -> COMStatus:
        if self.status is None:
            raise RuntimeError("COM_178A status is not available. Run COM_178A.run() first.")
        if isinstance(self.status, COMSearchStatus):
            return self.status.best
        return self.status

    def _run_search(self, search: COMSearchConfig) -> COMSearchStatus:
        """
        Run 178A search skeleton.

        The search shell mirrors COM_93A, but candidate execution uses
        COM_178A._run_once().
        """
        candidates = search.candidates(self.cfg.filter)
        total = len(candidates)
        rows: list[COMSearchRow] = []
        best_row: Optional[COMSearchRow] = None
        best_cfg: Optional[COMConfig] = None
        num_error = 0
        start_time = time.perf_counter()
        last_print_time = start_time
        print(f"COM 178A search started: {total} candidates")

        for idx, candidate in enumerate(candidates):
            candidate_cfg = self._config_with_search_candidate(candidate)
            try:
                candidate_status = COM_178A(candidate_cfg)._run_once(calculate_pmf=False)
                row = self._search_row_from_status(idx, candidate, candidate_status)
            except Exception as exc:
                if not search.continue_on_error:
                    raise
                num_error += 1
                row = COMSearchRow(
                    idx=idx,
                    candidate=candidate,
                    FOM=float("-inf"),
                    status="error",
                    error=str(exc),
                )
                rows.append(row)
                continue

            rows.append(row)
            if best_row is None or row.FOM > best_row.FOM:
                best_row = row
                best_cfg = candidate_cfg

            now = time.perf_counter()
            done = idx + 1
            should_print = done == total or done == 1 or done % 10 == 0 or (now - last_print_time) >= 5.0
            if should_print:
                elapsed = now - start_time
                rate = done / elapsed if elapsed > 0.0 else float("nan")
                remaining = (total - done) / rate if np.isfinite(rate) and rate > 0.0 else float("nan")
                percent = 100.0 * done / total if total > 0 else 100.0
                best_text = "n/a" if best_row is None else f"{best_row.FOM:.3f} dB @ {best_row.idx}"
                print(
                    "COM 178A search progress: "
                    f"{done}/{total} ({percent:.1f}%), "
                    f"elapsed={self._format_duration(elapsed)}, "
                    f"eta={self._format_duration(remaining)}, "
                    f"best_FOM={best_text}"
                )
                last_print_time = now

        if best_row is None or best_cfg is None:
            raise RuntimeError("COM 178A search did not produce any successful candidate.")

        print(f"COM 178A search best candidate: idx={best_row.idx}, FOM={best_row.FOM:.3f} dB")
        print("Computing full PMF/COM for best 178A candidate...")
        best_status = COM_178A(best_cfg)._run_once(calculate_pmf=True)
        elapsed_total = time.perf_counter() - start_time
        print(
            "COM 178A search completed: "
            f"elapsed={self._format_duration(elapsed_total)}, "
            f"best_COM={best_status.pmf.COM if best_status.pmf is not None else 'n/a'}"
        )
        return COMSearchStatus(
            best=best_status,
            best_row=best_row,
            rows=self._select_search_rows(rows, search),
            num_candidates=len(candidates),
            num_success=len(candidates) - num_error,
            num_error=num_error,
        )

    def _config_with_search_candidate(self, candidate: COMSearchCandidate) -> COMConfig178A:
        """
        Return a COMConfig178A copy with one search candidate applied.

        The current shared COMSearchCandidate uses the 93A names g_DC/g_DC2.
        For 178A these two search gains map to the 178A CTF fields g_1/g_2.
        """
        ft_cfg = self.cfg.filter
        new_filter = replace(
            ft_cfg,
            c_m2=candidate.c_m2,
            c_m1=candidate.c_m1,
            c_1=candidate.c_1,
            g_1=candidate.g_DC,
            g_2=candidate.g_DC2,
        )
        return replace(self.cfg, filter=new_filter)

    def build_all_paths_178A(self) -> list[COMPath]:
        """
        Build all 178A COM paths.

        LV-1 hierarchy mirrors COM_93A:
        1. build channel-under-test models
        2. build path-shared models
        3. build every path-specific model
        """
        channels = _build_channel_under_test_178A(self.cfg.channel)
        shared = _build_shared_path_178A(self.cfg, channels[0].freqs)
        return _build_paths_178A(self.cfg, shared, channels)

    def find_pos_and_dfe_178A(self, h: np.ndarray) -> COMDFEStatus:
        """
        Find 178A sampling phase and DFE coefficients.

        Parameters
        ----------
        h:
            Victim pulse response in V, sampled on self.cfg.link time grid.
        """
        raise NotImplementedError("find_pos_and_dfe_178A() skeleton is defined; implement 178A DFE/sampling flow.")

    def calculate_imp_178A(
        self,
        h_XTs: list[np.ndarray],
    ) -> COMImpairmentStatus_178A:
        """
        Calculate 178A impairment status.

        Parameters
        ----------
        h:
            Victim pulse response in V.
        dfe_status:
            178A DFE/sampling result.
        h_XTs:
            Crosstalk pulse responses in V.
        """
        link_cfg = self.cfg.link
        imp_cfg = self.cfg.imp
        ft_cfg = self.cfg.filter
        L = self.cfg.L

        # sigma_x
        sigma_X = np.sqrt( (L**2 - 1) / (3 * (L-1)**2) )

        # psd
        S_rn = _build_rx_noise_psd_178A(link_cfg, imp_cfg, ft_cfg)
        S_xn_all = _build_xtalk_psd_178A(h_XTs, link_cfg, sigma_X)
        raise NotImplementedError(
            "calculate_imp_178A() currently builds S_rn and S_xn_all; "
            "complete the 178A impairment scalar/status calculations before returning COMImpairmentStatus_178A."
        )

    def calculate_COM_178A(self, imp_status: COMImpairmentStatus) -> COMPMFStatus:
        """
        Calculate 178A final PMF/COM result from impairment status.

        Parameters
        ----------
        imp_status:
            178A impairment status.
        """
        raise NotImplementedError("calculate_COM_178A() skeleton is defined; implement 178A PMF/COM flow.")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]

    # Project-owned COM input workbook.
    config_path = project_root / "cases" / "c2m_8023dj_4p13p0_50mm" / "config.xlsx"

    # Choose one mode:
    # - "single": use fixed_config only and export one full debug/study status
    # - "search": use fixed_config + search_config and export search result + best status
    run_mode = "search"

    if run_mode == "single":
        cfg = excel_to_config(str(config_path))
        output_path = project_root / "reports" / "single_run"
        config_outputs = cfg.export(str(output_path))

        status = COM_93A(cfg).run()
        outputs = status.export(str(output_path), include_plots=False)
        outputs.update(status.export_report_summary(str(output_path)))
        COMReport(cfg, status).plot_single_run(str(output_path / "plots"), path_idx=0)
        outputs["plots"] = str(output_path / "plots")
        outputs.update(config_outputs)

        print("COM single run completed")
        print(f"config: {config_path}")
        print(f"output: {output_path}")
        print(f"FOM: {status.FOM}")
        if status.pmf is not None:
            print(f"COM: {status.pmf.COM}")
        print(outputs)
    elif run_mode == "search":
        cfg = excel_to_config(str(config_path))
        search = excel_to_search_config(str(config_path))
        output_path = project_root / "reports" / "search_run"
        config_outputs = cfg.export(str(output_path))

        search_status = COM_93A(cfg).run(search)
        outputs = search_status.export(str(output_path), include_plots=False)
        outputs.update(search_status.best.export_report_summary(str(output_path / "best")))
        COMReport(cfg, search_status).plot_search_run(str(output_path / "plots"))
        outputs["plots"] = str(output_path / "plots")
        outputs.update(config_outputs)

        print("COM search run completed")
        print(f"config: {config_path}")
        print(f"output: {output_path}")
        print(f"best FOM: {search_status.best.FOM}")
        if search_status.best.pmf is not None:
            print(f"best COM: {search_status.best.pmf.COM}")
        print(outputs)
    else:
        raise ValueError(f"Unsupported run_mode: {run_mode!r}. Use 'single' or 'search'.")
