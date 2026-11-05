# 178A stage documentation

This directory owns the stable input/output and status-lifecycle contract for each 178A model stage. Functional blocks are documented inside their owning stage; small private helpers remain in source docstrings.

Every stage document also records the same semantic `COM` call-tree hierarchy:
`COM` model → stage set → stage → function set → functional block → function.
The tree is used to review whether each algorithm branch belongs to the correct
L3 structural owner; it is not a raw Python call graph.

## Stage order and status

1. [Path construction](path_construction.md) — implemented structural contract; specification equations still require independent reference validation.
2. [Pre-DTE impairment](pre_dte.md) — phase-independent common impairment plus the numerical per-phase builder consumed by Stage 3.
3. [Sampling-phase evaluation](sampling_phase.md) — phase scheduling, candidate pairing, minimum-MSE selection, and atomic selected-phase commit.
4. [MMSE DTE](mmse_dte.md) — one-phase floating placement, limiter flow, MSE, and `H_rxffe` finalization.
5. [Post-FFE impairment](post_ffe.md) — selected-phase post-FFE equivalent responses and impairment, committed together without changing the selected phase.
6. [DFE COM](com_dfe.md) — implemented final-PMF accuracy override, component ownership, quantization handoff, combined PMF, and scalar result contract; equations still require independent reference validation.
7. [MLSD COM](com_mlsd.md) — implemented added-noise calibration, convergence history, MLSD PSD/autocorrelation, truncated DER, final adjustment, and reporting contract; equations still require independent reference validation.

Reporting and search are downstream orchestration layers documented in [Reporting architecture](../../../architecture/reporting_architecture.md), [Search execution](../../../operations/search_execution.md), and the model [Call tree](../call_tree.md).

## Review state

A stage document distinguishes:

- **implemented structure**: confirmed from current source;
- **validated behavior**: backed by a named test or reproducible reference case;
- **unresolved**: requires specification or numerical review.

Source inspection alone does not validate a protected model equation. Mathematical assertions are added only through the Core Model Change Contract defined in `AGENTS.md`.

## CP-BR review progress

This table is the consolidated progress view for the per-stage layered call
trees. Detailed behavior remains authoritative in each linked stage document
and in the [branch registry](../branch_behavior_registry.md).

| Stage | Layered call tree | Closed decisions | Pending / next |
|---|---|---|---|
| 0 Input/shared utilities/pipeline gate | Registry-owned | ALG-001, ALG-002, ALG-003 | PHY-001, NUM-001, NUM-002, EXE-001 |
| 1 Path construction | Recorded | ALG-005, ALG-006 | ALG-004 external evidence |
| 2 Common impairment | Recorded | NUM-003 shared-L3 ownership and config exposure；legacy B-009 removed | No additional Stage 2 owner |
| 3 Sampling-phase / ADC input | Recorded | NUM-003 XT-phase separation；NUM-004 ADC-input grid | SRCH-001, ALG-007, ALG-008, NUM-006 |
| 4 MMSE DTE | Recorded | None under current CP-BR pass | ALG-009 |
| 5 Post-FFE impairment | Recorded | NUM-003 shared-L3 consumer | ALG-010 |
| 6 DFE COM | Recorded | NUM-005 final-grid domain | ALG-011 pending D3p2 evidence；ALG-012 |
| 7 MLSD COM | Recorded | NUM-003 `S_isi` shared-L3 consumer | ALG-013, ALG-014, ALG-015, ALG-016 |

NUM-003 (legacy B-005) closed on 2026-11-01 after implementation,
documentation/workbook sync, unchanged SiCoPR golden COM values, branch
isolation tests, and full non-GUI regression. ALG-007 and ALG-011 are pending
D3p2 evidence. ALG-011's RG name and observability status are recorded without
changing its numerical flow; main-tap accumulation is a separate deferred
issue, not an ALG-011 option.
