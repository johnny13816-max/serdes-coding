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

Project-level presets are resolved at boundary 2. For 178A, the workbook-only
`align_to_ref` switch is expanded by `com_excel_io_178A` into named runtime
methods and effective execution profiles before `COMConfig` is constructed.
The model and utilities receive those named values and never branch on the
workbook switch. The config snapshot records the applied profile and each
raw/effective override.

The project workbook format is stable within each COM version. Similar presentation across versions does not make their parameter sets interchangeable. Channel files are selected in the workbook's `channels` sheet and stored under `reference_data/COM_channel_data/`.

## Configuration domains and classes

### Case config

Case identity and provenance describe the case, not a runtime COM parameter. Keep `case_id`, source identity/note, and case warnings in the case-config domain. They must not be labeled `intrinsic` or passed into `COMConfig` unless an explicit runtime field is defined.

### Fixed config

Fixed config contains values used by the selected version's run. Its `Parameter Class` is one of:

- **`intrinsic`** — a model input supplied by the matching COM Ad Hoc source or required by the applicable COM specification. Map it from Ad Hoc when the source defines it.
- **`policy`** — a project-owned behavior or numerical control absent from COM Ad Hoc and the COM specification. Every policy field has an explicit project default and is managed separately from Ad Hoc mapping.
- **`derived`** — a version-contract field calculated from source/config inputs by an explicit conversion formula. Keep it in the project template when the approved version contract requires a visible value; document its formula and runtime destination.

`runtime` and `compatibility` are not fixed-config classes in the approved schema. Runtime-only values are created or resolved by code. Legacy compatibility parsing belongs in a source/versioned parser and must not become an undocumented project field.

### Execution and search config

For 178A, `RUN_MODE` selects `single_run` or `search_run`; `EXEC_POLICY` holds `single_run`, `search_sweep`, and `search_final` execution settings; `SEARCH_CONFIG` holds candidate ranges and search-run controls. These are distinct from fixed config. 93A contains only controls supported by its own runtime contract; it does not receive 178A-only fields for visual symmetry.

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

The current templates/adapters are not fully aligned with this contract. Version trees identify observed gaps, including the missing 93A class column, class labels needing correction, and the 93A legacy Ad Hoc path. These are implementation discrepancies; this documentation update does not change code or workbook files.

## Related documents

- [93A config tree](../models/93A/config_tree.md)
- [178A config tree](../models/178A/config_tree.md)
- [Project structure](project_structure.md)
- [Documentation contract](documentation_contract.md)
