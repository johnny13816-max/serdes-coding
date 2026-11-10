# Branch behavior contract

## Purpose

This contract defines how the project distinguishes a researchable algorithm
or numerical-method choice from ordinary model configuration.  Its purpose is
to keep future model extension explicit: adding a method must not require
guessing whether it is a case input, an implementation detail, or a supported
parallel behavior.

This contract defines classification and documentation obligations.  It does
not approve any new method, change a model equation, or make an existing
candidate selectable.

## Definition

A **branch behavior** is a named choice between two or more algorithmic or
numerical realizations of the same semantic operation for the same class of
valid physical input.  It exists when the governing specification does not
uniquely prescribe one realization, or when the project deliberately retains
an alternate/reference realization for research comparison.

One option may be the specification-facing baseline.  The choice remains a
branch behavior when a second, explicitly bounded realization is supported.
The branch is project-owned; a specification must not be represented as
selecting between project methods unless it actually does so.

## Configuration classes

The canonical classification is shared by branch review, Project Config, and
runtime-config migration.  Project Config uses the full names; the 178A
runtime target uses the registered lower-case abbreviations for grouped fields.
`physical_input` remains in the physical object tree instead of gaining a
`cfg.phy` wrapper.

| Prefix | Canonical class | 178A runtime target | Boundary |
|---|---|---|---|
| `PHY` | `physical_input` | root fields such as `cfg.link` and `cfg.channel` | System, specification, topology, physical conditions, and case data bounds. |
| `SRC` | `block_source` | `cfg.src` | Selected data/design artifact, its identity, format, units, interface, and interpretation metadata. |
| `ALG` | `algorithm_policy` | `cfg.alg` | Named mathematical or numerical realization of one semantic operation. |
| `NUM` | `numerical_control` | `cfg.num` | Resolution, convergence, truncation, precision, and computational cost. |
| `SRCH` | `search` | `cfg.srch` | Search variables, candidate coverage, search strategy, and result-retention controls. |
| `EXE` | `execution` | `cfg.exe` | Run extent, scheduling, and stage gates that do not change formulas in an executed stage. |

`intrinsic` is a Project Config parameter class, not a runtime wrapper.  A
derived value remains with its physical dataclass (`init=False`/`__post_init__`),
its runtime owner, or status.  Profile/source history is adapter or report
metadata.  Neither `derived` nor `provenance` is a top-level runtime control
group, and neither may select numerical flow.

| Class | Definition | Examples | Is it a branch behavior? |
|---|---|---|---|
| Specification / case configuration | Defines the modeled physical case or an externally supplied input. | package values, S-parameter paths, explicit measured-band limit | No |
| Branch selector | Chooses a documented alternative realization of one semantic operation. | CTLE realization, renormalization order | Yes |
| Branch parameter | Supplies a parameter required by one selected branch; it has no independent algorithm identity. | `num_trunc_ui` for `eq_ch_imp_len="truncated"`, Gaussian support value for an override method | Part of its parent branch only |
| Execution configuration | Controls whether or how far one resolved run executes, without changing formulas in a stage that executes. | target, stage gate | No; if a value changes method, accuracy, convergence, search coverage, or candidate selection, classify it under `ALG`, `NUM`, or `SRCH` instead. |
| Search configuration | Controls variables, candidate coverage, search strategy, or result retention. | TX FFE/CTLE candidate axes, sampling-phase search, top-K retention | No, unless a choice independently satisfies the branch-behavior definition. |
| Input/boundary handling | Handles absent, malformed, or bounded data. | missing-DC completion, file-read errors | No |
| Fixed implementation behavior | Has one supported behavior and no selectable alternate. | a fixed utility contract | No |
| Provenance | Explains how effective settings were obtained, but must not decide model flow. | profile name and override record | No |

An execution or search control becomes a branch-behavior candidate only if its
choices select materially different algorithms or numerical formulations,
rather than only run extent, coverage, tolerance, retention, or scheduling.

## Required structure and ownership

Every approved branch behavior must have:

1. one semantic operation and one owner in the COM call-tree hierarchy;
2. one L3 functional-block owner that owns the choice, its shared state, and
   its extension contract;
3. one or more L4 execution points that realize each choice;
4. a documented selector, legal values, project default, and provenance path;
5. any branch parameters and their applicability conditions;
6. stated inputs, outputs, quantities allowed to change, and quantities that
   must remain unchanged;
7. a stage-local regression or isolation test; and
8. a row in the version's branch behavior registry and a link from the owning
   stage document.

Structural fan-out (for example victim/NEXT/FEXT), guards, error handling,
input presence, and ordinary object construction do not become branch behavior
merely because they choose control flow.

An L3 owner may be shared by several stages when the same semantic branch must
govern all consumers. In that case the registry must say **multiple stages
involved / Shared L3**, name every consumer stage, and expose one selector and
one resolved branch state. Each review conclusion must explicitly record:

1. the coding-layer owner and execution points;
2. whether the selector remains independently exposed in project config and
   the workbook;
3. conditional branch parameters and validation rules;
4. project default and profile/preset overrides; and
5. quantities allowed to change and quantities required to remain unchanged.

## Review rule for existing candidates

Existing entries may remain documented while their classification is under
review.  A review must decide exactly one of the following outcomes:

| Outcome | Meaning |
|---|---|
| Approved branch behavior | Keep or add a selector and complete the required ownership record. |
| Branch parameter | Attach the value to its owning approved branch; do not give it an independent branch identity. |
| Execution strategy | Keep it separate from model-method branches and record its L0/L1 owner. |
| Case/input boundary | Record it with the case/config contract, not as a method choice. |
| Fixed behavior | Remove selector language and document the single utility or model contract. |
| Provenance | Store/export it without allowing it to control numerical flow. |

No candidate is reclassified, removed, or implemented differently solely by
adding it to the review list.

## Stage-by-stage completion lifecycle

Branch review advances one model stage at a time. A stage is not complete
merely because its desired ownership tree has been documented. For every
non-pending decision in the stage, documentation, implementation, and
validation move together.

```text
1. Record the stage L2/L3/L4 call tree and candidate inventory.
2. Decide each candidate: approved branch, parameter, execution strategy,
   boundary, fixed behavior, provenance, or pending external evidence.
3. For every decided change, update the owning technical contract, code, and
   focused regression/isolation test in the same stage-completion change.
4. Validate the resolved paths against the prior accepted behavior.
5. Remove resolved items from that stage's review-candidate list; retain only
   explicit pending items with their blocking evidence.
6. Only then begin the next stage's detailed branch review.
```

The version branch registry remains the durable record of approved behavior.
The per-stage review-candidate list is temporary: it contains only unresolved
or pending classification/implementation work, never completed items.

## Current review sources

The former candidate checklist duplicated review questions whose decisions are
now recorded in the [178A branch behavior registry](../models/178A/branch_behavior_registry.md)
and the [stage-by-stage progress table](../models/178A/stages/README.md#cp-br-review-progress).
Do not treat resolved classification questions or retired controls as current
review work. The registry owns current classification and legacy-ID mapping;
stage documents and `active_contracts.md` identify implementation or evidence
that remains pending. Add a candidate here only when it is unresolved, has a
named owner and scope, and records the evidence that blocks a decision.

## Maintenance rule

Any new non-specification method choice must be classified under this contract
before it is exposed in a public config, workbook, or preset.  A new case
parameter must not be promoted to a branch merely because it changes a result.
