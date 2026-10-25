"""Annex 178A model exceptions."""


class COMError(RuntimeError):
    """Base error for a COM calculation that cannot produce a valid result."""


class COMMainCursorError(COMError):
    """Raised when a sampled or equalized response violates the main-cursor contract."""


class COMTxfirMainCursorError(COMError):
    """Raised when a TX FFE candidate cannot keep c(0) as the main cursor."""


class COMLengthMismatchError(COMError):
    """Raised when a COM calculation violates an array-length contract."""


__all__ = [
    "COMError",
    "COMLengthMismatchError",
    "COMMainCursorError",
    "COMTxfirMainCursorError",
]
