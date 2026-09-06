"""Backward-compatible facade for :mod:`serdes_coding.models.com_model_93A`."""

from .models import com_model_93A as _impl

globals().update({name: value for name, value in vars(_impl).items() if not name.startswith("__")})
__all__ = [name for name in vars(_impl) if not name.startswith("_")]
