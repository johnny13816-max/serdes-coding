"""Shared stage orchestration for versioned COM reports.

The base class owns report lifecycle, optional-stage handling, artifact export,
and the shallow canonical field surface.  Version adapters map their config and
status trees onto that surface and provide only the stage-specific composition.
No model quantity is calculated here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable
import warnings

from .com_report_common import ReportFigureTools, write_plot_manifest


class COMReportDataWarning(UserWarning):
    """A report renderer was skipped because its stored input was incomplete."""


class COMReportBase(ABC):
    """Common read-only report flow for 93A and 178A.

    Canonical fields are intentionally direct attributes instead of another
    typed dataclass tree.  Their purpose is to give stage orchestration stable
    names while leaving versioned status objects as the owners of model data.
    """

    _CANONICAL_FIELDS = (
        "paths",
        "equalizer",
        "pre_dte_impairment",
        "final_impairment",
        "pmf",
        "mlsd",
        "search",
    )

    def __init__(self, cfg: Any, status: Any):
        self.cfg = cfg
        is_search = all(hasattr(status, name) for name in ("best", "best_row", "rows"))
        self.search_status = status if is_search else None
        self.status = status.best if is_search else status

        mapped = self._map_canonical_fields()
        unknown = set(mapped) - set(self._CANONICAL_FIELDS)
        if unknown:
            raise ValueError(f"Unknown canonical report fields: {sorted(unknown)}")
        for name in self._CANONICAL_FIELDS:
            setattr(self, name, mapped.get(name))

    @abstractmethod
    def _map_canonical_fields(self) -> dict[str, Any]:
        """Map one version's completed status to the shallow report surface."""

    def _plot_optional_stage(
        self,
        stage_name: str,
        available: bool,
        renderer: Callable[..., dict[str, Any]],
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not available:
            return {}
        try:
            return renderer(*args, **kwargs)
        except (AttributeError, RuntimeError, ValueError) as exc:
            warnings.warn(
                f"Skipping COM report stage '{stage_name}': {exc}",
                COMReportDataWarning,
                stacklevel=2,
            )
            return {}

    def plot_overview(self, save_path: str | Path = "") -> dict[str, Any]:
        """Plot the common path overview when path data is available."""
        return self._plot_optional_stage(
            "overview", bool(self.paths), self._plot_overview_stage, save_path
        )

    def plot_paths(
        self,
        save_path: str | Path = "",
        path_idx: int = 0,
    ) -> dict[str, Any]:
        """Plot one detailed channel path using the version adapter."""
        return self._plot_optional_stage(
            "paths", bool(self.paths), self._plot_paths_stage, path_idx, save_path
        )

    def plot_equalizer(self, save_path: str | Path = "") -> dict[str, Any]:
        """Plot the selected equalizer stage when it was completed."""
        return self._plot_optional_stage(
            "equalizer",
            self.equalizer is not None,
            self._plot_equalizer_stage,
            save_path,
        )

    def plot_impairments(self, save_path: str | Path = "") -> dict[str, Any]:
        """Plot every stored impairment stage owned by the version adapter."""
        available = self.pre_dte_impairment is not None or self.final_impairment is not None
        return self._plot_optional_stage(
            "impairments", available, self._plot_impairments_stage, save_path
        )

    def plot_pmf(self, save_path: str | Path = "") -> dict[str, Any]:
        """Plot stored final-PMF data without rebuilding missing quantities."""
        return self._plot_optional_stage(
            "pmf", self.pmf is not None, self._plot_pmf_stage, save_path
        )

    def plot_mlsd(self, save_path: str | Path = "") -> dict[str, Any]:
        """Plot stored MLSD data when the model version provides it."""
        return self._plot_optional_stage(
            "mlsd", self.mlsd is not None, self._plot_mlsd_stage, save_path
        )

    def plot_search(self, save_path: str | Path = "") -> dict[str, Any]:
        """Plot search metrics and the selected candidate report."""
        return self._plot_optional_stage(
            "search", self.search is not None, self._plot_search_stage, save_path
        )

    def plot_single_run(
        self,
        save_path: str | Path = "",
        path_idx: int = 0,
    ) -> dict[str, Any]:
        """Plot one completed run in canonical stage order."""
        if save_path:
            Path(save_path).mkdir(parents=True, exist_ok=True)
        stages = (
            ("overview", self.plot_overview(save_path)),
            ("paths", self.plot_paths(save_path, path_idx=path_idx)),
            ("equalizer", self.plot_equalizer(save_path)),
            ("impairments", self.plot_impairments(save_path)),
            ("pmf", self.plot_pmf(save_path)),
            ("mlsd", self.plot_mlsd(save_path)),
        )
        return {name: output for name, output in stages if output}

    def export_single_run(
        self,
        artifact_root: str | Path,
        path_idx: int = 0,
    ) -> dict[str, str]:
        """Write canonical plots and a verified cross-version manifest."""
        root = Path(artifact_root)
        plot_dir = ReportFigureTools.prepare_plot_directory(root / "plots")
        report = self.plot_single_run(plot_dir, path_idx=path_idx)
        manifest = write_plot_manifest(report, root, discover_under=plot_dir)
        return {"plots": str(plot_dir), "plot_manifest": manifest}

    def export_search_run(self, artifact_root: str | Path) -> dict[str, str]:
        """Write search plots and a verified cross-version manifest."""
        root = Path(artifact_root)
        plot_dir = ReportFigureTools.prepare_plot_directory(root / "plots")
        report = self.plot_search(plot_dir)
        manifest = write_plot_manifest(report, root, discover_under=plot_dir)
        return {"plots": str(plot_dir), "plot_manifest": manifest}

    # Compatibility spelling retained for existing entry points.
    def plot_search_run(self, save_path: str | Path = "") -> dict[str, Any]:
        return self.plot_search(save_path)

    @abstractmethod
    def _plot_overview_stage(self, save_path: str | Path) -> dict[str, Any]:
        """Compose the version's overview from shared renderers."""

    @abstractmethod
    def _plot_paths_stage(
        self, path_idx: int, save_path: str | Path
    ) -> dict[str, Any]:
        """Compose one detailed path from shared renderers."""

    @abstractmethod
    def _plot_equalizer_stage(self, save_path: str | Path) -> dict[str, Any]:
        """Compose the version's selected equalizer plots."""

    @abstractmethod
    def _plot_impairments_stage(self, save_path: str | Path) -> dict[str, Any]:
        """Compose the version's stored impairment plots."""

    @abstractmethod
    def _plot_pmf_stage(self, save_path: str | Path) -> dict[str, Any]:
        """Compose the version's final-PMF plots."""

    def _plot_mlsd_stage(self, save_path: str | Path) -> dict[str, Any]:
        return {}

    @abstractmethod
    def _plot_search_stage(self, save_path: str | Path) -> dict[str, Any]:
        """Compose the version's search plots."""


__all__ = ["COMReportBase", "COMReportDataWarning"]
