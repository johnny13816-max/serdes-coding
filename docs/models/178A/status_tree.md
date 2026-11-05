# 178A status tree

> **Status: authoritative status ownership and lifecycle reference.** This document records implemented dataclass structure, assignment/merge behavior, legal absence, and downstream consumers. Stage equations belong in the individual stage documents.

## Scope and sources

The maintained sources are:

- `src/serdes_coding/models/com_178a/status.py` for version-owned 178A path and calculation-state contracts;
- `src/serdes_coding/models/com_model_178A.py` for incremental assignment and the compatibility exports;
- `src/serdes_coding/models/com_dataclass_text.py` for text-formatting mechanics;
- `src/serdes_coding/reporting/com_report_178A.py` for reporting consumers;
- `src/serdes_coding/search/com_search_178A.py` for search consumers.

## Root tree

```text
COMStatus                              standalone 178A root status
├── paths: list[COMPath]
│   ├── victim path
│   └── zero or more NEXT/FEXT paths
├── run: COMRunStatus | None
├── eq_ch: COMEqChannelStatus | None
│   ├── phase_index
│   ├── pre_dte: COMPreDTEEqChannelStatus
│   └── post_ffe: COMPostFFEEqChannelStatus | None
├── dte: COMDTEStatus | None
│   └── H_rxffe: SampledResponse | None
├── imp: COMImpairmentStatus | None
│   ├── pre_dte: COMImpStageStatus | None
│   │   ├── psd: COMPSDStatus | None
│   │   └── adc_input: COMAdcInputPMF | None
│   └── post_ffe: COMImpStageStatus | None
│       ├── psd: COMPSDStatus | None
│       └── adc_input: COMAdcInputPMF | None
├── pmf: COMPMFStatus | None
└── mlsd: COMMLSDStatus | None
```

The 178A selected equalizer result is `status.dte`, and the 178A search metric is
`status.dte.mse`. The root status deliberately has no 93A `dfe` or `FOM` field.
`COMStatus`, `COMPath`, `COMSharedPath`, and `COMPMFStatus` are standalone
178A-owned types and do not inherit or alias their 93A counterparts.

Every 178A-owned status dataclass defines its own semantic sections, field
labels, units, conversions, and bounded summaries. `to_string()` and `print()`
use those definitions; `repr()` remains one line. This presentation contract
does not change status lifecycle or numerical content. See
[COM dataclass 文字介面契約](../../architecture/dataclass_text_contract.md).

`status.final_COM` returns `status.mlsd.COM_MLSD` when present, otherwise `status.pmf.COM` when the DFE PMF stage has completed.

## Lifecycle by execution target

| Completion point | Guaranteed status | Legally absent |
|---|---|---|
| before path construction | empty `COMStatus` | every optional field; `paths` empty |
| paths completed | `paths` | `run`, `dte`, `imp`, `pmf`, `mlsd` |
| phase sweep initialized | `paths`, `run` | selected `dte`, selected `imp`, later stages |
| selected phase, `target="mse"` return | `paths`, `run`, `eq_ch.phase_index`, `eq_ch.pre_dte`, `dte` including `H_rxffe`, `imp.pre_dte` | `eq_ch.post_ffe`, `imp.post_ffe`, `pmf`, `mlsd` |
| post-FFE completed | previous fields plus `eq_ch.post_ffe` and `imp.post_ffe` for the same selected phase | `pmf`, `mlsd` until requested |
| DFE COM completed | previous fields plus `pmf` | `mlsd` |
| MLSD completed | previous fields plus `mlsd` | none of the requested MLSD result fields |

A failure does not roll the root status back. Fields assigned by completed stages remain available for diagnosis.

## Assignment and merge rules

| Helper | Behavior |
|---|---|
| `_assign_paths(paths)` | replaces `status.paths` |
| `_assign_run(run_status)` | replaces `status.run` |
| `_assign_selected_phase(eq_ch, imp, dte)` | validates one phase identity and atomically publishes the selected pre-DTE equivalent channel, impairment, and completed DTE |
| `_assign_post_ffe(phase_index, eq_ch_post, imp_post)` | validates selected phase identity and atomically adds both Stage 5 outputs without replacing pre-DTE or DTE data |
| `_assign_pmf(pmf_status)` | replaces `status.pmf` |
| `_assign_mlsd(mlsd_status)` | replaces `status.mlsd` |

The phase-independent pre-DTE common calculation is a run-local cache. It is merged into the selected `pre_dte` result and is not stored as an additional root stage.

## Path status

`COMPath` 與 `COMSharedPath` 均由 178A 擁有。`COMSharedPath` 保存共用 filter、
RX package 與可選的 `ctle_iir` candidate object。

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
| `pmf_grid_quality` | optional legacy/effective annotation | `_run_once()` from selected `COMRunConfig` | compatibility report annotation；canonical grid evidence is the resolved ADC-input/final PMF runtime config |
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
| `H_rxffe` | dimensionless `SampledResponse` | Stage 4 representation of the selected `w_lim` on the noise grid |

The compatibility property `dfe_coeff` returns `b_lim` for shared report code.

## Impairment status

### Stage ownership

`COMImpStageStatus` contains only `psd` and `adc_input`. Equivalent-channel responses are owned by root `COMStatus.eq_ch`; RX FFE ownership belongs to `COMDTEStatus`.

| Root field | Producer | Replacement behavior |
|---|---|---|
| `pre_dte` | selected output from `calculate_pre_dte_imp_at_pos()` | assigned after phase selection |
| `post_ffe` | `calculate_post_ffe_imp()` | added after DTE selection |
| `status.eq_ch` | selected Stage 3 candidate | pre-DTE fields are preserved; Stage 5 adds only `post_ffe` |
| `status.dte.H_rxffe` | Stage 4 | completed before candidate selection/commit |

Stage 3/4 selection retains only the current minimum-MSE candidate's complete
`eq_ch`／`imp`／`dte` bundle. Other phases retain only `COMRunStatus` summaries.
The selected bundle is committed once, so mixed-phase root status is illegal.

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

| Object | Fields | Type |
|---|---|---|
| `COMEqChannelStatus` | `phase_index`, `pre_dte`, optional `post_ffe` | selected-phase lifecycle |
| `COMPreDTEEqChannelStatus` | `h_dsamp`, `h_tn`, `h_J`, `h_XTs_dsamp` | `SampledResponse` or list thereof |
| `COMPostFFEEqChannelStatus` | `h_ISI`, `h_w_J`, `h_w`, `h_XTs_w` | `SampledResponse` or list thereof |

Each COM-produced response retains the run-level `LinkConfig` reference and owns its impulse/transfer representation. Reporting consumes these stored objects.

### `COMAdcInputPMF`

| Field | Type/role |
|---|---|
| `p_sig`, `p_s`, `p_XT`, `p_DD`, `p_ga`, `p_n`, `p_sn` | optional `Pmf1D` intermediates |
| `V_qc`, `delta` | optional voltage scalars |
| `method` | optional method/status label |

Which PMF components are present depends on stage, quantization enablement, and execution policy. Reporting must check each field rather than assume all components exist.

### Compatibility proxies

`COMImpairmentStatus` exposes PSD/scalar compatibility properties such as
`S_rn`, `sigma_rn`, `S_xn`, and `sigma_xn`; they search `post_ffe` before
`pre_dte`. Equivalent responses are intentionally not proxied through
impairment. `COMEqChannelStatus` provides flat read-only response properties
over its `pre_dte` and `post_ffe` children for calculation/report compatibility.

## DFE PMF status

`COMPMFStatus` is owned by 178A and assigned only after the 178A DFE COM stage completes.

| Field | Unit/type |
|---|---|
| `dy` | V, PMF grid step |
| `tap_abs_th` | V, PMF tap threshold |
| `final_vqc_convention` | selected B-007 policy value |
| `final_V_qc`, `final_delta` | optional V scalars actually used by final COM |
| `p_ISI`, `p_G`, `p_DD`, `p_XT`, `p_qn`, `p_combined` | optional `Pmf1D` |
| `y0`, `A_ni` | optional V scalars |
| `COM` | optional dB scalar |

The three final-clipping fields provide observability only; they do not feed
back into the calculation. The stage returns a completed object, but individual PMF fields remain optional
in the 178A dataclass to support incremental stage construction and reporting.

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
| pre-DTE impairment plots | `status.imp.pre_dte` plus `status.eq_ch.pre_dte` |
| post-FFE impairment plots | `status.imp.post_ffe`, `status.eq_ch.post_ffe`, and `status.dte.H_rxffe` when used |
| DFE PMF plots | `status.pmf` |
| MLSD plots | `status.mlsd` and completed `status.pmf` baseline |
| partial-search row | `status.dte.mse`, `ts`, and `pos` |
| final search export | the completed status produced by the configured final execution profile |

Reporting is a read-only consumer. Missing status causes a clear unavailable-stage error or omission from the summary; reporting must not recreate a missing model result from configuration.

## Search status boundary

`COMSearchStatus` and `COMSearchRow` live in `search/com_search_178A.py` and describe orchestration across candidates. They are not children of one candidate's `COMStatus` dataclass tree. `COMSearchStatus.best` points to the selected valid final `COMStatus`; `num_grid_overflow` counts final candidates excluded by the fixed-grid guard. The final CSV records their `grid_overflow` status, full/grid lengths, and tail ratios without assigning a COM value. Partial CSV rows retain scalar comparison data rather than duplicating every nested status object.
