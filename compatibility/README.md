# Standalone Python compatibility exports

This directory contains single-file exports for legacy Python environments.
They are intentionally not a Python package.

- `utility_py36.py`: direct-import export for exact CPython 3.6.0.
- `utility_py37.py`: direct-import export for CPython 3.7.3.
- `requirements_py36.txt` and `requirements_py37.txt`: pinned dependencies.
- `validate_utility_py36.py`: exact Python 3.6.0 validation entry.

Add this directory to `sys.path`, run from this directory, or copy the selected
utility and matching requirements file to the target environment. Then import
the module directly:

```python
import utility_py36
# or
import utility_py37
```

These exports do not replace the maintained package under
`src/serdes_coding/utilities/`.
