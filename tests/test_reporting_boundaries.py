from inspect import signature
from types import SimpleNamespace

import pytest

from serdes_coding.models.com_model_93A import (
    COMSearchStatus as COMSearchStatus93A,
    COMStatus as COMStatus93A,
)
from serdes_coding.models.com_model_178A import COMStatus as COMStatus178A
from serdes_coding.reporting.com_report_93A import COMReport
from serdes_coding.reporting.com_report_178A import COMReport178A
from serdes_coding.reporting.com_report_base import (
    COMReportBase,
    COMReportDataWarning,
)
from serdes_coding.search.com_search_178A import COMSearchStatus as COMSearchStatus178A


def test_status_exports_do_not_control_plotting():
    for status_type in (
        COMStatus93A,
        COMSearchStatus93A,
        COMStatus178A,
        COMSearchStatus178A,
    ):
        assert "include_plots" not in signature(status_type.export).parameters
        assert not hasattr(status_type, "plot_summary")


def test_reporters_own_single_and_search_plot_exports():
    for reporter_type in (COMReport, COMReport178A):
        assert issubclass(reporter_type, COMReportBase)
        assert callable(getattr(reporter_type, "export_single_run"))
        assert callable(getattr(reporter_type, "export_search_run"))


class _DummyReport(COMReportBase):
    def __init__(self, cfg, status):
        self.calls = []
        super().__init__(cfg, status)

    def _map_canonical_fields(self):
        return {
            name: getattr(self.status, name, None)
            for name in self._CANONICAL_FIELDS
        }

    def _record(self, name):
        self.calls.append(name)
        return {name: name}

    def _plot_overview_stage(self, save_path):
        return self._record("overview")

    def _plot_paths_stage(self, path_idx, save_path):
        return self._record("paths")

    def _plot_equalizer_stage(self, save_path):
        return self._record("equalizer")

    def _plot_impairments_stage(self, save_path):
        return self._record("impairments")

    def _plot_pmf_stage(self, save_path):
        return self._record("pmf")

    def _plot_mlsd_stage(self, save_path):
        return self._record("mlsd")

    def _plot_search_stage(self, save_path):
        return self._record("search")


def test_common_report_flow_uses_canonical_stage_order():
    marker = object()
    status = SimpleNamespace(
        paths=[marker],
        equalizer=marker,
        pre_dte_impairment=marker,
        final_impairment=marker,
        pmf=marker,
        mlsd=marker,
        search=None,
    )
    report = _DummyReport(SimpleNamespace(), status)

    outputs = report.plot_single_run()

    assert report.calls == [
        "overview",
        "paths",
        "equalizer",
        "impairments",
        "pmf",
        "mlsd",
    ]
    assert list(outputs) == report.calls


def test_common_report_flow_omits_absent_optional_stages():
    status = SimpleNamespace(
        paths=[],
        equalizer=None,
        pre_dte_impairment=None,
        final_impairment=None,
        pmf=None,
        mlsd=None,
        search=None,
    )
    report = _DummyReport(SimpleNamespace(), status)

    assert report.plot_single_run() == {}
    assert report.calls == []


def test_incomplete_stage_warns_and_skips_renderer():
    class IncompleteReport(_DummyReport):
        def _plot_equalizer_stage(self, save_path):
            raise ValueError("stored response is unavailable")

    status = SimpleNamespace(
        paths=[],
        equalizer=object(),
        pre_dte_impairment=None,
        final_impairment=None,
        pmf=None,
        mlsd=None,
        search=None,
    )
    report = IncompleteReport(SimpleNamespace(), status)

    with pytest.warns(COMReportDataWarning, match="stored response is unavailable"):
        assert report.plot_equalizer() == {}


def test_version_adapters_expose_shallow_canonical_fields():
    marker = object()
    status_93a = SimpleNamespace(paths=[marker], dfe=marker, imp=marker, pmf=marker)
    report_93a = COMReport(SimpleNamespace(), status_93a)
    assert report_93a.paths is status_93a.paths
    assert report_93a.equalizer is marker
    assert report_93a.final_impairment is marker
    assert report_93a.pre_dte_impairment is None
    assert report_93a.mlsd is None

    impairment = SimpleNamespace(pre_dte=marker, post_ffe=marker)
    status_178a = SimpleNamespace(
        paths=[marker], dte=marker, imp=impairment, pmf=marker, mlsd=marker
    )
    report_178a = COMReport178A(SimpleNamespace(), status_178a)
    assert report_178a.paths is status_178a.paths
    assert report_178a.equalizer is marker
    assert report_178a.pre_dte_impairment is marker
    assert report_178a.final_impairment is marker
    assert report_178a.pmf is marker
    assert report_178a.mlsd is marker
