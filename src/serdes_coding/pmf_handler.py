from __future__ import annotations

import numpy as np
from typing import Optional
from math import erf, sqrt

# helpers
def fir_filtered_pmf(
    p: Pmf1D,
    fir: np.ndarray,
    *,
    keep_mass: float = float(1-1e-5),
    tap_abs_th: float = 0.0,
    max_taps: Optional[int] = None,
    name: Optional[str] = None
) -> Pmf1D:
    """
    Return a FIR-filtered copy of p.

    Parameters
    ----------
    p:
        Input PMF representing the symbol distribution X.
    fir:
        1D FIR tap coefficients.
    keep_mass:
        Target probability mass kept after optional truncation.
    tap_abs_th:
        Absolute tap threshold. Keep taps with abs(tap) >= tap_abs_th.
    max_taps:
        Maximum number of strongest taps to keep.
    name:
        Optional name for the output PMF.
    """
    pass

def _truncate_keep_mass(p: Pmf1D, *, keep_mass: float) -> Pmf1D:
    """
    Return p truncated to keep the requested probability mass.

    Parameters
    ----------
    p:
        Input PMF to truncate.
    keep_mass:
        Probability mass target to keep, usually close to 1.
    """
    if not isinstance(p, Pmf1D):
        raise TypeError("p must be a Pmf1D.")

    keep_mass = float(keep_mass)
    if not np.isfinite(keep_mass) or keep_mass <= 0.0 or keep_mass > 1.0:
        raise ValueError("keep_mass must be finite and in (0, 1].")

    if keep_mass == 1.0:
        return p

    tail = 0.5 * (1.0 - keep_mass)
    cdf = p.cdf

    i0 = int(np.searchsorted(cdf, tail, side="left"))
    i1 = int(np.searchsorted(cdf, 1.0 - tail, side="left"))
    i0 = max(0, min(i0, len(p.pmf) - 1))
    i1 = max(i0, min(i1, len(p.pmf) - 1))

    p.pmf = Pmf1D._validate_mass(p.pmf[i0:i1 + 1])
    p.pmf = Pmf1D._validate_pmf(p.pmf / np.sum(p.pmf))
    p.st_idx += i0
    p.x_st = p.st_idx * p.dx
    return p

def _prune_fir_coeff(
    fir: np.ndarray,
    *,
    tap_abs_th: float = 0.0,
    max_taps: Optional[int] = None
) -> np.ndarray:
    """
    Return FIR taps after threshold and count pruning.

    Parameters
    ----------
    fir:
        1D FIR tap coefficients.
    tap_abs_th:
        Absolute tap threshold. Keep taps with abs(tap) >= tap_abs_th.
    max_taps:
        Maximum number of strongest taps to keep.
    """
    fir = np.asarray(fir, dtype=float)

    if fir.ndim != 1:
        raise ValueError("fir must be a 1D array.")

    if len(fir) == 0:
        raise ValueError("fir must contain at least one tap.")

    if not np.all(np.isfinite(fir)):
        raise ValueError("fir contains non-finite values.")

    tap_abs_th = float(tap_abs_th)
    if not np.isfinite(tap_abs_th) or tap_abs_th < 0:
        raise ValueError("tap_abs_th must be finite and non-negative.")

    if max_taps is not None:
        if not isinstance(max_taps, (int, np.integer)) or max_taps <= 0:
            raise ValueError("max_taps must be a positive integer or None.")
        max_taps = int(max_taps)

    max_abs = np.max(np.abs(fir))
    if max_abs == 0.0:
        return np.array([], dtype=float)

    keep = np.abs(fir) >= tap_abs_th

    if max_taps is not None and np.count_nonzero(keep) > max_taps:
        kept_indices = np.flatnonzero(keep)
        strongest = kept_indices[np.argsort(np.abs(fir[kept_indices]))[-max_taps:]]
        keep = np.zeros_like(keep, dtype=bool)
        keep[np.sort(strongest)] = True

    return fir[keep]

class Pmf1D:
    """
    One-dimensional probability mass function on a uniform x grid.

    The x-axis is represented by:
        x[k] = (st_idx + k) * dx

    Keep only dx, st_idx, and pmf in memory. The explicit x array is generated
    on demand by the x property.
    """

    def __init__(self, dx: float, st_idx: int, pmf: np.ndarray, unit: str = "", name: str = ""):
        """
        Build a PMF on a uniform grid.

        Parameters
        ----------
        dx:
            X-axis grid spacing.
        st_idx:
            Integer grid index of pmf[0].
        pmf:
            1D probability mass array; must be non-negative and sum to 1.
        unit:
            Optional x-axis unit label.
        name:
            Optional PMF name for debug / plotting.
        """
        self.dx = self._validate_dx(dx)
        self.st_idx = self._validate_st_idx(st_idx)
        self.x_st = self.st_idx * self.dx
        self.pmf = self._validate_pmf(pmf)
        self.unit = unit
        self.name = name

    @property
    def x(self) -> np.ndarray:
        "Don't save 'x' to save memory."
        return self.x_st + np.arange(len(self.pmf)) * self.dx

    @property
    def cdf(self) -> np.ndarray:
        "Don't save CDF to avoid cache invalidation in in-place operations."
        return np.cumsum(self.pmf)

    # --------------------------------
    # validation
    # --------------------------------
    @staticmethod
    def _validate_dx(dx: float) -> float:
        """
        Validate x-axis grid spacing.

        Parameters
        ----------
        dx:
            Candidate grid spacing.
        """
        dx = float(dx)
        if not np.isfinite(dx) or dx <= 0:
            raise ValueError("dx must be a finite positive value.")
        return dx

    @staticmethod
    def _validate_st_idx(st_idx: int) -> int:
        """
        Validate integer start index.

        Parameters
        ----------
        st_idx:
            Candidate integer grid index.
        """
        if not isinstance(st_idx, (int, np.integer)):
            raise TypeError("st_idx must be an integer grid index.")
        return int(st_idx)

    @staticmethod
    def _validate_mass(mass: np.ndarray) -> np.ndarray:
        """
        Validate non-negative mass values without requiring sum == 1.

        Parameters
        ----------
        mass:
            Candidate 1D non-negative mass array.
        """
        mass = np.asarray(mass, dtype=float)

        if mass.ndim != 1:
            raise ValueError("mass must be a 1D array.")

        if len(mass) == 0:
            raise ValueError("mass must contain at least one point.")

        if not np.all(np.isfinite(mass)):
            raise ValueError("mass contains non-finite values.")

        if np.any(mass < 0):
            raise ValueError("mass must not contain negative probability mass.")

        return mass

    @staticmethod
    def _validate_pmf(pmf: np.ndarray, rtol: float = 1e-12, atol: float = 1e-15) -> np.ndarray:
        """
        Validate a complete probability mass function.

        Parameters
        ----------
        pmf:
            Candidate 1D probability mass array.
        rtol:
            Relative tolerance for sum(pmf) == 1.
        atol:
            Absolute tolerance for sum(pmf) == 1.
        """
        pmf = Pmf1D._validate_mass(pmf)

        total_mass = np.sum(pmf)
        if not np.isclose(total_mass, 1.0, rtol=rtol, atol=atol):
            raise ValueError(f"pmf must sum to 1. Got sum={total_mass}.")

        return pmf

    @staticmethod
    def _validate_scale(scale: float) -> float:
        """
        Validate x-axis scale factor.

        Parameters
        ----------
        scale:
            Candidate finite scale factor.
        """
        scale = float(scale)
        if not np.isfinite(scale):
            raise ValueError("scale must be finite.")
        return scale

    @staticmethod
    def snap_to_grid(x: np.ndarray, mass: np.ndarray, dx: float) -> tuple[int, np.ndarray]:
        """
        Deposit point masses at arbitrary x values onto a uniform dx grid.

        Each mass is linearly split between the two nearest grid points. This
        preserves total probability mass and avoids nearest-grid stair-step
        artifacts when projecting a distribution onto a chosen grid.

        Parameters
        ----------
        x:
            1D locations of point masses.
        mass:
            1D mass values at x; must be non-negative.
        dx:
            Target grid spacing.
        """
        dx = Pmf1D._validate_dx(dx)
        x = np.asarray(x, dtype=float)
        mass = np.asarray(mass, dtype=float)

        if x.ndim != 1 or mass.ndim != 1:
            raise ValueError("x and mass must be 1D arrays.")

        if x.shape != mass.shape:
            raise ValueError("x and mass must have the same shape.")

        if len(x) == 0:
            raise ValueError("x and mass must contain at least one point.")

        if not np.all(np.isfinite(x)):
            raise ValueError("x contains non-finite values.")

        mass = Pmf1D._validate_mass(mass)

        grid_pos = x / dx
        st_idx = int(np.floor(np.min(grid_pos)))
        end_idx = int(np.ceil(np.max(grid_pos)))
        out = np.zeros(end_idx - st_idx + 1, dtype=float)

        lo = np.floor(grid_pos).astype(int)
        frac = grid_pos - lo

        rel_lo = lo - st_idx
        np.add.at(out, rel_lo, mass * (1.0 - frac))

        hi_mask = frac > 0.0
        rel_hi = rel_lo[hi_mask] + 1
        np.add.at(out, rel_hi, mass[hi_mask] * frac[hi_mask])

        return st_idx, out

    # --------------------------------
    # constructors
    # --------------------------------
    @classmethod
    def uniform(cls, delta: float, pmf_cfg: object, *, unit: str = "volt", name: str = "") -> 'Pmf1D':
        """
        Build a zero-mean uniform PMF over [-delta/2, delta/2).

        This constructor uses bin-integrated probability mass, consistent with
        gaussian_from_bin_integral(). It is intended for ADC quantization noise
        where the continuous quantization error is uniform over one step.

        Parameters
        ----------
        delta:
            Uniform distribution width. For quantization noise this is the ADC
            quantization step.
        pmf_cfg:
            PMF runtime/config object with a ``dy`` attribute used as the
            amplitude grid spacing.
        unit:
            Optional x-axis unit label.
        name:
            Optional PMF name for debug / plotting.
        """
        delta = float(delta)
        if not np.isfinite(delta) or delta <= 0:
            raise ValueError("delta must be a finite positive value.")

        if not hasattr(pmf_cfg, "dy"):
            raise TypeError("pmf_cfg must provide a dy attribute.")
        dx = cls._validate_dx(getattr(pmf_cfg, "dy"))

        half = 0.5 * delta
        st_idx = int(np.floor((-half - 0.5 * dx) / dx))
        end_idx = int(np.ceil((half + 0.5 * dx) / dx))
        idx = np.arange(st_idx, end_idx + 1)
        x = idx * dx

        bin_lo = x - 0.5 * dx
        bin_hi = x + 0.5 * dx
        overlap = np.maximum(0.0, np.minimum(bin_hi, half) - np.maximum(bin_lo, -half))
        keep = overlap > 0.0
        if not np.any(keep):
            raise RuntimeError("Uniform PMF construction produced no nonzero bins.")

        idx = idx[keep]
        pmf = overlap[keep] / delta
        pmf = pmf / np.sum(pmf)

        return cls(
            dx=dx,
            st_idx=int(idx[0]),
            pmf=pmf,
            unit=unit,
            name=name or "uniform",
        )

    @classmethod
    def gaussian(
        cls,
        mu: float,
        sigma: float,
        dx: float,
        *,
        n_sigma: float = 8.0,
        unit: str = "",
        name: str = "",
    ) -> 'Pmf1D':
        """
        Build a Gaussian PMF using bin-integrated probability mass.

        Parameters
        ----------
        mu:
            Gaussian mean.
        sigma:
            Gaussian standard deviation.
        dx:
            X-axis grid spacing.
        n_sigma:
            Truncation half-width in sigma units.
        unit:
            Optional x-axis unit label.
        name:
            Optional PMF name for debug / plotting.
        """
        return cls.gaussian_from_bin_integral(
            mu=mu,
            sigma=sigma,
            dx=dx,
            n_sigma=n_sigma,
            unit=unit,
            name=name,
        )

    @classmethod
    def gaussian_from_pdf_sample(
        cls,
        mu: float,
        sigma: float,
        dx: float,
        *,
        n_sigma: float = 8.0,
        unit: str = "",
        name: str = "",
    ) -> 'Pmf1D':
        """
        Build a Gaussian PMF by sampling the PDF on grid points.

        Parameters
        ----------
        mu:
            Gaussian mean.
        sigma:
            Gaussian standard deviation.
        dx:
            X-axis grid spacing.
        n_sigma:
            Truncation half-width in sigma units.
        unit:
            Optional x-axis unit label.
        name:
            Optional PMF name for debug / plotting.
        """
        mu = float(mu)
        sigma = float(sigma)
        if not np.isfinite(sigma) or sigma <= 0:
            raise ValueError("sigma must be a finite positive value.")

        dx = cls._validate_dx(dx)
        n_sigma = float(n_sigma)
        if not np.isfinite(n_sigma) or n_sigma <= 0:
            raise ValueError("n_sigma must be a finite positive value.")

        st_idx = int(np.floor((mu - n_sigma * sigma) / dx))
        end_idx = int(np.ceil((mu + n_sigma * sigma) / dx))
        x = np.arange(st_idx, end_idx + 1) * dx
        pmf = np.exp(-0.5 * ((x - mu) / sigma) ** 2)
        pmf = pmf / np.sum(pmf)
        return cls(dx=dx, st_idx=st_idx, pmf=pmf, unit=unit, name=name)

    @classmethod
    def gaussian_from_bin_integral(
        cls,
        mu: float,
        sigma: float,
        dx: float,
        *,
        n_sigma: float = 8.0,
        unit: str = "",
        name: str = "",
    ) -> 'Pmf1D':
        """
        Build a Gaussian PMF by integrating probability over each grid bin.

        Parameters
        ----------
        mu:
            Gaussian mean.
        sigma:
            Gaussian standard deviation.
        dx:
            X-axis grid spacing.
        n_sigma:
            Truncation half-width in sigma units.
        unit:
            Optional x-axis unit label.
        name:
            Optional PMF name for debug / plotting.
        """
        mu = float(mu)
        sigma = float(sigma)
        if not np.isfinite(sigma) or sigma <= 0:
            raise ValueError("sigma must be a finite positive value.")

        dx = cls._validate_dx(dx)
        n_sigma = float(n_sigma)
        if not np.isfinite(n_sigma) or n_sigma <= 0:
            raise ValueError("n_sigma must be a finite positive value.")

        st_idx = int(np.floor((mu - n_sigma * sigma) / dx))
        end_idx = int(np.ceil((mu + n_sigma * sigma) / dx))
        x = np.arange(st_idx, end_idx + 1) * dx

        z_hi = (x + 0.5 * dx - mu) / (sigma * sqrt(2.0))
        z_lo = (x - 0.5 * dx - mu) / (sigma * sqrt(2.0))
        cdf_hi = 0.5 * (1.0 + np.vectorize(erf)(z_hi))
        cdf_lo = 0.5 * (1.0 + np.vectorize(erf)(z_lo))
        pmf = cdf_hi - cdf_lo
        pmf = pmf / np.sum(pmf)
        return cls(dx=dx, st_idx=st_idx, pmf=pmf, unit=unit, name=name)

    @classmethod
    def multi_dirac(
        cls,
        values: np.ndarray,
        probs: Optional[np.ndarray] = None,
        *,
        dx: float,
        unit: str = "",
        name: str = "",
    ) -> 'Pmf1D':
        """
        Build a PMF from multiple Dirac masses.

        Parameters
        ----------
        values:
            1D x locations of Dirac masses.
        probs:
            Probability mass at each value. If None, values are equally likely.
        dx:
            X-axis grid spacing.
        unit:
            Optional x-axis unit label.
        name:
            Optional PMF name for debug / plotting.
        """
        dx = cls._validate_dx(dx)
        values = np.asarray(values, dtype=float)

        if values.ndim != 1:
            raise ValueError("values must be a 1D array.")

        if len(values) == 0:
            raise ValueError("values must contain at least one point.")

        if not np.all(np.isfinite(values)):
            raise ValueError("values contains non-finite values.")

        if probs is None:
            probs = np.full(len(values), 1.0 / len(values), dtype=float)
        else:
            probs = cls._validate_pmf(probs)
            if len(probs) != len(values):
                raise ValueError("probs must have the same length as values.")

        st_idx, pmf = cls.snap_to_grid(values, probs, dx)
        pmf = pmf / np.sum(pmf)
        return cls(dx=dx, st_idx=st_idx, pmf=pmf, unit=unit, name=name)

    # --------------------------------
    # public methods
    # --------------------------------
    def copy(self, *, name: Optional[str]=None) -> 'Pmf1D':
        """
        Return a deep copy of this PMF.

        Parameters
        ----------
        name:
            Optional name override for the copied PMF.
        """
        return Pmf1D(
            dx=self.dx,
            st_idx=self.st_idx,
            pmf=self.pmf.copy(),
            unit=self.unit,
            name=self.name if name is None else name,
        )

    def quantile(self, prob: float) -> float:
        """
        Return the x value where CDF first reaches prob.

        Parameters
        ----------
        prob:
            Target cumulative probability in [0, 1].
        """
        prob = float(prob)
        if not np.isfinite(prob) or prob < 0.0 or prob > 1.0:
            raise ValueError("prob must be finite and in [0, 1].")

        idx = int(np.searchsorted(self.cdf, prob, side="left"))
        idx = min(idx, len(self.pmf) - 1)
        return float(self.x[idx])

    def shift_x(self, idx_shift: int) -> 'Pmf1D':
        """
        Return a copy with the x grid shifted by idx_shift samples.

        Probability mass values are unchanged. Only st_idx / x_st move:
            Y = X + idx_shift * dx

        Parameters
        ----------
        idx_shift:
            Integer number of grid samples to shift.
        """
        idx_shift = self._validate_st_idx(idx_shift)
        return Pmf1D(
            dx=self.dx,
            st_idx=self.st_idx + idx_shift,
            pmf=self.pmf.copy(),
            unit=self.unit,
            name=self.name,
        )

    def scale_x(
        self,
        scale: float,
        *,
        keep_dx: bool = False,
        dx_ref: Optional[float] = None,
    ) -> 'Pmf1D':
        """
        Return a copy with the x axis scaled.

        This models:
            Y = scale * X

        By default this is pure x-axis scaling and dx changes by abs(scale).
        With keep_dx=True, probability mass is projected onto dx_ref so the
        output remains on a shared grid. This is the FIR-friendly mode.

        Parameters
        ----------
        scale:
            X-axis scale factor. Negative values mirror the distribution.
        keep_dx:
            If True, deposit scaled probability mass onto dx_ref.
        dx_ref:
            Shared target grid spacing when keep_dx=True. Defaults to current
            self.dx.
        """
        scale = self._validate_scale(scale)

        if keep_dx:
            dx_ref = self.dx if dx_ref is None else self._validate_dx(dx_ref)

            if scale == 0.0:
                return Pmf1D(
                    dx=dx_ref,
                    st_idx=0,
                    pmf=np.array([np.sum(self.pmf)], dtype=float),
                    unit=self.unit,
                    name=self.name,
                )

            st_idx, pmf = self.snap_to_grid(scale * self.x, self.pmf, dx_ref)
            return Pmf1D(
                dx=dx_ref,
                st_idx=st_idx,
                pmf=self._validate_pmf(pmf),
                unit=self.unit,
                name=self.name,
            )

        if dx_ref is not None:
            raise ValueError("dx_ref is only used when keep_dx=True.")

        if scale == 0.0:
            return Pmf1D(
                dx=self.dx,
                st_idx=0,
                pmf=np.array([np.sum(self.pmf)], dtype=float),
                unit=self.unit,
                name=self.name,
            )

        st_idx = self.st_idx
        pmf = self.pmf.copy()
        if scale < 0.0:
            st_idx = -(self.st_idx + len(self.pmf) - 1)
            pmf = pmf[::-1].copy()

        return Pmf1D(
            dx=self.dx * abs(scale),
            st_idx=st_idx,
            pmf=self._validate_pmf(pmf),
            unit=self.unit,
            name=self.name,
        )

    def resample_dx(self, dx_new: float, *, name: Optional[str]=None) -> 'Pmf1D':
        """
        Return a copy projected to a new x-grid spacing.

        This keeps the same random variable and only changes the PMF
        representation grid. Probability mass at each existing x location is
        linearly deposited onto the nearest points of the dx_new grid.

        Parameters
        ----------
        dx_new:
            New target grid spacing.
        name:
            Optional name override after resampling.
        """
        dx_new = self._validate_dx(dx_new)
        st_idx, pmf = self.snap_to_grid(self.x, self.pmf, dx_new)
        return Pmf1D(
            dx=dx_new,
            st_idx=st_idx,
            pmf=self._validate_pmf(pmf),
            unit=self.unit,
            name=self.name if name is None else name,
        )

    def fir_filter(
        self,
        fir: np.ndarray,
        *,
        keep_mass: float = float(1-1e-5),
        dx_ref: Optional[float] = None,
        tap_abs_th: float = 0.0,
        max_taps: Optional[int] = None,
        name: Optional[str] = None,
    ) -> 'Pmf1D':
        """
        Return the FIR-filtered PMF.

        If self represents the symbol distribution X, this method returns the
        distribution of:
            Y = sum_i fir[i] * X_i

        The X_i are treated as independent random variables with the original
        self distribution. Each tap-scaled PMF is projected to dx_ref before
        convolution so all terms share one representation grid.

        Parameters
        ----------
        fir:
            1D FIR tap coefficients.
        keep_mass:
            Probability mass to keep after each convolution.
        dx_ref:
            Shared grid spacing for each tap contribution. Defaults to self.dx.
        tap_abs_th:
            Absolute tap threshold. Keep taps with abs(tap) >= tap_abs_th.
        max_taps:
            Maximum number of strongest taps to keep.
        name:
            Optional name override after filtering.
        """
        coeff = _prune_fir_coeff(fir, tap_abs_th=tap_abs_th, max_taps=max_taps)
        dx_ref = self.dx if dx_ref is None else self._validate_dx(dx_ref)

        if len(coeff) == 0:
            filtered = Pmf1D(
                dx=dx_ref,
                st_idx=0,
                pmf=np.array([1.0], dtype=float),
                unit=self.unit,
                name=self.name if name is None else name,
            )
        else:
            base = self.copy()

            out_st_idx = 0
            out_pmf = np.array([1.0], dtype=float)

            for c in coeff:
                term = base.copy().scale_x(c, keep_dx=True, dx_ref=dx_ref)
                out_pmf = np.convolve(out_pmf, term.pmf)
                out_st_idx += term.st_idx

                if keep_mass < 1.0:
                    tmp = Pmf1D(dx=dx_ref, st_idx=out_st_idx, pmf=out_pmf, unit=self.unit)
                    tmp = _truncate_keep_mass(tmp, keep_mass=keep_mass)
                    out_st_idx = tmp.st_idx
                    out_pmf = tmp.pmf

            filtered = Pmf1D(
                dx=dx_ref,
                st_idx=out_st_idx,
                pmf=out_pmf,
                unit=self.unit,
                name=self.name if name is None else name,
            )

        return filtered

    def combine(self, other: 'Pmf1D', *, name: Optional[str]=None) -> 'Pmf1D':
        """
        Return the convolution with another independent PMF.

        If self represents X and other represents Y, this method returns the
        distribution of:
            Z = X + Y

        Both PMFs must already use the same dx. Use resample_dx() explicitly
        before combine() when grid alignment is required.

        Parameters
        ----------
        other:
            Independent PMF to add to self.
        name:
            Optional name override after convolution.
        """
        if not isinstance(other, Pmf1D):
            raise TypeError("other must be a Pmf1D.")

        if not np.isclose(self.dx, other.dx, rtol=1e-12, atol=1e-15):
            raise ValueError("Cannot combine PMFs with different dx. Resample to a shared grid first.")

        if self.unit and other.unit and self.unit != other.unit:
            raise ValueError("Cannot combine PMFs with different non-empty units.")

        return Pmf1D(
            dx=self.dx,
            st_idx=self.st_idx + other.st_idx,
            pmf=self._validate_pmf(np.convolve(self.pmf, other.pmf)),
            unit=self.unit or other.unit,
            name=self.name if name is None else name,
        )
