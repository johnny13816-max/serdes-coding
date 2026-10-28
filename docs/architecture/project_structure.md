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
  AGENTS.md                   minimal mandatory gates and authority links
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

Each active case uses `cases/<case_id>/<model>/config.xlsx`; generated output stays below that model's `results/<run_name>/`. A reusable project-config template belongs at `cases/_templates/<model>/config.xlsx` only after it passes the conversion schema reader and has no case-specific provenance or channel selection. A template may intentionally leave channel S4P paths blank and is not a runnable case until the channel rows are completed. Do not keep obsolete or empty placeholder templates.

### Downloaded workflow artifacts

- 本機下載與解壓的完整位置為 `cases/<case_id>/<model>/results/<run_name>/`，其中 GitHub
  artifact 使用可辨識 run ID／attempt 的名稱，例如 `github_38745800222_attempt1`；不得覆寫不同
  run 或 attempt。無法確認 case/model 時，先保存在 `%TEMP%` 的專用子目錄並查明來源，不猜測歸屬。
- 本文件中的 artifact `results/` 均指上述 case/model 下的位置，不指 repository root；不得因此
  新增頂層 `results/`、`artifacts/` 或 `downloads/`。`.gitignore` 排除不等於目錄建立授權。
- 保留 artifact 內部相對結構；下載各分片時依 manifest／原 workflow 佈局組合，並以實際 output
  root 執行適用 verify。保留 run/attempt、source revision、input hashes、manifest 與驗證結果，
  缺少的 provenance 須明示，不以本機 HEAD 取代來源 revision。
- ZIP 只有在解壓成功、適用完整性驗證通過且確認為可重取的重複下載副本後才清除；不得把此條款
  用於刪除 reference input ZIP、唯一原始檔或他人既有資料。解壓或驗證失敗時保留可恢復副本。
- `%TEMP%` 驗證產物為可拋棄暫存；正式保留的 evidence 位於上述 case output，且應受 Git ignore
  規則排除。既有非標準位置另案盤點，不因本規則自動搬移、刪除或提交。
- CI runner 可使用 workflow 明定的暫存 output path，例如 `artifacts/partial_search`；此為 CI
  工作目錄內的暫時產物，不改變本機 canonical root 的 allowlist。本機執行相同驗證時，使用
  `%TEMP%` 專用子目錄或已定義的 case output，並明確傳入 output root。

### Workbook ownership

178A workbooks contain `fixed_config`, `search_config`, `channels`, and `run_config`. Channel paths are defined exclusively in `config.xlsx`'s `channels` sheet and resolved relative to the workbook. S4P inputs remain in `reference_data/COM_channel_data/`; do not duplicate them under cases. Manifests record provenance; they do not override channel definitions. Legacy `config/config_178A.xlsx` and shared channel manifests are not templates for new runs.

`fixed_config` uses the existing Domain, Parameter, Parameter Class, Value, Unit and Description schema. Preserve model-defined PMF settings. Reference parameters, including MLSD_en, are intrinsic; project model-processing methods are fixed-config policy. Execution policy contains per-stage calculation/acceleration choices and may affect results. Validate reference-to-project and project-to-runtime mappings at their boundaries.

Excel I/O is versioned under `src/serdes_coding/io/`: `com_excel_common.py` owns model-neutral workbook parsing, `com_excel_io_93A.py` and `com_excel_io_178A.py` own their respective field-to-runtime mappings, and `com_excel_io.py` is the compatibility facade. Version-specific mapping must not be added to the common parser.

## Runtime entry ownership

This document owns runtime locations and folder placement. Execution steps and workflow behavior are maintained in:

- [`../operations/manual_execution.md`](../operations/manual_execution.md)
- [`../operations/search_execution.md`](../operations/search_execution.md)

All supported entries resolve inputs and outputs within the canonical case layout above. Operational controls do not redefine folder ownership, workbook semantics, or model equations.
