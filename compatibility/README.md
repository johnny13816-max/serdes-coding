# Standalone Python compatibility exports

This directory contains single-file exports for legacy Python environments.
They are intentionally not a Python package.

- `utility_py36.py`: direct-import export for exact CPython 3.6.0.
- `utility_py37.py`: direct-import export for CPython 3.7.3.
- `build_utility_py37.py`: deterministically rebuilds the Python 3.7 export
  from the canonical utility modules.
- `validate_utility_py37.py`: checks Python 3.7 grammar plus representative
  S-parameter and eye-reconstruction behavior against the package utilities.
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

Rebuild and validate the Python 3.7 export from the repository root with:

```powershell
.\.venv\Scripts\python.exe compatibility\build_utility_py37.py
.\.venv\Scripts\python.exe compatibility\validate_utility_py37.py
```

These exports do not replace the maintained package under
`src/serdes_coding/utilities/`.
