"""Registry and explicit format detection for COM Ad Hoc workbook readers."""

from __future__ import annotations

from pathlib import Path

from .ieee8023dj_d3p2_cakr_178_v1 import IEEE8023djD3p2CAKR178V1Parser
from .schema import AdhocParser, ProbeResult, ProbeStatus


_PARSERS: tuple[AdhocParser, ...] = (IEEE8023djD3p2CAKR178V1Parser(),)


def list_adhoc_formats() -> tuple[str, ...]:
    return tuple(parser.descriptor.format_id for parser in _PARSERS)


def get_adhoc_parser(format_id: str) -> AdhocParser:
    matches = [parser for parser in _PARSERS if parser.descriptor.format_id == format_id]
    if len(matches) != 1:
        raise KeyError(f"Unknown COM Ad Hoc format ID: {format_id!r}.")
    return matches[0]


def detect_adhoc_format(workbook_path: str | Path) -> ProbeResult:
    """Return a unique exact/compatible parser match without guessing."""
    probes = [parser.probe(workbook_path) for parser in _PARSERS]
    exact = [probe for probe in probes if probe.status is ProbeStatus.EXACT]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return _ambiguous(exact)

    compatible = [probe for probe in probes if probe.status is ProbeStatus.COMPATIBLE]
    if len(compatible) == 1:
        return compatible[0]
    if len(compatible) > 1:
        return _ambiguous(compatible)

    return ProbeResult(
        status=ProbeStatus.UNKNOWN,
        descriptor=None,
        matched_signatures=(),
        missing_signatures=(),
        candidates=(),
    )


def _ambiguous(probes: list[ProbeResult]) -> ProbeResult:
    return ProbeResult(
        status=ProbeStatus.AMBIGUOUS,
        descriptor=None,
        matched_signatures=(),
        missing_signatures=(),
        candidates=tuple(
            probe.descriptor.format_id
            for probe in probes
            if probe.descriptor is not None
        ),
    )


__all__ = ["detect_adhoc_format", "get_adhoc_parser", "list_adhoc_formats"]
