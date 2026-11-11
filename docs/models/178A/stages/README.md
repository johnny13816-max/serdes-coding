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

## Branch review index

分支分類、review status、validation evidence，以及每個 branch 在 semantic
function call tree 中的位置，統一由
[178A Branch Behavior Registry](../branch_behavior_registry.md) 保存。本目錄的
stage 文件只描述各 stage 的 I/O、data handoff、function ordering 與未解決的
stage-local technical question，不另建 branch progress 或 owner 表。
