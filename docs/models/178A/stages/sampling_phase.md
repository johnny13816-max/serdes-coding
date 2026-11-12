# 178A Stage 3 — Sampling search function set

> **Review state:** SRCH-001 ownership was corrected on 2026-11-13 after the
> Stage numbers were retained as runtime/navigation labels but retired as the
> primary ownership coordinate.
> The semantic owner is the Sampling search function set; the concrete callable
> owner is the phase-search loop in `COM._run_once()`.

## Purpose

Stage 3 Sampling search is a control function set, not a physical/numerical model. It:

- resolves `each_phase` or `coarse_fine` plus `pos_coarse_stride`;
- determines phase visit order;
- records per-phase MSE or `COMMainCursorError` in `COMRunStatus`;
- retains the strict-minimum-MSE complete bundle;
- commits the selected `eq_ch`／`imp`／`dte` bundle atomically.

It does not construct pre-DTE impairment or solve MMSE-DTE. Those domain
operations remain directly visible in the root runtime flow.

## Runtime flow and domain boundaries

```text
Stage 3 — COM._run_once() phase-search loop      [SRCH-001 concrete owner]
├── read pos_sweep_method / pos_coarse_stride   [sole selector read]
├── _initial_pos_sweep_indices(...)             [schedule helper; non-owner]
├── while one phase batch remains
│   └── for pos in phase batch
│       ├── Stage 2 — Pre-DTE model
│       │   └── calculate_pre_dte_imp_at_pos(...)
│       ├── Stage 4 — DTE solver
│       │   └── calculate_MMSE_DTE(...)
│       └── Stage 3 — Sampling search control
│           ├── record MSE or cursor error
│           └── retain strict-minimum complete bundle
├── coarse_fine only
│   └── _fine_pos_sweep_indices(...)            [schedule helper; non-owner]
└── _assign_selected_phase(...)                 [commit validator; non-owner]
```

Stage numbering describes the runtime domains, not a single-pass linear call
order: the Stage 3 controller repeatedly invokes Stage 2 and Stage 4. This
caller relationship does not transfer ownership between those function sets.

One shared phase-batch loop executes both the initial and optional fine batch.
Coarse/fine changes only the next batch of positions; it does not duplicate or
wrap the Pre-DTE and DTE operations.

## SRCH-001 owner boundary

The phase-search loop inside `COM._run_once()` is the smallest cohesive callable
boundary that can keep all of these responsibilities together while leaving
the physical domain operations visible:

- selector dispatch and visit-order state;
- initial-to-fine feedback through the current best phase;
- error/MSE records;
- strict-minimum complete-bundle retention;
- final selected-bundle commit.

Extracting this loop would either hide the Pre-DTE/DTE runtime architecture or
create a callback-only forwarding wrapper. Therefore `_run_once()` is the
approved concrete owner for this one control block; it is not the owner of the
Pre-DTE or DTE algorithms it calls.

`_initial_pos_sweep_indices()` and `_fine_pos_sweep_indices()` receive concrete
values and never read project config. `calculate_pre_dte_imp_at_pos()` owns its
Pre-DTE result, `COM_MMSE_DTE.run()` owns ALG-010 dispatch, and
`_assign_selected_phase()` only validates/publishes the already-selected bundle.

## Candidate and status contract

One successful phase produces a local bundle:

```text
phase candidate
├── eq_ch: COMEqChannelStatus
│   ├── phase_index == pos
│   ├── pre_dte is present
│   └── post_ffe is None
├── imp: COMImpairmentStatus
│   ├── pre_dte is present
│   └── post_ffe is None
└── dte: COMDTEStatus
    ├── pos == phase_index
    └── H_rxffe is present
```

Only the current best complete bundle is retained. Exact MSE ties keep the
earlier evaluated candidate because replacement uses strict `<`.
`COMRunStatus.coarse_pos`, `fine_pos`, `mse_by_pos`, and
`main_cursor_error_by_pos` preserve the search trace without retaining every
full candidate object.

## Preserved behavior

- `each_phase` visits every integer phase.
- `coarse_fine` visits the configured coarse set, then unvisited positions in
  the circular fine window around the best valid coarse phase.
- `COMMainCursorError` rejects only the affected phase; other exceptions
  propagate.
- XT independent-phase preparation belongs to the Pre-DTE model and is not
  controlled by SRCH-001.
- NUM-003, ALG-008, NUM-004 and ALG-010 retain their independent owners.

## Validation

`tests/test_com_model_178A_stage_commit.py` executes the real `_run_once()`
control flow with isolated domain operations. It verifies coarse/fine visit
order, one shared batch loop, complete-bundle retention, cursor rejection,
strict-tie behavior, status traces and atomic commit. The policy ownership test
statically confirms `_run_once()` is the only production reader of the two
SRCH-001 selector fields. Focused/policy validation is `49 passed`; the fixed
SiCoPR production golden is `1 passed`, confirming the structure rewrite did
not change the accepted selected-phase or downstream numerical outputs.
