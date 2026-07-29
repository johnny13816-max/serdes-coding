from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .link_segment import LinkConfig, LinkSegment, sparamModel


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


class IEEECOMsparam(sparamModel):
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
    sparamModel. This class only adds spec-defined COM construction behavior.
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
            LinkConfig that defines the frequency grid.
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
        - IEEE 802.3 Annex 93A.1.2.3, Eq. 93A-9a.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid.
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
        gamma0: float = 0.0,
        a1: float = float(1.734e-3),
        a2: float = float(1.455e-4),
        tau: float = float(6.141e-3),
        Zc: float = 78.2,
    ) -> 'IEEECOMsparam':
        """
        Build the COM package transmission-line Sdd two-port on cfg.freqs.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.4, Eq. 93A-9 through Eq. 93A-14.

        Parameters
        ----------
        cfg:
            LinkConfig that defines the frequency grid.
        R0:
            Single-ended reference resistance.
        zp:
            Package line length in millimeters.
        gamma0, a1, a2, tau:
            COM propagation-coefficient model parameters.
        Zc:
            Package differential characteristic impedance.
        """
        f = cfg.freqs
        if np.any(f < 0):
            raise ValueError("The package transmission-line model does not include f < 0.")

        R0 = float(R0)
        zp = float(zp)

        gamma1 = a1 * (1 + 1j)
        gamma2 = a2 * (1 - (1j * (2 / np.pi) * np.log(f[f > 0] / 1e9))) + 1j * 2 * np.pi * tau
        gamma2 = np.r_[0, gamma2]
        gamma = gamma0 + gamma1 * np.sqrt(f) + gamma2 * f
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

        return cls.from_sdd_array(cfg.freqs, sdd, z0=2 * R0)

    def cascade_com(self, other: sparamModel) -> 'IEEECOMsparam':
        """
        Cascade two Sdd two-port networks using IEEE COM equations.

        Reference:
        - IEEE 802.3 Annex 93A.1.2.1, Eq. 93A-4 through Eq. 93A-7.

        Parameters
        ----------
        other:
            Sdd two-port physically following self.
        """
        self.validate_compatible_sparam(other)
        cascaded_sdd = IEEECOM_cascade_sdd(self.sdd, other.sdd)
        return type(self).from_sdd_array(self.freqs, cascaded_sdd, z0=self.network.z0)


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


@dataclass
class COMChannelInput:
    """
    Input description for the channel path used by IEEE 802.3 Annex 93A COM.

    Parameters
    ----------
    freqs:
        Frequency axis of the input S-parameter data, in Hz.
    s4p:
        Single-ended four-port S-parameter matrix with shape (N, 4, 4).
    port_order:
        Old port order interpreted as (tx_p, tx_n, rx_p, rx_n).
    z0:
        Single-ended reference impedance of the S4P data.
    gamma_src:
        Source reflection coefficient used by Eq. 93A-18.
    gamma_load:
        Load reflection coefficient used by Eq. 93A-18.
    """
    freqs: np.ndarray
    s4p: np.ndarray
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3)
    z0: float = 50.0
    gamma_src: complex | np.ndarray = 0.0
    gamma_load: complex | np.ndarray = 0.0


@dataclass
class COMSignalPathConfig:
    """
    Optional linear filters applied after the terminated channel H21(f).

    Parameters
    ----------
    tx_fir:
        TX FFE taps for Eq. 93A-21. None disables the block.
    tx_num_pre:
        Number of pre-cursor taps before the TX FFE main cursor.
    rx_eq:
        CTLE parameters for Eq. 93A-22. Use keys g_DC, g_DC2, f_z, f_LF,
        f_p1, and f_p2. None disables the block.
    rect_pulse_amplitude:
        Amplitude parameter At for the rectangular pulse of Eq. 93A-23. None
        disables the block.
    """
    tx_fir: np.ndarray | None = None
    tx_num_pre: int = 0
    rx_eq: dict[str, float] | None = None
    rect_pulse_amplitude: float | None = None


@dataclass
class COMComputationResult:
    """
    Container for intermediate and final COM calculation results.

    Parameters
    ----------
    channel_sparam:
        Differential two-port S-parameter model converted from the input S4P.
    channel_response:
        Terminated scalar H21(f) represented as a LinkSegment.
    signal_path:
        Linear signal path after optional TX/RX filtering.
    com_db:
        Final COM value in dB. None until 93A.1.6 and 93A.1.7 are implemented.
    """
    channel_sparam: sparamModel
    channel_response: LinkSegment
    signal_path: LinkSegment
    com_db: float | None = None
    notes: list[str] = field(default_factory=list)


class COMModel93A:
    """
    Orchestrator for IEEE 802.3 Annex 93A COM calculation.

    Class boundary
    --------------
    COMModel93A owns the calculation flow across existing lower-level objects:
    - S4P/Sdd channel ingestion through sparamModel
    - terminated voltage transfer H21(f) through Eq. 93A-18
    - scalar filter cascade through LinkSegment / IEEECOMFilter
    - later: 93A.1.6 equalizer/FOM optimization
    - later: 93A.1.7 interference and noise amplitude distribution

    It should not reimplement S-parameter storage, FFT scaling, or PMF algebra.
    Those remain in sparamModel, LinkSegment, and Pmf1D.
    """

    def __init__(self, cfg: LinkConfig):
        """
        Parameters
        ----------
        cfg:
            Shared LinkConfig grid used by all LinkSegment objects in this COM
            calculation.
        """
        if not isinstance(cfg, LinkConfig):
            raise TypeError("cfg must be a LinkConfig.")
        self.cfg = cfg

    def channel_sparam_from_s4p(self, channel: COMChannelInput) -> sparamModel:
        """
        Convert the input single-ended S4P channel to a differential Sdd model.

        Parameters
        ----------
        channel:
            Channel S4P input and reference impedance metadata.
        """
        if not isinstance(channel, COMChannelInput):
            raise TypeError("channel must be a COMChannelInput.")

        return sparamModel.from_s4p_array(
            freqs=channel.freqs,
            s4p=channel.s4p,
            port_order=channel.port_order,
            z0=2.0 * channel.z0,
        )

    def channel_response(self, channel: COMChannelInput) -> tuple[sparamModel, LinkSegment]:
        """
        Build the terminated channel voltage transfer H21(f).

        Parameters
        ----------
        channel:
            Channel S4P input plus Eq. 93A-18 source/load reflection
            coefficients.
        """
        channel_sparam = self.channel_sparam_from_s4p(channel)
        response = channel_sparam.to_LinkSegment(
            cfg=self.cfg,
            gamma_src=channel.gamma_src,
            gamma_load=channel.gamma_load,
        )
        return channel_sparam, response

    def signal_path(
        self,
        channel_response: LinkSegment,
        path_cfg: COMSignalPathConfig | None = None,
    ) -> LinkSegment:
        """
        Cascade optional linear TX/RX filters onto the scalar channel response.

        Parameters
        ----------
        channel_response:
            Terminated channel response H21(f) on self.cfg.
        path_cfg:
            Optional TX FFE, RX CTLE, and rectangular pulse settings.
        """
        if not isinstance(channel_response, LinkSegment):
            raise TypeError("channel_response must be a LinkSegment.")

        path_cfg = path_cfg or COMSignalPathConfig()
        signal = channel_response

        for filt in self._build_filters(path_cfg):
            signal = signal.cascade_tf(filt)

        return signal

    def run(
        self,
        channel: COMChannelInput,
        path_cfg: COMSignalPathConfig | None = None,
    ) -> COMComputationResult:
        """
        Run the implemented subset of the Annex 93A COM calculation.

        Parameters
        ----------
        channel:
            Channel S4P input and termination settings.
        path_cfg:
            Optional linear signal-path filter settings.
        """
        channel_sparam, channel_response = self.channel_response(channel)
        signal_path = self.signal_path(channel_response, path_cfg)

        return COMComputationResult(
            channel_sparam=channel_sparam,
            channel_response=channel_response,
            signal_path=signal_path,
            com_db=None,
            notes=[
                "Full COM is not calculated yet: 93A.1.6 optimization is not implemented.",
                "Full COM is not calculated yet: 93A.1.7 noise/interference distribution is not integrated.",
            ],
        )

    def _build_filters(self, path_cfg: COMSignalPathConfig) -> Sequence[LinkSegment]:
        filters: list[LinkSegment] = []

        if path_cfg.tx_fir is not None:
            filters.append(IEEECOMFilter.tx_ffe(self.cfg, path_cfg.tx_fir, path_cfg.tx_num_pre))

        if path_cfg.rx_eq is not None:
            filters.append(IEEECOMFilter.rx_equalizer(self.cfg, **path_cfg.rx_eq))

        if path_cfg.rect_pulse_amplitude is not None:
            filters.append(IEEECOMFilter.rect_pulse(self.cfg, path_cfg.rect_pulse_amplitude))

        return filters
