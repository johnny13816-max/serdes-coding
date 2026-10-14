# 178A pre-DTE impairment stage

> **Review state:** the two-part stage boundary, cache lifecycle, runtime-policy inputs, produced status fields, and current component data flow are confirmed from source. Specification equations and numerical equivalence have not been independently revalidated by this documentation change.

## Purpose and ownership

This stage prepares the sampled impairment data required to evaluate each receiver sampling phase before the discrete-time equalizer is solved.

It is split into:

1. a phase-independent common calculation performed once per concrete path/filter candidate;
2. a phase-dependent calculation performed for every sampling phase selected by the execution policy.

It owns pre-DTE receiver noise, crosstalk, TX noise, jitter noise, optional ADC quantization noise, the combined sampled PSD/autocorrelation, and the sampled equivalent responses used by the DTE solver.

It does not select the best phase, solve DTE coefficients, construct post-FFE responses, or calculate final COM.

## Governing references

Current source identifies these Annex 178A references:

| Implemented component | Reference named by current source | Validation state |
|---|---|---|
| receiver input noise | Eq. 178A-17 | implementation reference recorded; equation not revalidated here |
| crosstalk PSD and per-aggressor sampling phase | Eq. 178A-18 | implementation reference recorded; equation not revalidated here |
| transmitter output noise | Eq. 178A-19 and Eq. 178A-20 | implementation reference recorded; equation not revalidated here |
| sampled jitter sensitivity and jitter PSD | Eq. 178A-21 and Eq. 178A-22 | implementation reference recorded; equation not revalidated here |
| ADC quantization-noise path | Annex 178A.1.7.6, including Eq. 178A-26 through Eq. 178A-28 | implementation reference recorded; equation not revalidated here |

This document records what the current program does and where each result is stored. It does not certify those formulas against the specification.

## Stage entries

```text
calculate_pre_dte_imp_common(victim, h_XTs)
    -> (common_psd: COMPSDStatus, h_XTs_dsamp: list[np.ndarray])

calculate_pre_dte_imp_at_pos(victim, pos, common_psd, h_XTs_dsamp, run_cfg)
    -> COMImpairmentStatus
```

`calculate_pos_candidate()` is the orchestration wrapper that calls `calculate_pre_dte_imp_at_pos()` and then passes its output to `calculate_MMSE_DTE()`.

## Cache and status lifecycle

```text
once per concrete candidate
└── calculate_pre_dte_imp_common(...)
    ├── common_psd
    └── h_XTs_dsamp

for every requested victim pos
└── calculate_pre_dte_imp_at_pos(...)
    └── candidate COMImpairmentStatus

phase selection
└── only the selected candidate is merged into status.imp.pre_dte / status.imp.eq_ch
```

The common return values are run-local cache objects. They are not a separate `COMStatus` stage. Each phase candidate receives them explicitly. Unselected phase impairment objects are not retained at the root status.

## Required inputs

### Common calculation

| Input | Required data | Use |
|---|---|---|
| `COMConfig.link` | sampled grid, `fb`, `theta`, and `per_ui` | sampled PSD/response construction |
| `COMConfig.policy noise-grid 欄位` | `analysis_grid` or fixed even `num_ui` | common MMSE noise PSD/correlation record |
| `COMConfig.filter` | receiver noise-filter and CTF controls | receiver-noise filtering |
| `COMConfig.imp` | `eta_0` | receiver-noise PSD |
| `COMConfig.L` | PAM order | normalized symbol standard deviation |
| `h_XTs` | one-dimensional aggressor pulse arrays | per-aggressor sampling and crosstalk PSD |

The `victim` argument is accepted by the current public method but is not read inside the common calculation.

### Per-phase calculation

| Input | Required data | Use |
|---|---|---|
| `victim` | `pulse.ir`, `H_t`, `H_21`, `H_r`, `H_ctf`, optional shared `ctle_iir` | victim samples, TX-noise path, and jitter response; TX noise reuses the candidate's selected CTLE pulse realization |
| `pos` | integer in `[0, per_ui)` | victim phase selection |
| `common` | `sigma_X`, `S_rn`, `S_xn`, and their integrated values | reused phase-independent components |
| `h_XTs_dsamp` | one-dimensional sampled response for each aggressor | selected candidate equivalent-channel status |
| `COMConfig.imp` | `SNR_TX`, `sigma_RJ`, `A_DD`, `N_qb`, `P_qc`, `R_LM` | phase-specific impairment and optional quantization controls |
| `COMConfig.pmf` | base PMF grid controls | ADC-input PMF construction |
| `run_cfg` | `pre_dte_pmf_method`, `pmf_grid_quality`, `pmf_keep_mass`, optional `pmf_dy_override` | execution-policy accuracy/cost selection |

The exact workbook mappings are defined in [Configuration tree](../config_tree.md).

## Common functional blocks

```text
calculate_pre_dte_imp_common(...)
├── derive sigma_X from the configured PAM order
├── _build_psd_rx_noise(...)
│   ├── construct continuous receiver-noise PSD
│   ├── filter through receiver-noise and CTF responses
│   └── convert onto the sampled theta grid
├── _build_psd_xtalk(...)
│   └── for each aggressor
│       ├── apply the explicit fixed-UI record when selected
│       ├── choose its own implemented worst-energy sampling phase
│       ├── build its sampled-response PSD
│       └── add it to the uncorrelated crosstalk PSD sum
└── return common COMPSDStatus plus sampled aggressor arrays
```

The aggressor phase selection is independent of the victim `pos` loop in the current implementation.

The common `COMPSDStatus` populates:

- `sigma_X`;
- `S_rn`, `sigma_rn`;
- `S_xn`, `sigma_xn`.

All other fields remain absent until the per-phase calculation.

## Per-phase functional blocks

```text
calculate_pre_dte_imp_at_pos(...)
├── validate pos and common cache
├── resolve ADC-input PMF runtime config
├── sample victim pulse at pos -> h_dsamp
├── enforce positive dominant main cursor
├── _build_psd_tx_noise(...) -> S_tn, h_tn
├── _build_psd_tx_jitter(...) -> S_jn, h_J
├── build PAM input PMF
├── combine full-jitter non-quantization PSD components -> S_ga
├── select clipping-only Gaussian PSD and CDF tail by fixed policy
├── branch on N_qb / P_qc
│   ├── disabled -> zero S_qn and method="disabled"
│   └── enabled -> _build_psd_adc_qn(...)
│       ├── gaussian_approx path, or
│       └── pmf_exact path
├── add S_qn -> S_total
├── derive sigma values and R_n
└── return candidate COMImpairmentStatus
```

## Produced status

The phase candidate returns:

```text
COMImpairmentStatus
├── pre_dte: COMImpStageStatus
│   ├── psd: COMPSDStatus
│   │   ├── sigma_X
│   │   ├── S_rn / sigma_rn
│   │   ├── S_xn / sigma_xn
│   │   ├── S_tn / sigma_tn
│   │   ├── S_jn / sigma_jn
│   │   ├── S_qn / sigma_qn
│   │   ├── S_total / sigma_total
│   │   └── R_n
│   └── adc_input: COMAdcInputPMF
└── eq_ch: COMEqChannelStatus
    ├── h_dsamp
    ├── h_tn
    ├── h_J
    └── h_XTs_dsamp
```

`eq_ch` is on the root `COMImpairmentStatus`; it is not nested under `pre_dte`. `pos` and `ts` belong to the DTE result rather than impairment status.

Every stored `S_*` value is a `SampledPSD`. Every stored `h_*` value is a `SampledResponse`. Grid ownership and legal absence are defined in [Status tree](../status_tree.md).

## ADC-input execution policy

`pre_dte_pmf_method` changes only the method used to obtain the pre-DTE ADC clipping/quantization material:

| Mode | Current stored ADC-input material |
|---|---|
| `gaussian_approx` | `p_sig`, approximate `p_sn`, `V_qc`, `delta`, method label |
| `pmf_exact` | `p_sig`, `p_s`, `p_ga`/`p_n` (same Gaussian PMF object), `p_sn`, `V_qc`, `delta`, method label |
| quantization disabled | `p_sig` and method `disabled`; `S_qn` is a zero PSD |

`pmf_grid_quality` resolves the PMF grid through `COMPMFConfig.resolve()` when `pmf_dy_override` is blank. A finite positive `pmf_dy_override` directly replaces the resolved `dy`, bypassing `dy_rel_As` and `dy_abs_max`. `pmf_keep_mass` replaces the resolved PMF retention value for this ADC-input calculation. These run controls trade runtime for numerical fidelity; the fixed `pre_dte_adc_clipping_convention` instead selects the clipping equation inputs.

workbook `align_to_ref=True` 時，adapter 已將各 run profile 展開為 exact
PMF、fine grid、`keep_mass=1`，並由 fine-grid 規則求 `dy`；同時把
pre-DTE clipping、離散訊號最近落格及 Gaussian reference sampling 寫入
具名 runtime methods。此 stage 與 `Pmf1D` 都不讀取 `align_to_ref`。

For `annex_d3`, clipping uses the full-jitter `S_ga=S_rn+S_xn+S_tn+S_jn` and left-tail `P_qc/2`. `matlab_4_17_reference_only` uses random-jitter-only `S_jn_RJ` **only for the clipping Gaussian sigma** and left-tail `P_qc`. Both modes keep the full `S_jn` in `S_total=S_ga+S_qn` and therefore in MMSE `R_n`. `COMAdcInputPMF.clipping_convention` records the selected mode separately from `method` (`pmf_exact` or `gaussian_approx`). The latter mode is a reference comparison branch, not a general 178A claim. The later final-COM ADC PMF calculation does not use this pre-DTE selector.

This pre-DTE policy does not control the accuracy-required final COM PMF configuration; final COM resolves its own PMF settings in the later COM DFE stage.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- an aggressor pulse or sampled aggressor response is not one-dimensional;
- `pos` is outside `[0, per_ui)`;
- common cache lacks `sigma_X`, `S_rn`, or `S_xn`;
- victim sampling produces an empty sequence;
- the sampled victim response does not have the required positive dominant cursor;
- jitter finite difference has no valid interior samples;
- a sampled response exceeds the configured sampled DFT window;
- PSD grids cannot be added or filtered consistently;
- `pre_dte_pmf_method` is unsupported;
- enabled quantization fails to produce a clipping value;
- PMF, impairment, or link config validation fails.

`COMMainCursorError` is handled specially by `_run_once()`: the phase is recorded as invalid and the sweep continues. Other errors propagate according to the model/search boundary.

## Downstream consumers

| Consumer | Data read |
|---|---|
| `calculate_MMSE_DTE()` | selected candidate `h_dsamp`, `R_n`, and `sigma_X` |
| phase selection | candidate `COMDTEStatus.mse`, after the DTE solver consumes this stage |
| `calculate_post_ffe_imp()` | selected pre-DTE impairment and equivalent responses |
| pre-DTE reporting | stored PSD components, sigmas, equivalent responses, and ADC-input PMF material |
| partial search row | no direct impairment fields; it consumes the following DTE result |

Reporting is read-only and must not rebuild pre-DTE PSDs or ADC PMFs from configuration.

## Validation evidence and tolerance

`tests/test_com_model_178A_policy_branches.py` checks both PMF methods under both clipping policies, confirms unchanged `h_dsamp` and non-quantization PSDs, and checks that the combined PSD difference equals the quantization-PSD difference. This does not independently validate every pre-DTE component against the specification.

Required stage-specific validation remains:

1. receiver-noise PSD and integrated sigma on a fixed grid;
2. one- and multi-aggressor crosstalk phase selection and power sum;
3. TX-noise sampled response and PSD;
4. jitter sampled response, units, PSD, and boundary handling;
5. quantization disabled, `gaussian_approx`, and `pmf_exact` paths;
6. `S_total`, integrated sigma, and autocorrelation consistency;
7. status grid/shape assertions and explicit numerical tolerances.

Until these exist, this document makes no specification-accuracy or numerical-tolerance claim.

## Known limitations and unresolved questions

- The implemented equations and unit conversions listed in the governing-reference table still require independent comparison with the accepted 178A reference.
- The common method accepts an unused `victim` argument; this is an API cleanup opportunity and does not change current calculations.
- `analysis_grid` 保留完整分析記錄；`fixed_ui` 明確採用有限 circular DFT record。
  這是可稽核的 policy，不由 tail threshold 自動切換。Akinwale 4096-UI 分支已
  對 SiCoPR total `R_n[0:87]` 至 `3.71e-21 V²`。
- The pre-DTE ADC PMF policy intentionally allows approximation, so `search_sweep` and accuracy-focused profiles may produce different pre-DTE numerical paths.
- Interference sources outside the currently represented receiver, crosstalk, TX noise, jitter, and quantization components require an explicit specification and config/status change before inclusion.
