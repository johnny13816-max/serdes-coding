# CP-2 — company development platform contract draft

> Status: **proposal for review, 2026-10-29**.  This is a planning document,
> not an implemented API or authorization to change protected COM behavior.
> It translates the CP-1 gap map into the smallest proposed extension boundary.

## Goal and non-goal

The current 178A baseline is the handoff source for a future, independent
company private repository.  Before handoff, its existing stages, utilities,
config/status boundaries, and functional branches must be organized around
declared interfaces so future company work can add a branch without first
redesigning those basic definitions.

This proposal deliberately does **not** introduce unrestricted dynamic plugins,
runtime discovery, or arbitrary third-party code loading.  The preferred first
implementation is an explicit, versioned registry at each supported seam.  It
is inspectable, testable, and safer for numerical/research work.

An extension may add behavior.  It may not silently alter a baseline default,
the protected numerical kernel, or the SiCoPR reference profile.  Those remain
separate change decisions with their own evidence.

## Common rules for every supported extension

| Requirement | Proposed contract |
|---|---|
| Identity | A stable extension identifier, owning version/stage, implementation revision, and maturity: `experiment`, `parallel`, or `default-candidate`. |
| Selection | Only an explicit project config/profile, case adapter, or programmatic registry selection may select an extension.  A workbook does not expose every helper switch. |
| Inputs and outputs | Typed input/output objects; required fields, units/domain, legal absence, and failure behavior are documented by the owning seam. |
| Provenance | Resolved config/profile, extension identifier/revision, input fingerprints, baseline/candidate relation, and artifact schema identity are exported together. |
| Baseline safety | `experiment` and `parallel` paths never replace baseline defaults.  Promotion to a default is an independent, reviewed change. |
| Private boundary | Private source files, channels, device data, internal result values, and internal reports stay in an independent internal repository/package.  The company repository does not depend on ongoing synchronization, rebase, or upstreaming to this project after handoff. |
| Validation | Every extension provides contract validation, a scenario-specific test, declared failure behavior, and an unchanged current SiCoPR baseline check where applicable. |

## C1 — case adapter and private-asset contract

### Owner and boundary

Before handoff, this repository supplies the versioned project schema,
`case_manifest.yaml`, conversion audit structure, and typed `COMConfig`.  After
handoff, the independent internal repository owns its private source parsers,
asset locators, credentials, company-specific metadata, and any evolution of
the copied contracts.

### Required adapter result

A supported case adapter must produce:

1. a public-compatible case manifest containing case ID, selected model,
   public-safe provenance, and project-config location or equivalent typed
   config source;
2. a typed version-specific configuration that passes the public adapter's
   validation;
3. an input fingerprint for each resolved asset; and
4. a conversion/audit record declaring source fields, derived fields, policy
   defaults, warnings, and unresolved/unsupported fields.

Private asset locations may be resolved by the internal adapter, but must not
be serialized into artifacts intended to leave the company repository.  The
handoff baseline does not import the private adapter, and the company repository
does not require a future public-repository release to continue operating.

### Compatibility rule

`case_manifest.yaml` remains metadata, not model input.  Manifest keys may be
added; changing the meaning or removal of a required public key requires a
versioned migration.  A new case must not be accepted by guessing missing
intrinsic inputs from template defaults.

## C2 — named method contract

### Owner and boundary

Each method belongs to exactly one versioned stage or utility family.  The
stage owner, not the workbook or report layer, resolves the method and invokes
it.  The core orchestrator owns ordering and baseline/default selection.

### Required descriptor

Every registered method declares:

| Field | Meaning |
|---|---|
| `method_id` / revision | Stable name and implementation revision used in config and provenance. |
| owner | Version, stage/utility family, and accountable module. |
| maturity | `experiment`, `parallel`, or `default-candidate`; never inferred from its name. |
| capability and prerequisites | Supported targets, required config/status inputs, units/domain, and incompatible modes. |
| outputs | Typed result/status fragment and legal absence rule. |
| invariants and failures | Required preserved quantities, error classes, warning policy, and prohibited silent fallback. |
| evidence | Baseline/candidate comparison boundary and required test set. |

### Selection and promotion

The first registry is explicit and version-local.  It maps a declared
`method_id` to a typed implementation; unknown identifiers fail at the
adapter/config boundary.  Existing `COMPolicyConfig` literals and execution
profiles remain the baseline implementation until a CP-3 migration is approved.

Promotion is one-way in responsibility, not automatic in code:

```text
experiment → parallel → default-candidate → separately approved baseline default
```

An experiment may live outside the production registry.  A parallel method
requires the descriptor, provenance, and comparison evidence above.  A default
change requires a separate protected-model/default-change decision.

## C3 — stage and utility contract

### Stage contract

Each supported stage declares, before implementation:

- its ordering/dependency position, owner, and top-level orchestrator call;
- typed config/policy inputs and consumed prior status fields;
- its produced typed status fragment, units/shapes, and legal absence;
- merge/replacement behavior at the root status;
- failure and partial-result behavior;
- downstream search/report consumers; and
- its method registry, if the stage supports alternatives.

CP-2 additionally creates one consolidated hierarchy index:
`software layer → stage → functional block → primary function/module`.  Existing
`software_layers.md`, `call_tree.md`, stage documents, config tree, and status
tree remain the detailed authorities; the index supplies the single navigation
view needed to identify where a future branch belongs.

The orchestrator remains responsible for sequencing and lifecycle.  A stage
does not mutate unrelated root status or choose a profile from workbook data.
Adding a new root status field or changing an existing field's meaning is a
versioned schema change, not a local stage edit.

### Utility contract

A reusable utility declares its data invariant (unit, domain, grid/reference
impedance, ownership), operation class (construction, transform, filter/
cascade, representation change), loss/overflow policy, and test oracle.  A
utility receives a fully selected method; it does not inspect case IDs or
execution profiles.  A utility method is promoted to the public extension
surface only when at least one stage owns its selection and validation.

## C4 — search and reporting contract

### Search

A supported search extension supplies a typed candidate schema, candidate-to-
config application rule, sweep evaluator, ranking metric/direction, final
evaluator, row/status schema, and failure classification.  The current
178A FFE/CTLE MSE search is the baseline strategy, not a generic format to be
silently repurposed.

Search artifacts must record: candidate schema identity, selected method/
profile IDs, resolved config fingerprint, input fingerprints, code revision,
ranking definition, and finalization coverage.  A new metric or candidate
dimension is a new named strategy, not an extra undocumented CSV column.

### Reporting

Reporters are read-only consumers of completed typed status.  A report
extension declares the status fields it requires, optional-stage behavior,
artifact schema, and manifest verification.  It cannot recompute missing model
quantities or alter config/status.  New stage presentation joins through its
own versioned reporter adapter; it does not change the cross-version base until
both versions need the same stable concept.

## C5 — compatibility, serialization, and conformance contract

### Stable boundary

The in-memory dataclasses and existing exports are not yet a general checkpoint
API.  CP-3 must designate the supported external artifacts.  The proposed
minimum is a JSON-compatible resolved-config/provenance record plus named
search/result summary records; large numerical arrays remain model-owned
artifacts rather than a promise of object reconstruction.

Every supported serialized record includes `schema_id` and `schema_version`.
Within one major schema version, changes may add optional fields with documented
absence semantics; they may not rename, remove, or change the meaning/unit of
an existing field.  Breaking changes require a new schema version plus a
reader/migration decision.

### Minimum conformance evidence

| Evidence | Required for |
|---|---|
| Typed contract validation and unknown-ID rejection | every adapter/method/stage/search/report extension |
| Provenance and schema record assertion | every persisted extension result |
| Legal absence/error-path test | every optional stage or expected failure mode |
| Current SiCoPR baseline non-regression | any change that reaches the 178A execution path |
| Candidate-specific comparison/test | parallel method, utility, stage, or search strategy |
| Private-data leak scan/review | case adapter and report/artifact additions |

## Revised CP-3 implementation order proposed by this draft

1. Complete CP-BR: reconcile current source with the authoritative
   branch-behavior document and identify missing or ambiguous same-stage
   algorithm/numerical choices.  Guard methods, input validation, exception
   paths, and data-presence conditions are outside this branch-design review.
2. Make the smallest baseline-only refactor that turns one existing stage's
   selection and utility boundary into the approved contract.  It does not add
   a company-specific alternative method.
3. Apply the same definition to every existing branch in scope only where the
   CP-BR review proves it is required; do not build a generic plugin system.
4. Use CP-4 contract/non-regression tests to prove the existing baseline
   conforms to the seams future company branches will use.

## Decisions still requiring user approval

1. **Decided:** no new company-specific branch is part of this plan.  The
   milestone is a baseline architecture that can later accept such branches
   without redesigning its basic definitions.
2. **Decided:** the company version is an independent private repository after
   handoff.  It does not depend on this project or synchronize changes back.
3. Does CP-BR review every current 178A functional branch selected by config,
   execution target, or algorithm policy (recommended), excluding ordinary
   validation/error handling and loop-local implementation details?

No implementation follows from this draft until these decisions and the CP-3
scope are approved.
