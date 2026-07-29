from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from .link_segment import IEEECOMFilter, LinkConfig, LinkSegment, sparamModel


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
