"""Backward-compatible facade for :mod:`serdes_coding.models.com_model_178A`.

Run the canonical debug entry with:
``python -m serdes_coding.models.com_model_178A``.
"""

from .models import com_model_178A as _impl

globals().update({name: value for name, value in vars(_impl).items() if not name.startswith("__")})
__all__ = [name for name in vars(_impl) if not name.startswith("_")]
