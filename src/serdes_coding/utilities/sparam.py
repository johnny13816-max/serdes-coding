"""S-parameter utility types and preprocessing operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, cast

import numpy as np
import skrf as rf

from .link import (
    LinkConfig,
    LinkSegment,
    SdefT,
    _differential_z0_from_s4p_z0,
    _s4p_to_sdd,
    _validate_s4p_port_order,
)

if TYPE_CHECKING:
    from matplotlib.axes import Axes


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

__all__ = ["SparamModel", "SparamProcessor"]
