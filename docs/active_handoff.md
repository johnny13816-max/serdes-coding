# Active Engineering Handoff

Date: 2026-09-09

## Current objective

The near-term deliverable is not a generally feature-complete COM platform. It is
a defensible IEEE 802.3 Annex 178A **spec-defined execution path** for an
externally supplied channel/config case:

1. retain the original channel/config source and metadata;
2. map every consumed field into the project workbook with units and derived
   rules documented;
3. run a reproducible calculation; and
4. compare stage-by-stage evidence and final COM with an external result.

Allowed public wording after validation is limited to: "Annex 178A
spec-defined execution path, validated against named external reference cases."
Do not claim official IEEE compliance, official-tool equivalence, or silicon
correlation without separate evidence.

## Worktree and safety boundary

- Active worktree:
  `C:\Users\johnn\OneDrive\文件\Serdes-learn\serdes-coding\tmp\.codex-merge-main`
- Active branch: `feature/mlsd-added-noise`
- The primary `serdes-coding` checkout is user-owned and dirty. Do not edit,
  reset, clean, or treat it as the active checkout.
- Current untracked path:
  `cases/c2m_8023dj_4p13p0_50mm/report/`
  It is runtime/report output. Do not add, delete, or alter it as part of code
  changes.
- Do not push or merge this branch until the user explicitly asks.
- The active worktree does not contain `serdes-coding/.venv`. Before any Python
  run, follow the repository `AGENTS.md` Python Environment Contract: verify the
  intended project-managed interpreter and dependency versions; do not silently
  substitute system Python.

## Recent local commits

```text
4e66857 Add MLSD workbook configuration schema
ae5cb98 Complete MLSD single-run COM stage
b890a0a Calculate truncated MLSD DER terms
e1cb215 Add PMF CDF evaluation
c9b3e5a Initialize MLSD analysis status
da07e13 Solve MLSD added-noise scale factor
280990f Record MLSD target resolution gate
6aa7a85 Add MLSD added-noise evaluator
```

These commits are local to this branch; they are not yet pushed.

## MLSD implementation status

Implemented in `src/serdes_coding/models/com_model_178A.py`:

- `COMMLSDConfig(enable, trunc_len, delta_com_an, minimum_com_limit)`.
- `evaluate_delta_com_an(...)`: constructs `S_an`, `sigma_an`, `p_an`, and the
  temporary delta-COM result.
- `solve_g_an(...)`: brackets and bisects `g_an`. A missing explicit
  `delta_com_an` and missing `minimum_com_limit` is a configuration error; no
  arbitrary target may be invented.
- `initialize_mlsd_status(...)`: builds `S_ni` and `R_ni` after `p_an` is
  available.
- `Pmf1D.cdf_at(...)` and `calculate_der_mlsd(...)`: calculate the truncated
  Eq. (178A-48) result and retain `der_by_j` for convergence plots.
- `COM.calculate_COM_MLSD()`: preserves `COM_DFE`, computes the raw MLSD result,
  and reports `max(COM_DFE, COM_MLSD_raw)` according to Eq. (178A-47).

Workbook parser support exists in `src/serdes_coding/io/com_excel_io.py`.
`cases/c2m_8023dj_4p13p0_50mm/config/config_178A.xlsx` now contains:

```text
mlsd_enable          False
mlsd_trunc_len       blank
delta_com_an         blank
minimum_com_limit    blank
```

This deliberately preserves DFE-only behavior. The `0.075 dB` value used in a
transient solver test is not a spec target and must not be written into a
project profile.

Validated locally before this handoff:

- source compilation succeeded;
- disabled MLSD parses as `enable=False`, `trunc_len=0`, and no target;
- a temporary single-run MLSD input with `trunc_len=4` and test-only
  `delta_com_an=0.075 dB` converged and produced a finite `DER_MLSD`;
- the `COM_MLSD_raw < COM_DFE` floor behavior was explicitly exercised.

Not complete:

- no traceable external MLSD-enabled profile exists yet;
- MLSD is not integrated into full-search candidate ranking, standardized
  reporting, or external reference validation;
- therefore MLSD must not be part of the first external conformance claim
  unless the selected source profile explicitly enables it.

## C01 external validation plan

Use one external case as `C01` before adding more channel types. A current C2M
50 mm case is only eligible if the source config, S-parameter files, package
profile, and reported external 8-9 dB COM result are demonstrably the same
case.

For C01, create an intake bundle containing:

1. original ad hoc workbook and exact source/version identity;
2. all victim/NEXT/FEXT files, port order, termination assumptions, and hashes;
3. external tool/result metadata and the expected final COM;
4. field-by-field mapping into project `config_178A.xlsx`, including units and
   every project-only numerical control;
5. stage evidence for `H_21`, package/path transfer, `H_ctf`, pulse response,
   `ts/pos`, DTE coefficients/MSE, `A_s`, impairment sigmas, PMF quantile,
   DER, and final COM.

Comparison rules, tolerances, and the exact expected output must be derived
from the named external reference, not chosen ad hoc. A failed final-COM match
must be diagnosed from the earliest mismatching stage.

## Read first

1. repository-root `AGENTS.md`
2. `docs/project_contracts.md`
3. `docs/future_ideas.md`
4. `docs/case_input_contract.md`
5. `docs/reference_cases.md`
6. this file

## Next task

Do not begin broad platform refactoring. First audit the candidate C2M source
files and determine whether the external 8-9 dB result is an exact C01 pairing.
Report the source identity, configuration deltas, and missing evidence before
editing the mapping or running a comparison.
