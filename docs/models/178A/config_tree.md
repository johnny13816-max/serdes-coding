# 178A configuration tree

Ad Hoc source interpretation, conditional requiredness, and GUI review follow
[the mapping contract](../../architecture/adhoc_mapping_contract.md) and its
[field table](../../architecture/adhoc_mapping_fields.md). Source-derived values
and project policy defaults are separate review areas. Package submodule enable
extensions are deferred to the separate core contract described there.

> This is the 178A-specific inventory of project fields and typed runtime ownership. It does not define model equations. Project-wide rules are in [configuration architecture](../../architecture/configuration_architecture.md).

## Configuration layers after CFG-178A-F

```text
CASE_CONFIG
└── case identity and provenance
FIXED_CONFIG
├── intrinsic                         physical inputs; class may be intrinsic/derived
├── algorithm_policy                  ALG selector rows
└── numerical_control                 NUM rows
CHANNELS
└── block_source                      path / representation metadata
SEARCH_CONFIG
└── search                            candidate values and retention
RUN_CONFIG
├── algorithm_policy                  facade selector / floating method
├── numerical_control                 per-run PMF convergence input
├── search                            phase coverage and outer orchestration
└── execution                         target only
```

`search_sweep` is the first step of `search_run`; `search_final` evaluates
retained candidates.  These workbook rows are adapter inputs that resolve
algorithm, numerical, search, and execution values before a `COMConfig` is
constructed.  They are not one runtime `execution` object. Search ranges stay
in `search_config`.

## Runtime dataclass tree

Every 178A-owned config dataclass defines a semantic `to_string()`/`print()`
view with explicit engineering units and bounded array summaries. The common
formatter owns layout only; each class owns its field selection, order, labels,
stored/display units, and conversions. See
[COM dataclass 文字介面契約](../../architecture/dataclass_text_contract.md).

### Current implementation after CFG-178A-F

```text
COMConfig
├── physical root fields and leaf dataclasses
├── channel: COMChannelConfig
│   ├── R0 / R_d_tx / R_d_rx
│   ├── gamma_src / gamma_load              construction-derived
│   └── sparam_frequency_limit_Hz            measured-data boundary
├── src: COMSourceConfig
│   └── channel
│       ├── victim: ChannelBinding
│       ├── next: tuple[ChannelBinding, ...]
│       └── fext: tuple[ChannelBinding, ...]
│           └── each binding: path / representation / port_order
├── pmf: COMPMFConfig
├── alg: COMAlgorithmPolicyConfig
│   └── missing_dc_policy                    ALG-001
├── num: COMNumericalControlConfig
├── srch: COMSearchConfig
│   ├── TX FFE / CTLE scalar-or-vector candidate axes
│   ├── pos_sweep_method / pos_coarse_stride
│   ├── result-retention controls
│   └── group_size / final_top_k
├── exe: COMExecutionConfig
│   └── target
└── mlsd: COMMLSDConfig
```

ALG/NUM/SRCH/EXE/SRC runtime boundaries are implemented. `COMRunConfig` and
`COMRunProfiles` are adapter-only workbook compatibility objects and never
enter `COMConfig` or Stage 1--7. Profile resolution metadata is not a runtime
config field; `to_export_dict()` emits the adapter's private resolution record
separately from `config` and `derived`.

### Approved target after CFG-178A-B through F

Project Config uses the full classification names. Runtime grouped-field names
use the registered lower-case prefixes:

```text
COMConfig
├── L
├── DER_0
├── link: LinkConfig
├── filter: COMFilterConfig
├── channel: COMChannelConfig           physical conditions / input boundary
├── txpkg_victim: COMPkgConfig
├── txpkg_fext: COMPkgConfig
├── txpkg_next: COMPkgConfig
├── rxpkg: COMPkgConfig
├── dte: COMDTEConfig
├── imp: COMImpairmentConfig
├── mlsd: COMMLSDConfig
├── src: COMSourceConfig                SRC / block_source
│   ├── channel.victim
│   ├── channel.next
│   └── channel.fext
├── alg: COMAlgorithmPolicyConfig       ALG / algorithm_policy
├── num: COMNumericalControlConfig      NUM / numerical_control
├── srch: COMSearchConfig               SRCH / search
└── exe: COMExecutionConfig             EXE / execution
    └── target
```

There is no `cfg.intrinsic`, `cfg.phy`, `cfg.provenance`, or `cfg.derived`.
Intrinsic physical inputs keep their direct paths. Construction-derived values
stay in the owning dataclass; runtime-derived values stay with their owner or
status; profile/source history stays in adapter/report metadata.

`COMSearchConfig` is the only SRCH dataclass. At the Project Config/job
boundary, candidate fields may be scalar or non-empty one-dimensional vectors.
The outer runner normalizes axes and expands their Cartesian product. A product
of one uses the single-run path; a larger product uses sweep/ranking/final
orchestration. Every `COM` instance still receives one resolved scalar
candidate. Stage 3 reads only its sampling-phase search controls.

The grouped `COMRunProfiles` is adapter-internal: it reads the three workbook
profiles before `run_mode` selects one profile and flattens its ALG/NUM/EXE
values. It is never stored in `COMConfig` or passed through Stage 1--7.
Production search planning/finalization reads orchestration values from
`COMSearchConfig`.

`excel_to_config_178A(..., run_mode=...)` reads `fixed_config`, `run_config`, and
`channels`, then selects exactly one of `single_run`, `search_sweep`, or
`search_final` before constructing `COMConfig`. Each result includes the same
canonical `cfg.srch`; single-run mode scalarizes it to the physical filter,
while search modes retain the workbook axes for the outer runner.
`excel_to_search_config_178A()` remains a compatibility reader for the same
dataclass and is not a second production source.

## Case config

| Workbook field | Purpose | Runtime mapping |
|---|---|---|
| `case_id` | Case-folder identity | None |
| `source_config` | External workbook provenance | None |
| `source_note` | Human-readable conversion note | None |

The template leaves `Parameter Class` blank for these rows and identifies them by
the `case` domain. They belong to case metadata and do not enter `COMConfig`.

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

The `Runtime owner` column below records the current production path until its
own approved migration slice completes. The canonical target is `cfg.alg` for
ALG controls and `cfg.num` for NUM controls; the exact field-by-field slice is
listed in [the migration contract](../../planning/comconfig_domain_migration.md#field-migration-inventory).

| Field（舊欄位保留讀取相容） | Runtime owner | Default |
|---|---|---:|
| `adc_input_pmf_grid.rule` | `COMConfig.num.adc_input_pmf_grid` | `relative_As_with_cap` |
| `adc_input_pmf_grid.dy_rel_As` | same | 0.001 |
| `adc_input_pmf_grid.dy_abs_max` | same | 1e-5 V |
| `adc_input_pmf_grid.dy_override` | same | blank / `None` |
| `final_pmf_grid.rule` | `COMConfig.num.final_pmf_grid` | `relative_As_with_cap` |
| `final_pmf_grid.dy_rel_As` | same | 0.001 |
| `final_pmf_grid.dy_abs_max` | same | 1e-5 V |
| `final_pmf_grid.dy_override` | same | blank / `None` |
| `tap_rel_As` | `COMPMFConfig` | 0.001 |
| `missing_dc_policy` | `COMChannelConfig` | `skrf`; reference profile selects `mag_phase_trend_to_dc` |
| `execution_profile` | `run_config.control`；adapter preset selector，不進入 `COMConfig` | `project_standard` |
| `align_to_ref` | legacy compatibility alias；新模板不輸出 | absent |
| `out_of_measured` | `COMConfig.alg` | `cosine_decay` |
| `pre_dte_adc_clipping_convention` | `COMConfig.alg` | `full_jitter_half_tail` |
| `final_com_vqc_convention` | `COMConfig.alg` | `selected_phase_adc_input` |
| `ctle_pulse_realization` | `COMConfig.alg`（workbook 不單獨曝露） | `continuous_tf` |
| `rxffe_record_realization` | `COMConfig.alg`（workbook `fixed_config` 可明示；profile 可覆蓋） | `linear_fixed_grid` |
| `eq_ch_imp_len` | `COMConfig.num`（workbook 獨立曝露） | `full` |
| `num_trunc_ui` | `COMConfig.num`（僅 `truncated` 適用） | blank / `None` |
| `pmf_projection_method` | `COMConfig.alg`（workbook 獨立曝露） | `linear` |
| `pdf_to_pmf_method` | `COMConfig.alg`（由 profile 或 Python 設定） | `bin_integral` |

The eight grid fields have primary domain `numerical_control`, exposure
`advanced`, effect `accuracy/cost`, and workbook class `policy`. Their owners
are `_resolve_adc_input_pmf_config()` and `_resolve_final_com_pmf_config()`;
raw/effective/profile provenance is exported. An override must be finite and
positive and has priority over both derived rules. The ADC-input family covers
pre-DTE and selected-phase ADC-input PMFs only; the final family covers final
DFE/MLSD PMFs only. The legacy shared `dy_rel_As`, `dy_abs_max`,
`run_config.*.pmf_grid_quality`, and `run_config.*.pmf_dy_override` remain
read-compatible but are not emitted by new templates.

All remaining PMF controls and `missing_dc_policy` are labeled `policy`. There is
no `quantization_vqc_method` or `pre_dte_pmf_method` row in the 178A project
template. Pre-DTE ADC-input clipping uses the fixed exact-PMF flow owned by
`_build_psd_adc_qn()`; a legacy workbook row is accepted only when its value is
`pmf_exact`.

`run_config.control.execution_profile` 是新版 178A 模板的 facade selector；
合法值為 `project_standard`、`sicopr_reference_v1`、`custom`。NUM-003 的
`eq_ch_imp_len`／`num_trunc_ui` 保留為 workbook 獨立控制，不從 Ad Hoc 映射；
其他未曝露的底層 method controls 由 profile 展開。
`project_standard` 使用專案預設，
`custom` 讀取 workbook 明示的 advanced/legacy method；`sicopr_reference_v1` 由
`com_excel_io_178A` 在建構 runtime config 前展開為 SiCoPR／MATLAB 4.17
具名方法：`mag_phase_trend_to_dc`、`zero_padding`、`bilinear_iir`、
`finite_record_circshift`、pre-DTE/final ADC reference 分支，
`truncated` eq-channel impairment record（本案 4096 UI）、
以及 `COMAlgorithmPolicyConfig` 中的離散 tap 最近格點、原子干擾卷積、逐路徑
XT、Gaussian grid sampling（支撐範圍由 `NormalDist().inv_cdf(1-DER_0)`
決定）、uniform 最近端點、ordinate interpolation、reference support 與
relative-`As` final grid。`COMConfig` 不保留此 boolean；model 只讀上述
具名值。Reference profile 在 adapter 固定 exact PMF、`keep_mass=1`，將
ADC-input family 的 explicit `dy_override` 設為 `10e-6 V`，並將 final family
設為 `relative_As`、final override 留空。Final COM／MLSD 因此仍在專案未正規化
RX FFE 電壓座標使用 `dy_rel_As*As`，相當於 SiCoPR 主 tap 正規化後的 `dy`
乘回主 tap gain。
舊 workbook 的 `align_to_ref` 與仍受支援的個別欄位可讀；legacy boolean 為 `True` 時
等價於 `sicopr_reference_v1`，為 `False` 且存在個別 method 時等價於 `custom`。
Reference profile 以 preset 覆蓋；adapter 的 export-only
`adapter_resolution` 記錄 profile 與 raw/effective 值，不進入 `cfg.alg`。
此模式只供 reference 比對，不宣稱為 178A 通用方法。

`ctle_pulse_realization="bilinear_iir"` 是完整且不可拆分的 pulse-realization
方法：measured composite pre-CTLE TF、reference frequency grid、raw IFFT、
停用 causality correction、固定 `1e-3` peak 截尾、兩級 bilinear IIR 與一 UI
unit pulse。這些步驟沒有額外 config 欄位。`rxffe_record_realization` 是另一個
Stage 5 post-FFE record policy：`linear_fixed_grid` 保留 run grid 與 overflow guard；
`linear_expanded_grid` 建立足以容納完整 linear convolution 的共同 response grid；
`finite_record_circshift` 在原有限 record 做 shift-sum，供 reference preset 使用。
Stage 5 為唯一 branch owner，Stage 6 DFE 與 Stage 7 MLSD 只消費 status 中已解析的
response／PSD record grid。`num.eq_ch_imp_len`（NUM-003）仍獨立決定 full 或
truncated PSD/correlation record，不改變 ALG-011 的 response realization。

`out_of_measured` 控制 terminated scalar `H_21` 從量測 S-parameter grid
轉到 analysis grid 時的頻帶外處理。`cosine_decay` 保留原本的 cosine
衰減；`zero_padding` 僅在輸入的最高量測頻點以上補零。victim、NEXT、
FEXT 與 victim TX-noise equivalent channel 使用同一政策。analysis-grid
`H_21` 經 `LinkSegment.from_tf()`，bilinear finite record 經
`_reference_fd_to_td_record()`；兩者都將數值操作委派給 `resample_tf()`，
不修改 `S_ch` 或 `S_all` 矩陣。有效量測上限由
`COMChannelConfig.sparam_frequency_limit_Hz` 決定；
`zero_padding` 從該有效上限之後生效。Akinwale case 的六個原始 S4P 都到
100 GHz，而 Ad Hoc `flim=67 GHz` 會映射為 case-level
`sparam_frequency_limit_GHz=67`。一般模板留白，execution profile 本身不強制
任何固定頻率。

`channel_renormalization_order` 已從 `COMAlgorithmPolicyConfig`、profile 與 workbook
mapping 移除。舊 workbook 若仍帶此欄位會收到明確 migration error。178A
由 `_build_channel_under_test()` 依 Touchstone port count dispatch：measured S4P
固定先對完整 single-ended 四埠 renormalize 至 `R_0`，再取 Sdd；native
differential S2P 才直接 renormalize 至 `2R_0`。這是 D3.2 固定流程與 input
format contract，不是 selectable policy，也不改變 93A。

`pre_dte_adc_clipping_convention` 只控制 MMSE 前 ADC clipping 的
Gaussian noise sigma 與 CDF 左尾門檻。`full_jitter_half_tail` 是 D3.2
確認的專案預設：clipping Gaussian 含完整 jitter，左尾 `P_qc/2`。
`rj_only_full_tail_reference` 供 SiCoPR／COM MATLAB 4.17 對照：clipping
Gaussian 僅含 random jitter，左尾 `P_qc`。兩者送入 MMSE 的 jitter
PSD 仍含 random jitter 與 DDJ；切換只經 `V_qc → S_qn` 改變 `R_n`。
後續 selected-phase final COM 會另外建立 ADC-input PMF，此欄位不
控制該階段。它仍可能透過 selected phase／DTE taps 間接影響後續 COM；
reference-only 分支不是 general method。詳見 [TC-017](../../planning/tc017_pre_dte_adc_clipping_reference.md)。

`final_com_vqc_convention` 獨立選擇 final DFE COM 的 clipping-voltage
來源，不改 pre-DTE `S_qn`、MMSE 或 post-FFE reporting PSD。
`selected_phase_adc_input` 沿用 Stage 5 exact selected-phase ADC-input
`V_qc`／`delta`。`sicopr_final_reconstruction` 以 pre-FFE victim signal
與除以 RX FFE 主 tap gain 的 post-FFE ISI／XT／DDJ／Gaussian PMF
重建 final clipping input，取左尾 `P_qc` 得
`V_qc`／`delta`。ALG-012 到此為止，不定義後續量化 PMF 的 RX FFE
main-tap accumulation；該實作問題已另列 deferred issue。此分支在
D3p2 evidence 到手前維持 pending；pre-DTE 與 final-COM clipping policy
仍可獨立設定。

`pdf_to_pmf_method` 是 ALG-003 的 shared L3 policy。值
`bin_integral` 以 distribution 的 bin probability/overlap 建立 PMF；
`pmf_sample` 則使用 SiCoPR 的 grid-center rule：Gaussian sample 後
正規化，uniform 選取 `±delta/2` 的最近 centers（含端點）並等權重。
`COM` orchestration 將此值明示傳入 pre-DTE、final COM、MLSD 的 L2
helpers；`Pmf1D` 只執行建構，不保存 policy。178A Gaussian support 固定為
internal 8σ invariant；`pdf_to_pmf_method` 不能改變 support。

## Channels

The `channels` sheet provides one victim and indexed NEXT/FEXT rows, with the
legacy `S4P Path` column, port order, and enable/use state. The adapter maps each
enabled row to `cfg.src.channel` as a `ChannelBinding`; the existing column may
identify a supported S4P or native differential S2P artifact, and representation
is validated independently for each file. `R_0`, `R_d_tx`, `R_d_rx`, and the
measured frequency limit map to physical `cfg.channel`. `missing_dc_policy` maps
to `cfg.alg`. Every package `R0` remains required and the adapter rejects any
package/channel `R0` mismatch. CFG-D does not rename workbook columns.

## Search config

| Workbook parameter | Runtime field | Meaning |
|---|---|---|
| `c_m2`, `c_m1`, `c_1` | `c_m2_values`, `c_m1_values`, `c_1_values` | TX FFE candidate sequences |
| `g_1`, `g_2` | `g_DC_values`, `g_DC2_values` | 178A CTF gain candidate sequences |
| `keep_top_n` | `keep_top_n` | Retained successful result count |
| `keep_all_rows` | `keep_all_rows` | Result retention behavior |
| `continue_on_error` | `continue_on_error` | Candidate error handling |
| `run_config.search.group_size` | `group_size` | Candidates per partial-search group |
| `run_config.search.top_k` | `final_top_k` | Candidates receiving full final evaluation |

Fixed baselines and search candidates are separate. The current fixed baselines for `c_m2`, `c_m1`, `c_1`, `g_1`, and `g_2` are zero.

## Execution policy (`run_config`)

| Profile | Purpose |
|---|---|
| `control.execution_profile` | Workbook facade preset: `project_standard`, `sicopr_reference_v1`, or `custom` |
| `single_run` | Manual single execution |
| `search_sweep` | First step of `search_run`; candidate evaluation |
| `search_final` | Second step; final evaluation of retained candidates |
| `search` | Adapter input for outer `COMSearchConfig.group_size/final_top_k`; not a simulator-runtime owner |

Each canonical run profile supplies `target`, `pmf_keep_mass`, `floating_mode`, `pos_sweep_method`, and
`pos_coarse_stride`. Grid values come from the two fixed-config
`numerical_control` families rather than duplicated run rows. The existing
`execution_profile` expands effective controls: project standard uses accurate
ADC-input grids for single/final evaluation and relative-only grid for search
sweep; the reference preset uses explicit ADC-input `10 µV` and final
`relative_As`. Final COM still keeps all PMF mass (`keep_mass=1`) independently
of the selected grid family.

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
