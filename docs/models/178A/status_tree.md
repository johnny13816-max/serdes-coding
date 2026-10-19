# 178A status tree

> **Status: authoritative status ownership and lifecycle reference.** This document records implemented dataclass structure, assignment/merge behavior, legal absence, and downstream consumers. Stage equations belong in the individual stage documents.

## Scope and sources

The maintained sources are:

- `src/serdes_coding/models/com_model_178A.py` for 178A status types and incremental assignment;
- `src/serdes_coding/models/com_model_93A.py` for the temporarily shared `COMPath`, `COMPMFStatus`, and text-formatting base;
- `src/serdes_coding/reporting/com_report_178A.py` for reporting consumers;
- `src/serdes_coding/search/com_search_178A.py` for search consumers.

## Root tree

```text
COMStatus                              standalone 178A root status
├── paths: list[COMPath]
│   ├── victim path
│   └── zero or more NEXT/FEXT paths
├── run: COMRunStatus | None
├── dte: COMDTEStatus | None
├── imp: COMImpairmentStatus | None
│   ├── pre_dte: COMImpStageStatus | None
│   │   ├── psd: COMPSDStatus | None
│   │   └── adc_input: COMAdcInputPMF | None
│   ├── post_ffe: COMImpStageStatus | None
│   │   ├── psd: COMPSDStatus | None
│   │   └── adc_input: COMAdcInputPMF | None
│   ├── eq_ch: COMEqChannelStatus | None
│   └── H_rxffe: SampledResponse | None
├── pmf: COMPMFStatus | None
└── mlsd: COMMLSDStatus | None
```

The 178A selected equalizer result is `status.dte`, and the 178A search metric is
`status.dte.mse`. The root status deliberately has no 93A `dfe` or `FOM` field.
`COMStatus` does not inherit the 93A root status; shared leaf types remain explicit
temporary dependencies until their neutral-owner migration is reviewed.

`status.final_COM` returns `status.mlsd.COM_MLSD` when present, otherwise `status.pmf.COM` when the DFE PMF stage has completed.

## Lifecycle by execution target

| Completion point | Guaranteed status | Legally absent |
|---|---|---|
| before path construction | empty `COMStatus` | every optional field; `paths` empty |
| paths completed | `paths` | `run`, `dte`, `imp`, `pmf`, `mlsd` |
| phase sweep initialized | `paths`, `run` | selected `dte`, selected `imp`, later stages |
| selected phase, `target="mse"` return | `paths`, `run`, `dte`, `imp.pre_dte`, `imp.eq_ch` pre-DTE fields | `imp.post_ffe`, `imp.H_rxffe`, `pmf`, `mlsd` |
| post-FFE completed | previous fields plus `imp.post_ffe`, shared `imp.eq_ch` post-FFE fields, `imp.H_rxffe` | `pmf`, `mlsd` until requested |
| DFE COM completed | previous fields plus `pmf` | `mlsd` |
| MLSD completed | previous fields plus `mlsd` | none of the requested MLSD result fields |

A failure does not roll the root status back. Fields assigned by completed stages remain available for diagnosis.

## Assignment and merge rules

| Helper | Behavior |
|---|---|
| `_assign_paths(paths)` | replaces `status.paths` |
| `_assign_run(run_status)` | replaces `status.run` |
| `_assign_dte(dte_status)` | assigns the selected result to `status.dte` |
| `_merge_imp(imp_status)` | field-wise merge of `pre_dte`, `post_ffe`, `eq_ch`, and `H_rxffe`; non-`None` incoming fields replace the same field |
| `_assign_pmf(pmf_status)` | replaces `status.pmf` |
| `_assign_mlsd(mlsd_status)` | replaces `status.mlsd` |

The phase-independent pre-DTE common calculation is a run-local cache. It is merged into the selected `pre_dte` result and is not stored as an additional root stage.

## Path status

`COMPath` 沿用 93A；178A `COMSharedPath` 擴充 93A shared fields，增加可選的
`ctle_iir` candidate object。

```text
COMPath
├── kind: victim | next | fext
├── shared: COMSharedPath
│   ├── H_ffe
│   ├── H_ffe_next
│   ├── H_t
│   ├── S_rx
│   ├── H_r
│   ├── H_ctf
│   └── ctle_iir: COMBilinearCTLE | None
├── S_tx
├── S_ch
├── S_all
├── H_21
├── H_all
├── X
└── pulse
```

Every path points to the same `COMSharedPath` object. In `bilinear_iir` mode,
`ctle_iir` directly owns both sections' `b/a` coefficients and `Fs`; the victim,
NEXT, FEXT, and TX-noise flow reuse this one object for the candidate. In
`continuous_tf` mode it is `None`. It is not duplicated on root `COMStatus`, and
there is no separate pulse-realization status wrapper. TX package, measured
channel, augmented S-parameter model, scalar responses, and pulse are
path-specific. Reporting reads these objects directly and must not rebuild them
from configuration.

## Run status

`COMRunStatus` records the execution policy actually used and the sampling-phase sweep trace.

| Field | Type/domain | Producer | Consumer |
|---|---|---|---|
| `pmf_grid_quality` | optional string | `_run_once()` from selected `COMRunConfig` | report annotation |
| `pmf_keep_mass` | optional probability | `_run_once()` from selected `COMRunConfig` | report annotation |
| `mse_by_pos` | list indexed by phase; `float V²` or `None` | phase evaluation loop | phase/MSE report |
| `main_cursor_error_by_pos` | list indexed by phase; message or `None` | phase evaluation loop | invalid-phase report |
| `coarse_pos` | phase indices | initial sweep | phase/MSE report |
| `fine_pos` | phase indices | optional fine sweep | phase/MSE report |

`None` in `mse_by_pos` means that phase did not produce a valid candidate or was not visited by the selected sweep policy. The corresponding error list distinguishes a recorded main-cursor rejection from an unvisited position.

## Selected DTE status

`COMDTEStatus` is the selected sampling-phase result. Candidate statuses for phases that were not selected are not retained at the root.

| Field | Domain/unit | Ownership |
|---|---|---|
| `ts` | index on the continuous-time sampled record | selected DTE metadata |
| `pos` | phase index in `[0, per_ui)` | selected DTE metadata |
| `d` | sampled-domain cursor/index metadata | selected DTE metadata |
| `w_lim` | dimensionless array, shape `(N_max,)` | limited, zero-filled FFE coefficients |
| `b_lim` | dimensionless array, shape `(N_b,)` | limited DFE coefficients |
| `mse` | V² | selected candidate metric |
| `pruned_index` | integer tap-index array | selected FFE placement diagnostic |
| `H_all`, `Rnn_all` | arrays on the full solver domain | solver diagnostic |
| `H`, `R_nn`, `H_b` | arrays on the selected solver domain | solver diagnostic |
| `w`, `b` | unlimited coefficient arrays | limiter/report diagnostic |

The compatibility property `dfe_coeff` returns `b_lim` for shared report code.

## Impairment status

### Stage ownership

`COMImpStageStatus` contains only `psd` and `adc_input`. Equivalent-channel responses are stored once in `COMImpairmentStatus.eq_ch`; they are not nested separately under each stage.

| Root field | Producer | Replacement behavior |
|---|---|---|
| `pre_dte` | selected output from `calculate_pre_dte_imp_at_pos()` | assigned after phase selection |
| `post_ffe` | `calculate_post_ffe_imp()` | added after DTE selection |
| `eq_ch` | pre-DTE candidate, then completed post-FFE result | later non-`None` object replaces the earlier object |
| `H_rxffe` | `calculate_post_ffe_imp()` | absent before post-FFE |

The post-FFE `eq_ch` object carries both the selected pre-DTE responses and the post-FFE responses, so replacing the earlier object does not intentionally discard the selected pre-DTE response fields.

### `COMPSDStatus`

```text
COMPSDStatus
├── signal/reference scalars
│   ├── As
│   └── sigma_X
├── component PSD and integrated scalar pairs
│   ├── S_rn / sigma_rn
│   ├── S_xn / sigma_xn
│   ├── S_tn / sigma_tn
│   ├── S_jn / sigma_jn
│   └── S_qn / sigma_qn
├── combined PSD
│   ├── S_total
│   ├── sigma_total
│   └── R_n
└── post-FFE summary scalars
    ├── sigma_G
    └── sigma_ISI
```

Every `S_*` field is a `SampledPSD` and therefore carries its own `theta`, `fb`, PSD samples, and the run-level `LinkConfig` reference when produced by COM. The matching scalar is stored rather than recomputed by reporting. Fields remain optional because the same dataclass represents partial pre-DTE common output, selected pre-DTE output, and post-FFE output.

### `COMEqChannelStatus`

| Phase | Fields | Type |
|---|---|---|
| selected pre-DTE | `h_dsamp`, `h_tn`, `h_J`, `h_XTs_dsamp` | `SampledResponse` or list thereof |
| post-FFE | `h_ISI`, `h_w_J`, `h_w`, `h_XTs_w` | `SampledResponse` or list thereof |

Each COM-produced response retains the run-level `LinkConfig` reference and owns its impulse/transfer representation. Reporting consumes these stored objects.

### `COMAdcInputPMF`

| Field | Type/role |
|---|---|
| `p_sig`, `p_s`, `p_XT`, `p_DD`, `p_ga`, `p_n`, `p_sn` | optional `Pmf1D` intermediates |
| `V_qc`, `delta` | optional voltage scalars |
| `method` | optional method/status label |

Which PMF components are present depends on stage, quantization enablement, and execution policy. Reporting must check each field rather than assume all components exist.

### Compatibility proxies

`COMImpairmentStatus` exposes compatibility properties such as `S_rn`, `sigma_rn`, `S_xn`, `sigma_xn`, `h_dsamp`, and `h_w`. PSD proxies search `post_ffe` before `pre_dte`; equivalent-response proxies read `eq_ch`. These properties are views over stored status and do not create new numerical data.

## DFE PMF status

`COMPMFStatus` is shared with 93A and assigned only after the 178A DFE COM stage completes.

| Field | Unit/type |
|---|---|
| `dy` | V, PMF grid step |
| `tap_abs_th` | V, PMF tap threshold |
| `p_ISI`, `p_G`, `p_DD`, `p_XT`, `p_qn`, `p_combined` | optional `Pmf1D` |
| `y0`, `A_ni` | optional V scalars |
| `COM` | optional dB scalar |

The stage returns a completed object, but individual PMF fields remain optional in the shared dataclass to support incremental/shared code paths.

## MLSD status

`COMMLSDNoiseStatus` is a transient result of `build_mlsd_noise()`: it owns
`S_isi`, `sigma_isi`, `S_ni`, `sigma_ni`, and `R_ni` until the top-level MLSD
flow assembles the final status. `calculate_der_mlsd()` reads only `p_an`
and `R_ni` and returns `DER_MLSD` plus `der_by_j`; it does not mutate a status.
The final `COMMLSDStatus` keeps the existing flat reporting fields:

```text
COMMLSDStatus
├── added_noise: COMAddedNoiseStatus
│   ├── g_an
│   ├── S_an
│   ├── sigma_an
│   ├── p_an
│   ├── delta_com_an_temp
│   ├── target_delta_com_an
│   ├── residual_dB
│   ├── iterations
│   ├── sigma_added
│   ├── A_ref
│   ├── A_an
│   └── iteration_history[]
│       └── COMAddedNoiseIterationStatus
├── S_isi / sigma_isi
├── S_ni / sigma_ni
├── R_ni
├── der_by_j
├── DER_MLSD
├── A_MLSD
├── delta_COM
├── COM_MLSD_raw
└── COM_MLSD
```

`COMAddedNoiseIterationStatus` records one baseline, bracket, or bisection observation with its iteration index and scalar diagnostics. The convergence report reads `iteration_history`; search CSV output does not expand this history.

`COMMLSDStatus` is absent when MLSD is not requested or enabled. Its required `added_noise` field identifies the calibration result; the top-level MLSD flow constructs and assigns this final status only after all three blocks and Eq. 178A-47 have completed. Optional field types remain for compatibility with reporting and serialization consumers.

## Reporting and search consumers

| Consumer | Required status boundary |
|---|---|
| path plots | `status.paths` |
| phase/MSE and DTE plots | `status.run` and `status.dte` |
| pre-DTE impairment plots | `status.imp.pre_dte`, plus stored `status.imp.eq_ch` responses when used |
| post-FFE impairment plots | `status.imp.post_ffe`, plus `status.imp.eq_ch` and `H_rxffe` when used |
| DFE PMF plots | `status.pmf` |
| MLSD plots | `status.mlsd` and completed `status.pmf` baseline |
| partial-search row | `status.dte.mse`, `ts`, and `pos` |
| final search export | the completed status produced by the configured final execution profile |

Reporting is a read-only consumer. Missing status causes a clear unavailable-stage error or omission from the summary; reporting must not recreate a missing model result from configuration.

## Search status boundary

`COMSearchStatus` and `COMSearchRow` live in `search/com_search_178A.py` and describe orchestration across candidates. They are not children of one candidate's `COMStatus` dataclass tree. `COMSearchStatus.best` points to the selected valid final `COMStatus`; `num_grid_overflow` counts final candidates excluded by the fixed-grid guard. The final CSV records their `grid_overflow` status, full/grid lengths, and tail ratios without assigning a COM value. Partial CSV rows retain scalar comparison data rather than duplicating every nested status object.
