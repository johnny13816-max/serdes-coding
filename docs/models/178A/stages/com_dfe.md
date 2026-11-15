# 178A Stage 6 — DFE COM model

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
依這些方法讓 ISI／XT／DD 由原始 PAM 振幅乘 tap 後最近落格；Gaussian grid support
固定為 internal 8σ，並依選定 PDF→PMF method 建構；ADC uniform
使用最近端點和 ADC-input clipping-noise PMF 的完整 support，RX FFE tap 縮放
使用 ordinate interpolation；專案方法維持 mass deposit。final `dy=dy_rel_As*As` 以未正規化的
RX FFE 電壓座標表示，除以主 tap gain 後即為 reference 的 grid。
模型只傳遞已解析的方法，通用 PMF utility 與此 stage
都不包含 SiCoPR 專用 boolean。此選用方法不替代 D3.0 一般模式。

## Entry and prerequisites

```text
calculate_COM_DFE(imp_status, eq_ch, dte_status) -> COMPMFStatus
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

Final COM does not use the ADC-input grid family or active run's
`pmf_keep_mass`; it uses the independent effective `final_pmf_grid` family and
fixes `keep_mass=1.0`. Stage 6 therefore is not a NUM-006 consumer.

```text
_resolve_final_com_pmf_config(...)
├── resolve final_pmf_grid.rule with final-domain As
├── apply final_pmf_grid.dy_override when provided
├── delegate spacing arithmetic to COMPMFGridControl.resolve_dy()
└── override keep_mass=1.0
```

This boundary prevents ADC-input resolution and run-level mass truncation from
changing final COM. A positive final override directly supplies `dy`; otherwise
the final family selects relative-only or relative-with-cap. Tap threshold and
Gaussian span still come from `COMPMFConfig`.

This L4 resolver is the NUM-005 sole domain owner and Stage 6 execution point.
`calculate_COM_DFE()` is its direct consumer: every component PMF and
`p_combined` are constructed on the resolved spacing, so NUM-005 is not a final
post-combination regrid. The L5 `resolve_dy()` operation is shared with NUM-004
and does not own final-domain identity.

The stage reads the resolved `cfg.alg` and `cfg.num` of its `COM` instance.
The adapter selects the run mode before construction, so this method neither
accepts nor resolves an execution profile.

## Ordered functional blocks

```text
calculate_COM_DFE(...)
├── resolve final-COM PMF runtime config
├── build base PAM-L symbol PMF
├── build p_ISI from h_ISI
├── build p_XT from all h_XTs_w
├── build p_DD from A_DD and h_w_J
├── build p_G from sigma_G
├── _build_final_adc_quantization() → p_qn, V_qc, delta [ALG-012／013 owner]
│   ├── disabled -> zero-amplitude unit-mass PMF
│   └── enabled
│       ├── require post-FFE method="pmf_exact"; spec mode requires delta
│       ├── select V_qc / delta and quantization taps by convention
│       └── build uniform PMF and FIR-filter with selected taps
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

`policy.final_com_vqc_convention` is the ALG-012 boundary. With
`selected_phase_adc_input`, the stage reuses the exact selected-phase ADC-input
`V_qc` and `delta` prepared in Stage 5. With `sicopr_final_reconstruction`, it
reconstructs the final clipping distribution from the pre-FFE victim signal and
post-FFE ISI, XT, DDJ, and Gaussian components referred back through the RX FFE
main gain, then applies the SiCoPR `P_qc` tail rule to obtain `V_qc` and `delta`.

The reference path also follows the SiCoPR quantization-tap selection described
below; this reference-only behavior is not the complete FIR model. Both V_qc
conventions share the selected phase, FFE/DFE, and non-quantization final PMFs.

ALG-013 的 concrete owner 是 `COM._build_final_adc_quantization()`。

PMF 卷積方法由 NUM-007 獨立控制：`fft` 是 project 預設，reference profile
使用 `linear`。`Pmf1D.fir_filter()` 和 `Pmf1D.combine()` 為 operation owners；
此選擇不改變 ALG-013 的 support、tap threshold 或 grid 定義。完整 reference
對照範圍與限制記錄於 `docs/validation/178A_pmf_convolution_evidence.md`。
`annex_d3` 保留原本的 tap threshold 與 mass-deposit scaling；
`reference_support` 使用 ADC-input noise PMF 的 amplitude grid 和 ordinate
interpolation，並要求 `pdf_to_pmf_method=pmf_sample`。此 reference 數值
路徑已通過固定輸入的 SiCoPR PMF 比較及現有 golden；不能由此推論完整 COM 對齊。
固定 golden 首次驗證：MSE、`V_qc`、`delta` 既有斷言通過；
`A_ni` 從 `0.2656833333333335 V` 變成約 `0.2694833333333335 V`，
不符合原 `1e-12 V` 容差。測試在此停止，未驗證 final COM；未修改 golden。
修正 ADC grid 後，固定 golden 重跑 `1 passed`，MSE、`A_ni`、DFE COM、
final COM 均符合既有 tolerance，未變更 golden。
同一 golden case、phase 5、MSE `0.006191300963670364` 的 Stage 6
counterfactual，以相同 noise、FFE、`delta` 隔離兩個數值選擇：

| Uniform PMF grid | Tap scaling | `p_qn` bins | `A_ni` (V) |
|---|---|---:|---:|
| ADC input (`5.374294198730745 µV`) | mass deposit | 33541 | 0.2656833333333335 |
| ADC input | ordinate interpolation | 33567 | 0.2656833333333326 |
| Final (`316.6666666666667 µV`) | mass deposit | 1420693 | 0.2685333333333233 |
| Final | ordinate interpolation | 1420717 | 0.2694833333333406 |

此對照表明本 case 的 `A_ni` 變化主要來自 grid；它不是 SiCoPR 實跑資料，
不能單憑此表宣稱逐格對齊。先前 TC-019 的 SiCoPR 對照記錄顯示兩側
電壓座標須經 main tap gain 換算；直接使用 final grid 的錯誤修改已依核准修正。

進一步以 SiCoPR Python 1.2.1（`cb7c4be5c63d41e88b6ee7d04fb17e0046ab0f75`，
模擬 COM 4.17）實際執行 quantization PMF：固定 golden case phase 5、
共用 `V_qc=0.0431394595332117 V` 與同一組 noise／FFE；以 main gain
`58.92246590100227` 轉換座標，ADC grid 加 ordinate interpolation 的
兩側 PMF 都有 33567 bins，逐格最大差 `8.413408858487514e-17`、L1 差
`2.5034663500457392e-14`。這是 fixed-input 的 PMF 對照，不是完整 SiCoPR
COM run；兩側 clipping 先固定為相同值，ALG-012 的差異未包含。
SiCoPR 1.2.1 使用 direct convolution；專案可由 NUM-007 選擇 FFT 或 linear。
有限資料的尾端對照記錄於 `docs/validation/178A_pmf_convolution_evidence.md`。

The pre-DTE quantization PSD exists to support the MMSE solve. It is not substituted for this final quantization PMF.

## Produced status

```text
COMPMFStatus
├── dy
├── tap_abs_th
├── final_vqc_convention
├── final_V_qc
├── final_delta
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

- **SiCoPR quantization tap indexing：** reference path 先找出 `w_lim` 的非零
  係數，再跳過第 `d_w + 1` 個；不足該位置時不跳過。此方式重現 SiCoPR
  4.17 的索引規則，不是完整 FIR 模型。Spec path 仍使用完整 taps；
  `Pmf1D.fir_filter()` 不負責選擇要跳過的 tap。Stage 6 focused 7 passed、
  3 subtests passed（涵蓋有／無前置零及非零 taps 不足）；project golden 1 passed。
  其他 reference 數值細節仍需審查。
- Shared 93A PMF helper reuse in the 178A stage needs explicit reference confirmation.
- Final PMF mass retention remains hard-coded to 1.0; its voltage grid is owned by
  `cfg.num.final_pmf_grid`. There is no shared runtime `dy` override in the
  stage API.
- `calculate_COM()` remains a compatibility alias to `calculate_COM_DFE()` and should not be documented as a separate numerical stage.
- The PMF backend and general `Pmf1D` contracts remain utility-level documentation work outside this stage.
