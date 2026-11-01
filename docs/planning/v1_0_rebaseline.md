# v1.0 rebaseline — goals and paused inventory

> Status: **selected company-platform baseline**. CP-BR was resumed by the user;
> other paused proposals remain unchanged unless explicitly selected.

## Purpose

The prior P1–P9 sequence mixed three different outcomes: proving a maintained
178A reference platform, deciding whether/how to support 93A, and preparing a
public release. They are now separate goals. No unfinished item resumes until
the user selects one goal and approves its smallest next boundary.

## Established facts

| Area | Established evidence | Boundary |
|---|---|---|
| 178A architecture | ARC-178A-001/004 made 178A roots, config, status, path stage, and remaining helpers version-owned; `40470e8` removed 178A → 93A model dependencies. | This is ownership/behavior-preservation evidence, not universal spec certification. |
| 178A current reference case | `sicopr_akinwale_vendorx_22db` has fixed-case, search, artifact, profile/provenance, and P3 workbook-interface evidence. | It is the only current project-synchronized case used for review conclusions. |
| 93A | `case_260915_report` is an implementation-regression anchor only. No current-schema 93A golden/support claim exists. | Do not infer reference alignment, broad support, or release readiness. |
| Public release | v1.0 release gates G7, G9, G10, and G11 remain unmet. | No package/tag/release claim is authorized. |

Historical C2M workbooks remain records. They are not current runnable cases,
not migration commitments, and not blockers for the current SiCoPR 178A case.

## Re-defined goal: company development platform readiness

The active planning goal is not a public v1.0 release or a chapter-by-chapter
design review.  It is to make the 178A path a platform that can safely be
extended in a company setting while keeping the current public reference
baseline reproducible.

**Definition of done:** the current 178A baseline itself is organized around
documented stage/utility seams and reviewed branch definitions, so a future
company engineer can add a supported branch without first redesigning the
orchestrator, config/status ownership, or numerical-utility boundary.  A future
change must have a declared owner, typed input/output contract, provenance,
compatibility rule, and proportionate regression evidence.  This plan does not
implement company-specific alternative branches.

This goal does **not** assert IEEE compliance, official-tool equivalence, or
silicon correlation.  It also does not require completing a public package
release, migrating the historical C2M workbooks, or extending 93A unless a
later company use case explicitly selects them.

## New plan — company development platform

The old P4–P9 sequence is historical context only.  It is not the work queue
below.  P1–P3 remain evidence of useful foundations (product boundaries,
version ownership, and the current SiCoPR config facade), but are not treated
as proof of platform readiness.

| ID | Outcome to establish | Work and required output | Exit evidence |
|---|---|---|---|
| CP-0 | A bounded company-use target | State the supported extension scenarios and non-goals.  The default scenarios are: add a case/input adapter; add a named method inside an existing stage; add a stage or utility; add search/report output. | A one-page platform charter with claim boundary, private-data boundary, and the chosen scenarios. |
| CP-1 | A factual map of present extension seams | Review current entry points, config/status trees, stages, utilities, search, and reporting.  For every scenario, name the owner, insertion point, inputs, outputs, and current hidden coupling. | A gap map distinguishing reusable seams, local-only code, and places that need a new contract. |
| CP-BR | Algorithm-branch document reconciliation and review | Reconcile current source against the authoritative 178A branch-behavior technical document.  The scope is a same-stage choice between different algorithmic/numerical methods; it excludes guard methods, input-validity checks, exception/error paths, and simple data-presence conditions.  Inventory every in-scope branch's selector, owner, input/output/status effect, baseline role, legal combinations, provenance, and regression evidence. | `docs/models/178A/branch_behavior_registry.md` is completed or corrected as the authoritative algorithm-branch document; every in-scope behavior is accepted, constrained, reclassified, or queued for refactor.  No undocumented algorithm branch remains. |
| CP-2 | Stable extension contracts and hierarchy map | Define the minimum contracts for case adapters, execution profiles/method selection, stage and utility interfaces, status/artifact serialization, and reporting readers.  Add one consolidated `stage → functional block → primary function` hierarchy map, linked to the existing layer/call/config/status documents.  Specify ownership, versioning, legal absence, error/provenance behavior, and backward-compatibility policy. | Reviewed technical contract documents plus the consolidated hierarchy map; baseline behavior stays unchanged. |
| CP-3 | Baseline seam implementation | Refactor only the current baseline where CP-BR/CP-2 proves a basic definition is missing: make existing stage selection, config/status ownership, and utility interfaces explicit.  Do not add a company-specific alternative branch. | Existing baseline paths implement the approved seams; a future branch can be localized without redesigning the core architecture. |
| CP-4 | Extensibility proof without a new algorithm | Prove the seam using existing baseline behavior: contract tests, selection/unknown-ID rejection where applicable, status/provenance assertions, and SiCoPR non-regression. | Evidence that the current baseline conforms to the new contracts; no new company method is required. |
| CP-5 | Company-use operational boundary | Provide reproducible setup/run instructions, an extension author checklist, data/attribution rules, compatibility/deprecation policy, and a minimal review gate for future changes. | A new engineer can run the baseline and follow one extension example; private data stays outside the repository. |

## Completion gate

The plan is complete only when CP-0 through CP-5 are closed and the following
claims are supported by evidence:

1. The current SiCoPR reference baseline remains reproducible.
2. Existing functional branches have a reviewed owner and contract; future
   additions have explicit, tested seams rather than edits scattered through
   the baseline orchestration.
3. Config, runtime status, artifacts, and reports retain enough provenance to
   compare a named extension with the baseline.
4. A company team can keep private cases, data, and results outside the public
   repository while using the same public-safe contracts.

Items such as public packaging, 93A support, C2M migration, new numerical
methods, and presentation refinement become separate follow-on contracts only
when they are selected as a company use case.

## Paused inventory

| Item | State | Resumption gate |
|---|---|---|
| Old P4–P8 design-review chapters | Superseded / paused | They are not resumed.  CP-1 determines which concrete gaps still matter. |
| Old P9/release preparation | Paused | Public release is a separate decision after CP-5, not this plan's completion criterion. |
| ARC-CROSS-001 current-schema 93A golden | Paused | Select 93A as a concrete company-use scenario and approve its source, schema strategy, baseline, and validation level. |
| ARC-REPORT-001 plot refinement | Paused | Select reporting as a CP-0 scenario and provide the exact user-facing defect or need. |
| C2M workbook migration | Not planned | Explicitly promote a named historical case to a supported case. |

`open_issues.xlsx` records B-005 as Closed and B-006 as the single Approved
review item. `active_contracts.md` is the authority for the active CP-BR
boundary and the remaining paused workstreams.

## Decision order

1. Perform CP-BR to review the existing functional branch map.
2. Review CP-2 contracts against the accepted current branch definitions.
3. Approve only the minimum CP-3 baseline-seam refactor required by those
   findings; do not introduce company-specific algorithms.
4. Keep all old items paused unless a CP item explicitly adopts one.
