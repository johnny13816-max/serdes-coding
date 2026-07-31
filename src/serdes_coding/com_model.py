from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional, Sequence
import numpy as np
from .link_segment import LinkConfig, LinkSegment, SparamModel

def excel_to_config(excel_path: str) -> COMConfig:
    """
    Build COMConfig from one Excel row by direct field assignment.

    Expected Excel format:
    - first sheet
    - one header row
    - first data row contains values

    Column names intentionally match dataclass field names so this function
    stays simple and easy to edit.
    """
    import pandas as pd

    row = pd.read_excel(excel_path).iloc[0]

    return COMConfig(
        filter=COMFilterConfig(
            txfir=row["txfir"],
            num_pre=row["num_pre"],
            Tr=row["Tr"],
            fr=row["fr"],
            g_DC=row["g_DC"],
            g_DC2=row["g_DC2"],
            f_z=row["f_z"],
            f_LF=row["f_LF"],
            f_p1=row["f_p1"],
            f_p2=row["f_p2"],
            At=row["At"],
        ),
        channel=COMChannelConfig(
            victim_s4p_path=row["victim_s4p_path"],
            next_s4p_paths=row["next_s4p_paths"],
            fext_s4p_paths=row["fext_s4p_paths"],
            port_order=row["port_order"],
            R0=row["R0"],
            gamma_src=row["gamma_src"],
            gamma_load=row["gamma_load"],
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
            z_p2=row["z_p2"],
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
        C = float(capacitance)
        R0 = float(R0)

        if C < 0.0:
            raise ValueError("capacitance must be non-negative.")

        y = 1j * 2 * np.pi * cfg.freqs * C
        denom = 2 + y * R0

        s11 = -(y * R0) / denom
        s21 = 2 / denom

        sdd = np.stack([
            np.stack([s11, s21], axis=-1),
            np.stack([s21, s11], axis=-1),
        ], axis=-2)
        return cls.from_sdd_array(cfg.freqs, sdd, z0=2 * R0)

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
        L = float(inductance)
        R0 = float(R0)

        if L < 0.0:
            raise ValueError("inductance must be non-negative.")

        y = 1j * 2 * np.pi * cfg.freqs * L
        denom = 2 + y / R0
        s11 = (y / R0) / denom
        s21 = 2 / denom
        sdd = np.stack([
            np.stack([s11, s21], axis=-1),
            np.stack([s21, s11], axis=-1),
        ], axis=-2)

        return cls.from_sdd_array(cfg.freqs, sdd, z0=2 * R0)

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
        f_hz = cfg.freqs
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

@dataclass
class COMPkgConfig:
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

@dataclass
class COMChannelConfig:
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

@dataclass
class COMFilterConfig:
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

@dataclass
class COMConfig:
    """Top-level COM configuration grouped by function."""
    link: LinkConfig
    filter: COMFilterConfig
    channel: COMChannelConfig
    pkg: COMPkgConfig

# ========================================
# Status (all integrated in COMStatus)
# ========================================

@dataclass
class COMCommonStatus:
    S_tp: IEEECOMsparam
    S_tp_next: IEEECOMsparam
    S_rp: IEEECOMsparam
    H_ffe: IEEECOMFilter
    H_ffe_next: IEEECOMFilter
    H_t: IEEECOMFilter
    H_r: IEEECOMFilter
    H_ctf: IEEECOMFilter
    X_v: IEEECOMFilter
    X_fe: IEEECOMFilter
    X_ne: IEEECOMFilter

@dataclass
class COMPathStatus:
    kind: Literal["victim", "next", "fext"]
    S_ch: SparamModel
    S_all: SparamModel      # augmented signal path
    H_21: LinkSegment
    H_all: LinkSegment      # voltage transfer function with filters
    X: IEEECOMFilter

@dataclass
class COMStatus:
    common: COMCommonStatus
    paths: list[COMPathStatus]

    @property
    def victim(self) -> COMPathStatus:
        return self.paths[0]

    @property
    def xtalks(self) -> list[COMPathStatus]:
        return self.paths[1:]

# -------------------
# helpers
# -------------------

def _bulid_txpkg(link_cfg: LinkConfig, txpkg_cfg: COMPkgConfig, *, isNext: bool = False) -> IEEECOMsparam:
    "Eq. 93A-15 and 93A-15a, 93A-16b"
    C_d = txpkg_cfg.C_d * 1e-12
    L_s = txpkg_cfg.L_s * 1e-9
    C_b = txpkg_cfg.C_b * 1e-12
    C_p = txpkg_cfg.C_p * 1e-12

    S_d = IEEECOMsparam.shunt_capacitance(link_cfg, C_d, txpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance(link_cfg, L_s, txpkg_cfg.R0)
    S_b = IEEECOMsparam.shunt_capacitance(link_cfg, C_b, txpkg_cfg.R0)
    S_l = IEEECOMsparam.pkg_trans_line(link_cfg, txpkg_cfg.R0, txpkg_cfg.z_p, Zc=txpkg_cfg.Z_c)
    if (txpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line(link_cfg, txpkg_cfg.R0, txpkg_cfg.z_p2, Zc=txpkg_cfg.Z_c2)
    S_p = IEEECOMsparam.shunt_capacitance(link_cfg, C_p, txpkg_cfg.R0)

    # cascade
    S_td = (S_d.cascade_com(S_s)).cascade_com(S_b)
    if (txpkg_cfg.z_p2 is not None):
        S_tp = ((S_td.cascade_com(S_l)).cascade_com(S_l2)).cascade_com(S_p)
    else:
        S_tp = (S_td.cascade_com(S_l)).cascade_com(S_p)
    return S_tp

def _bulid_rxpkg(link_cfg: LinkConfig, rxpkg_cfg: COMPkgConfig) -> IEEECOMsparam:
    "Eq. 93A-16 and 93A-16a, 93A-16c"
    C_d = rxpkg_cfg.C_d * 1e-12
    L_s = rxpkg_cfg.L_s * 1e-9
    C_b = rxpkg_cfg.C_b * 1e-12
    C_p = rxpkg_cfg.C_p * 1e-12

    S_p = IEEECOMsparam.shunt_capacitance(link_cfg, C_p, rxpkg_cfg.R0)
    if (rxpkg_cfg.z_p2 is not None):
        S_l2 = IEEECOMsparam.pkg_trans_line(link_cfg, rxpkg_cfg.R0, rxpkg_cfg.z_p2, Zc=rxpkg_cfg.Z_c2)
    S_l = IEEECOMsparam.pkg_trans_line(link_cfg, rxpkg_cfg.R0, rxpkg_cfg.z_p, Zc=rxpkg_cfg.Z_c)
    S_b = IEEECOMsparam.shunt_capacitance(link_cfg, C_b, rxpkg_cfg.R0)
    S_s = IEEECOMsparam.series_inductance(link_cfg, L_s, rxpkg_cfg.R0)
    S_d = IEEECOMsparam.shunt_capacitance(link_cfg, C_d, rxpkg_cfg.R0)
    
    # cascade
    S_rd = (S_b.cascade_com(S_s)).cascade_com(S_d)
    if (rxpkg_cfg.z_p2 is not None):
        S_rp = ((S_p.cascade_com(S_l2)).cascade_com(S_l)).cascade_com(S_rd)
    else:
        S_rp = (S_p.cascade_com(S_l)).cascade_com(S_rd)
    return S_rp

def _bulid_channel_under_test(
    link_cfg: LinkConfig,
    channel_cfg: COMChannelConfig
) -> list[SparamModel]:
    """
    Build resampled channel-under-test S-parameter models.

    Output order:
    - index 0: victim channel
    - following indices: NEXT channels, then FEXT channels, in config order

    The returned models are resampled onto the same in-band subset of
    link_cfg.freqs so they can be directly used by later cascade / combination
    stages without another S-parameter-grid alignment step.
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

    common_f_stop = min(channel.freqs[-1] for channel in channel_models)
    common_freqs = link_cfg.freqs[link_cfg.freqs <= common_f_stop]
    if len(common_freqs) < 2:
        raise ValueError("No usable common frequency grid between link_cfg and channel S4P files.")

    return [channel.resampled(common_freqs) for channel in channel_models]

#%% conduct search in this class
class COM:
    def __init__(self, cfg: COMConfig):
        self.cfg = cfg

    def run(self) -> COMStatus:
        channels = _bulid_channel_under_test(self.cfg.link, self.cfg.channel)
        return self._bulid_status(
            link_cfg=self.cfg.link,
            ch_cfg=self.cfg.channel,
            pkg_cfg=self.cfg.pkg,
            ft_cfg=self.cfg.filter,
            channels=channels,
        )

    # -----------------------
    # Level-1 methods
    # -----------------------
    def _bulid_status(
        self,
        link_cfg: LinkConfig,
        ch_cfg: COMChannelConfig,
        pkg_cfg: COMPkgConfig,
        ft_cfg: COMFilterConfig,
        channels: list[SparamModel],
    ) -> COMStatus:
        common = self._bulid_common_status(link_cfg, pkg_cfg, ft_cfg)

        paths: list[COMPathStatus] = [
            self._bulid_path(
                kind="victim",
                S_ch=channels[0],
                common=common,
                ch_cfg=ch_cfg,
                link_cfg=link_cfg,
            )
        ]

        next_count = len(ch_cfg.next_s4p_paths)
        next_channels = channels[1 : 1 + next_count]
        fext_channels = channels[1 + next_count :]

        for S_ch in next_channels:
            paths.append(
                self._bulid_path(
                    kind="next",
                    S_ch=S_ch,
                    common=common,
                    ch_cfg=ch_cfg,
                    link_cfg=link_cfg,
                )
            )

        for S_ch in fext_channels:
            paths.append(
                self._bulid_path(
                    kind="fext",
                    S_ch=S_ch,
                    common=common,
                    ch_cfg=ch_cfg,
                    link_cfg=link_cfg,
                )
            )

        return COMStatus(common=common, paths=paths)

    def _bulid_common_status(
        self,
        link_cfg: LinkConfig,
        pkg_cfg: COMPkgConfig,
        ft_cfg: COMFilterConfig,
    ) -> COMCommonStatus:
        S_tp = _bulid_txpkg(link_cfg, pkg_cfg, isNext=False)
        S_tp_next = _bulid_txpkg(link_cfg, pkg_cfg, isNext=True)
        S_rp = _bulid_rxpkg(link_cfg, pkg_cfg)

        H_ffe = IEEECOMFilter.tx_ffe(link_cfg, ft_cfg.txfir, ft_cfg.num_pre)
        H_ffe_next = IEEECOMFilter.tx_ffe(link_cfg, self._next_txfir(ft_cfg), ft_cfg.num_pre)
        H_t = IEEECOMFilter.transition_time_filter(link_cfg, ft_cfg.Tr)
        H_r = IEEECOMFilter.rx_noise_filter(link_cfg, ft_cfg.fr)
        H_ctf = IEEECOMFilter.rx_equalizer(
            link_cfg,
            ft_cfg.g_DC,
            ft_cfg.g_DC2,
            ft_cfg.f_z,
            ft_cfg.f_LF,
            ft_cfg.f_p1,
            ft_cfg.f_p2,
        )

        return COMCommonStatus(
            S_tp=S_tp,
            S_tp_next=S_tp_next,
            S_rp=S_rp,
            H_ffe=H_ffe,
            H_ffe_next=H_ffe_next,
            H_t=H_t,
            H_r=H_r,
            H_ctf=H_ctf,
            X_v=IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_v),
            X_fe=IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_fe),
            X_ne=IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_ne),
        )

    def _bulid_path(
        self,
        kind: Literal["victim", "next", "fext"],
        S_ch: SparamModel,
        common: COMCommonStatus,
        ch_cfg: COMChannelConfig,
        link_cfg: LinkConfig,
    ) -> COMPathStatus:
        S_tp = common.S_tp_next if kind == "next" else common.S_tp
        H_ffe = common.H_ffe_next if kind == "next" else common.H_ffe
        X = {"victim": common.X_v, "next": common.X_ne, "fext": common.X_fe}[kind]

        S_all = (S_tp.cascade_com(S_ch)).cascade_com(common.S_rp)
        H_21 = S_all.to_LinkSegment(
            link_cfg,
            ch_cfg.gamma_src,
            ch_cfg.gamma_load,
        )
        H_all = (
            H_21
            .cascade_tf(H_ffe)
            .cascade_tf(common.H_t)
            .cascade_tf(common.H_r)
            .cascade_tf(common.H_ctf)
        )

        return COMPathStatus(
            kind=kind,
            S_ch=S_ch,
            S_all=S_all,
            H_21=H_21,
            H_all=H_all,
            X=X,
        )

    def _next_txfir(self, ft_cfg: COMFilterConfig) -> np.ndarray:
        txfir = np.zeros_like(ft_cfg.txfir, dtype=float)
        txfir[ft_cfg.num_pre] = 1.0
        return txfir
