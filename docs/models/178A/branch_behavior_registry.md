# 178A 分支行為登錄表

狀態：**authoritative**  
最後核對：2026-11-05

本文件是 178A model 現有具名方法選擇及其分類審查候選的正式索引。新增、修改、重新命名、合併或移除 branch behavior 時，必須在同一變更中更新本文件。歷史 change contract 說明決策過程；本文件描述目前實作。

範圍包含 178A runtime 及其實際呼叫的 shared utility 分支；不把 178A 選項自動視為 93A 行為。若 93A 新增平行算法，應建立或更新對應的 `docs/models/93A/branch_behavior_registry.md`。

## 判定規則

branch behavior、一般 config、execution strategy、input boundary、固定行為與
provenance 的正式定義，見 [Branch behavior contract](../../architecture/branch_behavior_contract.md)。
本表以「可選控制項」作為 review umbrella；每個 ID 的前綴表示正式分類，號碼在同一分類內依
**最早 behavioral owner／consumer** 的 stage 排序。完全位於 COM pipeline 外的 shared utility、
input-boundary 或 orchestration control 列為 Stage 0；跨多 stage 的控制以最早 consumer 代表，
但 impact scope 必須列出全部 consumers。若後續 evidence 改變 scope，ID 允許隨 stage order 重排，
並須在同一變更同步本表、stage 文件及 legacy mapping。

一個 branch behavior 對應某個 coding layer 的一個 function set 分支，並可由一個或多個
RG fields 共同完整定義；RG 數量本身不是分支數量。即使兩組 RG 使用相同 dataclass 或數值
公式，只要它們由不同 function set 擁有、作用於不同 stage／impact boundary，仍是不同分支。

- `ALG` — `algorithm_policy`：相同物理輸入可選擇兩種以上具名數學或數值實作。
- `NUM` — `numerical_control`：精度、解析度、截斷、收斂或計算成本。
- `PHY` — `physical_input`／input boundary：描述 case 或輸入資料邊界。
- `SRC` — `block_source`：選擇 block 的資料／設計 artifact；目前 178A review set 無此類 ID。
- `SRCH` — `search`：搜尋目標、候選覆蓋與搜尋策略。
- `EXE` — `execution`：run extent、排程與 stage gate，不改已執行 stage 的公式。
- **輸入邊界**：描述 case 實際提供的資料範圍，不是算法分支。
- **固定行為**：目前只有一種合法值，不能宣稱為可切換分支。
- `execution_profile` 只在 workbook adapter 選取具名 preset；model 不讀取 selector。
- 所有 runtime 算法 policy 平放在 `COMConfig.policy: COMPolicyConfig`；不得為單一 stage 再加入 nested policy dataclass。

## Reference preset

`com_excel_io_178A._resolve_project_profile_178A()` 在建立 runtime config 前展開 preset。`project_standard` 使用專案標準方法，`custom` 讀取 workbook 明示的 legacy/advanced method，`sicopr_reference_v1` 使用下表的 reference 組合，並在 `COMConfig.policy.config_profile_overrides` 記錄 raw/effective 值。舊 `align_to_ref` 只作相容 alias。

| Runtime control | Project default | `sicopr_reference_v1` | Preset 是否控制 |
|---|---|---|---|
| `policy.channel_renormalization_order` | `sdd_first` | `s4p_first` | 是 |
| `policy.out_of_measured` | `cosine_decay` | `zero_padding` | 是 |
| `policy.ctle_pulse_realization` | `continuous_tf` | `bilinear_iir` | 是 |
| `policy.rxffe_record_realization` | `linear_convolution` | `finite_record_circshift` | 是 |
| `policy.eq_ch_imp_len` | `full` | `truncated` | 是；workbook 保留獨立控制 |
| `policy.num_trunc_ui` | `None` | `4096` | 是；只在 `truncated` 時適用 |
| `policy.pre_dte_adc_clipping_convention` | `annex_d3` | `matlab_4_17_reference_only` | 是 |
| `policy.final_com_vqc_convention` | `selected_phase_adc_input` | `sicopr_final_reconstruction` | 是 |
| `policy.pmf_projection_method` | `linear` | `nearest` | 是 |
| `policy.pdf_to_pmf_method` | `bin_integral` | `pmf_sample` | 是 |
| `policy.pmf_scaling_method` | `mass_deposit` | `interpolate_ordinates` | 是 |
| `numerical_control.final_pmf_grid.rule` | `relative_As_with_cap` | `relative_As` | 是 |
| `policy.final_adc_pmf_projection` | `annex_d3` | `reference_support` | 是 |
| `policy.gaussian_n_sigma_override` | `None` | `NormalDist().inv_cdf(1-DER_0)` | 是 |
| `policy.added_noise_pdf` | `gaussian_addition` | `scaled_total_pdf` | 是 |
| `policy.mlsd_quantization_psd` | `pre_dte_filtered` | `main_tap_white` | 是 |
| `policy.sequence_termination` | `fixed_length_sum` | `matlab_relative_tail` | 是 |
| `policy.reported_der` | `raw_sequence_sum` | `baseline_pdf_re_evaluation` | 是 |
| `execution.*.pre_dte_pmf_method` | profile 值 | `pmf_exact` | 是 |
| `execution.*.pmf_keep_mass` | profile 值 | `1.0` | 是 |
| `numerical_control.adc_input_pmf_grid.dy_override` | workbook 值 | `10e-6 V` | 是 |
| `numerical_control.final_pmf_grid.dy_override` | workbook 值 | `None` | 是 |
| `channel.sparam_frequency_limit_Hz` | case input | 不覆蓋 | 否 |
| `channel.missing_dc_policy` | project workbook default `skrf` | 不覆蓋 | 否 |
| `execution.*.floating_mode` | profile 值 | 不覆蓋 | 否 |
| `execution.*.pos_sweep_method/pos_coarse_stride` | profile 值 | 不覆蓋 | 否 |

`policy.applied_config_profile` 保存已套用 preset 的名稱；`policy.config_profile_overrides` 保存每個被覆蓋欄位的 raw value、effective value 與 preset 名稱。兩者只供 provenance/export 使用，model 不得以它們決定數值流程。

## Stage-by-stage selectable-control inventory

| ID | Class | Representative stage | Legacy ID | Control | Project default／alternate | Responsibility boundary |
|---|---|---|---|---|---|---|
| `PHY-001` | `physical_input` | Stage 0 — input boundary | B-019 | `channel.missing_dc_policy` | workbook `skrf`／constructor `error`；另有 `hold` | S-parameter ingestion owns missing-DC completion. It is not controlled by the execution profile and must not be mixed with out-of-measured high-frequency behavior. |
| `NUM-001` | `numerical_control` | Stage 0 — shared response utility | B-020 | `cascade_ir(..., force_grid=...)` | `True` keeps the original cfg and checks discarded tail／`False` keeps the complete linear record | `LinkSegment`／`SampledResponse` utility owns the grid result. No implicit COM regrid. Classification remains reviewable because this is not a Project Config field today. |
| `NUM-002` | `numerical_control` | Stage 0 — shared PMF utility | B-014 | `policy.gaussian_n_sigma_override` | config support／reference `NormalDist().inv_cdf(1-DER_0)` | Controls Gaussian support only; sigma, dy and tail-probability definitions remain unchanged. Earliest owner is the shared Gaussian PMF constructor. |
| `ALG-001` | `algorithm_policy` | Stage 0 — shared PMF utility | B-008 | `policy.pmf_projection_method` | `linear`／`nearest` | The projection operation receives the method explicitly; `Pmf1D` stores data, not policy. Applies only when an operation deposits onto a target grid. |
| `ALG-002` | `algorithm_policy` | Stage 0 — shared PMF utility | B-010/B-011 | `policy.pdf_to_pmf_method` | `bin_integral`／`pmf_sample` | Shared Gaussian/uniform PDF→PMF construction across pre-DTE, final COM and MLSD. Each distribution retains its own applicable rule. |
| `ALG-003` | `algorithm_policy` | Stage 0 — shared PMF utility | B-012 | `policy.pmf_scaling_method` | `mass_deposit`／`interpolate_ordinates` | Direct scalar-PMF resampling only. `mass_deposit` delegates grid placement to `ALG-001`; FIR tap construction does not receive this selector. |
| `EXE-001` | `execution` | Stage 0 — pipeline gate | E-001 | `COMRunConfig.target` | `mse/dfe/mlsd/full` | Selects run extent only; it does not change formulas in stages that execute. |
| `ALG-004` | `algorithm_policy` | Stage 1 — path construction | B-001 | `policy.channel_renormalization_order` | `sdd_first`／`s4p_first` | `_build_channel_under_test()` owns the ordered representation operations. Pending draft/reference evidence; `_build_path()` must not renormalize again. |
| `ALG-005` | `algorithm_policy` | Stage 1 — path construction | B-002 | `policy.out_of_measured` | `cosine_decay`／`zero_padding` | Applies only beyond the effective measured boundary of scalar `H_21`; it must not change `S_ch`, `S_all`, or the case frequency limit. |
| `ALG-006` | `algorithm_policy` | Stage 1 — path construction | B-003 | `policy.ctle_pulse_realization` | `continuous_tf`／`bilinear_iir` | CTLE pulse realization under shared-path construction; TX FFE and continuous VTF ownership remain separate. |
| `NUM-003` | `numerical_control` | Stage 2 — common impairment | B-005 | `policy.eq_ch_imp_len`, `policy.num_trunc_ui` | `full`／`truncated` | Shared L3 used by Stages 2, 3, 5 and 7. Only the PSD/correlation record may change; full responses, phase selection and channel grids remain unchanged. |
| `SRCH-001` | `search` | Stage 3 — phase scheduling | E-006 | `pos_sweep_method`, `pos_coarse_stride` | `each_phase`／`coarse_fine` | Selects evaluated phases; every visited candidate enters the same Stage 4 solver. |
| `ALG-007` | `algorithm_policy` | Stage 3 — per-phase ADC input | B-006 | `policy.pre_dte_adc_clipping_convention` | `annex_d3`／`matlab_4_17_reference_only` | Changes clipping PMF/tail convention and therefore `V_qc → delta → S_qn`; other jitter PSD remains RJ+DDJ. Pending D3p2 evidence. |
| `ALG-008` | `algorithm_policy` | Stage 3 — per-phase ADC input | E-002 | `pre_dte_pmf_method` | `gaussian_approx`／`pmf_exact` | Selects the approximate or complete PMF flow used to obtain ADC-input `V_qc`; reference profile selects exact. |
| `NUM-004` | `numerical_control` | Stage 3 — ADC-input PMF grid | E-003 | `numerical_control.adc_input_pmf_grid.*` | `relative_As`／`relative_As_with_cap` plus override | `_resolve_adc_input_pmf_config()` owns the ADC-input grid function set used by pre-DTE and selected-phase ADC-input PMF. It must not control the final domain. |
| `NUM-005` | `numerical_control` | Stage 6 — final PMF grid | B-013 | `numerical_control.final_pmf_grid.*` | `relative_As`／`relative_As_with_cap` plus override | `_resolve_final_com_pmf_config()` owns the final DFE/MLSD grid function set. It shares the control shape with NUM-004 but not its RG group or impact boundary. |
| `NUM-006` | `numerical_control` | Stage 3 — ADC-input PMF convergence | E-004 | `pmf_keep_mass` | `1-1e-5`／reference `1.0` | Controls ADC-input convolution retained mass only; it does not own grid spacing. |
| `ALG-009` | `algorithm_policy` | Stage 4 — MMSE DTE | E-005 | `floating_mode` | `heuristic/simplified/spec-defined` | `COM_MMSE_DTE.run()` selects the floating-tap/group solve flow; fixed tap limiter definition remains unchanged. |
| `ALG-010` | `algorithm_policy` | Stage 5 — post-FFE impairment | B-004 | `policy.rxffe_record_realization` | `linear_convolution`／`finite_record_circshift` | `_apply_rxffe_response()` owns the record realization; RX FFE taps, MMSE solve and pre-FFE response remain unchanged. |
| `ALG-011` | `algorithm_policy` | Stage 6 — DFE COM | B-007 | `policy.final_com_vqc_convention` | `selected_phase_adc_input`／`sicopr_final_reconstruction` | Controls final-COM clipping voltage convention only. Main-tap accumulation is the separate deferred issue below. Pending D3p2 evidence. |
| `ALG-012` | `algorithm_policy` | Stage 6 — final ADC PMF | B-015 | `policy.final_adc_pmf_projection` | `annex_d3`／`reference_support` | Final ADC quantization PMF only; reference support requires the reference final-`V_qc` convention and must not affect pre-DTE ADC. |
| `ALG-013` | `algorithm_policy` | Stage 7 — MLSD added noise | B-016 | `policy.added_noise_pdf` | `gaussian_addition`／`scaled_total_pdf` | `solve_g_an()` selects added-noise PDF construction; `S_isi` and `S_ni` definitions remain separate. |
| `ALG-014` | `algorithm_policy` | Stage 7 — MLSD noise PSD | B-021 | `policy.mlsd_quantization_psd` | `pre_dte_filtered`／`main_tap_white` | `build_mlsd_noise()` owns Eq. 178A-54 composition; MMSE noise, RxFFE taps, `S_an`, `S_isi` and DER solver remain unchanged. |
| `ALG-015` | `algorithm_policy` | Stage 7 — MLSD DER recurrence | B-017 | `policy.sequence_termination` | `fixed_length_sum`／`matlab_relative_tail` | `calculate_der_mlsd()` owns recurrence termination; the shared Eq. 178A-49 sign is not a branch. |
| `ALG-016` | `algorithm_policy` | Stage 7 — MLSD reported result | B-018 | `policy.reported_der` | `raw_sequence_sum`／`baseline_pdf_re_evaluation` | Changes reported DER formation only; raw sequence DER must remain separately recorded. |

`COMRunConfig.pmf_grid_quality` and `COMRunConfig.pmf_dy_override` remain legacy
compatibility fields only. Canonical effective grid fields are
`COMRunConfig.adc_input_pmf_grid` under `NUM-004` and
`COMRunConfig.final_pmf_grid` under `NUM-005`.

The former E-007 final-quantization tap-accumulation item has no selectable
runtime control, so it receives no selectable-control ID. It remains a deferred
technical issue: production ordering is frozen until PMF seed, main-tap
contribution, projection/support, and `ALG-012` interaction are resolved.

### Legacy ID mapping

| Legacy ID | Current ID | Note |
|---|---|---|
| B-001 / B-002 / B-003 | `ALG-004` / `ALG-005` / `ALG-006` | Stage 1 path construction |
| B-004 / B-005 / B-006 / B-007 | `ALG-010` / `NUM-003` / `ALG-007` / `ALG-011` | Reordered by earliest stage and class |
| B-008 | `ALG-001` | Stage 0 shared PMF utility |
| B-009 | — | Retired selector; historical ID only |
| B-010/B-011 | `ALG-002` | Merged shared PDF→PMF control |
| B-012 / B-013 / B-014 / B-015 | `ALG-003` / `NUM-005` / `NUM-002` / `ALG-012` | B-013 remains the independent Stage 6 final-grid function set |
| B-016 / B-017 / B-018 | `ALG-013` / `ALG-015` / `ALG-016` | Stage 7 ordering follows production flow |
| B-019 / B-020 / B-021 | `PHY-001` / `NUM-001` / `ALG-014` | Stage 0 input/utility plus Stage 7 PSD |
| E-001 / E-002 / E-003 / E-004 | `EXE-001` / `ALG-008` / `NUM-004` / `NUM-006` | Reclassified by actual function-set effect |
| E-005 / E-006 / E-007 | `ALG-009` / `SRCH-001` / — | E-007 is a deferred non-selectable issue |

## 不是分支的項目

| 項目 | 分類與原因 |
|---|---|
| `channel.sparam_frequency_limit_Hz` | **輸入邊界**。描述實際送入 reader 的有效量測上限；execution profile 不得把任意 100 GHz 檔案暗中裁成 67 GHz。`ALG-005` 只決定此邊界外如何處理。 |
| `policy.xtalk_pmf_accumulation` | **固定行為**。目前唯一合法值是 `pathwise_convolution`，沒有 A/B 分支能力；保留是待清理的 API 欄位。 |
| TX FFE discrete filter 與 `LinkSegment.cascade_ir()` | **等價實作**。對 oversampled pulse 做 shift-sum／convolution，不屬 CTLE branch。 |
| sinc／boxcar unit-pulse 表示 | **等價表示**。對齊 transfer function 與時間原點後不建立平行算法。 |
| RX package `reverse_ports()` | **共同正確流程**。die-to-channel network 建立後交換 two-port port orientation，不提供錯誤舊法作分支。 |
| Eq. 178A-49 `(-1)^(j+1)` | **共同公式修正**。不是 Annex/reference 平行方法。 |
| final quantization FIR 是否「包含 main tap」 | **不是 `ALG-011` 分支**。它是 PMF seed／FIR accumulation 的等價實作問題；目前 production ordering 依 deferred final-quantization accumulation issue 凍結。 |
| B-009 `interference_pmf_method` | **已移除的非必要分支**。`signal_fir` 與 `pam_atoms` 的差異源自過早 grid projection；固定採 exact PAM atoms → tap scaling → grid projection → convolution。Runtime config、preset 與 workbook 不再提供 B-009 selector。 |
| `SampledPSD.filtered_by()` grid matching | **固定 utility contract**。輸入 grid 不一致即由 caller 先處理；沒有隱藏 auto-regrid branch。 |

### `ALG-001`／retired B-009 coding-layer review

| Layer | Owner | Contract / review result |
|---|---|---|
| Project config | `COMPolicyConfig.pmf_projection_method` | `ALG-001` 保留唯一 workbook selector；SiCoPR preset 選 `nearest`，project default 為 `linear`。B-009 selector 已從 config、preset 與 runtime dispatcher 移除。 |
| Shared L3 function set | PMF construction across pre-DTE、selected-phase ADC-input、final COM | 各 stage 從同一 project policy 把 `projection_method` 明示傳入會重新投影 grid 的 helper；stage 不自行實作 `linear`／`nearest`。 |
| L4 model helper | `_build_pmf_pam_L()`、`_build_pmf_interference_178A()`、`_build_pmf_w_XT_all()` | PAM source 固定為 exact natural-grid atoms；interference helper 在 tap scaling 後明示 target-grid projection method。這些是無 COM instance state 的 pure auxiliary functions，因此保留為 module functions，而不是 `COM` methods。 |
| PMF utility | `Pmf1D._project_to_grid()`、`Pmf1D.multi_dirac()`、`Pmf1D.scale_x()`、`Pmf1D.resample_dx()`、`Pmf1D.fir_filter()` | Private `_project_to_grid()` 是唯一底層 projection decision point。`Pmf1D` 本身不保存 policy；`copy/shift/combine` 只處理資料。`ALG-003` 的 `interpolate_ordinates` 不呼叫 projection decision point。B-009 移除後只保留一個 public FIR-filter path。 |

Coding-layer conclusion: `ALG-001` 的 branch decision point 位於 PMF utility，model
layer 只負責在每個 projection operation 明示注入同一個 project policy；B-009 已不再形成
平行 call path。`tap_abs_th`／PMF retained-mass 等 numerical controls 是另一個
契約，不屬於 `ALG-001` placement 或已移除的 B-009 ordering。

## 實作入口與驗證證據

| 範圍 | 主要實作入口 | 主要驗證 |
|---|---|---|
| Preset 展開與 provenance | `io/com_excel_io_178A.py::_resolve_project_profile_178A()` | `tests/test_com_model_178A_policy_branches.py` |
| Channel renormalization | `models/com_178a/path_stage.py::_build_channel_under_test()` + `utilities/sparam.py` 的具名 representation methods | `tests/test_channel_renormalization.py`、`tests/test_sparam_synthetic_s4p.py` |
| High-frequency handling | `SparamModel.to_LinkSegment()`、`utilities/link.py::resample_tf()` | `tests/test_sparam_out_of_measured.py` |
| CTLE pulse realization | `_build_shared_path()`、`_prepare_ctle_pulse_realization()`、`_realize_ctle_pulse_for_path()` | `tests/test_com_model_178A_ctle_pulse.py` |
| RX FFE record | `_apply_rxffe_response()` | `tests/test_com_model_178A_post_ffe.py`、CTLE pulse tests |
| Eq-channel impairment record／MMSE inputs | `COM._realize_eq_ch_imp_record()`、`COM._build_eq_ch_imp_psd()`；Stage 3 `_select_xtalk_path_phase()` | policy tests、`tests/test_com_model_178A_mlsd_noise.py` |
| PMF branches | `_build_pmf_interference_178A()`、`_build_pmf_G()`、ADC/final PMF builders | `tests/test_pmf_reference_methods.py`、policy tests |
| MLSD branches | `solve_g_an()`、`build_mlsd_noise()`、`calculate_der_mlsd()`、`calculate_COM_MLSD()` | `tests/test_com_model_178A_mlsd_flow.py`、`test_com_model_178A_mlsd_noise.py`、`test_com_model_178A_mlsd_eq47.py` |
| Fixed-grid cascade | `utilities/link.py::LinkSegment.cascade_ir()`、`SampledResponse.cascade_ir()` | `tests/test_fixed_grid_contract.py` |

## 維護檢查表

任何 branch change 必須在同一變更中完成：

1. 更新本文件的 preset matrix、branch row、責任邊界與驗證連結。
2. 若 runtime field 改變，更新 `config_tree.md`；若 stage call flow 改變，更新 `call_tree.md` 與相應 stage 文件。
3. 明確分類為算法分支、執行分支、輸入邊界或固定行為。
4. 寫出 project default、所有合法 alternate、哪些 versioned execution profiles 會覆蓋，以及互相依賴的欄位。
5. 列出會改變與不得改變的中間量，並提供 branch isolation test。
6. 新增 reference-only 分支時保留 general method，不得用 reference 接近度取代公式正確性判定。
7. 若發現 general method 錯誤，依 Core Model Change Contract 直接修正共同流程，不保留已知錯誤作平行分支。
