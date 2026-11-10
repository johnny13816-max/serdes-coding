# ALG-001 missing-DC completion contract

Historical / non-authoritative closure evidence. Current behavior is owned by
[`branch_behavior_registry.md`](../models/178A/branch_behavior_registry.md),
[`path_construction.md`](../models/178A/stages/path_construction.md), and
[`sparameter_model_contract.md`](../architecture/sparameter_model_contract.md).

Status: Closed 2026-11-05
Classification: `algorithm_policy`
Control: `alg.missing_dc_policy`

CFG-178A-D later moved this already-closed selector from the mixed channel
object to the canonical ALG domain; its values, numerical owner, and effective
profile behavior did not change.

## Goal and boundary

ALG-001 在 terminated `H21` 進入 analysis-grid resampling 或 pulse realization
前，只做一次 missing-DC completion。`continuous_tf` 與 `bilinear_iir` 共用
同一份 `completed_freqs`／`completed_H21`。高頻 `out_of_measured`、channel
renormalization、CTLE realization、3Tr 與 downstream filters 不屬於本契約。

```text
S_all
└─ terminated H21 + ALG-001 completion
   └─ completed_freqs + completed_H21
      ├─ LinkSegment analysis-grid path
      └─ bilinear-IIR measured-grid path
```

## Approved methods

| Value | Completion domain | Behavior |
|---|---|---|
| `error` | none | Missing DC raises an error. |
| `hold` | scalar H21 | Prepend `H21(0)=H21(f_min)`. |
| `skrf` | S-matrix | Extrapolate the S-matrix to DC, then calculate terminated H21. |
| `mag_phase_trend_to_dc` | scalar H21 | Magnitude uses the first ten samples' linear trend; phase uses the low-frequency group-delay trend corresponding to pinned SiCoPR `interp_Sparam`. |

Reference evidence: SiCoPR revision
`f58a1e913c6b74b1b069d6c3759acd8992b7aede`,
`com_functions/fn/interp_Sparam/py_impl.py` blob
`502a80496e161a1733e78dd8374b7948a73d1e1f`.

Project workbook default remains `skrf`. The `sicopr_reference_v1` profile selects
`mag_phase_trend_to_dc` and records raw/effective provenance.

## Implementation boundary

- `SparamModel.completed_voltage_transfer_function()` owns completion semantics.
- `_build_path()` calls the owner once and stores the completed measured transfer in
  `COMPath` for all downstream consumers.
- `_evaluate_pre_ctle_on_measured_grid()` accepts only completed scalar H21; it does
  not recompute termination from `S_all`.
- `_reference_fd_to_td_record()` requires a DC sample and has no missing-DC fallback.
- 93A configuration and numerical flow are unchanged. 178A single and search runs
  share the same path construction and therefore the same policy.

## Validation

- Focused semantics/config/path-realization tests, including all four methods:
  `59 passed`.
- Fixed SiCoPR production golden: `1 passed`.
- Python 3.7 standalone utility export: synchronized; validator passed.
- Fixed acceptance values:
  - `COM_DFE = 1.5247607834259893 dB`
  - final `COM = 2.895898684873246 dB`
- Boundary and rollback commit: `7c256b239ae633afe918f0a9cb1eedc989e0824e`;
  pushed to `origin/main`.

