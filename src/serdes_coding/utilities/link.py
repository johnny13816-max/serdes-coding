from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, cast
from dataclasses import dataclass, field
import skrf as rf

from .psd import ContinuousPSD, OneSidePSD, SampledPSD

if TYPE_CHECKING:
    from matplotlib.axes import Axes

SdefT = Literal["power", "pseudo", "traveling"]

# =========================
# helper
# =========================
def isFreqsEqual(f1: np.ndarray, f2: np.ndarray, rtol: float = 1e-9, atol: float = 1e-6) -> bool:
    f1 = np.asarray(f1, dtype=float)
    f2 = np.asarray(f2, dtype=float)

    if f1.shape != f2.shape:
        return False

    return np.allclose(f1, f2, rtol=rtol, atol=atol)

def resample_tf(
    H_meas: np.ndarray,
    freqs_meas: np.ndarray,
    freqs_new: np.ndarray,
    taper_ratio: float = 0.25,
    min_tail_points: int = 5,
) -> np.ndarray:
    """
    Resample a measured transfer function onto the target rfft frequency grid.

    In band => linear interpolate.
    Out band:
        extends phase using estimated group delay (constant group delay), 
        and smoothly tapers magnitude to zero.
    """
    def normalize_and_validate_inputs() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        H = np.asarray(H_meas, dtype=complex)
        f_meas = np.asarray(freqs_meas, dtype=float)
        f_new = np.asarray(freqs_new, dtype=float)

        if H.shape != f_meas.shape:
            raise ValueError("H_meas and freqs_meas must have the same shape.")

        if f_meas.ndim != 1 or f_new.ndim != 1:
            raise ValueError("freqs_meas and freqs_new must be 1D arrays.")

        if len(f_meas) < 2 or len(f_new) < 2:
            raise ValueError("Frequency axes must contain at least two points.")

        if not np.all(np.isfinite(f_meas)) or not np.all(np.isfinite(f_new)):
            raise ValueError("Frequency axes must be finite.")

        if not np.all(np.diff(f_meas) > 0):
            raise ValueError("freqs_meas must be strictly increasing.")

        if not np.all(np.diff(f_new) > 0):
            raise ValueError("freqs_new must be strictly increasing.")

        # Check that the target FFT frequency axis is uniformly spaced.
        LinkConfig.validate_freqs(f_new, require_uniform=True)

        if f_meas[0] > f_new[0]:
            raise ValueError("freqs_meas must include the target DC / low-frequency start.")

        return H, f_meas, f_new

    def extend_phase_with_group_delay() -> None:
        tail = max(min_tail_points, len(freqs_meas) // 10)
        tail = min(tail, len(freqs_meas))

        p = np.polyfit(freqs_meas[-tail:], phase_meas[-tail:], 1)
        dphi_df = p[0]
        tau = -dphi_df / (2 * np.pi)

        beyond = freqs_new > f_stop
        phase_at_stop = phase_meas[-1]
        phase_new[beyond] = phase_at_stop - 2 * np.pi * tau * (freqs_new[beyond] - f_stop)

    def extend_mag_with_taper() -> None:
        beyond = freqs_new > f_stop
        taper_bw = taper_ratio * f_stop
        if taper_bw <= 0:
            raise ValueError("taper bandwidth must be positive.")

        f_taper_end = min(f_nyq, f_stop + taper_bw)

        if f_taper_end <= f_stop:
            mag_new[beyond] = 0.0
            return

        taper_region = (freqs_new > f_stop) & (freqs_new < f_taper_end)
        zero_region = freqs_new >= f_taper_end

        mag_at_stop = mag_meas[-1]

        u = (freqs_new[taper_region] - f_stop) / (f_taper_end - f_stop)
        taper = 0.5 * (1 + np.cos(np.pi * u))

        mag_new[taper_region] = mag_at_stop * taper
        mag_new[zero_region] = 0.0

    H_meas, freqs_meas, freqs_new = normalize_and_validate_inputs()
    f_stop = freqs_meas[-1]
    f_nyq = freqs_new[-1]

    mag_meas = np.abs(H_meas)
    phase_meas = np.unwrap(np.angle(H_meas))

    # Base interpolation region.
    interp_freq = np.minimum(freqs_new, f_stop)

    mag_new = np.interp(interp_freq, freqs_meas, mag_meas)
    phase_new = np.interp(interp_freq, freqs_meas, phase_meas)

    # Case A: measurement covers target Nyquist.
    if f_stop >= f_nyq:
        H_new = mag_new * np.exp(1j * phase_new)
        H_new[0] = H_new[0].real + 0j
        H_new[-1] = H_new[-1].real + 0j
        return H_new

    # Case B: measurement does not cover target Nyquist.
    extend_phase_with_group_delay()
    extend_mag_with_taper()

    H_new = mag_new * np.exp(1j * phase_new)

    # Real-valued h(t) constraints for rfft/irfft with even Nfft.
    H_new[0] = H_new[0].real + 0j
    H_new[-1] = H_new[-1].real + 0j

    return H_new

def _differential_z0_from_s4p_z0(
    z0: Union[float, np.ndarray],
    port_order: tuple[int, int, int, int],
) -> Union[float, np.ndarray]:
    """
    Derive Sdd two-port reference impedance from single-ended S4P z0.

    port_order is the old S4P order mapped to:
        (tx_p, tx_n, rx_p, rx_n)

    For equal single-ended ports this reduces to 2*R0. For skrf's per-frequency
    per-port z0 arrays, this returns a two-port array:
        [z0_tx_p + z0_tx_n, z0_rx_p + z0_rx_n]
    """
    port_order = _validate_s4p_port_order(port_order)

    if np.isscalar(z0):
        return 2.0 * float(z0)

    z0_array = np.asarray(z0)
    if z0_array.ndim == 0:
        return 2.0 * float(z0_array)

    if z0_array.shape[-1] != 4:
        raise ValueError("S4P network.z0 must be scalar or have four port impedances.")

    z0_ordered = z0_array[..., port_order]
    return np.stack(
        [
            z0_ordered[..., 0] + z0_ordered[..., 1],
            z0_ordered[..., 2] + z0_ordered[..., 3],
        ],
        axis=-1,
    )

def _validate_s4p_port_order(port_order: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if len(port_order) != 4:
        raise ValueError("port_order must contain four zero-based port indices.")

    # ensure all elements are integers
    port_order = (
        int(port_order[0]),
        int(port_order[1]),
        int(port_order[2]),
        int(port_order[3])
    )
    if sorted(port_order) != [0, 1, 2, 3]:
        raise ValueError("port_order must be a permutation of (0, 1, 2, 3).")

    return port_order

def _validate_s4p(s4p: np.ndarray, freqs: np.ndarray) -> np.ndarray:
    s4p = np.asarray(s4p, dtype=complex)

    if s4p.shape != (len(freqs), 4, 4):
        raise ValueError("s4p must have shape (len(freqs), 4, 4).")

    if not np.all(np.isfinite(s4p)):
        raise ValueError("s4p contains non-finite values.")

    return s4p

def _renum_s4p(
    s4p: np.ndarray,
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
) -> np.ndarray:
    """
    Return S4P reordered to the project's single-ended COM input order.

    Parameters
    ----------
    s4p:
        Single-ended 4-port S-parameter array with shape (N, 4, 4).
    port_order:
        Old zero-based S4P ports in desired order:
            (tx_p, tx_n, rx_p, rx_n)
    """
    s4p = np.asarray(s4p, dtype=complex)
    if s4p.ndim != 3 or s4p.shape[1:] != (4, 4):
        raise ValueError("s4p must have shape (N, 4, 4).")

    if not np.all(np.isfinite(s4p)):
        raise ValueError("s4p contains non-finite values.")

    port_order = _validate_s4p_port_order(port_order)
    return s4p[:, port_order, :][:, :, port_order]

def _s4p_to_sdd(
    s4p: np.ndarray,
    port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
    freqs: np.ndarray | None = None,
) -> np.ndarray:
    """
    Convert single-ended S4P to differential-mode Sdd.

    port_order gives old single-ended S4P ports in the desired COM-style order:
        (tx_p, tx_n, rx_p, rx_n)

    After reordering to this convention, the through term is:
        Sdd21 = 0.5 * (S31 - S32 - S41 + S42)
    """
    if freqs is None:
        s4p = np.asarray(s4p, dtype=complex)
        if s4p.ndim != 3 or s4p.shape[1:] != (4, 4):
            raise ValueError("s4p must have shape (N, 4, 4).")
        if not np.all(np.isfinite(s4p)):
            raise ValueError("s4p contains non-finite values.")
    else:
        s4p = _validate_s4p(s4p, freqs)

    s = _renum_s4p(s4p, port_order)

    S11, S12, S13, S14 = s[:, 0, 0], s[:, 0, 1], s[:, 0, 2], s[:, 0, 3]
    S21, S22, S23, S24 = s[:, 1, 0], s[:, 1, 1], s[:, 1, 2], s[:, 1, 3]
    S31, S32, S33, S34 = s[:, 2, 0], s[:, 2, 1], s[:, 2, 2], s[:, 2, 3]
    S41, S42, S43, S44 = s[:, 3, 0], s[:, 3, 1], s[:, 3, 2], s[:, 3, 3]

    Sdd11 = 0.5 * (S11 - S12 - S21 + S22)
    Sdd21 = 0.5 * (S31 - S32 - S41 + S42)
    Sdd12 = 0.5 * (S13 - S14 - S23 + S24)
    Sdd22 = 0.5 * (S33 - S34 - S43 + S44)

    return np.stack([
        np.stack([Sdd11, Sdd12], axis=-1),
        np.stack([Sdd21, Sdd22], axis=-1),
    ], axis=-2)

# ========================
# classes
# ========================

@dataclass
class LinkConfig:
    """
    Frequency/time grid definition shared by LinkSegment and COM S-param builders.

    Class boundary
    --------------
    LinkConfig owns only sampling-grid convention:
    - baud frequency and UI
    - samples per UI
    - FFT length and rfft frequency axis
    - time axis used by impulse/step/single-bit responses

    It should not own channel data, S-parameters, or response conversion logic.
    """
    fb: float = 53.125e9                            # unit: Hz, baud/signaling frequency
    per_ui: int = 64                                # unit: samples/UI
    target_df: float = 1e8                          # unit: Hz, requested frequency resolution

    # ----- derived attributes -----
    bt: float = field(init=False)                   # unit: s/UI
    L_ui: int = field(init=False)                   # unit: UI, total time span

    # fft pair setup
    Nfft: int = field(init=False)                   # even points, s.t. freqs include H(f=Fs/2)
    Fs: float = field(init=False)                   # unit: Hz, sampling frequency
    f_nyq: float = field(init=False)                # unit: Hz, Nyquist frequency
    dt: float = field(init=False)                   # unit: s, sample interval
    df: float = field(init=False)                   # unit: Hz, exact frequency resolution
    T_max: float = field(init=False)                # unit: s, total time span
    freqs: np.ndarray = field(init=False)           # unit: Hz, positive half side, np.arange(0,Fs/2+df,df)
    times: np.ndarray = field(init=False)           # unit: sec
    times_ui: np.ndarray = field(init=False)        # unit: UI
    sampled_nfft: int = field(init=False)           # unit: samples, symbol-rate sampled-domain FFT length
    sampled_df: float = field(init=False)            # unit: Hz, sampled-domain frequency resolution
    theta: np.ndarray = field(init=False)            # unit: rad/sample, sampled-domain rfft axis [0, pi]
    theta_freqs: np.ndarray = field(init=False)      # unit: Hz, equivalent baseband axis theta*fb/(2*pi)

    def __post_init__(self):
        self.bt = 1.0 / self.fb
        self.dt = self.bt / self.per_ui
        self.Fs = 1.0 / self.dt
        self.f_nyq = self.Fs / 2
        raw_nfft = int(np.ceil(self.Fs / self.target_df))
        # Default configs align the continuous-time rfft grid and the
        # symbol-rate sampled-domain rfft grid to the same df:
        #   df = Fs/Nfft = fb/sampled_nfft, sampled_nfft = Nfft/per_ui.
        # The 2*per_ui block keeps Nfft/per_ui even, so theta includes pi.
        block = 2 * int(self.per_ui)
        nfft = int(np.ceil(raw_nfft / block) * block)
        self._set_derived_grid(nfft)

    @classmethod
    def from_Nfft(
        cls,
        fb: float,
        per_ui: int,
        Nfft: int,
        target_df: float | None = None,
    ) -> 'LinkConfig':
        """
        Build a LinkConfig directly from FFT length.

        Parameters
        ----------
        fb:
            Baud frequency in Hz.
        per_ui:
            Number of samples per UI.
        Nfft:
            Even FFT length. Even length is required so rfft includes a Nyquist
            bin and LinkSegment.validate_tf() remains valid.
        target_df:
            Optional metadata target df. If None, use the resulting exact df.
        """
        cfg = cls.__new__(cls)
        cfg.fb = fb
        cfg.per_ui = per_ui
        cfg.bt = 1.0 / cfg.fb
        cfg.dt = cfg.bt / cfg.per_ui
        cfg.Fs = 1.0 / cfg.dt
        cfg.f_nyq = cfg.Fs / 2
        cfg.target_df = cfg.Fs / Nfft if target_df is None else target_df
        cfg._set_derived_grid(Nfft)
        return cfg

    def _set_derived_grid(self, Nfft: int) -> None:
        Nfft = int(Nfft)
        if Nfft < 2:
            raise ValueError("Nfft must be at least 2.")
        if Nfft % 2 != 0:
            raise ValueError("Nfft must be even so rfft includes a Nyquist bin.")

        self.Nfft = Nfft
        self.df = self.Fs / self.Nfft
        self.T_max = 1.0 / self.df
        self.freqs = np.fft.rfftfreq(self.Nfft, d=self.dt)      
        self.times = np.arange(self.Nfft) * self.dt
        self.L_ui = int(self.Nfft / self.per_ui)
        self.times_ui = self.times / self.bt
        self._set_sampled_grid()

        self.validate_freqs(self.freqs, require_uniform=True, expected_stop=self.f_nyq)
        self.validate_times(self.times, expected_stop=self.T_max - self.dt)

    def _set_sampled_grid(self) -> None:
        """
        Define the symbol-rate sampled-domain rfft grid.

        For default LinkConfig objects, Nfft is chosen as a multiple of
        2*per_ui, so sampled_df equals the continuous-time df exactly. For
        from_Nfft() configs created from arbitrary linear-convolution lengths,
        use the closest even sampled-domain FFT length.
        """
        if self.Nfft % self.per_ui == 0:
            sampled_nfft = self.Nfft // self.per_ui
        else:
            sampled_nfft = int(np.ceil(self.fb / self.df))

        sampled_nfft = max(2, int(sampled_nfft))
        if sampled_nfft % 2 != 0:
            sampled_nfft += 1

        self.sampled_nfft = sampled_nfft
        self.sampled_df = self.fb / self.sampled_nfft
        self.theta = np.linspace(0.0, np.pi, self.sampled_nfft // 2 + 1)
        self.theta_freqs = self.theta * self.fb / (2 * np.pi)

    @staticmethod
    def validate_freqs(
        freqs: np.ndarray,
        require_uniform: bool = False,
        expected_stop: float | None = None,
        rtol: float = 1e-9,
        atol: float = 1e-15,
    ) -> np.ndarray:
        """
        Validate a frequency axis.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        require_uniform:
            If True, require all frequency steps to be equal within tolerance.
        expected_stop:
            Optional expected last frequency value. LinkConfig uses this to
            check that cfg.freqs ends at cfg.f_nyq.
        rtol:
            Relative tolerance for uniform-grid and endpoint checks.
        atol:
            Absolute tolerance for uniform-grid and endpoint checks.
        """
        freqs = np.asarray(freqs, dtype=float)

        # Check that the frequency axis is one-dimensional.
        if freqs.ndim != 1:
            raise ValueError("freqs must be a 1D array.")

        # Check that the frequency axis has enough points for interpolation.
        if len(freqs) < 2:
            raise ValueError("freqs must contain at least two points.")

        # Check that all frequency values are finite.
        if not np.all(np.isfinite(freqs)):
            raise ValueError("freqs contains non-finite values.")

        # Check that the frequency axis is non-negative.
        if freqs[0] < 0:
            raise ValueError("freqs must be non-negative.")

        # Check that the frequency axis is strictly increasing.
        if not np.all(np.diff(freqs) > 0):
            raise ValueError("freqs must be strictly increasing.")

        if require_uniform:
            df = np.diff(freqs)
            if not np.allclose(df, df[0], rtol=rtol, atol=atol):
                raise ValueError("freqs must be uniformly spaced.")

        if expected_stop is not None:
            if not np.isclose(freqs[-1], expected_stop, rtol=rtol, atol=atol):
                raise ValueError("freqs[-1] must equal expected_stop within numerical tolerance.")

        return freqs

    @staticmethod
    def validate_times(
        times: np.ndarray,
        expected_stop: float | None = None,
        rtol: float = 1e-12,
        atol: float = 1e-15,
    ) -> np.ndarray:
        """
        Validate a time axis.

        Parameters
        ----------
        times:
            Time axis in seconds.
        expected_stop:
            Optional expected last time value. LinkConfig uses this to check
            that cfg.times ends at cfg.T_max - cfg.dt.
        rtol:
            Relative tolerance for endpoint checks.
        atol:
            Absolute tolerance for endpoint checks.
        """
        times = np.asarray(times, dtype=float)

        if times.ndim != 1:
            raise ValueError("times must be a 1D array.")

        if len(times) < 2:
            raise ValueError("times must contain at least two points.")

        if not np.all(np.isfinite(times)):
            raise ValueError("times contains non-finite values.")

        if not np.all(np.diff(times) > 0):
            raise ValueError("times must be strictly increasing.")

        if expected_stop is not None:
            if not np.isclose(times[-1], expected_stop, rtol=rtol, atol=atol):
                raise ValueError("times[-1] must equal expected_stop within numerical tolerance.")

        return times


@dataclass
class SampledResponse:
    """
    Sampled/discrete-time response container.

    Class boundary
    --------------
    SampledResponse owns a discrete-time LTI response on a normalized
    one-sided rfft-style frequency axis. It is the sampled-domain counterpart
    of LinkSegment, but it does not represent a continuous-time physical link
    and does not apply continuous-time IFFT scaling.

    Stored conventions:
    - theta: rad/sample, one-sided rfft-style grid from 0 to pi.
    - tf: H(e^jtheta), complex sampled-domain transfer function.
    - ir: h[n], discrete-time impulse response.
    - fb: sampling rate / baud rate in Hz.
    """
    theta: np.ndarray                # unit: rad/sample, one-sided rfft-style axis
    tf: np.ndarray                   # unit: response gain, H(e^jtheta)
    ir: np.ndarray                   # unit: discrete-time impulse response h[n]
    fb: float                        # unit: Hz, sampling rate / baud rate

    def __post_init__(self) -> None:
        self.theta = self.validate_rfft_theta(self.theta)
        self.tf = self.validate_tf(self.tf, self.theta)
        self.ir = self.validate_ir(self.ir)
        expected_ir_len = 2 * (len(self.theta) - 1)
        if len(self.ir) != expected_ir_len:
            raise ValueError(
                "ir length must match the even-length rfft theta grid. "
                f"Expected {expected_ir_len}, got {len(self.ir)}."
            )
        self.fb = float(self.fb)
        if not np.isfinite(self.fb) or self.fb <= 0.0:
            raise ValueError("fb must be finite and positive.")

    @staticmethod
    def validate_rfft_theta(theta: np.ndarray) -> np.ndarray:
        """
        Validate a one-sided even-length rfft theta grid.

        Parameters
        ----------
        theta:
            Frequency axis in rad/sample. First point must be 0, last point
            must be pi, and spacing must be uniform.
        """
        theta = SampledPSD.validate_theta(theta)
        if not np.isclose(theta[0], 0.0):
            raise ValueError("theta[0] must be 0 for SampledResponse.")
        if not np.isclose(theta[-1], np.pi):
            raise ValueError("theta[-1] must be pi for SampledResponse.")
        steps = np.diff(theta)
        if not np.allclose(steps, steps[0], rtol=1e-12, atol=1e-15):
            raise ValueError("theta must be uniformly spaced for SampledResponse.")
        return theta

    @staticmethod
    def validate_tf(tf: np.ndarray, theta: np.ndarray) -> np.ndarray:
        """
        Validate sampled-domain transfer-function samples.

        Parameters
        ----------
        tf:
            Complex one-sided transfer function H(e^jtheta).
        theta:
            One-sided theta grid used for shape checking.
        """
        tf = np.asarray(tf, dtype=complex)
        if tf.shape != theta.shape:
            raise ValueError("tf and theta must have the same shape.")
        if tf.ndim != 1:
            raise ValueError("tf must be a 1D array.")
        if not np.all(np.isfinite(tf)):
            raise ValueError("tf contains non-finite values.")
        if not np.isclose(tf[0].imag, 0.0):
            raise ValueError("SampledResponse tf[0] must be real for irfft.")
        if not np.isclose(tf[-1].imag, 0.0):
            raise ValueError("SampledResponse tf[-1] must be real for even-length irfft.")
        return tf

    @staticmethod
    def validate_ir(ir: np.ndarray) -> np.ndarray:
        """
        Validate discrete-time impulse response samples.

        Parameters
        ----------
        ir:
            Real-valued discrete-time impulse response h[n].
        """
        ir = np.asarray(ir, dtype=float)
        if ir.ndim != 1:
            raise ValueError("ir must be a 1D array.")
        if len(ir) < 2:
            raise ValueError("ir must contain at least two samples.")
        if len(ir) % 2 != 0:
            raise ValueError("SampledResponse currently requires even-length ir.")
        if not np.all(np.isfinite(ir)):
            raise ValueError("ir contains non-finite values.")
        return ir

    @classmethod
    def from_tf(
        cls,
        theta: np.ndarray,
        tf: np.ndarray,
        fb: float,
        nfft: Optional[int] = None,
    ) -> 'SampledResponse':
        """
        Build SampledResponse from H(e^jtheta).

        Parameters
        ----------
        theta:
            One-sided rfft-style theta grid in rad/sample.
        tf:
            Complex H(e^jtheta) samples on theta.
        fb:
            Sampling rate / baud rate in Hz.
        nfft:
            Optional even FFT length. If omitted, use 2*(len(tf)-1).
            When provided, it must be consistent with len(tf).

        Notes
        -----
        Uses DSP DFT convention directly:
            ir = irfft(tf)
        No continuous-time Fs scaling is applied.
        """
        theta = cls.validate_rfft_theta(theta)
        tf = cls.validate_tf(tf, theta)
        if nfft is None:
            nfft = 2 * (len(theta) - 1)
        nfft = int(nfft)
        if nfft <= 0 or nfft % 2 != 0:
            raise ValueError("SampledResponse nfft must be a positive even integer.")
        if len(tf) != nfft // 2 + 1:
            raise ValueError("len(tf) must equal nfft//2 + 1.")
        ir = np.fft.irfft(tf, n=nfft)
        return cls(theta=theta, tf=tf, ir=ir, fb=fb)

    @classmethod
    def from_ir(
        cls,
        ir: np.ndarray,
        cfg: LinkConfig,
    ) -> 'SampledResponse':
        """
        Build SampledResponse from discrete-time impulse response h[n].

        Parameters
        ----------
        ir:
            Real-valued discrete-time impulse response h[n].
        cfg:
            LinkConfig that owns the sampled-domain grid. The response is
            zero-padded to cfg.sampled_nfft and uses cfg.theta as its
            one-sided sampled-domain frequency axis.
        """
        ir = np.asarray(ir, dtype=float)
        if ir.ndim != 1:
            raise ValueError("ir must be a 1D array.")
        if len(ir) < 1:
            raise ValueError("ir must contain at least one sample.")
        if not np.all(np.isfinite(ir)):
            raise ValueError("ir contains non-finite values.")
        nfft = int(cfg.sampled_nfft)
        if nfft < len(ir):
            raise ValueError("cfg.sampled_nfft must be greater than or equal to len(ir).")
        if nfft % 2 != 0:
            raise ValueError("cfg.sampled_nfft must be even.")
        ir_padded = np.zeros(nfft, dtype=float)
        ir_padded[:len(ir)] = ir
        tf = np.fft.rfft(ir_padded, n=nfft)
        return cls(theta=cfg.theta, tf=tf, ir=ir_padded, fb=cfg.fb)

    @property
    def freqs(self) -> np.ndarray:
        """
        Debug convenience axis in Hz: f = theta*fb/(2*pi).
        """
        return self.theta * self.fb / (2 * np.pi)

    @property
    def nfft(self) -> int:
        """
        Even FFT length associated with this rfft-style sampled response.
        """
        return int(len(self.ir))

    def magnitude_squared(self) -> np.ndarray:
        """
        Return |H(e^jtheta)|^2 on this response's theta grid.
        """
        return np.abs(self.tf) ** 2

    def cascade_tf(self, other: 'SampledResponse') -> 'SampledResponse':
        """
        Cascade two sampled-domain responses by multiplying transfer functions.

        Parameters
        ----------
        other:
            Another SampledResponse on the same theta grid and fb.
        """
        if not np.isclose(self.fb, other.fb):
            raise ValueError("SampledResponse fb values must match.")
        if not np.allclose(self.theta, other.theta, rtol=1e-12, atol=1e-15):
            raise ValueError("SampledResponse theta grids must match.")
        return type(self).from_tf(self.theta, self.tf * other.tf, self.fb)

    def cascade_ir(self, other: 'SampledResponse', *, per_ui: int) -> 'SampledResponse':
        """Cascade finite sampled-time responses by full linear convolution.

        The stored ``ir`` arrays are normally zero-padded for their own FFT
        grids.  Trailing zero padding is removed before convolution, then a
        new sampled-domain grid is created for the complete linear result.
        No continuous-time ``dt`` factor is applied to this discrete-time
        cascade.
        """
        if not np.isclose(self.fb, other.fb):
            raise ValueError("SampledResponse fb values must match.")

        def _finite_support(ir: np.ndarray) -> np.ndarray:
            ir = np.asarray(ir, dtype=float)
            nonzero = np.flatnonzero(ir != 0.0)
            return ir[: int(nonzero[-1]) + 1] if len(nonzero) else ir[:1]

        ir_total = np.convolve(_finite_support(self.ir), _finite_support(other.ir))
        if len(ir_total) % 2 != 0:
            ir_total = np.r_[ir_total, 0.0]

        per_ui = int(per_ui)
        if per_ui <= 0:
            raise ValueError("per_ui must be positive.")
        # SampledResponse does not retain per_ui, so the caller supplies it
        # to construct the corresponding LinkConfig sampled grid.
        cfg_nfft = max(2, len(ir_total))
        return type(self).from_ir(
            ir_total,
            LinkConfig.from_Nfft(self.fb, per_ui, cfg_nfft * per_ui),
        )

    def plot_tf(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        label: str | None = None,
    ) -> Axes:
        """
        Plot sampled transfer-function magnitude versus theta.

        Parameters
        ----------
        ax:
            Optional matplotlib Axes.
        save_path:
            Optional output path. If provided, save and close the figure.
        xlim:
            Optional theta limits in rad/sample.
        label:
            Optional curve label.
        """
        import matplotlib.pyplot as plt

        created_ax = ax is None
        if created_ax:
            _, ax = plt.subplots()

        theta = self.theta
        mag_db = 20 * np.log10(np.maximum(np.abs(self.tf), np.finfo(float).tiny))
        if xlim is not None:
            lo, hi = float(xlim[0]), float(xlim[1])
            if lo >= hi:
                raise ValueError("xlim must be strictly increasing.")
            mask = (theta >= lo) & (theta <= hi)
            if not np.any(mask):
                raise ValueError("xlim selects no response samples.")
            theta = theta[mask]
            mag_db = mag_db[mask]

        ax.plot(theta, mag_db, label=label)
        if label is not None:
            ax.legend()
        ax.set_xlabel("Frequency (rad/sample)")
        ax.set_ylabel("|H(e^jtheta)| (dB)")
        ax.set_title("Sampled Response TF")
        ax.grid(True)

        fig = ax.figure
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
            if created_ax:
                plt.close(fig)
        elif created_ax:
            fig.canvas.draw_idle()
            plt.show()

        return ax

    def plot_ir(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        xlim: Optional[tuple[int, int]] = None,
        label: str | None = None,
    ) -> Axes:
        """
        Plot sampled impulse response h[n].

        Parameters
        ----------
        ax:
            Optional matplotlib Axes.
        save_path:
            Optional output path. If provided, save and close the figure.
        xlim:
            Optional sample-index limits.
        label:
            Optional curve label.
        """
        import matplotlib.pyplot as plt

        if ax is None:
            _, ax = plt.subplots()

        n = np.arange(len(self.ir))
        ir = self.ir
        if xlim is not None:
            lo, hi = int(xlim[0]), int(xlim[1])
            if lo >= hi:
                raise ValueError("xlim must be strictly increasing.")
            mask = (n >= lo) & (n <= hi)
            if not np.any(mask):
                raise ValueError("xlim selects no impulse-response samples.")
            n = n[mask]
            ir = ir[mask]

        ax.plot(n, ir, label=label)
        if label is not None:
            ax.legend()
        ax.set_xlabel("Sample index")
        ax.set_ylabel("h[n]")
        ax.set_title("Sampled Response IR")
        ax.grid(True)

        fig = ax.figure
        fig.tight_layout()
        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
            plt.close(fig)
        else:
            fig.canvas.draw_idle()
            plt.show()

        return ax



class LinkSegment:
    """
    Scalar channel response container on a LinkConfig grid.

    Class boundary
    --------------
    LinkSegment owns scalar transfer-function / impulse-response /
    step-response / single-bit-response representations of one LTI segment.
    It also owns the conversion rules between those scalar representations,
    including continuous-domain FFT/IFFT scaling convention.

    It should not own two-port S-parameter storage, S4P-to-Sdd conversion,
    mixed-mode conversion, or IEEE COM package primitive construction. Those
    belong in SparamModel or a versioned COM module before a scalar response is
    selected.
    """
    DEFAULT_MAIN_CURSOR_UI = 20.0

    def __init__(self, cfg: 'LinkConfig'):
        self.cfg = cfg

        # transfer function: positive half side, with extension to cfg.f_nyq
        self._tf = None

        # time-domain response
        #   t-axis starts from 0, with step = dt = bt / per_ui
        #   raw_ir is the response before causality handling. causal_ir is the
        #   response after the LinkSegment causality contract.
        #   For TF-originated segments, raw_ir is the direct IFFT result and
        #   causal_ir may be circularly shifted. For IR/SR-originated segments,
        #   raw_ir and causal_ir are identical after passing causality checks.
        self._raw_ir = None
        self._causal_ir = None
        self._causal_shift_samples = None
        self._ir = None         # impulse response alias kept for compatibility
        self._sr = None         # step response
        self._sbr = None        # single-bit response

    @staticmethod
    def _force_real_rfft_edges(tf: np.ndarray) -> np.ndarray:
        """
        Force DC and Nyquist bins to be real for the LinkSegment rfft contract.

        LinkSegment stores one-sided transfer functions for real-valued time
        responses. With even cfg.Nfft, the DC and Nyquist bins are self-conjugate
        frequency points, so their imaginary parts are not valid degrees of
        freedom in the rfft/irfft representation.
        """
        tf = np.asarray(tf, dtype=complex).copy()
        tf[0] = tf[0].real + 0j
        tf[-1] = tf[-1].real + 0j
        return tf

    @staticmethod
    def _prepare_tf_dc(
        f_meas: np.ndarray,
        H_meas: np.ndarray,
        dc: Literal["error", "hold"],
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Prepare transfer-function samples for the LinkSegment DC contract.

        Parameters
        ----------
        f_meas:
            Frequency axis in Hz.
        H_meas:
            Scalar transfer function samples on f_meas.
        dc:
            Missing-DC policy. "error" raises if f_meas does not include DC.
            "hold" prepends H(0)=H(f_min).
        """
        f = LinkConfig.validate_freqs(f_meas)
        H = np.asarray(H_meas, dtype=complex)
        if H.shape != f.shape:
            raise ValueError("H_meas and f_meas must have the same shape.")

        if np.isclose(f[0], 0.0):
            return f, H

        if dc == "error":
            raise ValueError('f_meas must include DC. Use dc="hold" to prepend H(0)=H(f_min).')
        if dc == "hold":
            return np.r_[0.0, f], np.r_[H[0], H]

        raise ValueError('dc must be "error" or "hold".')

    # ----- constructors -----
    @classmethod
    def from_tf(
        cls,
        f_meas: np.ndarray,
        H_meas: np.ndarray,
        cfg: 'LinkConfig',
        dc: Literal["error", "hold"] = "error",
    ) -> 'LinkSegment':
        """
        Build a LinkSegment from scalar transfer-function samples.

        Parameters
        ----------
        f_meas:
            Frequency axis in Hz for H_meas.
        H_meas:
            Scalar transfer function samples on f_meas. If f_meas is not equal
            to cfg.freqs, H_meas is resampled / extended onto cfg.freqs using
            the module transfer-function resampling convention.
        cfg:
            LinkConfig defining the target FFT frequency and time grids.
        dc:
            Missing-DC policy. "error" keeps the strict LinkSegment contract.
            "hold" prepends H(0)=H(f_min) before resampling.
        """
        f_meas, H_meas = cls._prepare_tf_dc(f_meas, H_meas, dc)

        if not(isFreqsEqual(f_meas, cfg.freqs)):
            H_meas = resample_tf(H_meas, f_meas, cfg.freqs)

        seg = cls(cfg)
        H_meas = seg._force_real_rfft_edges(H_meas)
        seg._tf = seg.validate_tf(H_meas)
        return seg

    @classmethod
    def from_sr(cls, sr: np.ndarray, cfg: 'LinkConfig') -> 'LinkSegment':
        """
        Build a LinkSegment from scalar step-response samples.

        Parameters
        ----------
        sr:
            Step response sampled on cfg.times.
        cfg:
            LinkConfig defining the response time grid and conversion rules.

        Contract:
            raw_ir is computed from sr before causality checking. If the check
            passes, causal_ir is assigned to the same response. No automatic
            circular shift is applied to SR-originated data.
        """
        seg = cls(cfg)
        seg._sr = seg.validate_time_response(sr, "sr")
        seg._raw_ir = seg.sr2ir(seg._sr)
        seg._causal_ir = seg.validate_ir_from_time_domain(seg._raw_ir, source_name="sr")
        seg._causal_shift_samples = 0
        seg._ir = seg._causal_ir
        return seg

    @classmethod
    def from_ir(cls, ir: np.ndarray, cfg: 'LinkConfig') -> 'LinkSegment':
        """
        Build a LinkSegment from scalar impulse-response samples.

        Parameters
        ----------
        ir:
            Impulse response sampled on cfg.times.
        cfg:
            LinkConfig defining the response time grid and conversion rules.

        Contract:
            raw_ir is the input impulse response before causality checking. If
            the check passes, causal_ir is assigned to the same response. No
            automatic circular shift is applied to IR-originated data.
        """
        seg = cls(cfg)
        seg._raw_ir = seg.validate_ir(ir, correct_wrap=False)
        seg._causal_ir = seg.validate_ir_from_time_domain(seg._raw_ir, source_name="ir")
        seg._causal_shift_samples = 0
        seg._ir = seg._causal_ir
        return seg

    # ----- proxy & lazy evaluation -----
    @property
    def freqs(self) -> np.ndarray:
        """
        Frequency grid proxy in Hz.

        This is the LinkSegment scalar response grid and is owned by cfg. It is
        exposed here so downstream code can use segment.freqs without reaching
        into segment.cfg.
        """
        return self.cfg.freqs

    @property
    def times(self) -> np.ndarray:
        """
        Time grid proxy in seconds.

        This is the LinkSegment scalar response grid and is owned by cfg. It is
        exposed here so downstream code can use segment.times without reaching
        into segment.cfg.
        """
        return self.cfg.times

    @property
    def tf(self) -> np.ndarray:
        if (self._tf is None):
            assert self._raw_ir is not None or self._sr is not None
            self._tf = self.ir2tf()
        return self._tf

    @property
    def sr(self) -> np.ndarray:
        if (self._sr is None):
            if (self._tf is not None):
                self._sr = self.tf2sr(self._tf)
            else:
                self._sr = self.ir2sr(self.ir)
        return self._sr

    @property
    def ir(self) -> np.ndarray:
        if (self._causal_ir is None):
            if (self._tf is not None):
                self._raw_ir, self._causal_ir = self.tf2ir(self._tf)
            elif (self._sr is not None):
                self._raw_ir = self.sr2ir(self._sr)
                self._causal_ir = self.validate_ir_from_time_domain(self._raw_ir, source_name="sr")
                self._causal_shift_samples = 0
            else:
                raise Exception("Error @ calling LinkSegment.ir ...")
        self._ir = self._causal_ir
        return self._causal_ir

    @property
    def raw_ir(self) -> np.ndarray:
        """
        Impulse response before LinkSegment causality/alignment handling.

        For TF-originated segments this is the direct continuous-scaled IFFT
        result. For IR/SR-originated segments this is the input-domain impulse
        response before the causality check; after a passing check it is
            identical to causal_ir.
        """
        if (self._raw_ir is None):
            if (self._tf is not None):
                self._raw_ir, self._causal_ir = self.tf2ir(self._tf)
            elif (self._sr is not None):
                self._raw_ir = self.sr2ir(self._sr)
                self._causal_ir = self.validate_ir_from_time_domain(self._raw_ir, source_name="sr")
                self._causal_shift_samples = 0
            else:
                raise Exception("Error @ calling LinkSegment.raw_ir ...")
        return self._raw_ir

    @property
    def causal_ir(self) -> np.ndarray:
        """
        Causal analysis impulse response.

        For TF-originated segments this is raw_ir circularly shifted to minimize
        head/tail edge energy. For IR/SR
        originated segments this is the validated input-domain impulse response.
        """
        return self.ir

    @property
    def causal_shift_samples(self) -> int:
        """Circular shift from raw_ir to causal_ir, in samples."""
        _ = self.ir
        assert self._causal_shift_samples is not None
        return int(self._causal_shift_samples)

    @property
    def sbr(self) -> np.ndarray:
        if (self._sbr is None):
            self._sbr = self.sr2sbr(self.sr)
        return self._sbr

    # ============================
    # methods
    # ============================
    @staticmethod
    def _plt() -> Any:
        import matplotlib.pyplot as plt
        return plt

    def _finish_plot(self, ax: Axes, save_path: str, show: bool = True) -> Axes:
        """
        Apply LinkSegment's plot output convention.

        If save_path is provided, save the figure and close it. If save_path is
        not provided, refresh and show the figure. This makes chained calls such
        as ax = plot1(); plot2(ax=ax) visible in interactive environments.
        """
        plt = self._plt()
        fig = ax.figure
        fig.tight_layout()

        if save_path:
            fig.savefig(save_path, bbox_inches="tight")
            plt.close(fig)
        elif show:
            fig.canvas.draw_idle()
            plt.show()

        return ax

    def plot_tf(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
        auto_ylim: bool = True,
        x_scale: Literal["log", "linear"] = "log",
        label: str | None = None,
    ) -> Axes:
        """
        Plot absolute transfer-function magnitude in dB versus frequency.

        Parameters
        ----------
        ax:
            Optional matplotlib Axes. If provided, draw on this Axes and leave
            display / close behavior to the caller unless save_path is set.
        save_path:
            Optional output path. If provided, save the figure and close it.
        xlim:
            Optional frequency limits in Hz. If None, use the SerDes default
            in-band view from 0 to cfg.fb.
        ylim:
            Optional y-axis limits in dB.
        auto_ylim:
            If True and ylim is None, set y-limits from the plotted frequency
            range. The default in-band range is [0, fb].
        x_scale:
            Frequency-axis scale. ``"log"`` is the default SerDes view and
            displays from the first positive frequency bin to the selected
            upper limit; DC remains in ``tf`` but cannot be displayed on a
            logarithmic axis. Use ``"linear"`` to display DC at 0 Hz.
        label:
            Optional curve label. Useful when plotting multiple transfer
            functions on the same Axes.
        """
        created_ax = ax is None
        if created_ax:
            _, ax = self._plt().subplots()

        tf = self.validate_tf(self.tf)
        if x_scale not in {"log", "linear"}:
            raise ValueError("x_scale must be either 'log' or 'linear'.")

        if xlim is None:
            lo_hz = float(self.cfg.freqs[1]) if x_scale == "log" else 0.0
            hi_hz = self.cfg.fb
        else:
            if len(xlim) != 2:
                raise ValueError("xlim must contain two values: (start_hz, stop_hz).")
            lo_hz = float(xlim[0])
            hi_hz = float(xlim[1])
            if not np.isfinite(lo_hz) or not np.isfinite(hi_hz) or lo_hz >= hi_hz:
                raise ValueError("xlim must be finite and strictly increasing.")

        if x_scale == "log" and lo_hz <= 0.0:
            raise ValueError("Logarithmic frequency plots require xlim[0] > 0 Hz.")

        if lo_hz < self.cfg.freqs[0] or hi_hz > self.cfg.freqs[-1]:
            raise ValueError("xlim must stay within cfg.freqs.")

        mask = (self.cfg.freqs >= lo_hz) & (self.cfg.freqs <= hi_hz)
        if not np.any(mask):
            raise ValueError("xlim selects no frequency samples.")

        mag_db = 20 * np.log10(np.maximum(np.abs(tf), np.finfo(float).tiny))
        ax.plot(self.cfg.freqs[mask] / 1e9, mag_db[mask], label=label)
        if label is not None:
            ax.legend()
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("|H(f)| (dB)")
        ax.set_title("Transfer Function")
        ax.set_xscale(x_scale)
        ax.set_xlim(lo_hz / 1e9, hi_hz / 1e9)
        if ylim is not None:
            if len(ylim) != 2:
                raise ValueError("ylim must contain two values: (min_db, max_db).")
            lo_db = float(ylim[0])
            hi_db = float(ylim[1])
            if not np.isfinite(lo_db) or not np.isfinite(hi_db) or lo_db >= hi_db:
                raise ValueError("ylim must be finite and strictly increasing.")
            ax.set_ylim(lo_db, hi_db)
        elif auto_ylim:
            visible = mag_db[mask]
            visible = visible[np.isfinite(visible)]
            above_floor = visible[visible > -300.0]
            if above_floor.size > 0:
                visible = above_floor
            if visible.size > 0:
                y_min = float(np.min(visible))
                y_max = float(np.max(visible))
                if np.isclose(y_min, y_max):
                    pad = max(1.0, abs(y_min) * 0.05)
                else:
                    pad = (y_max - y_min) * 0.05
                ax.set_ylim(y_min - pad, y_max + pad)
        ax.grid(True)

        return self._finish_plot(ax, save_path, show=created_ax)

    def annotate_f(self, ax: Axes, f: Optional[Union[float, np.ndarray]] = None) -> Axes:
        """
        Annotate one or more frequencies on a transfer-function plot.

        Parameters
        ----------
        ax:
            Matplotlib Axes containing a plot_tf() result.
        f:
            Frequency or frequencies in Hz. If None, annotate cfg.f_nyq.

        The annotated gain is:
            20log10|H(f)| - 20log10|H(0)|
        """
        from matplotlib.axes import Axes as MplAxes

        if not isinstance(ax, MplAxes):
            raise TypeError("ax must be a matplotlib Axes.")

        if f is None:
            freqs_to_mark = np.array([self.cfg.f_nyq], dtype=float)
        else:
            freqs_to_mark = np.atleast_1d(np.asarray(f, dtype=float))

        if not np.all(np.isfinite(freqs_to_mark)):
            raise ValueError("f contains non-finite values.")

        if np.any((freqs_to_mark < self.cfg.freqs[0]) | (freqs_to_mark > self.cfg.freqs[-1])):
            raise ValueError("f must be within cfg.freqs.")

        tf = self.validate_tf(self.tf)
        mag_db = 20 * np.log10(np.maximum(np.abs(tf), np.finfo(float).tiny))
        gain_db = mag_db - mag_db[0]

        y_min, y_max = ax.get_ylim()
        for f_hz in freqs_to_mark:
            mag_at_f = float(np.interp(f_hz, self.cfg.freqs, mag_db))
            gain_at_f = float(np.interp(f_hz, self.cfg.freqs, gain_db))
            f_ghz = float(f_hz / 1e9)

            ax.axvline(f_ghz, linestyle="--", color="tab:red", linewidth=1.0)
            ax.plot(f_ghz, mag_at_f, marker="o", color="tab:red", markersize=4)
            ax.annotate(
                f"({f_ghz:.3f} GHz, {gain_at_f:.1f} dB)",
                xy=(f_ghz, mag_at_f),
                xytext=(6, 8),
                textcoords="offset points",
                color="tab:red",
                fontsize=9,
                bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "tab:red", "alpha": 0.85},
            )

        ax.set_ylim(y_min, y_max)
        return ax

    def frequency_at_gain(self, gain_db: float = -3.0) -> Optional[float]:
        """
        Return first frequency where |H(f)| drops to a relative gain target.

        Parameters
        ----------
        gain_db:
            Relative gain in dB with respect to H(0).
        """
        tf = self.validate_tf(self.tf)
        mag_db = 20 * np.log10(np.maximum(np.abs(tf), np.finfo(float).tiny))
        rel_db = mag_db - mag_db[0]
        target = float(gain_db)
        crossing = np.where(rel_db <= target)[0]
        if len(crossing) == 0:
            return None
        idx = int(crossing[0])
        if idx == 0:
            return float(self.cfg.freqs[0])
        x0, x1 = float(self.cfg.freqs[idx - 1]), float(self.cfg.freqs[idx])
        y0, y1 = float(rel_db[idx - 1]), float(rel_db[idx])
        if np.isclose(y0, y1):
            return x1
        return float(x0 + (target - y0) * (x1 - x0) / (y1 - y0))

    def _response_x_axis(
        self,
        response: np.ndarray,
        x_unit: Literal["ui", "ns"],
        x_origin: Literal["start", "max"],
        origin_response: Optional[np.ndarray] = None,
    ) -> tuple[np.ndarray, str]:
        """
        Build a time axis for scalar response plots.

        Parameters
        ----------
        response:
            Time-domain response sampled on cfg.times.
        x_unit:
            "ui" uses cfg.times_ui; "ns" uses cfg.times converted to ns.
        x_origin:
            "start" keeps cfg.times[0] as x=0; "max" shifts the largest
            abs(origin_response) sample to x=0.
        origin_response:
            Optional response used only to choose the x-origin. If None, use
            response itself.
        """
        response = self.validate_time_response(response, "response")
        origin_ref = response if origin_response is None else self.validate_time_response(origin_response, "origin_response")
        if x_unit == "ui":
            x = self.cfg.times_ui.copy()
            xlabel = "Time (UI)"
        elif x_unit == "ns":
            x = self.cfg.times * 1e9
            xlabel = "Time (ns)"
        else:
            raise ValueError('x_unit must be "ui" or "ns".')

        if x_origin == "start":
            return x, xlabel
        if x_origin == "max":
            origin_index = int(np.argmax(np.abs(origin_ref)))
            return x - x[origin_index], xlabel

        raise ValueError('x_origin must be "start" or "max".')

    def _set_response_xlim(
        self,
        ax: Axes,
        x_unit: Literal["ui", "ns"],
        x_origin: Literal["start", "max"],
        xlim_ui: Optional[tuple[float, float]],
    ) -> None:
        """
        Set a compact SerDes response window in UI or ns.

        Parameters
        ----------
        ax:
            Matplotlib Axes to update.
        x_unit:
            "ui" or "ns".
        x_origin:
            "start" or "max".
        xlim_ui:
            Optional x-limits in UI. If None, use a compact default window:
            (-5, 20) UI for max-centered plots and (0, 20) UI for start-based
            plots.
        """
        if xlim_ui is None:
            xlim_ui = (-5.0, 20.0) if x_origin == "max" else (0.0, 20.0)

        if len(xlim_ui) != 2:
            raise ValueError("xlim_ui must contain two values: (start_ui, stop_ui).")

        lo_ui = float(xlim_ui[0])
        hi_ui = float(xlim_ui[1])
        if not np.isfinite(lo_ui) or not np.isfinite(hi_ui) or lo_ui >= hi_ui:
            raise ValueError("xlim_ui must be finite and strictly increasing.")

        if x_unit == "ui":
            ax.set_xlim(lo_ui, hi_ui)
        elif x_unit == "ns":
            ax.set_xlim(lo_ui * self.cfg.bt * 1e9, hi_ui * self.cfg.bt * 1e9)
        else:
            raise ValueError('x_unit must be "ui" or "ns".')

    def _plot_time_response(
        self,
        response: np.ndarray,
        name: str,
        ylabel: str,
        title: str,
        ax: Optional[Axes],
        save_path: str,
        x_unit: Literal["ui", "ns"],
        x_origin: Literal["start", "max"],
        xlim_ui: Optional[tuple[float, float]],
        origin_response: Optional[np.ndarray] = None,
        label: str | None = None,
    ) -> Axes:
        response = self.validate_time_response(response, name)
        created_ax = ax is None
        if created_ax:
            _, ax = self._plt().subplots()

        x, xlabel = self._response_x_axis(response, x_unit, x_origin, origin_response=origin_response)
        ax.plot(x, response, label=label)
        if label is not None:
            ax.legend()
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        self._set_response_xlim(ax, x_unit, x_origin, xlim_ui)
        ax.grid(True)

        return self._finish_plot(ax, save_path, show=created_ax)

    def plot_ir(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        x_unit: Literal["ui", "ns"] = "ui",
        x_origin: Literal["start", "max"] = "max",
        xlim_ui: Optional[tuple[float, float]] = None,
        label: str | None = None,
    ) -> Axes:
        """
        Plot impulse response.

        Parameters
        ----------
        ax:
            Optional matplotlib Axes. If provided, draw on this Axes and leave
            display / close behavior to the caller unless save_path is set.
        save_path:
            Optional output path. If provided, save the figure and close it.
        x_unit:
            "ui" for UI axis or "ns" for nanosecond axis.
        x_origin:
            "start" keeps the original time zero; "max" shifts the largest
            abs(ir) sample to x=0.
        xlim_ui:
            Optional x-limits in UI after applying x_origin. If None, use the
            default compact window.
        label:
            Optional curve label. Useful when plotting multiple responses on
            the same Axes.
        """
        return self._plot_time_response(
            response=self.ir,
            name="ir",
            ylabel="h(t)",
            title="Impulse Response",
            ax=ax,
            save_path=save_path,
            x_unit=x_unit,
            x_origin=x_origin,
            xlim_ui=xlim_ui,
            label=label,
        )

    def plot_sr(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        x_unit: Literal["ui", "ns"] = "ui",
        x_origin: Literal["start", "max"] = "start",
        xlim_ui: Optional[tuple[float, float]] = None,
        label: str | None = None,
    ) -> Axes:
        """
        Plot step response.

        Parameters
        ----------
        ax:
            Optional matplotlib Axes. If provided, draw on this Axes and leave
            display / close behavior to the caller unless save_path is set.
        save_path:
            Optional output path. If provided, save the figure and close it.
        x_unit:
            "ui" for UI axis or "ns" for nanosecond axis.
        x_origin:
            "start" keeps the original time zero; "max" shifts the largest
            abs(ir) sample to x=0 so SR and IR plots use the same delay
            reference.
        xlim_ui:
            Optional x-limits in UI after applying x_origin. If None, use the
            default compact window.
        label:
            Optional curve label. Useful when plotting multiple responses on
            the same Axes.
        """
        return self._plot_time_response(
            response=self.sr,
            name="sr",
            ylabel="Step response",
            title="Step Response",
            ax=ax,
            save_path=save_path,
            x_unit=x_unit,
            x_origin=x_origin,
            xlim_ui=xlim_ui,
            origin_response=self.ir,
            label=label,
        )

    def plot_sbr(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        x_unit: Literal["ui", "ns"] = "ui",
        x_origin: Literal["start", "max"] = "max",
        xlim_ui: Optional[tuple[float, float]] = None,
        label: str | None = None,
        normalize_main_cursor: bool = False,
    ) -> Axes:
        """
        Plot single-bit response.

        Parameters
        ----------
        ax:
            Optional matplotlib Axes. If provided, draw on this Axes and leave
            display / close behavior to the caller unless save_path is set.
        save_path:
            Optional output path. If provided, save the figure and close it.
        x_unit:
            "ui" for UI axis or "ns" for nanosecond axis.
        x_origin:
            "start" keeps the original time zero; "max" shifts the largest
            abs(sbr) sample to x=0.
        xlim_ui:
            Optional x-limits in UI after applying x_origin. If None, use the
            default compact window.
        label:
            Optional curve label. Useful when plotting multiple responses on
            the same Axes.
        normalize_main_cursor:
            If True, plot sbr divided by its main cursor magnitude so cursor
            ratios can be inspected directly.
        """
        response = self.sbr
        ylabel = "Single-bit response"
        if normalize_main_cursor:
            main = float(np.max(np.abs(response)))
            if not np.isfinite(main) or np.isclose(main, 0.0):
                raise ValueError("Cannot normalize SBR because the main cursor is zero or non-finite.")
            response = response / main
            ylabel = "Single-bit response / main cursor"

        return self._plot_time_response(
            response=response,
            name="sbr",
            ylabel=ylabel,
            title="Single-Bit Response",
            ax=ax,
            save_path=save_path,
            x_unit=x_unit,
            x_origin=x_origin,
            xlim_ui=xlim_ui,
            label=label,
        )

    def cascade_tf(self, other: 'LinkSegment') -> 'LinkSegment':
        """
        Cascade two scalar transfer-function LinkSegment objects in frequency domain.

        This is an LTI transfer-function cascade:
            H_total(f) = H_self(f) * H_other(f)

        It is not a two-port S-parameter cascade. S-parameter package/channel
        cascade must be handled before constructing a scalar LinkSegment tf.
        """
        self.validate_compatible_segment(other)

        seg = LinkSegment(self.cfg)
        seg._tf = self.validate_tf(self.tf * other.tf)
        return seg

    def cascade_ir(self, other: 'LinkSegment') -> 'LinkSegment':
        """
        Cascade two scalar impulse responses using full linear convolution.

        The continuous-time convolution integral is approximated by:
            h_total[n] = sum_k h1[k] * h2[n-k] * cfg.dt

        The full linear-convolution length is preserved. If the result length is
        odd, one trailing zero is appended so the returned LinkConfig keeps an
        even Nfft and therefore an explicit rfft Nyquist bin.
        """
        self.validate_compatible_segment(other)

        ir_total = np.convolve(self.ir, other.ir) * self.cfg.dt
        if len(ir_total) % 2 != 0:
            ir_total = np.r_[ir_total, 0.0]

        new_cfg = LinkConfig.from_Nfft(
            fb=self.cfg.fb,
            per_ui=self.cfg.per_ui,
            Nfft=len(ir_total),
        )
        return LinkSegment.from_ir(ir_total, new_cfg)

    def find_main_delay(self, energy_window_ui: float = 1.0) -> dict[str, float | int]:
        """
        Estimate the main delay from the impulse-response peak.

        The primary delay is reported from the largest |ir[n]| sample. An optional
        local energy centroid around that peak is also reported as a smoother delay
        estimate. This method only reports timing; it does not shift the response.

        Output parameters
        -----------------
        peak_index:
            Index of max(abs(ir)).
        peak_time / peak_time_ui:
            Time of the peak sample in seconds / UI.
        centroid_index:
            Energy-weighted average index inside the local window around the
            peak. This can be a fractional index.
        centroid_time / centroid_time_ui:
            Time of the local energy centroid in seconds / UI.
        energy_window_ui:
            Width of the local centroid window in UI.
        energy_ratio_in_window:
            Fraction of total impulse-response energy inside the centroid
            window.
        """
        ir = self.ir
        mag = np.abs(ir)
        energy = mag**2
        total_energy = float(np.sum(energy))

        if total_energy <= 0.0:
            raise ValueError("Cannot find main delay because impulse-response energy is zero.")

        peak_index = int(np.argmax(mag))
        peak_time = float(self.cfg.times[peak_index])
        peak_time_ui = float(self.cfg.times_ui[peak_index])
        peak_amplitude = float(mag[peak_index])

        half_window = max(1, int(round(energy_window_ui * self.cfg.per_ui / 2)))
        lo = max(0, peak_index - half_window)
        hi = min(len(ir), peak_index + half_window + 1)

        local_energy = energy[lo:hi]
        local_energy_sum = float(np.sum(local_energy))

        if local_energy_sum > 0.0:
            local_indices = np.arange(lo, hi)
            centroid_index = float(np.sum(local_indices * local_energy) / local_energy_sum)
            centroid_time = centroid_index * self.cfg.dt
            centroid_time_ui = centroid_time / self.cfg.bt
        else:
            centroid_index = float(peak_index)
            centroid_time = peak_time
            centroid_time_ui = peak_time_ui

        return {
            "peak_index": peak_index,
            "peak_time": peak_time,
            "peak_time_ui": peak_time_ui,
            "peak_amplitude": peak_amplitude,
            "centroid_index": centroid_index,
            "centroid_time": float(centroid_time),
            "centroid_time_ui": float(centroid_time_ui),
            "energy_window_start_index": int(lo),
            "energy_window_stop_index": int(hi),
            "energy_window_ui": float(energy_window_ui),
            "energy_ratio_in_window": float(local_energy_sum / total_energy),
        }

    def estimate_phase_delay(
        self,
        f_min: float | None = None,
        f_max: float | None = None,
        mag_floor_ratio: float = 1e-4,
    ) -> dict[str, Union[float, int]]:
        """
        Estimate bulk delay from the unwrapped TF phase slope.

        For a pure delay H(f)=A(f)exp(-j2*pi*f*tau), the unwrapped phase slope is:
            dphi/df = -2*pi*tau
        This method fits phase versus frequency over a usable band and reports:
            tau = -slope / (2*pi)

        The result is a bulk/group-delay estimate used to judge whether cfg.T_max
        is long enough to avoid DFT wrap-around. It does not modify the response.
        """
        tf = self.validate_tf(self.tf)
        freqs = self.cfg.freqs
        mag = np.abs(tf)
        phase = np.unwrap(np.angle(tf))

        if f_min is None:
            f_min = self.cfg.df
        if f_max is None:
            f_max = min(self.cfg.f_nyq, self.cfg.fb)

        mag_threshold = float(np.max(mag) * mag_floor_ratio)
        mask = (
            (freqs >= f_min) &
            (freqs <= f_max) &
            (mag >= mag_threshold) &
            np.isfinite(phase)
        )

        if np.count_nonzero(mask) < 2:
            raise ValueError("Not enough valid frequency points to estimate phase delay.")

        fit = np.polyfit(freqs[mask], phase[mask], 1)
        slope = float(fit[0])
        intercept = float(fit[1])
        tau = -slope / (2 * np.pi)

        phase_fit = slope * freqs[mask] + intercept
        residual = phase[mask] - phase_fit
        rms_phase_error = float(np.sqrt(np.mean(residual**2)))

        return {
            "delay": float(tau),
            "delay_ui": float(tau / self.cfg.bt),
            "fit_f_min": float(f_min),
            "fit_f_max": float(f_max),
            "fit_points": int(np.count_nonzero(mask)),
            "phase_slope_rad_per_hz": slope,
            "phase_intercept_rad": intercept,
            "rms_phase_error_rad": rms_phase_error,
            "mag_floor_ratio": float(mag_floor_ratio),
        }

    def debug_time_axis(self, head_ui: float = 1.0, tail_ui: float = 1.0) -> dict[str, Union[bool, float, int]]:
        """
        Report whether the configured time/frequency axes are internally consistent.

        This checks the cfg grid itself, estimates bulk delay from TF phase, and
        reports head/tail impulse-response energy ratios as warning indicators
        for wrap-around or insufficient time-window length. It does not
        automatically circular-shift the response.
        """
        ir = self.ir
        energy = np.abs(ir)**2
        total_energy = float(np.sum(energy))

        head_len = max(1, int(round(head_ui * self.cfg.per_ui)))
        tail_len = max(1, int(round(tail_ui * self.cfg.per_ui)))
        head_len = min(head_len, len(ir))
        tail_len = min(tail_len, len(ir))

        if total_energy > 0.0:
            head_energy_ratio = float(np.sum(energy[:head_len]) / total_energy)
            tail_energy_ratio = float(np.sum(energy[-tail_len:]) / total_energy)
        else:
            head_energy_ratio = 0.0
            tail_energy_ratio = 0.0

        main_delay = self.find_main_delay()
        phase_delay = self.estimate_phase_delay()

        expected_fs = 1.0 / self.cfg.dt
        expected_df = self.cfg.Fs / self.cfg.Nfft
        expected_t_max = self.cfg.Nfft * self.cfg.dt
        expected_l_ui = expected_t_max / self.cfg.bt
        remaining_time_after_phase_delay = self.cfg.T_max - phase_delay["delay"]

        return {
            "Nfft": int(self.cfg.Nfft),
            "Fs": float(self.cfg.Fs),
            "f_nyq": float(self.cfg.f_nyq),
            "df": float(self.cfg.df),
            "dt": float(self.cfg.dt),
            "T_max": float(self.cfg.T_max),
            "L_ui": float(expected_l_ui),
            "freq_axis_reaches_nyquist": bool(np.allclose(self.cfg.freqs[-1], self.cfg.f_nyq)),
            "fs_matches_dt": bool(np.allclose(self.cfg.Fs, expected_fs)),
            "df_matches_fft_grid": bool(np.allclose(self.cfg.df, expected_df)),
            "tmax_matches_fft_grid": bool(np.allclose(self.cfg.T_max, expected_t_max)),
            "head_ui": float(head_ui),
            "tail_ui": float(tail_ui),
            "head_energy_ratio": head_energy_ratio,
            "tail_energy_ratio": tail_energy_ratio,
            "phase_delay": float(phase_delay["delay"]),
            "phase_delay_ui": float(phase_delay["delay_ui"]),
            "phase_delay_fit_points": int(phase_delay["fit_points"]),
            "phase_delay_fit_f_min": float(phase_delay["fit_f_min"]),
            "phase_delay_fit_f_max": float(phase_delay["fit_f_max"]),
            "phase_delay_rms_phase_error_rad": float(phase_delay["rms_phase_error_rad"]),
            "remaining_time_after_phase_delay": float(remaining_time_after_phase_delay),
            "remaining_ui_after_phase_delay": float(remaining_time_after_phase_delay / self.cfg.bt),
            "phase_delay_within_time_window": bool(0.0 <= phase_delay["delay"] < self.cfg.T_max),
            "main_delay_peak_index": int(main_delay["peak_index"]),
            "main_delay_peak_time": float(main_delay["peak_time"]),
            "main_delay_peak_time_ui": float(main_delay["peak_time_ui"]),
            "main_delay_centroid_time": float(main_delay["centroid_time"]),
            "main_delay_centroid_time_ui": float(main_delay["centroid_time_ui"]),
        }

    def debug_round_trip(
        self,
        pair: str,
        x: np.ndarray | None = None,
        rtol: float = 1e-10,
        atol: float = 1e-12,
        raise_on_fail: bool = True,
    ) -> dict[str, Union[str, bool, float]]:
        """
        Check whether a conversion pair can round-trip within numerical tolerance.

        This debug check compares only the round-trip result:
            source -> target -> recovered_source
        It does not compare against an external expected target response. If x is
        provided, x replaces the instance-owned source response for this check.

        The pass/fail logic uses a global max-error criterion:
            abs_err = max(abs(recovered_source - source))
            source_scale = max(max(abs(source)), atol)
            rel_err = abs_err / source_scale
            tolerance = max(atol, rtol * source_scale)
            passed = abs_err <= tolerance
        This is intentional because continuous-scaled impulse responses can have
        large absolute values even when the relative numerical error is tiny.

        Supported pairs:
        - "tf2ir" and "ir2tf"
          Reversible when tf is on cfg.freqs, has real DC/Nyquist bins, and the
          inverse path uses the same cfg.Nfft/cfg.Fs scaling convention. This
          debug pair uses raw_ir, not causal_ir, because causal_ir includes a
          circular time-reference shift.
        - "tf2sr" and "sr2tf"
          Reversible only through the raw response path. The instance-owned
          sr property is an aligned analysis response and is not the object used
          for this round-trip check.
        - "ir2sr" and "sr2ir"
          Reversible for finite cfg.times-length arrays when sr2ir() uses the
          same left boundary condition sr[-1 before t=0] = 0.
        - "sr2sbr" and "sbr2sr"
          Reversible for finite cfg.times-length arrays when both directions use
          D = cfg.per_ui samples as exactly one UI and assume sr[n<0] = 0.

        If x is None, the source representation is taken from this instance.
        """
        pair_map = {
            "tf2ir": ("tf", "raw_ir", self.validate_tf, lambda v: self.tf2ir(v)[0], self.ir2tf),
            "ir2tf": ("ir", "tf", lambda v: self.validate_ir(v, correct_wrap=False), self.ir2tf, lambda v: self.tf2ir(v)[0]),
            "tf2sr": ("tf", "sr", self.validate_tf, lambda v: self.ir2sr(self.tf2ir(v)[0]), self.sr2tf),
            "sr2tf": ("sr", "tf", lambda v: self.validate_time_response(v, "sr"), self.sr2tf, lambda v: self.ir2sr(self.tf2ir(v)[0])),
            "ir2sr": ("ir", "sr", lambda v: self.validate_ir(v, correct_wrap=False), self.ir2sr, self.sr2ir),
            "sr2ir": ("sr", "ir", lambda v: self.validate_time_response(v, "sr"), self.sr2ir, self.ir2sr),
            "sr2sbr": ("sr", "sbr", lambda v: self.validate_time_response(v, "sr"), self.sr2sbr, self.sbr2sr),
            "sbr2sr": ("sbr", "sr", lambda v: self.validate_time_response(v, "sbr"), self.sbr2sr, self.sr2sbr),
        }

        if pair not in pair_map:
            supported = ", ".join(pair_map)
            raise ValueError(f"Unsupported round-trip pair: {pair}. Supported pairs: {supported}")

        source_name, target_name, validate_source, forward, backward = pair_map[pair]

        if x is None:
            x = getattr(self, source_name)

        source = validate_source(x)
        target = forward(source)
        recovered = backward(target)

        abs_err = float(np.max(np.abs(recovered - source)))
        source_scale = max(float(np.max(np.abs(source))), atol)
        rel_err = abs_err / source_scale
        tolerance = max(atol, rtol * source_scale)
        passed = bool(abs_err <= tolerance)

        if raise_on_fail and not passed:
            raise AssertionError(
                f"{pair} round-trip failed: "
                f"{source_name}->{target_name}->{source_name}, "
                f"abs_err={abs_err:.3e}, rel_err={rel_err:.3e}, tolerance={tolerance:.3e}"
            )

        return {
            "pair": pair,
            "source": source_name,
            "target": target_name,
            "passed": passed,
            "roundtrip_abs_err": abs_err,
            "roundtrip_rel_err": rel_err,
            "roundtrip_tolerance": tolerance,
        }

    # ---------------------------
    # validation methods
    # ---------------------------
    def validate_tf(self, tf: np.ndarray) -> np.ndarray:
        tf = np.asarray(tf, dtype=complex)

        if tf.shape != self.cfg.freqs.shape:
            raise ValueError("tf must have the same shape as cfg.freqs.")

        if not np.all(np.isfinite(tf)):
            raise ValueError("tf contains non-finite values.")

        if not np.allclose(tf[0].imag, 0.0):
            raise ValueError("tf[0] must be real for a real-valued impulse response.")

        if not np.allclose(tf[-1].imag, 0.0):
            raise ValueError("tf[-1] must be real because cfg.Nfft is even and this is the Nyquist bin.")

        return tf

    def validate_time_response(self, x: np.ndarray, name: str) -> np.ndarray:
        x = np.asarray(x, dtype=float)

        if x.shape != self.cfg.times.shape:
            raise ValueError(f"{name} must have the same shape as cfg.times.")

        if not np.all(np.isfinite(x)):
            raise ValueError(f"{name} contains non-finite values.")

        return x

    def validate_ir(
        self,
        ir: np.ndarray,
        correct_wrap: bool = False,
        wrap_peak_after_fraction: float = 0.75,
    ) -> np.ndarray:
        """
        Validate an impulse response and optionally correct circular wrap-around.

        Parameters
        ----------
        ir:
            Impulse response sampled on cfg.times.
        correct_wrap:
            If True, treat a dominant peak after wrap_peak_after_fraction*Nfft
            as a circularly wrapped response and roll that peak to t=0.
        wrap_peak_after_fraction:
            Fraction of the time window after which a peak is considered wrapped.

        This correction is intentionally opt-in. It is used by tf2ir(), where
        IFFT periodicity can place a wrapped response near the end of the time
        window. Constructors and IR-domain cascade keep the natural time
        reference by default.
        """
        ir = self.validate_time_response(ir, "ir")

        if not correct_wrap:
            return ir

        if not 0.0 < wrap_peak_after_fraction < 1.0:
            raise ValueError("wrap_peak_after_fraction must be between 0 and 1.")

        peak_index = int(np.argmax(np.abs(ir)))
        wrap_threshold = int(round(wrap_peak_after_fraction * len(ir)))
        if peak_index >= wrap_threshold:
            return np.roll(ir, -peak_index)

        return ir

    def validate_ir_from_time_domain(
        self,
        ir: np.ndarray,
        source_name: str = "ir",
        tail_ui: float = 1.0,
        tail_energy_tol: float = 1e-6,
        wrap_peak_after_fraction: float = 0.75,
    ) -> np.ndarray:
        """
        Validate an IR supplied directly in time domain.

        Parameters
        ----------
        ir:
            Impulse response sampled on cfg.times.
        source_name:
            Name used in error messages, typically "ir" or "sr".
        tail_ui:
            Tail window used to detect circular wrap-around.
        tail_energy_tol:
            Maximum allowed energy ratio in the tail window.
        wrap_peak_after_fraction:
            If the largest |ir| sample occurs after this fraction of the record,
            the response is treated as wrapped.

        Contract:
        from_ir() and from_sr() inputs must already be causal in cfg.times. If
        the response appears wrapped, LinkSegment raises instead of silently
        shifting it.
        """
        ir = self.validate_ir(ir, correct_wrap=False)

        if not 0.0 < wrap_peak_after_fraction < 1.0:
            raise ValueError("wrap_peak_after_fraction must be between 0 and 1.")
        if tail_ui <= 0.0:
            raise ValueError("tail_ui must be positive.")
        if tail_energy_tol < 0.0:
            raise ValueError("tail_energy_tol must be non-negative.")

        mag = np.abs(ir)
        energy = mag**2
        total_energy = float(np.sum(energy))
        if total_energy <= 0.0:
            raise ValueError(f"{source_name} impulse-response energy is zero.")

        peak_index = int(np.argmax(mag))
        wrap_threshold = int(round(wrap_peak_after_fraction * len(ir)))
        if peak_index >= wrap_threshold:
            raise ValueError(
                f"{source_name} appears circularly wrapped: main peak index "
                f"{peak_index} is after {wrap_peak_after_fraction:.2f} of the record."
            )

        tail_len = max(1, int(round(tail_ui * self.cfg.per_ui)))
        tail_len = min(tail_len, len(ir))
        tail_energy_ratio = float(np.sum(energy[-tail_len:]) / total_energy)
        if tail_energy_ratio > tail_energy_tol:
            raise ValueError(
                f"{source_name} appears to contain wrapped or truncated tail energy: "
                f"tail_energy_ratio={tail_energy_ratio:.3e} exceeds {tail_energy_tol:.3e}."
            )

        return ir

    def validate_causal_ir(
        self,
        ir: np.ndarray,
        source_name: str = "causal_ir",
        tail_ui: float = 1.0,
        tail_energy_tol: float = 1e-6,
    ) -> np.ndarray:
        """
        Validate a TF-originated causal impulse response.

        Parameters
        ----------
        ir:
            Causal impulse response sampled on cfg.times.
        source_name:
            Name used in error messages.
        tail_ui:
            Tail window, in UI, used to detect circularly wrapped energy after
            causality handling.
        tail_energy_tol:
            Maximum allowed energy ratio in the final tail_ui window.

        Contract:
        TF-originated responses may be circularly shifted for causal analysis.
        The record tail should not contain significant wrapped energy. If it
        does, the LinkConfig time window is not safe for ISI/PMF calculation.
        """
        ir = self.validate_ir(ir, correct_wrap=False)
        if tail_ui <= 0.0:
            raise ValueError("tail_ui must be positive.")
        if tail_energy_tol < 0.0:
            raise ValueError("tail_energy_tol must be non-negative.")

        energy = np.abs(ir) ** 2
        total_energy = float(np.sum(energy))
        if total_energy <= 0.0:
            raise ValueError(f"{source_name} impulse-response energy is zero.")

        tail_len = max(1, int(round(tail_ui * self.cfg.per_ui)))
        tail_len = min(tail_len, len(ir))
        tail_energy_ratio = float(np.sum(energy[-tail_len:]) / total_energy)
        if tail_energy_ratio > tail_energy_tol:
            raise ValueError(
                f"{source_name} contains significant tail energy after causality handling: "
                f"tail_energy_ratio={tail_energy_ratio:.3e} exceeds {tail_energy_tol:.3e}. "
                "This usually means precursor/main-lobe energy wrapped to the end "
                "of the IFFT record; increase LinkConfig time span or inspect the response delay."
            )

        return ir

    def causalize_ir(
        self,
        ir: np.ndarray,
        edge_fraction: float = 0.05,
    ) -> tuple[np.ndarray, int]:
        """
        Circularly shift an IFFT impulse response to minimize edge energy.

        Parameters
        ----------
        ir:
            Direct IFFT impulse response sampled on cfg.times.
        edge_fraction:
            Fraction of the record used at both edges for the causality score.

        The score is E_front + E_tail, where each term is the squared-magnitude
        energy in edge_fraction of the record. The first minimum returned by
        np.argmin is used as a deterministic tie break. This changes the time
        reference; raw_ir remains the only TF round-trip representation.
        """
        ir = self.validate_ir(ir, correct_wrap=False)
        if not 0.0 < edge_fraction < 0.5:
            raise ValueError("edge_fraction must be between 0 and 0.5.")

        edge_len = max(1, int(np.ceil(edge_fraction * len(ir))))
        energy = np.abs(ir) ** 2
        total_energy = float(np.sum(energy))
        if total_energy <= 0.0:
            raise ValueError("ir impulse-response energy is zero.")

        # Circular length-edge_len window energies for every original start index.
        # This evaluates all circular shifts in O(N), not O(N**2).
        extended_energy = np.concatenate([energy, energy[:edge_len - 1]])
        cumulative_energy = np.concatenate([[0.0], np.cumsum(extended_energy)])
        window_energy = cumulative_energy[edge_len:edge_len + len(ir)] - cumulative_energy[:len(ir)]
        shift_index = np.arange(len(ir), dtype=int)
        front_start = (-shift_index) % len(ir)
        tail_start = (front_start - edge_len) % len(ir)
        edge_score = window_energy[front_start] + window_energy[tail_start]
        shift = int(np.argmin(edge_score))
        return np.roll(ir, shift), shift

    def validate_compatible_segment(self, other: 'LinkSegment') -> None:
        if not isinstance(other, LinkSegment):
            raise TypeError("other must be a LinkSegment.")

        if self.cfg.Nfft != other.cfg.Nfft:
            raise ValueError("Cannot cascade LinkSegment objects with different Nfft.")

        if not np.allclose(self.cfg.freqs, other.cfg.freqs):
            raise ValueError("Cannot cascade LinkSegment objects with different frequency grids.")

        if not np.allclose(self.cfg.times, other.cfg.times):
            raise ValueError("Cannot cascade LinkSegment objects with different time grids.")

    # ---------------------------
    # response transformation
    # ---------------------------
    # tf -> ir -> sr
    def tf2ir(
        self,
        tf: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Convert TF to both raw and causal impulse responses.

        Parameters
        ----------
        tf:
            One-sided transfer function sampled on cfg.freqs.
        Returns
        -------
        raw_ir:
            Direct continuous-scaled IFFT result before causality/alignment
            handling. Use this for tf <-> ir round-trip validation.
        causal_ir:
            Circularly shifted analysis view with minimum 5% head/tail energy.
        """
        tf = self.validate_tf(tf)
        raw_ir = np.fft.irfft(tf, n=self.cfg.Nfft) * self.cfg.Fs
        raw_ir = self.validate_ir(raw_ir, correct_wrap=False)
        causal_ir, shift = self.causalize_ir(raw_ir)
        self._causal_shift_samples = shift
        return raw_ir, causal_ir

    def to_sampled_response(
        self,
        pos: int = 0,
        source: Literal["raw", "causal"] = "causal",
    ) -> SampledResponse:
        """
        Convert this continuous-time response to a symbol-rate SampledResponse.

        Parameters
        ----------
        pos:
            Sampling phase in continuous-time samples. Must satisfy
            ``0 <= pos < cfg.per_ui``. The corresponding time-domain sequence
            is ``source_ir[pos::cfg.per_ui]``.
        source:
            ``"raw"`` uses ``raw_ir`` as the continuous-time time reference.
            ``"causal"`` uses ``causal_ir`` and is therefore aligned with the
            response used by COM time-domain analysis.

        Returns
        -------
        SampledResponse
            Symbol-rate response on ``cfg.theta``. Its impulse response is
            numerically equivalent to sampling the selected continuous-time
            impulse response at ``pos`` and every ``cfg.per_ui`` samples.

        Notes
        -----
        This implements the finite-DFT form of continuous-time to sampled-time
        conversion. Let ``M = cfg.per_ui``, ``N = cfg.Nfft``, and
        ``N_d = N / M``. For sampled bin ``r``:

        ``H_d[r] = fb * sum_l H_c[r + l*N_d]
                           * exp(j*2*pi*(r + l*N_d)*pos/N)``.

        The sum contains every alias branch of the finite continuous-time
        grid. The factor ``fb`` follows LinkSegment's continuous scaling
        convention, where ``ir = irfft(tf) * Fs``. This method deliberately
        reconstructs the full two-sided DFT spectrum so that negative-frequency
        aliases are included exactly.
        """
        if source not in ("raw", "causal"):
            raise ValueError('source must be "raw" or "causal".')

        M = int(self.cfg.per_ui)
        N = int(self.cfg.Nfft)
        pos = int(pos)
        if not 0 <= pos < M:
            raise ValueError("pos must satisfy 0 <= pos < cfg.per_ui.")
        if N % M != 0:
            raise ValueError(
                "CT-to-DT conversion requires cfg.Nfft to be divisible by "
                "cfg.per_ui so the two DFT grids share df."
            )

        N_d = N // M
        if N_d != self.cfg.sampled_nfft or N_d % 2 != 0:
            raise ValueError(
                "LinkConfig sampled-domain grid is not exactly compatible "
                "with the continuous-time DFT grid."
            )

        source_ir = self.raw_ir if source == "raw" else self.causal_ir
        H_one_sided = self.ir2tf(source_ir)
        H_full = np.empty(N, dtype=complex)
        H_full[: N // 2 + 1] = H_one_sided
        H_full[N // 2 + 1 :] = np.conj(H_one_sided[1:-1][::-1])

        sampled_bins = np.arange(N_d // 2 + 1, dtype=int)
        alias_indices = sampled_bins[:, None] + N_d * np.arange(M, dtype=int)
        phase = np.exp(2j * np.pi * alias_indices * pos / N)
        H_sampled = self.cfg.fb * np.sum(H_full[alias_indices] * phase, axis=1)
        H_sampled[0] = H_sampled[0].real + 0j
        H_sampled[-1] = H_sampled[-1].real + 0j

        return SampledResponse.from_tf(
            theta=self.cfg.theta,
            tf=H_sampled,
            fb=self.cfg.fb,
            nfft=N_d,
        )

    def ir2sr(self, ir: np.ndarray) -> np.ndarray:
        """
        Convert impulse response to step response using continuous-time integration.

        Round-trip boundary condition with sr2ir():
        - ir and sr are cfg.times-length arrays.
        - sr is defined with zero prehistory: sr[n<0] = 0.
        - The inverse uses the same cfg.dt.
        """
        ir = self.validate_ir(ir, correct_wrap=False)
        return np.cumsum(ir) * self.cfg.dt

    def tf2sr(self, tf: np.ndarray) -> np.ndarray:
        """
        Convert transfer function to step response through the continuous-scaled impulse response.

        Round-trip boundary condition with sr2tf():
        - Requires the tf2ir/ir2tf and ir2sr/sr2ir boundary conditions.
        - In particular, sr2tf() treats the sample before t=0 as zero.
        """
        return self.ir2sr(self.tf2ir(tf)[1])

    # sr -> ir -> tf
    def sr2ir(self, sr: np.ndarray) -> np.ndarray:
        """
        Convert step response to impulse response by finite difference.

        Boundary condition:
        - Prepends sr[-1 before t=0] = 0 via np.r_[0, sr].
        - This makes ir2sr(sr2ir(sr)) reversible only for step responses that use
          the same zero-prehistory convention.
        """
        sr = self.validate_time_response(sr, "sr")
        return np.diff(np.r_[0, sr]) / self.cfg.dt

    def ir2tf(self, ir: np.ndarray | None = None) -> np.ndarray:
        """
        Convert continuous-scaled impulse response samples back to one-sided TF samples.

        Round-trip boundary condition with tf2ir():
        - ir must be cfg.times-length and continuous-scaled.
        - If ir is None, use this instance's raw_ir, not causal_ir.
        - The forward FFT divides by cfg.Fs to undo tf2ir()'s continuous scaling.
        - The returned DC/Nyquist bins are forced real for rfft/irfft consistency.
        """
        if ir is None:
            ir = self.raw_ir
        ir = self.validate_ir(ir, correct_wrap=False)
        tf = np.fft.rfft(ir, n=self.cfg.Nfft) / self.cfg.Fs
        tf[0] = tf[0].real + 0j
        tf[-1] = tf[-1].real + 0j
        return tf
    
    def sr2tf(self, sr: np.ndarray) -> np.ndarray:
        """
        Convert step response to transfer function through sr2ir() and ir2tf().

        Boundary condition:
        - Uses sr2ir()'s zero-prehistory convention at t=0.
        """
        return self.ir2tf(self.sr2ir(sr))

    # sr <-> sbr
    def sr2sbr(self, sr: np.ndarray) -> np.ndarray:
        """
        Convert step response to single-bit response.

        Definition:
            sbr[n] = sr[n] - sr[n-D]
            D = cfg.per_ui samples = one UI
            sr[n-D] = 0 for n < D

        Time-axis convention:
        - sbr has the same shape as cfg.times.
        - sbr[n] is aligned to cfg.times[n]; no center crop or cursor alignment is
          applied here. Any main-cursor alignment should be a separate operation.

        Round-trip boundary condition with sbr2sr():
        - Both directions must use the same D = cfg.per_ui.
        - The step response prehistory before t=0 is assumed zero.
        """
        sr = self.validate_time_response(sr, "sr")
        delay = self.cfg.per_ui     # per_ui points in cfg.times = cfg.bt
        sbr = sr.copy()
        sbr[delay:] -= sr[:-delay]

        return sbr

    def sbr2sr(self, sbr: np.ndarray) -> np.ndarray:
        """ 
        Convert single-bit response back to step response.

        Inverse recurrence:
            sr[n] = sbr[n]              for n < D
            sr[n] = sbr[n] + sr[n-D]    for n >= D
            D = cfg.per_ui samples = one UI

        Round-trip boundary condition with sr2sbr():
        - sbr must be cfg.times-length.
        - Uses the same D = cfg.per_ui as sr2sbr().
        - Assumes sr[n<0] = 0; finite-window truncation is part of the convention.
        """
        sbr = self.validate_time_response(sbr, "sbr")
        D = self.cfg.per_ui
        sr = np.zeros_like(sbr)
        for n in range(len(sbr)):
            sr[n] = sbr[n]
            if n >= D:
                sr[n] += sr[n - D]

        return sr

