# 178A configuration tree

Ad Hoc source interpretation, conditional requiredness, and GUI review follow
[the mapping contract](../../architecture/adhoc_mapping_contract.md) and its
[field table](../../architecture/adhoc_mapping_fields.md). Source-derived values
and project policy defaults are separate review areas. Package submodule enable
extensions are deferred to the separate core contract described there.

> This is the 178A-specific inventory of project fields and typed runtime ownership. It does not define model equations. Project-wide rules are in [configuration architecture](../../architecture/configuration_architecture.md).

## Configuration layers

```text
CASE_CONFIG
└── case identity and provenance
RUN_MODE
├── single_run
└── search_run
FIXED_CONFIG
├── intrinsic
├── derived
└── policy
EXEC_POLICY
├── single_run
├── search_sweep
└── search_final
SEARCH_CONFIG
└── candidate values and search controls
```

`search_sweep` is the first step of `search_run`; `search_final` evaluates retained candidates. Execution policy selects computational path/efficiency settings. Search ranges stay in `search_config`.

## Runtime dataclass tree

```text
COMConfig
├── L
├── link: LinkConfig
├── filter: COMFilterConfig
├── channel: COMChannelConfig
├── txpkg_victim: COMPkgConfig
├── txpkg_fext: COMPkgConfig
├── txpkg_next: COMPkgConfig
├── rxpkg: COMPkgConfig
├── dte: COMDTEConfig
├── imp: COMImpairmentConfig
├── DER_0
├── pmf: COMPMFConfig
├── policy: COMPolicyConfig
│   ├── out_of_measured
│   ├── channel_renormalization_order
│   ├── pre_dte_adc_clipping_convention
│   ├── final_adc_quantization_convention
│   ├── ctle_pulse_realization
│   ├── rxffe_record_realization
│   ├── noise_grid_method
│   ├── noise_grid_num_ui
│   ├── discrete_pmf_placement
│   ├── interference_pmf_method
│   ├── xtalk_pmf_accumulation
│   ├── gaussian_pmf_method
│   ├── uniform_pmf_method
│   ├── pmf_scaling_method
│   ├── final_pmf_grid
│   ├── final_adc_pmf_projection
│   ├── gaussian_n_sigma_override
│   ├── added_noise_pdf
│   ├── mlsd_quantization_psd
│   ├── sequence_termination
│   ├── reported_der
│   ├── applied_config_profile           provenance only
│   └── config_profile_overrides         provenance only
├── execution: COMExecutionConfig
│   ├── single_run: COMRunConfig
│   ├── search_sweep: COMRunConfig
│   ├── search_final: COMRunConfig
│   ├── search_group_size
│   └── search_top_k
└── mlsd: COMMLSDConfig

COMSearchConfig                 separate search-run input
```

`excel_to_config_178A()` reads `fixed_config`, `run_config`, and `channels`; `excel_to_search_config_178A()` reads `search_config`.

## Case config

| Workbook field | Purpose | Runtime mapping |
|---|---|---|
| `case_id` | Case-folder identity | None |
| `source_config` | External workbook provenance | None |
| `source_note` | Human-readable conversion note | None |

The current template labels these rows `intrinsic`; that is incorrect. They belong to case config.

## Fixed config tree

For package groups, every listed package field is repeated under `txpkg_victim`, `txpkg_fext`, `txpkg_next`, and `rxpkg`.

### Intrinsic fields

| Runtime owner | Project workbook fields | Source / blank contract |
|---|---|---|
| `LinkConfig` | `fb`, `per_ui`, `target_df` | Ad Hoc `f_b`, `M`, `Delta_f`; required, with unit conversion |
| `COMFilterConfig` | `c_m3`, `c_m2`, `c_m1`, `c_1`, `c_0_min`, `Tr`, `fr`, `g_1`, `g_2`, `f_z1`, `f_z2`, `f_p1`, `f_p2`, `f_p3`, `A_v`, `A_fe`, `A_ne` | Version-specific Ad Hoc keys and units; `Tr`, `fr`, and `f_p3` are required mapping inputs; other blanks also fail |
| `COMDTEConfig` | `N_wg`, `N_wf`, `N_b`, `w_pre1_max`, `w_post1_max`, `w_fixed_rest_max`, `w_float_max`, `b_first_min`, `b_first_max`, `b_rest_min`, `b_rest_max` | Ad Hoc DTE/FFE/DFE inputs; required |
| `COMImpairmentConfig` | `R_LM`, `SNR_TX`, `sigma_RJ`, `A_DD`, `eta_0`, `N_qb`, `P_qc` | Ad Hoc model inputs; `N_qb` and `P_qc` configure ADC quantization noise and are both required |
| `COMMLSDConfig` | `mlsd_enable`, `mlsd_trunc_len`, `delta_com_an`, `minimum_com_limit` | Ad Hoc MLSD inputs. When enabled, required truncation input must be present. Optional `delta_com_an` stays distinct from `minimum_com_limit` |
| `COMConfig` | `L`, `DER_0` | Direct Ad Hoc mapping; required |
| four `COMPkgConfig` objects | `device_term.C_d_seq`, `device_term.L_s_seq`, `device_term.C_b`; `device_pkg.z_p_seq`, `device_pkg.Z_c_seq`, `device_pkg.gamma_0`, `device_pkg.a1`, `device_pkg.a2`, `device_pkg.tau`, `device_pkg.C_p`; `partial_host.enable`, `partial_host.C_0`, `partial_host.C_1`, `partial_host.z_h`, `partial_host.Z_h`, `partial_host.gamma_0`, `partial_host.a1`, `partial_host.a2`, `partial_host.tau`; `R0` | Ad Hoc package profile and unit conversion; required |
| `COMChannelConfig` | `R_0`, `R_d_tx`, `R_d_rx`, `sparam_frequency_limit_GHz` | Resistance values are required intrinsic mappings. Runtime derives `gamma_src` and `gamma_load`; Gamma is not a project input. Ad Hoc `flim` maps to the optional frequency limit; blank maps to `None` and preserves the complete measured record. |

### Derived fields

| Workbook field | Runtime owner | Derivation |
|---|---|---|
| `d_w` | `COMDTEConfig` | `ffe_pre_tap_len`: precursor tap count |
| `N_fix` | `COMDTEConfig` | `ffe_pre_tap_len + 1 + ffe_post_tap_len`: precursor, main cursor, fixed postcursors |
| `N_max` | `COMDTEConfig` | `N_fix` when `N_bg=0`; otherwise `ffe_pre_tap_len + N_f + 1` |
| `num_pre` | `COMFilterConfig` | Current project TX FFE main cursor index; value is 3 for `[c(-3), c(-2), c(-1), c(0), c(1)]` |
| `w_float_min` | `COMDTEConfig` | Current converter derives as `-bmaxg` |

These rows stay in the template by the approved decision and are labeled
`derived`.

### Policy fields

These fields are project-owned and are not Ad Hoc mapping targets. Current defaults are carried forward from the project template.

| Field（舊欄位保留讀取相容） | Runtime owner | Default |
|---|---|---:|
| `dy_rel_As` | `COMPMFConfig` | 0.001 |
| `dy_abs_max` | `COMPMFConfig` | 1e-5 V |
| `tap_rel_As` | `COMPMFConfig` | 0.001 |
| `gaussian_n_sigma` | `COMPMFConfig` | 8 |
| `missing_dc_policy` | `COMChannelConfig` | `skrf` |
| `align_to_ref` | `com_excel_io_178A` preset selector；不進入 `COMConfig` | `False` |
| `out_of_measured` | `COMConfig.policy` | `cosine_decay` |
| `channel_renormalization_order` | `COMConfig.policy` | `sdd_first` |
| `pre_dte_adc_clipping_convention` | `COMConfig.policy` | `annex_d3` |
| `final_adc_quantization_convention` | `COMConfig.policy` | `annex_d3` |
| `ctle_pulse_realization` | `COMConfig.policy`（workbook 不單獨曝露） | `continuous_tf` |
| `rxffe_record_realization` | `COMConfig.policy`（workbook 不單獨曝露） | `linear_convolution` |
| `noise_grid_num_ui` | `COMPolicyConfig` | 留白：`analysis_grid` |

All listed PMF controls and `missing_dc_policy` are labeled `policy`. There is
no `quantization_vqc_method` row in the 178A project template: it has no 178A
runtime owner. `run_config.pre_dte_pmf_method` is the applicable execution
control.

`align_to_ref` 是新版 178A 模板唯一可見的 reference preset **開關**；模板另有
optional 數值 policy `noise_grid_num_ui`。兩者都不從 Ad Hoc 映射；
`noise_grid_num_ui` 留白表示沿用 analysis grid。`align_to_ref=False` 保持舊
case 個別 policy 與 run profile；`True` 由
`com_excel_io_178A` 在建構 runtime config 前展開為 SiCoPR／MATLAB 4.17
具名方法：`zero_padding`、`s4p_first`、`bilinear_iir`、
`finite_record_circshift`、pre-DTE/final ADC reference 分支，
`fixed_ui` noise grid（本案 4096 UI）、
以及 `COMPolicyConfig` 中的離散 tap 最近格點、原子干擾卷積、逐路徑
XT、Gaussian grid sampling（支撐範圍由 `NormalDist().inv_cdf(1-DER_0)`
決定）、uniform 最近端點、ordinate interpolation、reference support 與
relative-`As` final grid。`COMConfig` 不保留此 boolean；model 只讀上述
具名值。執行 profile 在 adapter 固定 exact PMF、fine grid、`keep_mass=1`，且
pre-DTE `dy` 依 fine grid 的 `min(dy_abs_max, dy_rel_As*As)` 求得；
final COM／MLSD 在專案未正規化的 RX FFE 電壓座標使用
`dy_rel_As*As`，相當於 SiCoPR 主 tap 正規化後的 `dy` 乘回主 tap gain。
舊 workbook
的個別欄位仍可讀；開關為 `True` 時 adapter 以 reference preset 覆蓋，
並在 `COMConfig.policy.applied_config_profile`／`config_profile_overrides` 記錄 profile 與
raw/effective 值。此模式只供 reference 比對，不宣稱為 178A 通用方法。

`ctle_pulse_realization="bilinear_iir"` 是完整且不可拆分的 pulse-realization
方法：measured composite pre-CTLE TF、reference frequency grid、raw IFFT、
停用 causality correction、固定 `1e-3` peak 截尾、兩級 bilinear IIR 與一 UI
unit pulse。這些步驟沒有額外 config 欄位。`rxffe_record_realization` 是另一個
post-FFE 邊界；reference preset 選 finite-record circular shift，general 預設
保留 fixed-grid linear convolution 與 overflow guard。

`out_of_measured` 控制 terminated scalar `H_21` 從量測 S-parameter grid
轉到 analysis grid 時的頻帶外處理。`cosine_decay` 保留原本的 cosine
衰減；`zero_padding` 僅在輸入的最高量測頻點以上補零。victim、NEXT、
FEXT 使用同一政策。數值操作由 `SparamModel.to_LinkSegment()` 呼叫
`LinkSegment.from_tf()`／`resample_tf()` 執行，不修改 `S_ch` 或 `S_all`
矩陣。有效量測上限由 `COMChannelConfig.sparam_frequency_limit_Hz` 決定；
`zero_padding` 從該有效上限之後生效。Akinwale case 的六個原始 S4P 都到
100 GHz，而 Ad Hoc `flim=67 GHz` 會映射為 case-level
`sparam_frequency_limit_GHz=67`。一般模板留白，`align_to_ref` 本身不強制
任何固定頻率。

`channel_renormalization_order` 在 S4P reader 選 `sdd_first` 或
`s4p_first`。前者保留 178A-4 的 Sdd 二埠 renormalization；後者先對
完整 single-ended 四埠 renormalize 至 `R_0`，再取 Sdd。`COMConfig`
只選方法；數值處理由 `SparamModel.from_touchstone()`／`from_network()`
執行，六條 channel 共用。模板預設 `sdd_first`，SiCoPR case 選
`s4p_first`；此欄位不從 Ad Hoc 映射，也不影響 93A。

`pre_dte_adc_clipping_convention` 只控制 MMSE 前 ADC clipping 的
Gaussian noise sigma 與 CDF 左尾門檻。`annex_d3` 是所持 D3.0 Annex
的預設：clipping Gaussian 含完整 jitter，左尾 `P_qc/2`。
`matlab_4_17_reference_only` 供 SiCoPR／COM MATLAB 4.17 對照：clipping
Gaussian 僅含 random jitter，左尾 `P_qc`。兩者送入 MMSE 的 jitter
PSD 仍含 random jitter 與 DDJ；切換只經 `V_qc → S_qn` 改變 `R_n`。
後續 selected-phase final COM 會另外建立 ADC-input PMF，此欄位不
控制該階段。reference-only 分支不是 general method；新版規範釐清後
再決定是否合併。詳見 [TC-017](../../planning/tc017_pre_dte_adc_clipping_reference.md)。

`final_adc_quantization_convention` 獨立選擇 final DFE COM 的 ADC
量化算法，不改 pre-DTE `S_qn`、MMSE 或 post-FFE reporting PSD。
`annex_d3` 沿用 selected-phase ADC-input `delta`，Eq. 178A-44 讓
全部 RX FFE tap 參與量化 PMF。`matlab_4_17_reference_only` 以
pre-FFE victim signal 與除以 RX FFE 主 tap gain 的 post-FFE
ISI／XT／DDJ／Gaussian PMF 組成 clipping 輸入，取左尾 `P_qc` 得
`V_qc`，再讓量化 PMF 通過非主 tap。此分支只供 reference 對照，
不視為 D3.0 通用公式；兩個 clipping policy 可獨立設定。

## Channels

The `channels` sheet provides one victim and indexed NEXT/FEXT rows, with S4P path, port order, and enable/use state. S4P files remain under `reference_data/COM_channel_data/` and are referenced by path. `R_0`, `R_d_tx`, and `R_d_rx` live in fixed config. Every package `R0` remains required and the project adapter rejects any package/channel `R0` mismatch.

## Search config

| Workbook parameter | Runtime field | Meaning |
|---|---|---|
| `c_m2`, `c_m1`, `c_1` | `c_m2_values`, `c_m1_values`, `c_1_values` | TX FFE candidate sequences |
| `g_1`, `g_2` | `g_DC_values`, `g_DC2_values` | 178A CTF gain candidate sequences |
| `keep_top_n` | `keep_top_n` | Retained successful result count |
| `keep_all_rows` | `keep_all_rows` | Result retention behavior |
| `continue_on_error` | `continue_on_error` | Candidate error handling |

Fixed baselines and search candidates are separate. The current fixed baselines for `c_m2`, `c_m1`, `c_1`, `g_1`, and `g_2` are zero.

## Execution policy (`run_config`)

| Profile | Purpose |
|---|---|
| `single_run` | Manual single execution |
| `search_sweep` | First step of `search_run`; candidate evaluation |
| `search_final` | Second step; final evaluation of retained candidates |
| `search` | Orchestration values `group_size` and `top_k` |

Each run profile supplies `target`, `pre_dte_pmf_method`, `pmf_grid_quality`, `pmf_keep_mass`, optional `pmf_dy_override`, `floating_mode`, `pos_sweep_method`, and `pos_coarse_stride`. These are execution policy: they select computational methods and speed/accuracy tradeoffs without changing the fixed model input. When `pmf_dy_override` is set to a finite positive voltage, the resolved runtime PMF `dy` uses that value directly for ADC-input and final DFE/MLSD PMFs; `dy_rel_As` and `dy_abs_max` are bypassed. A blank override retains the prior coarse/fine derivation. Final COM still keeps all PMF mass (`keep_mass=1`) independently of the run profile.

## Requiredness and runtime fallback

- A required Ad Hoc intrinsic absent from the source is a conversion failure; do not fill it from the template.
- An optional intrinsic may be blank only where its field contract permits omission; the runtime adapter then maps it to `None`.
- When MLSD is enabled, missing required `N_tc`/supported truncation data is a failure. The converter must not use 128.
- `delta_com_an` and `minimum_com_limit` remain independent. Any specification-defined fallback is applied at runtime and is not written into `delta_com_an` during conversion.
- A missing required workbook row is a schema error; a blank is valid only for a documented optional field.

## Presentation boundary

93A and 178A use the same workbook presentation columns, including Parameter
Class, while retaining their own runtime field inventories. A shared layout
does not authorize copying 178A-only parameters into 93A.
