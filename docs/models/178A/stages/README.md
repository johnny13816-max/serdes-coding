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
| 1 Path construction | Recorded | B-002, B-003 | B-001 external evidence; B-020 classification |
| 2 Pre-DTE impairment | Recorded | B-005 shared-L3 ownership and config exposure | B-006 **pending**（疑似 D3p2 差異，待規範證據）；**B-008 next**；B-009, B-010, B-014, E-002, E-003/E-004 |
| 3 Sampling-phase evaluation | Recorded | Stage boundary; B-005 XT-phase separation | Remaining Stage 3 candidates after Stage 2 review |
| 4 MMSE DTE | Recorded | None under current CP-BR pass | Branch review not started |
| 5 Post-FFE impairment | Recorded | B-005 shared-L3 consumer | B-004 formal review deferred until Stage 5 |
| 6 DFE COM | Recorded | B-007 closed as fixed/equivalent accumulation; dependent B-015 removed | B-011, B-012, B-013 |
| 6 DFE COM | Recorded | None under current CP-BR pass | Branch review not started |
| 7 MLSD COM | Recorded | B-005 `S_isi` shared-L3 consumer | Branch review not started |

B-005 closed on 2026-11-01 after implementation, documentation/workbook
sync, unchanged SiCoPR golden COM values, branch isolation tests, and full
non-GUI regression. B-006 is pending for D3p2 evidence. B-007 closed on
2026-11-02 after removing its false runtime branch and proving the two final
quantization accumulation orders equivalent; full non-GUI regression passed.
The next active review item is B-008.
