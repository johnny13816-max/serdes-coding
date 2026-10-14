from inspect import signature

from serdes_coding.models.com_model_93A import (
    COMSearchStatus as COMSearchStatus93A,
    COMStatus as COMStatus93A,
)
from serdes_coding.models.com_model_178A import COMStatus as COMStatus178A
from serdes_coding.reporting.com_report_93A import COMReport
from serdes_coding.reporting.com_report_178A import COMReport178A
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
        assert callable(getattr(reporter_type, "export_single_run"))
        assert callable(getattr(reporter_type, "export_search_run"))
