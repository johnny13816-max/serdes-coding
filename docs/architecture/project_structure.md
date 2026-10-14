# Project structure contract

This is the authoritative folder and runtime-location contract. AGENTS.md links to this document; inspect it before creating files or preparing a run.

## Canonical project root

On this machine: `C:/Users/johnn/Documents/Serdes-learn/serdes-coding`.
The canonical root owns `AGENTS.md`, `pyproject.toml`, `src/`, and `cases/`.
Do not infer the active project from a temporary checkout or stale tool cwd. Verify the resolved path and Git worktree before editing or installing dependencies. If the configured workspace points elsewhere, report the mismatch and use the explicitly agreed root.

## Folder ownership

```text
serdes-coding/
  .git/                       Git metadata
  .github/                    CI and workflow definitions
  .venv/                      local Python/IPython runtime; never committed
  cases/
    _templates/<model>/
      config.xlsx             fixed model-specific project-config template; channels blank
    <case_id>/
      case_manifest.yaml      case identity, provenance and model pairing
      README.md               case-specific purpose and limitations, when needed
      178A/
        config.xlsx           178A project config including channel references
        results/<run_name>/   generated 178A data and figures
      93A/
        config.xlsx           93A project config including channel references
        results/<run_name>/   generated 93A data and figures
  compatibility/              standalone direct-import exports for legacy Python
    README.md                  use and maintenance boundary
    utility_py36.py            CPython 3.6.0 compatibility export
    utility_py37.py            CPython 3.7.3 compatibility export
    requirements_py36.txt      Python 3.6 compatibility-test dependencies
    requirements_py37.txt      Python 3.7 compatibility-test dependencies
    validate_utility_py36.py   exact Python 3.6.0 validation entry
  docs/                       architecture, model, operation, planning and validation records
  reference_data/             immutable external inputs stored once with provenance
    COM_adhoc_config/          raw external configuration workbooks
      hansel/                  files received directly from Hansel
      ieee_matlab/             files distributed with IEEE COM Ad Hoc Matlab code
      manifest.csv             source, parser format, match status and checksum
    COM_channel_data/          existing channel S-parameters and source collateral
  scripts/                    orchestration, conversion and validation entries
  src/serdes_coding/
    interfaces/               user-facing GUI and interaction boundaries
    io/                       reference/project formats to typed runtime config
    models/                   COM dataclasses, equations and model pipeline
    reporting/                plots and result export
    search/                   candidate traversal, sweep, merge and finalization
    utilities/                reusable numerical and S-parameter primitives
  tests/                      automated validation
  .gitattributes              Git attribute rules
  .gitignore                  generated/local artifact exclusions
  AGENTS.md                   mandatory operating rules
  README.md                   repository entry and overview
  pyproject.toml              Python package and dependency definition
  poetry.lock                 resolved dependency lock
```

Optional top-level directories are limited to `tmp/`, `notebooks/`, and
`examples/`. Keep them only while they contain active disposable work or
maintained artifacts; remove empty placeholders. No other top-level entry may
be added until its owner and lifecycle are documented here and in `AGENTS.md`
in the same change. Generated output, downloaded workflow artifacts, recovery
copies, and local tool caches never justify a new root-level directory.

Optional `notebooks/` and `examples/` directories exist only while they contain maintained artifacts. Do not keep empty placeholder directories.

The files in `compatibility/` are intentional standalone exports for direct import in legacy Python environments. Keep each utility beside its matching requirements and validation material so the group can be copied without installing the main package. Exact-version validation environments such as `.venv-py360/` and `.venv-py373/` are disposable and must be recreated when needed; they are not part of the repository structure.

The runnable environment is `<project_root>/.venv`, never a venv inside `tmp/` or a nested checkout. Recreate a venv after relocating a project; do not copy it, because launchers contain absolute paths.
Temporary Git worktrees are not the default editing, installation, workbook or execution location. Create one only when explicitly requested, keep it outside the canonical project structure, and integrate and verify its changes at the canonical root before handoff. Remove obsolete recovery checkouts after their unique content is reconciled.

## Inputs and formats

Each active case uses `cases/<case_id>/<model>/config.xlsx`; generated output stays below that model's `results/<run_name>/`. A reusable project-config template belongs at `cases/_templates/<model>/config.xlsx` only after it passes the conversion schema reader and has no case-specific provenance or channel selection. A template may intentionally leave channel S4P paths blank and is not a runnable case until the channel rows are completed. Do not keep obsolete or empty placeholder templates. Downloaded workflow artifacts must be extracted into `results/` and their duplicate ZIP files removed.

178A workbooks contain `fixed_config`, `search_config`, `channels`, and `run_config`. Channel paths are defined exclusively in `config.xlsx`'s `channels` sheet and resolved relative to the workbook. S4P inputs remain in `reference_data/COM_channel_data/`; do not duplicate them under cases. Manifests record provenance; they do not override channel definitions. Legacy `config/config_178A.xlsx` and shared channel manifests are not templates for new runs.

`fixed_config` uses the existing Domain, Parameter, Parameter Class, Value, Unit and Description schema. Preserve model-defined PMF settings. Reference parameters, including MLSD_en, are intrinsic; project model-processing methods are fixed-config policy. Execution policy contains per-stage calculation/acceleration choices and may affect results. Validate reference-to-project and project-to-runtime mappings at their boundaries.

Excel I/O is versioned under `src/serdes_coding/io/`: `com_excel_common.py` owns model-neutral workbook parsing, `com_excel_io_93A.py` and `com_excel_io_178A.py` own their respective field-to-runtime mappings, and `com_excel_io.py` is the compatibility facade. Version-specific mapping must not be added to the common parser.

## Runtime entry ownership

This document owns runtime locations and folder placement. Execution steps and workflow behavior are maintained in:

- [`../operations/manual_execution.md`](../operations/manual_execution.md)
- [`../operations/search_execution.md`](../operations/search_execution.md)

All supported entries resolve inputs and outputs within the canonical case layout above. Operational controls do not redefine folder ownership, workbook semantics, or model equations.
