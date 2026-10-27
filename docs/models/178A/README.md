# IEEE 802.3dj 178A model documentation

This directory is the first model-documentation vertical slice.
It follows the stage-first rules in
[`../../architecture/documentation_contract.md`](../../architecture/documentation_contract.md).

## Authoritative and planned documents

1. [Configuration tree](config_tree.md) — implemented dataclass ownership, workbook mapping, fixed policy, execution policy, and search configuration.
2. [Status tree](status_tree.md) — implemented `COMStatus` lifecycle, nested ownership, assignment rules, and reporting/search consumers.
3. [Call tree](call_tree.md) — implemented manual entry, single run, local search, distributed search, execution-policy boundaries, and semantic model-stage calls.
4. [Branch behavior registry](branch_behavior_registry.md) — authoritative project defaults, alternate/reference methods, stage ownership, responsibility boundaries, and validation evidence.
5. [Stage documentation](stages/README.md) — stage-by-stage input/output, ownership, controls, failure boundaries, validation evidence, and unresolved review items.
6. [Design review](design_review.md) — v1.0 前的逐章審查順序、結論、證據與待決事項。

## Stage order

The first documentation pass will establish, from source and accepted
specification references:

```text
channel and path construction
pre-DTE common impairment
sampling-phase-specific pre-DTE impairment
MMSE DTE
post-FFE impairment
COM DFE
COM MLSD
reporting and search consumers
```

This index intentionally does not assert equation details before the individual
stage review is completed under the protected-kernel rules in `AGENTS.md`.

## Supporting artifacts

- [Single-run stage I/O workbook](artifacts/single_run_stage_io.xlsx)
