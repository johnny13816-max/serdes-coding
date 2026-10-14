# 178A sampling-phase and MMSE-DTE stage

> **Review state:** phase-sweep ownership, solver call boundaries, floating-tap variants, limiter flow, status output, and current selection behavior are confirmed from source. The MMSE equations and numerical results have not been independently revalidated by this documentation change.

## Purpose and ownership

This stage evaluates receiver sampling phases and selects one limited discrete-time equalizer result.

Responsibility is deliberately split:

- `COM._run_once()` owns phase scheduling, per-phase orchestration, rejection recording, and minimum-MSE phase selection;
- `COM_MMSE_DTE` owns the MMSE problem for one phase, including floating FFE placement, coefficient solving, limiting/refinement, MSE calculation, and `COMDTEStatus` construction.

The stage does not build pre-DTE PSDs, construct residual post-FFE responses, build final PMFs, or calculate COM.

## Governing references

Current solver docstrings identify Annex 178A Eq. 178A-31 through Eq. 178A-35 for the KKT solve, coefficient-limiter/refinement flow, and final MSE. This stage document records the implemented software flow and status ownership. It does not independently certify those equations or their numerical tolerance.

## Entries and outputs

```text
calculate_pos_candidate(...)
    -> (candidate_impairment, candidate_dte)

calculate_MMSE_DTE(victim, imp_pre, pos, run_cfg)
    -> COMDTEStatus

COM_MMSE_DTE.run(h_dsamp, R_n, sigma_x, pos, per_ui)
    -> COMDTEStatus
```

`calculate_MMSE_DTE()` currently receives `victim` for the stage-level API but reads the sampled response and noise data from `imp_pre`.

## Phase-sweep orchestration

```text
initialize COMRunStatus
├── mse_by_pos = [None] * per_ui
├── main_cursor_error_by_pos = [None] * per_ui
├── coarse_pos = []
└── fine_pos = []

choose initial phases
├── each_phase -> every integer phase
└── coarse_fine -> every pos_coarse_stride phase

for each initial phase
└── calculate_pos_candidate(...)
    ├── calculate_pre_dte_imp_at_pos(...)
    └── calculate_MMSE_DTE(...)

if coarse_fine
├── identify current best valid coarse phase
├── build circular fine window around it
├── exclude phases already evaluated
└── evaluate remaining fine phases

select minimum-MSE valid candidate
├── status.dte = selected COMDTEStatus
└── status.imp = matching selected pre-DTE impairment
```

The pre-DTE impairment and DTE result remain paired throughout selection. The model never selects a DTE result while retaining impairment data from a different phase.

### Phase-policy behavior

| Policy | Implemented phase set |
|---|---|
| `each_phase` | every integer phase from `0` through `per_ui - 1` |
| `coarse_fine` | initial `range(0, per_ui, pos_coarse_stride)`, followed by unvisited phases in a circular window around the best coarse result |

The fine-window radius is currently derived from `pos_coarse_stride`. `COMRunStatus.coarse_pos` contains the initial phase set for either policy; `fine_pos` is populated only for the second pass.

A phase with `COMMainCursorError` keeps `mse_by_pos[pos]` as `None` and stores the message in `main_cursor_error_by_pos[pos]`. Other exceptions propagate. If MSE values tie exactly, the earlier evaluated candidate remains selected because replacement uses a strict lower-than comparison.

## Required inputs

### Phase orchestration

| Input | Role |
|---|---|
| `LinkConfig.per_ui` | complete phase domain |
| `COMRunConfig.pos_sweep_method` | exhaustive or coarse/fine scheduling |
| `COMRunConfig.pos_coarse_stride` | initial stride and fine-window construction |
| pre-DTE common cache and aggressor responses | input to the preceding per-phase impairment calculation |

### One-phase DTE solve

| Input | Source | Requirement |
|---|---|---|
| `h_dsamp` | `imp_pre.eq_ch.h_dsamp.ir` compatibility proxy | one-dimensional and at least `N_max` samples |
| `R_n` | `imp_pre.pre_dte.psd.R_n` compatibility proxy | at least `N_max` lags; solver retains the first `N_max` |
| `sigma_x` | `imp_pre.pre_dte.psd.sigma_X` | finite and positive |
| `pos` | phase orchestrator | integer in `[0, per_ui)` |
| `per_ui` | `LinkConfig` | positive |
| `COMDTEConfig` | fixed config | tap counts, placement domain, and coefficient limits |
| `COMRunConfig.floating_mode` | execution policy | floating-group algorithm |

The workbook mapping and intrinsic/policy classification are defined in [Configuration tree](../config_tree.md).

## DTE configuration ownership

`COMDTEConfig` owns:

- fixed FFE cursor position `d_w` and fixed-tap count `N_fix`;
- total FFE index domain `N_max`;
- floating group count `N_wg` and taps per group `N_wf`;
- DFE feedback count `N_b`;
- scalar fixed, floating, first-feedback, and remaining-feedback limits;
- derived full-index `w_lower`/`w_upper` arrays and `b_lower`/`b_upper` arrays.

The configured FFE main tap at index `d_w` is fixed to unity in the derived limit arrays. Fixed-tap limits are symmetric in the current project config; floating and DFE lower/upper limits are explicit.

## One-phase solver flow

```text
COM_MMSE_DTE.run(...)
├── _validate_input(...)
│   ├── validate shapes, lengths, phase, and variance
│   ├── require positive dominant sampled cursor
│   ├── locate sampled cursor d_h
│   ├── derive equalized cursor index d
│   └── derive continuous-record sample index ts
├── build_mmse_matrice()
│   ├── H_all
│   └── Rnn_all
├── choose FFE placement
│   ├── no floating groups
│   ├── heuristic
│   ├── simplified
│   └── spec-defined
├── for each placement being evaluated
│   ├── build_mmse_pruned_matrice(...)
│   ├── solve_mmse_kkt_system()
│   ├── apply_dte_limiter()
│   ├── calculate_mse()
│   └── _build_dte_status()
├── require equalized limited pulse peak at d
└── return COMDTEStatus
```

## Floating FFE variants

All modes retain fixed indices `0 .. N_fix - 1`. Floating groups must fit completely inside `[N_fix, N_max)`, each group contains `N_wf` consecutive taps, and selected groups cannot overlap.

| `floating_mode` | Implemented selection work | Solver evaluations |
|---|---|---|
| no floating groups (`N_wg=0`) | fixed taps only | one selected-placement solve |
| `heuristic` | score candidate groups from channel-sample energy, then greedily take highest-scoring non-overlapping groups | one selected-placement solve |
| `simplified` | perform one unlimited full-FFE solve, score groups from raw FFE coefficient energy, then greedily take highest-scoring non-overlapping groups | one full placement solve for scoring plus one selected-placement limited solve |
| `spec-defined` | enumerate every legal non-overlapping group placement and compare final limited MSE | one complete solve per legal placement, then one repeated solve for the selected placement to align solver diagnostics |

The two reduced modes choose groups sequentially by descending score; neither evaluates every legal placement's final limited MSE. The `spec-defined` mode is exhaustive over the legal placement set implemented by the code.

`pruned_index` is always an ascending vector with fixed taps first and selected floating taps afterward.

## Limiter and refinement boundary

For one placement, the current implementation:

1. solves the joint unlimited FFE/DFE system;
2. clips DFE feedback coefficients to configured bounds;
3. re-solves the FFE-only constrained system when DFE clipping changed the solution;
4. scales and applies the FFE bounds for the selected indices;
5. when FFE clipping changed the solution, renormalizes the limited FFE and recomputes/clips feedback coefficients;
6. calculates final candidate MSE from the limited result.

The detailed equations require separate specification validation. This contract fixes only that candidate selection uses the MSE after the current limiter/refinement flow.

## Produced `COMDTEStatus`

| Field | Shape/domain | Ownership |
|---|---|---|
| `ts` | integer sample index on the oversampled record | selected phase/cursor metadata |
| `pos` | integer phase index | selected phase metadata |
| `d` | sampled equalized cursor index | solver metadata |
| `w_lim` | `(N_max,)`, dimensionless | limited FFE, scattered into a full zero-filled vector |
| `b_lim` | `(N_b,)`, dimensionless | limited DFE feedback coefficients |
| `mse` | scalar V² | final candidate selection metric |
| `H_all`, `Rnn_all` | full-domain matrices | solver diagnostics |
| `pruned_index` | selected FFE indices | placement diagnostic |
| `H`, `R_nn`, `H_b` | selected-domain matrices | solver diagnostics |
| `w` | `(N_max,)`, dimensionless | unlimited FFE scattered into a full zero-filled vector |
| `b` | `(N_b,)`, dimensionless | unlimited DFE coefficients |

The `dfe_coeff` compatibility property returns `b_lim`. Residual ISI is not a `COMDTEStatus` field; it is constructed by the post-FFE stage.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- invalid DTE counts, placement domain, or coefficient bounds during config construction;
- `pos_coarse_stride` is non-positive or exceeds `per_ui` when coarse/fine scheduling is used;
- no valid phase survives the initial or complete sweep;
- `h_dsamp` or `R_n` is too short for `N_max`;
- sampled cursor polarity/main-cursor validation fails;
- the sampled response lacks enough postcursor samples for `N_b`;
- a floating group cannot fit or the requested number of non-overlapping groups cannot be selected;
- `pruned_index` is empty, duplicated, unordered, omits fixed tap zero, exceeds `N_max`, or omits the main tap;
- a linear system solve fails;
- returned FFE vector shape differs from `(N_max,)`;
- the limited equalized pulse peak is not at `d`.

`COMMainCursorError` rejects one phase at the orchestrator boundary. Other failures are not silently converted into phase rejection.

## Downstream consumers

| Consumer | Data read |
|---|---|
| post-FFE impairment | selected `w_lim`, `b_lim`, `d`, `pos`, and associated pre-DTE response |
| DFE COM | selected `w_lim` and `b_lim` with completed post-FFE impairment |
| MLSD | selected `b_lim` and completed DFE baseline |
| partial search | `mse`, `ts`, and `pos` |
| final search | complete selected status after rerun |
| DTE reporting | phase traces, selected phase, coefficient vectors, placement, and diagnostic matrices |

Search ranks 178A sweep candidates by lower `COMDTEStatus.mse`. Reporting consumes the stored vectors and matrices and must not rerun the solver.

## Validation evidence and tolerance

There is currently no dedicated automated unit test for phase scheduling, floating placement, limiter/refinement, or the complete `COM_MMSE_DTE` result. Existing single-run/search execution exercises the code but does not establish equation-level numerical equivalence.

Required validation remains:

1. fixed-tap-only solve against a small independently calculated system;
2. legal placement enumeration for one, two, and three floating groups;
3. deterministic heuristic and simplified group selection;
4. exhaustive mode selecting the minimum final limited MSE;
5. limiter activation cases for first/rest FFE and DFE bounds;
6. full-vector zero-fill and `pruned_index` consistency;
7. `each_phase` and circular `coarse_fine` scheduling;
8. phase rejection and exact-tie behavior;
9. explicit matrix, coefficient, and MSE tolerances against an accepted reference.

Until these exist, this document makes no specification-accuracy or numerical-tolerance claim.

## Known limitations and unresolved questions

- The current main-cursor guards are project-enforced constraints and remain pending separate theoretical/spec justification.
- `spec-defined` is exhaustive over the legal placements generated by the current code; correctness of that legal-set definition still requires specification review.
- The selected placement is solved a second time in exhaustive mode to restore diagnostic attributes, adding work without changing the intended selected placement.
- The phase scheduler retains only the selected candidate's full DTE and impairment objects; non-selected phases retain MSE/error trace values only.
- Solver matrices can be large for wide `N_max`; no stage-specific performance budget or conditioning threshold is currently documented.