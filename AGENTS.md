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
- Keep workbook parsing model-neutral in `io/com_excel_common.py`; place 93A and 178A field mappings only in their versioned `com_excel_io_93A.py` and `com_excel_io_178A.py` adapters. Preserve `com_excel_io.py` as the public compatibility facade.

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
- Manual 93A and 178A entries expose single_run/search_run; workbook search_config alone defines search ranges. The 178A entry supports EXEC_POLICY overrides. The 93A entry rejects non-empty EXEC_POLICY until native 93A execution profiles are defined.

## Protected COM model kernel

The COM mathematical kernel is read-only by default. Treat the following as
protected model code:

- `src/serdes_coding/models/com_model_93A.py`
- `src/serdes_coding/models/com_model_178A.py`
- PSD, PMF, sampled-response, FFT, S-parameter, and COM cascade primitives in
  `src/serdes_coding/utilities/psd.py`, `pmf.py`, `link.py`, and `sparam.py`

Work on reporting, plotting, search orchestration, workbook mapping, execution
policy, CLI or manual entry, CI, serialization, project structure, file moves,
or performance must not modify model equations, numerical data flow, physical
domains, normalization, or impairment composition as an incidental change.
General authorization to continue one of those tasks does not authorize a
model-kernel change.

Without an approved model change, agents may inspect the protected code, run
it, compare it with references, diagnose it, and add validation outside the
kernel. They must not edit protected behavior.

Before editing protected model behavior, prepare a **Core Model Change
Contract** for the user. It must state:

1. the reason for the change;
2. the governing specification equation, Ad Hoc reference, or other accepted
   source;
3. the current equation and data flow;
4. the proposed equation and data flow;
5. the exact functions and files to be changed;
6. the intermediate quantities expected to change;
7. the intermediate quantities and behavior that must remain unchanged;
8. the validation case, expected intermediate results, numerical tolerances,
   and final acceptance criteria;
9. the impact on 93A, 178A, single run, and search run; and
10. the rollback commit or other precise rollback boundary.

Protected behavior may be edited only after the user explicitly approves that
specific Core Model Change Contract. A general instruction such as "continue"
or "start modifying" in the context of another task is not approval. Approval
applies only to the files, functions, equations, and scope named in the
contract. Any newly discovered model change requires a revised contract and
new explicit approval.

Each approved model-behavior change must be isolated in a dedicated commit. Do
not mix it with file relocation, renaming, formatting, reporting, plotting,
search, workbook, CI, or unrelated refactoring. Do not use a broad
"synchronize" or package-layout commit to carry a mathematical change.

Validate model changes at intermediate boundaries, not only with final COM.
As applicable, preserve and compare pre-DTE PSDs and sigmas, `R_n`, selected
phase, `w_lim`, `b_lim`, MSE, post-DTE responses, each crosstalk path response,
`sigma_G`, ADC `V_qc` and `delta`, PMF component quantiles, and final COM. Add
equation-level invariants for the physical definition being changed. Run a
fixed golden case before any small or full search, and present the kernel diff
and validation evidence to the user before treating the change as complete.

Specification and project contracts are spec-first evidence. Do not infer a
model contract from current implementation and then use that inferred contract
to justify the implementation. Changes to model documentation require the same
approved Core Model Change Contract when they alter or assert mathematical
behavior.
