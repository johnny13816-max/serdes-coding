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
    tap_rel_th: float = 0.0,
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
    tap_rel_th:
        Relative tap threshold versus the largest absolute tap.
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
    tap_rel_th: float = 0.0,
    max_taps: Optional[int] = None
) -> np.ndarray:
    """
    Return FIR taps after threshold and count pruning.

    Parameters
    ----------
    fir:
        1D FIR tap coefficients.
    tap_rel_th:
        Keep taps with abs(tap) >= tap_rel_th * max(abs(fir)).
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

    tap_rel_th = float(tap_rel_th)
    if not np.isfinite(tap_rel_th) or tap_rel_th < 0:
        raise ValueError("tap_rel_th must be finite and non-negative.")

    if max_taps is not None:
        if not isinstance(max_taps, (int, np.integer)) or max_taps <= 0:
            raise ValueError("max_taps must be a positive integer or None.")
        max_taps = int(max_taps)

    max_abs = np.max(np.abs(fir))
    if max_abs == 0.0:
        return np.array([], dtype=float)

    keep = np.abs(fir) >= tap_rel_th * max_abs

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
    def uniform(cls):
        pass

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
        Shift the x grid in place by idx_shift samples and return self.

        Probability mass values are unchanged. Only st_idx / x_st move:
            Y = X + idx_shift * dx

        Parameters
        ----------
        idx_shift:
            Integer number of grid samples to shift.
        """
        idx_shift = self._validate_st_idx(idx_shift)
        self.st_idx += idx_shift
        self.x_st = self.st_idx * self.dx
        return self

    def scale_x(self, scale: float) -> 'Pmf1D':
        """
        Scale the x axis in place and return self.

        This models:
            Y = scale * X

        This is pure x-axis scaling. No projection to a shared grid is
        performed.

        Parameters
        ----------
        scale:
            X-axis scale factor. Negative values mirror the distribution.
        """
        scale = self._validate_scale(scale)

        if scale == 0.0:
            self.dx = self.dx
            self.st_idx = 0
            self.x_st = 0.0
            self.pmf = np.array([np.sum(self.pmf)], dtype=float)
            return self

        if scale < 0.0:
            self.st_idx = -(self.st_idx + len(self.pmf) - 1)
            self.pmf = self.pmf[::-1].copy()

        self.dx *= abs(scale)
        self.x_st = self.st_idx * self.dx
        self.pmf = self._validate_pmf(self.pmf)
        return self

    def scale_x_to_grid(self, scale: float, dx_ref: float) -> 'Pmf1D':
        """
        Scale X and project the result to dx_ref in place.

        This is the FIR-friendly operation:
            1. Y = scale * X
            2. deposit Y's probability mass onto a shared dx_ref grid

        Parameters
        ----------
        scale:
            X-axis scale factor.
        dx_ref:
            Shared target grid spacing after scaling.
        """
        scale = self._validate_scale(scale)
        dx_ref = self._validate_dx(dx_ref)

        if scale == 0.0:
            self.dx = dx_ref
            self.st_idx = 0
            self.x_st = 0.0
            self.pmf = np.array([np.sum(self.pmf)], dtype=float)
            return self

        st_idx, pmf = self.snap_to_grid(scale * self.x, self.pmf, dx_ref)
        self.dx = dx_ref
        self.st_idx = st_idx
        self.x_st = self.st_idx * self.dx
        self.pmf = self._validate_pmf(pmf)
        return self

    def resample_dx(self, dx_new: float, *, name: Optional[str]=None) -> 'Pmf1D':
        """
        Project self to a new x-grid spacing in place and return self.

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
        self.dx = dx_new
        self.st_idx = st_idx
        self.x_st = self.st_idx * self.dx
        self.pmf = self._validate_pmf(pmf)
        if name is not None:
            self.name = name
        return self

    def fir_filter(
        self,
        fir: np.ndarray,
        *,
        keep_mass: float = float(1-1e-5),
        dx_ref: Optional[float] = None,
        tap_rel_th: float = 0.0,
        max_taps: Optional[int] = None,
        name: Optional[str] = None,
    ) -> 'Pmf1D':
        """
        Apply FIR filtering to this PMF in place and return self.

        If self represents the symbol distribution X, this method replaces it
        with the distribution of:
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
        tap_rel_th:
            Relative tap threshold versus the largest absolute tap.
        max_taps:
            Maximum number of strongest taps to keep.
        name:
            Optional name override after filtering.
        """
        coeff = _prune_fir_coeff(fir, tap_rel_th=tap_rel_th, max_taps=max_taps)
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
                term = base.copy().scale_x_to_grid(c, dx_ref)
                out_pmf = np.convolve(out_pmf, term.pmf)
                out_st_idx += term.st_idx

                if keep_mass < 1.0:
                    tmp = Pmf1D(dx=dx_ref, st_idx=out_st_idx, pmf=out_pmf, unit=self.unit)
                    _truncate_keep_mass(tmp, keep_mass=keep_mass)
                    out_st_idx = tmp.st_idx
                    out_pmf = tmp.pmf

            filtered = Pmf1D(
                dx=dx_ref,
                st_idx=out_st_idx,
                pmf=out_pmf,
                unit=self.unit,
                name=self.name if name is None else name,
            )

        self.dx = filtered.dx
        self.st_idx = filtered.st_idx
        self.x_st = filtered.x_st
        self.pmf = filtered.pmf
        self.unit = filtered.unit
        self.name = filtered.name
        return self

    def combine(self, other: 'Pmf1D', *, name: Optional[str]=None) -> 'Pmf1D':
        """
        Combine another independent PMF into self by convolution.

        If self represents X and other represents Y, this method replaces self
        with the distribution of:
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

        self.pmf = self._validate_pmf(np.convolve(self.pmf, other.pmf))
        self.st_idx += other.st_idx
        self.x_st = self.st_idx * self.dx
        if name is not None:
            self.name = name
        return self
