# 178A DFE COM stage

> **Review state:** final-PMF configuration override, component ownership, quantization handoff, status output, and report/test dependencies are confirmed from source. The governing COM equations and numerical accuracy have not been independently revalidated by this documentation change.

## Purpose and ownership

This stage converts the selected post-FFE impairment responses and statistics into the DFE-based interference/noise PMF and scalar COM result.

It owns:

- the accuracy-required PMF runtime config used for final COM;
- ISI, Gaussian-noise, dual-Dirac, crosstalk, and ADC-quantization PMFs;
- their combined PMF;
- the configured error-ratio quantile, noise/interference amplitude, and DFE COM result;
- `COMPMFStatus` assignment to `status.pmf`.

It does not recompute path, pre-DTE, DTE, or post-FFE results and does not modify the expanded reporting PSDs.

## Governing-reference state

`calculate_COM_DFE()` is the current 178A DFE baseline used directly and as the baseline for MLSD. It reuses shared 93A PMF helper implementations for discrete interference construction and aggressor combination.

The current function does not provide a complete clause-by-clause 178A citation for every PMF component. A specification review must therefore confirm the reuse boundary, component membership, quantile convention, and final ratio before this stage can claim spec validation.

TC-019 的 reference preset 會在 adapter 展開成具名 PMF methods。此 stage
依這些方法讓 ISI／XT／DD 由原始 PAM 振幅乘 tap 後最近落格；Gaussian grid support 由
`NormalDist().inv_cdf(1-DER_0)` 決定並在 grid 取樣；ADC uniform
使用最近端點和 clipping-noise PMF 的完整 support，RX FFE tap 縮放
採 ordinate interpolation。final `dy=dy_rel_As*As` 以未正規化的
RX FFE 電壓座標表示，除以主 tap gain 後即為 reference 的 grid。
模型只傳遞已解析的方法，通用 PMF utility 與此 stage
都不包含 SiCoPR 專用 boolean。此選用方法不替代 D3.0 一般模式。

## Entry and prerequisites

```text
calculate_COM_DFE(imp_status, dte_status, run_cfg=None) -> COMPMFStatus
```

Required completed inputs are:

| Input | Required field | Use |
|---|---|---|
| post-FFE impairment | `As` | signal amplitude and PMF-grid resolution |
| equivalent channel | `h_ISI` | residual-ISI PMF |
| equivalent channel | `h_XTs_w` | combined crosstalk PMF |
| equivalent channel | `h_w_J` | dual-Dirac jitter PMF |
| post-FFE PSD status | `sigma_G` | Gaussian PMF |
| post-FFE ADC input | `method`, `delta` when enabled | quantization PMF |
| selected DTE | full `(N_max,)` `w_lim` | filter uniform quantization error through RX FFE |
| fixed config | `L`, `DER_0`, `A_DD`, PMF controls | symbol PMF, threshold, and component construction |

The stage is called only after `calculate_post_ffe_imp()` has been merged into status.

## Accuracy-required PMF policy

Final COM does not use the active execution profile's `pmf_grid_quality` or `pmf_keep_mass`; it does use its optional `pmf_dy_override`.

```text
_resolve_final_com_pmf_config(...)
├── resolve COMPMFConfig with grid_quality="fine"
├── replace dy with run_cfg.pmf_dy_override when provided
└── override keep_mass=1.0
```

This boundary prevents single-run/search mass truncation from changing final COM. When `pmf_dy_override` is blank, relative/absolute grid rules remain in `COMPMFConfig`; otherwise the run profile's positive voltage step directly supplies `dy`. Tap threshold and Gaussian span still come from `COMPMFConfig`.

`_run_once()` passes its selected `COMRunConfig` explicitly. A direct call without `run_cfg` uses `cfg.execution.single_run` for compatibility.

## Ordered functional blocks

```text
calculate_COM_DFE(...)
├── resolve final-COM PMF runtime config
├── build base PAM-L symbol PMF
├── build p_ISI from h_ISI
├── build p_XT from all h_XTs_w
├── build p_DD from A_DD and h_w_J
├── build p_qn
│   ├── disabled -> zero-amplitude unit-mass PMF
│   └── enabled
│       ├── require post-FFE method="pmf_exact" and delta
│       ├── build uniform one-sample quantization-error PMF
│       └── FIR-filter it by full w_lim
├── build p_G from sigma_G
├── combine p_ISI, p_XT, p_DD, p_qn, and p_G
├── evaluate configured DER_0 quantile -> y0
├── derive A_ni and COM
└── return COMPMFStatus
```

The combination order shown is the current software order. PMF combination represents independent-component convolution through `Pmf1D.combine()`.

## Component ownership

| Output component | Source quantity | Excluded from that component |
|---|---|---|
| `p_ISI` | stored `h_ISI` | Gaussian noise, crosstalk, DDJ, quantization |
| `p_XT` | all stored `h_XTs_w` | victim ISI and Gaussian noise |
| `p_DD` | configured `A_DD` and stored `h_w_J` | RJ; RJ is included in `sigma_G` upstream |
| `p_qn` | exact stored ADC `delta`, filtered by selected `w_lim` | pre-DTE approximate `S_qn` |
| `p_G` | stored post-FFE `sigma_G` | ISI, XT, DDJ, and quantization |

The stage reads `sigma_G` directly. It does not derive Gaussian noise from post-FFE reporting PSD components.

## Quantization boundary

When quantization is disabled, `p_qn` is a unit-mass PMF at zero.

When enabled, the `annex_d3` stage requires the exact selected-phase ADC-input material prepared earlier. It consumes `delta`, builds a uniform quantization-error PMF, and applies the selected full zero-filled FFE vector (Eq. 178A-44).

The separate `matlab_4_17_reference_only` policy follows the reference final-PDF calculation: it forms the clipping PMF from the pre-FFE victim signal and post-FFE ISI, XT, DDJ, and Gaussian components referred back through the RX FFE main gain. The clipping PMF grid and tap threshold are referred back by the same gain. Its left-tail CDF target is `P_qc`; its uniform quantization error is built on that ADC-input grid, then scaled through all RX FFE taps except the main tap onto the final PDF grid. This branch is for calibration against MATLAB/SiCoPR, not a replacement for the D3.0 default. The two policies share the already selected phase, FFE/DFE, and non-quantization final PMFs.

The pre-DTE quantization PSD exists to support the MMSE solve. It is not substituted for this final quantization PMF.

## Produced status

```text
COMPMFStatus
├── dy
├── tap_abs_th
├── p_ISI
├── p_G
├── p_DD
├── p_XT
├── p_qn
├── p_combined
├── y0
├── A_ni
└── COM
```

`COM._run_once()` assigns this object to `status.pmf`. `COMStatus.final_COM` returns this `COM` when no MLSD result is present.

The implemented scalar flow uses the configured `DER_0` quantile of `p_combined`, stores its absolute amplitude as `A_ni`, and forms the signal-to-interference/noise ratio in dB from `As` and `A_ni`. This behavior still requires independent equation-level validation.

## Failure conditions

The stage rejects or propagates errors for these conditions:

- completed post-FFE impairment or `sigma_G` is absent;
- quantization is enabled but ADC material is absent, is not `pmf_exact`, or lacks `delta`;
- `w_lim` does not have shape `(N_max,)`;
- a required equivalent response is absent;
- PMF grid, unit, or convolution inputs are incompatible;
- PMF construction or quantile evaluation fails;
- derived `A_ni` or COM becomes invalid through upstream data.

The current function does not add an explicit final finite/positive guard for `A_ni` before calculating COM; utility behavior and downstream consumers expose resulting invalid values. A dedicated validation contract should decide whether an explicit guard is required.

## Downstream consumers

| Consumer | Data read |
|---|---|
| single-run reporting | every component PMF, combined PDF/CDF, `y0`, `A_ni`, and `COM` |
| final search CSV | `COM` as `COM_DFE_dB`; also selected as final COM when MLSD is absent |
| MLSD added-noise solve | combined DFE PMF, `A_ni`, and DFE `COM` baseline |
| `COMStatus.final_COM` | DFE `COM` fallback |

Reporting is read-only and must not rebuild or recombine PMFs.

## Validation evidence and tolerance

Current automated evidence is limited to `tests/test_com_model_178A_post_ffe.py`:

- final `p_qn` RMS agrees with the post-FFE quantization reporting PSD RMS within `rtol=5e-4`, `atol=1e-8` for one fixed case;
- replacing all post-FFE display PSDs with zero leaves recomputed DFE COM unchanged to 12 decimal places.

There is no dedicated independent golden test for each component PMF, combined PMF, `DER_0` quantile, `A_ni`, or final DFE COM.

Required validation remains:

1. component PMFs against an accepted reference for a fixed selected DTE;
2. disabled and enabled quantization paths;
3. proof that final `keep_mass=1.0` is applied for all execution profiles;
4. PMF normalization, support, and grid consistency after every combination;
5. quantile convention at `DER_0`;
6. `A_ni` and COM numerical tolerances over more than one reference case;
7. explicit invalid/zero-amplitude failure behavior.

Until these exist, this document makes no specification-accuracy claim.

## Known limitations and unresolved questions

- Shared 93A PMF helper reuse in the 178A stage needs explicit reference confirmation.
- Final PMF mass retention remains hard-coded to 1.0; its voltage grid may be selected by `run_cfg.pmf_dy_override`.
- `calculate_COM()` remains a compatibility alias to `calculate_COM_DFE()` and should not be documented as a separate numerical stage.
- The PMF backend and general `Pmf1D` contracts remain utility-level documentation work outside this stage.
