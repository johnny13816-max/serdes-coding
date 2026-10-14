"""Source-specific readers for external COM Ad Hoc workbooks.

These readers stop at an :class:`AdhocConfigSnapshot`. They do not create
the project's workbook or runtime COM configuration.
"""

from .registry import detect_adhoc_format, get_adhoc_parser, list_adhoc_formats
from .schema import (
    AdhocConfigSnapshot,
    AdhocFormatDescriptor,
    AdhocSetting,
    ProbeResult,
    ProbeStatus,
)

__all__ = [
    "AdhocConfigSnapshot",
    "AdhocFormatDescriptor",
    "AdhocSetting",
    "ProbeResult",
    "ProbeStatus",
    "detect_adhoc_format",
    "get_adhoc_parser",
    "list_adhoc_formats",
]
