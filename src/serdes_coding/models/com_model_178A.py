"""
IEEE 802.3 Annex 178A COM model.

Public names in this module do not need a version suffix because the module
namespace already defines the spec version. This module owns the 178A-specific
configuration, root status, PSD/DTE helpers, and COM pipeline. Temporary shared
leaf primitives imported from ``com_model_93A.py`` are enumerated below.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import combinations, product
from pathlib import Path
import sys
from time import perf_counter
from typing import Any, Literal, Optional, Sequence
import numpy as np
from scipy.signal import lfilter

try:
    from ..utilities.link import ContinuousPSD, GridOverflowError, LinkConfig, LinkSegment, SampledPSD, SampledResponse
    from ..utilities.sparam import SparamModel
    from ..utilities.pmf import Pmf1D
    from ..search.com_search_178A import COMSearchRow, COMSearchStatus, run_full_search
    from .com_dataclass_text import COMDataclassText, TextField, TextSection
    from . import com_model_93A as com_93A
except ImportError:
    # Support direct interactive execution of this canonical module.
    # Package execution continues to use the relative imports above.
    source_root = str(Path(__file__).resolve().parents[2])
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from serdes_coding.utilities.link import ContinuousPSD, GridOverflowError, LinkConfig, LinkSegment, SampledPSD, SampledResponse
    from serdes_coding.utilities.sparam import SparamModel
    from serdes_coding.utilities.pmf import Pmf1D
    from serdes_coding.search.com_search_178A import COMSearchRow, COMSearchStatus, run_full_search
    from serdes_coding.models.com_dataclass_text import COMDataclassText, TextField, TextSection
    from serdes_coding.models import com_model_93A as com_93A

# 178A temporarily reuses these leaf data-flow primitives. Versioned config,
# text presentation, impairment status, PSD, DTE, root status, and COM pipeline
# definitions live here; shared-leaf ownership is reviewed independently.
COMChannelConfig = com_93A.COMChannelConfig
COMPMFConfig = com_93A.COMPMFConfig
COMPMFRuntimeConfig = com_93A.COMPMFRuntimeConfig
COMPMFStatus = com_93A.COMPMFStatus
COMPath = com_93A.COMPath
COMSearchCandidate = com_93A.COMSearchCandidate
COMSearchConfig = com_93A.COMSearchConfig
_build_channel_under_test_93A = com_93A._build_channel_under_test_93A
_build_pmf_interference_93A = com_93A._build_pmf_interference_93A
_build_pmf_XT_all_93A = com_93A._build_pmf_XT_all_93A
_find_pos_xtalk_93A = com_93A._find_pos_xtalk_93A


class COMError(RuntimeError):
    """Base error for a COM calculation that cannot produce a valid result."""


class COMMainCursorError(COMError):
    """Raised when a sampled or equalized response violates the main-cursor contract."""


class COMTxfirMainCursorError(COMError):
    """Raised when a TX FFE candidate cannot keep c(0) as the main cursor."""


class COMLengthMismatchError(COMError):
    """Raised when a COM calculation violates an array-length contract.

    This includes incompatible model arrays, path counts, sampled response
    lengths, and other shape contracts at the COM boundary.
    """


def _validate_positive_main_cursor(h_dsamp: np.ndarray, *, source_name: str, pos: int) -> None:
    """Require the dominant sampled input cursor to have positive polarity."""
    h_dsamp = np.asarray(h_dsamp, dtype=float)
    peak_index = int(np.argmax(np.abs(h_dsamp)))
    if h_dsamp[peak_index] <= 0.0:
        raise COMMainCursorError(
            f"{source_name} main cursor has non-positive polarity at pos={pos}: "
            f"index={peak_index}, value={h_dsamp[peak_index]:.6e}."
        )

class IEEECOMSparam(com_93A.IEEECOMSparam):
    """
    IEEE COM-specific S-parameter model builder.

    Class boundary
    --------------
    IEEECOMSparam owns S-parameter networks generated from IEEE COM equations.

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
    def device_termination(
        cls,
        freqs: np.ndarray,
        R0: float,
        dt_cfg: COMDeviceTermConfig,
    ) -> 'IEEECOMSparam':
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
        R0:
            Single-ended reference resistance in ohm.
        dt_cfg:
            Device termination configuration. It owns the stage-aligned L/C
            vectors and the bump/interface capacitance.

        Returns
        -------
        IEEECOMSparam
            Cascaded N-stage LC ladder as a differential 2-port Sdd model.
        """
        if not isinstance(dt_cfg, COMDeviceTermConfig):
            raise TypeError("dt_cfg must be a COMDeviceTermConfig.")

        # initialized with C_b
        S_d = cls.shunt_capacitance_93A(freqs, dt_cfg.C_b, R0)

        # build LC ladder in reverse order
        for l, c in zip(dt_cfg.L_s_seq[::-1], dt_cfg.C_d_seq[::-1]):
            S_C_temp = cls.shunt_capacitance_93A(freqs, c, R0)
            S_L_temp = cls.series_inductance_93A(freqs, l, R0)
            S_temp = S_C_temp.cascade_com_93A(S_L_temp)
            S_d = S_temp.cascade_com_93A(S_d)
            
        return S_d

    @classmethod
    def device_package(
        cls,
        freqs: np.ndarray,
        R0: float,
        dp_cfg: COMDevicePackageConfig,
    ) -> 'IEEECOMSparam':
        """
        Build the 178A device package S-parameter model.

        Reference:
        - IEEE 802.3 Annex 178A, Eq. 178A-9.

        Model convention
        ----------------
        The model is represented as a package-side shunt capacitance followed
        by N transmission-line stages. COMDevicePackageConfig normalizes the
        propagation parameters to one value per transmission-line stage.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        R0:
            Single-ended reference resistance in ohm.
        dp_cfg:
            Device package configuration. It owns package capacitance and all
            stage-aligned transmission-line parameters.

        Returns
        -------
        IEEECOMSparam
            Cascaded N-stage package TL as a differential 2-port Sdd model.
        """
        if not isinstance(dp_cfg, COMDevicePackageConfig):
            raise TypeError("dp_cfg must be a COMDevicePackageConfig.")

        # initialized with C_p
        S_p = cls.shunt_capacitance_93A(freqs, dp_cfg.C_p, R0)

        # build N-stage package transmission lines in reverse order
        for z_p, Z_c, gamma_0, a1, a2, tau in zip(
            dp_cfg.z_p_seq[::-1],
            dp_cfg.Z_c_seq[::-1],
            dp_cfg.gamma_0[::-1],
            dp_cfg.a1[::-1],
            dp_cfg.a2[::-1],
            dp_cfg.tau[::-1],
        ):
            S_temp = cls.pkg_trans_line_93A(
                freqs,
                R0,
                z_p,
                Zc=Z_c,
                gamma0=gamma_0,
                a1=a1,
                a2=a2,
                tau=tau,
            )
            S_p = S_temp.cascade_com_93A(S_p)

        return S_p

    @classmethod
    def partial_host_channel(
        cls,
        freqs: np.ndarray,
        R0: float,
        ph_cfg: COMPartialHostConfig,
    ) -> 'IEEECOMSparam':
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
        ph_cfg:
            Partial host channel configuration. When ``enable`` is False,
            return the identity two-port without a partial host block.

        Returns
        -------
        IEEECOMSparam
            Synthetic partial host channel as a differential 2-port Sdd model.
        """
        if not isinstance(ph_cfg, COMPartialHostConfig):
            raise TypeError("ph_cfg must be a COMPartialHostConfig.")
        if not ph_cfg.enable:
            return cls.shunt_capacitance_93A(freqs, 0.0, R0)

        S_0 = cls.shunt_capacitance_93A(freqs, ph_cfg.C_0, R0)
        S_h = cls.pkg_trans_line_93A(
            freqs,
            R0,
            ph_cfg.z_h,
            Zc=ph_cfg.Z_h,
            gamma0=ph_cfg.gamma_0,
            a1=ph_cfg.a1,
            a2=ph_cfg.a2,
            tau=ph_cfg.tau,
        )
        S_1 = cls.shunt_capacitance_93A(freqs, ph_cfg.C_1, R0)
        return (S_0.cascade_com_93A(S_h)).cascade_com_93A(S_1)

@dataclass(frozen=True, repr=False)
class COMBilinearCTLE(COMDataclassText):
    """Two-section digital CTLE used by the 178A reference pulse branch."""

    b1: np.ndarray
    a1: np.ndarray
    b2: np.ndarray
    a2: np.ndarray
    Fs: float

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Digital realization", (
                self._field("Fs", "sample rate", stored_unit="Hz", display_unit="GHz", scale=1e-9),
                self._field("b1", "section 1 numerator", stored_unit="dimensionless"),
                self._field("a1", "section 1 denominator", stored_unit="dimensionless"),
                self._field("b2", "section 2 numerator", stored_unit="dimensionless"),
                self._field("a2", "section 2 denominator", stored_unit="dimensionless"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (self._field("Fs", "sample rate", stored_unit="Hz", display_unit="GHz", scale=1e-9),)

    def __post_init__(self) -> None:
        for name in ("b1", "a1", "b2", "a2"):
            value = np.asarray(getattr(self, name), dtype=float)
            if value.ndim != 1 or value.size == 0 or not np.all(np.isfinite(value)):
                raise ValueError(f"COMBilinearCTLE.{name} must be a finite 1-D array.")
            value = value.copy()
            value.setflags(write=False)
            object.__setattr__(self, name, value)
        if not np.isfinite(float(self.Fs)) or float(self.Fs) <= 0.0:
            raise ValueError("COMBilinearCTLE.Fs must be finite and positive.")
        object.__setattr__(self, "Fs", float(self.Fs))

    def filtered(self, ir: np.ndarray) -> np.ndarray:
        """Apply both causal IIR sections with zero initial state."""
        ir = np.asarray(ir, dtype=float)
        if ir.ndim != 1 or not np.all(np.isfinite(ir)):
            raise ValueError("COMBilinearCTLE input must be a finite 1-D array.")
        return np.asarray(
            lfilter(self.b2, self.a2, lfilter(self.b1, self.a1, ir)),
            dtype=float,
        )


class IEEECOMFilter(com_93A.IEEECOMFilter):
    """
    IEEE 802.3 Annex 93A COM-specific scalar filter builders.

    Class boundary
    --------------
    IEEECOMFilter owns scalar transfer-function blocks defined by COM equations.
    The FFT/grid convention and scalar response conversion remain in
    LinkSegment.
    """

    @classmethod
    def _from_finite_record_ir(
        cls,
        ir: np.ndarray,
        cfg: LinkConfig,
    ) -> "IEEECOMFilter":
        """Store an intentional finite FFT record without causality correction.

        The reference bilinear-CTLE path keeps the raw IFFT record when
        causality enforcement is disabled.  This model-local constructor keeps
        that behavior out of the general ``LinkSegment.from_ir()`` contract.
        """
        segment = cls(cfg)
        record = segment.validate_ir(ir, correct_wrap=False)
        segment._raw_ir = record
        segment._causal_ir = record
        segment._causal_shift_samples = 0
        segment._ir = record
        return segment

    @classmethod
    def rx_equalizer(
        cls,
        cfg: LinkConfig,
        g_1: float,
        g_2: float,
        f_z1: float,
        f_z2: float,
        f_p1: float,
        f_p2: float,
        f_p3: float | None = None,
    ) -> 'IEEECOMFilter':
        """
        Build the 178A receiver equalizer transfer function.

        The IO uses the 178A spec-facing two-zero / three-pole names. When
        mapped from the aligned 93A Ad Hoc form, ``f_z2`` and ``f_p3`` both
        receive ``f_HP_PZ`` so they represent the same low-frequency term.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid in Hz.
        g_1, g_2:
            178A CTF gain terms in dB.
        f_z1, f_z2:
            178A CTF zero frequencies in Hz.
        f_p1, f_p2:
            Required CTF pole frequencies in Hz.
        f_p3:
            Optional third pole frequency in Hz. ``None`` bypasses this pole.
        """
        f = cfg.freqs
        pole_values = (f_p1, f_p2) if f_p3 is None else (f_p1, f_p2, f_p3)
        if any(float(value) <= 0.0 or not np.isfinite(float(value)) for value in pole_values):
            raise ValueError("CTF pole frequencies must be finite and positive.")
        denom = np.ones_like(f, dtype=complex)
        for pole in pole_values:
            denom *= 1 + 1j * f / float(pole)
        H_ctf = (
            (10**(g_1 / 20) + 1j * f / f_z1)
            * (10**(g_2 / 20) + 1j * f / f_z2)
            / denom
        )
        return cls.from_tf(f, H_ctf, cfg)

    @staticmethod
    def _bilinear_section_coefficients(
        cfg: LinkConfig,
        *,
        f_z: float,
        f_p1: float,
        g_dc: float,
        f_p2: Optional[float] = None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Build one causal CTLE section using the MATLAB TD_CTLE mapping."""
        values = {"f_z": f_z, "f_p1": f_p1}
        if f_p2 is not None:
            values["f_p2"] = f_p2
        if any(not np.isfinite(float(value)) or float(value) <= 0.0 for value in values.values()):
            raise ValueError("Bilinear CTLE frequencies must be finite and positive.")
        if not np.isfinite(float(g_dc)):
            raise ValueError("Bilinear CTLE gain must be finite.")

        K = 2.0 * float(cfg.Fs)
        p1 = -2.0 * np.pi * float(f_p1)
        zero = -2.0 * np.pi * float(f_z) * 10.0 ** (float(g_dc) / 20.0)
        p1d = (K + p1) / (K - p1)
        zd = (K + zero) / (K - zero)

        if f_p2 is None:
            # Exact f_p2 -> infinity limit of MATLAB TD_CTLE. The common
            # z=-1 pole/zero pair cancels, leaving this first-order section.
            gain = (K - zero) / (K - p1) * float(f_p1) / float(f_z)
            b = gain * np.array([1.0, -zd], dtype=float)
            a = np.array([1.0, -p1d], dtype=float)
        else:
            p2 = -2.0 * np.pi * float(f_p2)
            p2d = (K + p2) / (K - p2)
            kd = (
                (K - zero)
                / ((K - p1) * (K - p2))
                * float(f_p1)
                / float(f_z)
            )
            b = (-p2) * kd * np.poly([zd, -1.0])
            a = np.poly([p1d, p2d])

        poles = np.roots(a)
        if not np.all(np.isfinite(poles)) or np.any(np.abs(poles) >= 1.0):
            raise ValueError("Bilinear CTLE section must have poles inside the unit circle.")
        return np.asarray(b, dtype=float), np.asarray(a, dtype=float)

    @classmethod
    def apply_rx_equalizer_bilinear(
        cls,
        ir: np.ndarray,
        cfg: LinkConfig,
        *,
        g_1: float,
        g_2: float,
        f_z1: float,
        f_z2: float,
        f_p1: float,
        f_p2: float,
        f_p3: float,
    ) -> np.ndarray:
        """Apply two CTLE IIR sections to a normalized discrete-time kernel."""
        ir = np.asarray(ir, dtype=float)
        if ir.ndim != 1 or ir.size != cfg.Nfft or not np.all(np.isfinite(ir)):
            raise ValueError("Bilinear CTLE input must be a finite full-grid discrete kernel.")
        b1, a1 = cls._bilinear_section_coefficients(
            cfg, f_z=f_z1, f_p1=f_p1, f_p2=f_p2, g_dc=g_1
        )
        b2, a2 = cls._bilinear_section_coefficients(
            cfg, f_z=f_z2, f_p1=f_p3, g_dc=g_2
        )
        return COMBilinearCTLE(b1=b1, a1=a1, b2=b2, a2=a2, Fs=cfg.Fs).filtered(ir)

    @classmethod
    def build_rx_equalizer_bilinear(
        cls,
        cfg: LinkConfig,
        *,
        g_1: float,
        g_2: float,
        f_z1: float,
        f_z2: float,
        f_p1: float,
        f_p2: float,
        f_p3: float,
    ) -> COMBilinearCTLE:
        """Build the shared two-section digital CTLE for one candidate."""
        b1, a1 = cls._bilinear_section_coefficients(
            cfg, f_z=f_z1, f_p1=f_p1, f_p2=f_p2, g_dc=g_1
        )
        b2, a2 = cls._bilinear_section_coefficients(
            cfg, f_z=f_z2, f_p1=f_p3, g_dc=g_2
        )
        return COMBilinearCTLE(b1=b1, a1=a1, b2=b2, a2=a2, Fs=cfg.Fs)


@dataclass(repr=False)
class COMSharedPath(COMDataclassText, com_93A.COMSharedPath):
    """178A shared path with an optional digital CTLE pulse model."""

    ctle_iir: Optional[COMBilinearCTLE] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Shared filters", (
                self._field("H_ffe", "TX FFE response", stored_unit="dimensionless", summary="shape"),
                self._field("H_ffe_next", "NEXT TX FFE response", stored_unit="dimensionless", summary="shape"),
                self._field("H_t", "transition-time response", stored_unit="dimensionless", summary="shape"),
                self._field("S_rx", "RX package network", stored_unit="S-parameter", summary="shape"),
                self._field("H_r", "receiver noise filter", stored_unit="dimensionless", summary="shape"),
                self._field("H_ctf", "CTLE response", stored_unit="dimensionless", summary="shape"),
                self._field("ctle_iir", "bilinear CTLE realization", stored_unit="status"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("H_ffe", "TX FFE response", stored_unit="dimensionless", summary="shape"),
            self._field("ctle_iir", "bilinear CTLE realization", stored_unit="status"),
        )

# =========================================
# 178A configs, integrated to COMConfig
# =========================================

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

# =========================================
# 178A configs, integrated to COMConfig
# =========================================

@dataclass(repr=False)
class COMPSDStatus(COMDataclassText):
    """
    178A PSD-domain status.

    This class stores PSD objects, integrated sigma values, and PSD-derived
    scalar metadata. It should not store sampled response sequences; h_xx
    vectors belong to COMEqChannelStatus.
    """
    As: Optional[float] = None
    sigma_X: Optional[float] = None
    S_rn: Optional[SampledPSD] = None
    sigma_rn: Optional[float] = None
    S_xn: Optional[SampledPSD] = None
    sigma_xn: Optional[float] = None
    S_tn: Optional[SampledPSD] = None
    sigma_tn: Optional[float] = None
    S_jn: Optional[SampledPSD] = None
    sigma_jn: Optional[float] = None
    S_qn: Optional[SampledPSD] = None
    sigma_qn: Optional[float] = None
    S_total: Optional[SampledPSD] = None
    sigma_total: Optional[float] = None
    R_n: Optional[np.ndarray] = None
    sigma_G: Optional[float] = None
    sigma_ISI: Optional[float] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Signal", (
                self._field("As", "signal amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("sigma_X", "crosstalk sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("sigma_G", "Gaussian impairment sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("sigma_ISI", "ISI sigma", stored_unit="V", display_unit="mV", scale=1e3),
            )),
            TextSection("Noise components", (
                self._field("S_rn", "receiver noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_rn", "receiver noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_xn", "crosstalk PSD", stored_unit="V^2/Hz"),
                self._field("sigma_xn", "crosstalk sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_tn", "transmitter noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_tn", "transmitter noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_jn", "jitter noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_jn", "jitter noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_qn", "quantization noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_qn", "quantization noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_total", "total noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_total", "total noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("R_n", "noise autocorrelation", stored_unit="V^2", display_unit="mV^2", scale=1e6),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("As", "signal amplitude", stored_unit="V", display_unit="mV", scale=1e3),
            self._field("sigma_total", "total noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
        )


@dataclass(repr=False)
class COMAddedNoiseIterationStatus(COMDataclassText):
    """One scalar observation from the Annex 178A added-noise solver."""

    iteration: int
    phase: Literal["baseline", "bracket", "bisection"]
    g_an: float
    sigma_added: float
    sigma_an: float
    A_an: float
    delta_com_an_temp: float
    residual_dB: float

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Iteration", (
                self._field("iteration", "iteration", stored_unit="count"),
                self._field("phase", "solver phase", stored_unit="status"),
                self._field("g_an", "added-noise scale", stored_unit="dimensionless"),
                self._field("sigma_added", "added sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("sigma_an", "total added-noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("A_an", "added-noise amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("delta_com_an_temp", "temporary delta COM", stored_unit="dB"),
                self._field("residual_dB", "calibration residual", stored_unit="dB"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("iteration", "iteration", stored_unit="count"),
            self._field("phase", "solver phase", stored_unit="status"),
            self._field("residual_dB", "calibration residual", stored_unit="dB"),
        )


@dataclass(repr=False)
class COMAddedNoiseStatus(COMDataclassText):
    """178A.1.10.1 added-noise calibration result shared by MLSD stages."""
    g_an: float
    S_an: SampledPSD
    sigma_an: float
    p_an: Pmf1D
    delta_com_an_temp: float
    target_delta_com_an: Optional[float] = None
    residual_dB: Optional[float] = None
    iterations: Optional[int] = None
    sigma_added: Optional[float] = None
    A_ref: Optional[float] = None
    A_an: Optional[float] = None
    iteration_history: list[COMAddedNoiseIterationStatus] = field(default_factory=list)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Calibration result", (
                self._field("g_an", "added-noise scale", stored_unit="dimensionless"),
                self._field("sigma_an", "added-noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("A_an", "added-noise amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("A_ref", "reference amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("sigma_added", "added sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("delta_com_an_temp", "achieved delta COM", stored_unit="dB"),
                self._field("target_delta_com_an", "target delta COM", stored_unit="dB"),
                self._field("residual_dB", "calibration residual", stored_unit="dB"),
                self._field("iterations", "iterations", stored_unit="count"),
            )),
            TextSection("Distribution", (
                self._field("S_an", "added-noise PSD", stored_unit="V^2/Hz"),
                self._field("p_an", "added-noise PMF", stored_unit="probability mass"),
                self._field("iteration_history", "iteration history", stored_unit="record count", summary="count"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("g_an", "added-noise scale", stored_unit="dimensionless"),
            self._field("residual_dB", "calibration residual", stored_unit="dB"),
            self._field("iterations", "iterations", stored_unit="count"),
        )


@dataclass(repr=False)
class COMMLSDNoiseStatus(COMDataclassText):
    """Eq. (178A-54) PSD and autocorrelation, before DER evaluation."""
    S_isi: SampledPSD
    sigma_isi: float
    S_ni: SampledPSD
    sigma_ni: float
    R_ni: np.ndarray
    S_qn: Optional[SampledPSD] = None
    sigma_qn: Optional[float] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("MLSD noise", (
                self._field("S_isi", "ISI PSD", stored_unit="V^2/Hz"),
                self._field("sigma_isi", "ISI sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_ni", "MLSD input-noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_ni", "MLSD input-noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("R_ni", "MLSD noise autocorrelation", stored_unit="V^2", display_unit="mV^2", scale=1e6),
                self._field("S_qn", "MLSD quantization PSD", stored_unit="V^2/Hz"),
                self._field("sigma_qn", "MLSD quantization sigma", stored_unit="V", display_unit="mV", scale=1e3),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("sigma_isi", "ISI sigma", stored_unit="V", display_unit="mV", scale=1e3),
            self._field("sigma_ni", "MLSD input-noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
        )


@dataclass(repr=False)
class COMMLSDStatus(COMDataclassText):
    """MLSD-only inputs and results, separate from physical impairment stages."""
    added_noise: COMAddedNoiseStatus
    S_isi: Optional[SampledPSD] = None
    sigma_isi: Optional[float] = None
    S_qn: Optional[SampledPSD] = None
    sigma_qn: Optional[float] = None
    S_ni: Optional[SampledPSD] = None
    sigma_ni: Optional[float] = None
    R_ni: Optional[np.ndarray] = None
    der_by_j: Optional[np.ndarray] = None
    DER_MLSD_raw_sequence: Optional[float] = None
    DER_MLSD: Optional[float] = None
    DER_MLSD_reported: Optional[float] = None
    A_MLSD: Optional[float] = None
    delta_COM: Optional[float] = None
    COM_MLSD_raw: Optional[float] = None
    COM_MLSD: Optional[float] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Added noise", (
                self._field("added_noise", "added-noise calibration", stored_unit="status"),
            )),
            TextSection("Noise model", (
                self._field("S_isi", "ISI PSD", stored_unit="V^2/Hz"),
                self._field("sigma_isi", "ISI sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_qn", "quantization PSD", stored_unit="V^2/Hz"),
                self._field("sigma_qn", "quantization sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("S_ni", "MLSD input-noise PSD", stored_unit="V^2/Hz"),
                self._field("sigma_ni", "MLSD input-noise sigma", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("R_ni", "MLSD noise autocorrelation", stored_unit="V^2", display_unit="mV^2", scale=1e6),
            )),
            TextSection("Detector result", (
                self._field("der_by_j", "DER contribution by sequence length", stored_unit="dimensionless probability"),
                self._field("DER_MLSD_raw_sequence", "raw sequence DER", stored_unit="dimensionless probability"),
                self._field("DER_MLSD", "selected DER", stored_unit="dimensionless probability"),
                self._field("DER_MLSD_reported", "reported DER", stored_unit="dimensionless probability"),
                self._field("A_MLSD", "MLSD amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("delta_COM", "MLSD COM increment", stored_unit="dB"),
                self._field("COM_MLSD_raw", "raw COM MLSD", stored_unit="dB"),
                self._field("COM_MLSD", "reported COM MLSD", stored_unit="dB"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("delta_COM", "MLSD COM increment", stored_unit="dB"),
            self._field("COM_MLSD", "reported COM MLSD", stored_unit="dB"),
        )


@dataclass(repr=False)
class COMEqChannelStatus(COMDataclassText):
    """
    178A equivalent-channel status.

    Contract: only sampled response / equivalent-channel sequences named h_xx
    are stored here. PSD objects and scalar sigma values belong to COMPSDStatus.
    """
    # pre-dte
    h_dsamp: Optional[SampledResponse] = None
    h_tn: Optional[SampledResponse] = None
    h_J: Optional[SampledResponse] = None
    h_XTs_dsamp: Optional[list[SampledResponse]] = None

    # post-ffe
    h_ISI: Optional[SampledResponse] = None
    h_w_J: Optional[SampledResponse] = None
    h_w: Optional[SampledResponse] = None
    h_XTs_w: Optional[list[SampledResponse]] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Pre-DTE responses", (
                self._field("h_dsamp", "sampled victim response", stored_unit="V"),
                self._field("h_tn", "transmitter-noise response", stored_unit="V"),
                self._field("h_J", "jitter response", stored_unit="V/UI"),
                self._field("h_XTs_dsamp", "sampled crosstalk responses", stored_unit="V", summary="count"),
            )),
            TextSection("Post-FFE responses", (
                self._field("h_ISI", "ISI response", stored_unit="V"),
                self._field("h_w_J", "equalized jitter response", stored_unit="V/UI"),
                self._field("h_w", "equalized victim response", stored_unit="V"),
                self._field("h_XTs_w", "equalized crosstalk responses", stored_unit="V", summary="count"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("h_dsamp", "sampled victim response", stored_unit="V"),
            self._field("h_w", "equalized victim response", stored_unit="V"),
        )
    

@dataclass(repr=False)
class COMAdcInputPMF(COMDataclassText):
    """
    178A ADC-input PMF intermediate status.

    This object records PMF-side intermediate data used to determine ADC
    quantization/clipping values before building S_qn.
    """
    p_sig: Optional[Pmf1D] = None
    p_s: Optional[Pmf1D] = None
    p_XT: Optional[Pmf1D] = None
    p_DD: Optional[Pmf1D] = None
    p_ga: Optional[Pmf1D] = None
    p_n: Optional[Pmf1D] = None
    p_sn: Optional[Pmf1D] = None
    V_qc: Optional[float] = None
    delta: Optional[float] = None
    method: Optional[str] = None
    clipping_convention: Optional[str] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("PMF components", (
                self._field("p_sig", "signal PMF", stored_unit="probability mass"),
                self._field("p_s", "signal-plus-ISI PMF", stored_unit="probability mass"),
                self._field("p_XT", "crosstalk PMF", stored_unit="probability mass"),
                self._field("p_DD", "deterministic-jitter PMF", stored_unit="probability mass"),
                self._field("p_ga", "Gaussian approximation PMF", stored_unit="probability mass"),
                self._field("p_n", "noise PMF", stored_unit="probability mass"),
                self._field("p_sn", "combined signal-and-noise PMF", stored_unit="probability mass"),
            )),
            TextSection("ADC result", (
                self._field("V_qc", "clipping voltage", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("delta", "quantization step", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("method", "PMF construction method", stored_unit="policy"),
                self._field("clipping_convention", "clipping convention", stored_unit="policy"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("V_qc", "clipping voltage", stored_unit="V", display_unit="mV", scale=1e3),
            self._field("delta", "quantization step", stored_unit="V", display_unit="mV", scale=1e3),
            self._field("method", "PMF construction method", stored_unit="policy"),
        )

@dataclass(repr=False)
class COMImpStageStatus(COMDataclassText):
    """One 178A impairment stage's PSD, equivalent-channel, and ADC material."""
    psd: Optional[COMPSDStatus] = None
    adc_input: Optional[COMAdcInputPMF] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Stage outputs", (
                self._field("psd", "PSD status", stored_unit="status"),
                self._field("adc_input", "ADC-input PMF status", stored_unit="status"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("psd", "PSD status", stored_unit="status", summary="stage"),
            self._field("adc_input", "ADC-input PMF status", stored_unit="status", summary="stage"),
        )

@dataclass(repr=False)
class COMImpairmentStatus(COMDataclassText):
    """
    178A impairment status grouped by receiver-processing stage.

    Each stage stores its own PSD objects, equivalent-channel sequences, and
    ADC-input PMF material. ``pre_dte`` is the selected sampling-phase result;
    the phase-independent pre-DTE cache is intentionally run-local.
    """
    pre_dte: Optional[COMImpStageStatus] = None
    post_ffe: Optional[COMImpStageStatus] = None
    eq_ch: Optional[COMEqChannelStatus] = None
    H_rxffe: Optional[SampledResponse] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Stage lifecycle", (
                self._field("pre_dte", "pre-DTE impairments", stored_unit="status"),
                self._field("post_ffe", "post-FFE impairments", stored_unit="status"),
                self._field("eq_ch", "equivalent-channel responses", stored_unit="status"),
                self._field("H_rxffe", "RX FFE response", stored_unit="dimensionless"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("pre_dte", "pre-DTE impairments", stored_unit="status", summary="stage"),
            self._field("post_ffe", "post-FFE impairments", stored_unit="status", summary="stage"),
            self._field("eq_ch", "equivalent-channel responses", stored_unit="status", summary="stage"),
        )
    
    def _stages(self) -> tuple[COMImpStageStatus, ...]:
        return tuple(
            stage
            for stage in (self.post_ffe, self.pre_dte)
            if stage is not None
        )

    def _psd_attr(self, name: str) -> Any:
        for stage in self._stages():
            if stage.psd is not None:
                value = getattr(stage.psd, name, None)
                if value is not None:
                    return value
        raise AttributeError(f"{type(self).__name__}.{name} is not available.")

    def _eq_attr(self, name: str) -> Any:
        if self.eq_ch is not None:
            value = getattr(self.eq_ch, name, None)
            if value is not None:
                return value
        raise AttributeError(f"{type(self).__name__}.{name} is not available.")

    @property
    def adc_input_pmf(self) -> COMAdcInputPMF:
        """Compatibility proxy; final DFE data takes precedence over pre-DTE data."""
        for stage in self._stages():
            if stage.adc_input is not None:
                return stage.adc_input
        raise AttributeError(f"{type(self).__name__}.adc_input_pmf is not available.")

    @property
    def w_lim(self) -> SampledResponse:
        """Post-FFE sampled response proxy for the limited receiver FFE."""
        if self.H_rxffe is None:
            raise AttributeError(f"{type(self).__name__}.H_rxffe is not available.")
        return self.H_rxffe

    @property
    def sigma_X(self) -> float:
        return self._psd_attr("sigma_X")

    @property
    def S_rn(self) -> SampledPSD:
        return self._psd_attr("S_rn")

    @property
    def sigma_rn(self) -> float:
        return self._psd_attr("sigma_rn")

    @property
    def sigma_N(self) -> float:
        """Legacy proxy for `sigma_rn` used by shared 93A report/search code."""
        return self.sigma_rn

    @property
    def S_xn(self) -> SampledPSD:
        return self._psd_attr("S_xn")

    @property
    def sigma_xn(self) -> float:
        return self._psd_attr("sigma_xn")

    @property
    def sigma_XT(self) -> float:
        """Legacy proxy for `sigma_xn` used by shared 93A report/search code."""
        return self.sigma_xn

    @property
    def pos(self) -> int:
        return self._psd_attr("pos")

    @property
    def ts(self) -> int:
        return self._psd_attr("ts")

    @property
    def As(self) -> float:
        return self._psd_attr("As")

    @property
    def S_tn(self) -> SampledPSD:
        return self._psd_attr("S_tn")

    @property
    def sigma_tn(self) -> float:
        return self._psd_attr("sigma_tn")

    @property
    def S_jn(self) -> SampledPSD:
        return self._psd_attr("S_jn")

    @property
    def sigma_jn(self) -> float:
        return self._psd_attr("sigma_jn")

    @property
    def sigma_J(self) -> float:
        """Legacy proxy for `sigma_jn` used by shared 93A report/search code."""
        return self.sigma_jn

    @property
    def S_qn(self) -> SampledPSD:
        return self._psd_attr("S_qn")

    @property
    def sigma_qn(self) -> float:
        return self._psd_attr("sigma_qn")

    @property
    def S_total(self) -> SampledPSD:
        return self._psd_attr("S_total")

    @property
    def sigma_total(self) -> float:
        return self._psd_attr("sigma_total")

    @property
    def R_n(self) -> np.ndarray:
        return self._psd_attr("R_n")

    @property
    def sigma_G(self) -> float:
        return self._psd_attr("sigma_G")

    @property
    def sigma_ISI(self) -> float:
        return self._psd_attr("sigma_ISI")

    @property
    def h_dsamp(self) -> SampledResponse:
        return self._eq_attr("h_dsamp")

    @property
    def h_tn(self) -> SampledResponse:
        return self._eq_attr("h_tn")

    @property
    def h_J(self) -> SampledResponse:
        return self._eq_attr("h_J")

    @property
    def h_XTs_dsamp(self) -> list[SampledResponse]:
        return self._eq_attr("h_XTs_dsamp")

    @property
    def h_w(self) -> SampledResponse:
        return self._eq_attr("h_w")

    @property
    def h_XTs_w(self) -> list[SampledResponse]:
        return self._eq_attr("h_XTs_w")

    @property
    def h_ISI(self) -> SampledResponse:
        return self._eq_attr("h_ISI")

    @property
    def h_w_J(self) -> SampledResponse:
        return self._eq_attr("h_w_J")

@dataclass(repr=False)
class COMDTEStatus(COMDataclassText):
    """
    178A receiver discrete-time equalizer result for one sampling phase.
    """
    ts: int                         # unit: sample index on cfg.times
    pos: int                        # unit: sample phase index, 0 <= pos < per_ui
    d: int
    w_lim: np.ndarray             # unit: dimensionless, raw zero-filled FFE taps, shape (N_max,)
    b_lim: np.ndarray             # unit: dimensionless, DFE coefficients b
    mse: float                      # unit: V^2, mean-square error from 178A-35
    H_all: np.ndarray 
    Rnn_all: np.ndarray 
    pruned_index: np.ndarray         # unit: tap index, selected FFE tap index vector i
    H: np.ndarray 
    R_nn: np.ndarray 
    H_b: np.ndarray

    # without limter results
    w: np.ndarray                  # unit: dimensionless, raw zero-filled unlimited FFE taps, shape (N_max,)
    b: np.ndarray

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Sampling", (
                self._field("pos", "sampling phase", stored_unit="sample index"),
                self._field("ts", "main cursor location", stored_unit="sample index"),
                self._field("d", "decision delay", stored_unit="UI"),
            )),
            TextSection("Limited MMSE solution", (
                self._field("mse", "mean-square error", stored_unit="V^2", display_unit="mV^2", scale=1e6),
                self._field("w_lim", "FFE coefficients", stored_unit="dimensionless"),
                self._field("b_lim", "DFE coefficients", stored_unit="dimensionless"),
                self._field("pruned_index", "selected FFE indices", stored_unit="tap index"),
            )),
            TextSection("Unlimited solution", (
                self._field("w", "unlimited FFE coefficients", stored_unit="dimensionless"),
                self._field("b", "unlimited DFE coefficients", stored_unit="dimensionless"),
            )),
            TextSection("Solver matrices", (
                self._field("H_all", "full channel matrix", stored_unit="V", summary="shape"),
                self._field("Rnn_all", "full noise covariance", stored_unit="V^2", summary="shape"),
                self._field("H", "selected channel matrix", stored_unit="V", summary="shape"),
                self._field("R_nn", "selected noise covariance", stored_unit="V^2", summary="shape"),
                self._field("H_b", "DFE channel matrix", stored_unit="V", summary="shape"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("pos", "sampling phase", stored_unit="sample index"),
            self._field("ts", "main cursor location", stored_unit="sample index"),
            self._field("mse", "mean-square error", stored_unit="V^2"),
            self._field("w_lim", "FFE coefficients", stored_unit="dimensionless", summary="shape"),
            self._field("b_lim", "DFE coefficients", stored_unit="dimensionless", summary="shape"),
        )

    @property
    def dfe_coeff(self) -> np.ndarray:
        """Compatibility proxy for report code that plots feedback taps."""
        return self.b_lim


@dataclass(repr=False)
class COMRunStatus(COMDataclassText):
    """Runtime records collected while one concrete 178A COM point is evaluated."""
    pmf_grid_quality: Optional[str] = None
    pmf_keep_mass: Optional[float] = None
    mse_by_pos: list[Optional[float]] = field(default_factory=list)
    main_cursor_error_by_pos: list[Optional[str]] = field(default_factory=list)
    coarse_pos: list[int] = field(default_factory=list)
    fine_pos: list[int] = field(default_factory=list)

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Resolved precision", (
                self._field("pmf_grid_quality", "PMF grid quality", stored_unit="policy"),
                self._field("pmf_keep_mass", "retained PMF mass", stored_unit="dimensionless probability"),
            )),
            TextSection("Sampling sweep", (
                self._field("mse_by_pos", "MSE by phase", stored_unit="V^2"),
                self._field("main_cursor_error_by_pos", "main-cursor errors", stored_unit="status"),
                self._field("coarse_pos", "coarse phases", stored_unit="sample index"),
                self._field("fine_pos", "fine phases", stored_unit="sample index"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("pmf_grid_quality", "PMF grid quality", stored_unit="policy"),
            self._field("mse_by_pos", "MSE by phase", stored_unit="V^2", summary="count"),
        )


@dataclass(repr=False)
class COMStatus(COMDataclassText):
    """Standalone 178A COM status in stage-execution order."""
    paths: list[COMPath] = field(default_factory=list)
    run: Optional[COMRunStatus] = None
    dte: Optional[COMDTEStatus] = None
    imp: Optional[COMImpairmentStatus] = None
    pmf: Optional[COMPMFStatus] = None
    mlsd: Optional[COMMLSDStatus] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        selected = ()
        if self.dte is not None:
            selected += (
                TextField("dte.pos", "sampling phase", self.dte.pos, "sample index"),
                TextField("dte.ts", "main cursor location", self.dte.ts, "sample index"),
                TextField("dte.mse", "mean-square error", self.dte.mse, "V^2", "mV^2", 1e6),
            )
        if self.pmf is not None:
            selected += (TextField("pmf.COM", "COM DFE", self.pmf.COM, "dB"),)
        if self.mlsd is not None:
            selected += (
                TextField("mlsd.delta_COM", "MLSD COM increment", self.mlsd.delta_COM, "dB"),
                TextField("mlsd.COM_MLSD", "COM MLSD", self.mlsd.COM_MLSD, "dB"),
            )
        if not selected:
            selected = (TextField("final_COM", "final COM", self.final_COM, "dB"),)
        return (
            TextSection("Pipeline state", (
                self._field("paths", "channel paths", stored_unit="path count", summary="count"),
                self._field("run", "run records", stored_unit="status", summary="stage"),
                self._field("dte", "DTE stage", stored_unit="status", summary="stage"),
                self._field("imp", "impairment stage", stored_unit="status", summary="stage"),
                self._field("pmf", "PMF stage", stored_unit="status", summary="stage"),
                self._field("mlsd", "MLSD stage", stored_unit="status", summary="stage"),
            )),
            TextSection("Selected result", selected),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("paths", "channel paths", stored_unit="path count", summary="count"),
            self._field("dte", "DTE stage", stored_unit="status", summary="stage"),
            TextField("final_COM", "final COM", self.final_COM, "dB"),
        )

    @property
    def victim(self) -> COMPath:
        return self.paths[0]

    @property
    def xtalks(self) -> list[COMPath]:
        return self.paths[1:]

    @property
    def final_COM(self) -> Optional[float]:
        """Return the selected MLSD result when available, else COM_DFE."""
        if self.mlsd is not None and self.mlsd.COM_MLSD is not None:
            return self.mlsd.COM_MLSD
        return None if self.pmf is None else self.pmf.COM

    def export(self, save_path: str) -> dict[str, str]:
        """Export 178A status data without invoking a report renderer.

        The inherited 93A exporter assumes the flat 93A impairment contract,
        including ``imp.sigma_TX``. 178A impairment data is grouped by stage,
        so top-K finalization must use a 178A-specific export boundary.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = out_dir / "status_summary.txt"
        summary_path.write_text(str(self), encoding="utf-8")
        return {"status_summary_txt": str(summary_path)}


# ----------------------------------------
# bulid_all_paths(): private helpers
# ----------------------------------------

def _build_txpkg(freqs: np.ndarray, txpkg_cfg: COMPkgConfig, *, isNext: bool = False) -> IEEECOMSparam:
    """
    Build the 178A TX package S-parameter model.

    The current 178A package contract is:
        device termination -> device package -> partial host channel
    """
    freqs = LinkConfig.validate_freqs(freqs)
    S_td = IEEECOMSparam.device_termination(
        freqs=freqs,
        R0=txpkg_cfg.R0,
        dt_cfg=txpkg_cfg.device_term,
    )
    S_tp = IEEECOMSparam.device_package(
        freqs=freqs,
        R0=txpkg_cfg.R0,
        dp_cfg=txpkg_cfg.device_pkg,
    )
    S_th = IEEECOMSparam.partial_host_channel(
        freqs=freqs,
        R0=txpkg_cfg.R0,
        ph_cfg=txpkg_cfg.partial_host,
    )
    return S_td.cascade_com_93A(S_tp).cascade_com_93A(S_th)

def _build_rxpkg(freqs: np.ndarray, rxpkg_cfg: COMPkgConfig) -> IEEECOMSparam:
    """
    Build the 178A RX package S-parameter model.

    Build in die-to-channel order, then exchange the completed two-port's
    ports so the returned model is oriented channel-to-die.
    """
    freqs = LinkConfig.validate_freqs(freqs)
    S_rh = IEEECOMSparam.partial_host_channel(
        freqs=freqs,
        R0=rxpkg_cfg.R0,
        ph_cfg=rxpkg_cfg.partial_host,
    )
    S_rp = IEEECOMSparam.device_package(
        freqs=freqs,
        R0=rxpkg_cfg.R0,
        dp_cfg=rxpkg_cfg.device_pkg,
    )
    S_rd = IEEECOMSparam.device_termination(
        freqs=freqs,
        R0=rxpkg_cfg.R0,
        dt_cfg=rxpkg_cfg.device_term,
    )
    S_rx_die_to_channel = S_rd.cascade_com_93A(S_rp).cascade_com_93A(S_rh)
    return S_rx_die_to_channel.reverse_ports()

def _build_H_ffe(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """Build the 178A victim/FEXT TX FFE filter."""
    ft_cfg.validate_txfir_main_cursor()
    return IEEECOMFilter.tx_ffe_93A(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)

def _build_H_ffe_next(link_cfg: LinkConfig) -> IEEECOMFilter:
    """Build the 178A NEXT TX FFE filter."""
    ffe_next = np.array([0, 1, 0])
    return IEEECOMFilter.tx_ffe_93A(link_cfg, ffe_next, num_pre=1)

def _build_H_t(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """Build the 178A transmitter transition-time filter."""
    return IEEECOMFilter.transition_time_filter_93A(link_cfg, ft_cfg.Tr)

def _build_H_r(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """Build the 178A receiver noise filter."""
    return IEEECOMFilter.rx_noise_filter_93A(link_cfg, ft_cfg.fr)

def _build_H_ctf(link_cfg: LinkConfig, ft_cfg: COMFilterConfig) -> IEEECOMFilter:
    """
    Build the 178A receiver equalizer / CTF filter.

    Maps COMFilterConfig178A directly to IEEECOMFilter.rx_equalizer().
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

    return IEEECOMFilter.rx_equalizer(
        link_cfg,
        required["g_1"],
        required["g_2"],
        required["f_z1"],
        required["f_z2"],
        required["f_p1"],
        required["f_p2"],
        required["f_p3"],
    )


def _reference_fd_to_td_record(
    measured_freqs: np.ndarray,
    measured_tf: np.ndarray,
    link_cfg: LinkConfig,
    *,
    relative_truncation_threshold: float = 1e-3,
) -> np.ndarray:
    """Realize the reference raw-IFFT finite record consumed by TD CTLE.

    This is the fixed numerical definition of ``bilinear_iir``: retain the
    measured frequency spacing, interpolate magnitude and unwrapped phase onto
    the nearest compatible Nyquist grid, zero above the measured band, perform
    a raw Hermitian IFFT with no causality correction, then retain through the
    last sample above 0.1% of the impulse peak.
    """
    freqs = LinkConfig.validate_freqs(measured_freqs)
    response = np.asarray(measured_tf, dtype=complex)
    if response.shape != freqs.shape or not np.all(np.isfinite(response)):
        raise ValueError("measured CTLE input TF must be finite and match its frequency grid.")
    if len(freqs) < 3:
        raise ValueError("reference FD-to-TD realization requires at least three frequency points.")

    measured_df = float(freqs[2] - freqs[1])
    if measured_df <= 0.0:
        raise ValueError("reference FD-to-TD realization requires positive frequency spacing.")
    n_steps = max(1, int(np.floor(link_cfg.f_nyq / measured_df + 0.5)))
    output_freqs = np.arange(n_steps + 1, dtype=float) * (link_cfg.f_nyq / n_steps)

    magnitude = np.abs(response)
    phase = np.unwrap(np.angle(response))
    if freqs[0] > 0.0:
        low_count = min(10, len(freqs))
        magnitude_at_dc = float(np.polyval(np.polyfit(freqs[:low_count], magnitude[:low_count], 1), 0.0))
        freqs = np.r_[0.0, freqs]
        magnitude = np.r_[max(magnitude_at_dc, np.finfo(float).eps), magnitude]
        phase = np.r_[0.0, phase]

    in_band = output_freqs <= freqs[-1]
    interpolated = np.zeros(output_freqs.shape, dtype=complex)
    magnitude_i = np.interp(output_freqs[in_band], freqs, magnitude)
    phase_i = np.interp(output_freqs[in_band], freqs, phase)
    interpolated[in_band] = magnitude_i * np.exp(1j * phase_i)
    interpolated[0] = interpolated[0].real + 0j
    interpolated[-1] = interpolated[-1].real + 0j

    raw_record = np.fft.irfft(interpolated, n=2 * n_steps)
    peak = float(np.max(np.abs(raw_record)))
    retained = np.flatnonzero(np.abs(raw_record) > peak * relative_truncation_threshold)
    if len(retained) == 0:
        return raw_record[:1].copy()
    return raw_record[: int(retained[-1]) + 1].copy()


def _evaluate_pre_ctle_on_measured_grid(
    S_all: SparamModel,
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig,
    *,
    kind: Literal["victim", "next", "fext"],
    include_txffe: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Build the composite pre-CTLE TF on the measured S-parameter grid."""
    freqs = S_all.freqs
    H_21 = S_all.voltage_transfer_function(
        gamma_src=channel_cfg.gamma_src,
        gamma_load=channel_cfg.gamma_load,
    )
    if not include_txffe:
        txfir = np.array([1.0])
        num_pre = 0
    elif kind == "next":
        txfir = np.array([0.0, 1.0, 0.0])
        num_pre = 1
    else:
        txfir = np.asarray(ft_cfg.txfir, dtype=float)
        num_pre = int(ft_cfg.num_pre)
    H_ffe = np.zeros_like(freqs, dtype=complex)
    for tap_index, coefficient in enumerate(txfir):
        # Eq. 178A-13: the main cursor is n=0 at tap index num_pre.
        n = tap_index - num_pre
        H_ffe += coefficient * np.exp(-1j * 2.0 * np.pi * n * freqs / link_cfg.fb)

    # Eq. 93A-46 reused by 178A for transmitter transition time.
    H_t = np.exp(-2.0 * (np.pi * freqs * ft_cfg.Tr / 1.6832) ** 2)
    # Eq. 178A receiver-noise bandwidth response (shared 93A-20 primitive).
    ratio = freqs / ft_cfg.fr
    H_r = 1.0 / (
        1.0 - 3.414214 * ratio**2 + ratio**4
        + 1j * 2.613126 * (ratio - ratio**3)
    )
    # The reference FD-to-TD realization carries the transition filter's 3Tr
    # time origin.  This is a pure delay, not a separately selectable filter.
    time_origin = np.exp(-1j * 2.0 * np.pi * freqs * (3.0 * ft_cfg.Tr))
    return freqs, H_ffe * H_t * H_21 * H_r * time_origin


def _realize_ctle_response(
    pre_ctle: LinkSegment,
    H_ctf: LinkSegment,
    link_cfg: LinkConfig,
    realization: Literal["continuous_tf", "bilinear_iir"],
    ctle_iir: Optional[COMBilinearCTLE],
    *,
    measured_freqs: Optional[np.ndarray] = None,
    measured_tf: Optional[np.ndarray] = None,
) -> tuple[LinkSegment, Literal["frequency_tf", "finite_record_ir"]]:
    """Realize only the CTLE output from an already-built pre-CTLE response.

    TX FFE, channel/package cascade, receiver filtering, and symbol-pulse
    formation are outside this boundary.  The returned domain tag tells the
    common symbol-pulse helper how to preserve the selected realization's
    numerical convolution semantics.
    """
    if realization == "continuous_tf":
        return pre_ctle.cascade_tf(H_ctf), "frequency_tf"
    if realization != "bilinear_iir":
        raise ValueError("CTLE pulse realization must be continuous_tf or bilinear_iir.")
    if ctle_iir is None:
        raise ValueError("bilinear_iir realization requires shared.ctle_iir.")
    if not np.isclose(ctle_iir.Fs, link_cfg.Fs, rtol=0.0, atol=0.0):
        raise ValueError("shared.ctle_iir sample rate must match LinkConfig.Fs.")
    if measured_freqs is None or measured_tf is None:
        raise ValueError("bilinear_iir realization requires the measured pre-CTLE TF.")
    discrete_kernel = _reference_fd_to_td_record(
        measured_freqs,
        measured_tf,
        link_cfg,
    )
    ctle_ir = ctle_iir.filtered(discrete_kernel)
    ctle_record = np.zeros(link_cfg.Nfft, dtype=float)
    if len(ctle_ir) > link_cfg.Nfft:
        raise COMLengthMismatchError(
            "bilinear CTLE finite record exceeds LinkConfig.Nfft: "
            f"len={len(ctle_ir)}, Nfft={link_cfg.Nfft}."
        )
    ctle_record[:len(ctle_ir)] = ctle_ir * link_cfg.Fs
    return IEEECOMFilter._from_finite_record_ir(ctle_record, link_cfg), "finite_record_ir"


def _apply_rectangular_unit_pulse(
    post_ctle: LinkSegment,
    X: LinkSegment,
    link_cfg: LinkConfig,
    amplitude: float,
    domain: Literal["frequency_tf", "finite_record_ir"],
) -> LinkSegment:
    """Apply the common one-UI rectangular symbol pulse after CTLE realization."""
    if domain == "frequency_tf":
        return post_ctle.cascade_tf(X)
    if domain != "finite_record_ir":
        raise ValueError("CTLE response domain must be frequency_tf or finite_record_ir.")
    discrete_kernel = post_ctle.ir / link_cfg.Fs
    support = np.flatnonzero(discrete_kernel != 0.0)
    discrete_kernel = (
        discrete_kernel[: int(support[-1]) + 1]
        if len(support)
        else discrete_kernel[:1]
    )
    pulse_ir = lfilter(
        np.ones(link_cfg.per_ui, dtype=float),
        np.array([1.0]),
        discrete_kernel,
    ) * float(amplitude)
    pulse_record = np.zeros(link_cfg.Nfft, dtype=float)
    if len(pulse_ir) > link_cfg.Nfft:
        raise COMLengthMismatchError(
            "bilinear CTLE symbol pulse exceeds LinkConfig.Nfft: "
            f"len={len(pulse_ir)}, Nfft={link_cfg.Nfft}."
        )
    pulse_record[:len(pulse_ir)] = pulse_ir
    return IEEECOMFilter._from_finite_record_ir(pulse_record, link_cfg)

def _build_channel_under_test(
    channel_cfg: COMChannelConfig,
    renormalization_order: Literal["sdd_first", "s4p_first"] = "sdd_first",
) -> list[SparamModel]:
    """
    Build 178A measured-domain channel-under-test S-parameter models.

    Output contract mirrors _build_channel_under_test_93A():
    - index 0: victim
    - following indices: NEXT channels, then FEXT channels
    """
    if renormalization_order == "sdd_first":
        return _build_channel_under_test_93A(channel_cfg)
    if renormalization_order != "s4p_first":
        raise ValueError("renormalization_order must be sdd_first or s4p_first.")
    if channel_cfg.victim_s4p_path is None:
        raise ValueError("channel_cfg.victim_s4p_path must be provided.")
    paths = [
        channel_cfg.victim_s4p_path,
        *channel_cfg.next_s4p_paths,
        *channel_cfg.fext_s4p_paths,
    ]
    channels = [
        SparamModel.from_touchstone(
            path, mode="s4p", port_order=channel_cfg.port_order,
            z0=2.0 * channel_cfg.R0, renormalization_order="s4p_first",
            frequency_limit_Hz=channel_cfg.sparam_frequency_limit_Hz,
        )
        for path in paths
    ]
    common_freqs = channel_cfg.align_grid(channels)
    return [channel.resampled(common_freqs) for channel in channels]

def _build_path(
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig,
    txpkg_cfg: COMPkgConfig,
    shared: COMSharedPath,
    kind: Literal["victim", "next", "fext"],
    S_ch: SparamModel,
    out_of_measured: Literal["cosine_decay", "zero_padding"],
    ctle_pulse_realization: Literal["continuous_tf", "bilinear_iir"],
) -> COMPath:
    """
    Build one 178A COM signal path from a measured-domain channel-under-test model.

    IO contract mirrors _build_path_93A() so COM can reuse COMPath and
    COMReport while the package and CTF equations remain version-specific.
    """
    if not np.allclose(S_ch.freqs, shared.S_rx.freqs):
        raise ValueError("S_ch.freqs must match shared.S_rx.freqs for measured-domain cascade.")

    if kind == "next":
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg, isNext=True)
        H_ffe = shared.H_ffe_next
        amplitude = ft_cfg.A_ne
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, amplitude)
    elif kind == "fext":
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        amplitude = ft_cfg.A_fe
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, amplitude)
    elif kind == "victim":
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        amplitude = ft_cfg.A_v
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, amplitude)
    else:
        raise ValueError(f"Unsupported COM path kind: {kind}")

    S_all = S_tx.cascade_com_93A(S_ch).cascade_com_93A(shared.S_rx)
    H_21 = S_all.to_LinkSegment(
        link_cfg,
        gamma_src=channel_cfg.gamma_src,
        gamma_load=channel_cfg.gamma_load,
        dc=channel_cfg.missing_dc_policy,
        out_of_measured=out_of_measured,
    )
    H_pre = (
        H_ffe
        .cascade_tf(shared.H_t)
        .cascade_tf(H_21)
        .cascade_tf(shared.H_r)
    )
    H_all = H_pre.cascade_tf(shared.H_ctf)
    measured_freqs = None
    measured_pre_ctle = None
    if ctle_pulse_realization == "bilinear_iir":
        measured_freqs, measured_pre_ctle = _evaluate_pre_ctle_on_measured_grid(
            S_all,
            link_cfg,
            channel_cfg,
            ft_cfg,
            kind=kind,
        )
    post_ctle, pulse_domain = _realize_ctle_response(
        H_pre,
        shared.H_ctf,
        link_cfg,
        ctle_pulse_realization,
        shared.ctle_iir,
        measured_freqs=measured_freqs,
        measured_tf=measured_pre_ctle,
    )
    pulse = _apply_rectangular_unit_pulse(
        post_ctle,
        X,
        link_cfg,
        amplitude,
        pulse_domain,
    )

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
    Build 178A path-shared COM models.

    The returned COMSharedPath keeps the same fields as 93A:
    H_ffe, H_ffe_next, H_t, S_rx, H_r, H_ctf.
    """
    link_cfg = cfg.link
    ft_cfg = cfg.filter
    H_ctf = _build_H_ctf(link_cfg, ft_cfg)
    ctle_iir = None
    if cfg.policy.ctle_pulse_realization == "bilinear_iir":
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
                "COMFilterConfig178A is missing required bilinear CTF fields: "
                + ", ".join(missing)
            )
        ctle_iir = IEEECOMFilter.build_rx_equalizer_bilinear(
            link_cfg,
            g_1=required["g_1"],
            g_2=required["g_2"],
            f_z1=required["f_z1"],
            f_z2=required["f_z2"],
            f_p1=required["f_p1"],
            f_p2=required["f_p2"],
            f_p3=required["f_p3"],
        )
    return COMSharedPath(
        H_ffe=_build_H_ffe(link_cfg, ft_cfg),
        H_ffe_next=_build_H_ffe_next(link_cfg),
        H_t=_build_H_t(link_cfg, ft_cfg),
        S_rx=_build_rxpkg(freqs, cfg.rxpkg),
        H_r=_build_H_r(link_cfg, ft_cfg),
        H_ctf=H_ctf,
        ctle_iir=ctle_iir,
    )

def _build_paths(
    cfg: COMConfig,
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
        raise COMLengthMismatchError(
            "channels length must match victim + NEXT + FEXT path count. "
            f"Expected {expected_count}, got {len(channels)}."
        )

    paths = [
        _build_path(
            link_cfg=link_cfg,
            channel_cfg=ch_cfg,
            ft_cfg=ft_cfg,
            txpkg_cfg=cfg.txpkg_victim,
            shared=shared,
            kind="victim",
            S_ch=channels[0],
            out_of_measured=cfg.policy.out_of_measured,
            ctle_pulse_realization=cfg.policy.ctle_pulse_realization,
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
                txpkg_cfg=cfg.txpkg_next,
                shared=shared,
                kind="next",
                S_ch=S_ch,
                out_of_measured=cfg.policy.out_of_measured,
                ctle_pulse_realization=cfg.policy.ctle_pulse_realization,
            )
        )

    for S_ch in fext_channels:
        paths.append(
            _build_path(
                link_cfg=link_cfg,
                channel_cfg=ch_cfg,
                ft_cfg=ft_cfg,
                txpkg_cfg=cfg.txpkg_fext,
                shared=shared,
                kind="fext",
                S_ch=S_ch,
                out_of_measured=cfg.policy.out_of_measured,
                ctle_pulse_realization=cfg.policy.ctle_pulse_realization,
            )
        )

    return paths

# --------------------------------------------
# calculate_pre_dte_imp_common(): private helpers
# --------------------------------------------
# @dataclass(repr=False)
# class COMImpairmentCommon(_PrettyDataclass):
#     """
#     178A impairment components that are independent of sampling phase.

#     This object is computed once per concrete path/filter configuration and
#     reused across the sampling-phase loop in COM._run_once().
#     """
#     sigma_X: float
#     S_rn: SampledPSD                # unit: V^2/Hz, receiver input noise PSD, theta-indexed one-sided equivalent
#     sigma_N: float                  # unit: V, receiver noise amplitude standard deviation
#     S_xn: SampledPSD                # unit: V^2/Hz, crosstalk PSD using each path's worst sampling phase
#     sigma_XT: float                 # unit: V, crosstalk amplitude standard deviation
#     h_XTs_dsamp: list[np.ndarray]   # unit: V, worst-phase sampled crosstalk responses

def _build_psd_rx_noise(link_cfg: LinkConfig, imp_cfg: COMImpairmentConfig, ft_cfg: COMFilterConfig) -> SampledPSD:
    # 178A-17 uses eta_0/2 as the two-sided white-noise density. ContinuousPSD
    # stores one-sided CT PSD, so the corresponding positive-frequency value is
    # eta_0.
    S_rn_broadband = ContinuousPSD.from_constant(link_cfg.freqs, imp_cfg.eta_0, cfg=link_cfg)
    H_rn = _build_H_r(link_cfg, ft_cfg).cascade_tf(_build_H_ctf(link_cfg, ft_cfg))
    S_rn_filtered = S_rn_broadband.filtered_by(H_rn)
    return S_rn_filtered.to_sampled(link_cfg.fb, link_cfg.theta)

def _find_pos_xtalk(h_XT: np.ndarray, per_ui: int) -> tuple[int, np.ndarray]:
    """
    Find the 178A-18 crosstalk worst-case sampling phase.

    Eq. 178A-18 defines h_xn^(k)(n) using t_s^(k), where t_s^(k) is chosen to
    maximize sum_n [h_xn^(k)(n)]^2 for that crosstalk path. This phase is not
    the victim sampling phase candidate.
    """
    return _find_pos_xtalk_93A(h_XT, per_ui)

def _build_psd_xtalk(
    h_XTs: list[np.ndarray],
    link_cfg: LinkConfig,
    sigma_x: float,
    *,
    noise_link_cfg: Optional[LinkConfig] = None,
    noise_grid: COMPolicyConfig = COMPolicyConfig(),
) -> tuple[SampledPSD, list[np.ndarray]]:

    noise_link_cfg = noise_link_cfg or link_cfg

    # initialized with psd_constant = 0.0
    S_xn_all = SampledPSD.from_constant(
        noise_link_cfg.theta, 0.0, noise_link_cfg.fb, cfg=noise_link_cfg
    )
    h_XTs_dsamp = []
    for h_XT in h_XTs:
        # Eq. 178A-18 selects one sampling phase per crosstalk path.  A fixed
        # noise record applies before both the phase-energy search and DFT,
        # matching num_ui_RXFF_noise in the MATLAB/SiCoPR implementation.
        if noise_grid.noise_grid_method == "fixed_ui":
            record_samples = int(noise_grid.noise_grid_num_ui) * link_cfg.per_ui
            phase, h_XT_noise = _find_pos_xtalk(
                np.asarray(h_XT)[:record_samples], link_cfg.per_ui
            )
            h_XT_dsamp = np.asarray(h_XT)[phase::link_cfg.per_ui]
        else:
            phase, h_XT_noise = _find_pos_xtalk(h_XT, link_cfg.per_ui)
            h_XT_dsamp = h_XT_noise
        S_xn_temp = _build_psd_from_DFT_response(
            noise_grid.fit_noise_response(h_XT_noise),
            noise_link_cfg,
            sigma_x**2,
        )
        h_XTs_dsamp.append(h_XT_dsamp)
        S_xn_all = S_xn_all.add(S_xn_temp)

    return S_xn_all, h_XTs_dsamp

# ---------------------------------------------
# calculate_pre_dte_imp_at_pos(): private helpers
# ---------------------------------------------
# @dataclass(repr=False)
# class COMImpairmentAtPos(_PrettyDataclass):
#     pos: int
#     ts: int
#     As: float
#     sigma_X: float
#     h_dsamp: np.ndarray
#     S_tn: SampledPSD
#     sigma_tn: float
#     h_tn: np.ndarray
#     S_jn: SampledPSD
#     sigma_J: float
#     h_J: np.ndarray
#     S_qn: SampledPSD
#     sigma_qn: float
#     S_total: SampledPSD
#     sigma_total: float
#     R_n: np.ndarray

def _build_psd_from_DFT_response(
    h_dsamp: np.ndarray,
    link_cfg: LinkConfig,
    variance: float,
) -> SampledPSD:
    """
    Build one sampled-domain PSD component from a sampled impulse response.

    This implements the 178A PSD terms that have the form:
        variance * |DFT(h[n])|^2 / fb

    SampledPSD stores the rfft one-sided equivalent of the spec's two-sided
    theta-indexed Hz-density PSD. Therefore the source PSD constant passed to
    SampledPSD.from_constant() is the spec value ``variance / fb``; no
    Jacobian/radian-density scaling is applied here.
    """
    variance = float(variance)
    if not np.isfinite(variance) or variance < 0.0:
        raise ValueError("variance must be finite and non-negative.")
    h_dsamp = np.asarray(h_dsamp, dtype=float)
    if h_dsamp.ndim != 1:
        raise ValueError("h_dsamp must be one-dimensional.")
    if len(h_dsamp) > link_cfg.sampled_nfft:
        raise COMLengthMismatchError(
            "Linear sampled response exceeds the target sampled DFT window: "
            f"len(response)={len(h_dsamp)}, "
            f"cfg.sampled_nfft={link_cfg.sampled_nfft}. "
            "Choose an expanded sampled grid or an explicit fixed-grid DTFT "
            "projection; do not truncate the response implicitly."
        )
    S_base = SampledPSD.from_constant(link_cfg.theta, variance / link_cfg.fb, link_cfg.fb, cfg=link_cfg)
    H = SampledResponse.from_ir(h_dsamp, link_cfg)
    return S_base.filtered_by(H)

def _build_psd_tx_noise(
    victim: COMPath,
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig,
    imp_cfg: COMImpairmentConfig,
    pos: int,
    ctle_pulse_realization: Literal["continuous_tf", "bilinear_iir"],
    *,
    noise_link_cfg: Optional[LinkConfig] = None,
    noise_grid: COMPolicyConfig = COMPolicyConfig(),
) -> tuple[SampledPSD, np.ndarray]:
    """
    Build transmitter output noise PSD and the sampled no-FFE pulse response.

    Reference:
    - IEEE 802.3 Annex 178A.1.7.3, Eq. 178A-19 and Eq. 178A-20.
    """
    noise_link_cfg = noise_link_cfg or link_cfg
    H_pre_noffe = (
        victim.H_t
        .cascade_tf(victim.H_21)
        .cascade_tf(victim.H_r)
    )
    X_v = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_v)
    measured_freqs = None
    measured_pre_ctle = None
    if ctle_pulse_realization == "bilinear_iir":
        measured_freqs, measured_pre_ctle = _evaluate_pre_ctle_on_measured_grid(
            victim.S_all,
            link_cfg,
            channel_cfg,
            ft_cfg,
            kind="victim",
            include_txffe=False,
        )
    post_ctle_noffe, pulse_domain = _realize_ctle_response(
        H_pre_noffe,
        victim.H_ctf,
        link_cfg,
        ctle_pulse_realization,
        victim.shared.ctle_iir,
        measured_freqs=measured_freqs,
        measured_tf=measured_pre_ctle,
    )
    pulse_noffe = _apply_rectangular_unit_pulse(
        post_ctle_noffe,
        X_v,
        link_cfg,
        ft_cfg.A_v,
        pulse_domain,
    )
    h_tn = pulse_noffe.ir[int(pos)::link_cfg.per_ui]
    variance = 10 ** (-imp_cfg.SNR_TX / 10)
    return _build_psd_from_DFT_response(
        noise_grid.fit_noise_response(h_tn), noise_link_cfg, variance
    ), h_tn

def _apply_fir_finite_record(response: np.ndarray, taps: np.ndarray) -> np.ndarray:
    """Apply FIR taps as a fixed-length circular shift sum."""
    response = np.asarray(response, dtype=float)
    taps = np.asarray(taps, dtype=float)
    if response.ndim != 1 or taps.ndim != 1:
        raise ValueError("finite-record FIR inputs must be one-dimensional.")
    result = np.zeros_like(response)
    for tap_index in np.flatnonzero(taps != 0.0):
        result += float(taps[tap_index]) * np.roll(response, int(tap_index))
    return result


def _apply_rxffe_response(
    response: SampledResponse,
    taps: np.ndarray,
    link_cfg: LinkConfig,
    realization: Literal["linear_convolution", "finite_record_circshift"],
    context: str,
) -> SampledResponse:
    """Apply the selected post-FFE record-boundary convention."""
    taps = np.asarray(taps, dtype=float)
    if realization == "finite_record_circshift":
        return SampledResponse.from_ir(
            _apply_fir_finite_record(response.ir, taps),
            link_cfg,
        )
    if realization != "linear_convolution":
        raise ValueError(
            "RxFFE record realization must be linear_convolution or "
            "finite_record_circshift."
        )
    tap_response = SampledResponse.from_ir(taps, link_cfg)
    try:
        return response.cascade_ir(tap_response, force_grid=True)
    except GridOverflowError as error:
        raise error.with_context(context) from error


def _calculate_h_J(
    h: np.ndarray,
    pos: int,
    link_cfg: LinkConfig,
    w: Optional[np.ndarray] = None,
    rxffe_record_realization: Literal[
        "linear_convolution", "finite_record_circshift"
    ] = "linear_convolution",
) -> np.ndarray:
    """
    Calculate 178A sampled jitter sensitivity.

    Reference:
    - IEEE 802.3 Annex 178A.1.7.4, Eq. 178A-21.

    The returned samples are in V/UI because COM jitter parameters A_DD and
    sigma_RJ are specified in UI. Eq. 178A-21 is evaluated with
    Delta t = link_cfg.dt, the waveform sample interval.
    """
    per_ui = link_cfg.per_ui
    center_idx = np.arange(pos, len(h), per_ui)
    valid = (center_idx > 0) & (center_idx < len(h) - 1)
    center_idx = center_idx[valid]
    if len(center_idx) == 0:
        raise ValueError("No valid samples for 178A h_J finite difference.")

    delta_t_ui = link_cfg.dt / link_cfg.bt
    h_m1 = h[center_idx - 1]
    h_p1 = h[center_idx + 1]
    if w is not None:
        if rxffe_record_realization == "linear_convolution":
            h_m1 = np.convolve(h_m1, w)
            h_p1 = np.convolve(h_p1, w)
        elif rxffe_record_realization == "finite_record_circshift":
            h_m1 = _apply_fir_finite_record(h_m1, w)
            h_p1 = _apply_fir_finite_record(h_p1, w)
        else:
            raise ValueError(
                "RxFFE record realization must be linear_convolution or "
                "finite_record_circshift."
            )
    h_J = (h_p1 - h_m1) / (2 * delta_t_ui)
    return h_J

def _build_psd_tx_jitter(
    victim: COMPath,
    link_cfg: LinkConfig,
    imp_cfg: COMImpairmentConfig,
    pos: int,
    sigma_X: float,
    *,
    noise_link_cfg: Optional[LinkConfig] = None,
    noise_grid: COMPolicyConfig = COMPolicyConfig(),
) -> tuple[SampledPSD, np.ndarray]:

    noise_link_cfg = noise_link_cfg or link_cfg
    h_J = _calculate_h_J(victim.pulse.ir, pos, link_cfg)
    jitter_variance = sigma_X**2 * (imp_cfg.A_DD**2 + imp_cfg.sigma_RJ**2)
    S_jn = _build_psd_from_DFT_response(
        noise_grid.fit_noise_response(h_J), noise_link_cfg, jitter_variance
    )
    return S_jn, h_J

def _calculate_V_qc(
    p_sig: Pmf1D,
    h_dsamp: np.ndarray,
    sigma_ga: float,
    P_qc: float,
    pmf_cfg: COMPMFRuntimeConfig,
    *,
    cdf_tail: Optional[float] = None,
    L: Optional[int] = None,
    pmf_methods: COMPolicyConfig = COMPolicyConfig(),
) -> COMAdcInputPMF:
    """Build the exact ADC-input PMF chain and resolve V_qc from p_sn."""
    if pmf_methods.interference_pmf_method == "pam_atoms" and L is None:
        raise ValueError("Atomic ADC PMF construction requires PAM order L.")
    pmf_s = _build_pmf_interference_178A(
        p_sig, h_dsamp, pmf_cfg, L or len(p_sig.pmf),
        method=pmf_methods.interference_pmf_method, name="Noiseless signal",
    )

    pmf_ga = Pmf1D.gaussian(
        mu=0,
        sigma=sigma_ga,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Noise",
        method=pmf_methods.gaussian_pmf_method,
    )

    pmf_sn = pmf_s.combine(pmf_ga, name="Noisy signal")
    # Annex 178A.1.7.6 uses P_qc/2; the reference-only pre-DTE branch
    # supplies P_qc explicitly from calculate_pre_dte_imp_at_pos().
    V_qc = -(pmf_sn.quantile(P_qc / 2 if cdf_tail is None else cdf_tail))

    return COMAdcInputPMF(
        p_sig=p_sig,
        p_s=pmf_s,
        p_ga=pmf_ga,
        p_n=pmf_ga,
        p_sn=pmf_sn,
        V_qc=V_qc,
        method="pmf_exact",
    )

def _calculate_V_qc_gaussian_approx(
    p_sig: Pmf1D,
    h_dsamp: np.ndarray,
    sigma_ga: float,
    P_qc: float,
    pmf_cfg: COMPMFRuntimeConfig,
    *,
    cdf_tail: Optional[float] = None,
) -> COMAdcInputPMF:
    """
    Fast approximation for 178A pre-DTE quantization clipping amplitude.

    The exact 178A.1.7.6 path builds ``p_sn = conv[p_s, p_ga]`` and finds the
    clipping point from its CDF. This approximation keeps the same target tail
    probability but approximates the noisy signal amplitude as Gaussian with
    variance equal to signal variance plus Gaussian-noise variance.
    """
    from statistics import NormalDist

    x = p_sig.x
    probs = p_sig.pmf
    mu_x = float(np.sum(x * probs))
    var_x = float(np.sum((x - mu_x)**2 * probs))
    var_signal = var_x * float(np.sum(np.asarray(h_dsamp, dtype=float)**2))
    sigma_sn = float(np.sqrt(max(0.0, var_signal + float(sigma_ga)**2)))
    tail = float(P_qc) / 2.0 if cdf_tail is None else float(cdf_tail)
    V_qc = float(NormalDist().inv_cdf(1.0 - tail) * sigma_sn)
    p_sn = Pmf1D.gaussian(
        mu=0.0,
        sigma=sigma_sn,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="ADC-input Gaussian approximation",
    )
    return COMAdcInputPMF(
        p_sig=p_sig,
        p_sn=p_sn,
        V_qc=V_qc,
        method="gaussian_approx",
    )

def _build_psd_adc_qn(
    p_sig: Pmf1D, 
    h_dsamp: np.ndarray, 
    sigma_ga: float, 
    P_qc: float,
    N_qb: int,
    pmf_cfg: COMPMFRuntimeConfig, 
    link_cfg: LinkConfig,
    vqc_method: str = "gaussian_approx",
    *,
    cdf_tail: Optional[float] = None,
    L: Optional[int] = None,
    pmf_methods: COMPolicyConfig = COMPolicyConfig(),
) -> tuple[SampledPSD, COMAdcInputPMF]:

    if vqc_method == "gaussian_approx":
        adc_input_pmf = _calculate_V_qc_gaussian_approx(
            p_sig,
            h_dsamp,
            sigma_ga,
            P_qc,
            pmf_cfg,
            cdf_tail=cdf_tail,
        )
        V_qc = adc_input_pmf.V_qc
        if V_qc is None:
            raise RuntimeError("Gaussian-approximate ADC input did not resolve V_qc.")
    elif vqc_method == "pmf_exact":
        adc_input_pmf = _calculate_V_qc(
            p_sig, h_dsamp, sigma_ga, P_qc, pmf_cfg, cdf_tail=cdf_tail,
            L=L, pmf_methods=pmf_methods,
        )
        V_qc = adc_input_pmf.V_qc
        if V_qc is None:
            raise RuntimeError("Exact ADC-input PMF did not resolve V_qc.")
    else:
        raise ValueError("vqc_method must be 'gaussian_approx' or 'pmf_exact'.")

    # 178A-27
    delta = 2 * V_qc / (2**N_qb - 1)

    # 178A-26
    S_qn = SampledPSD.from_constant(link_cfg.theta, (delta**2/12)/link_cfg.fb, link_cfg.fb, cfg=link_cfg)

    adc_input_pmf.delta = delta
    return S_qn, adc_input_pmf

# for psd fallback
def _zero_sampled_psd(link_cfg: LinkConfig) -> SampledPSD:
    """Return a zero-valued sampled-domain PSD on link_cfg.theta."""
    return SampledPSD.from_constant(link_cfg.theta, 0.0, link_cfg.fb, cfg=link_cfg)

# -----------------------------------------
# calculate_MMSE_DTE(): private helper
# -----------------------------------------
class COM_MMSE_DTE:
    def __init__(
        self,
        cfg: COMDTEConfig,
        floating_mode: Literal["heuristic", "simplified", "spec-defined"],
    ):
        self.cfg = cfg
        self.floating_mode = floating_mode
        
    def run(self, h_dsamp: np.ndarray, R_n: np.ndarray, sigma_x: float, pos: int, per_ui: int) -> COMDTEStatus:
        """Run one 178A MMSE-DTE solve for the supplied sampling phase."""
        self._validate_input(h_dsamp, R_n, sigma_x, pos, per_ui)

        # Step 1: build full MMSE matrices.
        self.build_mmse_matrice()

        # Step 2: select floating FFE groups, or enter the spec-defined search.
        if self.cfg.N_wg == 0:
            pruned_index = np.arange(self.cfg.N_fix, dtype=int)
        elif self.floating_mode == "heuristic":
            pruned_index = self._select_floating_tap_by_isi()
        elif self.floating_mode == "simplified":
            pruned_index = self._select_floating_tap_onetime()
        elif self.floating_mode == "spec-defined":
            dte_status = self._calculate_float_ffe_178A()
        else:
            raise ValueError(f"Unsupported floating_mode: {self.floating_mode!r}.")

        if self.cfg.N_wg == 0 or self.floating_mode in {"heuristic", "simplified"}:
            # Step 3 to Step 5: solve, limit/refine, calculate MSE, and build status.
            dte_status = self._solve_pruned_tap_set(pruned_index)

        self._validate_equalized_main_cursor(dte_status)
        return dte_status

    def _validate_input(
        self,
        h_dsamp: np.ndarray,
        R_n: np.ndarray,
        sigma_x: float,
        pos: int,
        per_ui: int,
    ) -> None:
        """Validate and store one sampling-phase MMSE problem before Step 1."""
        self.h_dsamp = np.asarray(h_dsamp, dtype=float)
        self.R_n = np.asarray(R_n, dtype=float)[:self.cfg.N_max]
        self.pos = int(pos)
        self.per_ui = int(per_ui)
        self.var_x = float(sigma_x) ** 2

        if self.h_dsamp.ndim != 1 or len(self.h_dsamp) < self.cfg.N_max:
            raise ValueError("h_dsamp must be one-dimensional and cover COMDTEConfig.N_max samples.")
        if len(self.R_n) < self.cfg.N_max:
            raise ValueError("R_n must contain at least COMDTEConfig.N_max samples.")
        if self.per_ui <= 0 or not 0 <= self.pos < self.per_ui:
            raise ValueError("pos must satisfy 0 <= pos < per_ui, with per_ui positive.")
        if not np.isfinite(self.var_x) or self.var_x <= 0.0:
            raise ValueError("sigma_x must be finite and positive.")

        _validate_positive_main_cursor(
            self.h_dsamp,
            source_name="COM_MMSE_DTE.h_dsamp",
            pos=self.pos,
        )

        self.d_h = int(np.argmax(np.abs(self.h_dsamp)))
        self.N = len(self.h_dsamp)
        self.d = int(self.d_h + self.cfg.d_w)
        self.ts = int(self.pos + self.d_h * self.per_ui)
        if self.d + self.cfg.N_b >= self.N:
            raise ValueError("h_dsamp does not contain enough post-cursor samples for the configured DFE taps.")

    def _validate_equalized_main_cursor(self, dte_status: COMDTEStatus) -> None:
        """Require the limited FFE output pulse to peak at the DTE main index d."""
        w_lim = np.asarray(dte_status.w_lim, dtype=float)
        expected_shape = (int(self.cfg.N_max),)
        if w_lim.shape != expected_shape:
            raise COMLengthMismatchError(
                "COMDTEStatus.w_lim must be the full zero-filled FFE tap vector; "
                f"expected shape {expected_shape}, got {w_lim.shape}."
            )
        h_w = np.convolve(self.h_dsamp, w_lim)
        peak_index = int(np.argmax(np.abs(h_w)))
        if peak_index != dte_status.d:
            raise COMMainCursorError(
                "Equalized main cursor is misaligned: "
                f"pos={dte_status.pos}, expected d={dte_status.d}, "
                f"observed peak={peak_index}, h_w[d]={h_w[dte_status.d]:.6e}, "
                f"h_w[peak]={h_w[peak_index]:.6e}."
            )
        
    def build_mmse_matrice(self) -> None:
        from scipy.linalg import toeplitz
        self.H_all = toeplitz(
            np.r_[self.h_dsamp, np.zeros(self.cfg.N_max - 1)],
            np.r_[self.h_dsamp[0], np.zeros(self.cfg.N_max - 1)],
        )
        self.Rnn_all = toeplitz(self.R_n, self.R_n)

    def _solve_pruned_tap_set(self, pruned_index: np.ndarray) -> COMDTEStatus:
        """Evaluate one fixed-plus-floating FFE placement through Step 3 to Step 5."""
        self.build_mmse_pruned_matrice(pruned_index)
        self.solve_mmse_kkt_system()
        self.apply_dte_limiter()
        self.calculate_mse()
        return self._build_dte_status()
    
    def build_mmse_pruned_matrice(self, pruned_index: np.ndarray) -> None:
        """Build Step 3 matrices for one canonical ascending FFE tap placement."""
        self.pruned_index = np.asarray(pruned_index, dtype=int)
        if self.pruned_index.ndim != 1 or len(self.pruned_index) == 0:
            raise ValueError("pruned_index must be a non-empty one-dimensional index vector.")
        if not np.array_equal(self.pruned_index, np.unique(self.pruned_index)):
            raise ValueError("pruned_index must be ascending and contain no duplicate taps.")
        if self.pruned_index[0] != 0 or self.pruned_index[-1] >= self.cfg.N_max:
            raise ValueError("pruned_index must start at fixed tap 0 and stay below N_max.")
        self.H = self.H_all[:, self.pruned_index]
        self.R_nn = self.Rnn_all[np.ix_(self.pruned_index, self.pruned_index)]
        dfe_index = range(self.d+1, self.d+self.cfg.N_b+1)    # post 1 ~ post N_b
        self.H_b = self.H[dfe_index, :]
        self.h_0 = self.H[self.d, :]

    def solve_mmse_kkt_system(self) -> None:
        "eq. 178A-31"
        self.R = self.H.T @ self.H + self.R_nn / self.var_x
        N_w = len(self.pruned_index)
        N_b = self.cfg.N_b
        self.system_matrix = np.block([
            [self.R,                   -self.H_b.T,        -self.h_0.reshape(N_w, 1)],
            [-self.H_b,                np.eye(N_b),        np.zeros((N_b, 1))      ],
            [self.h_0.reshape(1, N_w), np.zeros((1, N_b)), np.zeros((1, 1))        ],
        ])
        self.system_column = np.concatenate([
            self.h_0,                   # shape (Nw,)
            np.zeros(N_b),              # shape (Nb,)
            np.array([1.0]),            # shape (1,)
        ])
        self.system_sol = np.linalg.solve(self.system_matrix, self.system_column)
        self.w = self.system_sol[:N_w]
        self.b = self.system_sol[N_w: N_w + N_b]
        self.lam = self.system_sol[-1]

    def apply_dte_limiter(self) -> None:
        "eq. 178A-32~34"
        # dfe limiter
        self.b_lim = np.clip(self.b, self.cfg.b_lower, self.cfg.b_upper)

        # recalculate ffe
        b_was_limited = not np.allclose(self.b, self.b_lim, rtol=0.0, atol=1e-12)
        if b_was_limited:
            self.solve_mmse_kkt_system_ffe()

        # ffe limiter
        w_lim_in = self.w_1 if b_was_limited else self.w
        w_lower, w_upper = self._ffe_limits_for_pruned_indices()
        main_position = int(np.flatnonzero(self.pruned_index == self.cfg.d_w)[0])
        main_scale = w_lim_in[main_position]
        bound_a = w_lower * main_scale
        bound_b = w_upper * main_scale
        self.w_lim = np.clip(
            w_lim_in,
            np.minimum(bound_a, bound_b),
            np.maximum(bound_a, bound_b),
        )

        # refine ffe and dfe
        w_was_limited = not np.allclose(w_lim_in, self.w_lim, rtol=0.0, atol=1e-12)
        if w_was_limited:
            gain = self.w_lim.dot(self.h_0)
            self.w_lim = self.w_lim / gain
            b_from_w_lim = self.H_b @ self.w_lim
            self.b_lim = np.clip(b_from_w_lim, self.cfg.b_lower, self.cfg.b_upper)

    def _ffe_limits_for_pruned_indices(self) -> tuple[np.ndarray, np.ndarray]:
        """Return FFE lower/upper limits aligned to the current pruned tap order."""
        lower = self.cfg.w_lower[self.pruned_index].copy()
        upper = self.cfg.w_upper[self.pruned_index].copy()
        main_position = np.flatnonzero(self.pruned_index == self.cfg.d_w)
        if len(main_position) != 1:
            raise ValueError("pruned_index must contain the fixed FFE main tap exactly once.")
        lower[main_position[0]] = 1.0
        upper[main_position[0]] = 1.0
        return lower, upper

    def solve_mmse_kkt_system_ffe(self) -> None:
        "eq. 178A-33"
        N_w = len(self.pruned_index)
        self.system_matrix_1 = np.block([
            [self.R,                   -self.h_0.reshape(N_w, 1)],
            [self.h_0.reshape(1, N_w), np.zeros((1, 1))        ],
        ])
        self.system_column_1 = np.concatenate([
            self.h_0 + self.H_b.T @ self.b_lim,                     # shape (Nw,)
            np.array([1.0]),                                        # shape (1,)
        ])
        self.system_sol_1 = np.linalg.solve(self.system_matrix_1, self.system_column_1)
        self.w_1 = self.system_sol_1[:N_w]
        self.lam_1 = self.system_sol_1[-1]

    def calculate_mse(self) -> None:
        "eq. 178A-35"
        var_e = self.var_x*(
            self.w_lim.reshape(1,-1) @ self.R @ self.w_lim.reshape(-1,1) +
            1 + self.b_lim.dot(self.b_lim) 
            - 2*self.w_lim.dot(self.h_0)
            - 2*self.w_lim.reshape(1,-1) @ self.H_b.T @ self.b_lim.reshape(-1,1)
        )
        self.var_e = float(np.asarray(var_e).squeeze())

    def _build_dte_status(self) -> COMDTEStatus:
        """Build the final Step 5 status with full zero-filled FFE outputs."""
        w_lim_out = np.zeros(self.cfg.N_max)
        w_lim_out[self.pruned_index] = self.w_lim
        w_out = np.zeros(self.cfg.N_max)
        w_out[self.pruned_index] = self.w
        return COMDTEStatus(
            ts=int(self.ts),
            pos=int(self.pos),
            d=int(self.d),
            w_lim=np.asarray(w_lim_out, dtype=float),
            b_lim=np.asarray(self.b_lim, dtype=float),
            mse=float(self.var_e),
            H_all=self.H_all,
            Rnn_all=self.Rnn_all,
            pruned_index=np.asarray(self.pruned_index, dtype=int),
            H=self.H,
            R_nn=self.R_nn,
            H_b=self.H_b,
            w=np.asarray(w_out, dtype=float),
            b=np.asarray(self.b, dtype=float),
        )

    # ============================================
    # floating group selection
    # ============================================
    def _select_floating_tap_by_isi(self) -> np.ndarray:
        """Choose floating groups with the largest channel-ISI group energy."""
        starts = self._candidate_floating_group_starts()
        scores = np.zeros(len(starts), dtype=float)
        for idx, start in enumerate(starts):
            h_index = self.d - np.arange(start, start + self.cfg.N_wf, dtype=int)
            valid = (0 <= h_index) & (h_index < self.N)
            scores[idx] = float(np.sum(np.abs(self.h_dsamp[h_index[valid]]) ** 2))
        return self._select_non_overlapping_floating_groups(starts, scores)
    
    def _select_floating_tap_onetime(self) -> np.ndarray:
        """Use one full-FFE MMSE solve, then rank groups by raw coefficient energy."""
        full_index = np.arange(self.cfg.N_max, dtype=int)
        self.build_mmse_pruned_matrice(full_index)
        self.solve_mmse_kkt_system()
        self.w_full = np.asarray(self.w, dtype=float).copy()
        self.b_full = np.asarray(self.b, dtype=float).copy()

        starts = self._candidate_floating_group_starts()
        scores = np.array(
            [np.sum(np.abs(self.w_full[start:start + self.cfg.N_wf]) ** 2) for start in starts],
            dtype=float,
        )
        return self._select_non_overlapping_floating_groups(starts, scores)

    def _calculate_float_ffe_178A(self) -> COMDTEStatus:
        """Exhaustively select the legal floating FFE placement with minimum final MSE."""
        def candidate_floating_group_starts() -> np.ndarray:
            """Return starts for full floating groups contained in [N_fix, N_max)."""
            starts = np.arange(
                self.cfg.N_fix,
                self.cfg.N_max - self.cfg.N_wf + 1,
                dtype=int,
            )
            if len(starts) == 0:
                raise ValueError("COMDTEConfig does not provide a full floating FFE group candidate.")
            return starts

        def non_overlapping_group_placements(group_starts: np.ndarray) -> list[np.ndarray]:
            """Enumerate every ascending, non-overlapping set of N_wg group starts."""
            placements: list[np.ndarray] = []
            for starts in combinations(group_starts, self.cfg.N_wg):
                starts_array = np.asarray(starts, dtype=int)
                if np.all(np.diff(starts_array) >= self.cfg.N_wf):
                    placements.append(starts_array)
            if not placements:
                raise ValueError("Not enough non-overlapping floating FFE groups are available.")
            return placements

        fixed_index = np.arange(self.cfg.N_fix, dtype=int)
        best_status: Optional[COMDTEStatus] = None
        for group_starts in non_overlapping_group_placements(candidate_floating_group_starts()):
            floating_index = np.concatenate(
                [np.arange(start, start + self.cfg.N_wf, dtype=int) for start in group_starts]
            )
            pruned_index = np.concatenate([fixed_index, floating_index])
            dte_status = self._solve_pruned_tap_set(pruned_index)
            if best_status is None or dte_status.mse < best_status.mse:
                best_status = dte_status

        if best_status is None:
            raise RuntimeError("No valid floating FFE placement was evaluated.")

        # Keep this solver's middle-result attributes aligned with the selected status.
        return self._solve_pruned_tap_set(best_status.pruned_index)

    def _candidate_floating_group_starts(self) -> np.ndarray:
        """Return full-length floating FFE group starts inside [N_fix, N_max)."""
        starts = np.arange(self.cfg.N_fix, self.cfg.N_max - self.cfg.N_wf + 1, dtype=int)
        if len(starts) == 0:
            raise ValueError("COMDTEConfig does not provide a full floating FFE group candidate.")
        return starts

    def _select_non_overlapping_floating_groups(
        self,
        group_starts: np.ndarray,
        scores: np.ndarray,
    ) -> np.ndarray:
        """Select N_wg non-overlapping full floating groups by descending score."""
        group_starts = np.asarray(group_starts, dtype=int)
        scores = np.asarray(scores, dtype=float)
        if group_starts.shape != scores.shape:
            raise COMLengthMismatchError(
                "group_starts and scores must have identical shape."
            )

        selected_starts: list[int] = []
        selected_taps: set[int] = set()
        for start in group_starts[np.argsort(scores)[::-1]]:
            group = set(range(int(start), int(start) + self.cfg.N_wf))
            if group.isdisjoint(selected_taps):
                selected_starts.append(int(start))
                selected_taps.update(group)
            if len(selected_starts) == self.cfg.N_wg:
                break
        if len(selected_starts) != self.cfg.N_wg:
            raise ValueError("Not enough non-overlapping floating FFE groups are available.")

        self.floating_group_starts = np.array(sorted(selected_starts), dtype=int)
        self.floating_group_scores = scores.copy()
        floating_index = np.concatenate(
            [np.arange(start, start + self.cfg.N_wf, dtype=int) for start in self.floating_group_starts]
        )
        return np.concatenate([np.arange(self.cfg.N_fix, dtype=int), floating_index])
   
    
# ----------------------------
# pmf
# ----------------------------
def _resolve_adc_input_pmf_config(
    pmf_config: COMPMFConfig,
    As: float,
    run_cfg: COMRunConfig,
    *,
    gaussian_n_sigma_override: Optional[float] = None,
) -> COMPMFRuntimeConfig:
    """Resolve execution-policy PMF settings used before ADC quantization."""
    resolved = pmf_config.resolve(As, grid_quality=run_cfg.pmf_grid_quality)
    return replace(
        resolved,
        dy=resolved.dy if run_cfg.pmf_dy_override is None else run_cfg.pmf_dy_override,
        keep_mass=run_cfg.pmf_keep_mass,
        gaussian_n_sigma=(
            resolved.gaussian_n_sigma if gaussian_n_sigma_override is None
            else gaussian_n_sigma_override
        ),
    )


def _resolve_final_com_pmf_config(
    pmf_config: COMPMFConfig,
    As: float,
    run_cfg: COMRunConfig,
    *,
    gaussian_n_sigma_override: Optional[float] = None,
    final_pmf_grid: Literal["fine", "relative_As"] = "fine",
) -> COMPMFRuntimeConfig:
    """Resolve accuracy-required PMF settings used to calculate final COM."""
    # In the reference profile, RxFFE is represented with a unit main tap.
    # This model retains the unnormalized main gain, so reference delta_y
    # must be multiplied by that gain: 0.001*(As/gain)*gain = 0.001*As.
    use_relative_grid = final_pmf_grid == "relative_As"
    if final_pmf_grid not in {"fine", "relative_As"}:
        raise ValueError("final_pmf_grid must be fine or relative_As.")
    resolved = pmf_config.resolve(As, grid_quality="coarse" if use_relative_grid else "fine")
    return replace(
        resolved,
        dy=(
            resolved.dy if use_relative_grid or run_cfg.pmf_dy_override is None
            else run_cfg.pmf_dy_override
        ),
        keep_mass=1.0,
        gaussian_n_sigma=(
            resolved.gaussian_n_sigma if gaussian_n_sigma_override is None
            else gaussian_n_sigma_override
        ),
    )


def _pam_levels(L: int) -> np.ndarray:
    return np.array([2 * level / (L - 1) - 1 for level in range(L)], dtype=float)


def _build_pmf_pam_L(
    L: int,
    pmf_cfg: COMPMFRuntimeConfig,
    *,
    placement: Literal["linear", "nearest"] = "linear",
) -> Pmf1D:
    # Base PAM4 signal pmf
    return Pmf1D.multi_dirac(
        values = _pam_levels(L),
        probs = 1/L * np.ones(L),
        dx = pmf_cfg.dy,
        unit = "volt",
        name = f"PAM{L}_signal",
        placement=placement,
    )


def _build_pmf_interference_178A(
    p_sig: Pmf1D,
    h: np.ndarray,
    pmf_cfg: COMPMFRuntimeConfig,
    L: int,
    *,
    method: Literal["signal_fir", "pam_atoms"] = "signal_fir",
    name: Optional[str] = None,
) -> Pmf1D:
    if method == "pam_atoms":
        return Pmf1D.fir_filter_atoms(
            _pam_levels(L), np.full(L, 1.0 / L), np.asarray(h, dtype=float),
            dx=pmf_cfg.dy, keep_mass=pmf_cfg.keep_mass,
            tap_abs_th=np.nextafter(pmf_cfg.dy, np.inf),
            unit="volt", name=name or "",
        )
    if method == "signal_fir":
        return _build_pmf_interference_93A(p_sig, h, pmf_cfg, name=name)
    raise ValueError("interference PMF method must be signal_fir or pam_atoms.")


def _build_pmf_w_XT_all(
    p_sig: Pmf1D,
    h_XTs_w: list[np.ndarray | SampledResponse],
    pmf_cfg: COMPMFRuntimeConfig,
    *,
    L: Optional[int] = None,
    methods: COMPolicyConfig = COMPolicyConfig(),
) -> Pmf1D:
    responses = [value.ir if isinstance(value, SampledResponse) else value for value in h_XTs_w]
    if methods.interference_pmf_method == "pam_atoms":
        if L is None:
            raise ValueError("Atomic crosstalk PMF construction requires PAM order L.")
        result = Pmf1D.multi_dirac(
            np.array([0.0]), np.array([1.0]), dx=pmf_cfg.dy,
            unit="volt", name="XT_all", placement=methods.discrete_pmf_placement,
        )
        for response in responses:
            result = result.combine(
                _build_pmf_interference_178A(
                    p_sig, response, pmf_cfg, L,
                    method=methods.interference_pmf_method, name="XT",
                ),
                name="XT_all",
            )
        return result
    if methods.interference_pmf_method == "signal_fir":
        return _build_pmf_XT_all_93A(p_sig, responses, pmf_cfg)
    raise ValueError("Unsupported crosstalk PMF construction method.")

def _build_adc_input_pmf_exact(
    p_sig: Pmf1D, 
    h_dsamp: np.ndarray,
    h_XTs_dsamp: list[np.ndarray],
    A_DD: float,
    h_J: np.ndarray,
    sigma_gn: float, 
    P_qc: float,
    N_qb: int,
    pmf_cfg: COMPMFRuntimeConfig,
    *,
    L: Optional[int] = None,
    pmf_methods: COMPolicyConfig = COMPolicyConfig(),
) -> COMAdcInputPMF:
    """Build the selected-phase exact ADC-input PMF chain for final COM."""
    if pmf_methods.interference_pmf_method == "pam_atoms" and L is None:
        raise ValueError("Atomic ADC PMF construction requires PAM order L.")
    pam_order = L or len(p_sig.pmf)
    
    # noiseless signal
    pmf_s = _build_pmf_interference_178A(
        p_sig, h_dsamp, pmf_cfg, pam_order,
        method=pmf_methods.interference_pmf_method, name="Noiseless signal",
    )

    pmf_XT = _build_pmf_w_XT_all(
        p_sig, h_XTs_dsamp, pmf_cfg, L=pam_order, methods=pmf_methods,
    )
    pmf_DD = _build_pmf_interference_178A(
        p_sig, A_DD * h_J, pmf_cfg, pam_order,
        method=pmf_methods.interference_pmf_method, name="ADC-input Dual-Dirac",
    )

    pmf_ga = Pmf1D.gaussian(
        mu=0,
        sigma=sigma_gn,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Gaussian Noise",
        method=pmf_methods.gaussian_pmf_method,
    )
    pmf_n = pmf_XT.combine(pmf_DD).combine(pmf_ga, name="ADC-input noise")

    pmf_sn = pmf_s.combine(pmf_n, name="Noisy signal")
    V_qc = -(pmf_sn.quantile(P_qc/2))

    delta = 2.0 * V_qc / (2**N_qb - 1)
    return COMAdcInputPMF(
        p_sig=p_sig,
        p_s=pmf_s,
        p_XT=pmf_XT,
        p_DD=pmf_DD,
        p_ga=pmf_ga,
        p_n=pmf_n,
        p_sn=pmf_sn,
        V_qc=V_qc,
        delta=delta,
        method="pmf_exact",
    )

def _build_pmf_G(
    imp_status: COMImpairmentStatus, dte_status: COMDTEStatus,
    link_cfg: LinkConfig, pmf_cfg: COMPMFRuntimeConfig, *,
    gaussian_method: Literal["bin_integral", "reference_sample"] = "bin_integral",
) -> Pmf1D:
    del dte_status, link_cfg
    post_ffe = imp_status.post_ffe
    if post_ffe is None or post_ffe.psd is None or post_ffe.psd.sigma_G is None:
        raise ValueError("Completed post-FFE impairment status must provide sigma_G.")
    sigma_G = float(post_ffe.psd.sigma_G)
    return Pmf1D.gaussian(
        mu=0,
        sigma=sigma_G,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Noise",
        method=gaussian_method,
    )


def _final_adc_clip_reference_only(
    imp_status: COMImpairmentStatus,
    L: int,
    pmf_cfg: COMPMFRuntimeConfig,
    main_gain: float,
    A_DD: float,
    P_qc: float,
    *,
    pmf_methods: COMPolicyConfig = COMPolicyConfig(),
) -> tuple[float, COMPMFRuntimeConfig, Pmf1D]:
    """MATLAB 4.17 comparison boundary: pre-FFE signal plus normalized final noise.

    This is deliberately separate from the Annex D3 post-FFE ADC-input PMF.
    SiCoPR's final quantizer convolves the pre-FFE victim signal with the
    post-FFE ISI/XT/DD/Gaussian noise expressed back at the ADC input, then
    locates the one-sided ``P_qc`` CDF point.
    """
    if not np.isfinite(main_gain) or main_gain <= 0.0:
        raise ValueError("Reference final ADC clipping requires positive RX FFE main gain.")
    # The final PMF uses the post-FFE voltage grid. Refer it back to the ADC
    # input together with the post-FFE responses; otherwise a 59x FFE gain
    # silently makes the clipping CDF grid 59x coarser than the final PDF.
    clip_cfg = replace(
        pmf_cfg,
        dy=pmf_cfg.dy / main_gain,
        tap_abs_th=pmf_cfg.tap_abs_th / main_gain,
    )
    p_sig = _build_pmf_pam_L(
        L, clip_cfg, placement=pmf_methods.discrete_pmf_placement,
    )
    p_s = _build_pmf_interference_178A(
        p_sig, imp_status.h_dsamp.ir, clip_cfg, L,
        method=pmf_methods.interference_pmf_method, name="ADC reference signal",
    )
    p_isi = _build_pmf_interference_178A(
        p_sig, imp_status.h_ISI.ir / main_gain, clip_cfg, L,
        method=pmf_methods.interference_pmf_method, name="ADC reference ISI",
    )
    p_xt = _build_pmf_w_XT_all(
        p_sig,
        [
            (path.ir if isinstance(path, SampledResponse) else path) / main_gain
            for path in imp_status.h_XTs_w
        ],
        clip_cfg,
        L=L,
        methods=pmf_methods,
    )
    p_dd = _build_pmf_interference_178A(
        p_sig,
        A_DD * imp_status.h_w_J.ir / main_gain,
        clip_cfg,
        L, method=pmf_methods.interference_pmf_method, name="ADC reference Dual-Dirac",
    )
    p_ga = Pmf1D.gaussian(
        mu=0.0,
        sigma=imp_status.sigma_G / main_gain,
        dx=clip_cfg.dy,
        n_sigma=clip_cfg.gaussian_n_sigma,
        unit="volt",
        name="ADC reference Gaussian",
        method=pmf_methods.gaussian_pmf_method,
    )
    p_noise = p_isi.combine(p_xt).combine(p_dd).combine(p_ga)
    p_sn = p_s.combine(p_noise)
    return -float(p_sn.quantile(P_qc)), clip_cfg, p_noise


def evaluate_delta_com_an(
    g_an: float,
    post_ffe: COMImpStageStatus,
    pmf_dfe: COMPMFStatus,
    pmf_cfg: COMPMFRuntimeConfig,
    der_0: float,
    *,
    gaussian_method: Literal["bin_integral", "reference_sample"] = "bin_integral",
) -> COMAddedNoiseStatus:
    """Evaluate the Annex 178A MLSD added-receiver-noise penalty.

    This implements the calibration calculation in 178A.1.10.1 only.  The
    added noise is defined at the receiver FFE output, so the pre-existing ADC
    quantization distribution is retained.  In particular, ``p_qn`` is not
    recomputed: its quantizer range was already determined at the ADC input.

    Parameters
    ----------
    g_an:
        Non-negative PSD scale factor from Eq. (178A-50).
    post_ffe:
        Post-FFE impairment stage from the DFE calculation.  Its ``S_rn``
        already includes the receiver FFE response.
    pmf_dfe:
        Complete COM_DFE PMF result at the same sampling phase.
    pmf_cfg:
        Resolved PMF numerical settings used for the COM_DFE calculation.
    der_0:
        Target detector error rate used for the inverse-CDF comparison.

    Returns
    -------
    COMAddedNoiseStatus
        The full noise-and-interference PDF, added-noise PSD, and the dB
        value of ``20 * log10(abs(P_an^-1(der_0)) / abs(P^-1(der_0)))``.
    """
    g_an = float(g_an)
    if not np.isfinite(g_an) or g_an < 0.0:
        raise ValueError("g_an must be finite and non-negative.")

    der_0 = float(der_0)
    if not np.isfinite(der_0) or not 0.0 < der_0 < 0.5:
        raise ValueError("der_0 must be finite and in (0, 0.5).")

    if not np.isclose(pmf_dfe.dy, pmf_cfg.dy):
        raise ValueError(
            "pmf_dfe and pmf_cfg must use the same PMF grid spacing: "
            f"{pmf_dfe.dy!r} != {pmf_cfg.dy!r}."
        )

    post_psd = post_ffe.psd
    if post_psd is None or post_psd.S_rn is None or post_psd.sigma_G is None:
        raise ValueError(
            "post_ffe must contain S_rn and sigma_G from the completed "
            "post-FFE impairment stage."
        )

    missing_pmf = [
        name
        for name in ("p_ISI", "p_XT", "p_DD", "p_qn", "p_combined")
        if getattr(pmf_dfe, name) is None
    ]
    if missing_pmf:
        raise ValueError(
            "pmf_dfe must be the complete COM_DFE PMF result; missing "
            + ", ".join(missing_pmf)
            + "."
        )

    # Eq. (178A-50).  post_ffe.S_rn already contains |H_rxffe|^2.
    S_an = SampledPSD(
        theta=post_psd.S_rn.theta,
        psd=g_an * post_psd.S_rn.psd,
        fb=post_psd.S_rn.fb,
        cfg=post_psd.S_rn.cfg,
    )
    sigma_G = float(post_psd.sigma_G)
    # Eq. (178A-51): to_sigma() integrates S_an on the SampledPSD one-sided grid;
    # hypot then forms sqrt(sigma_G^2 + sigma_added^2).
    sigma_added = float(S_an.to_sigma())
    sigma_an = float(np.hypot(sigma_G, sigma_added))

    # Eq. (178A-51) and its following text: replace the Gaussian part of p_an
    # with sigma_an, retaining the DFE-stage ISI/XT/DD/quantization PMFs.
    p_G_an = Pmf1D.gaussian(
        mu=0.0,
        sigma=sigma_an,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Added receiver noise",
        method=gaussian_method,
    )
    p_an = (
        pmf_dfe.p_ISI
        .combine(pmf_dfe.p_XT)
        .combine(pmf_dfe.p_DD)
        .combine(pmf_dfe.p_qn)
        .combine(p_G_an, name="MLSD added-noise total")
    )

    a_ref = abs(float(pmf_dfe.p_combined.quantile(der_0)))
    a_an = abs(float(p_an.quantile(der_0)))
    if not np.isfinite(a_ref) or not np.isfinite(a_an) or a_ref <= 0.0 or a_an <= 0.0:
        raise COMError(
            "MLSD added-noise quantiles must be finite and non-zero at "
            f"DER_0={der_0:.6e}; got reference={a_ref!r}, added={a_an!r}."
        )

    return COMAddedNoiseStatus(
        g_an=g_an,
        S_an=S_an,
        sigma_an=sigma_an,
        p_an=p_an,
        delta_com_an_temp=float(20.0 * np.log10(a_an / a_ref)),
        sigma_added=sigma_added,
        A_ref=a_ref,
        A_an=a_an,
    )


def solve_g_an(
    target_delta_com_an: float,
    post_ffe: COMImpStageStatus,
    pmf_dfe: COMPMFStatus,
    pmf_cfg: COMPMFRuntimeConfig,
    der_0: float,
    *,
    cvg_th: float = 1e-2,
    max_iter: int = 64,
    gaussian_method: Literal["bin_integral", "reference_sample"] = "bin_integral",
) -> COMAddedNoiseStatus:
    """Solve Eq. (178A-50) scale factor for a target added-noise penalty.

    The evaluator is numerical because it includes PMF convolution and an
    inverse-CDF measurement.  This solver therefore finds a non-negative
    bracket by doubling ``g_an`` and then bisects it until the dB residual is
    within ``cvg_th``.
    """
    target_delta_com_an = float(target_delta_com_an)
    if not np.isfinite(target_delta_com_an) or target_delta_com_an < 0.0:
        raise ValueError("target_delta_com_an must be finite and non-negative.")

    cvg_th = float(cvg_th)
    if not np.isfinite(cvg_th) or cvg_th <= 0.0:
        raise ValueError("cvg_th must be finite and positive in dB.")

    max_iter = int(max_iter)
    if max_iter <= 0:
        raise ValueError("max_iter must be positive.")

    history: list[COMAddedNoiseIterationStatus] = []

    def record(
        candidate: COMAddedNoiseStatus,
        iteration: int,
        phase: Literal["baseline", "bracket", "bisection"],
    ) -> None:
        if candidate.sigma_added is None or candidate.A_an is None or candidate.residual_dB is None:
            raise RuntimeError("Added-noise solver observation is incomplete.")
        history.append(
            COMAddedNoiseIterationStatus(
                iteration=int(iteration),
                phase=phase,
                g_an=float(candidate.g_an),
                sigma_added=float(candidate.sigma_added),
                sigma_an=float(candidate.sigma_an),
                A_an=float(candidate.A_an),
                delta_com_an_temp=float(candidate.delta_com_an_temp),
                residual_dB=float(candidate.residual_dB),
            )
        )

    def finish(candidate: COMAddedNoiseStatus) -> COMAddedNoiseStatus:
        candidate.iteration_history = list(history)
        return candidate

    low = evaluate_delta_com_an(
        0.0, post_ffe, pmf_dfe, pmf_cfg, der_0, gaussian_method=gaussian_method,
    )
    low.target_delta_com_an = target_delta_com_an
    low.residual_dB = low.delta_com_an_temp - target_delta_com_an
    low.iterations = 0
    record(low, 0, "baseline")
    if abs(low.residual_dB) <= cvg_th:
        return finish(low)
    if low.residual_dB > 0.0:
        raise COMError(
            "Non-negative g_an cannot reduce the baseline added-noise penalty: "
            f"delta(0)={low.delta_com_an_temp:.6g} dB, "
            f"target={target_delta_com_an:.6g} dB."
        )

    high_g_an = 1.0
    high: Optional[COMAddedNoiseStatus] = None
    for iteration in range(1, max_iter + 1):
        candidate = evaluate_delta_com_an(
            high_g_an, post_ffe, pmf_dfe, pmf_cfg, der_0,
            gaussian_method=gaussian_method,
        )
        candidate.target_delta_com_an = target_delta_com_an
        candidate.residual_dB = candidate.delta_com_an_temp - target_delta_com_an
        candidate.iterations = iteration
        record(candidate, iteration, "bracket")
        if candidate.delta_com_an_temp + 1e-12 < low.delta_com_an_temp:
            raise COMError(
                "Added-noise penalty must be non-decreasing while bracketing "
                f"g_an; delta({high_g_an / 2.0:.6g})={low.delta_com_an_temp:.6g} dB, "
                f"delta({high_g_an:.6g})={candidate.delta_com_an_temp:.6g} dB."
            )
        if abs(candidate.residual_dB) <= cvg_th:
            return finish(candidate)
        if candidate.residual_dB > 0.0:
            high = candidate
            break
        low = candidate
        high_g_an *= 2.0

    if high is None:
        raise COMError(
            "Unable to bracket target_delta_com_an within max_iter: "
            f"target={target_delta_com_an:.6g} dB, "
            f"last_delta={low.delta_com_an_temp:.6g} dB, max_iter={max_iter}."
        )

    low_g_an = low.g_an
    high_g_an = high.g_an
    best = min((low, high), key=lambda status: abs(status.residual_dB))
    for iteration in range(int(high.iterations) + 1, max_iter + 1):
        mid_g_an = (low_g_an + high_g_an) / 2.0
        mid = evaluate_delta_com_an(
            mid_g_an, post_ffe, pmf_dfe, pmf_cfg, der_0,
            gaussian_method=gaussian_method,
        )
        mid.target_delta_com_an = target_delta_com_an
        mid.residual_dB = mid.delta_com_an_temp - target_delta_com_an
        mid.iterations = iteration
        record(mid, iteration, "bisection")
        if mid.delta_com_an_temp + 1e-12 < low.delta_com_an_temp:
            raise COMError(
                "Added-noise penalty decreased inside the bisection bracket: "
                f"delta({low_g_an:.6g})={low.delta_com_an_temp:.6g} dB, "
                f"delta({mid_g_an:.6g})={mid.delta_com_an_temp:.6g} dB."
            )
        if abs(mid.residual_dB) < abs(best.residual_dB):
            best = mid
        if abs(mid.residual_dB) <= cvg_th:
            return finish(mid)
        if mid.residual_dB < 0.0:
            low_g_an = mid_g_an
            low = mid
        else:
            high_g_an = mid_g_an
            high = mid

    raise COMError(
        "solve_g_an did not converge within the bisection iteration budget: "
        f"target={target_delta_com_an:.6g} dB, best_g_an={best.g_an:.6g}, "
        f"best_residual={best.residual_dB:.6g} dB, cvg_th={cvg_th:.6g} dB."
    )


def _pmf_variance(pmf: Pmf1D) -> float:
    """Return the variance of one normalized PMF on its physical x grid."""
    mean = float(np.sum(pmf.pmf * pmf.x))
    return float(np.sum(pmf.pmf * (pmf.x - mean) ** 2))


def _build_scaled_total_pdf_added_noise(
    target_delta_com_an: float,
    post_ffe: COMImpStageStatus,
    pmf_dfe: COMPMFStatus,
    der_0: float,
    *,
    scaling_method: Literal["mass_deposit", "interpolate_ordinates"],
) -> COMAddedNoiseStatus:
    """Build the MATLAB 4.17 reference p_an by scaling the complete DFE PDF."""
    if pmf_dfe.p_combined is None:
        raise ValueError("scaled_total_pdf requires the complete COM_DFE PMF.")
    post_psd = post_ffe.psd
    if post_psd is None or post_psd.S_rn is None or post_psd.sigma_G is None:
        raise ValueError(
            "scaled_total_pdf requires post-FFE receiver-noise PSD S_rn and sigma_G."
        )

    scale = float(10.0 ** (float(target_delta_com_an) / 20.0))
    p_ref = pmf_dfe.p_combined
    p_an = p_ref.scale_x(
        scale,
        keep_dx=True,
        dx_ref=p_ref.dx,
        method=scaling_method,
    )
    variance_ref = _pmf_variance(p_ref)
    variance_an = _pmf_variance(p_an)
    receiver_variance = float(post_psd.S_rn.to_sigma() ** 2)
    variance_added = variance_an - variance_ref
    if receiver_variance <= 0.0 or variance_added < -1e-15:
        raise COMError(
            "scaled_total_pdf produced invalid added-noise variance: "
            f"added={variance_added!r}, receiver={receiver_variance!r}."
        )
    variance_added = max(0.0, variance_added)
    g_an = variance_added / receiver_variance
    S_an = SampledPSD(
        theta=post_psd.S_rn.theta,
        psd=g_an * post_psd.S_rn.psd,
        fb=post_psd.S_rn.fb,
        cfg=post_psd.S_rn.cfg,
    )
    A_ref = abs(float(p_ref.quantile(der_0)))
    A_an = abs(float(p_an.quantile(der_0)))
    if A_ref <= 0.0 or A_an <= 0.0:
        raise COMError("scaled_total_pdf requires positive reference-tail amplitudes.")
    return COMAddedNoiseStatus(
        g_an=float(g_an),
        S_an=S_an,
        sigma_an=float(np.hypot(post_psd.sigma_G, S_an.to_sigma())),
        p_an=p_an,
        delta_com_an_temp=float(20.0 * np.log10(A_an / A_ref)),
        target_delta_com_an=float(target_delta_com_an),
        residual_dB=float(20.0 * np.log10(A_an / A_ref) - target_delta_com_an),
        iterations=0,
        sigma_added=float(S_an.to_sigma()),
        A_ref=A_ref,
        A_an=A_an,
    )


def _build_mlsd_sequence_vector(j: int, b_lim_1: float) -> np.ndarray:
    """Build Eq. (178A-49) using the specification's one-based i index."""
    u_j = np.empty(j + 1, dtype=float)
    u_j[0] = 1.0
    if j > 1:
        indices = np.arange(2, j + 1, dtype=int)
        u_j[1:j] = ((-1.0) ** (indices - 1)) * (1.0 - b_lim_1)
    # The last element is i=j+1 in Eq. (178A-49).  Its Python position is j,
    # but converting the array subscript does not change the equation exponent.
    u_j[j] = ((-1.0) ** (j + 1)) * b_lim_1
    return u_j


def _reference_cdf_ev(pmf: Pmf1D, positive_threshold: float) -> float:
    """Match MATLAB CDF_ev: first PMF grid point x >= -threshold."""
    index = int(np.searchsorted(pmf.x, -float(positive_threshold), side="left"))
    index = min(max(index, 0), len(pmf.pmf) - 1)
    return float(pmf.cdf[index])


def calculate_der_mlsd(
    p_an: Pmf1D,
    R_ni: np.ndarray,
    *,
    L: int,
    As: float,
    b_lim_1: float,
    trunc_len: int,
    pmf_scaling_method: Literal["mass_deposit", "interpolate_ordinates"] = "mass_deposit",
    sequence_termination: Literal["fixed_length_sum", "matlab_relative_tail"] = "fixed_length_sum",
) -> tuple[float, np.ndarray]:
    """Evaluate the truncated Annex 178A MLSD detector error ratio.

    This function implements Eqs. (178A-48), (178A-49), (178A-52), and
    (178A-53). ``p_j`` is deliberately local: it is only the state needed to
    construct the next sequence-length term.  The returned ``der_by_j`` holds
    the weighted Eq. (178A-48) contribution for each ``j=1..trunc_len``;
    therefore ``der_by_j.sum()`` is the truncated ``DER_MLSD``.

    The caller supplies the Eq. (178A-51) added-noise PDF and Eq. (178A-54)
    autocorrelation directly. Neither input is modified.
    """
    if not isinstance(p_an, Pmf1D):
        raise TypeError("p_an must be a Pmf1D.")

    L = int(L)
    if L < 2:
        raise ValueError("L must be at least 2 for PAM MLSD.")

    As = float(As)
    if not np.isfinite(As) or As <= 0.0:
        raise ValueError("As must be finite and positive.")

    b_lim_1 = float(b_lim_1)
    if not np.isfinite(b_lim_1) or b_lim_1 == 0.0:
        raise ValueError("b_lim_1 must be finite and non-zero for MLSD.")

    trunc_len = int(trunc_len)
    if trunc_len <= 0:
        raise ValueError("trunc_len must be positive.")
    if trunc_len > 1 and b_lim_1 == 1.0:
        raise ValueError(
            "b_lim_1 must differ from one when trunc_len is greater than one."
        )

    if R_ni is None:
        raise ValueError("R_ni is required before calculating DER_MLSD.")
    R_ni = np.asarray(R_ni)
    if R_ni.ndim != 1 or R_ni.size < trunc_len + 1:
        raise COMLengthMismatchError(
            "MLSD R_ni must be one-dimensional with at least trunc_len + 1 "
            f"entries; got shape {R_ni.shape}, trunc_len={trunc_len}."
        )
    if np.iscomplexobj(R_ni) and not np.allclose(R_ni.imag, 0.0, atol=1e-15):
        raise ValueError("MLSD R_ni must be real-valued.")
    R_ni = np.asarray(R_ni.real, dtype=float)
    if not np.all(np.isfinite(R_ni)) or R_ni[0] <= 0.0:
        raise ValueError("MLSD R_ni must be finite with positive R_ni[0].")

    # This local import keeps scipy confined to the normalized Toeplitz V_j
    # described after Eq. (178A-54).
    from scipy.linalg import toeplitz

    der_by_j = np.empty(trunc_len, dtype=float)
    p_j: Optional[Pmf1D] = None
    # Eq. (178A-52): p_an(y / b_1) / |b_1| is the PDF of +b_1 times the noise.
    p_1_term = p_an.scale_x(
        b_lim_1,
        keep_dx=True,
        dx_ref=p_an.dx,
        method=pmf_scaling_method,
    )
    p_later_term: Optional[Pmf1D] = None
    if trunc_len > 1:
        # Eq. (178A-53): the recurrence adds (1 - b_1) times the noise.
        p_later_term = p_an.scale_x(
            1.0 - b_lim_1,
            keep_dx=True,
            dx_ref=p_an.dx,
            method=pmf_scaling_method,
        )

    if sequence_termination not in {"fixed_length_sum", "matlab_relative_tail"}:
        raise ValueError(
            "sequence_termination must be fixed_length_sum or matlab_relative_tail."
        )
    p_trunc = p_an
    truncation_term: Optional[float] = None

    for j in range(1, trunc_len + 1):
        if j == 1:
            # Eq. (178A-52): convolve p_an with the scaled first term.
            # scale_x includes the PDF's 1 / |b_1| normalization.
            p_j = p_an.combine(p_1_term, name="MLSD p_1")
        else:
            assert p_j is not None and p_later_term is not None
            # Eq. (178A-53): recur with the scaled later term; scale_x
            # includes the PDF's 1 / |1 - b_1| normalization.
            p_j = p_j.combine(p_later_term, name=f"MLSD p_{j}")

        # Eq. (178A-49), including its one-based i=j+1 final element.
        u_j = _build_mlsd_sequence_vector(j, b_lim_1)

        # The Toeplitz V_j defined after Eq. (178A-54), normalized by R_ni(0).
        V_j = toeplitz(R_ni[:j + 1] / R_ni[0])
        quadratic = float(u_j @ V_j @ u_j)
        norm_sq = float(u_j @ u_j)
        if not np.isfinite(quadratic) or quadratic <= 0.0:
            raise COMError(
                f"MLSD V_{j} produced invalid u_j^T V_j u_j={quadratic!r}."
            )
        # Eq. (178A-48): evaluate the CDF P_j at its u_j/V_j threshold.
        threshold = -As * norm_sq ** 1.5 / np.sqrt(quadratic)
        der_event = (
            _reference_cdf_ev(p_j, -threshold)
            if sequence_termination == "matlab_relative_tail"
            else float(p_j.cdf_at(threshold))
        )
        if not np.isfinite(der_event) or not 0.0 <= der_event <= 1.0:
            raise COMError(
                f"MLSD p_{j} CDF produced invalid event probability {der_event!r}."
            )

        # Eq. (178A-48), including the probability of a j-event sequence.
        der_by_j[j - 1] = ((L - 1.0) / L) ** (j - 1) * der_event

        if sequence_termination == "matlab_relative_tail":
            if j == trunc_len:
                # MATLAB 4.17 truncation penalty drops the final u_j element and
                # evaluates the separately accumulated p_trunc distribution.
                u_trunc = u_j[:j]
                V_trunc = V_j[:j, :j]
                trunc_quadratic = float(u_trunc @ V_trunc @ u_trunc)
                trunc_norm_sq = float(u_trunc @ u_trunc)
                trunc_threshold = -As * trunc_norm_sq ** 1.5 / np.sqrt(trunc_quadratic)
                truncation_term = float(
                    L
                    * ((L - 1.0) / L) ** (j - 1)
                    * _reference_cdf_ev(p_trunc, -trunc_threshold)
                )
            elif j < trunc_len:
                assert p_later_term is not None
                p_trunc = p_trunc.combine(p_later_term, name=f"MLSD p_trunc_{j}")

    if not np.all(np.isfinite(der_by_j)) or np.any(der_by_j < 0.0):
        raise COMError("MLSD DER contributions must be finite and non-negative.")

    # Eq. (178A-48): sum the truncated j-event contributions.
    DER_MLSD = float(np.sum(der_by_j))
    if sequence_termination == "matlab_relative_tail":
        assert truncation_term is not None
        DER_MLSD = float(np.sum(der_by_j[:-1]) + truncation_term)
    return DER_MLSD, der_by_j


class COM:
    """
    IEEE 802.3 Annex 178A COM calculator.

    Class boundary
    --------------
    COM owns the versioned 178A algorithm pipeline:
    - build_all_paths()
    - outer-loop sampling phase search
    - calculate_pre_dte_imp_common()
    - calculate_pre_dte_imp_at_pos()
    - calculate_post_ffe_imp()
    - calculate_MMSE_DTE()
    - calculate_COM()

    Path building, impairment, MMSE-DTE, status ownership, and orchestration are
    explicit 178A responsibilities. Outer TXFFE/CTLE search remains a separate
    file-backed workflow and ranks candidates by minimum DTE MSE.
    """

    def __init__(self, cfg: COMConfig):
        self.cfg = cfg
        self.noise_link_cfg = cfg.policy.resolve_noise_grid(cfg.link)
        self.status: Optional[COMStatus | COMSearchStatus] = None

    def _effective_run_cfg(self, run_cfg: COMRunConfig) -> COMRunConfig:
        """Return the run profile already resolved by the input adapter."""
        return self.cfg.resolve_run_cfg(run_cfg)

    @staticmethod
    def _validate_victim_time_alignment(victim: COMPath) -> None:
        """Guard the victim H21 and pulse against IFFT precursor wrap."""
        victim.H_21.validate_causal_ir(
            victim.H_21.ir,
            source_name="victim H_21 causal_ir",
        )
        victim.pulse.validate_causal_ir(
            victim.pulse.ir,
            source_name="victim pulse causal_ir",
        )

    def run(
        self,
        search: Optional[COMSearchConfig] = None,
        *,
        report_dir: Optional[str | Path] = None,
        progress: bool = False,
    ) -> COMStatus | COMSearchStatus:
        """Run the configured single profile or delegate file-backed search.

        ``progress`` prints single-run stage/phase timing for interactive
        debugging only. Search execution deliberately remains file-backed and
        does not emit this per-phase reporting.
        """
        if search is None:
            self.status = self._run_once(
                run_cfg=self.cfg.execution.single_run,
                progress=progress,
            )
        else:
            if report_dir is None:
                raise ValueError(
                    "178A search requires report_dir. Use the case path "
                    "cases/<case_id>/report/178A/search_run."
                )
            self.status = run_full_search(self.cfg, search, report_dir)
        return self.status

    def _run_once(self, *, run_cfg: COMRunConfig, progress: bool = False) -> COMStatus:
        """
        Run one concrete 178A COMConfig point under one execution profile.

        178A pipeline:
        paths -> pre-DTE common impairment cache ->
        pre-DTE impairment(pos) / MMSE-DTE(pos) sweep -> selected target.

        ``target="mse"`` returns after the best valid DTE result.
        ``target="dfe"`` additionally produces post-FFE impairment and DFE
        COM PMFs. ``target="mlsd"`` includes that DFE baseline and then runs
        the enabled MLSD receiver stage. ``target="full"`` includes MLSD only
        when ``cfg.mlsd.enable`` is true.
        """
        run_cfg = self._effective_run_cfg(run_cfg)
        self.status = COMStatus()
        started = perf_counter()

        mlsd_requested = run_cfg.target == "mlsd" or (
            run_cfg.target == "full" and self.cfg.mlsd.enable
        )
        if run_cfg.target == "mlsd" and not self.cfg.mlsd.enable:
            raise ValueError("target='mlsd' requires cfg.mlsd.enable=True.")
        if mlsd_requested and self.cfg.dte.N_b != 1:
            raise ValueError(
                "Annex 178A MLSD requires the receiver DTE configuration to use N_b=1."
            )

        def report(message: str) -> None:
            if progress:
                elapsed_s = perf_counter() - started
                print(f"[178A single-run +{elapsed_s:8.2f} s] {message}", flush=True)

        # stage 1: build all paths
        report("build_all_paths: start")
        paths = self.build_all_paths()
        self._assign_paths(paths)
        victim = paths[0]
        xtalk_paths = paths[1:]
        self._validate_victim_time_alignment(victim)
        h_XTs = [path.pulse.ir for path in xtalk_paths]
        report(f"build_all_paths: done ({len(paths)} paths)")

        # stage 2: calculate pre-DTE impairment common cache
        report("pre_dte_imp_common: start")
        pre_dte_imp_common, h_XTs_dsamp = self.calculate_pre_dte_imp_common(
            victim=victim,
            h_XTs=h_XTs,
        )
        report("pre_dte_imp_common: done")

        # ===========================
        # pos sweeping
        # ===========================
        run_status = COMRunStatus(
            pmf_grid_quality=run_cfg.pmf_grid_quality,
            pmf_keep_mass=run_cfg.pmf_keep_mass,
            mse_by_pos=[None] * self.per_ui,
            main_cursor_error_by_pos=[None] * self.per_ui,
        )
        self._assign_run(run_status)
        best_dte: Optional[COMDTEStatus] = None
        best_imp_pre: Optional[COMImpairmentStatus] = None

        def evaluate_pos_indices(pos_indices: list[int], phase_label: str) -> None:
            nonlocal best_dte, best_imp_pre
            for pos in pos_indices:
                pos_started = perf_counter()
                try:
                    report(f"{phase_label} pos {pos + 1}/{self.per_ui}: start")
                    imp_pre, dte_status = self.calculate_pos_candidate(
                        victim=victim,
                        pos=pos,
                        common=pre_dte_imp_common,
                        h_XTs_dsamp=h_XTs_dsamp,
                        run_cfg=run_cfg,
                    )
                except COMMainCursorError as error:
                    run_status.main_cursor_error_by_pos[pos] = str(error)
                    report(f"{phase_label} pos {pos + 1}/{self.per_ui}: skipped (main cursor error)")
                    continue

                run_status.mse_by_pos[pos] = float(dte_status.mse)
                is_best = best_dte is None or dte_status.mse < best_dte.mse
                if is_best:
                    best_dte = dte_status
                    best_imp_pre = imp_pre
                report(
                    f"{phase_label} pos {pos + 1}/{self.per_ui}: done in "
                    f"{perf_counter() - pos_started:.2f} s; mse={dte_status.mse:.6e}"
                    f"{' (best)' if is_best else ''}"
                )

        coarse_pos_indices = self._initial_pos_sweep_indices(run_cfg)
        run_status.coarse_pos = list(coarse_pos_indices)
        report(f"pos sweep ({run_cfg.pos_sweep_method}): {coarse_pos_indices}")
        initial_label = "phase" if run_cfg.pos_sweep_method == "each_phase" else "coarse"
        evaluate_pos_indices(coarse_pos_indices, initial_label)

        if run_cfg.pos_sweep_method == "coarse_fine":
            if best_dte is None:
                raise RuntimeError("Coarse phase sweep did not produce any valid sampling phase candidate.")
            fine_pos_indices = self._fine_pos_sweep_indices(
                coarse_best_pos=best_dte.pos,
                run_cfg=run_cfg,
                evaluated_indices=set(coarse_pos_indices),
            )
            run_status.fine_pos = list(fine_pos_indices)
            report(f"pos sweep fine around pos={best_dte.pos}: {fine_pos_indices}")
            evaluate_pos_indices(fine_pos_indices, "fine")

        if best_dte is None or best_imp_pre is None:
            raise RuntimeError("COM did not produce any valid sampling phase candidate.")

        self._assign_dte(best_dte)
        self._merge_imp(best_imp_pre)
        report(f"pos sweep: selected pos={best_dte.pos}, mse={best_dte.mse:.6e}")

        if run_cfg.target == "mse":
            report("single-run complete (target=mse)")
            return self._require_status()

        report("post_ffe_imp: start")
        imp_status = self.calculate_post_ffe_imp(
            dte_status=best_dte,
            imp_pre=best_imp_pre,
            h=victim.pulse.ir,
            run_cfg=run_cfg,
        )
        self._merge_imp(imp_status)
        report("post_ffe_imp: done")

        merged_imp_status = self._require_status().imp
        if not isinstance(merged_imp_status, COMImpairmentStatus):
            raise RuntimeError("Merged 178A impairment status is not available after post-FFE impairment.")

        if run_cfg.target in {"dfe", "mlsd", "full"}:
            report("calculate_COM_DFE: start")
            self._assign_pmf(self.calculate_COM_DFE(merged_imp_status, best_dte, run_cfg=run_cfg))
            report("calculate_COM_DFE: done")

        if mlsd_requested:
            report("calculate_COM_MLSD: start")
            self.calculate_COM_MLSD(run_cfg=run_cfg)
            report("calculate_COM_MLSD: done")
        report("single-run complete")
        return self._require_status()

    def _assign_paths(self, paths: list[COMPath]) -> None:
        """Assign build-path stage output into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.paths = paths

    def _assign_dte(self, dte_status: COMDTEStatus) -> None:
        """Assign selected DTE stage output into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.dte = dte_status

    def _assign_run(self, run_status: COMRunStatus) -> None:
        """Assign run-local status that is accumulated across the sampling-phase sweep."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.run = run_status

    def _merge_imp(self, imp_status: COMImpairmentStatus) -> None:
        """Merge one 178A impairment stage output into the incremental status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        if self.status.imp is None:
            self.status.imp = COMImpairmentStatus()
        if not isinstance(self.status.imp, COMImpairmentStatus):
            raise TypeError("COM status.imp must be COMImpairmentStatus.")
        current = self.status.imp
        if imp_status.eq_ch is not None:
            current.eq_ch = imp_status.eq_ch
        if imp_status.H_rxffe is not None:
            current.H_rxffe = imp_status.H_rxffe
        for name in ("pre_dte", "post_ffe"):
            value = getattr(imp_status, name)
            if value is not None:
                setattr(current, name, value)

    def _assign_pmf(self, pmf_status: Optional[COMPMFStatus]) -> None:
        """Assign COM DFE PMF stage output into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.pmf = pmf_status

    def _assign_mlsd(self, mlsd_status: COMMLSDStatus) -> None:
        """Assign MLSD-only status into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.mlsd = mlsd_status

    def _require_status(self) -> COMStatus:
        if self.status is None:
            raise RuntimeError("COM status is not available. Run COM.run() first.")
        if isinstance(self.status, COMSearchStatus):
            return self.status.best
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
    def h_dsamp(self) -> np.ndarray:
        """Victim pulse response sampled at the selected DFE sampling phase."""
        dte = self.dte_status
        if dte is None:
            raise RuntimeError("COM.dte_status is not available. Run COM.run() first.")
        return self.h[dte.pos::self.per_ui]

    @property
    def t_dsamp_ui(self) -> np.ndarray:
        """Discrete UI axis for h_dsamp with the selected main cursor at zero."""
        dte = self.dte_status
        if dte is None:
            raise RuntimeError("COM.dte_status is not available. Run COM.run() first.")
        num_pre = (dte.ts - dte.pos) // self.per_ui
        return np.arange(len(self.h_dsamp), dtype=float) - float(num_pre)

    @property
    def h_XT(self) -> list[np.ndarray]:
        """Crosstalk pulse responses h^(k)(t), k > 0."""
        return [path.pulse.ir for path in self.xtalks]

    @property
    def dte_status(self) -> Optional[COMDTEStatus]:
        return self._require_status().dte

    @property
    def imp_status(self) -> Optional[COMImpairmentStatus]:
        return self._require_status().imp

    @property
    def pmf_status(self) -> Optional[COMPMFStatus]:
        return self._require_status().pmf

    @property
    def mlsd_status(self) -> Optional[COMMLSDStatus]:
        return self._require_status().mlsd

    def build_all_paths(self) -> list[COMPath]:
        """
        Build all 178A COM paths.

        LV-1 hierarchy mirrors com_93A.COM:
        1. build channel-under-test models
        2. build path-shared models
        3. build every path-specific model
        """
        channels = _build_channel_under_test(
            self.cfg.channel, self.cfg.policy.channel_renormalization_order,
        )
        shared = _build_shared_path(self.cfg, channels[0].freqs)
        return _build_paths(self.cfg, shared, channels)

    def calculate_pre_dte_imp_common(
        self,
        victim: COMPath,
        h_XTs: list[np.ndarray],
    ) -> tuple[COMPSDStatus, list[np.ndarray]]:
        """
        Calculate pre-DTE impairment components that do not depend on phase.

        Parameters
        ----------
        victim:
            Victim COMPath for the current TX FFE/CTLE/channel candidate.
        h_XTs:
            Crosstalk pulse responses in V. Each crosstalk PSD uses its own
            worst-case sampling phase as defined below Eq. 178A-18.

        Returns
        -------
        tuple[COMPSDStatus, list[np.ndarray]]
            Cached receiver/crosstalk PSD terms and crosstalk sampled
            sequences. This is a run-local cache, not a standalone status
            stage; the selected pre-DTE result records these terms later.
        """
        link_cfg = self.cfg.link
        noise_link_cfg = self.noise_link_cfg
        imp_cfg = self.cfg.imp
        ft_cfg = self.cfg.filter
        L = self.cfg.L

        del victim
        if any(np.asarray(h_xt).ndim != 1 for h_xt in h_XTs):
            raise ValueError("Each crosstalk pulse response must be a one-dimensional array.")

        # input signal power
        sigma_X = np.sqrt((L**2 - 1) / (3 * (L - 1)**2))

        # Receiver input noise PSD
        S_rn = _build_psd_rx_noise(noise_link_cfg, imp_cfg, ft_cfg)
        sigma_rn = S_rn.to_sigma()

        # Crosstalk PSD
        S_xn, h_XTs_dsamp = _build_psd_xtalk(
            h_XTs,
            link_cfg,
            sigma_X,
            noise_link_cfg=noise_link_cfg,
            noise_grid=self.cfg.policy,
        )
        sigma_xn = S_xn.to_sigma()

        return (
            COMPSDStatus(
                sigma_X=sigma_X,
                S_rn=S_rn,
                sigma_rn=sigma_rn,
                S_xn=S_xn,
                sigma_xn=sigma_xn,
            ),
            h_XTs_dsamp,
        )

    def calculate_pre_dte_imp_at_pos(
        self,
        victim: COMPath,
        pos: int,
        common: COMPSDStatus,
        h_XTs_dsamp: list[np.ndarray],
        run_cfg: COMRunConfig,
    ) -> COMImpairmentStatus:
        """
        Calculate complete pre-DTE impairment status for one phase candidate.

        This stage combines common PSD terms with the candidate-dependent TX
        noise, jitter, and ADC quantization PSDs before solving the receiver
        discrete-time equalizer.

        Parameters
        ----------
        victim:
            Victim COMPath. The method uses victim.pulse.ir for the signal
            pulse and victim.H_t/H_21/H_r/H_ctf for the no-FFE TX-noise pulse.
        pos:
            Sample phase index in [0, cfg.link.per_ui).
        common:
            Sampling-phase-independent impairment components computed once by
            calculate_pre_dte_imp_common().
        run_cfg:
            Execution profile providing the pre-DTE quantization method.

        Notes
        -----
        The selected sampling metadata is not an impairment result. ``pos``
        and the derived oversampled main-cursor index ``ts`` are stored only
        by the subsequent COMDTEStatus.
        """
        run_cfg = self._effective_run_cfg(run_cfg)
        link_cfg = self.cfg.link
        imp_cfg = self.cfg.imp
        ft_cfg = self.cfg.filter
        L = self.cfg.L
        pos = int(pos)
        if pos < 0 or pos >= link_cfg.per_ui:
            raise ValueError("pos must be in [0, link_cfg.per_ui).")
        if common.sigma_X is None or common.S_rn is None or common.S_xn is None:
            raise ValueError(
                "common must be the complete output of "
                "calculate_pre_dte_imp_common()."
            )
        # The common stage owns the concrete noise-grid object. Reuse that
        # exact reference so equivalent COMConfig copies can consume a cached
        # common result without violating SampledPSD's shared-grid contract.
        noise_link_cfg = common.S_rn.cfg or self.noise_link_cfg
        if not isinstance(h_XTs_dsamp, list) or any(
            np.asarray(h_xt_dsamp).ndim != 1 for h_xt_dsamp in h_XTs_dsamp
        ):
            raise ValueError(
                "h_XTs_dsamp must be the list of one-dimensional sampled "
                "crosstalk responses returned by calculate_pre_dte_imp_common()."
            )
        pmf_cfg = _resolve_adc_input_pmf_config(
            self.cfg.pmf,
            imp_cfg.R_LM / (L - 1),
            run_cfg,
            gaussian_n_sigma_override=self.cfg.policy.gaussian_n_sigma_override,
        )
        
        h_dsamp = victim.pulse.ir[pos::link_cfg.per_ui]
        if len(h_dsamp) == 0:
            raise ValueError("Selected sampling phase produces an empty victim sequence.")
        _validate_positive_main_cursor(
            h_dsamp,
            source_name="calculate_pre_dte_imp_at_pos.h_dsamp",
            pos=pos,
        )
        h_dsamp_response = SampledResponse.from_ir(h_dsamp, link_cfg)
        
        # From common_psd
        sigma_X = common.sigma_X
        S_rn = common.S_rn
        S_xn = common.S_xn

        # transmitter output noise PSD, Eq. 178A-19 and Eq. 178A-20.
        S_tn, h_tn = _build_psd_tx_noise(
            victim,
            link_cfg,
            self.cfg.channel,
            ft_cfg,
            imp_cfg,
            pos,
            self.cfg.policy.ctle_pulse_realization,
            noise_link_cfg=noise_link_cfg,
            noise_grid=self.cfg.policy,
        )
        sigma_tn = S_tn.to_sigma()

        # transmitter jitter-induced noise PSD, Eq. 178A-21 and Eq. 178A-22.
        S_jn, h_J = _build_psd_tx_jitter(
            victim,
            link_cfg,
            imp_cfg,
            pos,
            sigma_X,
            noise_link_cfg=noise_link_cfg,
            noise_grid=self.cfg.policy,
        )
        sigma_jn = S_jn.to_sigma()

        # quantization noise
        p_sig = _build_pmf_pam_L(
            L, pmf_cfg, placement=self.cfg.policy.discrete_pmf_placement,
        )
        # Keep the full Eq. (178A-21)/(178A-22) jitter term in the MMSE
        # covariance. Only the ADC clipping input changes in the reference
        # comparison branch.
        S_ga = S_rn.add(S_xn).add(S_tn).add(S_jn)
        if self.cfg.policy.pre_dte_adc_clipping_convention == "matlab_4_17_reference_only":
            S_jn_clip = _build_psd_from_DFT_response(
                self.cfg.policy.fit_noise_response(h_J),
                noise_link_cfg,
                sigma_X**2 * imp_cfg.sigma_RJ**2,
            )
            S_clip = S_rn.add(S_xn).add(S_tn).add(S_jn_clip)
            cdf_tail = imp_cfg.P_qc
        else:
            S_clip = S_ga
            cdf_tail = None  # Preserve the Annex P_qc/2 default.
        sigma_clip = S_clip.to_sigma()
        if imp_cfg.N_qb is None or imp_cfg.P_qc is None:
            S_qn = _zero_sampled_psd(noise_link_cfg)
            adc_input_pmf = COMAdcInputPMF(p_sig=p_sig, method="disabled")
        else:
            S_qn, adc_input_pmf = _build_psd_adc_qn(
                p_sig = p_sig, 
                h_dsamp = h_dsamp,
                sigma_ga = sigma_clip,
                P_qc = imp_cfg.P_qc,
                N_qb = imp_cfg.N_qb,
                pmf_cfg = pmf_cfg, 
                link_cfg = noise_link_cfg,
                vqc_method=run_cfg.pre_dte_pmf_method,
                cdf_tail=cdf_tail,
                L=L,
                pmf_methods=self.cfg.policy,
            )
        adc_input_pmf.clipping_convention = self.cfg.policy.pre_dte_adc_clipping_convention
        sigma_qn = S_qn.to_sigma()

        # summation and IDFT
        # 但如果 N_max 太接近 FFT 長度，或者 noise correlation 在長時間 lag 還沒衰減完，
        # R_n 尾端的能量會 circular wrap 回前面，使得前幾個 lag 被污染。
        S_total = S_ga.add(S_qn)
        sigma_total = S_total.to_sigma()
        R_n = S_total.to_autocorrelation()

        return COMImpairmentStatus(
            pre_dte=COMImpStageStatus(
                psd=COMPSDStatus(
                sigma_X=sigma_X,
                S_rn=S_rn,
                sigma_rn=common.sigma_rn,
                S_xn=S_xn,
                sigma_xn=common.sigma_xn,
                S_tn=S_tn,
                sigma_tn=sigma_tn,
                S_jn=S_jn,
                sigma_jn=sigma_jn,
                S_qn=S_qn,
                sigma_qn=sigma_qn,
                S_total=S_total,
                sigma_total=sigma_total,
                R_n=R_n,
                ),
                adc_input=adc_input_pmf,
            ),
            eq_ch=COMEqChannelStatus(
                h_XTs_dsamp=[SampledResponse.from_ir(h_xt, link_cfg) for h_xt in h_XTs_dsamp],
                h_dsamp=h_dsamp_response,
                h_tn=SampledResponse.from_ir(h_tn, link_cfg),
                h_J=SampledResponse.from_ir(h_J, link_cfg),
            ),
        )

    def calculate_pos_candidate(
        self,
        victim: COMPath,
        pos: int,
        common: COMPSDStatus,
        h_XTs_dsamp: list[np.ndarray],
        run_cfg: COMRunConfig,
    ) -> tuple[COMImpairmentStatus, COMDTEStatus]:
        """Calculate one sampling phase's pre-DTE impairment and MMSE-DTE result."""
        imp_pre = self.calculate_pre_dte_imp_at_pos(
            victim=victim,
            pos=pos,
            common=common,
            h_XTs_dsamp=h_XTs_dsamp,
            run_cfg=run_cfg,
        )
        dte_status = self.calculate_MMSE_DTE(
            victim=victim,
            imp_pre=imp_pre,
            pos=pos,
            run_cfg=run_cfg,
        )
        return imp_pre, dte_status

    def _initial_pos_sweep_indices(self, run_cfg: COMRunConfig) -> list[int]:
        """Return the first phase set for exhaustive or coarse-fine sampling."""
        if run_cfg.pos_sweep_method == "each_phase":
            return list(range(self.per_ui))
        if run_cfg.pos_coarse_stride > self.per_ui:
            raise ValueError(
                "COMRunConfig.pos_coarse_stride must not exceed LinkConfig.per_ui."
            )
        return list(range(0, self.per_ui, run_cfg.pos_coarse_stride))

    def _fine_pos_sweep_indices(
        self,
        *,
        coarse_best_pos: int,
        run_cfg: COMRunConfig,
        evaluated_indices: set[int],
    ) -> list[int]:
        """Return unvisited integer phases in the circular fine window."""
        radius = (run_cfg.pos_coarse_stride + 1) // 2
        window = [
            (coarse_best_pos + offset) % self.per_ui
            for offset in range(-radius, radius + 1)
        ]
        return [pos for pos in window if pos not in evaluated_indices]

    def calculate_MMSE_DTE(
        self,
        victim: COMPath,
        imp_pre: COMImpairmentStatus,
        pos: int,
        run_cfg: COMRunConfig,
    ) -> COMDTEStatus:
        """
        Calculate 178A MMSE DTE status for one sampling-phase candidate.

        This stage only owns FFE/DFE coefficient solving and MSE. Residual ISI
        response construction belongs to the post-DTE impairment/PMF path, not
        COMDTEStatus.
        """
        h_dsamp = imp_pre.h_dsamp.ir
        solver = COM_MMSE_DTE(
            self.cfg.dte,
            run_cfg.floating_mode,
        )
        dte_status = solver.run(
            h_dsamp = h_dsamp,
            R_n = imp_pre.R_n,
            sigma_x = imp_pre.sigma_X,
            pos = pos,
            per_ui = self.per_ui,
        )
        return dte_status

    def calculate_post_ffe_imp(
        self,
        dte_status: COMDTEStatus,
        imp_pre: COMImpairmentStatus,
        h: np.ndarray,
        run_cfg: COMRunConfig,
    ) -> COMImpairmentStatus:
        """Finalize selected-phase equivalent responses and post-DTE diagnostics.

        The post-DTE component PSDs are 93A-aligned reporting quantities on the
        run-level sampled grid. DFE COM consumes the separately calculated
        Gaussian sigma, ADC-input clipping material, and equivalent responses;
        changing reporting PSD construction must not change MSE or COM.
        """
        As = self.cfg.imp.R_LM / (self.cfg.L - 1)

        w_lim_ndarray = np.asarray(dte_status.w_lim, dtype=float)
        expected_shape = (int(self.cfg.dte.N_max),)
        if w_lim_ndarray.shape != expected_shape:
            raise COMLengthMismatchError(
                "calculate_post_ffe_imp() requires COMDTEStatus.w_lim to be the "
                f"full zero-filled FFE tap vector with shape {expected_shape}, "
                f"got {w_lim_ndarray.shape}."
            )
        if not np.all(np.isfinite(w_lim_ndarray)):
            raise ValueError("COMDTEStatus.w_lim contains non-finite values.")

        nonzero_w = np.flatnonzero(w_lim_ndarray != 0.0)
        w_finite = (
            w_lim_ndarray[: int(nonzero_w[-1]) + 1]
            if len(nonzero_w)
            else w_lim_ndarray[:1]
        )
        noise_link_cfg = imp_pre.S_rn.cfg or self.noise_link_cfg
        w_lim_pre = SampledResponse.from_ir(w_lim_ndarray, noise_link_cfg)

        h_w = _apply_rxffe_response(
            imp_pre.h_dsamp,
            w_lim_ndarray,
            self.cfg.link,
            self.cfg.policy.rxffe_record_realization,
            "post_ffe victim",
        )
        H_rxffe = SampledResponse.from_ir(w_finite, noise_link_cfg)

        h_XTs_w: list[SampledResponse] = []
        for path_index, h_XT_dsamp in enumerate(imp_pre.h_XTs_dsamp, start=1):
            h_XT_w = _apply_rxffe_response(
                h_XT_dsamp,
                w_lim_ndarray,
                self.cfg.link,
                self.cfg.policy.rxffe_record_realization,
                f"post_ffe XT{path_index}",
            )
            h_XTs_w.append(h_XT_w)

        h_ISI_ndarray = h_w.ir.copy()
        d = int(dte_status.d)
        dfe_stop = d + 1 + len(dte_status.b_lim)
        if d < 0 or d >= len(h_ISI_ndarray) or dfe_stop > len(h_ISI_ndarray):
            raise COMLengthMismatchError(
                "DTE main cursor or feedback taps exceed the post-DTE response: "
                f"d={d}, feedback_stop={dfe_stop}, len(h_w)={len(h_ISI_ndarray)}."
            )
        h_ISI_ndarray[d] = 0.0
        h_ISI_ndarray[d + 1:dfe_stop] -= dte_status.b_lim
        h_ISI_noise = self.cfg.policy.fit_noise_response(h_ISI_ndarray)
        h_ISI = SampledResponse.from_ir(h_ISI_noise, noise_link_cfg)
        sigma_ISI = float(imp_pre.sigma_X * np.sqrt(np.sum(h_ISI.ir**2)))

        # DDJ uses the original selected-phase construction: take the two
        # adjacent victim-pulse phases through the FFE, then difference them.
        h_w_J_ndarray = _calculate_h_J(
            h,
            dte_status.pos,
            self.cfg.link,
            w_finite,
            self.cfg.policy.rxffe_record_realization,
        )
        if self.cfg.policy.rxffe_record_realization == "finite_record_circshift":
            h_w_J = SampledResponse.from_ir(h_w_J_ndarray, self.cfg.link)
        else:
            try:
                h_w_J = SampledResponse.from_linear_ir(h_w_J_ndarray, self.cfg.link)
            except GridOverflowError as error:
                raise error.with_context("post_ffe DDJ") from error

        run_cfg = self._effective_run_cfg(run_cfg)
        # Gaussian DFE-COM branch.  Build RJ on the pre-DTE grid, combine the
        # three Gaussian sources there, and filter once by the pre-grid FFE.
        S_jn_RJ_pre = _build_psd_from_DFT_response(
            self.cfg.policy.fit_noise_response(imp_pre.h_J.ir),
            noise_link_cfg,
            imp_pre.sigma_X**2 * self.cfg.imp.sigma_RJ**2,
        )
        S_G_pre = imp_pre.S_rn.add(imp_pre.S_tn).add(S_jn_RJ_pre)
        sigma_gn_adc = S_G_pre.to_sigma()
        sigma_G = S_G_pre.filtered_by(w_lim_pre).to_sigma()

        # Exact selected-phase ADC-input material remains in the pre-DTE
        # physical domain.  Its delta is then propagated through the FFE below.
        pmf_cfg_adc_input = _resolve_adc_input_pmf_config(
            self.cfg.pmf,
            As,
            run_cfg,
            gaussian_n_sigma_override=self.cfg.policy.gaussian_n_sigma_override,
        )
        p_sig = _build_pmf_pam_L(
            self.cfg.L,
            pmf_cfg_adc_input,
            placement=self.cfg.policy.discrete_pmf_placement,
        )
        if self.cfg.imp.N_qb is None or self.cfg.imp.P_qc is None:
            adc_input_pmf = COMAdcInputPMF(p_sig=p_sig, method="disabled")
        else:
            adc_input_pmf = _build_adc_input_pmf_exact(
                p_sig=p_sig,
                h_dsamp=imp_pre.h_dsamp.ir,
                h_XTs_dsamp=imp_pre.h_XTs_dsamp,
                A_DD=self.cfg.imp.A_DD,
                h_J=imp_pre.h_J.ir,
                sigma_gn=sigma_gn_adc,
                P_qc=self.cfg.imp.P_qc,
                N_qb=self.cfg.imp.N_qb,
                pmf_cfg=pmf_cfg_adc_input,
                L=self.cfg.L,
                pmf_methods=self.cfg.policy,
            )

        # All pre/post-FFE PSDs share the run-level sampled grid.
        S_rn = imp_pre.S_rn.filtered_by(H_rxffe)
        S_tn = imp_pre.S_tn.filtered_by(H_rxffe)

        S_xn = _zero_sampled_psd(noise_link_cfg)
        for h_XT_w in h_XTs_w:
            S_xn = S_xn.add(
                _build_psd_from_DFT_response(
                    self.cfg.policy.fit_noise_response(h_XT_w.ir),
                    noise_link_cfg,
                    imp_pre.sigma_X**2,
                )
            )

        S_jn = _build_psd_from_DFT_response(
            self.cfg.policy.fit_noise_response(h_w_J.ir),
            noise_link_cfg,
            imp_pre.sigma_X**2
            * (self.cfg.imp.A_DD**2 + self.cfg.imp.sigma_RJ**2),
        )

        if adc_input_pmf.delta is None:
            S_qn = _zero_sampled_psd(noise_link_cfg)
        else:
            S_qn_adc = SampledPSD.from_constant(
                noise_link_cfg.theta,
                (adc_input_pmf.delta**2 / 12.0) / noise_link_cfg.fb,
                noise_link_cfg.fb,
                cfg=noise_link_cfg,
            )
            S_qn = S_qn_adc.filtered_by(H_rxffe)

        S_total = S_rn.add(S_xn).add(S_tn).add(S_jn).add(S_qn)

        return COMImpairmentStatus(
            post_ffe=COMImpStageStatus(
                psd=COMPSDStatus(
                    As=As,
                    S_rn=S_rn,
                    sigma_rn=S_rn.to_sigma(),
                    S_xn=S_xn,
                    sigma_xn=S_xn.to_sigma(),
                    S_tn=S_tn,
                    sigma_tn=S_tn.to_sigma(),
                    S_jn=S_jn,
                    sigma_jn=S_jn.to_sigma(),
                    S_qn=S_qn,
                    sigma_qn=S_qn.to_sigma(),
                    S_total=S_total,
                    sigma_total=S_total.to_sigma(),
                    sigma_G=sigma_G,
                    sigma_ISI=sigma_ISI,
                ),
                adc_input=adc_input_pmf,
            ),
            eq_ch=COMEqChannelStatus(
                h_XTs_dsamp=imp_pre.h_XTs_dsamp,
                h_dsamp=imp_pre.h_dsamp,
                h_tn=imp_pre.h_tn,
                h_J=imp_pre.h_J,
                h_w=h_w,
                h_XTs_w=h_XTs_w,
                h_ISI=h_ISI,
                h_w_J=h_w_J,
            ),
            H_rxffe=H_rxffe,
        )

    def build_mlsd_noise(
        self,
        imp_status: COMImpairmentStatus,
        added_noise: COMAddedNoiseStatus,
    ) -> COMMLSDNoiseStatus:
        """Build Eq. (178A-54) MLSD input PSD and autocorrelation once.

        ``S_ni`` and ``R_ni`` are independent of MLSD sequence length ``j``.
        Return them before DER summation without constructing the final MLSD status.
        """
        pre_dte = imp_status.pre_dte
        if pre_dte is None or pre_dte.psd is None or pre_dte.psd.S_total is None:
            raise ValueError(
                "build_mlsd_noise requires pre-FFE total noise PSD S_n."
            )
        S_n = pre_dte.psd.S_total
        H_rxffe = imp_status.H_rxffe
        if not isinstance(H_rxffe, SampledResponse):
            raise TypeError("build_mlsd_noise requires H_rxffe to be a SampledResponse.")
        h_ISI = imp_status.h_ISI
        if not isinstance(h_ISI, SampledResponse):
            raise TypeError(
                "build_mlsd_noise requires h_ISI to be a SampledResponse."
            )
        if not np.isfinite(imp_status.sigma_X) or imp_status.sigma_X < 0.0:
            raise ValueError("build_mlsd_noise requires finite non-negative sigma_X.")

        if (
            S_n.theta.shape != H_rxffe.theta.shape
            or not np.isclose(S_n.fb, H_rxffe.fb)
            or not np.allclose(S_n.theta, H_rxffe.theta, rtol=1e-12, atol=1e-15)
        ):
            raise ValueError("pre-FFE S_n must share the H_rxffe theta grid and fb.")
        for name, psd in (("added_noise.S_an", added_noise.S_an),):
            if (
                psd.theta.shape != H_rxffe.theta.shape
                or not np.isclose(psd.fb, H_rxffe.fb)
                or not np.allclose(psd.theta, H_rxffe.theta, rtol=1e-12, atol=1e-15)
            ):
                raise ValueError(
                    f"{name} must share the H_rxffe theta grid and fb."
                )
        if (
            h_ISI.theta.shape != H_rxffe.theta.shape
            or not np.isclose(h_ISI.fb, H_rxffe.fb)
            or not np.allclose(h_ISI.theta, H_rxffe.theta, rtol=1e-12, atol=1e-15)
        ):
            raise ValueError("h_ISI must share the H_rxffe theta grid and fb.")

        # Eq. (178A-54): S_n is the complete pre-FFE Eq. (178A-15) PSD.
        # The run-level grid is shared, so no intermediate PSD regrid is needed.
        # The Annex path filters every component, including S_qn, by the full
        # RxFFE response.  The reference realization keeps S_qn white and
        # applies only the RxFFE main-tap gain; all other components still use
        # the complete response.
        quantization_method = self.cfg.policy.mlsd_quantization_psd
        source_qn = pre_dte.psd.S_qn
        if quantization_method == "pre_dte_filtered":
            S_n_filtered = S_n.filtered_by(H_rxffe)
            S_qn = source_qn.filtered_by(H_rxffe) if source_qn is not None else None
        elif quantization_method == "main_tap_white":
            if source_qn is None:
                raise ValueError("main_tap_white requires pre-DTE S_qn.")
            if (
                source_qn.theta.shape != H_rxffe.theta.shape
                or not np.isclose(source_qn.fb, H_rxffe.fb)
                or not np.allclose(source_qn.theta, H_rxffe.theta, rtol=1e-12, atol=1e-15)
            ):
                raise ValueError("pre-DTE S_qn must share the H_rxffe theta grid and fb.")
            d_w = int(self.cfg.dte.d_w)
            if d_w < 0 or d_w >= len(H_rxffe.ir):
                raise ValueError("main_tap_white requires d_w within H_rxffe.ir.")
            main_gain = float(H_rxffe.ir[d_w])
            if not np.isfinite(main_gain):
                raise ValueError("main_tap_white requires a finite RxFFE main tap.")
            non_qn = SampledPSD(
                theta=S_n.theta,
                psd=S_n.psd - source_qn.psd,
                fb=S_n.fb,
                cfg=S_n.cfg,
            )
            S_n_filtered = non_qn.filtered_by(H_rxffe)
            S_qn = SampledPSD(
                theta=source_qn.theta,
                psd=source_qn.psd * main_gain**2,
                fb=source_qn.fb,
                cfg=source_qn.cfg,
            )
            S_n_filtered = S_n_filtered.add(S_qn)
        else:
            raise ValueError(f"Unsupported MLSD quantization PSD method: {quantization_method}.")
        # Eq. (178A-54) gives a two-sided ISI density. from_constant() folds
        # interior rFFT bins into SampledPSD's one-sided representation.
        S_isi = SampledPSD.from_constant(
            H_rxffe.theta,
            imp_status.sigma_X**2 / H_rxffe.fb,
            H_rxffe.fb,
            cfg=H_rxffe.cfg,
        ).filtered_by(h_ISI)
        # Eq. (178A-54): sum receiver, added, and ISI noise densities.
        S_ni = S_n_filtered.add(added_noise.S_an).add(S_isi)
        # Eq. (178A-16), as directed by the text after Eq. (178A-54).
        R_ni = S_ni.to_autocorrelation()
        if not np.all(np.isfinite(R_ni)) or R_ni.size == 0 or R_ni[0] <= 0.0:
            raise COMError(
                "Eq. (178A-54) produced an invalid MLSD autocorrelation: "
                f"R_ni[0]={R_ni[0] if R_ni.size else None!r}."
            )

        return COMMLSDNoiseStatus(
            S_isi=S_isi,
            sigma_isi=S_isi.to_sigma(),
            S_ni=S_ni,
            sigma_ni=S_ni.to_sigma(),
            R_ni=R_ni,
            S_qn=S_qn,
            sigma_qn=S_qn.to_sigma() if S_qn is not None else None,
        )

    def calculate_COM_DFE(
        self,
        imp_status: COMImpairmentStatus,
        dte_status: COMDTEStatus,
        run_cfg: Optional[COMRunConfig] = None,
    ) -> COMPMFStatus:
        """
        Calculate 178A final COM result after DFE.

        Parameters
        ----------
        imp_status:
            178A impairment status.
        dte_status:
            Selected 178A receiver DTE result.
        """
        imp_cfg = self.cfg.imp
        run_cfg = self._effective_run_cfg(
            self.cfg.execution.single_run if run_cfg is None else run_cfg
        )
        pmf_cfg_for_com = _resolve_final_com_pmf_config(
            self.cfg.pmf,
            imp_status.As,
            run_cfg,
            gaussian_n_sigma_override=self.cfg.policy.gaussian_n_sigma_override,
            final_pmf_grid=self.cfg.policy.final_pmf_grid,
        )
        As = imp_status.As

        # base pmf of PAM-L
        p_sig = _build_pmf_pam_L(
            self.cfg.L,
            pmf_cfg_for_com,
            placement=self.cfg.policy.discrete_pmf_placement,
        )

        # pmf of ISI
        p_ISI = _build_pmf_interference_178A(
            p_sig, imp_status.h_ISI.ir, pmf_cfg_for_com, self.cfg.L,
            method=self.cfg.policy.interference_pmf_method, name="ISI",
        )

        # pmf of XT (all combined)
        p_w_XT_all = _build_pmf_w_XT_all(
            p_sig, imp_status.h_XTs_w, pmf_cfg_for_com,
            L=self.cfg.L, methods=self.cfg.policy,
        )

        # pmf of tx Dual-dirac jitter
        p_w_DD = _build_pmf_interference_178A(
            p_sig,
            imp_cfg.A_DD * imp_status.h_w_J.ir,
            pmf_cfg_for_com,
            self.cfg.L,
            method=self.cfg.policy.interference_pmf_method,
            name="Dual-Dirac",
        )

        # Annex D3 final quantization consumes the selected-phase ADC-input
        # delta prepared by calculate_post_ffe_imp(). The reference-only branch
        # below follows MATLAB 4.17's distinct final-PDF clipping boundary.
        # Pre-DTE S_qn remains MMSE-only in both branches.
        if imp_status.post_ffe is None:
            raise RuntimeError("calculate_COM_DFE requires post-FFE impairment status.")
        adc_input_pmf = imp_status.post_ffe.adc_input
        if adc_input_pmf is None or adc_input_pmf.method == "disabled":
            p_qn = Pmf1D.multi_dirac(
                np.array([0.0]),
                np.array([1.0]),
                dx=pmf_cfg_for_com.dy,
                unit="volt",
                name="ADC_QN",
            )
        else:
            if adc_input_pmf.method != "pmf_exact":
                raise RuntimeError(
                    "calculate_COM_DFE requires post-DTE ADC input material with method='pmf_exact'."
                )
            w_lim = np.asarray(dte_status.w_lim, dtype=float)
            expected_shape = (int(self.cfg.dte.N_max),)
            if w_lim.shape != expected_shape:
                raise COMLengthMismatchError(
                    "calculate_COM_DFE() requires COMDTEStatus.w_lim to be the "
                    f"full zero-filled FFE tap vector with shape {expected_shape}, got {w_lim.shape}."
                )
            if self.cfg.policy.final_adc_quantization_convention == "matlab_4_17_reference_only":
                # MATLAB 4.17 / SiCoPR final-PDF branch: P_qc at the ADC-input
                # CDF and quantization noise through all non-main RX FFE taps.
                main_gain = float(w_lim[self.cfg.dte.d_w])
                V_qc, adc_grid_cfg, p_noise_adc = _final_adc_clip_reference_only(
                    imp_status,
                    self.cfg.L,
                    pmf_cfg_for_com,
                    main_gain,
                    imp_cfg.A_DD,
                    imp_cfg.P_qc,
                    pmf_methods=self.cfg.policy,
                )
                delta = 2.0 * V_qc / (2**imp_cfg.N_qb - 1)
                quantization_taps = w_lim.copy()
                quantization_taps[self.cfg.dte.d_w] = 0.0
                # The uniform error exists at the ADC input. Project each
                # scaled tap to the final (post-FFE) PMF grid in fir_filter.
                p_delta = Pmf1D.uniform(
                    delta, adc_grid_cfg,
                    method=self.cfg.policy.uniform_pmf_method,
                    support=(
                        p_noise_adc
                        if self.cfg.policy.final_adc_pmf_projection == "reference_support"
                        else None
                    ),
                )
            else:
                # Annex 178A-44: every FFE tap contributes to final ADC
                # quantization PMF; clipping remains at the post-FFE owner.
                if adc_input_pmf.delta is None:
                    raise RuntimeError("Annex D3 final quantization requires ADC input delta.")
                delta = adc_input_pmf.delta
                quantization_taps = w_lim
                p_delta = Pmf1D.uniform(
                    delta, pmf_cfg_for_com,
                    method=self.cfg.policy.uniform_pmf_method,
                )
            p_qn = p_delta.fir_filter(
                quantization_taps,
                keep_mass = pmf_cfg_for_com.keep_mass,
                dx_ref = pmf_cfg_for_com.dy,
                tap_abs_th = (
                    np.nextafter(0.0, 1.0)
                    if self.cfg.policy.final_adc_pmf_projection == "reference_support"
                    else pmf_cfg_for_com.tap_abs_th
                ),
                max_taps = None,
                name = "ADC_QN",
                scaling_method=self.cfg.policy.pmf_scaling_method,
                initial_bin_range=(
                    (p_noise_adc.st_idx, p_noise_adc.st_idx + len(p_noise_adc.pmf) - 1)
                    if self.cfg.policy.final_adc_pmf_projection == "reference_support"
                    and self.cfg.policy.final_adc_quantization_convention
                    == "matlab_4_17_reference_only"
                    else None
                ),
            )

        # pmf of gaussian noise
        p_G = _build_pmf_G(
            imp_status, dte_status, self.cfg.link, pmf_cfg_for_com,
            gaussian_method=self.cfg.policy.gaussian_pmf_method,
        )

        # combined pmf, A_ni
        p_combined = p_ISI.combine(p_w_XT_all).combine(p_w_DD).combine(p_qn).combine(p_G)
        y0 = p_combined.quantile(self.cfg.DER_0)
        A_ni = abs(y0)

        # COM
        COM = 20 * np.log10( As / A_ni )
        return COMPMFStatus(
            dy=pmf_cfg_for_com.dy,
            tap_abs_th=pmf_cfg_for_com.tap_abs_th,
            p_ISI=p_ISI,
            p_G=p_G,
            p_DD=p_w_DD,
            p_XT=p_w_XT_all,
            p_qn=p_qn,
            p_combined=p_combined,
            y0=y0,
            A_ni=A_ni,
            COM=COM,
        )

    def calculate_COM_MLSD(self, run_cfg: Optional[COMRunConfig] = None) -> COMMLSDStatus:
        """Calculate the Annex 178A MLSD COM adjustment after COM_DFE.

        The DFE PMF remains the immutable baseline.  Eq. (178A-47) derives
        ``COM_MLSD_raw`` from its ``COM_DFE`` and ``A_s``; the specification
        then floors the selected result at ``COM_DFE``.
        """
        if not self.cfg.mlsd.enable:
            raise ValueError("calculate_COM_MLSD requires cfg.mlsd.enable=True.")
        if self.cfg.dte.N_b != 1:
            raise ValueError("Annex 178A MLSD requires cfg.dte.N_b == 1.")

        status = self._require_status()
        imp_status = status.imp
        dte_status = status.dte
        pmf_dfe = status.pmf
        if not isinstance(imp_status, COMImpairmentStatus):
            raise RuntimeError("calculate_COM_MLSD requires completed 178A impairment status.")
        if not isinstance(dte_status, COMDTEStatus):
            raise RuntimeError("calculate_COM_MLSD requires the selected N_b=1 DTE status.")
        if not isinstance(pmf_dfe, COMPMFStatus):
            raise RuntimeError("calculate_COM_MLSD requires completed COM_DFE PMF status.")
        if imp_status.post_ffe is None:
            raise RuntimeError("calculate_COM_MLSD requires the post-FFE impairment stage.")

        b_lim = np.asarray(dte_status.b_lim, dtype=float)
        if b_lim.shape != (1,):
            raise COMLengthMismatchError(
                "MLSD requires exactly one DFE feedback coefficient; "
                f"got b_lim shape {b_lim.shape}."
            )
        if pmf_dfe.A_ni is None or pmf_dfe.COM is None:
            raise RuntimeError("calculate_COM_MLSD requires finite COM_DFE and A_ni.")
        A_ni = float(pmf_dfe.A_ni)
        COM_DFE = float(pmf_dfe.COM)
        if not np.isfinite(A_ni) or A_ni <= 0.0 or not np.isfinite(COM_DFE):
            raise COMError(
                "calculate_COM_MLSD requires finite COM_DFE and positive A_ni; "
                f"got COM_DFE={COM_DFE!r}, A_ni={A_ni!r}."
            )

        run_cfg = self._effective_run_cfg(
            self.cfg.execution.single_run if run_cfg is None else run_cfg
        )
        pmf_cfg = _resolve_final_com_pmf_config(
            self.cfg.pmf, imp_status.As, run_cfg,
            gaussian_n_sigma_override=self.cfg.policy.gaussian_n_sigma_override,
            final_pmf_grid=self.cfg.policy.final_pmf_grid,
        )
        # Eqs. (178A-50) and (178A-51): calibrate added receiver noise.
        # The Annex realization replaces only the Gaussian component.  The
        # reference realization scales the complete DFE PDF before deriving g_an.
        if self.cfg.policy.added_noise_pdf == "scaled_total_pdf":
            added_noise = _build_scaled_total_pdf_added_noise(
                self.cfg.mlsd.resolved_delta_com_an(),
                imp_status.post_ffe,
                pmf_dfe,
                self.cfg.DER_0,
                scaling_method=self.cfg.policy.pmf_scaling_method,
            )
        else:
            added_noise = solve_g_an(
                self.cfg.mlsd.resolved_delta_com_an(),
                imp_status.post_ffe,
                pmf_dfe,
                pmf_cfg,
                self.cfg.DER_0,
                gaussian_method=self.cfg.policy.gaussian_pmf_method,
            )
        # Eq. (178A-54): build the MLSD noise PSD and autocorrelation.
        noise = self.build_mlsd_noise(imp_status, added_noise)
        # Eqs. (178A-48), (178A-49), (178A-52), (178A-53): calculate DER.
        DER_MLSD, der_by_j = calculate_der_mlsd(
            added_noise.p_an,
            noise.R_ni,
            L=self.cfg.L,
            As=imp_status.As,
            b_lim_1=float(b_lim[0]),
            trunc_len=self.cfg.mlsd.trunc_len,
            pmf_scaling_method=self.cfg.policy.pmf_scaling_method,
            sequence_termination=self.cfg.policy.sequence_termination,
        )
        if not np.isfinite(DER_MLSD) or not 0.0 < DER_MLSD < 0.5:
            raise COMError(
                "MLSD DER must be finite and in (0, 0.5) to evaluate Eq. (178A-47); "
                f"got {DER_MLSD!r}."
            )

        # Eq. (178A-47): -P_an^{-1}(DER_MLSD) is the MLSD amplitude.
        A_MLSD = -float(added_noise.p_an.quantile(DER_MLSD))
        if not np.isfinite(A_MLSD) or A_MLSD <= 0.0:
            raise COMError(
                "MLSD inverse-CDF amplitude must be finite and positive; "
                f"got {A_MLSD!r} at DER_MLSD={DER_MLSD:.6e}."
            )
        # Eq. (178A-47): the MLSD increment is relative to A_s, not A_ni.
        delta_COM = float(20.0 * np.log10(A_MLSD / imp_status.As))
        COM_MLSD_raw = COM_DFE + delta_COM
        DER_MLSD_raw_sequence = float(np.sum(der_by_j))
        if self.cfg.policy.reported_der == "baseline_pdf_re_evaluation":
            # MATLAB 4.17 re-evaluates the published DER on the original DFE
            # PDF at the amplitude implied by the calculated MLSD increment.
            DER_MLSD_reported = _reference_cdf_ev(
                pmf_dfe.p_combined,
                imp_status.As * 10.0 ** (delta_COM / 20.0),
            )
        else:
            DER_MLSD_reported = DER_MLSD
        mlsd_status = COMMLSDStatus(
            added_noise=added_noise,
            S_isi=noise.S_isi,
            sigma_isi=noise.sigma_isi,
            S_qn=noise.S_qn,
            sigma_qn=noise.sigma_qn,
            S_ni=noise.S_ni,
            sigma_ni=noise.sigma_ni,
            R_ni=noise.R_ni,
            der_by_j=der_by_j,
            DER_MLSD_raw_sequence=DER_MLSD_raw_sequence,
            DER_MLSD=DER_MLSD,
            DER_MLSD_reported=DER_MLSD_reported,
            A_MLSD=A_MLSD,
            delta_COM=delta_COM,
            COM_MLSD_raw=COM_MLSD_raw,
            # Text following Eq. (178A-49): MLSD COM is at least COM_DFE.
            COM_MLSD=max(COM_DFE, COM_MLSD_raw),
        )
        self._assign_mlsd(mlsd_status)
        return mlsd_status

    def calculate_COM(self, imp_status: COMImpairmentStatus, dte_status: COMDTEStatus) -> COMPMFStatus:
        """Backward-compatible alias for the DFE-based 178A COM stage."""
        return self.calculate_COM_DFE(imp_status, dte_status)


# Public helpers for building or inspecting one 178A COM stage.
build_txpkg = _build_txpkg
build_rxpkg = _build_rxpkg
build_H_ffe = _build_H_ffe
build_H_ffe_next = _build_H_ffe_next
build_H_t = _build_H_t
build_H_r = _build_H_r
build_H_ctf = _build_H_ctf
build_channel_under_test = _build_channel_under_test
build_path = _build_path
build_paths = _build_paths
build_shared_path = _build_shared_path
build_psd_adc_qn = _build_psd_adc_qn
build_psd_rx_noise = _build_psd_rx_noise
build_psd_tx_jitter = _build_psd_tx_jitter
build_psd_tx_noise = _build_psd_tx_noise
build_psd_xtalk = _build_psd_xtalk


__all__ = [
    "COM",
    "COMAdcInputPMF",
    "COMAddedNoiseStatus",
    "COMAddedNoiseIterationStatus",
    "COMBilinearCTLE",
    "COMChannelConfig",
    "COMConfig",
    "COMDTEConfig",
    "COMDTEStatus",
    "COMError",
    "COMExecutionConfig",
    "COMEqChannelStatus",
    "COMFilterConfig",
    "COMImpairmentConfig",
    "COMImpairmentStatus",
    "COMImpStageStatus",
    "COMPMFConfig",
    "COMPolicyConfig",
    "COMPMFStatus",
    "COMRunStatus",
    "COMRunConfig",
    "COMSharedPath",
    "COMMainCursorError",
    "COMLengthMismatchError",
    "COMMLSDConfig",
    "COMMLSDNoiseStatus",
    "COMMLSDStatus",
    "COMTxfirMainCursorError",
    "COMPkgConfig",
    "COMPSDStatus",
    "calculate_der_mlsd",
    "evaluate_delta_com_an",
    "solve_g_an",
    "COMSearchConfig",
    "COMSearchRow",
    "COMSearchStatus",
    "COMStatus",
    "IEEECOMFilter",
    "IEEECOMSparam",
    "build_channel_under_test",
    "build_H_ctf",
    "build_H_ffe",
    "build_H_ffe_next",
    "build_H_r",
    "build_H_t",
    "build_path",
    "build_paths",
    "build_psd_adc_qn",
    "build_psd_rx_noise",
    "build_psd_tx_jitter",
    "build_psd_tx_noise",
    "build_psd_xtalk",
    "build_rxpkg",
    "build_shared_path",
    "build_txpkg",
]


if __name__ == "__main__":
    """Manual project entry point.

    Edit only ``CASE_ID``, ``RUN_MODE`` and (when needed) ``EXEC_POLICY``
    before running this file with ``%run com_model_178A.py``.  Search ranges
    remain workbook-owned; internal sweep/final batching is not exposed here.
    """
    import importlib

    # User-facing controls for the manual entry point.
    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    CASE_ID = "case_260915_report"
    RUN_MODE = "single_run"  # "single_run" or "search_run"
    EXEC_POLICY: dict[str, dict[str, object]] = {
        # Example override:
        # "single_run": {"pre_dte_pmf_method": "pmf_exact"},
    }

    CASE_ROOT = PROJECT_ROOT / "cases" / CASE_ID / "178A"
    CONFIG_PATH = CASE_ROOT / "config.xlsx"
    REPORT_ROOT = CASE_ROOT / "results"
    SEARCH_OUTPUT_NAME = "scaled_search"

    # Keep the module identity stable when this file is executed directly or
    # through IPython, so the reader and runtime use the same dataclass classes.
    sys.modules["serdes_coding.models.com_model_178A"] = sys.modules[__name__]
    if __package__:
        from ..io import com_excel_io
        from ..reporting.com_report_178A import COMReport178A
    else:
        from serdes_coding.io import com_excel_io
        from serdes_coding.reporting.com_report_178A import COMReport178A
    com_excel_io = importlib.reload(com_excel_io)

    if RUN_MODE not in {"single_run", "search_run"}:
        raise ValueError("RUN_MODE must be 'single_run' or 'search_run'.")
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"178A project workbook not found: {CONFIG_PATH}")

    cfg = com_excel_io.excel_to_config_178A(str(CONFIG_PATH))

    # Manual overrides apply only to execution-policy fields.  They do not
    # alter fixed config, search ranges, or the COM calculation implementation.
    profiles = {
        "single_run": cfg.execution.single_run,
        "search_sweep": cfg.execution.search_sweep,
        "search_final": cfg.execution.search_final,
    }
    for profile_name, overrides in EXEC_POLICY.items():
        if profile_name not in profiles:
            raise ValueError(f"Unknown EXEC_POLICY profile: {profile_name}")
        invalid = set(overrides) - set(profiles[profile_name].__dataclass_fields__)
        if invalid:
            raise ValueError(
                f"Unsupported EXEC_POLICY fields for {profile_name}: {sorted(invalid)}"
            )
        profiles[profile_name] = replace(profiles[profile_name], **overrides)
    cfg.execution = replace(
        cfg.execution,
        single_run=profiles["single_run"],
        search_sweep=profiles["search_sweep"],
        search_final=profiles["search_final"],
    )

    if RUN_MODE == "single_run":
        REPORT_PATH = REPORT_ROOT / "single_run"
        started = perf_counter()
        status = COM(cfg).run(progress=True)
        elapsed_s = perf_counter() - started
        print(f"178A single_run completed in {elapsed_s:.2f} s ({elapsed_s / 60.0:.2f} min)")
        outputs = cfg.export(str(REPORT_PATH))
        outputs.update(status.export(str(REPORT_PATH)))
        outputs.update(COMReport178A(cfg, status).export_single_run(REPORT_PATH))
        print(outputs)
    else:
        REPORT_PATH = REPORT_ROOT / SEARCH_OUTPUT_NAME
        search_cfg = com_excel_io.excel_to_search_config_178A(str(CONFIG_PATH))
        candidate_count = len(search_cfg.candidates(cfg.filter))
        print(f"178A search_run: {candidate_count} candidates from workbook search_config")
        started = perf_counter()
        status = COM(cfg).run(search=search_cfg, report_dir=REPORT_PATH)
        elapsed_s = perf_counter() - started
        print(f"178A search_run completed in {elapsed_s:.2f} s ({elapsed_s / 60.0:.2f} min)")
