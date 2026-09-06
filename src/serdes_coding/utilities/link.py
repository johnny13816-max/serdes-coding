from __future__ import annotations

import numpy as np
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, cast
from dataclasses import dataclass, field
import skrf as rf

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
class ContinuousPSD:
    """
    Continuous-time one-sided power spectral density container.

    Class boundary
    --------------
    ContinuousPSD owns scalar one-sided PSD samples S_ct,1(f) on a
    non-negative continuous frequency axis. Internally the stored PSD is
    always one-sided and uses SI frequency units, so integrated power is
    approximated by integral S_ct,1(f) df.

    It does not own transfer-function FFT/IFFT conversion or S-parameter
    conversion. Filtering by an LTI response is represented by:
        S_out(f) = S_in(f) * |H(f)|^2

    The class can either preserve an arbitrary PSD grid or return a copy
    aligned to LinkConfig.freqs for 178A-style PSD arithmetic on a common
    frequency grid. The ifftable flag is True only when the PSD is known to be
    on a LinkConfig-compatible rfft grid.
    """
    freqs: np.ndarray                # unit: Hz, one-sided non-negative frequency axis
    psd: np.ndarray                  # unit: quantity^2/Hz, one-sided PSD samples
    ifftable: bool = False           # True when freqs are aligned to a LinkConfig rfft grid

    def __post_init__(self) -> None:
        self.freqs = LinkConfig.validate_freqs(self.freqs)
        self.psd = self.validate_psd(self.psd, self.freqs)
        self.ifftable = bool(self.ifftable or self.is_ifftable_freqs(self.freqs))

    @staticmethod
    def validate_psd(psd: np.ndarray, freqs: np.ndarray) -> np.ndarray:
        """
        Validate one-sided PSD samples.

        Parameters
        ----------
        psd:
            One-sided PSD samples in quantity^2/Hz.
        freqs:
            Frequency axis in Hz used only for shape checking.
        """
        psd = np.asarray(psd, dtype=float)
        if psd.shape != freqs.shape:
            raise ValueError("psd and freqs must have the same shape.")
        if psd.ndim != 1:
            raise ValueError("psd must be a 1D array.")
        if not np.all(np.isfinite(psd)):
            raise ValueError("psd contains non-finite values.")
        if np.any(psd < 0.0):
            raise ValueError("psd must be non-negative.")
        return psd

    @staticmethod
    def is_ifftable_freqs(freqs: np.ndarray) -> bool:
        """
        Check whether freqs are compatible with a one-sided rfft/irfft grid.

        This is a grid-shape check only. It confirms DC is present and the
        spacing is uniform; it does not prove the axis was produced by a
        specific LinkConfig instance.
        """
        try:
            LinkConfig.validate_freqs(freqs, require_uniform=True)
        except ValueError:
            return False
        freqs = np.asarray(freqs, dtype=float)
        return bool(len(freqs) >= 2 and np.isclose(freqs[0], 0.0))

    @classmethod
    def from_sigma(
        cls,
        freqs: np.ndarray,
        sigma: float,
        f_start: float = 0.0,
        f_stop: float = np.inf,
    ) -> 'ContinuousPSD':
        """
        Build a flat band-limited one-sided PSD from RMS amplitude.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        sigma:
            RMS amplitude in quantity units. The integrated PSD power is
            sigma**2 on this frequency grid.
        f_start:
            Start frequency of the flat PSD band in Hz.
        f_stop:
            Stop frequency of the flat PSD band in Hz. Values beyond freqs[-1]
            naturally do not contribute on this grid.
        """
        freqs = LinkConfig.validate_freqs(freqs)
        sigma = float(sigma)
        f_start = float(f_start)
        f_stop = float(f_stop)
        if not np.isfinite(sigma) or sigma < 0.0:
            raise ValueError("sigma must be finite and non-negative.")
        if not np.isfinite(f_start) or f_start < 0.0:
            raise ValueError("f_start must be finite and non-negative.")
        if not np.isfinite(f_stop) and not np.isinf(f_stop):
            raise ValueError("f_stop must be finite or np.inf.")
        if f_start >= f_stop:
            raise ValueError("f_start and f_stop must be strictly increasing.")

        shape = np.zeros_like(freqs)
        in_band = (freqs >= f_start) & (freqs <= f_stop)
        if not np.any(in_band):
            raise ValueError("The requested PSD band contains no frequency samples.")
        shape[in_band] = 1.0

        band_area = float(np.trapezoid(shape, freqs))
        if band_area <= 0.0:
            raise ValueError("The requested PSD band has zero integration area on this grid.")

        return cls(freqs=freqs, psd=(sigma**2 / band_area) * shape)

    @classmethod
    def from_constant(
        cls,
        freqs: np.ndarray,
        psd_value: float,
    ) -> 'ContinuousPSD':
        """
        Build a flat one-sided PSD from a constant PSD density.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        psd_value:
            Constant one-sided PSD density in quantity^2/Hz.
        """
        freqs = LinkConfig.validate_freqs(freqs)
        psd_value = float(psd_value)
        if not np.isfinite(psd_value) or psd_value < 0.0:
            raise ValueError("psd_value must be finite and non-negative.")
        return cls(freqs=freqs, psd=psd_value * np.ones_like(freqs, dtype=float))

    @classmethod
    def from_func(
        cls,
        freqs: np.ndarray,
        func: Any,
    ) -> 'ContinuousPSD':
        """
        Build a one-sided PSD from a scalar frequency-domain model.

        Parameters
        ----------
        freqs:
            Frequency axis in Hz.
        func:
            Callable that accepts freqs in Hz and returns PSD samples in
            quantity^2/Hz.
        """
        freqs = LinkConfig.validate_freqs(freqs)
        psd = np.asarray(func(freqs), dtype=float)
        return cls(freqs=freqs, psd=psd)

    @property
    def df(self) -> float | None:
        """
        Frequency spacing in Hz when the PSD grid is uniform; otherwise None.
        """
        steps = np.diff(self.freqs)
        if np.allclose(steps, steps[0], rtol=1e-12, atol=1e-15):
            return float(steps[0])
        return None

    def aligned_to(
        self,
        cfg: LinkConfig,
        *,
        dc: Literal["error", "hold"] = "error",
    ) -> 'ContinuousPSD':
        """
        Return a copy sampled on cfg.freqs.

        Parameters
        ----------
        cfg:
            LinkConfig whose cfg.freqs is the target one-sided frequency grid.
        dc:
            Missing-DC policy aligned with LinkSegment.from_tf(). "error"
            raises if cfg.freqs starts below the PSD low-frequency point.
            "hold" fills the low-frequency gap with the first PSD value.

        Notes
        -----
        This performs scalar interpolation/extrapolation on PSD values. It is
        suitable for noise PSD models. It should not be used to resample
        transfer functions with phase. High-frequency samples above the PSD
        stop frequency are set to zero.
        """
        f_new = cfg.freqs
        if f_new[0] < self.freqs[0] and dc == "error":
            raise ValueError("Target grid starts below PSD frequency span.")
        if dc not in ("error", "hold"):
            raise ValueError('dc must be "error" or "hold".')

        psd_new = np.interp(
            f_new,
            self.freqs,
            self.psd,
            left=self.psd[0] if dc == "hold" else 0.0,
            right=0.0,
        )

        return type(self)(freqs=f_new, psd=psd_new, ifftable=True)

    def filtered_by(self, response: 'LinkSegment') -> 'ContinuousPSD':
        """
        Return the PSD after filtering by a LinkSegment transfer function.

        Parameters
        ----------
        response:
            LinkSegment whose tf is defined on the same one-sided frequency
            grid as this PSD.
        """
        if not isFreqsEqual(self.freqs, response.freqs):
            raise ValueError("PSD and LinkSegment frequency grids must match. Use aligned_to(cfg, dc=...) first.")
        return type(self)(freqs=self.freqs, psd=self.psd * np.abs(response.tf)**2, ifftable=self.ifftable)

    def to_sampled(
        self,
        fb: float,
        theta: Optional[np.ndarray] = None,
        *,
        alias_kmax: Optional[int] = None,
        theta_points: Optional[int] = None,
    ) -> 'SampledPSD':
        """
        Convert this continuous-time one-sided PSD to a sampled-domain PSD.

        Parameters
        ----------
        fb:
            Sampling rate / baud rate in Hz.
        theta:
            Optional sampled-domain one-sided frequency axis in rad/sample.
            If omitted, a uniform one-sided sampled-domain axis from 0 to pi,
            including both endpoints, is generated.
        alias_kmax:
            Optional integer alias summation range. The method sums branches
            for k=-alias_kmax..alias_kmax. If omitted, the range is inferred
            from self.freqs[-1] and fb.
        theta_points:
            Optional number of points for the generated theta axis when
            theta is None. If omitted, use the number of CT samples inside
            [0, fb/2], with a minimum of two points.

        Notes
        -----
        Sampling always aliases continuous-time PSD. This method follows the
        IEEE 802.3 178A convention used by Equations 178A-17/18:
            theta = 2*pi*f/fb
            f0 = theta*fb/(2*pi)
            S_spec(theta) = sum_k S_ct,1(| f0 + k*fb |)

        The stored SampledPSD values remain PSD densities in quantity^2/Hz,
        indexed by theta. They are not converted to quantity^2/rad here. The
        only scale conversion is applied by SampledPSD.to_sigma() and
        SampledPSD.to_autocorrelation().

        ContinuousPSD itself stores one-sided CT PSD values. Therefore the
        direct one-sided alias sum already produces the SampledPSD one-sided
        equivalent. DC and Nyquist bins are halved for rfft-style endpoint
        accounting; interior bins are not doubled here.
        """
        fb = float(fb)
        if not np.isfinite(fb) or fb <= 0.0:
            raise ValueError("fb must be finite and positive.")

        if theta is None:
            in_band = self.freqs <= 0.5 * fb
            if theta_points is None:
                theta_points = max(2, int(np.count_nonzero(in_band)))
            else:
                theta_points = int(theta_points)
            if theta_points < 2:
                raise ValueError("theta_points must be at least 2.")
            theta = np.linspace(0.0, np.pi, theta_points)
        else:
            theta = SampledPSD.validate_theta(theta)

        if alias_kmax is None:
            alias_kmax = int(np.ceil(float(self.freqs[-1]) / fb)) + 1
        else:
            alias_kmax = int(alias_kmax)
        if alias_kmax < 0:
            raise ValueError("alias_kmax must be non-negative.")

        f0 = theta * fb / (2 * np.pi)

        def interp_ct_psd(f_abs: np.ndarray) -> np.ndarray:
            return np.interp(f_abs, self.freqs, self.psd, left=self.psd[0], right=0.0)

        folded = np.zeros_like(theta, dtype=float)
        for k in range(-alias_kmax, alias_kmax + 1):
            kfb = k * fb
            folded += interp_ct_psd(np.abs(f0 + kfb))

        psd_dt = folded
        if len(psd_dt) > 0 and np.isclose(theta[0], 0.0):
            psd_dt[0] *= 0.5
        if len(psd_dt) > 1 and np.isclose(theta[-1], np.pi):
            psd_dt[-1] *= 0.5

        return SampledPSD(theta=theta, psd=psd_dt, fb=fb)

    def to_sigma(self) -> float:
        """
        Integrate one-sided PSD over frequency and return RMS amplitude.

        Returns
        -------
        float
            RMS amplitude in quantity units.
        """
        power = float(np.trapezoid(self.psd, self.freqs))
        return float(np.sqrt(power))

    def plot(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        label: str | None = None,
    ) -> Axes:
        """
        Plot one-sided PSD versus frequency.

        Parameters
        ----------
        ax:
            Optional matplotlib Axes.
        save_path:
            Optional output path. If provided, save and close the figure.
        xlim:
            Optional frequency limits in Hz.
        label:
            Optional curve label.
        """
        import matplotlib.pyplot as plt

        created_ax = ax is None
        if created_ax:
            _, ax = plt.subplots()

        freqs = self.freqs
        psd = self.psd
        if xlim is not None:
            lo_hz, hi_hz = float(xlim[0]), float(xlim[1])
            if lo_hz >= hi_hz:
                raise ValueError("xlim must be strictly increasing.")
            mask = (freqs >= lo_hz) & (freqs <= hi_hz)
            if not np.any(mask):
                raise ValueError("xlim selects no PSD samples.")
            freqs = freqs[mask]
            psd = psd[mask]

        ax.plot(freqs / 1e9, psd, label=label)
        if label is not None:
            ax.legend()
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("One-sided PSD")
        ax.set_title("One-sided PSD")
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

@dataclass
class SampledPSD:
    """
    Sampled/discrete-time one-sided power spectral density container.

    Class boundary
    --------------
    SampledPSD owns scalar rfft-style one-sided PSD samples on the normalized
    sampled-domain frequency axis [0, pi].

    Important 178A convention
    -------------------------
    IEEE 802.3 178A writes sampled-domain PSDs as S(theta), but Equations
    178A-17/18/19/22/28 use PSD densities in quantity^2/Hz. This class follows
    that spec-compatible convention:
        - axis: theta in rad/sample
        - stored value unit: quantity^2/Hz, not quantity^2/rad

    The stored array is the one-sided equivalent of the spec's two-sided
    theta-indexed Hz-density PSD. Interior rfft bins are doubled; DC and
    Nyquist are not. Components can therefore be added directly only when they
    all follow this same contract.

    Scale conversion is centralized:
        - to_sigma(): power = df * sum(one-sided PSD), df = fb/Nfft
        - to_autocorrelation(): R[n] = fb * ifft(two-sided spec PSD)
    """
    theta: np.ndarray                # unit: rad/sample, one-sided axis [0, pi]
    psd: np.ndarray                  # unit: quantity^2/Hz, rfft one-sided equivalent PSD samples
    fb: float                        # unit: Hz, sampling rate / baud rate

    def __post_init__(self) -> None:
        self.theta = self.validate_theta(self.theta)
        self.psd = self.validate_psd(self.psd, self.theta)
        self.fb = float(self.fb)
        if not np.isfinite(self.fb) or self.fb <= 0.0:
            raise ValueError("fb must be finite and positive.")

    @staticmethod
    def validate_theta(theta: np.ndarray) -> np.ndarray:
        """
        Validate one-sided sampled-domain frequency samples.

        Parameters
        ----------
        theta:
            Frequency axis in rad/sample. Must be 1-D, finite, strictly
            increasing, and contained in [0, pi].
        """
        theta = np.asarray(theta, dtype=float)
        if theta.ndim != 1:
            raise ValueError("theta must be a 1D array.")
        if len(theta) < 2:
            raise ValueError("theta must contain at least two points.")
        if not np.all(np.isfinite(theta)):
            raise ValueError("theta contains non-finite values.")
        if not np.all(np.diff(theta) > 0):
            raise ValueError("theta must be strictly increasing.")
        if theta[0] < 0.0 or theta[-1] > np.pi:
            raise ValueError("theta must be within [0, pi].")
        return theta

    @staticmethod
    def validate_psd(psd: np.ndarray, theta: np.ndarray) -> np.ndarray:
        """
        Validate one-sided sampled PSD samples.

        Parameters
        ----------
        psd:
            One-sided PSD samples in quantity^2/Hz.
        theta:
            Sampled-domain frequency axis used only for shape checking.
        """
        psd = np.asarray(psd, dtype=float)
        if psd.shape != theta.shape:
            raise ValueError("psd and theta must have the same shape.")
        if psd.ndim != 1:
            raise ValueError("psd must be a 1D array.")
        if not np.all(np.isfinite(psd)):
            raise ValueError("psd contains non-finite values.")
        if np.any(psd < 0.0):
            raise ValueError("psd must be non-negative.")
        return psd

    @classmethod
    def from_constant(
        cls,
        theta: np.ndarray,
        psd_value: float,
        fb: float,
    ) -> 'SampledPSD':
        """
        Build a flat sampled PSD from a spec two-sided constant density.

        Parameters
        ----------
        theta:
            Sampled-domain frequency axis in rad/sample.
        psd_value:
            Constant spec-compatible two-sided PSD density in quantity^2/Hz.
            The returned object stores the rfft one-sided equivalent, so
            interior bins are doubled automatically.
        fb:
            Sampling rate / baud rate in Hz.
        """
        theta = cls.validate_theta(theta)
        psd_value = float(psd_value)
        if not np.isfinite(psd_value) or psd_value < 0.0:
            raise ValueError("psd_value must be finite and non-negative.")
        psd = psd_value * np.ones_like(theta, dtype=float)
        one_sided_interior = (theta > 0.0) & (theta < np.pi)
        psd[one_sided_interior] *= 2.0
        return cls(theta=theta, psd=psd, fb=fb)

    @property
    def freqs(self) -> np.ndarray:
        """
        Debug convenience axis in Hz: f = theta*fb/(2*pi).
        """
        return self.theta * self.fb / (2 * np.pi)

    def to_continuous_baseband(self) -> ContinuousPSD:
        """
        Convert sampled-domain PSD to a baseband-equivalent ContinuousPSD.

        This is not an inverse of broadband aliasing. It only maps the stored
        sampled-domain PSD back to the equivalent 0..fb/2 continuous baseband:
            S_ct,1(f) = S_sampled,1(theta)
        """
        return ContinuousPSD(
            freqs=self.freqs,
            psd=self.psd,
            ifftable=False,
        )

    def filtered_by(self, response: SampledResponse) -> 'SampledPSD':
        """
        Return the sampled PSD after filtering by a SampledResponse.

        Parameters
        ----------
        response:
            Sampled-domain response whose theta grid and fb match this PSD.
        """
        if not np.isclose(self.fb, response.fb):
            raise ValueError("SampledPSD and SampledResponse fb values must match.")
        if not np.allclose(self.theta, response.theta, rtol=1e-12, atol=1e-15):
            raise ValueError("SampledPSD and SampledResponse theta grids must match.")
        return type(self)(theta=self.theta, psd=self.psd * response.magnitude_squared(), fb=self.fb)

    def add(self, other: 'SampledPSD') -> 'SampledPSD':
        """
        Return the sum of two independent sampled-domain PSD components.

        Parameters
        ----------
        other:
            Another SampledPSD with the same fb and theta grid.

        Notes
        -----
        This method assumes the two PSD components are uncorrelated, so their
        power spectral densities add directly:
            S_total(theta) = S_self(theta) + S_other(theta)
        """
        if not isinstance(other, SampledPSD):
            raise TypeError("other must be a SampledPSD.")
        if not np.isclose(self.fb, other.fb):
            raise ValueError("SampledPSD fb values must match.")
        if not np.allclose(self.theta, other.theta, rtol=1e-12, atol=1e-15):
            raise ValueError("SampledPSD theta grids must match.")
        return type(self)(theta=self.theta, psd=self.psd + other.psd, fb=self.fb)

    def __add__(self, other: 'SampledPSD') -> 'SampledPSD':
        """
        Operator alias for add().
        """
        return self.add(other)

    def to_sigma(self) -> float:
        """
        Integrate sampled PSD and return RMS amplitude.

        The stored PSD is a theta-indexed Hz-density one-sided equivalent.
        With an rfft grid of even Nfft, df = fb/Nfft and:
            sigma^2 = df * sum(S_one_sided)
        """
        nfft = 2 * (len(self.theta) - 1)
        df = self.fb / nfft
        power = float(df * np.sum(self.psd))
        return float(np.sqrt(power))

    def to_autocorrelation(self) -> np.ndarray:
        """
        Return discrete-time autocorrelation R[n] from the sampled PSD.

        Returns
        -------
        np.ndarray
            Real-valued autocorrelation sequence with length Nfft.

        Notes
        -----
        The stored one-sided equivalent is converted back to the spec-style
        two-sided theta-indexed Hz-density PSD before IDFT:
            R[n] = fb * ifft(S_two_sided)[n]
        """
        nfft = 2 * (len(self.theta) - 1)
        psd_two = np.empty(nfft, dtype=float)
        psd_two[0] = self.psd[0]
        psd_two[nfft // 2] = self.psd[-1]
        if len(self.theta) > 2:
            interior = 0.5 * self.psd[1:-1]
            psd_two[1:nfft // 2] = interior
            psd_two[nfft // 2 + 1:] = interior[::-1]
        return np.real(np.fft.ifft(psd_two) * self.fb)

    def plot(
        self,
        ax: Optional[Axes] = None,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        label: str | None = None,
        x_axis: Literal["CT", "DT"] = "CT",
    ) -> Axes:
        """
        Plot the one-sided sampled PSD versus an equivalent CT or DT axis.

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
        x_axis:
            ``"CT"`` (default) plots the equivalent baseband frequency in Hz;
            ``"DT"`` plots theta in rad/sample. The PSD values are unchanged
            and remain in quantity^2/Hz for either axis.
        """
        import matplotlib.pyplot as plt

        if x_axis not in {"CT", "DT"}:
            raise ValueError("x_axis must be either 'CT' or 'DT'.")

        created_ax = ax is None
        if created_ax:
            _, ax = plt.subplots()

        x_values = self.freqs if x_axis == "CT" else self.theta
        psd = self.psd
        if xlim is not None:
            lo, hi = float(xlim[0]), float(xlim[1])
            if lo >= hi:
                raise ValueError("xlim must be strictly increasing.")
            mask = (x_values >= lo) & (x_values <= hi)
            if not np.any(mask):
                raise ValueError("xlim selects no PSD samples.")
            x_values = x_values[mask]
            psd = psd[mask]

        ax.plot(x_values, psd, label=label)
        if label is not None:
            ax.legend()
        if x_axis == "CT":
            ax.set_xlabel("Equivalent baseband frequency (Hz)")
        else:
            ax.set_xlabel("Normalized frequency (theta, rad/sample)")
        ax.set_ylabel("One-sided sampled PSD (quantity^2/Hz)")
        ax.set_title("Sampled PSD")
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

# Backward compatibility for the existing 93A implementation.
OneSidePSD = ContinuousPSD

@dataclass
class SparamProcessor:
    """
    S-parameter to SBR preprocessing and conversion flow.

    This class collects the practical issues called out by sparam_to_sbr.pdf:
    - missing DC value
    - causality check/fix
    - passivity check/fix
    - frequency grid / time-step alignment
    - frequency-domain interpolation / extrapolation
    - frequency-domain response to impulse response
    - impulse/step response to SBR

    First-version policy:
    - DC fix is implemented through SparamModel.extrapolated_to_dc().
    - Causality and passivity checks are implemented.
    - Causality and passivity fixes are intentionally explicit
      NotImplementedError methods because robust fixes require model fitting or
      minimum-phase reconstruction, not simple pointwise edits.
    """
    cfg: LinkConfig
    gamma_src: complex | np.ndarray = 0.0
    gamma_load: complex | np.ndarray = 0.0

    def check_dc(self, channel: SparamModel) -> dict[str, bool | float]:
        """
        Check whether the S-parameter model contains a DC point.

        Academic rationale:
        the DC value anchors low-frequency magnitude and phase. Missing or
        inconsistent DC can create baseline shift and non-causal-looking time
        responses after IFFT.
        """
        f0 = float(channel.freqs[0])
        return {
            "has_dc": bool(np.isclose(f0, 0.0)),
            "first_frequency": f0,
        }

    def fix_dc(self, channel: SparamModel) -> SparamModel:
        """
        Add a DC point using scikit-rf DC extrapolation.

        Academic rationale:
        DC extrapolation is a low-frequency boundary condition. It is more
        defensible than forcing zero because S-parameter phase and magnitude at
        DC determine the long-time step/SBR baseline.
        """
        return channel.extrapolated_to_dc()

    def check_passivity(self, channel: SparamModel, tol: float = 1e-6) -> dict[str, bool | float]:
        """
        Check passivity by the largest singular value of S(f).

        Academic rationale:
        for a passive network with consistent real reference impedance, the
        scattering matrix should not increase incident power. This is checked by
        max singular value <= 1.
        """
        singular_values = np.linalg.svd(channel.sdd, compute_uv=False)
        max_sigma = float(np.max(singular_values))
        return {
            "is_passive": bool(max_sigma <= 1.0 + tol),
            "max_singular_value": max_sigma,
            "tol": float(tol),
        }

    def fix_passivity(self, channel: SparamModel) -> SparamModel:
        """
        Placeholder for passivity enforcement.

        Academic rationale:
        passivity fixing should preserve a physically realizable network, which
        normally requires rational/vector fitting plus passivity enforcement.
        Pointwise clipping of S-parameters is not used here because it can break
        causality and reciprocity.
        """
        raise NotImplementedError("Passivity fixing requires a fitting-based enforcement method.")

    def check_reciprocity(self, channel: SparamModel, tol: float = 1e-6) -> dict[str, bool | float]:
        """
        Check two-port reciprocity by comparing Sdd21 and Sdd12.

        Academic rationale:
        many passive interconnect channels are reciprocal. A large mismatch
        between S21 and S12 usually indicates measurement, port-order, or data
        processing issues.
        """
        max_error = float(np.max(np.abs(channel.sdd21 - channel.sdd12)))
        return {
            "is_reciprocal": bool(max_error <= tol),
            "max_s12_s21_error": max_error,
            "tol": float(tol),
        }

    def check_frequency_grid(self, channel: SparamModel) -> dict[str, bool | float | int]:
        """
        Report frequency-grid coverage relative to cfg.

        Academic rationale:
        SBR time resolution and time-window length are set by df and fmax after
        resampling. The raw S-parameter grid must cover enough of cfg.freqs to
        build a stable in-band H(f) before scalar high-frequency extension.
        """
        f_inband = self.cfg.freqs[self.cfg.freqs <= channel.freqs[-1]]
        return {
            "channel_f_start": float(channel.freqs[0]),
            "channel_f_stop": float(channel.freqs[-1]),
            "cfg_f_nyq": float(self.cfg.f_nyq),
            "inband_points_on_cfg": int(len(f_inband)),
            "covers_cfg_nyq": bool(channel.freqs[-1] >= self.cfg.f_nyq),
        }

    def resample_for_sbr(self, channel: SparamModel) -> SparamModel:
        """
        Resample S-parameters onto the cfg frequency grid inside channel f_stop.

        Academic rationale:
        interpolation is acceptable inside measured bandwidth. High-frequency
        extrapolation is left to the scalar LinkSegment transfer-function stage,
        because extrapolating a full S-matrix while preserving passivity and
        causality is a harder physical-modeling problem.
        """
        return channel.resampled(self.cfg.freqs)

    def to_voltage_transfer(self, channel: SparamModel) -> np.ndarray:
        """
        Convert the Sdd two-port to terminated voltage transfer H21(f).

        Academic rationale:
        S-parameters describe traveling-wave ratios. SBR generation needs the
        scalar voltage transfer function seen by the source/load terminations.
        """
        return channel.voltage_transfer_function(
            gamma_src=self.gamma_src,
            gamma_load=self.gamma_load,
        )

    def frequency_to_segment(self, channel: SparamModel, dc_fix: bool = True) -> LinkSegment:
        """
        Convert S-parameters to a scalar LinkSegment.

        Flow:
        1. optionally add DC
        2. resample S-parameters inside measured bandwidth
        3. compute H21(f)
        4. use LinkSegment.from_tf() for scalar extension and IFFT-ready data
        """
        working = self.fix_dc(channel) if dc_fix and not self.check_dc(channel)["has_dc"] else channel
        working = self.resample_for_sbr(working)
        H21 = self.to_voltage_transfer(working)
        return LinkSegment.from_tf(working.freqs, H21, self.cfg)

    def check_causality(self, channel: SparamModel, dc_fix: bool = True) -> dict[str, bool | float | int]:
        """
        Check time-domain warning metrics after S-parameter to H21 conversion.

        Academic rationale:
        causality violations often appear as impulse-response energy wrapped to
        the end of the FFT time window or as delay inconsistent with phase
        slope. This method reports LinkSegment's time-axis diagnostics.
        """
        segment = self.frequency_to_segment(channel, dc_fix=dc_fix)
        return segment.debug_time_axis()

    def fix_causality(self, channel: SparamModel) -> SparamModel:
        """
        Placeholder for causality repair.

        Academic rationale:
        causality repair should modify phase/magnitude consistently. Common
        approaches include rational fitting or minimum-phase reconstruction from
        a physically meaningful magnitude response.
        """
        raise NotImplementedError("Causality fixing requires a model- or phase-reconstruction method.")

    def to_sbr(self, channel: SparamModel, dc_fix: bool = True) -> np.ndarray:
        """
        Convert an S-parameter channel to SBR.

        Academic rationale:
        SBR is the one-UI difference of the step response after the scalar
        H21(f) has been converted to the project's continuous-time FFT grid.
        """
        return self.frequency_to_segment(channel, dc_fix=dc_fix).sbr

class SparamModel:
    """
    Generic scikit-rf Network wrapper for differential S-parameter data.

    Class boundary
    --------------
    SparamModel is the generic container for Sdd two-port data after any required
    input normalization. It owns:
    - array / Touchstone / rf.Network ingestion
    - input validation contract for frequency axes, Sdd, S4P, and port order
    - single-ended S4P to differential-mode Sdd conversion
    - generic Sdd two-port cascade operations through scikit-rf
    - conversion from Sdd to terminated voltage transfer H21(f), then LinkSegment

    Domain wrapper contract
    -----------------------
    This class is intentionally more constrained than a raw skrf.Network. A
    raw Network is a flexible numerical container; SparamModel is the project's
    standardized S-parameter preprocessing boundary.

    The object guarantees:
    - self.network always stores a differential-mode Sdd two-port, not an S4P.
    - S4P port ordering is handled only at construction time through
      port_order=(tx_p, tx_n, rx_p, rx_n).
    - After S4P-to-Sdd conversion, z0 means differential reference impedance.
      A single-ended R0=50 ohm input should therefore become z0=100 ohm.
    - Public transformation methods do not mutate the original object, so raw
      measurement data and intermediate processing stages can be compared.
    - Resampling is S-matrix-domain interpolation within the measured frequency
      span. High-frequency extrapolation is intentionally handled later by the
      scalar LinkSegment transfer-function path, not here.

    The raw skrf.Network is still exposed as self.network for advanced
    inspection, but normal project code should prefer the SparamModel methods so
    the above contract remains visible and consistent.

    Public mutation policy
    ----------------------
    Public transformation methods return a modified copy and leave self
    unchanged:
    - cascade()
    - renormalized()
    - resampled()
    - extrapolated_to_dc()

    There is no public in-place transformation API. Methods that wrap in-place
    scikit-rf operations apply them to copied Networks before returning a new
    SparamModel.

    It should not own IEEE COM primitive model construction such as shunt
    capacitance, package transmission line, Tx package, Rx package builders, or
    IEEE COM-specific cascade formulas and primitive model builders belong in
    com_model_93A.py or com_model_178A.py, not in this generic container.

    Internal storage
    ----------------
    S-parameters are stored as an rf.Network whose network.s is always
    COM-style differential-mode Sdd:
    - differential-mode Sdd array with shape (N, 2, 2)
    - single-ended S4P array with shape (N, 4, 4), then converts to Sdd

    The stored Sdd matrix uses the COM-style two-port order:
        [[Sdd11, Sdd12],
         [Sdd21, Sdd22]]

    For S4P conversion, the default port order is:
        (tx_p, tx_n, rx_p, rx_n) = (0, 1, 2, 3)
    using Python zero-based indices.

    Public port-order convention
    ----------------------------
    SparamModel intentionally exposes only the 4-port single-ended S4P order:
        port_order = (tx_p, tx_n, rx_p, rx_n)

    Once the model is constructed, self.network stores only a 2-port Sdd
    representation. The internal Sdd port order is fixed and is not exposed as
    a public renumbering API.
    """

    def __init__(
        self,
        network: 'rf.Network',
        source_type: str,
        port_order: tuple[int, int, int, int] | None = None,
    ):
        self.network: rf.Network = self.validate_network(network)
        self.source_type = source_type
        self.port_order = port_order

    # -------------------
    # constructors
    # -------------------
    @staticmethod
    def _network_from_smatrix(
        freqs: np.ndarray,
        smatrix: np.ndarray,
        z0: Union[float, np.ndarray] = 100.0,
    ) -> 'rf.Network':
        frequency = rf.Frequency.from_f(freqs, unit="Hz")
        return rf.Network(frequency=frequency, s=smatrix, z0=z0)

    @classmethod
    def from_sdd_array(
        cls,
        freqs: np.ndarray,
        sdd: np.ndarray,
        z0: Union[float, np.ndarray] = 100.0,
    ) -> 'SparamModel':
        """
        Build from a differential-mode 2-port Sdd array.

        Input contract:
        - freqs: 1D, finite, strictly increasing frequency axis in Hz
        - sdd: complex array with shape (len(freqs), 2, 2)
        - z0: reference impedance assigned to the internal rf.Network
        """
        freqs = LinkConfig.validate_freqs(freqs)
        sdd = cls.validate_sdd(sdd, freqs)
        return cls(cls._network_from_smatrix(freqs, sdd, z0=z0), source_type="sdd")

    @classmethod
    def from_s4p_array(
        cls,
        freqs: np.ndarray,
        s4p: np.ndarray,
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
        z0: Union[float, np.ndarray] = 100.0,
    ) -> 'SparamModel':
        """
        Build from a single-ended 4-port S-parameter array.

        Input contract:
        - freqs: 1D, finite, strictly increasing frequency axis in Hz
        - s4p: complex array with shape (len(freqs), 4, 4)
        - port_order: old zero-based S4P ports in desired order
          (tx_p, tx_n, rx_p, rx_n)
        - z0: differential-mode reference impedance assigned after Sdd conversion
        """
        freqs = LinkConfig.validate_freqs(freqs)
        port_order = _validate_s4p_port_order(port_order)
        sdd = _s4p_to_sdd(s4p, port_order, freqs)
        return cls(cls._network_from_smatrix(freqs, sdd, z0=z0), source_type="s4p", port_order=port_order)

    @classmethod
    def from_network(
        cls,
        network: 'rf.Network',
        mode: str = "auto",
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
        z0: Union[float, np.ndarray, None] = None,
    ) -> 'SparamModel':
        """
        Build from an existing scikit-rf Network.

        Input contract:
        - mode="sdd": network.s must have shape (N, 2, 2)
        - mode="s4p": network.s must have shape (N, 4, 4)
        - mode="auto": 2-port is treated as Sdd, 4-port as single-ended S4P

        mode:
        - "auto": 2-port is treated as Sdd, 4-port as single-ended S4P
        - "sdd": input network.s is already differential-mode Sdd
        - "s4p": input network.s is single-ended 4-port data converted to Sdd

        z0:
        - None with mode="sdd": preserve network.z0
        - None with mode="s4p": derive differential z0 from the single-ended
          port pairs after applying port_order
        - explicit value: use it as the internal Sdd differential reference
          impedance
        """

        if mode not in {"auto", "sdd", "s4p"}:
            raise ValueError('mode must be "auto", "sdd", or "s4p".')

        if mode == "auto":
            if network.s.shape[1:] == (2, 2):
                mode = "sdd"
            elif network.s.shape[1:] == (4, 4):
                mode = "s4p"
            else:
                raise ValueError("Only 2-port Sdd and 4-port single-ended networks are supported.")

        if mode == "sdd":
            z0_sdd = network.z0 if z0 is None else z0
            return cls.from_sdd_array(network.f, network.s, z0=z0_sdd)

        z0_sdd = _differential_z0_from_s4p_z0(network.z0, port_order) if z0 is None else z0
        return cls.from_s4p_array(network.f, network.s, port_order=port_order, z0=z0_sdd)

    @classmethod
    def from_touchstone(
        cls,
        path: str,
        mode: str = "auto",
        port_order: tuple[int, int, int, int] = (0, 1, 2, 3),
        z0: Union[float, np.ndarray, None] = None,
    ) -> 'SparamModel':
        ntwk = rf.Network(path)
        return cls.from_network(ntwk, mode=mode, port_order=port_order, z0=z0)

    # --------------------
    # validation methods
    # --------------------
    @staticmethod
    def validate_sdd(sdd: np.ndarray, freqs: np.ndarray) -> np.ndarray:
        sdd = np.asarray(sdd, dtype=complex)

        if sdd.shape != (len(freqs), 2, 2):
            raise ValueError("sdd must have shape (len(freqs), 2, 2).")

        if not np.all(np.isfinite(sdd)):
            raise ValueError("sdd contains non-finite values.")

        return sdd

    @staticmethod
    def validate_network(network: 'rf.Network') -> 'rf.Network':

        if not isinstance(network, rf.Network):
            raise TypeError("network must be an skrf.Network.")

        sdd = np.asarray(network.s, dtype=complex)
        if sdd.ndim != 3 or sdd.shape[1:] != (2, 2):
            raise ValueError("SparamModel.network must store Sdd with shape (N, 2, 2).")

        freqs = np.asarray(network.f, dtype=float)
        LinkConfig.validate_freqs(freqs)
        SparamModel.validate_sdd(sdd, freqs)

        return network

    def validate_compatible_sparam(self, other: 'SparamModel') -> None:
        if not isinstance(other, SparamModel):
            raise TypeError("other must be an SparamModel.")

        if self.sdd.shape[1:] != (2, 2) or other.sdd.shape[1:] != (2, 2):
            raise ValueError("Both SparamModel objects must contain 2-port Sdd networks.")

        if self.sdd.shape[0] != other.sdd.shape[0]:
            raise ValueError("Cannot cascade SparamModel objects with different frequency counts.")

        if not np.allclose(self.freqs, other.freqs):
            raise ValueError("Cannot cascade SparamModel objects with different frequency grids.")

        if not np.allclose(self.network.z0, other.network.z0):
            raise ValueError("Cannot cascade SparamModel objects with different z0.")

    def validate_resample_freqs(self, freqs: np.ndarray) -> np.ndarray:
        freqs = LinkConfig.validate_freqs(freqs)

        if freqs[-1] < self.freqs[0]:
            raise ValueError("resample() target grid is entirely below the measured frequency span.")

        return freqs

    # -------------------
    # proxy
    # -------------------
    @property
    def freqs(self) -> np.ndarray:
        return self.network.f

    @property
    def sdd(self) -> np.ndarray:
        return self.network.s

    @property
    def sdd11(self) -> np.ndarray:
        return self.sdd[:, 0, 0]

    @property
    def sdd12(self) -> np.ndarray:
        return self.sdd[:, 0, 1]

    @property
    def sdd21(self) -> np.ndarray:
        return self.sdd[:, 1, 0]

    @property
    def sdd22(self) -> np.ndarray:
        return self.sdd[:, 1, 1]

    # -------------------
    # public methods
    # -------------------
    # ---- SerDes-oriented plot helpers ----
    @staticmethod
    def _plt() -> Any:
        import matplotlib.pyplot as plt
        return plt

    @staticmethod
    def _magnitude_db(response: np.ndarray) -> np.ndarray:
        return 20 * np.log10(np.maximum(np.abs(response), np.finfo(float).tiny))

    def _finish_frequency_plot(self, ax: Any, save_path: str, show: bool = True) -> Any:
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

    def _apply_frequency_plot_style(
        self,
        ax: Any,
        xlim: Optional[tuple[float, float]] = None,
        x_scale: Optional[float] = None,
        y_values: Optional[np.ndarray] = None,
        y_mask: Optional[np.ndarray] = None,
        auto_ylim: bool = True,
        ylim_pad_ratio: float = 0.05,
        auto_ylim_floor: Optional[float] = -300.0,
    ) -> Any:
        """
        Apply SparamModel's default frequency-plot convention.

        Parameters
        ----------
        ax:
            Matplotlib Axes to update.
        xlim:
            Optional frequency limits in Hz.
        x_scale:
            Multiplier from Hz to the plot x-axis unit. If None, infer the
            scale from the scikit-rf Network frequency object.
        y_values:
            Optional plotted y-values in dB or degrees used for automatic y-limit.
            Shape can be (N,) or (K, N).
        y_mask:
            Frequency mask corresponding to the displayed x-range.
        auto_ylim:
            If True, set y-limits from y_values inside y_mask.
        ylim_pad_ratio:
            Fractional y-span padding used when auto_ylim is True.
        auto_ylim_floor:
            Optional lower display floor for automatic y-limit calculation.
            Values below this floor are treated as numerical floor artifacts
            such as ideal zeros, but the plotted data itself is not clipped.
        """
        if ax is None:
            ax = self._plt().gca()

        ax.grid(True)
        if xlim is None:
            lo_hz = float(self.freqs[0])
            hi_hz = float(self.freqs[-1])
        else:
            if len(xlim) != 2:
                raise ValueError("xlim must contain two values: (start_hz, stop_hz).")
            lo_hz = float(xlim[0])
            hi_hz = float(xlim[1])
            if not np.isfinite(lo_hz) or not np.isfinite(hi_hz) or lo_hz >= hi_hz:
                raise ValueError("xlim must be finite and strictly increasing.")

        if x_scale is None:
            f_scaled = np.asarray(self.network.frequency.f_scaled, dtype=float)
            valid = np.abs(self.freqs) > 0.0
            x_scale = float(np.median(f_scaled[valid] / self.freqs[valid])) if np.any(valid) else 1.0

        if xlim is not None:
            ax.set_xlim(lo_hz * x_scale, hi_hz * x_scale)

        if y_mask is None:
            y_mask = (self.freqs >= lo_hz) & (self.freqs <= hi_hz)
        if auto_ylim and y_values is not None:
            y_arr = np.asarray(y_values, dtype=float)
            if y_arr.ndim == 1:
                visible = y_arr[y_mask]
            elif y_arr.ndim == 2:
                visible = y_arr[:, y_mask].ravel()
            else:
                raise ValueError("y_values must be 1D or 2D.")

            visible = visible[np.isfinite(visible)]
            if auto_ylim_floor is not None:
                above_floor = visible[visible > float(auto_ylim_floor)]
                if above_floor.size > 0:
                    visible = above_floor
            if visible.size > 0:
                y_min = float(np.min(visible))
                y_max = float(np.max(visible))
                if np.isclose(y_min, y_max):
                    pad = max(1.0, abs(y_min) * ylim_pad_ratio)
                else:
                    pad = (y_max - y_min) * float(ylim_pad_ratio)
                ax.set_ylim(y_min - pad, y_max + pad)

        return ax

    def plot_IL(
        self,
        ax: Any = None,
        logx: bool = False,
        xlim: Optional[tuple[float, float]] = None,
        save_path: str = "",
        label: str | None = None,
        auto_ylim: bool = True,
        annotate_f: Optional[float] = None,
        annotate_label: str = "IL",
        **kwargs: Any,
    ) -> Any:
        """
        Plot differential insertion loss IL = Sdd21 in dB.

        SparamModel stores a two-port Sdd network, so the SerDes through path is
        fixed as port[0] -> port[1]. This method intentionally does not expose
        arbitrary S-parameter indices.

        Parameters
        ----------
        ax:
            Optional matplotlib axes.
        logx:
            Whether to use a logarithmic frequency axis.
        xlim:
            Optional frequency limits in Hz.
        save_path:
            Optional output path. If provided, save the figure and close it.
        label:
            Optional curve label. Useful when overlaying multiple channels.
        auto_ylim:
            If True, set y-limits from the plotted frequency range.
        annotate_f:
            Optional frequency in Hz to annotate, e.g. fb for IL at baud rate.
        annotate_label:
            Label prefix for the annotation text.
        **kwargs:
            Additional keyword arguments passed to matplotlib ``plot``.
        """
        created_ax = ax is None
        if created_ax:
            _, ax = self._plt().subplots()
        il_db = self._magnitude_db(self.sdd21)
        ax.plot(self.freqs / 1e9, il_db, label=label or "Sdd21", **kwargs)
        if logx:
            ax.set_xscale("log")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("IL, Sdd21 (dB)")
        ax.set_title("Insertion Loss")
        ax.legend()
        self._apply_frequency_plot_style(ax, xlim=xlim, x_scale=1e-9, y_values=il_db, auto_ylim=auto_ylim)
        if annotate_f is not None:
            self.annotate_IL(ax, annotate_f, label=annotate_label)
        return self._finish_frequency_plot(ax, save_path, show=created_ax)

    def annotate_IL(self, ax: Any, f: float, label: str = "IL") -> Any:
        """Annotate insertion loss Sdd21 at a specific frequency."""
        f_hz = float(f)
        if not np.isfinite(f_hz):
            raise ValueError("f must be finite.")
        if f_hz < self.freqs[0] or f_hz > self.freqs[-1]:
            raise ValueError("f must be within self.freqs.")

        il_db = self._magnitude_db(self.sdd21)
        il_at_f = float(np.interp(f_hz, self.freqs, il_db))
        f_ghz = f_hz / 1e9
        ax.axvline(f_ghz, linestyle="--", color="tab:red", linewidth=1.0)
        y_min, y_max = ax.get_ylim()
        y_text = min(max(il_at_f, y_min), y_max)
        ax.annotate(
            f"{label}@{f_ghz:.3f} GHz = {il_at_f:.2f} dB",
            xy=(f_ghz, y_text),
            xytext=(6, 8),
            textcoords="offset points",
            fontsize=8,
            color="tab:red",
            arrowprops={"arrowstyle": "->", "color": "tab:red", "linewidth": 0.8},
        )
        return ax

    def annotate_f(self, ax: Any, f: float, label: str = "Sdd21") -> Any:
        """
        Annotate through-path Sdd21 relative gain at a specific frequency.

        Parameters
        ----------
        ax:
            Matplotlib Axes containing a SparamModel frequency plot.
        f:
            Frequency in Hz to annotate.
        label:
            Label prefix for the annotation text.
        """
        f_hz = float(f)
        if not np.isfinite(f_hz):
            raise ValueError("f must be finite.")
        if f_hz < self.freqs[0] or f_hz > self.freqs[-1]:
            raise ValueError("f must be within self.freqs.")

        mag_db = self._magnitude_db(self.sdd21)
        rel_db = mag_db - mag_db[0]
        mag_at_f = float(np.interp(f_hz, self.freqs, mag_db))
        rel_at_f = float(np.interp(f_hz, self.freqs, rel_db))
        f_ghz = f_hz / 1e9

        y_min, y_max = ax.get_ylim()
        ax.axvline(f_ghz, linestyle="--", color="tab:red", linewidth=1.0)
        ax.plot(f_ghz, mag_at_f, marker="o", color="tab:red", markersize=4)
        ax.annotate(
            f"{label}@{f_ghz:.3f} GHz = {rel_at_f:.1f} dB",
            xy=(f_ghz, mag_at_f),
            xytext=(6, 8),
            textcoords="offset points",
            fontsize=8,
            color="tab:red",
            bbox={"boxstyle": "round,pad=0.2", "fc": "white", "ec": "tab:red", "alpha": 0.85},
        )
        ax.set_ylim(y_min, y_max)
        return ax

    def frequency_at_sdd21_gain(self, gain_db: float = -3.0) -> Optional[float]:
        """
        Return first frequency where Sdd21 drops to a relative gain target.

        Parameters
        ----------
        gain_db:
            Relative gain in dB with respect to Sdd21 at DC.
        """
        rel_db = self._magnitude_db(self.sdd21) - self._magnitude_db(self.sdd21)[0]
        target = float(gain_db)
        crossing = np.where(rel_db <= target)[0]
        if len(crossing) == 0:
            return None
        idx = int(crossing[0])
        if idx == 0:
            return float(self.freqs[0])
        x0, x1 = float(self.freqs[idx - 1]), float(self.freqs[idx])
        y0, y1 = float(rel_db[idx - 1]), float(rel_db[idx])
        if np.isclose(y0, y1):
            return x1
        return float(x0 + (target - y0) * (x1 - x0) / (y1 - y0))

    def plot_RL(
        self,
        port: Literal["input", "output", "both"] = "both",
        ax: Any = None,
        logx: bool = False,
        xlim: Optional[tuple[float, float]] = None,
        save_path: str = "",
        label: str | None = None,
        auto_ylim: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Plot differential return loss RL in dB.

        RL is interpreted from the Sdd two-port reference planes:
        - port="input": Sdd11
        - port="output": Sdd22
        - port="both": Sdd11 and Sdd22

        Parameters
        ----------
        port:
            Which differential port reflection to plot.
        ax:
            Optional matplotlib axes.
        logx:
            Whether to use a logarithmic frequency axis.
        xlim:
            Optional frequency limits in Hz.
        save_path:
            Optional output path. If provided, save the figure and close it.
        label:
            Optional label prefix. Useful when overlaying multiple channels.
        auto_ylim:
            If True, set y-limits from the plotted frequency range.
        **kwargs:
            Additional keyword arguments passed to matplotlib ``plot``.
        """
        created_ax = ax is None
        if created_ax:
            _, ax = self._plt().subplots()
        prefix = "" if label is None else f"{label} "
        plotted: list[np.ndarray] = []
        if port == "input":
            y = self._magnitude_db(self.sdd11)
            plotted.append(y)
            ax.plot(self.freqs / 1e9, y, label=f"{prefix}Sdd11", **kwargs)
        elif port == "output":
            y = self._magnitude_db(self.sdd22)
            plotted.append(y)
            ax.plot(self.freqs / 1e9, y, label=f"{prefix}Sdd22", **kwargs)
        elif port == "both":
            y11 = self._magnitude_db(self.sdd11)
            y22 = self._magnitude_db(self.sdd22)
            plotted.extend([y11, y22])
            ax.plot(self.freqs / 1e9, y11, label=f"{prefix}Sdd11", **kwargs)
            ax.plot(self.freqs / 1e9, y22, label=f"{prefix}Sdd22", **kwargs)
        else:
            raise ValueError('port must be "input", "output", or "both".')
        if logx:
            ax.set_xscale("log")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("RL (dB)")
        ax.set_title("Return Loss")
        ax.legend()
        y_values = np.vstack(plotted) if plotted else None
        self._apply_frequency_plot_style(ax, xlim=xlim, x_scale=1e-9, y_values=y_values, auto_ylim=auto_ylim)
        return self._finish_frequency_plot(ax, save_path, show=created_ax)

    def plot_phase(
        self,
        ax: Any = None,
        logx: bool = False,
        unwrap: bool = True,
        xlim: Optional[tuple[float, float]] = None,
        save_path: str = "",
        label: str | None = None,
        auto_ylim: bool = True,
        **kwargs: Any,
    ) -> Any:
        """
        Plot through-path phase of Sdd21 in degrees.

        Parameters
        ----------
        ax:
            Optional matplotlib axes.
        logx:
            Whether to use a logarithmic frequency axis.
        unwrap:
            If True, unwrap phase before plotting. This is the SerDes default
            because through-channel phase continuity is usually the useful view.
        xlim:
            Optional frequency limits in Hz.
        save_path:
            Optional output path. If provided, save the figure and close it.
        label:
            Optional curve label. Useful when overlaying multiple channels.
        auto_ylim:
            If True, set y-limits from the plotted frequency range.
        **kwargs:
            Additional keyword arguments passed to matplotlib ``plot``.
        """
        created_ax = ax is None
        if created_ax:
            _, ax = self._plt().subplots()
        phase = np.angle(self.sdd21)
        if unwrap:
            phase = np.unwrap(phase)
        phase_deg = np.rad2deg(phase)
        ax.plot(self.freqs / 1e9, phase_deg, label=label or "Sdd21 phase", **kwargs)
        if logx:
            ax.set_xscale("log")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Phase (deg)")
        ax.set_title("Sdd21 Phase")
        ax.legend()
        self._apply_frequency_plot_style(ax, xlim=xlim, x_scale=1e-9, y_values=phase_deg, auto_ylim=auto_ylim)
        return self._finish_frequency_plot(ax, save_path, show=created_ax)

    def plot_sdd(
        self,
        ax: Any = None,
        logx: bool = False,
        xlim: Optional[tuple[float, float]] = None,
        save_path: str = "",
        auto_ylim: bool = True,
    ) -> Any:
        """
        Plot Sdd11, Sdd12, Sdd21, and Sdd22 magnitude in dB on one figure.

        Parameters
        ----------
        ax:
            Optional matplotlib axes. If provided, draw on this axes and leave
            display / close behavior to the caller unless save_path is set.
        logx:
            Whether to use a logarithmic frequency axis.
        xlim:
            Optional frequency limits in Hz.
        save_path:
            Optional output path. If provided, save the figure and close it;
            otherwise show the figure immediately.
        auto_ylim:
            If True, set y-limits from the plotted frequency range.
        """
        created_ax = ax is None
        if created_ax:
            _, ax = self._plt().subplots()
        y_values = np.vstack([
            self._magnitude_db(self.sdd11),
            self._magnitude_db(self.sdd12),
            self._magnitude_db(self.sdd21),
            self._magnitude_db(self.sdd22),
        ])
        ax.plot(self.freqs / 1e9, y_values[0], label="Sdd11")
        ax.plot(self.freqs / 1e9, y_values[1], label="Sdd12")
        ax.plot(self.freqs / 1e9, y_values[2], label="Sdd21")
        ax.plot(self.freqs / 1e9, y_values[3], label="Sdd22")
        if logx:
            ax.set_xscale("log")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Magnitude (dB)")
        ax.set_title("Sdd Parameters")
        ax.legend()
        self._apply_frequency_plot_style(ax, xlim=xlim, x_scale=1e-9, y_values=y_values, auto_ylim=auto_ylim)
        return self._finish_frequency_plot(ax, save_path, show=created_ax)

    def plot_smith(
        self,
        port: Literal["input", "output"] = "input",
        ax: Any = None,
        chart_type: str = "z",
        draw_labels: bool = False,
        label_axes: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Plot input or output differential return term on a Smith chart.

        Parameters
        ----------
        port:
            "input" plots Sdd11; "output" plots Sdd22.
        ax:
            Optional matplotlib axes.
        chart_type:
            Smith chart type passed to scikit-rf, usually "z" or "y".
        draw_labels:
            Whether to draw Smith chart labels.
        label_axes:
            Whether to label axes.
        **kwargs:
            Additional keyword arguments passed to scikit-rf.
        """
        if port == "input":
            m, n = 0, 0
        elif port == "output":
            m, n = 1, 1
        else:
            raise ValueError('port must be "input" or "output".')

        plot_ax = self.network.plot_s_smith(
            m=m,
            n=n,
            ax=ax,
            show_legend=True,
            chart_type=chart_type,
            draw_labels=draw_labels,
            label_axes=label_axes,
            **kwargs,
        )
        plot_ax.grid(True)
        return plot_ax

    def plot_all(self, *args: Any, **kwargs: Any) -> Any:
        """
        Plot scikit-rf's default S-parameter summary view.

        This delegates to Network.plot_it_all(), which draws dB, phase, Smith,
        and complex plots in subplots.
        """
        result = self.network.plot_it_all(*args, **kwargs)
        for ax in self._plt().gcf().axes:
            ax.grid(True)
        return result

    def _debug_scalar_tf(
        self,
        response: Literal["sdd11", "sdd12", "sdd21", "sdd22", "h21"] = "sdd21",
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
    ) -> np.ndarray:
        """
        Select a scalar frequency response from the Sdd model for debug plots.

        Parameters
        ----------
        response:
            Which scalar response to inspect. "h21" uses the terminated voltage
            transfer formula; with matched terminations it is equal to Sdd21.
        gamma_src:
            Source reflection coefficient used only when response="h21".
        gamma_load:
            Load reflection coefficient used only when response="h21".
        """
        if response == "sdd11":
            return self.sdd11
        if response == "sdd12":
            return self.sdd12
        if response == "sdd21":
            return self.sdd21
        if response == "sdd22":
            return self.sdd22
        if response == "h21":
            return self.voltage_transfer_function(gamma_src=gamma_src, gamma_load=gamma_load)
        raise ValueError('response must be "sdd11", "sdd12", "sdd21", "sdd22", or "h21".')

    def _debug_LinkSegment(
        self,
        cfg: 'LinkConfig',
        response: Literal["sdd11", "sdd12", "sdd21", "sdd22", "h21"] = "sdd21",
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
        dc: Literal["hold", "skrf", "error"] = "hold",
    ) -> 'LinkSegment':
        """
        Convert a selected S-domain scalar response into a LinkSegment for debug.

        This is intentionally a quick diagnostic path, not the formal COM
        channel conversion. It helps inspect whether an Sdd block has suspicious
        time-domain behavior before it is used in a full COM path.

        Parameters
        ----------
        cfg:
            LinkConfig defining the debug FFT/time grid.
        response:
            Scalar response selected from this Sdd model.
        gamma_src:
            Source reflection coefficient used only when response="h21".
        gamma_load:
            Load reflection coefficient used only when response="h21".
        dc:
            Missing-DC debug assumption. "hold" prepends H(0)=H(f_min), "skrf"
            uses SparamModel.extrapolated_to_dc(), and "error" raises if DC is
            absent.
        """
        if np.isclose(self.freqs[0], 0.0):
            freqs = self.freqs
            H = self._debug_scalar_tf(response, gamma_src=gamma_src, gamma_load=gamma_load)
            linksegment_dc: Literal["error", "hold"] = "error"
        elif dc == "hold":
            freqs = self.freqs
            H = self._debug_scalar_tf(response, gamma_src=gamma_src, gamma_load=gamma_load)
            linksegment_dc = "hold"
        elif dc == "skrf":
            model = self.extrapolated_to_dc()
            freqs = model.freqs
            H = model._debug_scalar_tf(response, gamma_src=gamma_src, gamma_load=gamma_load)
            linksegment_dc = "error"
        elif dc == "error":
            raise ValueError("SparamModel debug time plot requires DC; use dc='hold' or dc='skrf'.")
        else:
            raise ValueError('dc must be "hold", "skrf", or "error".')

        return LinkSegment.from_tf(freqs, H, cfg, dc=linksegment_dc)

    def plot_ir(
        self,
        cfg: 'LinkConfig',
        response: Literal["sdd11", "sdd12", "sdd21", "sdd22", "h21"] = "sdd21",
        ax: Optional[Axes] = None,
        save_path: str = "",
        x_unit: Literal["ui", "ns"] = "ui",
        x_origin: Literal["start", "max"] = "max",
        xlim_ui: Optional[tuple[float, float]] = None,
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
        dc: Literal["hold", "skrf", "error"] = "hold",
        label: str | None = None,
    ) -> Axes:
        """
        Debug-plot the time-domain IR of one S-domain scalar response.

        Parameters
        ----------
        cfg:
            LinkConfig defining the debug FFT/time grid.
        response:
            "sdd11", "sdd12", "sdd21", "sdd22", or "h21".
        ax:
            Optional matplotlib Axes.
        save_path:
            Optional output path.
        x_unit:
            "ui" or "ns".
        x_origin:
            "start" or "max".
        xlim_ui:
            Optional UI x-limits.
        gamma_src:
            Source reflection coefficient used only when response="h21".
        gamma_load:
            Load reflection coefficient used only when response="h21".
        dc:
            Missing-DC debug assumption: "hold", "skrf", or "error".
        label:
            Optional curve label. Useful when plotting multiple responses on
            the same Axes.
        """
        seg = self._debug_LinkSegment(
            cfg,
            response=response,
            gamma_src=gamma_src,
            gamma_load=gamma_load,
            dc=dc,
        )
        return seg.plot_ir(ax=ax, save_path=save_path, x_unit=x_unit, x_origin=x_origin, xlim_ui=xlim_ui, label=label)

    def plot_sbr(
        self,
        cfg: 'LinkConfig',
        response: Literal["sdd11", "sdd12", "sdd21", "sdd22", "h21"] = "sdd21",
        ax: Optional[Axes] = None,
        save_path: str = "",
        x_unit: Literal["ui", "ns"] = "ui",
        x_origin: Literal["start", "max"] = "max",
        xlim_ui: Optional[tuple[float, float]] = None,
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
        dc: Literal["hold", "skrf", "error"] = "hold",
        label: str | None = None,
        normalize_main_cursor: bool = False,
    ) -> Axes:
        """
        Debug-plot the SBR of one S-domain scalar response.

        Parameters are the same as plot_ir(), with normalize_main_cursor passed
        through to LinkSegment.plot_sbr(). This is a diagnostic convenience and
        does not replace the formal COM pulse/SBR path.
        """
        seg = self._debug_LinkSegment(
            cfg,
            response=response,
            gamma_src=gamma_src,
            gamma_load=gamma_load,
            dc=dc,
        )
        return seg.plot_sbr(
            ax=ax,
            save_path=save_path,
            x_unit=x_unit,
            x_origin=x_origin,
            xlim_ui=xlim_ui,
            label=label,
            normalize_main_cursor=normalize_main_cursor,
        )

    # ---- immutable / copy-returning operations ----
    def cascade(self, other: 'SparamModel') -> 'SparamModel':
        """
        Return a new model by cascading two Sdd two-port networks.

        The physical order is:
            self -> other

        Both models must already use the same frequency grid and reference
        impedance. Resample / renormalize explicitly before cascade.
        """
        self.validate_compatible_sparam(other)
        cascaded_network = self.network ** other.network
        return type(self).from_network(cascaded_network, mode="sdd", z0=cascaded_network.z0)

    def renormalized(self, z0_new: Union[float, np.ndarray], s_def: SdefT | None = None) -> 'SparamModel':
        """
        Return a copy with S-parameters renormalized to a new reference impedance.

        This changes the S-parameter values, not only the Network.z0 metadata.
        Internally this wraps skrf.Network.renormalize(), which is an in-place
        skrf API. SparamModel deliberately applies it to a copied Network and
        returns a new SparamModel so the original measurement object remains
        unchanged.

        Parameters
        ----------
        z0_new:
            New reference impedance for the internal Sdd two-port. In this
            class, z0 is differential reference impedance.
        s_def:
            scikit-rf wave definition: "power", "pseudo", "traveling", or None.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        model.network.renormalize(cast(Any, z0_new), s_def=s_def)
        model.network = model.validate_network(model.network)
        return model

    def resampled(
        self,
        freqs: np.ndarray,
        basis: str = "s",
        coords: str = "cart",
        kind: str | None = None,
        dc_method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        dc_kind: str = "linear",
        dc_coords: str = "cart",
    ) -> 'SparamModel':
        """
        Return a copy sampled on the requested grid within the measured span.

        If the requested grid starts below the measured low-frequency point,
        the copy first performs DC extrapolation. The returned model only keeps
        requested points up to the measured f_stop; high-frequency S-parameter
        extrapolation is intentionally not performed here.

        This method uses scikit-rf interpolation on a copied Network. The
        original object remains unchanged so the raw measurement grid and the
        COM processing grid can be compared during debugging.

        Parameters
        ----------
        freqs:
            Requested frequency grid in Hz. Returned points are limited to the
            available measured span after optional DC extrapolation.
        basis:
            scikit-rf interpolation basis.
        coords:
            scikit-rf interpolation coordinate system.
        kind:
            scikit-rf interpolation kind.
        dc_method:
            DC extrapolation method. Only "skrf" is currently implemented.
        dc_sparam:
            Optional DC S-parameter value passed to skrf.
        dc_kind:
            Interpolation kind used by skrf DC extrapolation.
        dc_coords:
            Coordinate system used by skrf DC extrapolation.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        freqs = model.validate_resample_freqs(freqs)

        if freqs[0] < model.freqs[0]:
            if dc_method != "skrf":
                raise NotImplementedError('Only dc_method="skrf" is implemented for DC extrapolation.')
            model.network = model.network.extrapolate_to_dc(
                dc_sparam=dc_sparam,
                kind=dc_kind,
                coords=dc_coords,
            )
            model.network = model.validate_network(model.network)

        f_stop = model.freqs[-1]
        freqs_inband = freqs[freqs <= f_stop]
        if len(freqs_inband) < 2:
            raise ValueError("resampled() target grid must contain at least two in-band frequency points.")

        if freqs_inband[0] < model.freqs[0]:
            raise ValueError("resampled() target grid starts below the available frequency span after DC handling.")

        model.network = model.network.interpolate(freqs_inband, basis=basis, coords=coords, kind=kind)
        model.network = model.validate_network(model.network)
        return model

    def extrapolated_to_dc(
        self,
        method: str = "skrf",
        dc_sparam: np.ndarray | None = None,
        kind: str = "linear",
        coords: str = "cart",
    ) -> 'SparamModel':
        """
        Return a copy with a DC point added when the measurement lacks DC.

        This wraps skrf.Network.extrapolate_to_dc() on a copied Network. It is
        copy-returning for the same reason as renormalized(): DC handling is a
        modeling assumption, and preserving the original measured data is useful
        for validation and comparison.

        Parameters
        ----------
        method:
            DC extrapolation method. Only "skrf" is currently implemented.
        dc_sparam:
            Optional DC S-parameter value passed to skrf.
        kind:
            Interpolation kind used by skrf.
        coords:
            Coordinate system used by skrf.
        """
        model = type(self).from_network(self.network.copy(), mode="sdd", z0=self.network.z0)
        if np.isclose(model.freqs[0], 0.0):
            return model

        if method != "skrf":
            raise NotImplementedError('Only method="skrf" is implemented for DC extrapolation.')

        model.network = model.network.extrapolate_to_dc(
            dc_sparam=dc_sparam,
            kind=kind,
            coords=coords,
        )
        model.network = model.validate_network(model.network)
        return model

    def voltage_transfer_function(
        self,
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
    ) -> np.ndarray:
        """
        Compute the terminated voltage transfer function H21(f).

        Reference:
        - IEEE 802.3 Annex 93A.1.3, Eq. 93A-18.

        gamma_src and gamma_load are the reflection coefficients seen at port 1
        and port 2. With matched terminations, both are zero and H21(f)=Sdd21(f).
        """
        gamma_src = np.asarray(gamma_src, dtype=complex)
        gamma_load = np.asarray(gamma_load, dtype=complex)

        delta_s = self.sdd11 * self.sdd22 - self.sdd12 * self.sdd21
        denom = (
            1
            - self.sdd11 * gamma_src
            - self.sdd22 * gamma_load
            + gamma_src * gamma_load * delta_s
        )
        if np.any(np.isclose(denom, 0.0)):
            raise ZeroDivisionError("H21 denominator is close to zero.")

        return self.sdd21 * (1 - gamma_src) * (1 + gamma_load) / denom

    # ---- derived scalar conversion ----
    def to_LinkSegment(
        self,
        cfg: 'LinkConfig',
        gamma_src: Union[float, complex, np.ndarray] = 0.0,
        gamma_load: Union[float, complex, np.ndarray] = 0.0,
    ) -> 'LinkSegment':
        """
        Build a scalar LinkSegment from the terminated voltage transfer H21(f).

        Contract:
        - self remains in its current S-parameter domain grid, normally the
          aligned measured-domain grid used by COM path construction.
        - H21(f) is computed on that S-parameter grid first.
        - LinkSegment.from_tf() then owns scalar transfer-function resampling
          and high-frequency extension to cfg.f_nyq.

        Flow:
        1. compute H21(f) with impedance mismatch using Eq. 93A-18 on self.freqs
        2. build LinkSegment from scalar H21(f)
        3. let LinkSegment.from_tf() resample / extend the scalar transfer
           function to cfg.freqs / cfg.f_nyq using the project TF rule
        """
        H21 = self.voltage_transfer_function(gamma_src=gamma_src, gamma_load=gamma_load)
        return LinkSegment.from_tf(self.freqs, H21, cfg)

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

