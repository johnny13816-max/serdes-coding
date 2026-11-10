# 178A COMConfig domain migration

> Status: **Closed 2026-11-10; CFG-178A A--F implemented, validated, and integrated locally.**
>
> Active priority: repair the 178A configuration boundary before resuming
> NUM-006. This contract does not decide NUM-006 scope, value, name, or owner.

## Objective

Project Config, the branch registry, runtime dataclasses, adapters, search
orchestration, and the Project Config GUI must use one classification. Project
Config and review documents use the full class name; grouped runtime fields use
the registered lower-case prefix.

| Prefix | Canonical class | Runtime field | Boundary |
|---|---|---|---|
| `PHY` | `physical_input` | direct physical fields | System, specification, topology, physical conditions, and case data bounds. |
| `SRC` | `block_source` | `cfg.src` | Data/design artifacts and the metadata required to interpret them. |
| `ALG` | `algorithm_policy` | `cfg.alg` | Named mathematical or numerical realizations. |
| `NUM` | `numerical_control` | `cfg.num` | Resolution, convergence, truncation, precision, and cost. |
| `SRCH` | `search` | `cfg.srch` | Variables, candidate coverage, search strategy, and retention. |
| `EXE` | `execution` | `cfg.exe` | Run extent, scheduling, and stage gates that do not change executed formulas. |

The abbreviations are runtime paths, not a parallel taxonomy. Public dataclass
names remain descriptive.

## Current validated boundary after CFG-178A-D

The working tree already contains the validated foundation slices:

1. Outer-search orchestration owns `group_size` and `final_top_k` through the
   existing `COMSearchConfig`.
2. `excel_to_config_178A(..., run_mode=...)` selects one of `single_run`,
   `search_sweep`, or `search_final` before constructing `COMConfig`.
3. `COMConfig.src`、`COMConfig.alg`、`COMConfig.num`、`COMConfig.srch`、
   `COMConfig.exe` store one resolved runtime setting set. Channel artifacts and
   their interpretation metadata live only in `cfg.src.channel`; physical
   termination and measured-boundary values live only in `cfg.channel`.
4. `alg.missing_dc_policy` is the sole runtime ALG-001 source. Source bindings
   load and validate each S2P/S4P artifact; Stage 1 keeps the existing
   representation dispatch and no-fallback behavior.
5. `COMRunConfig` and grouped profiles exist only inside the workbook adapter
   compatibility boundary.
6. `COM.run()` executes one resolved configuration; the outer search runner
   creates separate scalar-candidate `COM` instances.
7. Stage 1--7 production owners read canonical domain fields directly; Stage
   APIs do not accept or forward `run_cfg`.

The runtime domain tree is in place. Workbook/GUI presentation, profile
metadata, and legacy public aliases remain for E/F. `cfg.srch` owns both outer
candidate coverage and Stage 3 phase-search controls; `cfg.exe` contains only
`target`.

## Approved runtime target

```text
COMConfig
├─ L
├─ DER_0
├─ link: LinkConfig
├─ filter: COMFilterConfig
├─ channel: COMChannelConfig             physical conditions / input boundary
├─ txpkg_victim: COMPkgConfig
├─ txpkg_fext: COMPkgConfig
├─ txpkg_next: COMPkgConfig
├─ rxpkg: COMPkgConfig
├─ dte: COMDTEConfig
├─ imp: COMImpairmentConfig
├─ mlsd: COMMLSDConfig
├─ src: COMSourceConfig                  SRC / block_source
│  ├─ channel.victim
│  ├─ channel.next
│  └─ channel.fext
├─ alg: COMAlgorithmPolicyConfig         ALG / algorithm_policy
├─ num: COMNumericalControlConfig        NUM / numerical_control
├─ srch: COMSearchConfig                 SRCH / search
└─ exe: COMExecutionConfig               EXE / execution
   └─ target
```

`PHY` does not add `cfg.phy`: physical objects retain direct paths such as
`cfg.link` and `cfg.channel`. `intrinsic` remains a Project Config parameter
class and does not add `cfg.intrinsic`.

There is no top-level `cfg.provenance` or `cfg.derived`:

- construction-derived values use `init=False`/`__post_init__` in the owning
  physical dataclass;
- runtime-context resolution stays owner-local or in a private cache;
- stage outputs stay in `COMStatus`;
- applied profile, raw/effective override, and source history stay in adapter
  resolution records and reports and never control model flow.

## Project Config mapping

Project Config presents the full canonical names while preserving the existing
workbook sheet layout during this migration:

```text
Project Config presentation
├─ intrinsic                         maps to physical root fields
├─ block_source                      maps to cfg.src
├─ algorithm_policy                  maps to cfg.alg
├─ numerical_control                 maps to cfg.num
├─ search                            maps to cfg.srch
└─ execution                         maps to cfg.exe
```

The workbook's `Parameter Class` (`intrinsic`, `policy`, or approved visible
`derived`) remains a separate source/schema-treatment axis. It must not replace
the canonical domain. `execution_profile` is an adapter-boundary preset
selector; it is expanded before `COMConfig` construction and is not a runtime
branch or scheduler.

## Source contract

`COMSourceConfig` is the only approved public top-level source dataclass. The
public access contract is:

```text
cfg.src.channel.victim
cfg.src.channel.next
cfg.src.channel.fext
```

No public `COMChannelSource` class is introduced. A channel source binding owns
artifact identity/path, representation or format, port order, and the
information required to load and validate that artifact. A future block source
may extend the same container, for example `cfg.src.afe`, without changing the
canonical `SRC` class.

`cfg.channel` retains electrical conditions and the measured-data boundary.
`missing_dc_policy` is an algorithm policy. Reflection coefficients derived
from resistance inputs remain construction-derived fields in the physical
channel dataclass.

## Search contract

There is one `COMSearchConfig`; no `COMSearchRuntimeConfig` is added. It groups
the SRCH category even though individual fields have different coding owners:

- the outer runner owns TX FFE/CTLE candidate axes, Cartesian expansion,
  grouping, ranking, and result retention;
- the Stage 3 phase-search owner reads only sampling-phase method and stride;
- neither owner interprets the other owner's fields.

Candidate axes accept a scalar or a non-empty finite one-dimensional vector.
A scalar and a length-one vector are equivalent. The outer runner normalizes
all axes and forms their Cartesian product:

```text
product size == 1
└─ resolve one scalar candidate and execute the single-run configuration

product size > 1
└─ sweep scalar candidates → rank → final top-K scalar reruns
```

Vectors never reach `COM.run()` or Stage 1--7. Candidate resolution writes the
selected scalar TX FFE/CTLE values into the effective physical filter config.
Each `COM` remains one simulator instance with one resolved scalar candidate.

## Field migration inventory

| Current field or family | Canonical class | Approved target | Slice | Notes |
|---|---|---|---|---|
| `COMConfig.L`, `DER_0` | `physical_input` | unchanged root fields | B | No wrapper. |
| `link.*`, filter physical inputs, packages, DTE inputs, impairments, MLSD specification inputs | `physical_input` | existing physical leaf objects | B | Preserve formulas and values. |
| `filter.c_0`, `filter.txfir` | construction-derived | `COMFilterConfig` `init=False` fields | B | No `derived` group. |
| channel `R0`, `R_d_tx`, `R_d_rx`, frequency limit | `physical_input` / input boundary | `cfg.channel` | D | Frequency limit is not an algorithm selector. |
| channel paths, artifact representation, and port order | `block_source` | `cfg.src.channel` | D | Source binding loads and validates itself. |
| channel `gamma_src`, `gamma_load` | construction-derived | `COMChannelConfig` `init=False` fields | D | No `derived` group. |
| channel `missing_dc_policy` | `algorithm_policy` | `cfg.alg.missing_dc_policy` | D | ALG-001 values and owner unchanged. |
| existing algorithm selectors in `COMAlgorithmPolicyConfig` | `algorithm_policy` | `cfg.alg` | B | One effective selector per approved ALG branch. |
| `floating_mode` in `COMRunConfig` | `algorithm_policy` | `cfg.alg.floating_mode` | B | ALG-010, not scheduling. |
| `eq_ch_imp_len`, `num_trunc_ui` | `numerical_control` | `cfg.num` | B | NUM-003 values and owner unchanged. |
| ADC-input and final PMF grids | `numerical_control` | `cfg.num` | B | Preserve independent NUM-004/005 domains. |
| PMF grid/tap compatibility fields | `numerical_control` | canonical `cfg.num` field or adapter-only compatibility input | B/F | No duplicate runtime source. |
| `COMPMFConfig.keep_mass`, run-profile `pmf_keep_mass` | unresolved NUM-006 | unresolved under `cfg.num` | after F | Duplicate source is removed only after NUM-006 review; this migration does not choose semantics. |
| `pos_sweep_method`, `pos_coarse_stride` | `search` | `cfg.srch` | C | SRCH-001 Stage 3 owner unchanged. |
| TX FFE/CTLE candidate axes | `search` | `cfg.srch` at Project Config/job boundary | C | Scalar/vector normalization and Cartesian expansion are outer-runner work. |
| `group_size`, `keep_top_n`, `final_top_k`, error/retention controls | `search` | `cfg.srch` | C | Not execution fields. |
| `target` | `execution` | `cfg.exe.target` | B | Sole current EXE field. |
| grouped `single_run/search_sweep/search_final` config | adapter input | resolved before `COMConfig` | B/F | Not stored simultaneously in a simulator instance. |
| applied profile and raw/effective override records | metadata | adapter/report record | B/E/F | Never control runtime flow. |
| resolved runtime grids and stage products | owner-local/status | owning object or `COMStatus` | B/F | No top-level runtime group. |

## Owner contract

```text
Project Config / Python input
└─ adapter resolves preset, run mode, compatibility values, and candidate
   └─ COMConfig stores one effective value in its canonical runtime field
      └─ L3 owner reads self.cfg.src / alg / num / srch / exe directly
         └─ L4 kernel receives concrete operation arguments
            └─ status records effective behavior and outputs
```

- Stage APIs do not receive a composite run config or selectors merely to
  forward them.
- L4 utilities do not read `COMConfig`.
- A shared selector has one Shared-L3 owner and one resolved state.
- Config grouping does not define coding ownership: fields may share one domain
  dataclass while different L3 owners read disjoint fields.
- Adapter/report metadata and status never control runtime flow.

## Approved child contracts

| Slice | Boundary | Stop gate |
|---|---|---|
| `CFG-178A-A` | Taxonomy, target tree, field inventory, and documentation consistency only. | Documents agree; no code or workbook change. |
| `CFG-178A-B` | Split ALG/NUM/EXE runtime fields and owner access. | Focused tests and fixed golden pass; source/search redesign untouched. |
| `CFG-178A-C` | One SRCH config, scalar/vector normalization, outer Cartesian orchestration. | Search tests and single-run/search validation pass. |
| `CFG-178A-D` | `COMSourceConfig` and channel source/physical separation. | Source, S-parameter, Stage 1, and fixed golden tests pass. |
| `CFG-178A-E` | 178A Project Config templates/cases, converter, GUI generator, and workbook validation. | All tracked 178A workbooks load; formula and visual checks pass. |
| `CFG-178A-F` | Compatibility cleanup, exports/scripts, final docs, and integration validation. | No duplicate runtime source; full agreed validation passes. |

Each slice requires separate approval. Completion of one slice does not
authorize the next.

## Compatibility and protected invariants

- Preserve current workbook sheet names and profile names during B--D.
- Preserve `excel_to_config_178A(path)` as the single-run default.
- Temporary compatibility access may exist only at the adapter/public API
  boundary and may not become a second production source of truth.
- Do not change algorithm formulas, numerical defaults/effective values,
  candidate ranking, or fixed-case outputs.
- Do not restore retired branches or add selectors.
- Do not move outer search into `COM.run()`.
- Do not modify 93A as part of this contract.
- Do not resume NUM-006 before CFG-178A-F closes.

## Validation gates

1. Every implementation slice verifies the project-managed `.venv` interpreter
   and dependency versions before Python execution.
2. B verifies dataclass paths, adapter resolution, direct owner access, invalid
   values, and the fixed SiCoPR golden.
3. C verifies scalar/length-one equivalence, mixed Cartesian products, one-run
   dispatch, split search, and scalar-only `COM` inputs.
4. D verifies victim/NEXT/FEXT bindings, S2P/S4P dispatch, port order, measured
   boundary, ALG-005 no-fallback behavior, and the fixed golden.
5. E verifies templates, mapping, existing-project open/save, conversion, GUI
   grouping/parsing, workbook recalculation, formula-error scans, and changed
   sheet rendering.
6. F verifies exports, scripts, stale access paths, Python 3.7 compatibility,
   focused integration tests, and the fixed SiCoPR values/digests.

The established fixed baseline remains:

```text
MSE:       0.0061912610245255335
COM_DFE:   1.5247607834259893 dB
final COM: 2.895898684873246 dB
digests:   unchanged frozen Stage 3/5/6 digests
```

### CFG-178A-B evidence

- canonical runtime dataclasses: `COMAlgorithmPolicyConfig`、
  `COMNumericalControlConfig`、`COMExecutionConfig`;
- adapter selects one profile/run mode and flattens it before `COMConfig`
  construction;
- production owner scan has no `self.cfg.policy`、`self.cfg.numerical_control`、
  `self.cfg.execution` or `_effective_run_cfg()` access;
- domain/adapter/owner focused suite: `52 passed` plus `2 subtests passed`;
- related architecture/CTLE/post-FFE/fixed-grid/search suite: `34 passed` with
  two previously recorded non-gate failures; provenance rerun outside the repo:
  `2 passed`;
- fixed SiCoPR production golden: `1 passed`; MSE、COM_DFE、final COM and all
  three frozen digests unchanged.

### CFG-178A-C evidence

- `COMConfig.srch: COMSearchConfig` is the sole runtime SRCH group;
- scalar and length-one axes are equivalent; mixed axes expand as one Cartesian
  product; invalid empty/non-1D/non-finite axes fail explicitly;
- candidate resolution writes the same scalar values to the physical filter and
  scalar-only `cfg.srch`; unresolved vectors are rejected by `COM.run()`;
- `run_configured()` dispatches one point directly and multiple points through
  the unchanged split-search ranking/finalization flow;
- focused SRCH/adapter/finalization/provenance suite: `63 passed`;
- related owner/MLSD/fixed-grid suite: `29 passed` plus `2 subtests passed`;
- two-candidate file-backed partial-search smoke matched two direct COM runs:
  MSE `0.007518054868740354` and `0.008012572876666063`.
- fixed SiCoPR production golden: `1 passed`; MSE
  `0.0061912610245255335`、COM_DFE `1.5247607834259893 dB`、final COM
  `2.895898684873246 dB` and all three frozen digests unchanged.

### CFG-178A-D evidence

- `COMSourceConfig` is the only public top-level source dataclass; its nested
  channel binding owns path, representation, and port order without introducing
  a public `COMChannelSource` class;
- `COMChannelConfig` now contains only physical termination values, derived
  reflection coefficients, and the measured-frequency limit;
- ALG-001 moved to `cfg.alg.missing_dc_policy`; `_build_paths()` resolves it and
  passes one concrete method to `_build_path()`;
- source/config/adapter/S2P-S4P/no-fallback/Stage-1/path/profile/export focused
  suite: `93 passed`;
- supplemental S-parameter and search integration suite: `23 passed`;
- fixed SiCoPR production golden: `1 passed`; MSE
  `0.0061912610245255335`、COM_DFE `1.5247607834259893 dB`、final COM
  `2.895898684873246 dB` and all frozen path/stage digests unchanged.

### CFG-178A-E evidence

- all nine tracked 178A workbooks now use one four-sheet schema and canonical
  `Domain` metadata; the template remains intentionally non-runnable until its
  blank channel paths and intrinsic values are populated;
- legacy 150 mm and corrupted 250 mm C2M workbooks were rebuilt on the reviewed
  template schema, preserving case/channel/search data and using tracked C2M
  family values only for missing common physical/package/DTE rows;
- converter and existing-project save preserve `block_source` on rebuilt
  channel rows; GUI rows display and sort by canonical domain without replacing
  mapping/policy/baseline source-treatment tabs;
- workbook recalculation, formula-error scan, and four-sheet rendering passed
  for every workbook; all eight populated cases construct `COMConfig` and
  `COMSearchConfig`;
- focused converter/GUI/search/policy suite: `51 passed`;
- fixed SiCoPR production golden: `1 passed`; MSE
  `0.0061912610245255335`、COM_DFE `1.5247607834259893 dB`、final COM
  `2.895898684873246 dB` and all frozen path/stage digests unchanged.

### CFG-178A-F evidence

- removed the temporary `COMPolicyConfig` export and the read-only
  `cfg.policy`／`cfg.numerical_control`／`cfg.execution` aliases; production and
  public 178A exports now use only `cfg.alg/num/exe` and the descriptive
  dataclass names;
- `ProjectFieldDraft` stores `domain` directly; the temporary `group` storage
  vocabulary is removed from converter and GUI code;
- applied profile and raw/effective overrides were removed from
  `COMAlgorithmPolicyConfig`; the workbook adapter attaches a private,
  export-only `adapter_resolution` record that is preserved by production
  candidate/config copies and is never read by Stage 1--7;
- split-search CLI, workflow, and GUI resolve the canonical
  `cases/<case_id>/178A/config.xlsx` layout; a two-candidate partial-search
  smoke matched direct runs;
- all eight populated cases load in all three run modes; canonical export and
  stale-name scans pass; Python 3.7 utility validation and module compilation
  pass;
- focused integration: `136 passed`, `3 deselected`, `2 subtests passed`; the
  provenance test requiring an external temp root separately passes `2/2`.
  The three deselected converter tests require absent local-only Ad Hoc source
  workbooks and remain an environment deviation;
- fixed SiCoPR production golden: `1 passed`; MSE
  `0.0061912610245255335`、COM_DFE `1.5247607834259893 dB`、final COM
  `2.895898684873246 dB` and frozen digests unchanged.

## Foundation evidence retained

The already implemented foundation slices remain in the working tree:

- outer search owns `group_size` and `final_top_k`;
- adapter-only `COMRunConfig` profiles resolve into `cfg.alg/num/srch/exe`;
- `COM.run()` no longer accepts search/report arguments;
- Stage 3--7 no longer forward `run_cfg`;
- GUI, scripts, and search runner construct separate sweep/final configs;
- focused adapter/API/search validation previously passed `52` tests;
- the fixed SiCoPR golden previously passed with the values above and unchanged
  digests.

Known non-gate observations remain separate: the architecture suite has the
pre-existing 178A/93A retired Gaussian-support parity mismatch, and the generic
post-FFE fixture has a historical profile/MSE expectation mismatch. Neither is
part of the CFG migration gates.

## Paused review

NUM-006 remains paused. Prior ADC-only and global-PMF owner proposals are not
accepted decisions. Resume only after CFG-178A-F closes and the production
consumer mapping is reviewed again.
