"""Shared presentation helpers for 93A and 178A COM reports.

This module consumes completed status objects through their common path
interface. It owns plotting only and must not calculate COM model quantities.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np


def write_plot_manifest(
    report_outputs: Any,
    artifact_root: str | Path,
    *,
    filename: str = "plot_manifest.json",
    discover_under: Optional[str | Path] = None,
) -> str:
    """Validate all returned PNG artifacts and write one deterministic manifest."""
    root = Path(artifact_root)
    plot_files: list[Path] = []

    def collect(value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                collect(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                collect(item)
        elif isinstance(value, (str, Path)) and str(value).lower().endswith(".png"):
            plot_files.append(Path(value))

    collect(report_outputs)
    if discover_under is not None:
        plot_files.extend(Path(discover_under).rglob("*.png"))
    if not plot_files:
        raise RuntimeError("COM report produced no PNG outputs.")

    records = []
    for path in sorted(set(plot_files)):
        data = path.read_bytes()
        if len(data) < 100 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError(f"Invalid or empty report PNG: {path}")
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": len(data),
            }
        )

    manifest_path = root / filename
    manifest_path.write_text(
        json.dumps({"count": len(records), "files": records}, indent=2),
        encoding="utf-8",
    )
    return str(manifest_path)


class ReportFigureTools:
    """Version-neutral figure, annotation, and artifact-path helpers."""

    @staticmethod
    def pyplot() -> Any:
        import matplotlib.pyplot as plt

        return plt

    @staticmethod
    def prepare_plot_directory(path: str | Path) -> Path:
        """Create the generated plot root and remove stale PNG artifacts only."""
        plot_dir = Path(path)
        plot_dir.mkdir(parents=True, exist_ok=True)
        for artifact in plot_dir.rglob("*.png"):
            artifact.unlink()
        return plot_dir

    @staticmethod
    def output_path(directory_or_file: str | Path, filename: str) -> str:
        if not directory_or_file:
            return ""
        path = Path(directory_or_file)
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
            return str(path)
        path.mkdir(parents=True, exist_ok=True)
        return str(path / filename)

    @classmethod
    def subplots(cls, output_path: str, *args: Any, **kwargs: Any) -> tuple[Any, Any]:
        """Create a local Agg figure for files and preserve interactive pyplot otherwise."""
        if output_path:
            from matplotlib.backends.backend_agg import FigureCanvasAgg
            from matplotlib.figure import Figure

            figsize = kwargs.pop("figsize", None)
            fig = Figure(figsize=figsize)
            FigureCanvasAgg(fig)
            return fig, fig.subplots(*args, **kwargs)
        return cls.pyplot().subplots(*args, **kwargs)

    @classmethod
    def subplots_in(
        cls,
        directory_or_file: str | Path,
        filename: str,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[Any, Any, str]:
        output = cls.output_path(directory_or_file, filename)
        fig, axes = cls.subplots(output, *args, **kwargs)
        return fig, axes, output

    @classmethod
    def finish(cls, fig: Any, output_path: str) -> None:
        fig.tight_layout()
        if output_path:
            fig.savefig(output_path, bbox_inches="tight")
        else:
            fig.canvas.draw_idle()
            cls.pyplot().show()

    @staticmethod
    def title(ax: Any, title: str, subtitle: str = "") -> None:
        ax.set_title(title, fontsize=14, pad=20 if subtitle else 8)
        if subtitle:
            ax.text(
                0.5,
                1.01,
                subtitle,
                transform=ax.transAxes,
                ha="center",
                va="bottom",
                fontsize=9,
                color="0.3",
            )

    @staticmethod
    def config_note(cfg: Any) -> str:
        return (
            f"f_nyq={float(cfg.link.fb) / 2e9:.3f} GHz, "
            f"OSR={int(cfg.link.per_ui)}, "
            f"df={float(cfg.link.df) / 1e6:.3f} MHz"
        )

    @classmethod
    def annotate_config(cls, ax: Any, cfg: Any) -> None:
        ax.text(
            0.01,
            0.01,
            cls.config_note(cfg),
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "alpha": 0.8,
                "edgecolor": "0.7",
            },
        )

    @staticmethod
    def annotate_upper_left(ax: Any, text: str) -> None:
        ax.text(
            0.01,
            0.99,
            text,
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            bbox={
                "boxstyle": "round,pad=0.25",
                "facecolor": "white",
                "alpha": 0.85,
                "edgecolor": "0.7",
            },
        )

    @staticmethod
    def impairment_note(cfg: Any) -> str:
        imp = cfg.imp
        lines = [
            f"R_LM={imp.R_LM:.4g}",
            f"SNR_TX={imp.SNR_TX:.3g} dB",
            f"sigma_RJ={imp.sigma_RJ:.3e} UI",
            f"A_DD={imp.A_DD:.3e} UI",
            f"eta_0={imp.eta_0:.3e} V^2/Hz",
        ]
        if getattr(imp, "N_qb", None) is not None:
            lines.append(f"N_qb={imp.N_qb}")
        if getattr(imp, "P_qc", None) is not None:
            lines.append(f"P_qc={imp.P_qc:.3e}")
        return "\n".join(lines)

    @classmethod
    def annotate_impairment(cls, ax: Any, cfg: Any) -> None:
        cls.annotate_upper_left(ax, cls.impairment_note(cfg))

    @staticmethod
    def annotate_pmf_settings(ax: Any, pmf: Any, keep_mass: float) -> None:
        missing_mass = max(0.0, 1.0 - float(keep_mass))
        keep_text = "1" if missing_mass == 0.0 else f"1-1e{int(round(np.log10(missing_mass)))}"
        ax.text(
            0.01,
            0.02,
            f"dy={pmf.dx:.3e} V, keep_mass={keep_text}",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "0.6", "pad": 2.0},
        )

    @staticmethod
    def frequency_xlim(freqs: np.ndarray, baud_rate: float) -> tuple[float, float]:
        values = np.asarray(freqs, dtype=float)
        if values.ndim != 1 or values.size == 0:
            raise ValueError("Frequency grid must be a non-empty 1D array.")
        positive = values[values > 0.0]
        if positive.size == 0:
            raise ValueError("Frequency axis must contain a positive bin for log-scale plots.")
        return float(positive[0]), min(float(values[-1]), 1.1 * float(baud_rate))

    @staticmethod
    def apply_auto_ylim_from_lines(
        ax: Any,
        xlim_hz: tuple[float, float],
        *,
        x_scale: float = 1e-9,
        floor_db: float = -300.0,
        pad_ratio: float = 0.05,
    ) -> None:
        lo_x = float(xlim_hz[0]) * float(x_scale)
        hi_x = float(xlim_hz[1]) * float(x_scale)
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
        if above_floor.size:
            visible = above_floor
        if visible.size == 0:
            return
        y_min = float(np.min(visible))
        y_max = float(np.max(visible))
        pad = (
            max(1.0, abs(y_min) * float(pad_ratio))
            if np.isclose(y_min, y_max)
            else (y_max - y_min) * float(pad_ratio)
        )
        ax.set_ylim(y_min - pad, y_max + pad)

    @staticmethod
    def path_label(index: int, path: Any) -> str:
        return f"{int(index)}:{path.kind}"

    @staticmethod
    def path_directory(root: str | Path, index: int, path: Any) -> str:
        if not root:
            return ""
        name = "path_victim" if int(index) == 0 and path.kind == "victim" else f"path_{int(index):02d}_{path.kind}"
        return str(Path(root) / name)

    @staticmethod
    def pmf_moments(pmf: Any) -> tuple[float, float]:
        x = np.asarray(pmf.x, dtype=float)
        mass = np.asarray(pmf.pmf, dtype=float)
        mu = float(np.sum(x * mass))
        variance = float(np.sum((x - mu) ** 2 * mass))
        return mu, float(np.sqrt(max(0.0, variance)))

    @staticmethod
    def relative_gain_db(segment: Any, frequency_hz: float) -> Optional[float]:
        if frequency_hz < float(segment.freqs[0]) or frequency_hz > float(segment.freqs[-1]):
            return None
        magnitude_db = 20.0 * np.log10(np.maximum(np.abs(segment.tf), np.finfo(float).tiny))
        return float(np.interp(frequency_hz, segment.freqs, magnitude_db - magnitude_db[0]))

    @staticmethod
    def annotate_step_transition(ax: Any, segment: Any, baud_rate: float) -> None:
        sr = np.asarray(segment.sr, dtype=float)
        main_index = int(np.argmax(np.abs(segment.ir)))
        x_ui = (np.asarray(segment.times) - segment.times[main_index]) * float(baud_rate)
        y0 = float(np.nanmin(sr))
        y1 = float(np.nanmax(sr))
        span = y1 - y0
        if not np.isfinite(span) or span <= 0.0:
            return

        def crossing(level: float) -> Optional[float]:
            indices = np.flatnonzero(sr >= level)
            if indices.size == 0:
                return None
            index = int(indices[0])
            if index == 0:
                return float(x_ui[0])
            x0, x1 = float(x_ui[index - 1]), float(x_ui[index])
            v0, v1 = float(sr[index - 1]), float(sr[index])
            if np.isclose(v0, v1):
                return x1
            return x0 + (level - v0) * (x1 - x0) / (v1 - v0)

        y20 = y0 + 0.2 * span
        y80 = y0 + 0.8 * span
        x20 = crossing(y20)
        x80 = crossing(y80)
        if x20 is None or x80 is None:
            return
        ax.axhline(y20, linestyle=":", color="tab:gray", linewidth=1.0)
        ax.axhline(y80, linestyle=":", color="tab:gray", linewidth=1.0)
        ax.axvline(x20, linestyle="--", color="tab:red", linewidth=1.0)
        ax.axvline(x80, linestyle="--", color="tab:red", linewidth=1.0)
        ax.annotate(
            f"20%-80% = {x80 - x20:.3g} UI",
            xy=((x20 + x80) / 2.0, y80),
            xytext=(8, 8),
            textcoords="offset points",
            color="tab:red",
            fontsize=9,
        )


def _require_paths(paths: Iterable[Any]) -> list[Any]:
    result = list(paths)
    if not result:
        raise ValueError("COM report requires at least one path.")
    return result


def _overview_directory(root: str | Path) -> str:
    return "" if not root else str(Path(root) / "overview")


def plot_sparam_sdd(
    cfg: Any,
    model: Any,
    root: str | Path,
    *,
    filename: str,
    title: str,
    subtitle: str = "",
    xlim: Optional[tuple[float, float]] = None,
    annotate_3db: bool = False,
    annotate_nyq: bool = False,
) -> tuple[Any, str]:
    if xlim is None:
        xlim = ReportFigureTools.frequency_xlim(model.freqs, cfg.link.fb)
    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    model.plot_sdd(ax=ax, logx=True, xlim=xlim)
    f_nyq = float(cfg.link.fb) / 2.0
    if annotate_nyq and float(model.freqs[0]) <= f_nyq <= float(model.freqs[-1]):
        model.annotate_IL(ax, f_nyq, label="IL")
    elif annotate_nyq:
        ax.text(
            0.99,
            0.08,
            "f_nyq outside S-param measured band",
            ha="right",
            va="bottom",
            transform=ax.transAxes,
            fontsize=8,
            color="tab:red",
        )
    if annotate_3db:
        f_3db = model.frequency_at_sdd21_gain(-3.0)
        if f_3db is not None and f_3db <= xlim[1]:
            model.annotate_f(ax, f_3db, label="Sdd21 -3dB")
    ReportFigureTools.title(ax, title, subtitle)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_sparam_il(
    cfg: Any,
    model: Any,
    root: str | Path,
    *,
    filename: str,
    title: str,
    subtitle: str = "",
    xlim: Optional[tuple[float, float]] = None,
    annotate_3db: bool = False,
) -> tuple[Any, str]:
    if xlim is None:
        xlim = ReportFigureTools.frequency_xlim(model.freqs, cfg.link.fb)
    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    f_nyq = float(cfg.link.fb) / 2.0
    annotate_f = f_nyq if float(model.freqs[0]) <= f_nyq <= float(model.freqs[-1]) else None
    model.plot_IL(
        ax=ax,
        logx=True,
        xlim=xlim,
        annotate_f=annotate_f,
        annotate_label="IL",
    )
    if annotate_f is None:
        ax.text(
            0.99,
            0.08,
            "f_nyq outside S-param measured band",
            ha="right",
            va="bottom",
            transform=ax.transAxes,
            fontsize=8,
            color="tab:red",
        )
    if annotate_3db:
        f_3db = model.frequency_at_sdd21_gain(-3.0)
        if f_3db is not None and f_3db <= xlim[1]:
            model.annotate_f(ax, f_3db, label="Sdd21 -3dB")
    ReportFigureTools.title(ax, title, subtitle)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_link_tf(
    cfg: Any,
    segment: Any,
    root: str | Path,
    *,
    filename: str,
    title: str,
    subtitle: str = "",
    xlim: Optional[tuple[float, float]] = None,
    ylim: Optional[tuple[float, float]] = None,
    annotate_3db: bool = False,
    annotate_nyq: bool = False,
    annotate_config: bool = True,
) -> tuple[Any, str]:
    if xlim is None:
        xlim = ReportFigureTools.frequency_xlim(segment.freqs, cfg.link.fb)
    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    segment.plot_tf(ax=ax, x_scale="log", xlim=xlim, ylim=ylim)
    f_nyq = float(cfg.link.fb) / 2.0
    if annotate_nyq and float(segment.freqs[0]) <= f_nyq <= float(segment.freqs[-1]):
        segment.annotate_f(ax, f_nyq)
    if annotate_3db:
        f_3db = segment.frequency_at_gain(-3.0)
        if f_3db is not None and f_3db <= xlim[1]:
            segment.annotate_f(ax, f_3db)
    ReportFigureTools.title(ax, title, subtitle)
    if annotate_config:
        ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_link_ir(
    cfg: Any,
    segment: Any,
    root: str | Path,
    *,
    filename: str,
    title: str,
    subtitle: str = "",
    xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
) -> tuple[Any, str]:
    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    segment.plot_ir(ax=ax, x_origin="max", x_unit="ui", xlim_ui=xlim_ui)
    ReportFigureTools.title(ax, title, subtitle)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_link_sr(
    cfg: Any,
    segment: Any,
    root: str | Path,
    *,
    filename: str,
    title: str,
    subtitle: str = "",
    xlim_ui: Optional[tuple[float, float]] = (-0.5, 1.5),
    annotate_20_80: bool = False,
) -> tuple[Any, str]:
    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    segment.plot_sr(ax=ax, x_origin="max", x_unit="ui", xlim_ui=xlim_ui)
    if annotate_20_80:
        ReportFigureTools.annotate_step_transition(ax, segment, cfg.link.fb)
    ReportFigureTools.title(ax, title, subtitle)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_path_pulse_overview(
    cfg: Any,
    paths: Iterable[Any],
    root: str | Path = "",
    *,
    xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
) -> tuple[Any, str]:
    paths = _require_paths(paths)
    fig, ax, output = ReportFigureTools.subplots_in(
        _overview_directory(root), "path_pulses.png", figsize=(7, 4)
    )
    for index, path in enumerate(paths):
        ir = np.asarray(path.pulse.ir, dtype=float)
        main = int(np.argmax(np.abs(ir)))
        x_ui = np.asarray(path.pulse.cfg.times_ui, dtype=float) - float(path.pulse.cfg.times_ui[main])
        ax.plot(x_ui, ir, label=ReportFigureTools.path_label(index, path))
    ax.set_xlabel("Time (UI, path main cursor = 0)")
    ax.set_ylabel("Pulse response (V)")
    if xlim_ui is not None:
        ax.set_xlim(*xlim_ui)
    ax.grid(True)
    ax.legend()
    ReportFigureTools.title(ax, "Path Pulse Responses")
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_path_sbr_overview(
    cfg: Any,
    paths: Iterable[Any],
    root: str | Path = "",
    *,
    xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
) -> tuple[Any, str]:
    paths = _require_paths(paths)
    fig, ax, output = ReportFigureTools.subplots_in(
        _overview_directory(root), "path_sbr.png", figsize=(7, 4)
    )
    for index, path in enumerate(paths):
        sbr = np.asarray(path.pulse.sbr, dtype=float).copy()
        main = float(np.max(np.abs(sbr)))
        if main > 0.0:
            sbr /= main
        peak = int(np.argmax(np.abs(sbr)))
        x_ui = np.asarray(path.pulse.cfg.times_ui, dtype=float) - float(path.pulse.cfg.times_ui[peak])
        ax.plot(x_ui, sbr, label=ReportFigureTools.path_label(index, path))
    ax.set_xlabel("Time (UI, path main cursor = 0)")
    ax.set_ylabel("SBR / main")
    if xlim_ui is not None:
        ax.set_xlim(*xlim_ui)
    ax.grid(True)
    ax.legend()
    ReportFigureTools.title(ax, "Path Single-Bit Responses")
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_path_il_overview(
    cfg: Any,
    paths: Iterable[Any],
    root: str | Path = "",
    *,
    xlim: Optional[tuple[float, float]] = None,
) -> tuple[Any, str]:
    paths = _require_paths(paths)
    if xlim is None:
        xlim = ReportFigureTools.frequency_xlim(paths[0].S_all.freqs, cfg.link.fb)
    fig, ax, output = ReportFigureTools.subplots_in(
        _overview_directory(root), "path_S_all_IL.png", figsize=(7, 4)
    )
    for index, path in enumerate(paths):
        path.S_all.plot_IL(
            ax=ax,
            logx=True,
            xlim=xlim,
            label=ReportFigureTools.path_label(index, path),
            auto_ylim=False,
        )
    ReportFigureTools.apply_auto_ylim_from_lines(ax, xlim)
    f_nyq = float(cfg.link.fb) / 2.0
    if float(paths[0].S_all.freqs[0]) <= f_nyq <= float(paths[0].S_all.freqs[-1]):
        ax.axvline(f_nyq / 1e9, color="tab:red", linestyle="--", linewidth=0.8, label="f_nyq")
    ax.legend()
    ReportFigureTools.title(ax, "Augmented Signal Path IL, S_all")
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_path_h21_overview(
    cfg: Any,
    paths: Iterable[Any],
    root: str | Path = "",
    *,
    xlim: Optional[tuple[float, float]] = None,
    ylim: Optional[tuple[float, float]] = None,
) -> tuple[Any, str]:
    paths = _require_paths(paths)
    if xlim is None:
        xlim = ReportFigureTools.frequency_xlim(paths[0].H_21.freqs, cfg.link.fb)
    fig, ax, output = ReportFigureTools.subplots_in(
        _overview_directory(root), "path_H21_tf.png", figsize=(7, 4)
    )
    for index, path in enumerate(paths):
        path.H_21.plot_tf(
            ax=ax,
            x_scale="log",
            xlim=xlim,
            ylim=ylim,
            auto_ylim=False,
            label=ReportFigureTools.path_label(index, path),
        )
    if ylim is None:
        ReportFigureTools.apply_auto_ylim_from_lines(ax, xlim)
    f_nyq = float(cfg.link.fb) / 2.0
    if float(paths[0].H_21.freqs[0]) <= f_nyq <= float(paths[0].H_21.freqs[-1]):
        ax.axvline(f_nyq / 1e9, color="tab:red", linestyle="--", linewidth=0.8, label="f_nyq")
    ax.legend()
    ReportFigureTools.title(ax, "Voltage Transfer Function H21")
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_ct_pulse_and_samples(
    cfg: Any,
    pulse_ir: np.ndarray,
    samples: np.ndarray,
    *,
    selected_pos: int,
    selected_ts: int,
    root: str | Path,
    filename: str = "h_dsamp.png",
    subtitle: str = "",
    shade_phase_interval: bool = False,
) -> tuple[Any, str]:
    """Render a continuous pulse and its selected UI-spaced samples."""
    pulse_ir = np.asarray(pulse_ir, dtype=float)
    samples = np.asarray(samples, dtype=float)
    per_ui = int(cfg.link.per_ui)
    pulse_index = np.arange(len(pulse_ir), dtype=float)
    sample_index = np.arange(len(samples), dtype=float) * per_ui + float(selected_pos)
    x_pulse = (pulse_index - float(selected_ts)) / per_ui
    x_samples = (sample_index - float(selected_ts)) / per_ui

    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    ax.plot(x_pulse, pulse_ir, color="0.35", linewidth=1.0, label="pulse.ir (CT)")
    ax.stem(
        x_samples,
        samples,
        linefmt="C0-",
        markerfmt="C0o",
        basefmt=" ",
        label="h_dsamp (DT)",
    )
    if shade_phase_interval:
        phase_offsets = (np.arange(per_ui, dtype=float) - float(selected_pos)) / per_ui
        ax.axvspan(
            float(np.min(phase_offsets)),
            float(np.max(phase_offsets)),
            color="tab:orange",
            alpha=0.12,
            label="candidate pos main-cursor interval",
        )
    ax.axvline(
        0.0,
        color="tab:green",
        linestyle="--",
        linewidth=1.0,
        label=f"selected pos={selected_pos}",
    )
    ax.set_xlabel("Time (UI, selected ts = 0)")
    ax.set_ylabel("Amplitude (V)")
    ax.set_xlim(-5.0, 20.0)
    ax.grid(True)
    ax.legend()
    ReportFigureTools.title(ax, "CT Pulse and Selected DT Response", subtitle)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_discrete_sequence(
    cfg: Any,
    values: np.ndarray,
    root: str | Path,
    *,
    filename: str,
    title: str,
    ylabel: str,
    reference_index: Optional[int] = None,
    xlim_ui: Optional[tuple[float, float]] = (-5.0, 20.0),
) -> tuple[Any, str]:
    """Render a UI-spaced sequence with its selected cursor at zero."""
    values = np.asarray(values, dtype=float)
    reference = int(np.argmax(np.abs(values))) if reference_index is None else int(reference_index)
    x = np.arange(len(values), dtype=float) - float(reference)
    fig, ax, output = ReportFigureTools.subplots_in(root, filename)
    ax.stem(x, values, basefmt=" ")
    ax.axvline(0.0, color="tab:green", linestyle="--", linewidth=0.8)
    ax.set_xlabel("Discrete time (UI, selected victim cursor = 0)")
    ax.set_ylabel(ylabel)
    if xlim_ui is not None:
        ax.set_xlim(*xlim_ui)
    ax.grid(True)
    ReportFigureTools.title(ax, title)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_equalizer_coefficients(
    cfg: Any,
    series: Iterable[tuple[str, np.ndarray, np.ndarray]],
    root: str | Path,
    *,
    title: str,
    subtitle: str = "",
) -> tuple[Any, str]:
    """Render one or more equalizer tap families on a shared coefficient axis."""
    fig, ax, output = ReportFigureTools.subplots_in(
        root,
        "equalizer_coefficients.png",
        figsize=(9, 4),
    )
    styles = (("C0-", "C0o"), ("C1-", "C1s"), ("C2-", "C2^"))
    for series_index, (label, tap_index, values) in enumerate(series):
        linefmt, markerfmt = styles[series_index % len(styles)]
        ax.stem(
            np.asarray(tap_index),
            np.asarray(values, dtype=float),
            linefmt=linefmt,
            markerfmt=markerfmt,
            basefmt=" ",
            label=label,
        )
    ax.axvline(0.0, color="tab:green", linestyle="--", linewidth=0.8, label="main cursor")
    ax.set_xlabel("Tap index relative to main cursor")
    ax.set_ylabel("Coefficient")
    ax.grid(True)
    ax.legend()
    ReportFigureTools.title(ax, title, subtitle)
    ReportFigureTools.annotate_config(ax, cfg)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_impairment_bars(
    cfg: Any,
    labels: Iterable[str],
    sigma_values: Iterable[float],
    root: str | Path,
    *,
    title_prefix: str,
    metric_text: str = "",
    render: tuple[str, ...] = ("summary", "proportion"),
) -> dict[str, str]:
    """Render common RMS and variance-proportion plots for one impairment stage."""
    labels = list(labels)
    sigma = np.asarray(list(sigma_values), dtype=float)
    if len(labels) != len(sigma):
        raise ValueError("Impairment labels and sigma values must have equal length.")
    valid = np.isfinite(sigma) & (sigma >= 0.0)
    labels = [label for label, keep in zip(labels, valid) if keep]
    sigma = sigma[valid]
    if sigma.size == 0:
        return {}

    outputs: dict[str, str] = {}
    if "summary" in render:
        fig, ax, output = ReportFigureTools.subplots_in(root, "imp_summary.png", figsize=(7, 4))
        ax.bar(labels, sigma, color="tab:blue")
        ax.set_ylabel("RMS amplitude (V)")
        ax.grid(True, axis="y", alpha=0.35)
        ReportFigureTools.title(ax, f"{title_prefix} RMS Breakdown")
        ReportFigureTools.annotate_impairment(ax, cfg)
        if metric_text:
            ax.text(0.99, 0.99, metric_text, transform=ax.transAxes, ha="right", va="top")
        ReportFigureTools.finish(fig, output)
        outputs["imp_summary"] = output

    variance = sigma**2
    total = float(np.sum(variance))
    if total <= 0.0 or "proportion" not in render:
        return outputs
    percentages = 100.0 * variance / total
    fig, ax, output = ReportFigureTools.subplots_in(root, "imp_proportion.png", figsize=(7, 4))
    bars = ax.bar(labels, percentages, color="tab:blue")
    for bar, percentage in zip(bars, percentages):
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height(),
            f"{percentage:.1f}%",
            ha="center",
            va="bottom",
            fontsize=9,
        )
    ax.set_ylabel("Variance contribution (%)")
    ax.set_ylim(0.0, max(100.0, float(np.max(percentages)) * 1.18))
    ax.grid(True, axis="y", alpha=0.35)
    ReportFigureTools.title(
        ax,
        f"{title_prefix} Impairment Proportion",
        "Percentage of total impairment variance",
    )
    ReportFigureTools.annotate_impairment(ax, cfg)
    ReportFigureTools.finish(fig, output)
    outputs["imp_proportion"] = output
    return outputs


def plot_pmf_component(
    pmf: Any,
    name: str,
    root: str | Path,
    *,
    keep_mass: float,
) -> tuple[Any, str]:
    """Render one stored PMF component with common moments and grid metadata."""
    fig, ax, output = ReportFigureTools.subplots_in(root, f"{name}.png")
    pmf.plot(ax=ax, label=name)
    mu, std = ReportFigureTools.pmf_moments(pmf)
    ReportFigureTools.title(ax, name, f"mu={mu:.3e} V, std={std:.3e} V")
    ReportFigureTools.annotate_pmf_settings(ax, pmf, keep_mass)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_pmf_components(
    components: Iterable[tuple[str, Any]],
    root: str | Path,
    *,
    keep_mass: float,
) -> tuple[Any, str]:
    """Overlay all stored final PMF components with a stable shared layout."""
    components = list(components)
    fig, ax, output = ReportFigureTools.subplots_in(root, "pmf_components.png")
    for name, pmf in components:
        pmf.plot(ax=ax, label=name)
    ReportFigureTools.title(ax, "Final PMF Components")
    if components:
        ReportFigureTools.annotate_pmf_settings(ax, components[0][1], keep_mass)
    ReportFigureTools.finish(fig, output)
    return ax, output


def plot_combined_pmf_cdf(
    total: Any,
    root: str | Path,
    *,
    der0: float,
    y0: float,
    a_ni: float,
    com_value: Optional[float],
    keep_mass: float,
) -> tuple[Any, str]:
    """Render the stored final PMF and CDF threshold without recomputing model results."""
    der0 = float(der0)
    y0 = float(y0)
    a_ni = float(a_ni)
    fig, axes, output = ReportFigureTools.subplots_in(
        root,
        "combined_cdf.png",
        2,
        1,
        figsize=(7, 7),
        sharex=True,
    )
    pdf_ax, cdf_ax = axes
    total.plot(ax=pdf_ax, label="p_total")
    total.plot(ax=cdf_ax, quantity="cdf", label="CDF(p_total)")

    p_total_y0 = float(np.interp(y0, total.x, total.pmf))
    for axis in axes:
        axis.axvline(y0, color="tab:red", linestyle="--", linewidth=1.0)
    pdf_ax.scatter([y0], [p_total_y0], color="tab:red", zorder=3)
    pdf_ax.annotate(
        f"A_ni={a_ni:.3e} V",
        xy=(y0, p_total_y0),
        xytext=(8, 8),
        textcoords="offset points",
        color="tab:red",
        fontsize=8,
    )
    cdf_ax.scatter([y0], [der0], color="tab:red", zorder=3)
    cdf_ax.axhline(der0, color="tab:red", linestyle=":", linewidth=0.8)
    cdf_ax.annotate(
        f"DER_0={der0:.3e}\nA_ni={a_ni:.3e} V",
        xy=(y0, der0),
        xytext=(8, 8),
        textcoords="offset points",
        color="tab:red",
        fontsize=8,
    )
    cdf_values = np.asarray(total.cdf, dtype=float)
    positive_cdf = cdf_values[np.isfinite(cdf_values) & (cdf_values > 0.0)]
    cdf_ax.set_yscale("log")
    lower = max(1e-12, float(np.min(positive_cdf)) * 0.5 if positive_cdf.size else 1e-12)
    cdf_ax.set_ylim(lower, 1.0)

    com_text = f"COM={float(com_value):.3f} dB" if com_value is not None else "COM=None"
    ReportFigureTools.title(
        pdf_ax,
        "Total PMF PDF",
        f"{com_text}, DER_0={der0:.3e}, A_ni={a_ni:.3e} V",
    )
    ReportFigureTools.title(cdf_ax, "Total PMF CDF", f"{com_text}, DER_0 threshold")
    ReportFigureTools.annotate_pmf_settings(cdf_ax, total, keep_mass)
    ReportFigureTools.finish(fig, output)
    return axes, output
