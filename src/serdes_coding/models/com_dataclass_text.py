"""Human-readable text contracts for COM configuration and status objects.

This module owns presentation mechanics only.  Each COM dataclass owns the
semantic sections, labels, units, conversions, and inclusion decisions for its
fields through ``_text_sections()`` and ``_repr_fields()``.
"""

from __future__ import annotations

import builtins
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields, is_dataclass
from pathlib import Path
from typing import Any, Literal, Optional, TextIO

import numpy as np

from ..utilities.link import LinkConfig


SummaryMode = Literal["auto", "shape", "count", "stage"]


@dataclass(frozen=True)
class TextField:
    """One explicitly selected semantic field in a human-readable section."""

    source_name: str
    label: str
    value: Any
    stored_unit: Optional[str] = None
    display_unit: Optional[str] = None
    scale: float = 1.0
    summary: SummaryMode = "auto"

    @property
    def unit(self) -> Optional[str]:
        return self.display_unit or self.stored_unit


@dataclass(frozen=True)
class TextSection:
    """Ordered group of semantic fields selected by one COM dataclass."""

    title: str
    fields: tuple[TextField, ...]


class COMDataclassText(ABC):
    """Template for deterministic, bounded, human-readable COM object text."""

    _ARRAY_EDGE_ITEMS = 3

    def _field(
        self,
        source_name: str,
        label: str,
        *,
        stored_unit: Optional[str] = None,
        display_unit: Optional[str] = None,
        scale: float = 1.0,
        summary: SummaryMode = "auto",
    ) -> TextField:
        return TextField(
            source_name=source_name,
            label=label,
            value=getattr(self, source_name),
            stored_unit=stored_unit,
            display_unit=display_unit,
            scale=float(scale),
            summary=summary,
        )

    @abstractmethod
    def _text_sections(self) -> tuple[TextSection, ...]:
        """Return the class-owned semantic fields in display order."""

    @abstractmethod
    def _repr_fields(self) -> tuple[TextField, ...]:
        """Return the bounded fields used by the one-line representation."""

    def to_string(self) -> str:
        """Return deterministic multi-line text with explicit engineering units."""
        lines = [type(self).__name__]
        for section in self._text_sections():
            lines.append(f"  [{section.title}]")
            for field in section.fields:
                value_text = self._format_field(field, indent=4)
                if "\n" in value_text:
                    first, *rest = value_text.splitlines()
                    lines.append(f"    {field.label}: {first}")
                    lines.extend(f"      {line}" for line in rest)
                else:
                    lines.append(f"    {field.label}: {value_text}")
        return "\n".join(lines)

    def print(self, *, file: Optional[TextIO] = None) -> None:
        """Write ``to_string()`` to stdout or an explicitly supplied stream."""
        if file is not None and not hasattr(file, "write"):
            raise TypeError("file must be a writable text stream or None.")
        builtins.print(self.to_string(), file=file)

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        items = ", ".join(
            f"{field.source_name}={self._format_field(field, indent=0, concise=True)}"
            for field in self._repr_fields()
        )
        return f"{type(self).__name__}({items})"

    @staticmethod
    def _json_scalar(value: object) -> object:
        """Preserve the pre-existing JSON scalar conversion contract."""
        if value is None:
            return None
        if isinstance(value, np.integer):
            return int(value)
        if isinstance(value, np.floating):
            return float(value)
        if isinstance(value, np.bool_):
            return bool(value)
        if isinstance(value, complex):
            return {"real": value.real, "imag": value.imag}
        if isinstance(value, (str, int, float, bool)):
            return value
        return str(value)

    @classmethod
    def _json_value(cls, value: object) -> object:
        """Preserve the existing dataclass/config JSON snapshot behavior."""
        if isinstance(value, LinkConfig):
            return {
                "fb": cls._json_scalar(value.fb),
                "per_ui": cls._json_scalar(value.per_ui),
                "target_df": cls._json_scalar(value.target_df),
                "Nfft": cls._json_scalar(value.Nfft),
                "df": cls._json_scalar(value.df),
                "f_nyq": cls._json_scalar(value.f_nyq),
                "dt": cls._json_scalar(value.dt),
                "bt": cls._json_scalar(value.bt),
                "T_max": cls._json_scalar(value.T_max),
            }
        if isinstance(value, np.ndarray):
            return [cls._json_value(item) for item in value.tolist()]
        if isinstance(value, (list, tuple)):
            return [cls._json_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): cls._json_value(item) for key, item in value.items()}
        if is_dataclass(value):
            return {
                item.name: cls._json_value(getattr(value, item.name))
                for item in fields(value)
                if item.init
            }
        return cls._json_scalar(value)

    @staticmethod
    def _write_json(path: Path, data: dict[str, object]) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def _format_field(
        cls,
        field: TextField,
        *,
        indent: int,
        concise: bool = False,
    ) -> str:
        value = field.value
        if value is None:
            return "<not available>"

        if field.summary == "stage":
            return "complete" if value is not None else "not available"

        if field.summary == "count":
            try:
                count = len(value)
            except TypeError:
                count = int(value)
            return f"{count} {field.unit or 'count'}"

        if isinstance(value, COMDataclassText):
            return repr(value) if concise else value.to_string()

        scaled = cls._scale_value(value, field.scale)
        unit = field.unit
        text = cls._format_value(scaled, summary=field.summary, concise=concise)
        return f"{text} {unit}" if unit else text

    @staticmethod
    def _scale_value(value: Any, scale: float) -> Any:
        if scale == 1.0:
            return value
        if isinstance(value, np.ndarray):
            return value * scale
        if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool):
            return float(value) * scale
        return value

    @classmethod
    def _format_value(
        cls,
        value: Any,
        *,
        summary: SummaryMode,
        concise: bool,
    ) -> str:
        if isinstance(value, COMDataclassText):
            return repr(value) if concise else value.to_string()
        if isinstance(value, np.ndarray):
            return cls._format_array(value, shape_only=summary == "shape", concise=concise)
        if isinstance(value, (list, tuple)):
            return cls._format_sequence(value, count_only=summary == "count", concise=concise)
        if isinstance(value, dict):
            keys = sorted(str(key) for key in value)
            return f"dict(count={len(value)}, keys={cls._bounded_items(keys)})"
        if isinstance(value, (np.floating, float)):
            return f"{float(value):.9g}"
        if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
            return str(int(value))
        if isinstance(value, bool):
            return "enabled" if value else "disabled"
        if isinstance(value, str):
            return value
        if hasattr(value, "psd"):
            return cls._named_array_object(value, "psd")
        if hasattr(value, "ir"):
            return cls._named_array_object(value, "ir")
        if hasattr(value, "tf"):
            return cls._named_array_object(value, "tf")
        if hasattr(value, "pmf"):
            return cls._named_array_object(value, "pmf")
        if hasattr(value, "Nfft") and hasattr(value, "df"):
            return f"{type(value).__name__}(Nfft={value.Nfft}, df={float(value.df):.9g} Hz)"
        return f"<{type(value).__name__}>"

    @classmethod
    def _format_array(cls, value: np.ndarray, *, shape_only: bool, concise: bool) -> str:
        arr = np.asarray(value)
        base = f"shape={arr.shape}, dtype={arr.dtype}"
        if shape_only or arr.size == 0 or concise:
            return base
        flat = arr.ravel()
        edge = cls._bounded_items(flat)
        if np.issubdtype(arr.dtype, np.number) and not np.iscomplexobj(arr):
            finite = flat[np.isfinite(flat)]
            if finite.size:
                return f"{base}, min={float(np.min(finite)):.9g}, max={float(np.max(finite)):.9g}, values={edge}"
        return f"{base}, values={edge}"

    @classmethod
    def _format_sequence(cls, value: list[Any] | tuple[Any, ...], *, count_only: bool, concise: bool) -> str:
        if count_only or concise:
            return f"count={len(value)}"
        if not value:
            return "count=0, values=[]"
        if all(isinstance(item, (str, bool, int, float, np.integer, np.floating, type(None))) for item in value):
            return f"count={len(value)}, values={cls._bounded_items(value)}"
        types = [type(item).__name__ for item in value]
        return f"count={len(value)}, types={cls._bounded_items(types)}"

    @classmethod
    def _bounded_items(cls, values: Any) -> str:
        items = list(values)
        edge = cls._ARRAY_EDGE_ITEMS
        if len(items) <= 2 * edge:
            selected = items
        else:
            selected = items[:edge] + ["..."] + items[-edge:]
        return "[" + ", ".join(cls._format_atom(item) for item in selected) + "]"

    @staticmethod
    def _format_atom(value: Any) -> str:
        if value == "...":
            return "..."
        if value is None:
            return "<not available>"
        if isinstance(value, (np.floating, float)):
            return f"{float(value):.9g}"
        if isinstance(value, (np.integer, int)) and not isinstance(value, bool):
            return str(int(value))
        return str(value)

    @staticmethod
    def _named_array_object(value: Any, attr: str) -> str:
        array = np.asarray(getattr(value, attr))
        return f"{type(value).__name__}({attr}.shape={array.shape}, dtype={array.dtype})"


__all__ = ["COMDataclassText", "TextField", "TextSection"]
