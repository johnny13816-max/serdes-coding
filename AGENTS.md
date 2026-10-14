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

## High-Leverage Collaboration Mode

Default to work that is difficult, repetitive, or substantially faster for
Codex to execute: cross-file audits, numerical comparison, automation, tests,
Git/GitHub operations, coordinated implementation, and documentation upkeep.
Reserve user attention for decisions that materially affect specification
interpretation, mathematical-model boundaries, branch selection, public claims,
or Core Model Change Contract approval.

- Report in this order: conclusion, confirmed error or parallel method, key
  numerical evidence, completed work, and next action.
- Do not repeat established background or narrate routine reads, commands, and
  passing checks. Give progress updates only at start, a material finding or
  blocker, and completion.
- Resolve low-risk choices from code, project documents, prior decisions, and
  conservative defaults. Bundle any truly direction-changing questions.
- Close known issues: fix confirmed errors through the required contract,
  represent legitimate design differences as named branches, and record any
  deferred item with its owner, reason, and closure condition.
- Keep the requested stage in scope. Finish and report it before expanding into
  another major investigation.

### Stage Gate Before Search Or Advancing The Model Flow

Before starting a search run or moving to the next COM stage, audit every open
error, contract, and reference-method difference in the stages that feed the
requested execution target.

- State the search objective and final execution target explicitly, then trace
  which model stages can affect candidate ranking and the reported result.
- Block advancement when an unresolved confirmed error or an unimplemented
  selected method can change any upstream input, ranking objective, or final
  reported quantity. Present the required Core Model Change Contract when the
  blocker belongs to protected model code.
- An open item outside the selected execution path does not block the run, but
  report its exclusion and the reason before proceeding. For example, a search
  with `search_sweep.target="mse"` and `search_final.target="dfe"` does not
  execute or depend on the MLSD stage.
- Do not reopen a completed stage from a speculative note. Distinguish a
  verified implementation gap from an unverified research candidate, and state
  the evidence needed to promote a candidate into a project task.


## Mandatory project structure and execution location

The repository root is governed by an allowlist. Do not create a new top-level
file or directory unless its ownership is first added to both this section and
`docs/architecture/project_structure.md`. Move misplaced content to its owning
directory or delete it when it is generated, duplicated, obsolete, or empty.

Allowed top-level directories are `.git/`, `.github/`, `.venv/`, `cases/`,
`compatibility/`, `docs/`, `reference_data/`, `scripts/`, `src/`, and `tests/`. `tmp/`,
`notebooks/`, and `examples/` are optional and may exist only while they contain
active disposable work, maintained notebooks, or maintained examples.

Allowed top-level project files are `.gitattributes`, `.gitignore`, `AGENTS.md`,
`README.md`, `pyproject.toml`, and `poetry.lock`. Standalone legacy-Python
exports, requirements and validators belong in `compatibility/`; they must not
be scattered across the repository root. Update this allowlist and the structure
contract together before adding any other top-level entry.

- Follow [docs/architecture/project_structure.md](docs/architecture/project_structure.md) before creating folders, editing case inputs, installing environments, or preparing a run. It is the authoritative project layout reference.
- Canonical root on this machine: `C:/Users/johnn/Documents/Serdes-learn/serdes-coding`. Verify resolved paths and Git worktree; stale tool cwd is not authority.
- Use `<project_root>/.venv`, `<project_root>/src`, and `<project_root>/cases`. Do not edit, install, or run from `tmp/.codex-merge-main` or another temporary checkout unless the user explicitly requests that location.
- Temporary worktree changes must be integrated and verified at the canonical root before handoff. Never silently substitute a worktree for the project root or copy a venv across paths.
- Channels are defined in each model config.xlsx channels sheet. S4P files stay in `reference_data/COM_channel_data/`; generated results belong in `cases/<case_id>/<model>/results/<run_name>/`.
- Preserve external COM Ad Hoc workbooks under `reference_data/COM_adhoc_config/<source_id>/`, where `source_id` names the supplying source (for example, `hansel` or `ieee_matlab`). Keep parser format IDs and match status in `manifest.csv`; they do not define storage paths. Preserve original workbooks, record batch/probe/hash metadata, and do not edit copied originals.
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

## Documentation governance

- `docs/README.md` is the documentation entry point. Read it before adding or relocating project documentation.
- `docs/architecture/documentation_contract.md` defines the required stage-first model documentation structure.
- `docs/architecture/software_layers.md` defines dependency direction and code ownership.
- Model documentation is organized by version and stage. A stage owns the stable input/output and status-lifecycle contract; functional blocks explain algorithms inside that stage; individual helpers remain in docstrings or generated API references unless independently significant.
- Changes to stage boundaries, config/status dataclasses, workbook mappings, semantic call trees, or reporting dependencies must update the corresponding authoritative document in the same change.
- Do not treat historical plans or change contracts as current architecture unless `docs/README.md` identifies them as authoritative.
- `docs/models/<version>/branch_behavior_registry.md` is the authoritative location for each COM version's algorithm, numerical, execution, and applicable utility branch behavior. The current 178A registry is `docs/models/178A/branch_behavior_registry.md`; create the corresponding version registry when another model gains configurable parallel behavior. Any addition, modification, rename, merge, or removal of a branch must update the applicable registry in the same change.
- Every branch entry must identify its stage, runtime control, project default, all alternate behaviors, `align_to_ref` participation, numerical owner, responsibility boundary, quantities allowed to change, quantities that must remain unchanged, and validation evidence. Inputs, equivalent representations, common bug fixes, and single-valued controls must be explicitly classified instead of being presented as parallel algorithms.
- Do not add a nested per-stage policy dataclass under `COMConfig.policy`. The 178A runtime branch controls stay one level deep in `COMPolicyConfig`; stage helpers receive the named values they need. A proposed exception requires an explicitly approved configuration-architecture change contract.
- A Core Model Change Contract that adds or changes a branch is incomplete until it names the corresponding branch-registry row and the documentation/tests that will be updated.

## Repository cleanup safety

- Before deleting or relocating project material, classify it as source, authoritative input, external reference, generated output, scratch, or unresolved recovery data.
- Preserve user changes and external provenance until their canonical replacement is identified and verified.
- The retired `tmp/.codex-merge-main` worktree was removed on 2026-09-25 after its branch, binary patch, inventory, and unique inputs were preserved in `C:/Users/johnn/Documents/Serdes-learn/serdes-coding-recovery-20260925`. Do not recreate a nested checkout under this project.
- Do not combine repository cleanup, file relocation, or documentation restructuring with a protected COM model change.

## Configuration contract

GUI and conversion changes must follow `docs/architecture/adhoc_mapping_contract.md`
and the executable registry `io/conversion/mapping_rules.py`. Update the field
table in `docs/architecture/adhoc_mapping_fields.md` with registry changes.
Do not introduce GUI-only requiredness, hidden source defaults, or mapping rules
in widget callbacks. User channel selection and project policies remain separate.

Use [docs/architecture/configuration_architecture.md](docs/architecture/configuration_architecture.md) as the mandatory project-wide configuration contract and the version-specific `docs/models/<version>/config_tree.md` as the field inventory.

- Keep three boundaries distinct: external Ad Hoc → project config, project config → runtime config, and specification-defined fallback performed inside the runtime implementation.
- Project-config fields are version-specific. Similar workbook layout does not authorize copying a parameter or feature from 178A into 93A (or vice versa).
- Classify fixed configuration as `intrinsic`, `policy`, or `derived`. Keep case identity/provenance in the case-config domain. Do not classify runtime-only values as project-config fields.
- `intrinsic` means a COM Ad Hoc/spec input. Required source values must be supplied; if the source lacks one, conversion fails. An intrinsic may be blank only where the applicable specification permits omission and the versioned field contract says blank maps to `None`.
- `policy` means a project-defined control absent from COM Ad Hoc and the specification. Every policy field has an explicit project default and is managed separately from Ad Hoc mapping.
- `derived` fields remain in the project template when the approved version contract requires them. Their conversion formula and runtime destination must be documented; do not silently remove or relabel them as policy.
- Distinguish an absent workbook row/schema field from a blank cell. An absent required row is a schema/configuration error. A blank cell is valid only for an explicitly optional field; it maps to `None` and leaves any specification-defined fallback to the runtime owner.
- Never copy a specification-defined runtime fallback into a second project-config field. Keep the project field empty when the source omits that optional value; implement the accepted fallback once at its runtime owner.
- Conversion UI status is limited to `success`, `fail`, and `empty`: successful mapping, blocked/invalid mapping, and an allowed blank. Policy editing is a separate UI area and does not appear as an Ad Hoc mapping result.
- Keep the shared workbook presentation format aligned across 93A and 178A, including the `Parameter Class` column. Keep each version's parameter inventory native; do not add unsupported fields merely to make the lists look alike.
- Document both mapping directions and their requiredness/default semantics in the version tree. If implementation disagrees with this contract, document it as a gap; do not silently describe the desired behavior as implemented.
- Every parameter row in a project config must have a runtime destination or an explicit case/provenance purpose. Do not keep an orphan row merely because an older workbook contained it. Conversely, workbook inputs required to construct a supported runtime configuration must be present in that version's project schema.
- Do not expose internal runtime/dataclass fields that are calculated, transient, or owned by execution code as project parameters unless the version contract explicitly makes them user/project configurable. `Parameter Class` and other workbook structure metadata are schema metadata, not runtime parameters.
