# 178A Stage 5 — Post-FFE model

> **Review state:** adaptive-grid integration is in progress; equations and broad reference-case accuracy remain subject to validation.

## Purpose and ownership

This stage takes the selected pre-DTE impairment and selected limited DTE result and constructs the post-FFE responses and statistics needed by later DFE COM and MLSD stages.

It owns:

- 每條 response 在其來源 grid 上的固定 circular RX FFE；
- consumption of the Stage 4 RX FFE response representation;
- equalized victim and aggressor responses;
- residual ISI after applying selected DFE feedback taps;
- post-FFE jitter sensitivity;
- Gaussian-noise sigma used by DFE COM;
- exact selected-phase ADC-input material used by final quantization PMF;
- reporting PSDs obtained by filtering the already-built pre-DTE PSDs on their existing record.

It does not change the selected DTE MSE and does not build the final interference/noise PMF or COM value.

## Entry and output

```text
calculate_post_ffe_imp(dte_status, eq_ch, imp_pre, victim_pulse)
    -> (COMPostFFEEqChannelStatus, COMImpairmentStatus)
```

`COM._run_once()` commits both Stage 5 outputs through `_assign_post_ffe()`.
The commit validates the selected phase and adds only `eq_ch.post_ffe` and
`imp.post_ffe`; it cannot replace selected pre-DTE or DTE data.

## Required inputs

| Input | Required fields/data | Role |
|---|---|---|
| `dte_status` | `w_lim`, `H_rxffe`, `b_lim`, `d`, `pos` | selected RX FFE/DFE and cursor metadata |
| `eq_ch` | matching `phase_index` plus pre-DTE `h_dsamp`, `h_J`, `h_XTs_dsamp` | selected equivalent-channel inputs |
| `imp_pre` | `sigma_X`, pre-DTE `S_rn`, `S_tn`, and selected impairment data | physical pre-DTE inputs |
| `h` | oversampled victim pulse | post-FFE jitter sensitivity from adjacent phases |
| response `cfg` | 每條 pre-DTE response 自帶的 grid | RX FFE 的輸入與輸出 grid |
| `COMConfig.imp` | `R_LM`, `sigma_RJ`, `A_DD`, `N_qb`, `P_qc` | signal amplitude, jitter, and quantization controls |
| `COMConfig.L` | PAM order | signal amplitude and PMF input |
| `COMConfig.pmf` plus `COMConfig.num` | ADC-input PMF grid/retention policy | exact selected-phase ADC clipping material |

`w_lim` must be the full zero-filled vector with shape `(N_max,)`, as guaranteed by the DTE stage contract.

## Response domain and pre-DTE PSD record

`_apply_rxffe_response()` executes fixed circular shift-sum on each input's
own `LinkConfig`. Victim, ISI and DDJ retain the victim grid; each XT retains
its input grid. There is no RX FFE realization selector and Stage 5 does not
read the Stage 1 grid mode.

Stage 5 does not resolve NUM-003. Reporting PSDs reuse
`imp.pre_dte.record_cfg`; that PSD record does not determine response grids.

```text
pre-FFE victim response cfg → h_w / h_ISI / h_w_J
pre-FFE each XT response cfg → h_XTs_w[*]
imp.pre_dte.record_cfg → filtered post-FFE reporting PSDs
```

The post-FFE component PSDs are reporting quantities. Their construction
does not change DTE MSE or DFE COM.

## Ordered functional blocks

### 1. Validate the selected FFE

- validate `w_lim` shape and finite values;
- retain the full vector for run-level-grid convolution/filter use;
- require the matching `dte_status.H_rxffe` constructed by Stage 4;
- construct `w_lim_pre` on the pre-DTE PSD record grid.

### 2. Build one resolved set of equivalent responses

```text
eq_ch.pre_dte.h_dsamp + w_lim -> _apply_rxffe_response -> h_w on input cfg
for every eq_ch.pre_dte.h_XTs_dsamp
    circular FFE -> h_XTs_w[k] on that input cfg
pre-FFE h_J + w_lim -> circular FFE -> h_w_J on victim cfg
```

Responses may use different grids. No downstream stage selects a realization.

### 3. Build residual ISI

The current implementation copies `h_w`, removes the desired cursor at `d`, and applies the selected feedback coefficients to the following `N_b` samples. The result becomes `h_ISI`; its stored scalar summary is `sigma_ISI`.

The exact residual-ISI equation and sign convention remain subject to specification validation.

### 4. Build post-FFE jitter sensitivity

The stage calls `_calculate_h_J()` only for the pre-FFE adjacent-phase derivative,
then passes that response through the same `_apply_rxffe_response()` owner used by
victim and XT. `_calculate_h_J()` does not select a grid mode.

This preserves the implementation's adjacent-phase construction through the selected FFE. Its equation and units still require independent reference validation.

### 5. Build Gaussian sigma for DFE COM

The current DFE-COM Gaussian branch:

- constructs the RJ-only jitter PSD on the pre-DTE grid;
- combines pre-DTE RX noise, TX noise, and RJ noise;
- filters that combined PSD once through the selected FFE;
- integrates the result to `sigma_G`.

Crosstalk, residual ISI, dual-Dirac jitter, and ADC quantization are represented separately in the later PMF flow and are not included in this `sigma_G` value.

### 6. Build exact selected-phase ADC-input material

When quantization is enabled, `_build_adc_input_pmf_exact()` uses the selected pre-DTE victim response, aggressor responses, dual-Dirac jitter response, Gaussian sigma before RX FFE, and quantization controls. It stores exact PMF intermediates and the resulting `V_qc`/`delta` in `post_ffe.adc_input`.

When `N_qb` or `P_qc` is absent, the ADC-input method is `disabled` and no `delta` is produced.

**延後確認 — 非零 interference noise `S_in`：** D3.2 的 final-quantization
Gaussian noise 定義包含 `S_in`；目前此處的 ADC-input Gaussian sigma 使用
`S_rn + S_tn + S_jn_RJ`。一般不使用 interference calibration 的情況
`S_in = 0`；非零 `S_in` 是否屬於本專案支援範圍及如何納入，留待需要時確認，
目前不新增支援，也不宣稱非零情況已對齊 D3.2。

This exact material is prepared regardless of the faster pre-DTE clipping method. Final DFE COM consumes its `delta` under the default `annex_d3` policy; the separate reference-only final policy reconstructs its own clipping amplitude in `calculate_COM_DFE()` without changing this stored selected-phase material.

### 7. Build reporting PSDs

Every component is represented on the existing pre-DTE `record_cfg`:

- `S_rn` and `S_tn`: pre-DTE PSDs filtered directly by `H_rxffe`, with no regrid;
- `S_xn`: pre-DTE crosstalk PSD filtered by the completed RX FFE;
- `S_jn`: reporting jitter PSD from `h_w_J` and the configured DD/RJ terms;
- `S_qn`: white ADC quantization PSD based on stored `delta`, then filtered by `H_rxffe`; zero when quantization is disabled;
- `S_total`: sum of the five stored reporting components.

The stored component sigmas are obtained from their matching PSDs. Stage 7 does
not consume these reporting PSDs; its own NUM-003 owner rebuilds MLSD inputs
from complete equivalent-channel responses.

## Produced status

```text
COMStatus Stage 5 additions
├── eq_ch.post_ffe: COMPostFFEEqChannelStatus
│   ├── h_w
│   ├── h_XTs_w
│   ├── h_ISI
│   └── h_w_J
└── imp.post_ffe: COMImpStageStatus
    ├── record_cfg
│   ├── psd: COMPSDStatus
│   │   ├── As
│   │   ├── S_rn / sigma_rn
│   │   ├── S_xn / sigma_xn
│   │   ├── S_tn / sigma_tn
│   │   ├── S_jn / sigma_jn
│   │   ├── S_qn / sigma_qn
│   │   ├── S_total / sigma_total
│   │   ├── sigma_G
│   │   └── sigma_ISI
│   └── adc_input: COMAdcInputPMF
```

`As` is created at this stage. `R_n` remains a pre-DTE DTE-solver input and is not recreated for post-FFE reporting.

## Calculation versus reporting boundary

| Quantity | Used by later COM/MLSD calculation | Reporting use |
|---|---:|---:|
| `h_ISI` | yes | yes |
| `h_XTs_w` | yes | yes |
| `h_w_J` | yes, for dual-Dirac PMF | yes |
| `sigma_G` | yes, Gaussian PMF | summary/proportion context |
| `post_ffe.adc_input.delta` | yes, final quantization PMF | yes |
| existing-record `S_rn/S_xn/S_tn/S_jn/S_qn/S_total` | no；DFE/MLSD calculations use their dedicated inputs | yes |
| component `sigma_rn/.../sigma_total` | no for DFE COM | yes |
| `sigma_ISI` | summary value; final ISI PMF uses `h_ISI` | yes |

The automated test explicitly checks that replacing every fixed-grid display PSD with zero does not change recomputed DFE COM.

## Execution-policy controls

The stage uses the supplied run's effective `adc_input_pmf_grid` and
`pmf_keep_mass` while resolving selected-phase ADC-input PMF material. It is the
second NUM-006 direct consumer: `_build_adc_input_pmf_exact()` injects the
resolved scalar for signal／XT／DDJ FIR-PMF construction, and L5
`Pmf1D.fir_filter()` owns truncation after each tap convolution. Its
`dy_override` bypasses that family's relative/absolute rule and cannot affect
the final-PMF family. Enabled pre-DTE and post-FFE ADC-input material are both
built through their fixed exact paths; neither stage exposes a PMF-method selector.

Stage 5 是 NUM-004 的第二個 consumer。它呼叫同一個 L4 owner
`_resolve_adc_input_pmf_config()`，為 selected-phase ADC-input material 解析
grid；owner 再使用 shared L5 `COMPMFGridControl.resolve_dy()`。Stage 5 不讀取
`final_pmf_grid`，L5 kernel 也不區分 ADC-input／final domain，因此不能取代
兩個 L4 domain owners。

The stage reads the already resolved `cfg.alg` and `cfg.num` owned by this
single simulator instance. Run-mode selection occurs in the workbook adapter
before `COM` construction; Stage 5 does not receive or interpret a profile.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- `w_lim` is not finite or does not have shape `(N_max,)`;
- cursor `d` or the configured DFE feedback range exceeds `h_w`;
- pre-DTE PSDs/responses required for the selected phase are absent;
- a response lacks a valid cfg, or PSD objects do not share `record_cfg`;
- ADC-input exact PMF construction fails or produces invalid clipping material;
- any derived response, PSD, or scalar fails its utility/dataclass validation.

The stage runs only after a valid phase/DTE candidate has been selected.

## Downstream consumers

| Consumer | Data read |
|---|---|
| DFE COM | `As`, `sigma_G`, `h_ISI`, `h_XTs_w`, `h_w_J`, exact ADC `delta`, and selected DTE coefficients |
| MLSD initialization | complete pre/post-FFE `eq_ch`, selected DTE, `sigma_X`, ADC delta, and added-noise scale；Stage 7 rebuilds its own PSDs |
| post-FFE reporting | resolved-grid PSDs, sigmas, equivalent responses, provenance, and ADC-input PMFs |
| final search CSV | `As`, `sigma_ISI`, and post-FFE component sigmas |

Reporting reads the stored fixed-grid objects and must not reconstruct this stage from config.

## Validation evidence and tolerance

`tests/test_com_model_178A_post_ffe.py` currently supplies one fixed-case integration test with five checks:

1. selected MSE is finite;
2. each response retains its input cfg and every post-FFE PSD reuses pre-DTE `record_cfg`;
3. stored crosstalk PSD equals the filtered pre-DTE crosstalk PSD;
4. stored quantization PSD equals the filtered pre-DTE quantization PSD;
5. zeroing display PSDs leaves recomputed DFE COM unchanged to 12 decimal places.

Focused tests cover the fixed circular operation, independent response grids,
and the invariant that Stage 5 never becomes a NUM-003 owner. Stage 7
NUM-003 behavior is tested independently. This is implementation-regression
evidence, not independent specification validation.

## Known limitations and unresolved questions

- The overflow guard is an engineering numerical policy; it must not be represented as a specification limit or universal COM-error bound.
- The post-FFE test depends on a case workbook and therefore is integration-level rather than a small isolated unit test.
- Residual-ISI indexing/sign, post-FFE jitter construction, Gaussian-source membership, and exact ADC-input construction still require independent comparison with the accepted 178A reference.
- The test method contains four test functions but the first function checks both the fixed MSE and post-grid contract; validation counts should be interpreted by assertions rather than function count.
