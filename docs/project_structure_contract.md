# Project structure contract

This is the authoritative folder and runtime-location contract. AGENTS.md links to this document; inspect it before creating files or preparing a run.

## Canonical project root

On this machine: `C:/Users/johnn/Documents/Serdes-learn/serdes-coding`.
The canonical root owns `AGENTS.md`, `pyproject.toml`, `src/`, and `cases/`.
Do not infer the active project from a temporary checkout or stale tool cwd. Verify the resolved path and Git worktree before editing or installing dependencies. If the configured workspace points elsewhere, report the mismatch and use the explicitly agreed root.

## Folder ownership

```text
serdes-coding/
  AGENTS.md                    operating rules
  pyproject.toml               Python package and dependencies
  .venv/                       local Python/IPython environment
  src/serdes_coding/
    io/                        reference/project formats to typed runtime config
    models/                    COM dataclasses, equations and model pipeline
    utilities/                 reusable numerical and S-parameter primitives
    search/                    candidate traversal, sweep, merge and finalization
    reporting/                 plots and result export
  cases/<case_id>/
    case_manifest.yaml         case provenance and model pairing
    178A/config.xlsx            model inputs including channel references
    178A/results/<run_name>/    generated result data and figures
    93A/config.xlsx             when the case supports 93A
    93A/results/<run_name>/     generated 93A results
  reference_data/               external datasets and provenance
  templates/                   reusable workbook/input templates
  docs/                        contracts, decisions, plans and validation notes
  scripts/                     orchestration and validation commands
  tests/                       automated tests
  notebooks/                   exploratory notebooks
  examples/                    maintained usage examples
  .github/                     CI and workflow definitions
  tmp/                         disposable scratch or recovery backups only
```

The runnable environment is `<project_root>/.venv`, never a venv inside `tmp/` or a nested checkout. Recreate a venv after relocating a project; do not copy it, because launchers contain absolute paths.
Temporary Git worktrees are not the default editing, installation, workbook or execution location. Use a different worktree only when explicitly requested. Integrate and verify its changes at the canonical root before handing off a runnable path. Existing `tmp/.codex-merge-main` is a recovery source only, not an active execution location.

## Inputs and formats

178A workbooks contain `fixed_config`, `search_config`, `channels`, and `run_config`. Channel paths are defined exclusively in `config.xlsx`'s `channels` sheet and resolved relative to the workbook. S4P inputs remain in `reference_data/COM_channel_data/`; do not duplicate them under cases. Manifests record provenance; they do not override channel definitions. Legacy `config/config_178A.xlsx` and shared channel manifests are not templates for new runs.

`fixed_config` uses the existing Domain, Parameter, Parameter Class, Value, Unit and Description schema. Preserve model-defined PMF settings. Reference parameters, including MLSD_en, are intrinsic; project model-processing methods are fixed-config policy. Execution policy contains per-stage calculation/acceleration choices and may affect results. Validate reference-to-project and project-to-runtime mappings at their boundaries.

Excel I/O is versioned under `src/serdes_coding/io/`: `com_excel_common.py` owns model-neutral workbook parsing, `com_excel_io_93A.py` and `com_excel_io_178A.py` own their respective field-to-runtime mappings, and `com_excel_io.py` is the compatibility facade. Version-specific mapping must not be added to the common parser.

## Manual execution

The supported manual entries are `src/serdes_coding/models/com_model_93A.py` and `src/serdes_coding/models/com_model_178A.py`, executed with `%run com_model_93A.py` or `%run com_model_178A.py` from their directory. Both define case/config/output selection and RUN_MODE. RUN_MODE has only `single_run` and `search_run`; search ranges come exclusively from workbook search_config, and a smaller grid is still search_run. The 178A entry also applies EXEC_POLICY overrides for single_run, search_sweep and search_final. The 93A entry exposes the same top-level control name but rejects non-empty overrides until native 93A execution profiles are defined. Batching, top-K and timeout remain internal controls.

Before handoff, verify the interpreter and imported module paths, workbook channel resolution, and output write access at the canonical root. Output-path permission failures must be resolved there, not by silently redirecting to tmp or a different checkout. Record changes to folder ownership in this document and summarize them in AGENTS.md.


## GitHub Actions search

The workbook search workflow accepts only case_id. It reads cases/<case_id>/178A/config.xlsx. Small and full runs use separate case workbooks; fixed_config, channels and run_config remain identical. Internal workers partition all workbook candidates without downsampling, with at most 256 workers and 20 concurrent jobs. Artifacts carry the input SHA256 fingerprints, complete group CSVs, final CSV, per-candidate plot manifests and a validation summary. Finalize always exports plots. Any selected final candidate failure fails the stage after writing diagnostic CSVs. A separate job downloads the final artifact and verifies selected candidate coverage and each PNG hash.
