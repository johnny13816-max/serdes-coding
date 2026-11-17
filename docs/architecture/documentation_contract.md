# Documentation contract

## Purpose

Project documentation must explain the software at three stable levels:

1. the model pipeline and stage order;
2. each stage contract and its data ownership;
3. the functional blocks that implement each stage.

Governance documents use a separate authority hierarchy:

```text
AGENTS.md                              minimal always-on gates
architecture/project_workflow.md       how work is classified and completed
architecture/collaboration_contract.md how Agent and user divide work
architecture/<technical contract>.md   durable software boundaries
planning/v1_0_roadmap.md               platform direction and chapter status
planning/active_contracts.md            executable current boundary
planning/HANDOFF.md / NOTES.md          temporary context / candidate lessons
```

Do not duplicate detailed workflows in `AGENTS.md`. Do not promote HANDOFF, NOTES, planning drafts, chat text,
or a counterfactual result into a software contract without review and incorporation into the owning document.

## Document classes

```text
Project documents
├─ Rule documents
│  ├─ AGENTS.md
│  ├─ architecture/project_workflow.md
│  ├─ architecture/collaboration_contract.md
│  └─ architecture/documentation_contract.md
├─ Authoritative technical documents
│  ├─ architecture/   project-wide software contracts
│  ├─ models/         version/stage/config/status/equation contracts
│  ├─ validation/     reproducible evidence and tolerances
│  └─ operations/     supported execution and artifact procedures
└─ Temporary working documents
   ├─ planning/open_issues.xlsx
   ├─ planning/active_contracts.md
   ├─ planning/<ITEM_ID>_<short_name>.md
   ├─ planning/HANDOFF.md
   └─ planning/NOTES.md
```

Rule documents constrain how the project is changed. Technical documents define the implemented software. Temporary
documents help work progress but cannot redefine either class. A completed item promotes durable content into the
appropriate technical owner before its issue is closed; copying a temp contract verbatim is not promotion.

## Lifecycle registry

[`../document_registry.md`](../document_registry.md) 是 project document lifecycle metadata
的唯一逐檔清單。Registry 只擁有 authority class、lifecycle、content owner、update
trigger 與 closure disposition；它不擁有文件內的技術結論，也不得取代 architecture、
model、validation、operations 或 state owner。

Lifecycle 使用以下固定值：

| Lifecycle | Meaning | Update / closure rule |
|---|---|---|
| `live` | 現行 rule、technical authority、runbook、index 或 state owner | 所屬 boundary 改變時同步；不得被 temporary document 覆蓋。 |
| `active-temporary` | 唯一 active boundary 的暫存 contract | 必須由 `active_contracts.md` 指向；完成後不得保留此狀態。 |
| `paused-temporary` | 已明確暫停、可依 resume gate 恢復的 contract | 只在使用者恢復該 boundary 時更新；不得作為現行 behavior。 |
| `historical-frozen` | 已結束的 evidence、decision record 或 superseded contract | 原則上凍結；header／registry 必須指向 current owner，或說明它只擁有 dated evidence。 |
| `migration-inventory` | 尚在分流內容的過渡 inventory | 只能縮減或完成 migration；不得承接新的 durable contract。 |
| `retire-pending` | 已確認無 current ownership value、等待核准刪除 | 不得被引用為 active/current；刪除後從 registry 移除並在 closure evidence 記錄。 |

Authority class 使用 `rule`、`architecture`、`model`、`evidence`、`operations`、
`state`、`working` 或 `index`。`lifecycle=live` 不表示每次任務都要修改；它表示
該文件仍是現行 owner，只有 update trigger 成立時才更新。

每個由 Git 追蹤的 project document（`AGENTS.md`、repository `README.md`、
`docs/**/*.md`、`docs/**/*.xlsx`）必須恰好有一筆 registry entry。新增、改名、
搬移或 lifecycle transition 與 registry update 必須在同一 commit。執行
`python scripts/check_document_lifecycle.py` 檢查 coverage、enum、owner target、
active-contract linkage 與 historical/current-owner boundary；檢查通過是文件 commit
及 closure 的必要條件。

Lifecycle transition 固定為：

```text
new live authority ────────────────────────────────→ live
new modifying item → active-temporary → live promotion + delete
                                      └→ paused-temporary → active-temporary
                                      └→ historical-frozen（僅限允許保留的 ADR/evidence）
migration-inventory → content promoted → retire-pending → delete
```

不得以 `historical-frozen` 逃避 durable-content promotion，也不得僅為保持檔案而
把 completed temp contract 改成 `paused-temporary`。Destructive disposition 先列入
manifest，確認 owner/evidence 已保留並取得使用者核准後才刪除。

A raw Python call graph is not an architecture document. Calls to validation,
array conversion, plotting helpers, NumPy, SciPy, and trivial accessors are
omitted unless they change data ownership or mathematical behavior.

## COM call-tree hierarchy

For a COM model, the authoritative stage documents record the semantic call
tree using the following fixed vocabulary.  This hierarchy describes runtime
responsibility; it does not replace the separate configuration, status, or
mathematical contracts.

| Level | Name | Contract |
|---|---|---|
| Root | `COM` model | One model execution instance. Owns model config, root status lifecycle, and cross-stage lifetime. |
| L0 | Stage set | Defines the ordered stages for one run, their data handoffs, and target-dependent completion. It does not own each stage's domain algorithm. |
| L1 | Stage | One recognizable COM domain step with an explicit input, output, and status-ownership boundary. |
| L2 | Function set | A cooperating set within one stage that constructs one class of intermediate data or model objects. |
| L3 | Functional block | A domain-meaningful unit inside an L2 function set. It may own a branch behavior, its shared state, and its input/output contract. |
| L4 | Model auxiliary function | A model/version-aware helper whose complete behavior is supplied by explicit arguments. |
| L5 | Generic utility / numerical kernel | Reusable behavior independent of COM stage, version, and status semantics. A public L5 operation may own a branch; a private kernel delegated by that operation is not automatically the owner. |

For a call that crosses into a generic utility or third-party implementation,
the L4 call is normally the leaf of a stage call tree. The version Branch
Registry continues to L5 when the shared utility owns selectable mathematical
behavior. Validation guards, simple data
presence conditions, error paths, array conversion, and trivial accessors are
not algorithm branches and are normally omitted from this hierarchy.

## COM method and auxiliary-function ownership

Call-tree level does not by itself decide whether a callable belongs to the
`COM` class. Use the following ownership rule:

- make it a `COM` method when it reads resolved model/run configuration,
  accesses run-owned state, coordinates stages, commits status, or enforces a
  cross-stage invariant;
- make it a module-level auxiliary function when it is pure numerical work
  whose complete behavior is determined by explicit arguments and return
  values;
- when both concerns exist, keep a thin `COM` method as the policy/ownership
  boundary and delegate the pure numerical transform to an auxiliary function.

Branch selection and shared branch state remain visible at the owning L3
boundary. Moving numerical mechanics outside the class must not hide or
duplicate the branch decision.

## Required model documents

Each supported COM version owns:

```text
docs/models/<version>/
  README.md
  branch_behavior_registry.md
  call_tree.md
  config_tree.md
  status_tree.md
  stages/
    <stage_name>.md
```

The model README defines the stage sequence and links to every authoritative
stage document. `branch_behavior_registry.md` is the single authoritative
classification table and branch ownership/function-position tree for that
version. `call_tree.md` records the non-duplicated pipeline and stage calls.
Config and status trees are separate because their sources, ownership, and
lifecycles differ.

## Stage contract

Every model stage document records:

- purpose and ownership boundary;
- governing specification section or accepted reference;
- input objects and required fields;
- output objects and fields produced or updated;
- ordered functional blocks;
- configuration and execution-policy controls;
- failure conditions;
- downstream consumers and reports;
- validation evidence and numerical tolerance;
- known limitations or unresolved questions.

Every model stage document also records a **COM call-tree hierarchy**. It must
show the owning L1 stage entry, its L2 function sets, L3 functional blocks,
and material L4 functions in execution order. The stage tree marks structural
fan-out and may annotate a branch ID, but it must not duplicate the branch's
classification, owner conclusion, review status, or validation record. Those
records live only in the version Branch Registry. Path kind, guards, error
handling, and input presence do not become algorithm branches merely because
they select control flow.

The stage contract is authoritative even when private helper functions are
refactored.

## Functional blocks

A functional block belongs inside a stage when it has one or more of these
properties:

- an independent equation or algorithm;
- a specification reference;
- its own config or policy controls;
- ownership of status fields;
- a material effect on COM, MSE, PMF, or reported results;
- an independent validation requirement.

Each block identifies its reads, writes, algorithm variants, primary functions,
and complexity when relevant. Several functions may implement one block, and
one function may coordinate several blocks.

## Config field record

Config trees and field tables record:

- Python path and type;
- workbook parameter name;
- source: Ad Hoc/reference, project-defined, execution override, or derived;
- class: intrinsic, fixed policy, execution policy, search config, or runtime;
- unit and default;
- owning stage and consumers;
- reference-to-project and project-to-runtime mappings.

## Status field record

Status trees and field tables record:

- producing stage;
- consuming stages;
- merge or replacement behavior;
- unit, domain, grid, and array shape;
- reporting-only consumers;
- whether absence is legal at each lifecycle point.

Reporting must consume status. It must not silently recreate protected model
quantities.

## Update rule

專案技術文件用來描述特定模組、功能集、契約、設計假設，以及需要文字輔助理解與演進的抽象概念。

每項專案修改在標記 `Closed` 前，必須辨認受影響的技術文件，核對其描述是否與修改後的實作一致，
並在同一責任邊界內完成必要同步。若無需更新，須在結案紀錄簡述理由；若尚有必要文件未同步，
則不得標記 `Closed`。

同一核對也必須確認 registry entry、lifecycle 與 update trigger。文件內容沒有改變，
不代表 lifecycle metadata 一定不需改變；反之，僅更新 registry 不得取代必要的 owner
document 同步。

文件同步以既有的唯一權威文件為主，不要求每次修改新增文件，也不得藉技術文件同步修改專案治理規則。

A change to a stage boundary, config dataclass, status dataclass, workbook
mapping, semantic call tree, or reporting dependency updates its authoritative
document in the same change. Mathematical documentation is subject to the Core
Model Change Contract in `AGENTS.md` when it changes or asserts protected model
behavior.

Governance rules follow the same single-owner principle. Update links and summaries in index files, but keep the
normative wording in one owning document. Periodically remove superseded, duplicated and stale material.

Method-choice classification is governed by the
[Branch behavior contract](branch_behavior_contract.md).  A stage document
records the call-tree owner and implementation point; the version registry
records the selector, legal behaviors, and validation evidence.

At active-item closure, apply the lifecycle in `project_workflow.md`: promote durable content, reconcile trackers,
dispose of the temp contract, then slim HANDOFF and NOTES. Protected contracts or ADR-like decisions may remain only
as clearly marked historical evidence with a link to the current technical authority.

## Knowledge convergence and cross-session transfer

Treat project documentation as the durable memory for decisions and current state; conversation history and agent
recollection are temporary context. Each fact has one owning source according to the authority hierarchy above.
Other files may link to that source or carry a necessary current-state summary, but duplicated explanations must not
become competing authorities.

Before closing a non-trivial item or handing work to another session, perform a bounded reconciliation using the
item ID/name and affected behavior. Check the technical owner documents identified for the change, `active_contracts.md`,
the applicable tracker/roadmap, the temporary contract, and HANDOFF/NOTES only when they refer to the item. For every
matching current-work reference, determine whether it is authoritative current state, a synchronized pointer, valid
historical evidence, or stale content. Resolve contradictions before closure: remove completed work from active queues
and obsolete next steps; keep historical evidence only when marked `Historical / non-authoritative` and linked to its
current owner; delete superseded temporary plans unless an allowed historical record must remain. Do not scan unrelated
history or rewrite unrelated documents as part of this check.

The closure record must identify the status-owning source, the documents checked and updated, any stale entry removed
or historical record retained, and the reason when a document did not need an update. Commit the reconciled records
with the item boundary or its authorized closure commit. A new session resumes from current Git, the authoritative
technical owner, and the status-owning source; it must not reopen an item from chat recollection or a stale snapshot.
If these sources disagree, reconcile them before continuing or report the specific blocker. HANDOFF remains a compact
snapshot and never becomes the source of truth.
