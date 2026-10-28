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

A raw Python call graph is not an architecture document. Calls to validation,
array conversion, plotting helpers, NumPy, SciPy, and trivial accessors are
omitted unless they change data ownership or mathematical behavior.

## Required model documents

Each supported COM version owns:

```text
docs/models/<version>/
  README.md
  call_tree.md
  config_tree.md
  status_tree.md
  stages/
    <stage_name>.md
```

The model README defines the stage sequence and links to every authoritative
stage document. `call_tree.md` records semantic calls between entries,
workflows, and stages. Config and status trees are separate because their
sources, ownership, and lifecycles differ.

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

A change to a stage boundary, config dataclass, status dataclass, workbook
mapping, semantic call tree, or reporting dependency updates its authoritative
document in the same change. Mathematical documentation is subject to the Core
Model Change Contract in `AGENTS.md` when it changes or asserts protected model
behavior.

Governance rules follow the same single-owner principle. Update links and summaries in index files, but keep the
normative wording in one owning document. Periodically remove superseded, duplicated and stale material.
