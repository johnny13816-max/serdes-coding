# 178A Stage 3: sampling-phase evaluation

> **Review state:** implemented ownership and behavior-preservation contract.
> Phase scheduling, MSE comparison, selected-candidate retention, and atomic
> commit are covered by focused tests. Branch algorithms remain subject to
> their individual CP-BR review.

## Purpose

Stage 3 owns the evaluation envelope for sampling phase. It generates the
requested phase set, builds each phase's pre-DTE equivalent-channel and
impairment data, invokes Stage 4, and selects the valid candidate with the
lowest DTE MSE.

Before the victim-phase loop, Stage 3 also selects each XT path's independent
worst-energy phase from its **full oversampled response**. This is not the
victim sampling phase. It produces one full-length one-sample/UI `eq_ch_XT`
record per path, then passes those records through the shared NUM-003 L3 to form
`S_xn`.

It does not change the existing phase definition, retain every candidate's
full status, solve MMSE internally, or construct post-FFE results.

## COM call-tree hierarchy

```text
COM._run_once()                                      [L0: stage set]
└── Stage 3: sampling-phase evaluation               [L1]
    ├── XT phase / common impairment preparation     [L2]
    │   ├── _select_xtalk_path_phase()               [L3/L4]
    │   └── eq-channel impairment PSD construction   [Shared L3; NUM-003]
    │       ├── _realize_eq_ch_imp_record()          [L4]
    │       └── _build_eq_ch_imp_psd()               [L4]
    ├── phase-set construction                       [L2]
    │   ├── _initial_pos_sweep_indices()             [L3/L4]
    │   └── _fine_pos_sweep_indices()                [L3/L4]
    ├── one-phase candidate construction             [L2]
    │   └── calculate_pos_candidate()                [L3]
    │       ├── calculate_pre_dte_imp_at_pos()       [L4]
    │       └── calculate_MMSE_DTE()                 [L4: Stage 4 handoff]
    ├── minimum-MSE selection                        [L2]
    │   └── strict candidate.mse comparison          [L3/L4]
    └── selected-phase commit                        [L2]
        └── _assign_selected_phase()                 [L3/L4]
```

## Candidate contract

One phase evaluation produces a local bundle:

```text
phase candidate
├── eq_ch: COMEqChannelStatus
│   ├── phase_index == pos
│   ├── pre_dte: COMPreDTEEqChannelStatus
│   └── post_ffe is None
├── imp: COMImpairmentStatus
│   ├── pre_dte is present
│   └── post_ffe is None
└── dte: COMDTEStatus
    ├── pos == phase_index
    └── H_rxffe is present
```

The loop retains only the current minimum-MSE complete bundle. Exact ties keep
the earlier evaluated candidate. `COMRunStatus.mse_by_pos` and
`main_cursor_error_by_pos` retain per-phase summaries; non-selected full
candidate objects are not persisted.

## Atomic commit

`_assign_selected_phase()` validates the phase identity and required lifecycle
state before replacing the root `eq_ch`, `imp`, and `dte` together. Validation
failure leaves the existing root status unchanged. A completed Stage 3 result
therefore cannot combine equivalent-channel, impairment, and DTE data from
different phases.

Stage 5 later adds `eq_ch.post_ffe` and `imp.post_ffe` through a separate atomic
commit. It cannot change `phase_index`, pre-DTE objects, or the selected DTE.

## Preserved behavior

- `phase_index` is the existing zero-based `pos` in `[0, per_ui)`.
- `each_phase` and `coarse_fine` phase generation are unchanged.
- `COMMainCursorError` skips only the affected phase.
- Other candidate failures propagate.
- Minimum MSE uses the existing strict lower-than comparison.
- No new phase-candidate dataclass or full-candidate history is introduced.
- XT phase selection always sees the full response; NUM-003 may only alter the
  record passed into PSD/correlation construction.

## Validation

`tests/test_com_model_178A_stage_commit.py` checks that mismatched selected or
post-FFE phase commits fail without partial root updates and that a valid Stage
5 commit preserves selected pre-DTE and DTE object identity. Existing golden,
post-FFE, policy, and phase-run tests protect the numerical selection path.
