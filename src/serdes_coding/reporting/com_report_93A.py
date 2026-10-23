"""Presentation-only reporting for IEEE 802.3 Annex 93A COM runs."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

from .com_report_common import (
    ReportFigureTools,
    plot_combined_pmf_cdf,
    plot_ct_pulse_and_samples,
    plot_discrete_sequence,
    plot_equalizer_coefficients,
    plot_impairment_bars,
    plot_link_ir,
    plot_link_sr,
    plot_link_tf,
    plot_path_h21_overview,
    plot_path_il_overview,
    plot_path_pulse_overview,
    plot_path_sbr_overview,
    plot_pmf_component,
    plot_pmf_components,
    plot_sparam_il,
    plot_sparam_sdd,
)
from .com_report_base import COMReportBase

if TYPE_CHECKING:
    from ..models.com_model_93A import (
        COMConfig,
        COMPath,
        COMSearchStatus,
        COMStatus,
    )
    from ..utilities.link import LinkSegment
    from ..utilities.pmf import Pmf1D
    from ..utilities.sparam import SparamModel


class COMReport(COMReportBase):
    """
    Plot/report orchestration for COM run results.

    Class boundary
    --------------
    COMReport owns presentation behavior that needs both COMConfig and
    COMStatus. COM and the 93A helper functions should stay focused on
    spec-defined computation; COMStatus remains the data container.
    """

    def _map_canonical_fields(self) -> dict[str, Any]:
        """Map 93A status names onto the common reporting stages."""
        return {
            "paths": self.status.paths,
            "equalizer": self.status.dfe,
            "pre_dte_impairment": None,
            "final_impairment": self.status.imp,
            "pmf": self.status.pmf,
            "mlsd": None,
            "search": self.search_status,
        }

    @staticmethod
    def _plt() -> Any:
        """Import pyplot without changing the active Matplotlib backend."""
        return ReportFigureTools.pyplot()

    @staticmethod
    def _plot_save_path(save_path: str, filename: str) -> str:
        return ReportFigureTools.output_path(save_path, filename)

    @staticmethod
    def _subplots(save_path: str, *args: Any, **kwargs: Any) -> tuple[Any, Any]:
        """
        Create a figure without changing Matplotlib's global backend.

        If save_path is provided, use a local Agg canvas so batch export does
        not require a GUI backend and does not pollute an interactive debug
        session.
        """
        return ReportFigureTools.subplots(save_path, *args, **kwargs)

    @staticmethod
    def _finish_figure(fig: Any, save_path: str) -> None:
        ReportFigureTools.finish(fig, save_path)

    @staticmethod
    def _path_display_label(idx: int, path: COMPath) -> str:
        return f"{idx}:{path.kind}"

    def _config_note(self) -> str:
        return (
            f"f_nyq={self.cfg.link.fb / 2e9:.3f} GHz, "
            f"OSR={self.cfg.link.per_ui}, "
            f"df={self.cfg.link.df / 1e6:.3f} MHz"
        )

    @staticmethod
    def _format_txfir(txfir: np.ndarray) -> str:
        values = [f"{float(x):.3g}" for x in np.asarray(txfir, dtype=float)]
        return "[" + ", ".join(values) + "]"

    @staticmethod
    def _format_freq_ghz(value: Optional[float]) -> str:
        return "None" if value is None else f"{float(value) / 1e9:.3g} GHz"

    @property
    def _f_nyq(self) -> float:
        return float(self.cfg.link.fb) / 2.0

    @staticmethod
    def _pmf_moments(pmf: Pmf1D) -> tuple[float, float]:
        return ReportFigureTools.pmf_moments(pmf)

    @staticmethod
    def _relative_gain_db(segment: LinkSegment, frequency_hz: float) -> Optional[float]:
        return ReportFigureTools.relative_gain_db(segment, frequency_hz)

    def _il_f_nyq_subtitle(self, model: SparamModel) -> str:
        if self._f_nyq < float(model.freqs[0]) or self._f_nyq > float(model.freqs[-1]):
            return "IL @ f_nyq = outside measured band"
        il_db = 20.0 * np.log10(np.maximum(np.abs(model.sdd21), np.finfo(float).tiny))
        value = float(np.interp(self._f_nyq, model.freqs, il_db))
        return f"IL @ f_nyq = {value:.2f} dB"

    def _annotate_pmf_settings(self, ax: Any, pmf: Pmf1D) -> None:
        ReportFigureTools.annotate_pmf_settings(ax, pmf, self.cfg.pmf.keep_mass)

    def _set_plot_title(self, ax: Any, title: str, subtitle: str = "") -> None:
        ReportFigureTools.title(ax, title, subtitle)

    def _annotate_config(self, ax: Any) -> None:
        ReportFigureTools.annotate_config(ax, self.cfg)

    def _annotate_imp_config(self, ax: Any) -> None:
        ReportFigureTools.annotate_impairment(ax, self.cfg)

    def _path_label(self, path_idx: int) -> str:
        path = self.status.paths[path_idx]
        return f"{path_idx:02d}_{path.kind}"

    def _path_dir(self, save_path: str, path_idx: int) -> str:
        if not save_path:
            return ""
        if path_idx == 0 and self.status.paths[path_idx].kind == "victim":
            dirname = "path_victim"
        else:
            dirname = f"path_{self._path_label(path_idx)}"
        path = Path(save_path) / dirname
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _default_freq_xlim(self, freqs: np.ndarray) -> tuple[float, float]:
        return ReportFigureTools.frequency_xlim(freqs, self.cfg.link.fb)

    @staticmethod
    def _apply_auto_ylim_from_lines(
        ax: Any,
        xlim_hz: tuple[float, float],
        *,
        x_scale: float = 1e-9,
        floor_db: float = -300.0,
        pad_ratio: float = 0.05,
    ) -> None:
        lo_x = float(xlim_hz[0]) * x_scale
        hi_x = float(xlim_hz[1]) * x_scale
        values: list[np.ndarray] = []
        for line in ax.lines:
            x = np.asarray(line.get_xdata(), dtype=float)
            y = np.asarray(line.get_ydata(), dtype=float)
            if x.shape != y.shape:
                continue
            mask = (x >= lo_x) & (x <= hi_x)
            if np.any(mask):
                values.append(y[mask])
        if not values:
            return
        visible = np.concatenate(values)
        visible = visible[np.isfinite(visible)]
        above_floor = visible[visible > float(floor_db)]
        if above_floor.size > 0:
            visible = above_floor
        if visible.size == 0:
            return
        y_min = float(np.min(visible))
        y_max = float(np.max(visible))
        if np.isclose(y_min, y_max):
            pad = max(1.0, abs(y_min) * float(pad_ratio))
        else:
            pad = (y_max - y_min) * float(pad_ratio)
        ax.set_ylim(y_min - pad, y_max + pad)

    def _plot_sparam_sdd(
        self,
        model: SparamModel,
        title: str,
        filename: str,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        subtitle: str = "",
        annotate_3db: bool = False,
        annotate_nyq: bool = False,
    ) -> Any:
        ax, _ = plot_sparam_sdd(
            self.cfg,
            model,
            save_path,
            filename=filename,
            title=title,
            subtitle=subtitle,
            xlim=xlim,
            annotate_3db=annotate_3db,
            annotate_nyq=annotate_nyq,
        )
        return ax

    def _plot_sparam_il(
        self,
        model: SparamModel,
        title: str,
        filename: str,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        subtitle: str = "",
        annotate_3db: bool = False,
    ) -> Any:
        ax, _ = plot_sparam_il(
            self.cfg,
            model,
            save_path,
            filename=filename,
            title=title,
            subtitle=subtitle,
            xlim=xlim,
            annotate_3db=annotate_3db,
        )
        return ax

    def _plot_link_tf(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
        subtitle: str = "",
        annotate_3db: bool = False,
        annotate_nyq: bool = False,
    ) -> Any:
        ax, _ = plot_link_tf(
            self.cfg,
            segment,
            save_path,
            filename=filename,
            title=title,
            subtitle=subtitle,
            xlim=xlim,
            ylim=ylim,
            annotate_3db=annotate_3db,
            annotate_nyq=annotate_nyq,
        )
        return ax

    def _plot_link_ir(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        ax, _ = plot_link_ir(
            self.cfg,
            segment,
            save_path,
            filename=filename,
            title=title,
            xlim_ui=xlim_ui,
        )
        return ax

    def _plot_pmf(
        self,
        pmf: Optional[Pmf1D],
        title: str,
        filename: str,
        save_path: str = "",
    ) -> Any:
        if pmf is None:
            raise ValueError(f"{title} PMF is not available.")
        ax, _ = plot_pmf_component(
            pmf,
            title,
            save_path,
            keep_mass=self.cfg.pmf.keep_mass,
        )
        return ax

    def _plot_discrete_time_response(
        self,
        x_ui: np.ndarray,
        y: np.ndarray,
        title: str,
        ylabel: str,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
        filename: str = "discrete_response.png",
    ) -> Any:
        x_ui = np.asarray(x_ui, dtype=float)
        y = np.asarray(y, dtype=float)
        if x_ui.shape != y.shape:
            raise ValueError("x_ui and y must have the same shape.")
        if not np.all(np.isfinite(x_ui)) or not np.all(np.isfinite(y)):
            raise ValueError("x_ui and y must contain only finite values.")

        output_file = self._plot_save_path(save_path, filename)
        created_ax = ax is None
        if created_ax:
            fig, ax = self._subplots(output_file)
        else:
            fig = ax.figure

        ax.plot(x_ui, y, marker="o", markersize=3, linewidth=1.0, label=label)
        if label is not None:
            ax.legend()
        ax.set_title(title)
        ax.set_xlabel("Discrete time (UI, main cursor = 0)")
        ax.set_ylabel(ylabel)
        if xlim_ui is not None:
            ax.set_xlim(*xlim_ui)
        ax.grid(True)
        self._annotate_config(ax)

        if output_file or created_ax:
            self._finish_figure(fig, output_file)
        return ax

    def _h_dsamp(self) -> np.ndarray:
        dfe = self.status.dfe
        if dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")
        return self.status.victim.pulse.ir[dfe.pos::self.cfg.link.per_ui]

    def _h_isi(self) -> np.ndarray:
        if self.status.imp is not None:
            return self.status.imp.h_ISI
        dfe = self.status.dfe
        if dfe is None or not hasattr(dfe, "h_ISI"):
            raise RuntimeError("Residual ISI is not available. Run post-DTE impairment calculation first.")
        return dfe.h_ISI

    def _t_dsamp_ui(self) -> np.ndarray:
        dfe = self.status.dfe
        if dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")
        num_pre = (dfe.ts - dfe.pos) // self.cfg.link.per_ui
        return np.arange(len(self._h_dsamp()), dtype=float) - float(num_pre)

    def _h_j_ui_axis(self) -> np.ndarray:
        dfe = self.status.dfe
        if dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")

        h = self.status.victim.pulse.ir
        pos = int(dfe.ts) % self.cfg.link.per_ui
        center_idx = np.arange(pos, len(h), self.cfg.link.per_ui)
        valid = (center_idx > 0) & (center_idx < len(h) - 1)
        center_idx = center_idx[valid]
        return (center_idx.astype(float) - float(dfe.ts)) / float(self.cfg.link.per_ui)

    def plot_paths_pulses(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        ax, _ = plot_path_pulse_overview(
            self.cfg,
            self.status.paths,
            save_path,
            xlim_ui=xlim_ui,
        )
        return ax

    def plot_paths_sbr(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        ax, _ = plot_path_sbr_overview(
            self.cfg,
            self.status.paths,
            save_path,
            xlim_ui=xlim_ui,
        )
        return ax

    def plot_paths_S_all_IL(
        self,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
    ) -> Any:
        ax, _ = plot_path_il_overview(
            self.cfg,
            self.status.paths,
            save_path,
            xlim=xlim,
        )
        return ax

    def _plot_link_sbr(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-2.0, 4.0),
        subtitle: str = "",
    ) -> Any:
        output_file = self._plot_save_path(save_path, filename)
        fig, ax = self._subplots(output_file)
        segment.plot_sbr(ax=ax, x_origin="start", x_unit="ui", xlim_ui=xlim_ui)
        self._set_plot_title(ax, title, subtitle)
        self._finish_figure(fig, output_file)
        return ax

    def _plot_link_sr(
        self,
        segment: LinkSegment,
        title: str,
        filename: str,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-0.2, 1.2),
        subtitle: str = "",
        annotate_20_80: bool = False,
    ) -> Any:
        ax, _ = plot_link_sr(
            self.cfg,
            segment,
            save_path,
            filename=filename,
            title=title,
            subtitle=subtitle,
            xlim_ui=xlim_ui,
            annotate_20_80=annotate_20_80,
        )
        return ax

    def plot_paths_H21_tf(
        self,
        save_path: str = "",
        xlim: Optional[tuple[float, float]] = None,
        ylim: Optional[tuple[float, float]] = None,
    ) -> Any:
        ax, _ = plot_path_h21_overview(
            self.cfg,
            self.status.paths,
            save_path,
            xlim=xlim,
            ylim=ylim,
        )
        return ax

    def plot_COMPath(self, path_idx: int = 0, save_path: str = "") -> dict[str, Any]:
        """
        Plot detailed path-building results for one COMPath.

        Parameters
        ----------
        path_idx:
            Index in COMStatus.paths. Default 0 plots the victim path.
        save_path:
            Optional output directory. If provided, figures are written under a
            path-specific subdirectory.
        """
        path_idx = int(path_idx)
        if path_idx < 0 or path_idx >= len(self.status.paths):
            raise IndexError("path_idx is outside COMStatus.paths.")

        path = self.status.paths[path_idx]
        path_dir = self._path_dir(save_path, path_idx)
        outputs: dict[str, Any] = {}
        outputs["S_tx_sdd"] = self._plot_S_tx(path, path_dir)
        outputs["S_ch_sdd"] = self._plot_S_ch(path, path_dir)
        outputs["S_rx_sdd"] = self._plot_S_rx(path, path_dir)
        outputs["S_all_sdd"] = self._plot_S_all(path, path_dir)
        outputs["S_ch_IL"] = self._plot_sparam_il(
            path.S_ch,
            f"{self._path_label(path_idx)} S_ch IL",
            "S_ch_IL.png",
            path_dir,
            subtitle=f"Measured channel Sdd21; {self._il_f_nyq_subtitle(path.S_ch)}",
        )
        outputs["S_all_IL"] = self._plot_sparam_il(
            path.S_all,
            f"{self._path_label(path_idx)} S_all IL",
            "S_all_IL.png",
            path_dir,
            subtitle=f"Cascaded through-path Sdd21; {self._il_f_nyq_subtitle(path.S_all)}",
        )
        outputs["H_ffe_tf"] = self._plot_H_ffe(path, path_dir)
        outputs["H_t_tf"] = self._plot_H_t(path, path_dir)
        outputs["H_t_sr"] = self._plot_H_t_sr(path, path_dir)
        outputs["H_21_tf"] = self._plot_H_21(path, path_dir)
        outputs["H_21_ir"] = self._plot_link_ir(path.H_21, f"{self._path_label(path_idx)} H_21 IR", "H_21_ir.png", path_dir)
        outputs["H_r_tf"] = self._plot_H_r(path, path_dir)
        outputs["H_ctf_tf"] = self._plot_H_ctf(path, path_dir)
        h_all_nyq = self._relative_gain_db(path.H_all, self._f_nyq)
        h_all_subtitle = (
            f"All continuous-time filters cascaded; gain @ f_nyq={h_all_nyq:.2f} dB"
            if h_all_nyq is not None
            else "All continuous-time filters cascaded; f_nyq outside measured band"
        )
        outputs["H_all_tf"] = self._plot_link_tf(
            path.H_all,
            f"{self._path_label(path_idx)} H_all",
            "H_all_tf.png",
            path_dir,
            subtitle=h_all_subtitle,
            annotate_nyq=True,
        )
        outputs["pulse_ir"] = self._plot_link_ir(path.pulse, f"{self._path_label(path_idx)} Pulse IR", "pulse_ir.png", path_dir)
        return outputs

    def _plot_S_tx(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_tx,
            f"{path.kind} S_tx",
            "S_tx_sdd.png",
            save_path,
            subtitle="TX package S-parameter",
        )

    def _plot_S_rx(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_rx,
            f"{path.kind} S_rx",
            "S_rx_sdd.png",
            save_path,
            subtitle="RX package S-parameter",
        )

    def _plot_S_ch(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_ch,
            f"{path.kind} S_ch",
            "S_ch_sdd.png",
            save_path,
            subtitle="Channel Sdd; IL@f_nyq is absolute when fb is inside measured band",
            annotate_nyq=True,
        )

    def _plot_S_all(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_sparam_sdd(
            path.S_all,
            f"{path.kind} S_all",
            "S_all_sdd.png",
            save_path,
            subtitle="Cascaded S_tx + S_ch + S_rx; IL@f_nyq is absolute when fb is inside measured band",
            annotate_nyq=True,
        )

    def _plot_H_ffe(self, path: COMPath, save_path: str = "") -> Any:
        if path.kind == "next":
            subtitle = "NEXT aggressor H_ffe = 1 by COM path convention"
        else:
            subtitle = f"txfir = {self._format_txfir(self.cfg.filter.txfir)}"
        return self._plot_link_tf(
            path.H_ffe,
            f"{path.kind} H_ffe",
            "H_ffe_tf.png",
            save_path,
            subtitle=subtitle,
        )

    def _plot_H_t(self, path: COMPath, save_path: str = "") -> Any:
        Tr = self.cfg.filter.Tr
        if Tr is None:
            subtitle = "Tr = None"
        else:
            subtitle = f"Tr = {Tr * 1e12:.3g} ps = {Tr * self.cfg.link.fb:.3g} UI"
        return self._plot_link_tf(
            path.H_t,
            f"{path.kind} H_t",
            "H_t_tf.png",
            save_path,
            subtitle=subtitle,
            annotate_nyq=True,
        )

    def _plot_H_t_sr(self, path: COMPath, save_path: str = "") -> Any:
        Tr = self.cfg.filter.Tr
        if Tr is None:
            subtitle = "Tr = None"
        else:
            subtitle = f"Tr = {Tr * 1e12:.3g} ps = {Tr * self.cfg.link.fb:.3g} UI"
        return self._plot_link_sr(
            path.H_t,
            f"{path.kind} H_t Step Response",
            "H_t_sr.png",
            save_path,
            xlim_ui=(-0.5, 1.5),
            subtitle=subtitle,
            annotate_20_80=True,
        )

    def _plot_H_21(self, path: COMPath, save_path: str = "") -> Any:
        return self._plot_link_tf(
            path.H_21,
            f"{path.kind} H_21",
            "H_21_tf.png",
            save_path,
            subtitle="Terminated voltage transfer function; f_nyq marker shows channel loss relative to DC",
            annotate_nyq=True,
        )

    def _plot_H_r(self, path: COMPath, save_path: str = "") -> Any:
        fr = self.cfg.filter.fr
        subtitle = "fr = None" if fr is None else f"fr = {fr / 1e9:.3g} GHz"
        return self._plot_link_tf(
            path.H_r,
            f"{path.kind} H_r",
            "H_r_tf.png",
            save_path,
            subtitle=subtitle,
            annotate_3db=True,
            annotate_nyq=True,
        )

    def _plot_H_ctf(self, path: COMPath, save_path: str = "") -> Any:
        subtitle = (
            f"g_DC={self.cfg.filter.g_DC} dB, g_DC2={self.cfg.filter.g_DC2} dB, "
            f"fz={self._format_freq_ghz(self.cfg.filter.f_z)}, "
            f"fp1={self._format_freq_ghz(self.cfg.filter.f_p1)}, "
            f"fp2={self._format_freq_ghz(self.cfg.filter.f_p2)}"
        )
        return self._plot_link_tf(
            path.H_ctf,
            f"{path.kind} H_ctf",
            "H_ctf_tf.png",
            save_path,
            subtitle=subtitle,
        )

    def plot_COMDFEStatus(self, save_path: str = "") -> dict[str, Any]:
        if self.status.dfe is None:
            raise ValueError("COMStatus.dfe is None; run DFE calculation first.")
        out_dir = "" if not save_path else str(Path(save_path) / "equalization")
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        outputs: dict[str, Any] = {}
        outputs["h_dsamp"] = self._plot_pulse_and_h_dsamp(out_dir)
        outputs["h_ISI"] = self.plot_h_ISI(save_path=out_dir)
        outputs["dfe_summary"] = self._plot_dfe_summary(out_dir)
        return outputs

    def _plot_pulse_and_h_dsamp(self, save_path: str = "") -> Any:
        if self.status.dfe is None:
            raise ValueError("COMStatus.dfe is None; run DFE calculation first.")
        dfe = self.status.dfe
        ax, _ = plot_ct_pulse_and_samples(
            self.cfg,
            self.status.victim.pulse.ir,
            self._h_dsamp(),
            selected_pos=dfe.pos,
            selected_ts=dfe.ts,
            root=save_path,
            subtitle="93A selected sampling phase",
        )
        return ax

    def _plot_dfe_summary(
        self,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
    ) -> Any:
        if self.status.dfe is None:
            raise ValueError("COMStatus.dfe is None; run DFE calculation first.")

        tap_idx = np.arange(1, len(self.status.dfe.dfe_coeff) + 1)
        ax, _ = plot_equalizer_coefficients(
            self.cfg,
            [("DFE", tap_idx, -np.asarray(self.status.dfe.dfe_coeff, dtype=float))],
            save_path,
            title="93A Equalizer Coefficients",
            subtitle="DFE is shown with feedback subtraction sign",
        )
        return ax

    def plot_h_dsamp(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        return self._plot_discrete_time_response(
            self._t_dsamp_ui(),
            self._h_dsamp(),
            title="Downsampled Victim Pulse",
            ylabel="h_dsamp (V)",
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
            filename="h_dsamp.png",
        )

    def plot_h_ISI(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        if self.status.dfe is None:
            raise RuntimeError("COMStatus.dfe is not available.")
        if ax is None:
            axis = self._t_dsamp_ui()
            reference_index = int(np.argmin(np.abs(axis)))
            rendered_ax, _ = plot_discrete_sequence(
                self.cfg,
                self._h_isi(),
                save_path,
                filename="h_ISI.png",
                title="Residual ISI Samples",
                ylabel="h_ISI (V)",
                reference_index=reference_index,
                xlim_ui=xlim_ui,
            )
            return rendered_ax
        return self._plot_discrete_time_response(
            self._t_dsamp_ui(),
            self._h_isi(),
            title="Residual ISI Samples",
            ylabel="h_ISI (V)",
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
            filename="h_ISI.png",
        )

    def plot_h_J(
        self,
        ax: Any = None,
        save_path: str = "",
        xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
        label: Optional[str] = None,
    ) -> Any:
        if self.status.imp is None:
            raise RuntimeError("COMStatus.imp is not available.")
        return self._plot_discrete_time_response(
            self._h_j_ui_axis(),
            self.status.imp.h_J,
            title="Sampled Jitter Sensitivity",
            ylabel="h_J (V/UI)",
            ax=ax,
            save_path=save_path,
            xlim_ui=xlim_ui,
            label=label,
            filename="h_J.png",
        )

    def plot_COMImpairmentStatus(self, save_path: str = "") -> dict[str, Any]:
        if self.status.imp is None:
            raise ValueError("COMStatus.imp is None; run imp calculation first.")
        out_dir = "" if not save_path else str(Path(save_path) / "impairment" / "final")
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        outputs: dict[str, Any] = {}
        outputs["imp_summary"] = self._plot_imp_summary(out_dir)
        outputs["imp_proportion"] = self._plot_imp_proportion(out_dir)
        outputs["h_J"] = self.plot_h_J(save_path=out_dir)
        outputs["noise_filter"] = self._plot_noise_filter(out_dir)
        return outputs

    def _plot_imp_proportion(self, save_path: str = "") -> Any:
        if self.status.imp is None:
            raise ValueError("COMStatus.imp is None; run imp calculation first.")
        labels = ["TX", "ISI", "J", "XT", "N"]
        sigma = np.asarray(
            [
                self.status.imp.sigma_TX,
                self.status.imp.sigma_ISI,
                self.status.imp.sigma_J,
                self.status.imp.sigma_XT,
                self.status.imp.sigma_N,
            ],
            dtype=float,
        )
        outputs = plot_impairment_bars(
            self.cfg,
            labels,
            sigma,
            save_path,
            title_prefix="93A Final",
            metric_text=self._imp_metric_text(),
            render=("proportion",),
        )
        return outputs.get("imp_proportion", "")

    def _plot_imp_summary(self, save_path: str = "") -> Any:
        if self.status.imp is None:
            raise ValueError("COMStatus.imp is None; run imp calculation first.")

        labels = ["TX", "ISI", "J", "XT", "N"]
        values = [
            self.status.imp.sigma_TX,
            self.status.imp.sigma_ISI,
            self.status.imp.sigma_J,
            self.status.imp.sigma_XT,
            self.status.imp.sigma_N,
        ]

        outputs = plot_impairment_bars(
            self.cfg,
            labels,
            values,
            save_path,
            title_prefix="93A Final",
            metric_text=self._imp_metric_text(),
            render=("summary",),
        )
        return outputs.get("imp_summary", "")

    def _imp_metric_text(self) -> str:
        if self.status.imp is None:
            return ""
        text = f"As={self.status.imp.As:.4e} V"
        if self.status.FOM is not None:
            text += f"\nFOM={self.status.FOM:.2f} dB"
        return text

    def _plot_noise_filter(self, save_path: str = "") -> Any:
        # Lazy import avoids a module cycle while preserving this recorded legacy plot.
        from ..models.com_model_93A import _build_H_ctf_93A, _build_H_r_93A

        noise_filter = _build_H_r_93A(self.cfg.link, self.cfg.filter).cascade_tf(
            _build_H_ctf_93A(self.cfg.link, self.cfg.filter)
        )
        output_file = self._plot_save_path(save_path, "noise_filter_tf.png")
        fig, ax = self._subplots(output_file)
        noise_filter.plot_tf(ax=ax)
        if self.cfg.filter.fr is not None:
            fr_ghz = self.cfg.filter.fr / 1e9
            ax.axvline(fr_ghz, linestyle="--", color="tab:red", linewidth=1.0, label=f"fr={fr_ghz:.3f} GHz")
            ax.legend()
        ax.set_title("Receiver Noise Filter H_r * H_ctf")
        self._annotate_config(ax)
        self._finish_figure(fig, output_file)
        return ax

    def plot_COMPMFStatus(self, save_path: str = "") -> dict[str, Any]:
        if self.status.pmf is None:
            raise ValueError("COMStatus.pmf is None; run PMF calculation first.")
        out_dir = "" if not save_path else str(Path(save_path) / "pmf")
        if out_dir:
            Path(out_dir).mkdir(parents=True, exist_ok=True)

        pmf_status = self.status.pmf
        outputs: dict[str, Any] = {}
        components = [
            (name, getattr(pmf_status, name))
            for name in ("p_ISI", "p_G", "p_DD", "p_XT", "p_qn")
            if getattr(pmf_status, name) is not None
        ]
        for name, pmf in components:
            outputs[name] = self._plot_pmf(pmf, name, f"{name}.png", out_dir)

        ax, _ = plot_pmf_components(
            components,
            out_dir,
            keep_mass=self.cfg.pmf.keep_mass,
        )
        outputs["components"] = ax
        outputs["combined_cdf"] = self._plot_pmf_summary(out_dir)
        return outputs

    def _plot_pmf_summary(self, save_path: str = "") -> Any:
        if self.status.pmf is None or self.status.pmf.p_combined is None:
            raise ValueError("COMStatus.pmf.p_combined is not available.")

        pmf_status = self.status.pmf
        total = pmf_status.p_combined
        if pmf_status.y0 is None or pmf_status.A_ni is None:
            raise ValueError("Combined PMF reporting requires stored y0 and A_ni.")
        axes, _ = plot_combined_pmf_cdf(
            total,
            save_path,
            der0=self.cfg.DER_0,
            y0=pmf_status.y0,
            a_ni=pmf_status.A_ni,
            com_value=pmf_status.COM,
            keep_mass=self.cfg.pmf.keep_mass,
        )
        return axes

    def _plot_overview_stage(self, save_path: str | Path) -> dict[str, Any]:
        return {
            "path_pulses": self.plot_paths_pulses(str(save_path)),
            "path_sbr": self.plot_paths_sbr(str(save_path)),
            "path_S_all_IL": self.plot_paths_S_all_IL(str(save_path)),
            "path_H21_tf": self.plot_paths_H21_tf(str(save_path)),
        }

    def _plot_paths_stage(
        self,
        path_idx: int,
        save_path: str | Path,
    ) -> dict[str, Any]:
        return self.plot_COMPath(path_idx=path_idx, save_path=str(save_path))

    def _plot_equalizer_stage(self, save_path: str | Path) -> dict[str, Any]:
        return self.plot_COMDFEStatus(str(save_path))

    def _plot_impairments_stage(self, save_path: str | Path) -> dict[str, Any]:
        return self.plot_COMImpairmentStatus(str(save_path))

    def _plot_pmf_stage(self, save_path: str | Path) -> dict[str, Any]:
        return self.plot_COMPMFStatus(str(save_path))

    def _plot_search_stage(self, save_path: str | Path) -> dict[str, Any]:
        """
        Plot search-run report figures.

        The current search detail view keeps search-level summary figures and
        then plots the best candidate through the single-run report path.
        """
        outputs: dict[str, Any] = {}
        if save_path:
            Path(save_path).mkdir(parents=True, exist_ok=True)
        outputs["search_fom_trace"] = self._plot_search_fom_trace(str(save_path))
        outputs["search_top_candidates"] = self._plot_search_top_candidates(str(save_path))
        best_dir = "" if not save_path else str(Path(save_path) / "best")
        outputs["best"] = type(self)(self.cfg, self.search_status.best).plot_single_run(best_dir)
        return outputs

    def _plot_search_fom_trace(self, save_path: str = "") -> Any:
        if self.search_status is None:
            raise ValueError("COMReport was not initialized with COMSearchStatus.")
        rows = self.search_status.rows
        output = ReportFigureTools.output_path(save_path, "search_fom_trace.png")
        fig, ax = ReportFigureTools.subplots(output)
        ok = [row for row in rows if row.status == "ok"]
        if ok:
            ax.plot([row.idx for row in ok], [row.FOM for row in ok], marker="o", linestyle="none")
        failed = [row for row in rows if row.status != "ok"]
        if failed:
            ax.scatter([row.idx for row in failed], np.zeros(len(failed)), marker="x", color="tab:red", label="error")
        ax.set_title("Search FOM Trace")
        ax.set_xlabel("Candidate index")
        ax.set_ylabel("FOM (dB)")
        ax.grid(True)
        ReportFigureTools.finish(fig, output)
        return output

    def _plot_search_top_candidates(self, save_path: str = "", top_n: int = 10) -> Any:
        if self.search_status is None:
            raise ValueError("COMReport was not initialized with COMSearchStatus.")
        rows = [row for row in self.search_status.rows if row.status == "ok"]
        if not rows:
            raise ValueError("COMSearchStatus.rows contains no successful rows to plot.")
        rows = sorted(rows, key=lambda row: row.FOM, reverse=True)[:int(top_n)]
        labels = [f"{row.idx}\n({row.candidate.g_DC:.1f},{row.candidate.g_DC2:.1f})" for row in rows]
        output = ReportFigureTools.output_path(save_path, "search_top_candidates.png")
        fig, ax = ReportFigureTools.subplots(output, figsize=(max(7, 0.7 * len(rows)), 4))
        ax.bar(np.arange(len(rows)), [row.FOM for row in rows])
        ax.set_xticks(np.arange(len(rows)))
        ax.set_xticklabels(labels)
        ax.set_title("Top Search Candidates")
        ax.set_xlabel("Candidate idx\n(g_DC, g_DC2)")
        ax.set_ylabel("FOM (dB)")
        ax.grid(True, axis="y")
        ReportFigureTools.finish(fig, output)
        return output

__all__ = ["COMReport"]
