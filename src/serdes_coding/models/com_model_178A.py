"""
IEEE 802.3 Annex 178A COM model.

Public names in this module do not need a version suffix because the module
namespace already defines the spec version. This module owns the 178A-specific
configuration, status objects, PSD/DTE helpers, and COM pipeline. It imports
only stable v1 primitives from ``com_model_93A.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations, product
from pathlib import Path
import sys
from time import perf_counter
from typing import Any, Literal, Optional, Sequence
import numpy as np

try:
    from ..utilities.link import ContinuousPSD, LinkConfig, LinkSegment, SampledPSD, SampledResponse
    from ..utilities.sparam import SparamModel
    from ..utilities.pmf import Pmf1D
    from ..search.com_search_178A import COMSearchRow, COMSearchStatus, run_full_search
    from . import com_model_93A as com_93A
except ImportError:
    # Support direct interactive execution of this canonical module.
    # Package execution continues to use the relative imports above.
    source_root = str(Path(__file__).resolve().parents[2])
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from serdes_coding.utilities.link import ContinuousPSD, LinkConfig, LinkSegment, SampledPSD, SampledResponse
    from serdes_coding.utilities.sparam import SparamModel
    from serdes_coding.utilities.pmf import Pmf1D
    from serdes_coding.search.com_search_178A import COMSearchRow, COMSearchStatus, run_full_search
    from serdes_coding.models import com_model_93A as com_93A

# 178A reuses only these stable v1 data-flow/reporting primitives. Versioned
# config, impairment status, PSD, DTE, and COM pipeline definitions live here.
_PrettyDataclass = com_93A._PrettyDataclass
COMChannelConfig = com_93A.COMChannelConfig
COMPMFConfig = com_93A.COMPMFConfig
COMPMFRuntimeConfig = com_93A.COMPMFRuntimeConfig
COMPMFStatus = com_93A.COMPMFStatus
COMPath = com_93A.COMPath
COMReport = com_93A.COMReport
COMSearchCandidate = com_93A.COMSearchCandidate
COMSearchConfig = com_93A.COMSearchConfig
COMSharedPath = com_93A.COMSharedPath
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
    def rx_equalizer(
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

# =========================================
# 178A configs, integrated to COMConfig
# =========================================

@dataclass(repr=False)
class COMDeviceTermConfig(_PrettyDataclass):
    C_d_seq: Sequence[float] | np.ndarray = ()     # unit: F, device termination shunt-capacitance vector
    L_s_seq: Sequence[float] | np.ndarray = ()     # unit: H, device termination series-inductance vector
    C_b: float = 0.0                               # unit: F, bump/interface capacitance

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
class COMDevicePackageConfig(_PrettyDataclass):
    z_p_seq: Sequence[float] | np.ndarray = ()      # unit: mm, package TL stage lengths
    Z_c_seq: Sequence[float] | np.ndarray = ()      # unit: ohm, package TL stage differential impedances
    gamma_0: Sequence[float] | float = 0.0          # unit: 1/mm, package propagation coefficient term
    a1: Sequence[float] | float = float(1.734e-3)   # unit: 93A package TL model coefficient
    a2: Sequence[float] | float = float(1.455e-4)   # unit: 93A package TL model coefficient
    tau: Sequence[float] | float = float(6.141e-3)  # unit: ns/mm, package TL delay coefficient
    C_p: float = 0.0                                # unit: F, package-to-board capacitance

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
class COMPartialHostConfig(_PrettyDataclass):
    enable: bool = False                         # unit: boolean, include partial host channel
    C_0: float = 0.0                             # unit: F, package-to-board interface capacitance
    C_1: float = 0.0                             # unit: F, model-to-measurement interface capacitance
    z_h: float = 0.0                             # unit: mm, host transmission-line length
    Z_h: float = 78.2                            # unit: ohm, host differential characteristic impedance
    gamma_0: float = 0.0                         # unit: 1/mm, host propagation coefficient term
    a1: float = float(1.734e-3)                  # unit: host transmission-line loss coefficient
    a2: float = float(1.455e-4)                  # unit: host transmission-line loss coefficient
    tau: float = float(6.141e-3)                 # unit: ns/mm, host transmission-line delay coefficient

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
class COMPkgConfig(_PrettyDataclass):
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
class COMFilterConfig(_PrettyDataclass):
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
class COMDTEConfig(_PrettyDataclass):
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
    N_max: Optional[int] = None      # unit: tap index, highest allowed FFE tap index
    N_b: int = 0                     # unit: taps, number of DFE feedback taps

    # derived coefficient-limit arrays used by COM_MMSE_DTE
    w_upper: np.ndarray = field(init=False)
    w_lower: np.ndarray = field(init=False)

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
class COMRunConfig(_PrettyDataclass):
    """Algorithm policy and stage target for one 178A execution profile."""
    target: Literal["mse", "dfe", "mlsd", "full"] = "dfe"
    pre_dte_pmf_method: Literal["gaussian_approx", "pmf_exact"] = "gaussian_approx"
    pmf_grid_quality: Literal["coarse", "fine"] = "fine"
    floating_mode: Literal["heuristic", "simplified", "spec-defined"] = "heuristic"
    pos_sweep_method: Literal["each_phase", "coarse_fine"] = "each_phase"
    pos_coarse_stride: int = 4

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
class COMExecutionConfig(_PrettyDataclass):
    """Project-owned profiles for single run and split 178A search execution."""
    single_run: COMRunConfig = field(default_factory=COMRunConfig)
    search_sweep: COMRunConfig = field(
        default_factory=lambda: COMRunConfig(target="mse", pmf_grid_quality="coarse")
    )
    search_final: COMRunConfig = field(default_factory=COMRunConfig)
    search_group_size: int = 100
    search_top_k: int = 10

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
class COMImpairmentConfig(_PrettyDataclass):
    """178A physical impairment parameters, excluding numerical run policy."""
    R_LM: float                     # unit: dimensionless, level separation mismatch ratio
    SNR_TX: float                   # unit: dB, transmitter signal-to-noise ratio
    sigma_RJ: float                 # unit: UI, random jitter RMS
    A_DD: float                     # unit: UI, dual-Dirac jitter amplitude
    eta_0: float                    # unit: V^2/Hz, one-sided noise spectral density
    N_qb: Optional[int] = None      # unit: bits, None disables quantization noise
    P_qc: Optional[float] = None    # unit: probability, None disables quantization noise

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
class COMMLSDConfig(_PrettyDataclass):
    enable: bool
    trunc_len: int
    delta_com_an: float

@dataclass(repr=False)
class COMConfig(_PrettyDataclass):
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

# =========================================
# 178A configs, integrated to COMConfig
# =========================================

@dataclass(repr=False)
class COMPSDStatus(_PrettyDataclass):
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
    S_jn_RJ: Optional[SampledPSD] = None
    S_gn_adc: Optional[SampledPSD] = None
    sigma_gn_adc: Optional[float] = None
    sigma_ISI: Optional[float] = None

@dataclass(repr=False)
class COMEqChannelStatus(_PrettyDataclass):
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
    

@dataclass(repr=False)
class COMAdcInputPMF(_PrettyDataclass):
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

@dataclass(repr=False)
class COMImpStageStatus(_PrettyDataclass):
    """One 178A impairment stage's PSD, equivalent-channel, and ADC material."""
    psd: Optional[COMPSDStatus] = None
    adc_input: Optional[COMAdcInputPMF] = None

@dataclass(repr=False)
class COMImpairmentStatus(_PrettyDataclass):
    """
    178A impairment status grouped by receiver-processing stage.

    Each stage stores its own PSD objects, equivalent-channel sequences, and
    ADC-input PMF material. ``pre_dte`` is the selected sampling-phase result;
    the phase-independent pre-DTE cache is intentionally run-local.
    """
    pre_dte: Optional[COMImpStageStatus] = None
    post_ffe: Optional[COMImpStageStatus] = None
    pre_mlsd: Optional[COMImpStageStatus] = None
    eq_ch: Optional[COMEqChannelStatus] = None
    
    def _stages(self) -> tuple[COMImpStageStatus, ...]:
        return tuple(
            stage
            for stage in (self.pre_mlsd, self.post_ffe, self.pre_dte)
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
    def S_jn_RJ(self) -> SampledPSD:
        return self._psd_attr("S_jn_RJ")

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
    def h_ISI(self) -> np.ndarray:
        return self._eq_attr("h_ISI")

    @property
    def h_w_J(self) -> SampledResponse:
        return self._eq_attr("h_w_J")

@dataclass(repr=False)
class COMDTEStatus(_PrettyDataclass):
    """
    178A receiver discrete-time equalizer result for one sampling phase.
    """
    ts: int                         # unit: sample index on cfg.times
    pos: int                        # unit: sample phase index, 0 <= pos < per_ui
    d: int
    w_lim: SampledResponse       # unit: dimensionless, full FFE impulse response
    b_lim: np.ndarray             # unit: dimensionless, DFE coefficients b
    mse: float                      # unit: V^2, mean-square error from 178A-35
    H_all: np.ndarray 
    Rnn_all: np.ndarray 
    pruned_index: np.ndarray         # unit: tap index, selected FFE tap index vector i
    H: np.ndarray 
    R_nn: np.ndarray 
    H_b: np.ndarray

    # without limter results
    w: np.ndarray
    b: np.ndarray

    @property
    def dfe_coeff(self) -> np.ndarray:
        """Compatibility proxy for report code that plots feedback taps."""
        return self.b_lim


@dataclass(repr=False)
class COMRunStatus(_PrettyDataclass):
    """Runtime records collected while one concrete 178A COM point is evaluated."""
    mse_by_pos: list[Optional[float]] = field(default_factory=list)
    main_cursor_error_by_pos: list[Optional[str]] = field(default_factory=list)
    coarse_pos: list[int] = field(default_factory=list)
    fine_pos: list[int] = field(default_factory=list)


@dataclass(repr=False)
class COMStatus(com_93A.COMStatus):
    """178A COM status with selected stage outputs and runtime sweep records."""
    dfe: Optional[COMDTEStatus] = None
    imp: Optional[COMImpairmentStatus] = None
    run: Optional[COMRunStatus] = None

    def export(self, save_path: str, *, include_plots: bool = False) -> dict[str, str]:
        """Export a 178A status without invoking the legacy 93A exporter.

        The inherited 93A exporter assumes the flat 93A impairment contract,
        including ``imp.sigma_TX``. 178A impairment data is grouped by stage,
        so top-K finalization must use a 178A-specific export boundary.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = out_dir / "status_summary.txt"
        summary_path.write_text(str(self), encoding="utf-8")
        outputs = {"status_summary_txt": str(summary_path)}

        if include_plots:
            cfg = getattr(self, "_config_for_report", None)
            if cfg is None:
                raise ValueError(
                    "178A plot export requires the originating COMConfig."
                )
            from ..reporting.com_report_178A import COMReport178A

            plot_dir = out_dir / "plots"
            COMReport178A(cfg, self).plot_single_run(plot_dir)
            outputs["plots"] = str(plot_dir)
        return outputs


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

    The current 178A package contract is:
        partial host channel -> device package -> device termination
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
    return S_rh.cascade_com_93A(S_rp).cascade_com_93A(S_rd)

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

def _build_channel_under_test(channel_cfg: COMChannelConfig) -> list[SparamModel]:
    """
    Build 178A measured-domain channel-under-test S-parameter models.

    Output contract mirrors _build_channel_under_test_93A():
    - index 0: victim
    - following indices: NEXT channels, then FEXT channels
    """
    return _build_channel_under_test_93A(channel_cfg)

def _build_path(
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig,
    ft_cfg: COMFilterConfig,
    txpkg_cfg: COMPkgConfig,
    shared: COMSharedPath,
    kind: Literal["victim", "next", "fext"],
    S_ch: SparamModel,
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
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_ne)
    elif kind == "fext":
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg)
        H_ffe = shared.H_ffe
        X = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_fe)
    elif kind == "victim":
        S_tx = _build_txpkg(S_ch.freqs, txpkg_cfg)
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

def _build_shared_path(cfg: COMConfig, freqs: np.ndarray) -> COMSharedPath:
    """
    Build 178A path-shared COM models.

    The returned COMSharedPath keeps the same fields as 93A:
    H_ffe, H_ffe_next, H_t, S_rx, H_r, H_ctf.
    """
    link_cfg = cfg.link
    ft_cfg = cfg.filter
    return COMSharedPath(
        H_ffe=_build_H_ffe(link_cfg, ft_cfg),
        H_ffe_next=_build_H_ffe_next(link_cfg),
        H_t=_build_H_t(link_cfg, ft_cfg),
        S_rx=_build_rxpkg(freqs, cfg.rxpkg),
        H_r=_build_H_r(link_cfg, ft_cfg),
        H_ctf=_build_H_ctf(link_cfg, ft_cfg),
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
    S_rn_broadband = ContinuousPSD.from_constant(link_cfg.freqs, imp_cfg.eta_0)
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

def _build_psd_xtalk(h_XTs: list[np.ndarray], link_cfg: LinkConfig, sigma_x: float) -> tuple[SampledPSD, list[np.ndarray]]:

    # initialized with psd_constant = 0.0
    S_xn_all = SampledPSD.from_constant(link_cfg.theta, 0.0, link_cfg.fb)
    h_XTs_dsamp = []
    for h_XT in h_XTs:
        _, h_XT_dsamp = _find_pos_xtalk(h_XT, link_cfg.per_ui)
        S_xn_temp = _build_psd_from_DFT_response(h_XT_dsamp, link_cfg, sigma_x**2)
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
    S_base = SampledPSD.from_constant(link_cfg.theta, variance / link_cfg.fb, link_cfg.fb)
    H = SampledResponse.from_ir(h_dsamp, link_cfg)
    return S_base.filtered_by(H)

def _build_psd_tx_noise(
    victim: COMPath,
    link_cfg: LinkConfig,
    ft_cfg: COMFilterConfig,
    imp_cfg: COMImpairmentConfig,
    pos: int,
) -> tuple[SampledPSD, np.ndarray]:
    """
    Build transmitter output noise PSD and the sampled no-FFE pulse response.

    Reference:
    - IEEE 802.3 Annex 178A.1.7.3, Eq. 178A-19 and Eq. 178A-20.
    """
    H_noffe = (
        victim.H_t
        .cascade_tf(victim.H_21)
        .cascade_tf(victim.H_r)
        .cascade_tf(victim.H_ctf)
    )
    X_v = IEEECOMFilter.rect_pulse_93A(link_cfg, ft_cfg.A_v)
    h_tn = H_noffe.cascade_tf(X_v).ir[int(pos)::link_cfg.per_ui]
    variance = 10 ** (-imp_cfg.SNR_TX / 10)
    return _build_psd_from_DFT_response(h_tn, link_cfg, variance), h_tn

def _calculate_h_J(h: np.ndarray, pos: int, link_cfg: LinkConfig, w: Optional[np.ndarray]=None) -> np.ndarray:
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
        h_m1 = np.convolve(h_m1, w)
        h_p1 = np.convolve(h_p1, w)
    h_J = (h_p1 - h_m1) / (2 * delta_t_ui)
    return h_J

def _build_psd_tx_jitter(
    victim: COMPath,
    link_cfg: LinkConfig,
    imp_cfg: COMImpairmentConfig,
    pos: int,
    sigma_X: float
) -> tuple[SampledPSD, np.ndarray]:

    h_J = _calculate_h_J(victim.pulse.ir, pos, link_cfg)
    jitter_variance = sigma_X**2 * (imp_cfg.A_DD**2 + imp_cfg.sigma_RJ**2)
    S_jn = _build_psd_from_DFT_response(h_J, link_cfg, jitter_variance)
    return S_jn, h_J

def _calculate_V_qc(
    p_sig: Pmf1D,
    h_dsamp: np.ndarray,
    sigma_ga: float,
    P_qc: float,
    pmf_cfg: COMPMFRuntimeConfig,
) -> COMAdcInputPMF:
    """Build the exact ADC-input PMF chain and resolve V_qc from p_sn."""
    pmf_s = _build_pmf_interference_93A(
        p_sig, 
        h_dsamp, 
        pmf_cfg,
        name="Noiseless signal",
    )

    pmf_ga = Pmf1D.gaussian(
        mu=0,
        sigma=sigma_ga,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Noise"
    )

    pmf_sn = pmf_s.combine(pmf_ga, name="Noisy signal")
    V_qc = -(pmf_sn.quantile(P_qc/2))

    return COMAdcInputPMF(
        p_sig=p_sig,
        p_s=pmf_s,
        p_ga=pmf_ga,
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
    V_qc = float(NormalDist().inv_cdf(1.0 - float(P_qc) / 2.0) * sigma_sn)
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
) -> tuple[SampledPSD, COMAdcInputPMF]:

    if vqc_method == "gaussian_approx":
        adc_input_pmf = _calculate_V_qc_gaussian_approx(
            p_sig,
            h_dsamp,
            sigma_ga,
            P_qc,
            pmf_cfg,
        )
        V_qc = adc_input_pmf.V_qc
        if V_qc is None:
            raise RuntimeError("Gaussian-approximate ADC input did not resolve V_qc.")
    elif vqc_method == "pmf_exact":
        adc_input_pmf = _calculate_V_qc(p_sig, h_dsamp, sigma_ga, P_qc, pmf_cfg)
        V_qc = adc_input_pmf.V_qc
        if V_qc is None:
            raise RuntimeError("Exact ADC-input PMF did not resolve V_qc.")
    else:
        raise ValueError("vqc_method must be 'gaussian_approx' or 'pmf_exact'.")

    # 178A-27
    delta = 2 * V_qc / (2**N_qb - 1)

    # 178A-26
    S_qn = SampledPSD.from_constant(link_cfg.theta, (delta**2/12)/link_cfg.fb, link_cfg.fb)

    adc_input_pmf.delta = delta
    return S_qn, adc_input_pmf

# for psd fallback
def _zero_sampled_psd(link_cfg: LinkConfig) -> SampledPSD:
    """Return a zero-valued sampled-domain PSD on link_cfg.theta."""
    return SampledPSD.from_constant(link_cfg.theta, 0.0, link_cfg.fb)

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
        w_lim = (
            dte_status.w_lim.ir
            if isinstance(dte_status.w_lim, SampledResponse)
            else dte_status.w_lim
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
        self.H_all = toeplitz(self.h_dsamp, np.zeros(self.cfg.N_max))
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
def _build_pmf_pam_L(L: int, pmf_cfg: COMPMFRuntimeConfig) -> Pmf1D:
    # Base PAM4 signal pmf
    return Pmf1D.multi_dirac(
        values = np.array([2*l/(L-1)-1 for l in range(L)]),
        probs = 1/L * np.ones(L),
        dx = pmf_cfg.dy,
        unit = "volt",
        name = f"PAM{L}_signal"
    )

def _build_pmf_w_XT_all(
    p_sig: Pmf1D,
    h_XTs_w: list[np.ndarray | SampledResponse],
    pmf_cfg: COMPMFRuntimeConfig,
) -> Pmf1D:
    return _build_pmf_XT_all_93A(
        p_sig,
        [value.ir if isinstance(value, SampledResponse) else value for value in h_XTs_w],
        pmf_cfg,
    )

def _ffe_impulse_from_dte_status(dte_status: COMDTEStatus) -> np.ndarray:
    """Return the full FFE impulse response stored in COMDTEStatus.w_lim."""
    pruned_index = np.asarray(dte_status.pruned_index, dtype=int)
    w_lim_value = dte_status.w_lim
    w_lim = (
        np.asarray(w_lim_value.ir, dtype=float)
        if isinstance(w_lim_value, SampledResponse)
        else np.asarray(w_lim_value, dtype=float)
    )
    if len(pruned_index) == 0:
        raise ValueError("dte_status.pruned_index must not be empty.")
    if len(w_lim) <= int(np.max(pruned_index)):
        raise ValueError("dte_status.w_lim must be a full FFE impulse covering every pruned_index.")
    return w_lim

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
) -> COMAdcInputPMF:
    """Build the selected-phase exact ADC-input PMF chain for final COM."""
    
    # noiseless signal
    pmf_s = _build_pmf_interference_93A(
        p_sig, 
        h_dsamp, 
        pmf_cfg,
        name="Noiseless signal",
    )

    pmf_XT = _build_pmf_w_XT_all(p_sig, h_XTs_dsamp, pmf_cfg)
    pmf_DD = _build_pmf_interference_93A(p_sig, A_DD * h_J, pmf_cfg, name="ADC-input Dual-Dirac")

    pmf_ga = Pmf1D.gaussian(
        mu=0,
        sigma=sigma_gn,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Gaussian Noise"
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

def _build_pmf_G(imp_status: COMImpairmentStatus, dte_status: COMDTEStatus, link_cfg: LinkConfig, pmf_cfg: COMPMFRuntimeConfig) -> Pmf1D:
    # Post-FFE impairment construction already filters receiver noise,
    # transmitter noise, and RJ onto one common expanded sampled grid.
    post_ffe = imp_status.post_ffe
    if post_ffe is not None and post_ffe.psd is not None and post_ffe.psd.S_gn_adc is not None:
        S_G = post_ffe.psd.S_gn_adc
    else:
        S_G = imp_status.S_tn.add(imp_status.S_jn_RJ).add(imp_status.S_rn)
    sigma_G = S_G.to_sigma()
    return Pmf1D.gaussian(
        mu=0,
        sigma=sigma_G,
        dx=pmf_cfg.dy,
        n_sigma=pmf_cfg.gaussian_n_sigma,
        unit="volt",
        name="Noise"
    )

class COM(com_93A.COM):
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

    This class intentionally reuses com_93A.COM's shared proxy/report/search shell
    where possible, but all spec-defined calculation steps are routed to 178A
    method names. Path building, impairment, and MMSE-DTE are explicit 178A
    stages; outer TXFFE/CTLE search ranks candidates by minimum DTE MSE.
    """

    def __init__(self, cfg: COMConfig):
        self.cfg = cfg
        self.status: Optional[COMStatus | COMSearchStatus] = None

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
        COM PMFs. ``mlsd`` and ``full`` enter the reserved MLSD stage, which
        currently raises NotImplementedError instead of returning an invalid
        result.
        """
        self.status = COMStatus()
        started = perf_counter()

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

        self._assign_dfe(best_dte)
        self._merge_imp(best_imp_pre)
        report(f"pos sweep: selected pos={best_dte.pos}, mse={best_dte.mse:.6e}")

        if run_cfg.target == "mse":
            report("single-run complete (target=mse)")
            return self._require_status()

        report("post_ffe_imp: start")
        imp_status = self.calculate_post_ffe_imp(
            dte_status=best_dte,
            pre_dte_imp_common=pre_dte_imp_common,
            imp_pre=best_imp_pre,
            h=victim.pulse.ir,
        )
        self._merge_imp(imp_status)
        report("post_ffe_imp: done")

        merged_imp_status = self._require_status().imp
        if not isinstance(merged_imp_status, COMImpairmentStatus):
            raise RuntimeError("Merged 178A impairment status is not available after post-FFE impairment.")

        if run_cfg.target in {"dfe", "full"}:
            report("calculate_COM_DFE: start")
            self._assign_pmf(self.calculate_COM_DFE(merged_imp_status, best_dte))
            report("calculate_COM_DFE: done")

        if run_cfg.target in {"mlsd", "full"}:
            report("calculate_COM_MLSD: start")
            self.calculate_COM_MLSD()
        report("single-run complete")
        return self._require_status()

    def _assign_paths(self, paths: list[COMPath]) -> None:
        """Assign build-path stage output into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.paths = paths

    def _assign_dfe(self, dte_status: COMDTEStatus) -> None:
        """Assign selected DTE stage output into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.dfe = dte_status

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
        for name in ("pre_dte", "post_ffe", "pre_mlsd"):
            value = getattr(imp_status, name)
            if value is not None:
                setattr(current, name, value)

    def _assign_pmf(self, pmf_status: Optional[COMPMFStatus]) -> None:
        """Assign COM DFE PMF stage output into the incremental run status."""
        if self.status is None or isinstance(self.status, COMSearchStatus):
            self.status = COMStatus()
        self.status.pmf = pmf_status

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

    def build_all_paths(self) -> list[COMPath]:
        """
        Build all 178A COM paths.

        LV-1 hierarchy mirrors com_93A.COM:
        1. build channel-under-test models
        2. build path-shared models
        3. build every path-specific model
        """
        channels = _build_channel_under_test(self.cfg.channel)
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
        imp_cfg = self.cfg.imp
        ft_cfg = self.cfg.filter
        L = self.cfg.L

        del victim
        if any(np.asarray(h_xt).ndim != 1 for h_xt in h_XTs):
            raise ValueError("Each crosstalk pulse response must be a one-dimensional array.")

        # input signal power
        sigma_X = np.sqrt((L**2 - 1) / (3 * (L - 1)**2))

        # Receiver input noise PSD
        S_rn = _build_psd_rx_noise(link_cfg, imp_cfg, ft_cfg)
        sigma_rn = S_rn.to_sigma()

        # Crosstalk PSD
        S_xn, h_XTs_dsamp = _build_psd_xtalk(h_XTs, link_cfg, sigma_X)
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
        if not isinstance(h_XTs_dsamp, list) or any(
            np.asarray(h_xt_dsamp).ndim != 1 for h_xt_dsamp in h_XTs_dsamp
        ):
            raise ValueError(
                "h_XTs_dsamp must be the list of one-dimensional sampled "
                "crosstalk responses returned by calculate_pre_dte_imp_common()."
            )
        pmf_cfg = self.cfg.pmf.resolve(
            imp_cfg.R_LM / (L - 1), grid_quality=run_cfg.pmf_grid_quality
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
        S_tn, h_tn = _build_psd_tx_noise(victim, link_cfg, ft_cfg, imp_cfg, pos)
        sigma_tn = S_tn.to_sigma()

        # transmitter jitter-induced noise PSD, Eq. 178A-21 and Eq. 178A-22.
        S_jn, h_J = _build_psd_tx_jitter(victim, link_cfg, imp_cfg, pos, sigma_X)
        sigma_jn = S_jn.to_sigma()

        # quantization noise
        p_sig = _build_pmf_pam_L(L, pmf_cfg)
        S_ga = S_rn.add(S_xn).add(S_tn).add(S_jn)
        sigma_ga = S_ga.to_sigma()
        if imp_cfg.N_qb is None or imp_cfg.P_qc is None:
            S_qn = _zero_sampled_psd(link_cfg)
            adc_input_pmf = COMAdcInputPMF(p_sig=p_sig, method="disabled")
        else:
            S_qn, adc_input_pmf = _build_psd_adc_qn(
                p_sig = p_sig, 
                h_dsamp = h_dsamp,
                sigma_ga = sigma_ga, 
                P_qc = imp_cfg.P_qc,
                N_qb = imp_cfg.N_qb,
                pmf_cfg = pmf_cfg, 
                link_cfg = link_cfg,
                vqc_method=run_cfg.pre_dte_pmf_method,
            )
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
        dte_status.w_lim = SampledResponse.from_ir(dte_status.w_lim, self.cfg.link)
        return dte_status

    def calculate_post_ffe_imp(
        self, 
        dte_status: COMDTEStatus, 
        pre_dte_imp_common: COMPSDStatus,
        imp_pre: COMImpairmentStatus,
        h: np.ndarray,
    ) -> COMImpairmentStatus:
        As = self.cfg.imp.R_LM / (self.cfg.L - 1)
        w_ir = _ffe_impulse_from_dte_status(dte_status)
        w_response = SampledResponse.from_ir(w_ir, self.cfg.link)
        h_w_response = imp_pre.h_dsamp.cascade_ir(w_response, per_ui=self.per_ui)
        post_link_cfg = LinkConfig.from_Nfft(
            self.cfg.link.fb,
            self.per_ui,
            h_w_response.nfft * self.per_ui,
        )
        h_w_response = SampledResponse.from_ir(h_w_response.ir, post_link_cfg)
        h_w = h_w_response.ir

        h_XTs_w = []
        for h_XT_dsamp in imp_pre.h_XTs_dsamp:
            h_XT_response = SampledResponse.from_ir(h_XT_dsamp.ir, self.cfg.link)
            h_XT_w_response = h_XT_response.cascade_ir(w_response, per_ui=self.per_ui)
            h_XTs_w.append(SampledResponse.from_ir(h_XT_w_response.ir, post_link_cfg))

        h_ISI = h_w.copy()
        # Eq. 178A-40: the normalized desired cursor is not residual ISI.
        h_ISI[dte_status.d] = 0.0
        h_ISI[dte_status.d+1:dte_status.d+1+len(dte_status.b_lim)] -= dte_status.b_lim

        h_ISI_response = SampledResponse.from_ir(h_ISI, post_link_cfg)
        sigma_ISI = np.sqrt(imp_pre.sigma_X**2 * np.sum(h_ISI**2))

        h_J_response = SampledResponse.from_ir(
            _calculate_h_J(h, dte_status.pos, self.cfg.link),
            self.cfg.link,
        )
        h_w_J = h_J_response.cascade_ir(w_response, per_ui=self.per_ui)
        h_w_J = SampledResponse.from_ir(h_w_J.ir, post_link_cfg)

        # Keep post-FFE PSD components on the same sampled grid as pre-DTE.
        # The PSD records are useful for reporting; final PMF construction
        # still treats DDJ separately as a dual-Dirac PMF.
        H_ffe = SampledResponse.from_ir(w_ir, post_link_cfg)

        def _filter_on_post_grid(source: SampledPSD) -> SampledPSD:
            psd = np.interp(post_link_cfg.theta, source.theta, source.psd)
            return SampledPSD(
                theta=post_link_cfg.theta,
                psd=psd,
                fb=post_link_cfg.fb,
            ).filtered_by(H_ffe)

        S_rn = _filter_on_post_grid(imp_pre.S_rn)
        S_xn = _filter_on_post_grid(imp_pre.S_xn)
        S_tn = _filter_on_post_grid(imp_pre.S_tn)

        S_jn = _build_psd_from_DFT_response(
            h_w_J.ir,
            post_link_cfg,
            pre_dte_imp_common.sigma_X**2
            * (self.cfg.imp.A_DD**2 + self.cfg.imp.sigma_RJ**2),
        )

        # Separate RJ from DDJ for final PMF construction after the selected phase is known.
        S_jn_RJ = _build_psd_from_DFT_response(
            h_w_J.ir,
            post_link_cfg,
            pre_dte_imp_common.sigma_X**2 * self.cfg.imp.sigma_RJ**2,
        )
        S_gn_adc = S_rn.add(S_tn).add(S_jn_RJ)
        sigma_gn_adc = S_gn_adc.to_sigma()

        pmf_cfg = self.cfg.pmf.resolve(As)
        p_sig = _build_pmf_pam_L(self.cfg.L, pmf_cfg)
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
                pmf_cfg=pmf_cfg,
            )

        if adc_input_pmf.delta is None:
            S_qn = _zero_sampled_psd(self.cfg.link)
        else:
            S_qn = SampledPSD.from_constant(
                post_link_cfg.theta,
                (adc_input_pmf.delta**2 / 12.0) / self.cfg.link.fb,
                post_link_cfg.fb,
            )
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
                S_jn_RJ=S_jn_RJ,
                S_gn_adc=S_gn_adc,
                sigma_gn_adc=sigma_gn_adc,
                sigma_ISI=sigma_ISI,
                ),
                adc_input=adc_input_pmf,
            ),
            eq_ch=COMEqChannelStatus(
                h_XTs_dsamp=imp_pre.h_XTs_dsamp,
                h_dsamp=imp_pre.h_dsamp,
                h_tn=imp_pre.h_tn,
                h_J=imp_pre.h_J,
                h_w=h_w_response,
                h_XTs_w=h_XTs_w,
                h_ISI=h_ISI_response,
                h_w_J=h_w_J,
            ),
        )

    def calculate_COM_DFE(self, imp_status: COMImpairmentStatus, dte_status: COMDTEStatus) -> COMPMFStatus:
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
        pmf_cfg = self.cfg.pmf.resolve(imp_status.As)
        As = imp_status.As

        # base pmf of PAM-L
        p_sig = _build_pmf_pam_L(self.cfg.L, pmf_cfg)

        # pmf of ISI
        p_ISI = _build_pmf_interference_93A(p_sig, imp_status.h_ISI.ir, pmf_cfg, name="ISI")

        # pmf of XT (all combined)
        p_w_XT_all = _build_pmf_w_XT_all(p_sig, imp_status.h_XTs_w, pmf_cfg)

        # pmf of tx Dual-dirac jitter
        p_w_DD = _build_pmf_interference_93A(
            p_sig,
            imp_cfg.A_DD * imp_status.h_w_J.ir,
            pmf_cfg,
            name="Dual-Dirac",
        )

        # Final quantization PMF consumes the exact ADC-input material prepared
        # by calculate_post_ffe_imp(). Pre-DTE S_qn remains MMSE-only.
        if imp_status.post_ffe is None:
            raise RuntimeError("calculate_COM_DFE requires post-FFE impairment status.")
        adc_input_pmf = imp_status.post_ffe.adc_input
        if adc_input_pmf is None or adc_input_pmf.method == "disabled":
            p_qn = Pmf1D.multi_dirac(np.array([0.0]), np.array([1.0]), dx=pmf_cfg.dy, unit="volt", name="ADC_QN")
        else:
            if adc_input_pmf.method != "pmf_exact" or adc_input_pmf.delta is None:
                raise RuntimeError(
                    "calculate_COM_DFE requires post-DTE ADC input material with method='pmf_exact'."
                )
            p_delta = Pmf1D.uniform(adc_input_pmf.delta, pmf_cfg)
            p_qn = p_delta.fir_filter(
                _ffe_impulse_from_dte_status(dte_status),
                keep_mass = pmf_cfg.keep_mass,
                dx_ref = pmf_cfg.dy,
                tap_abs_th = pmf_cfg.tap_abs_th,
                max_taps = None,
                name = "ADC_QN"
            )

        # pmf of gaussian noise
        p_G = _build_pmf_G(imp_status, dte_status, self.cfg.link, pmf_cfg)

        # combined pmf, A_ni
        p_combined = p_ISI.combine(p_w_XT_all).combine(p_w_DD).combine(p_qn).combine(p_G)
        y0 = p_combined.quantile(self.cfg.DER_0)
        A_ni = abs(y0)

        # COM
        COM = 20 * np.log10( As / A_ni )
        return COMPMFStatus(
            dy=pmf_cfg.dy,
            tap_abs_th=pmf_cfg.tap_abs_th,
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

    def calculate_COM_MLSD(self) -> None:
        """
        Placeholder for the 178A MLSD COM stage.

        The current project flow explicitly reserves this stage after
        calculate_COM_DFE(), but the MLSD algorithm is not implemented yet.
        """
        raise NotImplementedError(
            "178A COM MLSD is not implemented. Use target='mse' or target='dfe' "
            "until the pre-MLSD and MLSD stages are implemented."
        )

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
    "COMPMFStatus",
    "COMRunStatus",
    "COMRunConfig",
    "COMMainCursorError",
    "COMLengthMismatchError",
    "COMTxfirMainCursorError",
    "COMPkgConfig",
    "COMPSDStatus",
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
    # Debug entry point. Run this module, rather than this file directly:
    #   python -m serdes_coding.models.com_model_178A
    # Change only CASE_ID when switching between project-owned 178A cases.
    import sys

    # excel_to_config_178A imports the versioned config dataclasses from this
    # module. When run with ``-m``, expose the current ``__main__`` module at
    # its package name so that parser and runner share one class identity.
    sys.modules["serdes_coding.models.com_model_178A"] = sys.modules[__name__]

    # ``%run -m`` may reuse a previously imported parser in an IPython
    # kernel. Reload it so its imported 178A dataclasses always refer to the
    # module instance executing this debug entry.
    import importlib
    if __package__:
        from ..io import com_excel_io
        from ..reporting.com_report_178A import COMReport178A
    else:
        from serdes_coding.io import com_excel_io
        from serdes_coding.reporting.com_report_178A import COMReport178A

    excel_to_config_178A = importlib.reload(com_excel_io).excel_to_config_178A

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    CASE_ID = "c2m_8023dj_4p13p0_50mm"
    CASE_ROOT = PROJECT_ROOT / "cases" / CASE_ID
    CONFIG_PATH = CASE_ROOT / "config" / "config_178A.xlsx"
    REPORT_PATH = CASE_ROOT / "report" / "178A" / "single_run"

    cfg = excel_to_config_178A(str(CONFIG_PATH))
    print("Single-run execution config:")
    print(cfg.execution.single_run)
    started = perf_counter()
    status = COM(cfg).run(progress=True)
    elapsed_s = perf_counter() - started
    print(status)
    print(f"Single-run elapsed time: {elapsed_s:.2f} s ({elapsed_s / 60.0:.2f} min)")
    COMReport178A(cfg, status).plot_single_run(REPORT_PATH)
