"""Power spectral density utility types.

This module owns continuous- and sampled-domain PSD containers. It accepts
LinkConfig-compatible grids structurally, but deliberately does not import the
link-response layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Optional, Union

import numpy as np

if TYPE_CHECKING:
    from matplotlib.axes import Axes


def _freqs_equal(
    f1: np.ndarray,
    f2: np.ndarray,
    rtol: float = 1e-9,
    atol: float = 1e-6,
) -> bool:
    """Return whether two frequency axes agree within numerical tolerance."""
    f1 = np.asarray(f1, dtype=float)
    f2 = np.asarray(f2, dtype=float)
    return f1.shape == f2.shape and np.allclose(f1, f2, rtol=rtol, atol=atol)


def _validate_freqs(
    freqs: np.ndarray,
    require_uniform: bool = False,
    expected_stop: float | None = None,
    rtol: float = 1e-9,
    atol: float = 1e-15,
) -> np.ndarray:
    """Validate a non-negative, strictly increasing frequency axis."""
    freqs = np.asarray(freqs, dtype=float)
    if freqs.ndim != 1:
        raise ValueError("freqs must be a 1D array.")
    if len(freqs) < 2:
        raise ValueError("freqs must contain at least two points.")
    if not np.all(np.isfinite(freqs)):
        raise ValueError("freqs contains non-finite values.")
    if freqs[0] < 0:
        raise ValueError("freqs must be non-negative.")
    if not np.all(np.diff(freqs) > 0):
        raise ValueError("freqs must be strictly increasing.")
    if require_uniform:
        df = np.diff(freqs)
        if not np.allclose(df, df[0], rtol=rtol, atol=atol):
            raise ValueError("freqs must be uniformly spaced.")
    if expected_stop is not None and not np.isclose(freqs[-1], expected_stop, rtol=rtol, atol=atol):
        raise ValueError("freqs[-1] must equal expected_stop within numerical tolerance.")
    return freqs


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
        self.freqs = _validate_freqs(self.freqs)
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
            _validate_freqs(freqs, require_uniform=True)
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
        freqs = _validate_freqs(freqs)
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
        freqs = _validate_freqs(freqs)
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
        freqs = _validate_freqs(freqs)
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
        cfg: Any,
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
        if not _freqs_equal(self.freqs, response.freqs):
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

__all__ = ["ContinuousPSD", "OneSidePSD", "SampledPSD"]
