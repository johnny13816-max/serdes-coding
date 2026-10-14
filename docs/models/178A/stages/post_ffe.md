# 178A post-FFE impairment stage

> **Review state:** selected-phase response construction, status ownership, reporting-PSD separation, downstream COM inputs, and current automated checks are confirmed from source. Governing equations and reference-case accuracy have not been independently revalidated by this documentation change.

## Purpose and ownership

This stage takes the selected pre-DTE impairment and selected limited DTE result and constructs the post-FFE responses and statistics needed by later DFE COM and MLSD stages.

It owns:

- the run-level fixed sampled grid shared with pre-DTE;
- RX FFE response representation;
- equalized victim and aggressor responses;
- residual ISI after applying selected DFE feedback taps;
- post-FFE jitter sensitivity;
- Gaussian-noise sigma used by DFE COM;
- exact selected-phase ADC-input material used by final quantization PMF;
- component PSDs on the run-level grid used for reporting.

It does not change the selected DTE MSE and does not build the final interference/noise PMF or COM value.

## Entry and output

```text
calculate_post_ffe_imp(dte_status, imp_pre, victim_pulse, run_cfg)
    -> COMImpairmentStatus
```

`COM._run_once()` merges this result into the selected pre-DTE impairment. The returned `eq_ch` object contains both selected pre-DTE and new post-FFE responses so the merge does not intentionally discard the earlier response fields.

## Required inputs

| Input | Required fields/data | Role |
|---|---|---|
| `dte_status` | `w_lim`, `b_lim`, `d`, `pos` | selected RX FFE/DFE and cursor metadata |
| `imp_pre` | `sigma_X`, pre-DTE `S_rn`, `S_tn`, `h_dsamp`, `h_J`, `h_XTs_dsamp`, and selected equivalent responses | physical pre-DTE inputs |
| `h` | oversampled victim pulse | post-FFE jitter sensitivity from adjacent phases |
| `COMConfig.link` | run-level sampled grid and symbol timing | all pre/post-FFE responses and PSDs |
| `COMConfig.policy.rxffe_record_realization` | `linear_convolution`／`finite_record_circshift` | victim、XT 與 DDJ 的 FFE record-boundary method |
| `COMConfig.imp` | `R_LM`, `sigma_RJ`, `A_DD`, `N_qb`, `P_qc` | signal amplitude, jitter, and quantization controls |
| `COMConfig.L` | PAM order | signal amplitude and PMF input |
| `COMConfig.pmf` plus `run_cfg` | ADC-input PMF grid/retention policy | exact selected-phase ADC clipping material |

`w_lim` must be the full zero-filled vector with shape `(N_max,)`, as guaranteed by the DTE stage contract.

## Fixed-grid numerical domain

The stage uses the one run-level `cfg.link` sampled grid. `linear_convolution`
computes the full convolution and checks the excluded tail before returning to
that grid; its guard requires `max|tail|/max|full| <= 2e-3` and
`sum(tail²)/sum(full²) <= 1e-6`. `finite_record_circshift` applies every FFE tap
as a circular shift on the existing finite record, matching the reference
record convention and intentionally bypassing the linear-tail guard. Both
methods retain the same `LinkConfig` object.

```text
run-level grid
├── imp_pre responses and PSDs
├── w_lim_pre
├── S_G_pre
├── sigma_G after one FFE filtering operation
├── H_rxffe
├── h_w
├── h_XTs_w
├── h_ISI
├── h_w_J
└── post-FFE display PSD components
```

The post-FFE component PSDs are reporting quantities. Their construction
does not change DTE MSE or DFE COM.

## Ordered functional blocks

### 1. Validate and represent the selected FFE

- validate `w_lim` shape and finite values;
- retain the full vector for run-level-grid convolution/filter use;
- trim only trailing zero taps for the compact `H_rxffe` representation;
- construct `w_lim_pre` on the run-level link grid.

### 2. Build fixed-grid equivalent responses

```text
imp_pre.h_dsamp + w_lim -> selected _apply_rxffe_response method -> h_w on cfg.link
w_finite on cfg.link -> H_rxffe
for every imp_pre.h_XTs_dsamp
    apply the same selected record method -> h_XTs_w[k] on cfg.link
```

The victim and every aggressor retain the original `cfg.link` reference.

### 3. Build residual ISI

The current implementation copies `h_w`, removes the desired cursor at `d`, and applies the selected feedback coefficients to the following `N_b` samples. The result becomes `h_ISI`; its stored scalar summary is `sigma_ISI`.

The exact residual-ISI equation and sign convention remain subject to specification validation.

### 4. Build post-FFE jitter sensitivity

The stage calls `_calculate_h_J()` using the oversampled victim pulse, selected phase, run-level `LinkConfig`, and finite FFE taps. Its full result is checked before `h_w_J` is stored on the fixed grid.

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

This exact material is prepared regardless of the faster pre-DTE clipping method. Final DFE COM consumes its `delta` under the default `annex_d3` policy; the separate reference-only final policy reconstructs its own clipping amplitude in `calculate_COM_DFE()` without changing this stored selected-phase material.

### 7. Build reporting PSDs

Every component is represented on `cfg.link`:

- `S_rn` and `S_tn`: pre-DTE PSDs filtered directly by `H_rxffe`, with no regrid;
- `S_xn`: uncorrelated power sum rebuilt from every `h_XTs_w` path;
- `S_jn`: reporting jitter PSD from `h_w_J` and the configured DD/RJ terms;
- `S_qn`: white ADC quantization PSD based on stored `delta`, then filtered by `H_rxffe`; zero when quantization is disabled;
- `S_total`: sum of the five stored reporting components.

The stored component sigmas are obtained from their matching fixed-grid PSDs.

## Produced status

```text
COMImpairmentStatus
├── post_ffe: COMImpStageStatus
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
├── eq_ch: COMEqChannelStatus
│   ├── selected pre-DTE response fields
│   ├── h_w
│   ├── h_XTs_w
│   ├── h_ISI
│   └── h_w_J
└── H_rxffe
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
| fixed-grid `S_rn/S_xn/S_tn/S_jn/S_qn/S_total` | no for DFE COM | yes |
| component `sigma_rn/.../sigma_total` | no for DFE COM | yes |
| `sigma_ISI` | summary value; final ISI PMF uses `h_ISI` | yes |

The automated test explicitly checks that replacing every fixed-grid display PSD with zero does not change recomputed DFE COM.

## Execution-policy controls

The stage uses `pmf_grid_quality`, `pmf_keep_mass`, and optional direct `pmf_dy_override` from the supplied `run_cfg` while resolving the selected ADC-input PMF material. A set override bypasses the relative/absolute dy rules. `pre_dte_pmf_method` does not choose the post-FFE method: enabled post-FFE ADC-input material is always built through the exact path.

The stage does not read `cfg.execution.single_run` implicitly; the caller passes the active single-run, search-sweep, or search-final profile.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- `w_lim` is not finite or does not have shape `(N_max,)`;
- cursor `d` or the configured DFE feedback range exceeds `h_w`;
- a linear response tail exceeds the fixed-grid peak or energy limit;
- pre-DTE PSDs/responses required for the selected phase are absent;
- PSDs or responses do not share the run-level grid;
- ADC-input exact PMF construction fails or produces invalid clipping material;
- any derived response, PSD, or scalar fails its utility/dataclass validation.

The stage runs only after a valid phase/DTE candidate has been selected.

## Downstream consumers

| Consumer | Data read |
|---|---|
| DFE COM | `As`, `sigma_G`, `h_ISI`, `h_XTs_w`, `h_w_J`, exact ADC `delta`, and selected DTE coefficients |
| MLSD initialization | post-FFE `S_rn`, `h_ISI`, `sigma_X`, plus the later added-noise result |
| post-FFE reporting | fixed-grid PSDs, sigmas, equivalent responses, and ADC-input PMFs |
| final search CSV | `As`, `sigma_ISI`, and post-FFE component sigmas |

Reporting reads the stored fixed-grid objects and must not reconstruct this stage from config.

## Validation evidence and tolerance

`tests/test_com_model_178A_post_ffe.py` currently supplies one fixed-case integration test with five checks:

1. selected MSE matches the recorded fixed-case value to 14 decimal places;
2. every post-FFE PSD shares `h_w`'s `fb` and theta grid (`rtol=1e-12`, `atol=1e-15` for theta);
3. stored crosstalk PSD equals the power sum rebuilt from `h_XTs_w` (`rtol=1e-12`, `atol=1e-24`);
4. post-FFE quantization PSD RMS matches the final quantization PMF RMS (`rtol=5e-4`, `atol=1e-8`);
5. zeroing display PSDs leaves recomputed DFE COM unchanged to 12 decimal places.

This is implementation-regression evidence for one case. It is not independent specification validation, and it does not yet cover disabled quantization, several DFE lengths, several floating placements, or multiple link grids.

## Known limitations and unresolved questions

- The overflow guard is an engineering numerical policy; it must not be represented as a specification limit or universal COM-error bound.
- The post-FFE test depends on a case workbook and therefore is integration-level rather than a small isolated unit test.
- Residual-ISI indexing/sign, post-FFE jitter construction, Gaussian-source membership, and exact ADC-input construction still require independent comparison with the accepted 178A reference.
- The test method contains four test functions but the first function checks both the fixed MSE and post-grid contract; validation counts should be interpreted by assertions rather than function count.
