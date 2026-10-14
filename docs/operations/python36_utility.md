# Python 3.6.0 standalone utility

`utility_py36.py` is a single-file compatibility copy of
`serdes_coding.utilities`. It exists for systems that must run exact CPython
3.6.0 and is imported directly rather than installed as a package.

## Supported entry

The files live in `compatibility/` and remain direct-import modules rather
than a package. Run from that directory, add it to `sys.path`, or copy the
selected utility to the target environment:

```python
import sys
sys.path.insert(0, r"C:\Users\johnn\Documents\Serdes-learn\serdes-coding\compatibility")
import utility_py36
```

The compatibility file preserves the public classes, functions, and numerical
algorithms from `utility_py37.py`. Its type annotations are stored as strings
because CPython 3.6.0 cannot parse `from __future__ import annotations` and must
not evaluate forward references during import.

Two runtime adapters are confined to `utility_py36.py`: `typing.NoReturn` is
provided from `typing_extensions` before importing scikit-rf, and
`SparamModel.renormalized()` omits `s_def` when it is `None`. Both preserve the
Python 3.7.3 baseline behavior for the validated API.

## Dependencies

Install the pinned base dependencies into a CPython 3.6.0 environment, then
install scikit-rf without dependency resolution:

```powershell
python -m pip install -r compatibility/requirements_py36.txt
python -m pip install --no-deps --ignore-requires-python scikit-rf==0.24.1
```

Use a Python-3.6-compatible pip such as 21.3.1. The base dependency file pins
transitive packages because current releases no longer support the exact 3.6.0
patch release. scikit-rf 0.24.1 declares Python 3.7 in its wheel metadata, but
its source passes the Python 3.6 grammar check and the API subset used by this
file is validated on exact CPython 3.6.0. Install it with `--no-deps` so its
Python-3.7 dependency ranges do not replace the tested legacy pins.

The local validation runtime is `.venv-py360/python.exe`. It is an ignored,
project-local copy of the official CPython 3.6.0 embeddable runtime and does not
change the system Python or `PATH`.

## Validation

Run:

```powershell
.\.venv-py360\python.exe compatibility\validate_utility_py36.py
```

The validator requires `sys.version_info[:3] == (3, 6, 0)` and checks PSD, PMF,
TF/IR, S-parameter construction, renormalization, DC handling, resampling,
cascade, Touchstone `.s2p` output, and plotting.

The compatibility implementation was also compared with `utility_py37.py`
under its Python 3.7.3 baseline using deterministic fixtures. Derived grids,
PSD arrays and sigmas, autocorrelation, PMFs, TF/IR/SBR arrays, and S-parameters
must agree at `rtol=1e-10`, `atol=1e-12`.
