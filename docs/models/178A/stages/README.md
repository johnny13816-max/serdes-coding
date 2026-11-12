# 178A domain function-set documentation

This directory owns the stable input/output, dataclass and status-lifecycle
contract for each 178A domain function set. Functional blocks are documented
inside their owning domain; small private helpers remain in source docstrings.

The primary semantic hierarchy is `COM model → domain function set → functional
block → operation/helper`. Numbered stages are no longer used as an ownership
coordinate because Sampling search repeatedly invokes both the Pre-DTE model
and DTE solver. Runtime order and loops are documented separately in
[`call_tree.md`](../call_tree.md).

## Domain function sets and owned dataclasses

- [Path realization](path_construction.md) → `COMPath`／`status.paths`.
- [Pre-DTE model](pre_dte.md) → `COMPreDTEEqChannelStatus` and
  `COMImpStageStatus(pre_dte)`.
- [Sampling search](sampling_phase.md) → `COMRunStatus` and selected-bundle
  control; it owns no physical model dataclass.
- [DTE solver](mmse_dte.md) → `COMDTEStatus`.
- [Post-FFE model](post_ffe.md) → `COMPostFFEEqChannelStatus` and
  `COMImpStageStatus(post_ffe)`.
- [DFE COM model](com_dfe.md) → `COMPMFStatus`.
- [MLSD model](com_mlsd.md) → `COMMLSDStatus`.

Reporting and search are downstream orchestration layers documented in [Reporting architecture](../../../architecture/reporting_architecture.md), [Search execution](../../../operations/search_execution.md), and the model [Call tree](../call_tree.md).

## Review state

A domain document distinguishes:

- **implemented structure**: confirmed from current source;
- **validated behavior**: backed by a named test or reproducible reference case;
- **unresolved**: requires specification or numerical review.

Source inspection alone does not validate a protected model equation. Mathematical assertions are added only through the Core Model Change Contract defined in `AGENTS.md`.

## Branch review index

分支分類、review status、validation evidence，以及每個 branch 在 semantic
function call tree 中的位置，統一由
[178A Branch Behavior Registry](../branch_behavior_registry.md) 保存。本目錄的
domain 文件只描述各 function set 的 I/O、dataclass、data handoff、function
ordering 與未解決的 domain-local technical question，不另建 branch progress 或
owner 表。
