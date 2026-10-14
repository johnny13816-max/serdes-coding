# 93A configuration tree

> This is the 93A-specific inventory of project fields and typed runtime ownership. It does not define model equations. Project-wide rules are in [configuration architecture](../../architecture/configuration_architecture.md).

## Configuration layers

```text
RUN_MODE
├── single_run
└── search_run
FIXED_CONFIG
├── intrinsic
├── derived
└── policy
SEARCH_CONFIG
└── candidate values and search controls
CASE_CONFIG
└── case identity and provenance
```

93A has no 178A `run_config` profiles and no MLSD/ADC quantization fields. Matching workbook presentation does not imply matching parameter inventories.

## Project workbook fields

`config.xlsx` uses `fixed_config`, `search_config`, and `channels`. The fixed sheet uses Domain, Parameter, Parameter Class, Value, Unit, and Description, matching the 178A presentation with a version-specific field inventory.

### Case config (not runtime config)

| Workbook field | Meaning | Runtime mapping |
|---|---|---|
| `case_id` | Case folder identity | None |
| `case_source` | Source provenance | None |
| `source_note` | User source note | None |

### Intrinsic and derived fixed config

Blank means conversion failure for required Ad Hoc inputs. `num_pre` and package segment-2 fields are exceptions only where specifically noted.

| Class | Domain / runtime owner | Workbook parameters | Source / derivation | Blank behavior |
|---|---|---|---|---|
| intrinsic | Link / `LinkConfig` | `fb`, `per_ui`, `target_df` | Ad Hoc: `f_b`, `M`, `Delta_f`; units converted to Hz/samples per UI | Required |
| intrinsic | Filter / `COMFilterConfig` | `c_m3`, `c_m2`, `c_m1`, `c_1`, `Tr`, `fr`, `g_DC`, `g_DC2`, `f_z`, `f_LF`, `f_p1`, `f_p2`, `A_v`, `A_fe`, `A_ne` | Source values plus unit mapping | Required; `c_m2`, `c_m1`, `c_1`, `g_DC`, `g_DC2` have zero fixed baselines while search ranges live in `search_config` |
| derived | Filter / `COMFilterConfig` | `num_pre` | Current TX FFE main cursor index, derived during conversion | Conversion must produce a value; no silent fallback |
| intrinsic | Package / four `COMPkgConfig` instances | For each of `txpkg_victim`, `txpkg_fext`, `txpkg_next`, `rxpkg`: `enable`, `C_d`, `L_s`, `C_b`, `z_p`, `C_p`, `R0`, `Z_c`, optional `z_p2`, `Z_c2`, `gamma_0`, `a1`, `a2`, `tau` | Ad Hoc package/device inputs, converted to SI/project units | Required except optional `z_p2`; blank `z_p2` maps to `None`. `Z_c2` is currently required by the adapter |
| intrinsic | Channel termination / `COMChannelConfig` | `R_0`, `R_d_tx`, `R_d_rx` | Ad Hoc `R_0`; TX-side `R_d` from selected TX package profile; RX-side `R_d` from selected RX package profile | Required. Runtime derives `gamma_src` and `gamma_load`; Gamma is not a project input |
| intrinsic | DFE / `COMDFEConfig` | `N_b`, `b_max`, `b_min` | N_b and first/rest tap limits. `b_max` → `b_max`; `b_min` → existing `bb_min`. Scalars or N_b vectors. | Required; finite bounds, lower must not exceed upper |
| intrinsic | Impairment / `COMImpairmentConfig` | `R_LM`, `SNR_TX`, `sigma_RJ`, `A_DD`, `eta_0` | Ad Hoc values; `eta_0` is converted from V²/GHz to V²/Hz per source keyword | Required |
| intrinsic | COM / `COMConfig` | `L`, `DER_0` | Ad Hoc direct mapping | Required |

No 93A project fields are defined for `N_qb`, `P_qc`, `quantization_vqc_method`, or MLSD. Do not add them to the 93A template or converter.

### Policy fixed config

Policy values are project-owned defaults, not Ad Hoc mapping targets.

| Workbook parameter | Runtime owner | Default in current template | Blank behavior |
|---|---|---:|---|
| `dy_rel_As` | `COMPMFConfig` | 0.001 | Should be populated by the policy default |
| `dy_abs_max` | `COMPMFConfig` | 1e-5 V | Should be populated by the policy default |
| `tap_rel_As` | `COMPMFConfig` | 0.001 | Should be populated by the policy default |
| `keep_mass` | `COMPMFConfig` | 0.99999 | Should be populated by the policy default |
| `gaussian_n_sigma` | `COMPMFConfig` | 8 | Should be populated by the policy default |
| `missing_dc_policy` | `COMChannelConfig` | `skrf` | Should be populated by the policy default |

The template labels these project-owned controls as policy.

### Channels

The `channels` sheet holds channel selection and interpretation, not copied S4P data:

- one victim row and zero or more NEXT/FEXT rows;
- S4P path, port order, and enable/use state;
- channel files remain in `reference_data/COM_channel_data/`.

`R_0`, `R_d_tx`, and `R_d_rx` live in fixed config. `COMChannelConfig.__post_init__()` derives source/load reflection coefficients. Every package `R0` remains a required package-model field and must equal channel `R_0` when the project adapter constructs the runtime config.

### Search config

| Workbook parameter | Runtime field | Meaning |
|---|---|---|
| `c_m2`, `c_m1`, `c_1` | `COMSearchConfig.c_m2_values`, `c_m1_values`, `c_1_values` | TX FFE candidate values |
| `g_DC`, `g_DC2` | `g_DC_values`, `g_DC2_values` | CTLE candidate values |
| `keep_top_n` | `keep_top_n` | Retained successful summary count |
| `keep_all_rows` | `keep_all_rows` | Search-result retention |
| `continue_on_error` | `continue_on_error` | Candidate error handling |

Fixed baseline and candidate sequence are separate: search values do not replace single-run fixed values.

## Runtime dataclass tree

```text
COMConfig
├── link: LinkConfig
├── filter: COMFilterConfig
├── channel: COMChannelConfig
├── txpkg_victim: COMPkgConfig
├── txpkg_fext: COMPkgConfig
├── txpkg_next: COMPkgConfig
├── rxpkg: COMPkgConfig
├── dfe: COMDFEConfig
├── imp: COMImpairmentConfig
├── L
├── DER_0
└── pmf: COMPMFConfig

COMSearchConfig                 separate search input
```

`COMChannelConfig` stores required `R0`, `R_d_tx`, and `R_d_rx`; its
`gamma_src` and `gamma_load` fields are derived during construction.

Each package config contains `C_d`, `L_s`, `C_b`, `z_p`, `C_p`, `enable`, `R0`, `Z_c`, optional `z_p2`, `Z_c2`, `gamma_0`, `a1`, `a2`, and `tau`. `LinkConfig` creates its sampling/time/frequency axes internally.

### Package TL coefficient mapping

For each package path, the selected package profile provides:

| Ad Hoc field | Project and runtime field | Unit |
|---|---|---|
| `package_tl_gamma0_a1_a2[0]` | `<path>.gamma_0` | 1/mm |
| `package_tl_gamma0_a1_a2[1]` | `<path>.a1` | 1/(mm sqrt(GHz)) |
| `package_tl_gamma0_a1_a2[2]` | `<path>.a2` | 1/(mm GHz) |
| `package_tl_tau` | `<path>.tau` | ns/mm |

Indices above are zero-based. The three coefficient entries have distinct
meanings and are not reduced by a maximum operation. TX paths use the selected
TX coefficient profile; RX uses the selected RX coefficient profile. Both TL
segments of a path use that profile's coefficients, with their own lengths and
impedances. The builder passes `gamma_0` as the existing primitive's `gamma0`.
The TL equations and cascade order are unchanged.

These four intrinsic inputs are blank in the template and required during
mapping and project parsing. Existing case workbooks must add them from their
source profile; the adapter does not silently substitute historical constants.
Direct Python `COMPkgConfig()` construction retains the former coefficients
`(0, 1.734e-3, 1.455e-4, 6.141e-3)` for API compatibility, not as a workbook
missing-value fallback.

## Mapping responsibilities and current gaps

- Intended conversion path: source-specific Ad Hoc parser/converter → fixed 93A project workbook → `excel_to_config_93A()` / `excel_to_search_config_93A()` → typed config.
- The current 93A adapter still accepts a legacy PyChOpMarg workbook directly. That is a boundary gap; this rules update does not remove it.
- The 93A fixed sheet includes `Parameter Class`, with version-specific fields.
- Current workbook baseline defaults for five filter search dimensions are zero; actual Ad Hoc search ranges belong in `search_config`.
- A blank required source intrinsic must fail conversion. An allowed optional blank (currently package `z_p2`/`Z_c2`) must map to `None`. Missing required project rows fail parsing.
- Ad Hoc mappings and provisional maximum-value package reduction follow [the mapping contract](../../architecture/adhoc_mapping_contract.md). `Z_c2` remains required by the adapter even when `z_p2` is empty.
