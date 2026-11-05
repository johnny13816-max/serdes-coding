# CP-1 — company development platform seam and gap map

> Status: **read-only assessment, 2026-10-29**.  This records the current
> 178A implementation boundary and does not authorize an architecture or code
> change.  The target is the company-development-platform goal in
> [`v1_0_rebaseline.md`](v1_0_rebaseline.md), not the superseded P4–P9 review.

## Assessment question

Can a future engineer add a supported capability at one declared seam, preserve
the SiCoPR baseline, and obtain provenance and regression evidence without
editing hidden baseline flow or introducing private assets into this repository?

**Answer today: partly.**  Case conversion and read-only reporting already have
useful boundaries.  Method, stage/utility, and search extension do not yet have
formal insertion contracts; additions there currently require coordinated edits
to version-specific implementation and its fixed configuration/status shape.

## Present seam map

| CP-0 scenario | Existing insertion point and evidence | Reusable boundary | Gap before it is a supported company seam |
|---|---|---|---|
| Add a case/input adapter | `io/conversion/` owns source-to-project conversion and safe `cases/<case_id>/<version>/config.xlsx` paths; `case_manifest.yaml` records case identity/provenance/model pairing; `io/com_excel_io_178A.py` owns project workbook to typed 178A config. | Versioned workbook schema, channel validation, source audit, case manifest, resolved config export. | The manifest is repository-local metadata, not a typed runtime/private-package interface.  CP-2 must define what an internal adapter may provide, how it resolves private assets, and which public provenance fields remain required. |
| Add a named method within an existing stage | `COMPolicyConfig` and `COMRunConfig` name several policy choices; adapter profile expansion records raw/effective overrides. | Typed selection values and SiCoPR profile provenance are strong foundations. | The adapter whitelist contains exactly `project_standard`, `sicopr_reference_v1`, and `custom`; policy choices are fixed `Literal` sets and the core branches on them.  There is no method registry/protocol, owner declaration, capability metadata, or standard validation hook. |
| Add a stage or utility | `COM._run_once()` has named steps; path construction is isolated in `com_178a/path_stage.py`; individual utilities/types have local contracts. | Existing stage documents, typed config/status, and numerical regression anchors. | The pipeline order and root `COMStatus` shape are fixed in `COM._run_once()`; there is no stage interface, declared inputs/outputs, dependency graph, or extension registration.  Utility methods are selected by core-owned literals, not an independently versioned utility contract. |
| Add search behavior | `search/com_search_178A.py` owns manifest, grouping, partial execution, MSE ranking, finalization, and file artifacts. | File-backed lifecycle and candidate/run provenance are well defined for the current FFE/CTLE MSE search. | Candidate fields, candidate application, ranking metric, executor (`COM(...)._run_once`), and reporter are direct 178A dependencies.  A new search dimension, metric, or executor needs edits in this module rather than a declared search strategy contract. |
| Add report/output | `COMReportBase` supplies a read-only canonical stage flow; `COMReport178A` maps version status into it. | Reporting does not recompute model results; optional-stage handling and plot manifests are reusable. | The canonical stage list and version reporter are fixed.  A new artifact/exporter or new stage presentation has no plugin/extension contract, schema/version promise, or declared compatibility policy. |

## Cross-cutting findings

| Area | Observed fact | Consequence | CP-2 decision needed |
|---|---|---|---|
| Baseline isolation | 178A no longer depends on 93A concrete implementation; current SiCoPR profile records effective overrides. | A good baseline boundary exists. | Define exactly which public interfaces an extension may use and prohibit core/default mutation by an extension. |
| Selection lifecycle | `evolution_strategy.md` defines `experiment → named parallel method → optional default`, but implementation has no shared representation of a method's identity, owner, capabilities, or maturity. | The rule is documentary, not mechanically connected to the runtime. | Minimum method descriptor/registration and the evidence required at each promotion step. |
| Config/status compatibility | Config/status ownership and legal absence are well documented.  Exports are intended for traceability, not a stable reconstruction/checkpoint format. | A consumer cannot rely on a stated serialized schema or evolution rule. | What is stable at the extension boundary; schema identifiers, additive-field policy, absence/error behavior, and artifact reader responsibility. |
| Provenance | Config export and search artifacts record profiles, source fingerprints, revision, and result files for the current flow. | Current baseline is diagnosable. | Common provenance payload required of every extension and how baseline/candidate comparisons are linked. |
| Verification | Numerous stage and regression tests exist, but no common extension-conformance suite or representative extension fixtures were found. | New work can pass local tests while violating platform boundaries. | A minimum conformance matrix: baseline non-regression, contract validation, provenance, error behavior, and one scenario-specific test. |
| Private-company boundary | Architecture says private data/adapters/reports live in an internal fork; the public project has path/workbook assumptions under its repository. | The intended policy is clear but the handoff surface is not yet operationally specified. | Internal package layout, injected asset/config boundary, licensing/attribution rule, and what may be upstreamed. |

## What is *not* a CP-1 gap

- Historical C2M workbooks are not required current cases.
- 93A support is not a prerequisite unless a selected company use case needs it.
- Public packaging/release gates are separate from this platform-readiness plan.
- A generic plugin framework is not automatically required.  CP-2 must choose
  the smallest contract that supports the approved scenarios; explicit
  versioned registries may be safer than unrestricted dynamic plugins.

## CP-2 contract candidates

The following are decisions, not approved implementations:

1. **Case adapter contract:** public typed config plus source/provenance record;
   private data resolution stays in the internal package.
2. **Method contract:** stable identifier, owner/stage, typed input/output,
   declared invariants/failure behavior, maturity, and baseline comparison
   metadata.
3. **Stage contract:** required config/status inputs, produced status fragment,
   legal absence, ordering/dependency, and report/search visibility.
4. **Search/report contract:** candidate schema, evaluator/ranker boundary,
   artifact/provenance schema, and read-only output consumer interface.
5. **Compatibility contract:** supported serialized artifacts, versioning rule,
   deprecation behavior, and minimum extension conformance tests.

## Evidence examined

- `docs/architecture/evolution_strategy.md`
- `docs/architecture/configuration_architecture.md`
- `docs/architecture/reporting_architecture.md`
- `docs/models/178A/{call_tree,config_tree,status_tree}.md`
- `src/serdes_coding/io/com_excel_io_178A.py`
- `src/serdes_coding/models/com_178a/{config,status,path_stage}.py`
- `src/serdes_coding/models/com_model_178A.py`
- `src/serdes_coding/search/com_search_178A.py`
- `src/serdes_coding/reporting/{com_report_base,com_report_178A}.py`

No Python, workbook, reference-data, or result artifact was changed.  CP-1 did
not run numerical tests because it made no executable change.
