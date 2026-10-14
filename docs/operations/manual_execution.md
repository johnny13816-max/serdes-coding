# Manual execution

This runbook describes the supported local debug entries. Model equations and workbook field semantics are owned by the model and configuration documents.

## COM Ad Hoc configuration conversion GUI

For a double-click Windows entry, run:

```text
scripts/run_config_conversion_gui.bat
```

The batch file resolves the repository root from its own location, requires
the canonical `.venv`, and adds `src` to `PYTHONPATH`. It does not silently
fall back to a system Python installation. The GUI lets you select version 93A
or 178A and automatically loads the matching template from
`cases/_templates/<version>/config.xlsx`; users do not choose a base workbook.
Both project versions have mappings from the currently registered Ad Hoc
format. 93A package conversion intentionally reduces the selected-side package
to its maximum supported value; the mapping table records that reduction for
review. The fixed single-run baselines for `c_m2`, `c_m1`, `c_1`, `g_DC`, and
`g_DC2` default to zero, while their Ad Hoc ranges map to `search_config`.

To launch with a source workbook preselected:

```powershell
.\.venv\Scripts\python.exe -m serdes_coding.interfaces.com_config_conversion_gui `
  --source reference_data\COM_adhoc_config\<source_id>\adhoc_config.xlsx
```

In the GUI, select the version, enter a case ID (which is also the case-folder
name), and choose an Ad Hoc workbook stored under
`reference_data/COM_adhoc_config/`. Load the mapping, resolve failed fields,
review permitted empty fields and select the required channel S4P files. The
GUI writes to `cases/<case_id>/<version>/config.xlsx` and asks before replacing
an existing config.

Automatic conversion requires an exact registered source-format match. Export
writes the fixed project workbook together with `.conversion.json` provenance
and a `.mapping.csv` field audit. Missing fields and invalid cross-field
combinations block export.

The mapping table has three user-facing outcomes: `success`, `fail`, and
`empty`. Acquisition method (direct, converted, derived, or reduced) and a
manual-edit marker are separate columns, so a manual edit is never mistaken for
a successful source mapping. Select a row to see its source and conversion
rationale. The conversion audit retains both the original source result and the
adopted value.

## Environment

Run from the canonical project root with its local environment:

```text
C:/Users/johnn/Documents/Serdes-learn/serdes-coding
```

Use `<project_root>/.venv`. Before a handoff, verify the interpreter, imported module path, workbook channel resolution, and output write access at the canonical root.

## Versioned entries

The supported manual files are:

- `src/serdes_coding/models/com_model_93A.py`
- `src/serdes_coding/models/com_model_178A.py`

Their `if __name__ == "__main__"` blocks are user-owned debug entries. They may be launched from IPython with `%run com_model_93A.py` or `%run com_model_178A.py` while the current directory is the model directory. Package execution with `python -m serdes_coding.models.<module>` is also supported from an installed project environment.

Both entries expose:

- `CASE_ID`
- `RUN_MODE`, limited to `single_run` or `search_run`
- `EXEC_POLICY`
- `SEARCH_OUTPUT_NAME`

Search ranges come from the workbook's `search_config`; a reduced range is still `search_run`. The 178A entry accepts execution-policy overrides for its defined run profiles. The 93A entry currently rejects a non-empty `EXEC_POLICY` because native 93A execution profiles have not been defined.

## Paths

For model `<version>`, the entry resolves:

```text
cases/<case_id>/<version>/config.xlsx
cases/<case_id>/<version>/results/<run_name>/
```

`single_run` uses the `single_run` result directory. `search_run` uses `SEARCH_OUTPUT_NAME`. Output-path failures must be fixed at the canonical case path rather than redirected to a temporary checkout.

## Result ownership

The entry loads typed configuration through the versioned Excel adapter, runs the selected model, exports numerical status, and invokes the version-specific reporting layer. Reporting consumes config and status; it does not recalculate protected model quantities.
