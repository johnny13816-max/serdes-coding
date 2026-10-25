# Software layers

Dependencies flow downward through these layers. A lower layer must not import workflow or interface behavior from a higher layer.

```text
Layer 1  Entry and interface
         manual __main__, scripts, GitHub Actions, workbook selection

Layer 2  Workflow
         single run, search sweep, search final, finalization, reporting

Layer 3  COM model orchestration
         versioned COM classes, stage ordering and status lifecycle

Layer 4  Domain stages
         channel, pre-DTE, DTE/MMSE, post-DTE, PMF/COM, MLSD

Layer 5  Domain utilities
         S-parameters, sampled responses, PSD, PMF, packages and channels

Layer 6  Numerical foundation
         NumPy/SciPy operations, interpolation, convolution, FFT and solving
```

## Ownership rules

- Entry code selects paths, run mode, and execution policy. It does not own COM equations.
- Excel I/O maps workbook data into typed config. Models do not read workbooks.
- Workflow code traverses candidates and persists results. It does not redefine model stages.
- Model orchestration owns stage order and status lifecycle.
- A stage owns its declared inputs, outputs, equations, and validation boundary.
- Reporting reads status and config snapshots; it does not reconstruct model results.
- Utilities contain reusable domain or numerical primitives and do not depend on search, reporting, or manual entry.
- Version-neutral parsing belongs in `io/com_excel_common.py`; version mapping belongs in the versioned adapter.

## Current module ownership

| Location | Responsibility |
|---|---|
| `serdes_coding/__init__.py` | Public package exports; 93A base symbols are imported directly and optional 178A/report/search adapters are loaded lazily. |
| `models/com_model_93A.py` | 93A dataclasses, orchestration, stages, model-specific helpers, and the 93A manual entry. |
| `models/com_model_178A.py` | Compatibility facade, current stage implementations, orchestration, and the 178A manual entry. |
| `models/com_178a/config.py` | Version-owned 178A configuration contracts. |
| `models/com_178a/status.py` | Version-owned 178A path and calculation-state contracts. Its current `COMStatus.export()` is a compatibility shim pending full reporting ownership. |
| `models/com_178a/errors.py` | Version-owned 178A model exceptions. |
| `models/com_dataclass_text.py` | Version-neutral text-formatting mechanics; each model dataclass retains ownership of semantic fields, units, and display order. |
| `io/com_excel_common.py` | Shared workbook table parsing and channel-row handling. |
| `io/com_excel_io_93A.py` | Project and legacy Ad Hoc workbook mapping into 93A typed configuration. |
| `io/com_excel_io_178A.py` | Project workbook and run-profile mapping into 178A typed configuration. |
| `io/com_excel_io.py` | Compatibility facade for versioned Excel adapter functions; unversioned aliases target 93A. |
| `io/adhoc/` | Labelled source-format-specific COM Ad Hoc detection and parsing into source snapshots. |
| `io/conversion/` | Source-snapshot to fixed project-workbook mapping, validation, export, and audit. |
| `interfaces/com_config_conversion_gui.py` | Manual review and override UI over conversion drafts; owns no mapping rules or COM equations. |
| `search/com_search_93A.py` | File-backed 93A candidate planning, partial execution, merge, and finalization. |
| `search/com_search_178A.py` | File-backed 178A candidate planning, partial execution, merge, and finalization. |
| `search/com_search_gui_178A.py` | Legacy GUI adapter over the 178A search API; its case paths are not canonical yet. |
| `reporting/com_report_common.py` | Shared figure construction, canonical plot paths, PNG validation, and manifest writing. |
| `reporting/com_report_base.py` | Shared canonical fields, `plot_<stage>()` orchestration, optional-stage warnings, and single/search export lifecycle. |
| `reporting/com_report_93A.py` | 93A presentation and plots derived from config and status. |
| `reporting/com_report_178A.py` | 178A presentation and plots derived from config and status. |
| `utilities/link.py` | `LinkConfig`, `LinkSegment`, and `SampledResponse`. |
| `utilities/psd.py` | `ContinuousPSD`, `SampledPSD`, and the `OneSidePSD` compatibility alias. |
| `utilities/sparam.py` | `SparamModel` and `SparamProcessor`. |
| `utilities/pmf.py` | `Pmf1D` and PMF utility functions. |

There are no current root-level `link_segment.py` or `pmf_handler.py` compatibility modules. Documentation and new imports must use the modules listed above.

## Current dependency notes

- `utilities/link.py` imports PSD containers; `utilities/psd.py` accepts link-compatible objects structurally and does not import the link module at runtime.
- `utilities/sparam.py` depends on link-domain types for conversion into scalar link responses.
- Search and reporting may depend on versioned model types. The target boundary
  forbids model dependencies on search workflow or interface code. The current
  178A `COM.run(search=...)` entry is a tracked transition exception: it imports
  search contracts and dispatch, and a later ARC-178A-004 batch must invert that
  edge without changing the one-candidate model.
- The 93A and 178A root `COM` orchestrators and root `COMStatus` containers are
  version-owned standalone types. One version must not acquire another
  version's stage methods, status fields, search helpers, or reporter through
  class inheritance.
- 178A config, path/status, PMF-status, exception, and search contracts are
  version-owned. `io/com_excel_common.py` parses common channel rows and receives
  the version-owned channel-config constructor from each adapter.
- Remaining 178A-to-93A dependencies are limited by an executable ratchet to
  S-parameter/filter inheritance and four stage helpers. Later stage-migration
  batches must reduce that allowlist; new dependencies are forbidden.

## Helper placement

Use the narrowest scope that matches actual reuse:

- Cross-module public behavior belongs in an intentional public module API.
- Logic shared by multiple classes or functions in one module belongs in a module-level private helper unless it is part of the public API.
- Logic shared by multiple methods of one class belongs in a private instance, class, or static method.
- Logic used by one method remains inside that method or in a nested helper.

Do not move a helper into common infrastructure because names or array shapes look similar. Its mathematical and data contracts must be shared and verified.

## Model sharing rule

Code moves into a common utility only when its mathematical definition and data contract are genuinely shared by 93A and 178A. Similar names or array shapes are not sufficient evidence. Version differences remain explicit in their model or adapter until validated as equivalent.
