# SerDes Coding Subproject Instructions

## Scope

This subproject contains Python code for SerDes and COM modeling experiments.

Code, tests, examples, notebooks, and package metadata belong here. IEEE PDFs,
raw reading notes, and theory summaries belong in `../serdes-theory-note/`.

This subproject is the main home for the user's personal after-work coding
artifact and public GitHub repository. It owns implementation decisions,
package structure, tests, examples, and repository hygiene for public-facing
SerDes/COM modeling code.

Theory or spec-reading discussions from `../serdes-theory-note/` may feed this
project with implementation guidance, API boundary recommendations, numerical
conventions, and validation ideas. Those discussions should become code here
only when the user explicitly asks to implement or port them into this
subproject.

## Conventions

- Keep importable source under `src/serdes_coding/`.
- Keep validation tests under `tests/`.
- Keep exploratory notebooks under `notebooks/`.
- Prefer small modules with clear numerical conventions.
- Document FFT, S-parameter, impedance, and COM equation conventions at the API boundary.
- Keep private PDFs, work documents, raw spec excerpts, and long-form theory notes out of this public coding repository.

## Helper Placement

Use this rule when deciding where to place validation helpers, conversion
helpers, and small internal functions:

- Use a module-level private helper when the function may be shared by multiple
  classes or module-level functions, or when the operation is a pure conversion
  that does not belong to one class instance.
- Use a class-level private helper when the helper is used by multiple methods
  in the same class and its meaning belongs to that class contract,
  representation, or validation boundary.
- Use a nested helper when the helper only supports one method and does not need
  independent reuse or testing.

Prefer choosing helper placement by semantic ownership, not only by the current
number of call sites. For example, an S4P-to-Sdd array conversion can be a
module-level helper even if it is initially called only by one constructor,
because the operation itself is not tied to one object instance.


## Mandatory project structure and execution location

- Follow [docs/project_structure_contract.md](docs/project_structure_contract.md) before creating folders, editing case inputs, installing environments, or preparing a run. It is the authoritative project layout reference.
- Canonical root on this machine: `C:/Users/johnn/Documents/Serdes-learn/serdes-coding`. Verify resolved paths and Git worktree; stale tool cwd is not authority.
- Use `<project_root>/.venv`, `<project_root>/src`, and `<project_root>/cases`. Do not edit, install, or run from `tmp/.codex-merge-main` or another temporary checkout unless the user explicitly requests that location.
- Temporary worktree changes must be integrated and verified at the canonical root before handoff. Never silently substitute a worktree for the project root or copy a venv across paths.
- Channels are defined in each model config.xlsx channels sheet. S4P files stay in reference_data; generated results belong in cases/<case_id>/<model>/results/<run_name>/.
- Manual 178A entry exposes single_run/search_run and EXEC_POLICY overrides; workbook search_config alone defines search ranges.
