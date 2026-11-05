# 178A Stage 5: post-FFE impairment

> **Review state:** selected-phase response construction, status ownership, reporting-PSD separation, downstream COM inputs, and current automated checks are confirmed from source. Governing equations and reference-case accuracy have not been independently revalidated by this documentation change.

## Purpose and ownership

This stage takes the selected pre-DTE impairment and selected limited DTE result and constructs the post-FFE responses and statistics needed by later DFE COM and MLSD stages.

It owns:

- ALG-011 的 post-FFE response record realization 與共同 response grid；
- consumption of the Stage 4 RX FFE response representation;
- equalized victim and aggressor responses;
- residual ISI after applying selected DFE feedback taps;
- post-FFE jitter sensitivity;
- Gaussian-noise sigma used by DFE COM;
- exact selected-phase ADC-input material used by final quantization PMF;
- component PSDs on the independently resolved NUM-003 record used for reporting and MLSD.

It does not change the selected DTE MSE and does not build the final interference/noise PMF or COM value.

## Entry and output

```text
calculate_post_ffe_imp(dte_status, eq_ch, imp_pre, victim_pulse, run_cfg)
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
| `COMConfig.link` | run-level sampled grid and symbol timing | pre-FFE input grid and fixed/circular output grid |
| `COMConfig.policy.rxffe_record_realization` | `linear_fixed_grid`／`linear_expanded_grid`／`finite_record_circshift` | victim、all XT 與 DDJ 的共同 FFE record realization |
| `COMConfig.policy.eq_ch_imp_len`／`num_trunc_ui` | `full`／`truncated` | independent NUM-003 PSD/correlation record length |
| `COMConfig.imp` | `R_LM`, `sigma_RJ`, `A_DD`, `N_qb`, `P_qc` | signal amplitude, jitter, and quantization controls |
| `COMConfig.L` | PAM order | signal amplitude and PMF input |
| `COMConfig.pmf` plus `run_cfg` | ADC-input PMF grid/retention policy | exact selected-phase ADC clipping material |

`w_lim` must be the full zero-filled vector with shape `(N_max,)`, as guaranteed by the DTE stage contract.

## ALG-011 response domain and NUM-003 PSD domain

`COM._resolve_post_ffe_response_cfg()` first resolves one response grid. All
victim、XT、DDJ and residual-ISI responses must share this exact `LinkConfig`:

- `linear_fixed_grid` computes linear convolution, checks the discarded tail,
  then returns to `cfg.link`. The guard requires
  `max|tail|/max|full| <= 2e-3` and `sum(tail²)/sum(full²) <= 1e-6`.
- `linear_expanded_grid` allocates one caller-owned grid large enough for
  `cfg.link.sampled_nfft + N_max - 1` samples and preserves the complete linear
  convolution without hidden regrid.
- `finite_record_circshift` applies every FFE tap as a circular shift on
  `cfg.link`, matching the SiCoPR finite-record convention and bypassing the
  linear-tail guard.

After ALG-011 resolves the response grid, NUM-003 independently resolves the
PSD/correlation record. `full` uses the ALG-011 response grid；`truncated` uses
the configured truncated record. This separation prevents a response-boundary
algorithm choice from silently becoming a PSD-cost control.

```text
pre-FFE cfg.link
├── imp_pre responses and PSDs
├── Stage 4 w_lim / H_rxffe
└── Stage 5 ALG-011 owner
    ├── response_cfg
    │   ├── h_w
    │   ├── h_XTs_w[*]
    │   ├── h_ISI
    │   └── h_w_J
    └── NUM-003 record_cfg
        ├── full -> response_cfg
        └── truncated -> configured truncated grid
            └── post-FFE PSDs and Stage 7 MLSD noise PSDs
```

The post-FFE component PSDs are reporting quantities. Their construction
does not change DTE MSE or DFE COM.

## Ordered functional blocks

### 1. Validate the selected FFE

- validate `w_lim` shape and finite values;
- retain the full vector for run-level-grid convolution/filter use;
- require the matching `dte_status.H_rxffe` constructed by Stage 4;
- construct `w_lim_pre` on the run-level link grid.

### 2. Build one resolved set of equivalent responses

```text
eq_ch.pre_dte.h_dsamp + w_lim -> _apply_rxffe_response -> h_w on response_cfg
for every eq_ch.pre_dte.h_XTs_dsamp
    apply the same selected record method -> h_XTs_w[k] on response_cfg
pre-FFE h_J + w_lim -> same owner/method -> h_w_J on response_cfg
```

The victim、every aggressor、DDJ and residual ISI share `response_cfg`. No
downstream stage selects the realization again.

### 3. Build residual ISI

The current implementation copies `h_w`, removes the desired cursor at `d`, and applies the selected feedback coefficients to the following `N_b` samples. The result becomes `h_ISI`; its stored scalar summary is `sigma_ISI`.

The exact residual-ISI equation and sign convention remain subject to specification validation.

### 4. Build post-FFE jitter sensitivity

The stage calls `_calculate_h_J()` only for the pre-FFE adjacent-phase derivative,
then passes that response through the same `_apply_rxffe_response()` owner used by
victim and XT. `_calculate_h_J()` does not own an ALG-011 selector.

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

### 7. Build reporting／MLSD-consumed PSDs

Every component is represented on resolved `record_cfg`:

- `S_rn` and `S_tn`: pre-DTE PSDs filtered directly by `H_rxffe`, with no regrid;
- `S_xn`: uncorrelated power sum rebuilt from every `h_XTs_w` path;
- `S_jn`: reporting jitter PSD from `h_w_J` and the configured DD/RJ terms;
- `S_qn`: white ADC quantization PSD based on stored `delta`, then filtered by `H_rxffe`; zero when quantization is disabled;
- `S_total`: sum of the five stored reporting components.

The stored component sigmas are obtained from their matching PSDs. Stage 7 MLSD
consumes this same record grid and does not introduce another selector.

## Produced status

```text
COMStatus Stage 5 additions
├── eq_ch.post_ffe: COMPostFFEEqChannelStatus
│   ├── record_realization
│   ├── response_cfg
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
| resolved-grid `S_rn/S_xn/S_tn/S_jn/S_qn/S_total` | MLSD consumes the resolved post record；DFE COM uses PMF quantities | yes |
| component `sigma_rn/.../sigma_total` | no for DFE COM | yes |
| `sigma_ISI` | summary value; final ISI PMF uses `h_ISI` | yes |

The automated test explicitly checks that replacing every fixed-grid display PSD with zero does not change recomputed DFE COM.

## Execution-policy controls

The stage uses the supplied run's effective `adc_input_pmf_grid` and
`pmf_keep_mass` while resolving selected-phase ADC-input PMF material. Its
`dy_override` bypasses that family's relative/absolute rule and cannot affect
the final-PMF family. `pre_dte_pmf_method` does not choose the post-FFE method:
enabled post-FFE ADC-input material is always built through the exact path.

The stage does not read `cfg.execution.single_run` implicitly; the caller passes the active single-run, search-sweep, or search-final profile.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- `w_lim` is not finite or does not have shape `(N_max,)`;
- cursor `d` or the configured DFE feedback range exceeds `h_w`;
- a `linear_fixed_grid` response tail exceeds the fixed-grid peak or energy limit;
- `linear_expanded_grid` cannot cover the complete response or a consumer changes the resolved grid;
- pre-DTE PSDs/responses required for the selected phase are absent;
- response objects do not share `response_cfg`, or PSD objects do not share `record_cfg`;
- ADC-input exact PMF construction fails or produces invalid clipping material;
- any derived response, PSD, or scalar fails its utility/dataclass validation.

The stage runs only after a valid phase/DTE candidate has been selected.

## Downstream consumers

| Consumer | Data read |
|---|---|
| DFE COM | `As`, `sigma_G`, `h_ISI`, `h_XTs_w`, `h_w_J`, exact ADC `delta`, and selected DTE coefficients |
| MLSD initialization | post-FFE `record_cfg`, `S_rn`, `h_ISI`, `sigma_X`, plus later added noise |
| post-FFE reporting | resolved-grid PSDs, sigmas, equivalent responses, provenance, and ADC-input PMFs |
| final search CSV | `As`, `sigma_ISI`, and post-FFE component sigmas |

Reporting reads the stored fixed-grid objects and must not reconstruct this stage from config.

## Validation evidence and tolerance

`tests/test_com_model_178A_post_ffe.py` currently supplies one fixed-case integration test with five checks:

1. selected MSE matches the recorded fixed-case value to 14 decimal places;
2. every response shares `response_cfg` and every post-FFE PSD shares `record_cfg`;
3. stored crosstalk PSD equals the power sum rebuilt from `h_XTs_w` (`rtol=1e-12`, `atol=1e-24`);
4. post-FFE quantization PSD RMS matches the final quantization PMF RMS (`rtol=5e-4`, `atol=1e-8`);
5. zeroing display PSDs leaves recomputed DFE COM unchanged to 12 decimal places.

Additional focused tests cover all three owner methods, the expanded common
response grid, full/truncated NUM-003 interaction, and Stage 7 consumption of
the resolved record. This is implementation-regression evidence, not independent
specification validation.

## Known limitations and unresolved questions

- The overflow guard is an engineering numerical policy; it must not be represented as a specification limit or universal COM-error bound.
- The post-FFE test depends on a case workbook and therefore is integration-level rather than a small isolated unit test.
- Residual-ISI indexing/sign, post-FFE jitter construction, Gaussian-source membership, and exact ADC-input construction still require independent comparison with the accepted 178A reference.
- The test method contains four test functions but the first function checks both the fixed MSE and post-grid contract; validation counts should be interpreted by assertions rather than function count.
