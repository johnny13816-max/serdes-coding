# 178A Stage 2 common impairment and Stage 3 per-phase impairment builder

> **Review state:** the two-part stage boundary, cache lifecycle, runtime-policy inputs, produced status fields, and current component data flow are confirmed from source. Specification equations and numerical equivalence have not been independently revalidated by this documentation change.

## Purpose and ownership

This document owns the pre-DTE impairment algorithms used across two stage boundaries.

It is split into:

1. Stage 2 performs the phase-independent common calculation once per concrete path/filter candidate;
2. Stage 3 calls the phase-dependent builder for every phase selected by its execution policy.

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
calculate_pre_dte_imp_common(victim)
    -> common_imp: COMImpairmentStatus

prepare_sampling_phase_common(common_imp, h_XTs)
    -> (common_imp: COMImpairmentStatus, h_XTs_dsamp: list[np.ndarray])

calculate_pre_dte_imp_at_pos(victim, pos, common_imp, h_XTs_dsamp)
    -> (COMEqChannelStatus, COMImpairmentStatus)
```

`calculate_pos_candidate()` is the Stage 3 candidate wrapper. It invokes the
per-phase builder, then hands the matching `eq_ch` and impairment to Stage 4.

## COM call-tree hierarchy

The two builders share a physical domain but have distinct stage ownership.

```text
COM                                                   [Root: model]
├── __init__(cfg)                                     [Root: shared context]
│   └── _resolve_eq_ch_imp_record_cfg()               [NUM-003 shared state]
└── _run_once()                                       [L0: stage set]
    ├── Stage 2: common pre-DTE impairment            [L1]
    │   └── calculate_pre_dte_imp_common()            [L2: common-cache set]
    │       ├── receiver-noise construction           [L3]
    │       │   └── _build_psd_rx_noise()             [L4; NUM-003 record]
    │       └── signal variance                       [L3/L4]
    └── Stage 3: sampling-phase evaluation            [L1]
        ├── prepare_sampling_phase_common()           [L2]
        │   ├── XT path phase selection               [L3]
        │   │   └── _select_xtalk_path_phase()        [L4; full response]
        │   └── eq-channel impairment PSD construction [Shared L3; NUM-003]
        │       ├── _realize_eq_ch_imp_record()       [L4]
        │       └── _build_eq_ch_imp_psd()            [L4]
        └── calculate_pre_dte_imp_at_pos()            [L2: phase-specific set]
            ├── sampled equivalent-channel formation  [L3]
            │   └── SampledResponse.from_ir()         [L4]
            ├── transmitter-noise construction        [L3]
            │   ├── _calculate_tx_noise_eq_ch()       [L4: sample stored pulse_no_txffe]
            │   └── _build_eq_ch_imp_psd()            [Shared L3; NUM-003]
            ├── jitter-noise construction             [L3]
            │   ├── _calculate_tx_jitter_eq_ch()      [L4]
            │   └── _build_eq_ch_imp_psd()            [Shared L3; NUM-003]
            ├── ADC-input / quantization              [L3]
            │   ├── _resolve_adc_input_pmf_config()   [L4: NUM-004/NUM-006; Gaussian support fixed 8σ]
            │   ├── _build_pmf_pam_L()                [L4: exact PAM source]
            │   ├── clipping PSD/tail selection        [L4: ALG-008]
            │   └── _build_psd_adc_qn()               [L4: fixed exact-PMF owner]
            │       └── _calculate_V_qc()
            │           ├── _build_pmf_interference_178A() [L4: ALG-002 direct injector]
            │           │   └── Pmf1D.fir_filter()/scale_x() [L5: ALG-002 owner set]
            │           └── Pmf1D.gaussian()          [L5: ALG-003]
            └── total-noise covariance                [L3]
                └── SampledPSD.add() / to_autocorrelation() [L4]
```

Stage 2 returns a phase-independent `COMImpairmentStatus` used only as a local
cache. Stage 3 builds a candidate `COMEqChannelStatus` plus candidate
`COMImpairmentStatus`; Stage 4 consumes their `h_dsamp`, `R_n`, and `sigma_X`.

### Branch references

本 stage 涉及 ALG-002、ALG-003、ALG-008、NUM-003、NUM-004、NUM-006，並保留
retired ALG-009 的 fixed exact-PMF flow。它們的分類、owner、review status 與
validation evidence 統一記錄於
[178A Branch Behavior Registry](../branch_behavior_registry.md)；本文件不另建
平行 review table。

Quantization disabled when `N_qb`／`P_qc` is absent is input/configuration
availability handling, not a branch behavior.

## Cache and status lifecycle

```text
once per concrete candidate
├── Stage 2: calculate_pre_dte_imp_common(...)
│   └── sigma_X + S_rn common cache
└── Stage 3 preparation: prepare_sampling_phase_common(...)
    └── S_xn + full one-sample/UI h_XTs_dsamp

for every requested victim pos
└── calculate_pre_dte_imp_at_pos(...)
    └── candidate COMEqChannelStatus + COMImpairmentStatus

phase selection
└── selected eq_ch / imp / dte are committed together at the root
```

The common return values are run-local cache objects. They are not a separate `COMStatus` stage. Each phase candidate receives them explicitly. Unselected phase impairment objects are not retained at the root status.

## Required inputs

### Common calculation

| Input | Required data | Use |
|---|---|---|
| `COMConfig.link` | sampled grid, `fb`, `theta`, and `per_ui` | sampled PSD/response construction |
| `COMConfig.num.eq_ch_imp_len/num_trunc_ui` | `full` or `truncated` plus an even UI count | shared impairment PSD/correlation record |
| `COMConfig.filter` | receiver noise-filter and CTF controls | receiver-noise filtering |
| `COMConfig.imp` | `eta_0` | receiver-noise PSD |
| `COMConfig.L` | PAM order | normalized symbol standard deviation |
| `h_XTs` | full oversampled aggressor pulse arrays | Stage 3 per-path phase selection, full sampled eq-channel records, and crosstalk PSD |

The `victim` argument is accepted by the current public method but is not read inside the common calculation.

### Per-phase calculation

| Input | Required data | Use |
|---|---|---|
| `victim` | `pulse.ir`, `pulse_no_txffe.ir` | victim samples, jitter response, and TX-noise sampling; all CTLE/ALG-006/ALG-007 work is already complete in Stage 1 |
| `pos` | integer in `[0, per_ui)` | victim phase selection |
| `common` | `sigma_X`, `S_rn`, `S_xn`, and their integrated values | reused phase-independent components |
| `h_XTs_dsamp` | one-dimensional sampled response for each aggressor | selected candidate equivalent-channel status |
| `COMConfig.imp` | `SNR_TX`, `sigma_RJ`, `A_DD`, `N_qb`, `P_qc`, `R_LM` | phase-specific impairment and optional quantization controls |
| `COMConfig.pmf` | PMF support/tap/mass defaults | ADC-input PMF construction |
| `COMConfig.num` | `pmf_keep_mass`, effective `adc_input_pmf_grid` | retained-mass and grid numerical controls；no PMF-method selector |

The exact workbook mappings are defined in [Configuration tree](../config_tree.md).

## Common functional blocks

```text
calculate_pre_dte_imp_common(...)
├── derive sigma_X from the configured PAM order
├── _build_psd_rx_noise(...)
│   ├── construct continuous receiver-noise PSD
│   ├── filter through receiver-noise and CTF responses
│   └── convert onto the sampled theta grid
└── return sigma_X + S_rn common cache

prepare_sampling_phase_common(...)
└── for each aggressor
    ├── select phase from the full oversampled response
    ├── retain the full one-sample/UI eq-channel response
    ├── apply NUM-003 only before PSD conversion
    └── add the PSD to the uncorrelated crosstalk sum
```

The aggressor phase selection is independent of the victim `pos` loop. It is
owned by Stage 3 preparation and cannot be changed by NUM-003 truncation.

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
├── sample victim.pulse_no_txffe at pos -> h_tn
├── _build_eq_ch_imp_psd(h_tn, ...) -> S_tn
├── _calculate_tx_jitter_eq_ch(...) -> full h_J
├── _build_eq_ch_imp_psd(h_J, ...) -> S_jn
├── build PAM input PMF
├── combine full-jitter non-quantization PSD components -> S_ga
├── select clipping-only Gaussian PSD and CDF tail by fixed policy
├── branch on N_qb / P_qc
│   ├── disabled -> zero S_qn and method="disabled"
│   └── enabled -> _build_psd_adc_qn(...)
│       └── exact p_s + p_ga -> p_sn -> V_qc -> delta -> S_qn
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

## ADC-input exact-PMF contract

Enabled quantization always obtains the pre-DTE ADC clipping/quantization material through the exact PMF flow:

| State | Current stored ADC-input material |
|---|---|
| quantization enabled | `p_sig`, `p_s`, `p_ga`/`p_n` (same Gaussian PMF object), `p_sn`, `V_qc`, `delta`, method `pmf_exact` |
| quantization disabled | `p_sig` and method `disabled`; `S_qn` is a zero PSD |

`adc_input_pmf_grid` owns `rule`, `dy_rel_As`, `dy_abs_max`, and optional
`dy_override`. The override has highest priority; otherwise the rule selects
relative-only or relative-with-cap resolution. `pmf_keep_mass` remains the
separate NUM-006 retention control. These numerical controls do not affect final
DFE/MLSD PMFs.

workbook `execution_profile=sicopr_reference_v1` 時，adapter 將各 run profile 展開為
`keep_mass=1` 與 ADC-input explicit `dy=10 µV`；同時把
pre-DTE clipping、離散訊號最近落格及 Gaussian reference sampling 寫入
具名 runtime methods。此 stage 與 `Pmf1D` 都不讀取 profile selector。

For `full_jitter_half_tail`, clipping uses the full-jitter `S_ga=S_rn+S_xn+S_tn+S_jn` and left-tail `P_qc/2`, matching D3.2 Eq. (178A-29) through Eq. (178A-31). `rj_only_full_tail_reference` uses random-jitter-only `S_jn_RJ` **only for the clipping Gaussian sigma** and left-tail `P_qc`. Both modes keep the full `S_jn` in `S_total=S_ga+S_qn` and therefore in MMSE `R_n`. `COMAdcInputPMF.clipping_convention` records the clipping convention separately from the fixed exact-PMF `method`. The later final-COM ADC PMF calculation remains independently owned.

This pre-DTE policy does not control the accuracy-required final COM PMF configuration; final COM resolves its own PMF settings in the later COM DFE stage.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- an aggressor pulse or sampled aggressor response is not one-dimensional;
- `pos` is outside `[0, per_ui)`;
- common cache lacks `sigma_X`, `S_rn`, or `S_xn`;
- victim sampling produces an empty sequence;
- the sampled victim response does not have the required positive dominant cursor;
- jitter finite difference has no valid interior samples;
- a NUM-003 record cannot be realized under its declared full/truncated contract;
- PSD grids cannot be added or filtered consistently;
- a legacy workbook requests retired `pre_dte_pmf_method=gaussian_approx`;
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

`tests/test_com_model_178A_policy_branches.py` checks the fixed exact-PMF path under both clipping policies, confirms unchanged `h_dsamp` and non-quantization PSDs, checks that the combined PSD difference equals the quantization-PSD difference, and covers legacy exact-row compatibility plus Gaussian-row rejection. This does not independently validate every pre-DTE component against the specification.

Required stage-specific validation remains:

1. receiver-noise PSD and integrated sigma on a fixed grid;
2. one- and multi-aggressor crosstalk phase selection and power sum;
3. TX-noise sampled response and PSD;
4. jitter sampled response, units, PSD, and boundary handling;
5. quantization disabled and fixed exact-PMF paths, including legacy-row compatibility/rejection;
6. `S_total`, integrated sigma, and autocorrelation consistency;
7. status grid/shape assertions and explicit numerical tolerances.

Until these exist, this document makes no specification-accuracy or numerical-tolerance claim.

## Known limitations and unresolved questions

- The implemented equations and unit conversions listed in the governing-reference table still require independent comparison with the accepted 178A reference.
- The common method accepts an unused `victim` argument; this is an API cleanup opportunity and does not change current calculations.
- `full` 保留完整 impairment equivalent-channel 記錄；`truncated` 明確採用
  `num_trunc_ui` 的有限 circular DFT record。這是可稽核的 policy，不由 tail
  threshold 自動切換。Akinwale 4096-UI 分支已
  對 SiCoPR total `R_n[0:87]` 至 `3.71e-21 V²`。
- Pre-DTE ADC PMF construction is fixed exact behavior; search profiles may still differ through independent retained-mass, grid, floating-tap, and phase-scheduling controls.
- Interference sources outside the currently represented receiver, crosstalk, TX noise, jitter, and quantization components require an explicit specification and config/status change before inclusion.
