# Configuration architecture

> Status: authoritative project-level configuration contract.
>
> Field ownership and current implementation are recorded in each version's `docs/models/<version>/config_tree.md`.

## Configuration boundaries

```text
COM Ad Hoc source workbook ──► project config workbook ──► typed/runtime config
                                      │                            │
                                      └── project policy defaults  └── specification-defined fallback
```

These are three distinct responsibilities:

1. **Ad Hoc → project config** parses a source-specific workbook, maps supported fields into the selected version's fixed project schema, converts units, and reports missing or unsupported source requirements. This mapping is version-specific.
2. **Project config → typed/runtime config** is owned by the versioned `com_excel_io_XX()` adapter. It validates the workbook and constructs typed runtime dataclasses. It must not parse external Ad Hoc variants.
3. **Runtime fallback** implements a fallback explicitly defined by the applicable specification or accepted runtime contract. It stays at the runtime owner; conversion must not copy it into another project field.

Project-level presets are resolved at boundary 2. For 178A,
`run_config.control.execution_profile` selects a versioned facade profile:
`project_standard`, `sicopr_reference_v1`, or `custom`. The adapter expands the
selected profile into named runtime methods and effective execution profiles
before `COMConfig` is constructed. Legacy `fixed_config.align_to_ref` remains a
read-only compatibility alias and is not emitted by new templates.
The model and utilities receive those named values and never branch on the
workbook switch. The config snapshot records the applied profile and each
raw/effective override.

The project workbook format is stable within each COM version. Similar presentation across versions does not make their parameter sets interchangeable. Channel files are selected in the workbook's `channels` sheet and stored under `reference_data/COM_channel_data/`.

## Configuration domains and classes

Workbook `Domain` describes the user's intent for a setting; workbook `Parameter Class`
describes its source/runtime treatment. These are independent axes and must not
be substituted for one another. For example, `algorithm_policy` may use the
existing `policy` class, while a construction-derived physical value uses
`Domain=intrinsic` and `Parameter Class=derived`.

Every user-configurable field has exactly one primary domain, plus a separate
exposure level:

| Domain | Meaning |
|---|---|
| `case` | Case identity and source note; adapter/report metadata, not `COMConfig`. |
| `intrinsic` | System, specification, and physical conditions; maps directly to physical runtime fields without a `cfg.intrinsic` wrapper. |
| `block_source` | Data/design variant selected for a named block, including its identity and provenance. |
| `search` | Search objective, variables, and candidate ranges. |
| `algorithm_policy` | Choice of mathematical or numerical method. |
| `numerical_control` | Resolution, convergence, truncation, precision, and computational-cost controls. |
| `execution` | Scheduling and run-flow controls that do not change mathematical results. |

For 178A, these domain names have one canonical runtime-access mapping:

| Runtime label | Project/domain name | Approved runtime field |
|---|---|---|
| physical fields | workbook `intrinsic` | physical root fields; no `cfg.phy` or `cfg.intrinsic` wrapper |
| `SRC` | `block_source` | `cfg.src` |
| `ALG` | `algorithm_policy` | `cfg.alg` |
| `NUM` | `numerical_control` | `cfg.num` |
| `SRCH` | `search` | `cfg.srch` |
| `EXE` | `execution` | `cfg.exe` |

The label is a runtime access path, not a branch taxonomy. Public
dataclass names remain descriptive (`COMSourceConfig`,
`COMAlgorithmPolicyConfig`, `COMNumericalControlConfig`, `COMSearchConfig`, and
`COMExecutionConfig`). Project Config uses `intrinsic` for the user-facing
physical family accepted by the user. Physical fields and the five nonphysical
runtime domains form the configuration set; only a selectable behavior that
independently satisfies the
[Branch Behavior Contract](branch_behavior_contract.md) receives a branch ID.
In particular, `SRC` and `EXE` remain valid runtime domains without becoming
branch classes, and no `PHY` branch prefix is created for physical inputs.

`intrinsic`, `policy`, and `derived` in the workbook's `Parameter Class` column
describe schema/source treatment; they do not replace the domains above.
Intrinsic values map directly to their physical runtime objects.  Runtime
derived values stay in the dataclass that derives them, owner-local state, or
status.  Provenance stays in adapter/report metadata.  Do not create
`cfg.intrinsic`, `cfg.derived`, or `cfg.provenance` merely to mirror workbook
classification or reporting metadata.

Each field also has exposure `frequent`, `advanced`, or `internal_readonly`.
Exposure describes who normally edits or views the value; it does not change
the domain, ownership, or effect of that value. A field with multiple effects
still receives one primary domain, with secondary consequences recorded in its
`effect` metadata.

Before a new config field is added to a project schema or exposed through an
API/workbook, its version config inventory must record:

```text
domain:                 exactly one domain above
exposure:               frequent | advanced | internal_readonly
owner:                  config resolver, adapter, manifest, or production owner
effect:                 physical model | source | method | accuracy | cost | scheduling
scope:                  production consumers and explicit exclusions
raw value:              supplied workbook/API/user value, including source
effective value:        value after preset/profile resolution and overrides
profile membership:     presets/profiles that set, lock, or inherit the value
override semantics:     allowed override, validation, and resulting mode/provenance
reporting metadata:     raw/effective/source identity exposed in results/status
```

If a field is internal and read-only, record why it is not directly configurable
and how its effective value is reported. Do not add a field when owner, scope,
effect, or override behavior is unresolved; record the gap and resolve it before
implementation. Required metadata is documentation and review evidence; this
rule alone does not authorize adding runtime fields or workbook columns.

### Progressive config migration

Config architecture evolves in approved, reviewable steps:

1. **Inventory:** classify existing fields and fill known metadata; mark unknowns
   as unresolved. Do not change runtime behavior, Python API, or workbook schema.
2. **Presentation:** improve config trees and result/status presentation while
   preserving current dataclasses, workbook fields, and parser behavior.
3. **Preset resolution:** document a reviewed mode matrix and raw/effective
   provenance using current profile selectors and legacy values; do not add a
   new mode solely to complete the taxonomy.
4. **Family migration:** migrate one config family per approved contract. Name
   compatibility adapters and deprecation behavior, keep existing Python and
   workbook inputs working during the transition, and validate the established
   fixed baseline before removing a legacy path.

Do not batch-move dataclass fields, rename workbook columns, force direct paths
into manifest variants, or remove a legacy API/workbook entry as part of
classification or inventory work. Such changes require a separate approved
migration contract with compatibility behavior, affected consumers, and
baseline acceptance.

### Mode and preset contract

Use the existing versioned `execution_profile` as the compatibility-preserving
selector for named simulation modes/presets. This is a resolution and provenance
boundary, not a numerical algorithm method or execution scheduler. This rule
does not introduce any new mode or rename the existing selector.

- A mode/preset has a reviewed matrix listing each included `algorithm_policy`
  and `numerical_control`, its resolved value, and whether it is inherited,
  fixed, or overridable.
- A preset cannot silently change `physical_input`, `block_source`, search
  ranges, execution target, or orchestration controls. Any proposed exception
  needs an explicit contract describing the semantics and compatibility impact.
- `fast_exploration` cannot claim reference alignment. A `sicopr_reference`
  profile may claim alignment only for the named, validated scope and only when
  all applicable reference methods/settings are selected.
- An override of a guarantee made by the selected profile must resolve to
  `custom`, or be reported as an explicit deviation. A deviated result cannot
  claim reference alignment.
- Preserve legacy `execution_profile` values and Python/workbook interfaces
  during migration. Adapters resolve legacy inputs into the same raw/effective
  provenance model; do not change runtime algorithms merely to implement this
  classification contract.

### Block source contract

`block_source` identifies which data/design artifact a block consumes; it does
not choose the algorithm that processes it or the numerical precision used.
Record the selected variant, artifact identity/revision, format, units,
interface compatibility, and content hash in resolved provenance/results.
Existing direct-path fields remain supported during migration and are recorded
as legacy source bindings. Moving paths into a manifest or variant selector
requires a separate approved contract and compatibility plan.

### Case config

Case identity and provenance describe the case, not a runtime COM parameter. Keep `case_id`, source identity/note, and case warnings in the case-config domain. They must not be labeled `intrinsic` or passed into `COMConfig` unless an explicit runtime field is defined.

### Fixed config

Fixed config contains values used by the selected version's run. Its `Parameter Class` is one of:

- **`intrinsic`** — a model input supplied by the matching COM Ad Hoc source or required by the applicable COM specification. Map it from Ad Hoc when the source defines it.
- **`policy`** — a project-owned behavior or numerical control absent from COM Ad Hoc and the COM specification. Every policy field has an explicit project default and is managed separately from Ad Hoc mapping.
- **`derived`** — a version-contract field calculated from source/config inputs by an explicit conversion formula. Keep it in the project template when the approved version contract requires a visible value; document its formula and runtime destination.

`runtime` and `compatibility` are not fixed-config classes in the approved schema. Runtime-only values are created or resolved by code. Legacy compatibility parsing belongs in a source/versioned parser and must not become an undocumented project field.

### Execution and search config

For 178A, `RUN_MODE` selects `single_run` or `search_run`; `EXEC_POLICY` holds the
cross-layer `execution_profile` selector plus `single_run`, `search_sweep`, and
`search_final` execution settings; `SEARCH_CONFIG` holds candidate ranges and
search-run controls. A profile may override project policy and numerical run
settings, but never intrinsic case inputs, search ranges, execution target, or
orchestration quantities such as group size and top-K. These remain distinct
from fixed config. 93A contains only controls supported by its own runtime
contract; it does not receive 178A-only fields for visual symmetry.

## Required, empty, and missing values

An absent workbook row and a blank value cell are different:

- **Missing row/field:** the workbook does not implement a required schema field. Parsing or validation fails.
- **Blank required intrinsic:** the selected source is required to provide the field, but no value was mapped. Ad Hoc conversion fails and requires source resolution; it must not substitute a project template value.
- **Allowed-empty intrinsic:** the specification and version field contract permit omission. The cell remains blank and the runtime adapter maps it to `None`.
- **Policy:** has an explicit project-owned default. It is not an Ad Hoc mapping result.
- **Derived:** conversion computes it using the documented formula. An uncomputable required derived value fails conversion.

A blank cell is not implicitly a fallback. Only a specification-defined runtime rule may resolve it, and it must be applied at its owning runtime/config boundary.

The conversion view uses three mapping outcomes: `success`, `fail`, and `empty`. `empty` is valid only for documented optional fields; `fail` blocks export. Project policy values are edited in their own section, outside Ad Hoc mapping.

## Mapping records

Each version tree lists, per field: project domain/group, class, source key or policy/default/derivation, requiredness, blank behavior, workbook location, runtime owner, and runtime field. Record unit conversions where applicable. Keep these audits separate:

- **Ad Hoc → project:** source key, source unit, conversion, target field, requiredness, and mapping outcome.
- **Project → runtime:** workbook field, target dataclass field/type, validation, and `None` behavior.

### Project/runtime coverage invariant

Every project-config parameter must have a runtime destination or an explicit case/provenance purpose. Do not retain an orphan row because an older workbook had it. Conversely, all user/project-supplied inputs required to construct a supported runtime configuration must exist in that version's project schema. Runtime dataclass attributes that are internal, derived in code, transient, or not consumed by the model are not automatically project-config fields. Workbook schema metadata such as `Parameter Class` is not itself a runtime parameter.

A source-format parser identifies workbook layout; its format ID is separate from source provenance. Preserve original source files under `reference_data/COM_adhoc_config/<source_id>/`. The GUI selects `cases/_templates/<version>/config.xlsx` and exports under `cases/<case_id>/<version>/config.xlsx`.

## MLSD and runtime-owned fallback example

For 178A, keep `mlsd_trunc_len`, `delta_com_an`, and `minimum_com_limit` independent. If MLSD is enabled and the source lacks required `N_tc` or supported truncation input, conversion fails; do not insert `128`. `delta_com_an` may remain blank when optional. If the specification defines how to resolve that blank using `minimum_com_limit`, the runtime implementation applies that rule without copying the minimum into `delta_com_an`. 93A has no MLSD fields unless its own runtime/spec contract defines them.

## Cross-version workbook presentation and scope

93A and 178A use the same presentation conventions and columns, including `Parameter Class` in fixed config. Each template contains all project inputs required by its version, including approved derived rows, and only that version's supported parameters. Shared visual format does not authorize adding 178A-only fields such as `N_qb`, `P_qc`, or MLSD to 93A.

The 178A templates and tracked cases implement this presentation. 93A remains
outside CFG-178A-E and retains its existing version-specific workbook contract.

## Related documents

- [93A config tree](../models/93A/config_tree.md)
- [178A config tree](../models/178A/config_tree.md)
- [Project structure](project_structure.md)
- [Documentation contract](documentation_contract.md)
