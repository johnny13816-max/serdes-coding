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

```text
COMConfig
├── specification / case configuration
│   └── physical parameters, topology, supplied files, and case data bounds
├── branch behavior configuration
│   ├── selector: chooses a named realization
│   └── branch parameter: only meaningful for a particular selector
├── execution configuration
│   └── run extent, search coverage, accuracy, convergence, and scheduling
└── provenance
    └── profile name, raw/effective overrides, and source history
```

| Class | Definition | Examples | Is it a branch behavior? |
|---|---|---|---|
| Specification / case configuration | Defines the modeled physical case or an externally supplied input. | package values, S-parameter paths, explicit measured-band limit | No |
| Branch selector | Chooses a documented alternative realization of one semantic operation. | CTLE realization, renormalization order | Yes |
| Branch parameter | Supplies a parameter required by one selected branch; it has no independent algorithm identity. | `num_trunc_ui` for `eq_ch_imp_len="truncated"`, Gaussian support value for an override method | Part of its parent branch only |
| Execution configuration | Controls whether, how far, or how accurately work is performed without defining a model method. | target, sweep coverage, grid-quality setting | Normally no; see review rule below |
| Input/boundary handling | Handles absent, malformed, or bounded data. | missing-DC completion, file-read errors | No |
| Fixed implementation behavior | Has one supported behavior and no selectable alternate. | a fixed utility contract | No |
| Provenance | Explains how effective settings were obtained, but must not decide model flow. | profile name and override record | No |

An execution control becomes a branch-behavior candidate only if its choices
select materially different algorithms or numerical formulations, rather than
only work coverage, tolerance, or scheduling.

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

## Current review set

The following items are explicitly in scope for review before the registry's
classification is treated as settled:

| Candidate | Current location | Review question |
|---|---|---|
| B-019 missing-DC handling | channel config / branch registry | Is this solely input-boundary handling, as expected, and therefore not a branch? |
| B-020 utility time-domain cascade | shared utility / branch registry | Is there a real supported selector, or is this a fixed utility contract? |
| `policy.xtalk_pmf_accumulation` | `COMPolicyConfig` | Does it have a genuine alternate method, or is it fixed behavior that should leave branch configuration? |
| E-002 `pre_dte_pmf_method` | execution profile | Does its approximation/exact choice make it a model-method branch? |
| E-003 / E-004 PMF grid and convergence controls | execution profile | Are these coverage/accuracy controls only, or does any option define a distinct numerical method? |
| E-005 `floating_mode` | execution profile | Does each value select a distinct DTE solve method and therefore require branch treatment? |
| E-006 phase sweep | execution profile | Is it an L0 evaluation strategy rather than an in-stage model branch? |
| `gaussian_n_sigma_override` | `COMPolicyConfig` | Is it recorded only as the support branch's parameter rather than a standalone branch? |
| `applied_config_profile` / `config_profile_overrides` | `COMPolicyConfig` | Should provenance be structurally separate from behavior selectors? |

The source inventory is [178A branch behavior registry](../models/178A/branch_behavior_registry.md).  Stage-specific ownership is documented in the corresponding files under `docs/models/178A/stages/`.

## Maintenance rule

Any new non-specification method choice must be classified under this contract
before it is exposed in a public config, workbook, or preset.  A new case
parameter must not be promoted to a branch merely because it changes a result.
