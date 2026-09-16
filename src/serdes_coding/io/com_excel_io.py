"""Versioned COM workbook adapters with backward-compatible public names."""

from __future__ import annotations

from .com_excel_io_93A import excel_to_config_93A, excel_to_search_config_93A
from .com_excel_io_178A import excel_to_config_178A, excel_to_search_config_178A


def excel_to_config(excel_path: str):
    """Backward-compatible alias for the native 93A workbook adapter."""
    return excel_to_config_93A(excel_path)


def excel_to_search_config(excel_path: str):
    """Backward-compatible alias for the native 93A search adapter."""
    return excel_to_search_config_93A(excel_path)


__all__ = [
    "excel_to_config",
    "excel_to_config_93A",
    "excel_to_config_178A",
    "excel_to_search_config",
    "excel_to_search_config_93A",
    "excel_to_search_config_178A",
]
