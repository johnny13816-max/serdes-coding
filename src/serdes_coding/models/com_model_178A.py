"""
IEEE 802.3 Annex 178A COM model.

Public names in this module do not need a version suffix because the module
namespace already defines the spec version. Version-owned configuration and
passive state live in ``models.com_178a`` and are re-exported here. This module
temporarily retains the 178A stage implementations and COM pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from itertools import combinations, product
from pathlib import Path
import sys
from time import perf_counter
from typing import Any, Literal, Optional, Sequence
import numpy as np

try:
    from ..utilities.link import ContinuousPSD, GridOverflowError, LinkConfig, SampledPSD, SampledResponse
    from ..utilities.pmf import Pmf1D
    from ..search.com_search_178A import (
        COMSearchCandidate, COMSearchConfig, COMSearchRow, COMSearchStatus, run_full_search,
    )
    from .com_dataclass_text import COMDataclassText, TextField, TextSection
    from .com_178a import (
        COMAdcInputPMF, COMAddedNoiseIterationStatus, COMAddedNoiseStatus,
        COMChannelConfig, COMConfig, COMDTEConfig, COMDTEStatus,
        COMDevicePackageConfig, COMDeviceTermConfig, COMError,
        COMExecutionConfig, COMFilterConfig, COMImpStageStatus,
        COMImpairmentConfig, COMImpairmentStatus, COMLengthMismatchError,
        COMMainCursorError, COMMLSDConfig, COMMLSDNoiseStatus, COMMLSDStatus,
        COMPMFConfig, COMPMFRuntimeConfig, COMPMFStatus, COMPSDStatus,
        COMPartialHostConfig, COMPath, COMPolicyConfig, COMPkgConfig,
        COMRunConfig, COMRunStatus, COMSharedPath, COMStatus,
        COMTxfirMainCursorError, COMEqChannelStatus,
    )
    from .com_178a.path_stage import (
        COMBilinearCTLE, IEEECOMFilter, IEEECOMSparam,
        _apply_rectangular_unit_pulse, _build_H_ctf, _build_H_ffe,
        _build_H_ffe_next, _build_H_r, _build_H_t,
        _build_channel_under_test, _build_path, _build_paths, _build_rxpkg,
        _build_shared_path, _build_txpkg, _evaluate_pre_ctle_on_measured_grid,
        _realize_ctle_response, _reference_fd_to_td_record,
    )
except ImportError:
    # Support direct interactive execution of this canonical module.
    # Package execution continues to use the relative imports above.
    source_root = str(Path(__file__).resolve().parents[2])
    if source_root not in sys.path:
        sys.path.insert(0, source_root)
    from serdes_coding.utilities.link import ContinuousPSD, GridOverflowError, LinkConfig, SampledPSD, SampledResponse
    from serdes_coding.utilities.pmf import Pmf1D
    from serdes_coding.search.com_search_178A import (
        COMSearchCandidate, COMSearchConfig, COMSearchRow, COMSearchStatus, run_full_search,
    )
    from serdes_coding.models.com_dataclass_text import COMDataclassText, TextField, TextSection
    from serdes_coding.models.com_178a import (
        COMAdcInputPMF, COMAddedNoiseIterationStatus, COMAddedNoiseStatus,
        COMChannelConfig, COMConfig, COMDTEConfig, COMDTEStatus,
        COMDevicePackageConfig, COMDeviceTermConfig, COMError,
        COMExecutionConfig, COMFilterConfig, COMImpStageStatus,
        COMImpairmentConfig, COMImpairmentStatus, COMLengthMismatchError,
        COMMainCursorError, COMMLSDConfig, COMMLSDNoiseStatus, COMMLSDStatus,
        COMPMFConfig, COMPMFRuntimeConfig, COMPMFStatus, COMPSDStatus,
        COMPartialHostConfig, COMPath, COMPolicyConfig, COMPkgConfig,
        COMRunConfig, COMRunStatus, COMSharedPath, COMStatus,
        COMTxfirMainCursorError, COMEqChannelStatus,
    )
    from serdes_coding.models.com_178a.path_stage import (
        COMBilinearCTLE, IEEECOMFilter, IEEECOMSparam,
        _apply_rectangular_unit_pulse, _build_H_ctf, _build_H_ffe,
        _build_H_ffe_next, _build_H_r, _build_H_t,
        _build_channel_under_test, _build_path, _build_paths, _build_rxpkg,
        _build_shared_path, _build_txpkg, _evaluate_pre_ctle_on_measured_grid,
        _realize_ctle_response, _reference_fd_to_td_record,
    )


def _validate_positive_main_cursor(h_dsamp: np.ndarray, *, source_name: str, pos: int) -> None:
    """Require the dominant sampled input cursor to have positive polarity."""
    h_dsamp = np.asarray(h_dsamp, dtype=float)
    peak_index = int(np.argmax(np.abs(h_dsamp)))
    if h_dsamp[peak_index] <= 0.0:
        raise COMMainCursorError(
            f"{source_name} main cursor has non-positive polarity at pos={pos}: "
            f"index={peak_index}, value={h_dsamp[peak_index]:.6e}."
        )


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
    rss = np.zeros(per_ui)
    for phase in np.arange(per_ui):
        rss[phase] = np.sum(h_XT[phase::per_ui] ** 2)
    pos = int(np.argmax(rss))
    return pos, h_XT[pos::per_ui]

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
    X_v = IEEECOMFilter.rect_pulse(link_cfg, ft_cfg.A_v)
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
        return p_sig.copy().fir_filter(
            fir=h,
            keep_mass=pmf_cfg.keep_mass,
            dx_ref=pmf_cfg.dy,
            tap_abs_th=pmf_cfg.tap_abs_th,
            max_taps=None,
            name=name,
        )
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
        result = Pmf1D.multi_dirac(
            np.array([0.0]),
            np.array([1.0]),
            dx=pmf_cfg.dy,
            unit="volt",
            name="XT_all",
        )
        for response in responses:
            result = result.combine(
                _build_pmf_interference_178A(
                    p_sig,
                    response,
                    pmf_cfg,
                    L or len(p_sig.pmf),
                    method="signal_fir",
                    name="XT",
                ),
                name="XT_all",
            )
        result.name = "XT_all"
        return result
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
