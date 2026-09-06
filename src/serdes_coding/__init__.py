"""SerDes coding utilities and COM modeling experiments."""

from .models.com_model_93A import (
    COM as COM93A,
    COMChannelConfig,
    COMConfig,
    COMDFEConfig,
    COMDFEStatus,
    COMFilterConfig,
    COMImpairmentConfig,
    COMImpairmentStatus,
    COMPMFConfig,
    COMPMFRuntimeConfig,
    COMPMFStatus,
    COMPath,
    COMSearchCandidate,
    COMSearchConfig,
    COMSearchRow,
    COMSearchStatus,
    COMSharedPath,
    COMPkgConfig,
    COMStatus,
    IEEECOMFilter,
    IEEECOMSparam,
)
from .utilities.link import ContinuousPSD, OneSidePSD, SampledPSD, SampledResponse
from .utilities.sparam import SparamModel


def __getattr__(name: str):
    """Load optional 178A public APIs without pre-importing its runnable module.

    This keeps the versioned model modules lazy and avoids importing the
    runnable debug module during package initialization.
    """
    if name == "COM178A":
        from .models.com_model_178A import COM

        return COM
    if name == "COMReport178A":
        from .reporting.com_report_178A import COMReport178A

        return COMReport178A
    if name in {
        "excel_to_config",
        "excel_to_config_93A",
        "excel_to_config_178A",
        "excel_to_search_config",
        "excel_to_search_config_178A",
    }:
        from .io import com_excel_io

        return getattr(com_excel_io, name)
    if name in {
        "COMSearchRow178A",
        "COMSearchStatus178A",
        "SearchArtifacts178A",
        "create_search_plan_178A",
        "run_partial_group_178A",
        "merge_partial_results_178A",
        "finalize_search_178A",
        "run_full_search_178A",
    }:
        from .search import com_search_178A

        source_name = {
            "COMSearchRow178A": "COMSearchRow",
            "COMSearchStatus178A": "COMSearchStatus",
            "SearchArtifacts178A": "SearchArtifacts",
            "create_search_plan_178A": "create_search_plan",
            "run_partial_group_178A": "run_partial_group",
            "merge_partial_results_178A": "merge_partial_results",
            "finalize_search_178A": "finalize_search",
            "run_full_search_178A": "run_full_search",
        }[name]
        return getattr(com_search_178A, source_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "COM178A",
    "COMReport178A",
    "COM93A",
    "COMSearchRow178A",
    "COMSearchStatus178A",
    "SearchArtifacts178A",
    "COMChannelConfig",
    "COMConfig",
    "COMDFEConfig",
    "COMDFEStatus",
    "COMFilterConfig",
    "COMImpairmentConfig",
    "COMImpairmentStatus",
    "COMPMFConfig",
    "COMPMFRuntimeConfig",
    "COMPMFStatus",
    "COMPath",
    "COMSearchCandidate",
    "COMSearchConfig",
    "COMSearchRow",
    "COMSearchStatus",
    "COMSharedPath",
    "COMPkgConfig",
    "COMStatus",
    "ContinuousPSD",
    "IEEECOMFilter",
    "IEEECOMSparam",
    "OneSidePSD",
    "SampledPSD",
    "SampledResponse",
    "SparamModel",
    "excel_to_config",
    "excel_to_config_93A",
    "excel_to_config_178A",
    "excel_to_search_config",
    "excel_to_search_config_178A",
    "create_search_plan_178A",
    "run_partial_group_178A",
    "merge_partial_results_178A",
    "finalize_search_178A",
    "run_full_search_178A",
]
