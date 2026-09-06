"""Backward-compatible facade for :mod:`serdes_coding.io.com_excel_io`."""

from .io import com_excel_io as _impl

globals().update({name: value for name, value in vars(_impl).items() if not name.startswith("__")})
__all__ = [name for name in vars(_impl) if not name.startswith("_")]
