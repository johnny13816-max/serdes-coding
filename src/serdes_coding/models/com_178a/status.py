"""Version-owned Annex 178A calculation-state contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np

from ...utilities.link import LinkSegment, SampledPSD, SampledResponse
from ...utilities.pmf import Pmf1D
from ...utilities.sparam import SparamModel
from ..com_dataclass_text import COMDataclassText, TextField, TextSection


@dataclass(repr=False)
class COMSharedPath(COMDataclassText):
    """Filters and RX package shared by every victim and aggressor path."""

    H_ffe: Any
    H_ffe_next: Any
    H_t: Any
    S_rx: SparamModel
    H_r: Any
    H_ctf: Any
    ctle_iir: Optional[Any] = None

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


@dataclass(repr=False)
class COMPath(COMDataclassText):
    """One constructed victim, NEXT, or FEXT signal path."""

    kind: Literal["victim", "next", "fext"]
    shared: COMSharedPath
    S_tx: SparamModel
    S_ch: SparamModel
    S_all: SparamModel
    H_21: LinkSegment
    H_all: LinkSegment
    X: Any
    pulse: LinkSegment

    @property
    def H_ffe(self) -> Any:
        return self.shared.H_ffe_next if self.kind == "next" else self.shared.H_ffe

    @property
    def H_t(self) -> Any:
        return self.shared.H_t

    @property
    def S_rx(self) -> SparamModel:
        return self.shared.S_rx

    @property
    def H_r(self) -> Any:
        return self.shared.H_r

    @property
    def H_ctf(self) -> Any:
        return self.shared.H_ctf

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Path", (
                self._field("kind", "path kind", stored_unit="category"),
                self._field("S_tx", "TX package network", stored_unit="S-parameter", summary="shape"),
                self._field("S_ch", "measured channel network", stored_unit="S-parameter", summary="shape"),
                self._field("S_all", "cascaded network", stored_unit="S-parameter", summary="shape"),
                self._field("H_21", "terminated channel response", stored_unit="dimensionless", summary="shape"),
                self._field("H_all", "equalized channel response", stored_unit="dimensionless", summary="shape"),
                self._field("pulse", "pulse response", stored_unit="V", summary="shape"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("kind", "path kind", stored_unit="category"),
            self._field("pulse", "pulse response", stored_unit="V", summary="shape"),
        )


@dataclass(repr=False)
class COMPMFStatus(COMDataclassText):
    """PMF-domain intermediate and final results for Annex 178A."""

    dy: float
    tap_abs_th: float
    p_ISI: Optional[Pmf1D] = None
    p_G: Optional[Pmf1D] = None
    p_DD: Optional[Pmf1D] = None
    p_XT: Optional[Pmf1D] = None
    p_qn: Optional[Pmf1D] = None
    p_combined: Optional[Pmf1D] = None
    y0: Optional[float] = None
    A_ni: Optional[float] = None
    COM: Optional[float] = None

    def _text_sections(self) -> tuple[TextSection, ...]:
        return (
            TextSection("Grid", (
                self._field("dy", "PMF grid step", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("tap_abs_th", "tap threshold", stored_unit="V", display_unit="mV", scale=1e3),
            )),
            TextSection("Components", (
                self._field("p_ISI", "ISI PMF", stored_unit="probability mass"),
                self._field("p_G", "Gaussian PMF", stored_unit="probability mass"),
                self._field("p_DD", "dual-Dirac PMF", stored_unit="probability mass"),
                self._field("p_XT", "crosstalk PMF", stored_unit="probability mass"),
                self._field("p_qn", "quantization PMF", stored_unit="probability mass"),
                self._field("p_combined", "combined PMF", stored_unit="probability mass"),
            )),
            TextSection("Result", (
                self._field("y0", "decision threshold", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("A_ni", "noise and interference amplitude", stored_unit="V", display_unit="mV", scale=1e3),
                self._field("COM", "COM DFE", stored_unit="dB"),
            )),
        )

    def _repr_fields(self) -> tuple[TextField, ...]:
        return (
            self._field("dy", "PMF grid step", stored_unit="V", display_unit="mV", scale=1e3),
            self._field("A_ni", "noise and interference amplitude", stored_unit="V", display_unit="mV", scale=1e3),
            self._field("COM", "COM DFE", stored_unit="dB"),
        )


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
        """Compatibility export for 178A status without a report renderer.

        The inherited 93A exporter assumes the flat 93A impairment contract,
        including ``imp.sigma_TX``. 178A impairment data is grouped by stage,
        so top-K finalization must use a 178A-specific export boundary. This
        compatibility method remains on the state object until reporting owns
        all file output in a later architecture batch.
        """
        out_dir = Path(save_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        summary_path = out_dir / "status_summary.txt"
        summary_path.write_text(str(self), encoding="utf-8")
        return {"status_summary_txt": str(summary_path)}
