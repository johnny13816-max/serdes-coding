# 178A 分支行為登錄表

狀態：**authoritative**  
最後核對：2026-10-15

本文件是 178A model 所有平行算法、數值策略與執行策略的正式索引。新增、修改、重新命名、合併或移除分支時，必須在同一變更中更新本文件。歷史 change contract 說明決策過程；本文件描述目前實作。

範圍包含 178A runtime 及其實際呼叫的 shared utility 分支；不把 178A 選項自動視為 93A 行為。若 93A 新增平行算法，應建立或更新對應的 `docs/models/93A/branch_behavior_registry.md`。

## 判定規則

- **算法分支**：相同物理輸入可選擇兩種以上具名數學或數值實作。
- **執行分支**：改變搜尋、精度或計算成本，但不重新定義物理輸入。
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
| `policy.noise_grid_method` | `analysis_grid` | `fixed_ui` | 是 |
| `policy.noise_grid_num_ui` | `None` | `4096`；`custom` 可由 legacy／advanced row 指定 | 是 |
| `policy.pre_dte_adc_clipping_convention` | `annex_d3` | `matlab_4_17_reference_only` | 是 |
| `policy.final_adc_quantization_convention` | `annex_d3` | `matlab_4_17_reference_only` | 是 |
| `policy.discrete_pmf_placement` | `linear` | `nearest` | 是 |
| `policy.interference_pmf_method` | `signal_fir` | `pam_atoms` | 是 |
| `policy.gaussian_pmf_method` | `bin_integral` | `reference_sample` | 是 |
| `policy.uniform_pmf_method` | `bin_integral` | `nearest_centers` | 是 |
| `policy.pmf_scaling_method` | `mass_deposit` | `interpolate_ordinates` | 是 |
| `policy.final_pmf_grid` | `fine` | `relative_As` | 是 |
| `policy.final_adc_pmf_projection` | `annex_d3` | `reference_support` | 是 |
| `policy.gaussian_n_sigma_override` | `None` | `NormalDist().inv_cdf(1-DER_0)` | 是 |
| `policy.added_noise_pdf` | `gaussian_addition` | `scaled_total_pdf` | 是 |
| `policy.mlsd_quantization_psd` | `pre_dte_filtered` | `main_tap_white` | 是 |
| `policy.sequence_termination` | `fixed_length_sum` | `matlab_relative_tail` | 是 |
| `policy.reported_der` | `raw_sequence_sum` | `baseline_pdf_re_evaluation` | 是 |
| `execution.*.pre_dte_pmf_method` | profile 值 | `pmf_exact` | 是 |
| `execution.*.pmf_grid_quality` | profile 值 | `fine` | 是 |
| `execution.*.pmf_keep_mass` | profile 值 | `1.0` | 是 |
| `execution.*.pmf_dy_override` | profile 值 | `None` | 是 |
| `channel.sparam_frequency_limit_Hz` | case input | 不覆蓋 | 否 |
| `channel.missing_dc_policy` | project workbook default `skrf` | 不覆蓋 | 否 |
| `execution.*.floating_mode` | profile 值 | 不覆蓋 | 否 |
| `execution.*.pos_sweep_method/pos_coarse_stride` | profile 值 | 不覆蓋 | 否 |

`policy.applied_config_profile` 保存已套用 preset 的名稱；`policy.config_profile_overrides` 保存每個被覆蓋欄位的 raw value、effective value 與 preset 名稱。兩者只供 provenance/export 使用，model 不得以它們決定數值流程。

## 算法分支

| ID | Stage | Runtime control | Project default | Alternate/reference 行為 | 責任邊界與不得影響項目 |
|---|---|---|---|---|---|
| B-001 | Channel ingestion | `policy.channel_renormalization_order` | `sdd_first`：先取 Sdd，再 renormalize differential two-port | `s4p_first`：先將完整 single-ended four-port renormalize 至 `R_0`，再依 `port_order` 取 Sdd | 數值操作只屬 `SparamModel.from_touchstone()/from_network()`。COM orchestration 只傳選項；不得在 `_build_path()` 再交換 port 或再次 renormalize。 |
| B-002 | S-parameter → scalar transfer | `policy.out_of_measured` | `cosine_decay`：在量測上限外做 cosine decay，phase linear extrapolation | `zero_padding`：量測上限以上的 scalar `H_21` 為零 | 屬 `SparamModel.to_LinkSegment()`／link resampling 邊界。不得修改 `S_ch`、`S_all` 或暗中改變量測上限。victim/NEXT/FEXT 共用。 |
| B-003 | Pre-CTLE response → pulse | `policy.ctle_pulse_realization` | `continuous_tf`：連續頻域 CTF 乘入等效 transfer function | `bilinear_iir`：measured composite TF → reference grid → raw IFFT → `1e-3` peak 截尾 → bilinear IIR → unit pulse | `_realize_ctle_response()` 擁有整個 realization。TX FFE 不屬此分支；連續 VTF `H_all` 不因 pulse realization 改寫。 |
| B-004 | Post-FFE record | `policy.rxffe_record_realization` | `linear_convolution`：固定 grid linear convolution，保留 overflow guard | `finite_record_circshift`：在既有有限 impulse record 上做 tap shift-sum | `_apply_rxffe_response()` 擁有 record 邊界。不得改變 RX FFE taps、MMSE 解或原始 pre-FFE response。 |
| B-005 | MMSE noise PSD/correlation | `policy.noise_grid_method`, `noise_grid_num_ui` | `analysis_grid`：使用 `LinkConfig` 的 sampled grid | `fixed_ui`：使用指定的偶數 UI record；reference case 為 4096 UI | `COMPolicyConfig.resolve_noise_grid()/fit_noise_response()` 只控制 noise DFT record、PSD 與 `R_n`。不得改變 channel/pulse analysis grid 或 `h_dsamp`。 |
| B-006 | Pre-DTE ADC clipping | `policy.pre_dte_adc_clipping_convention` | `annex_d3`：完整 jitter，CDF tail=`P_qc/2` | `matlab_4_17_reference_only`：clipping PMF 使用 RJ-only，CDF tail=`P_qc` | `calculate_pre_dte_imp_at_pos()`、`_calculate_V_qc*()`、`_build_psd_adc_qn()`。只經 `V_qc → delta → S_qn` 影響 MMSE `R_n`；其他 jitter PSD 仍含 RJ+DDJ。 |
| B-007 | Final COM ADC quantization | `policy.final_adc_quantization_convention` | `annex_d3`：selected-phase delta 與全部 FFE taps | `matlab_4_17_reference_only`：重建 final clipping PMF，略過主 tap | `calculate_COM_DFE()`／`_final_adc_clip_reference_only()`。與 B-006 是不同 stage，不得共用一個隱含 clipping 開關。 |
| B-008 | Discrete-amplitude PMF creation | `policy.discrete_pmf_placement` | `linear`：質量線性分配至相鄰格點 | `nearest`：質量放入最近格點 | 只在離散 amplitude/tap PMF 的建立者使用；不得改成 `Pmf1D` 所有操作的全域量化規則。 |
| B-009 | Interference PMF representation | `policy.interference_pmf_method` | `signal_fir`：由 signal PMF 經 tap FIR 建構 | `pam_atoms`：直接用 PAM amplitude atoms 卷積 | `_build_pmf_interference_178A()` 與 ADC/final PMF builders 選擇表示法；generic PMF utility 只執行被指定的 primitive。 |
| B-010 | Gaussian PMF creation | `policy.gaussian_pmf_method` | `bin_integral`：以 bin probability 積分 | `reference_sample`：在 grid centers 取樣後正規化 | `_build_pmf_G()` 及各 stage Gaussian builder。不得同時暗改 support；support 由 B-014 獨立控制。 |
| B-011 | Uniform PMF creation | `policy.uniform_pmf_method` | `bin_integral` | `nearest_centers` | 只影響 quantization uniform PMF 的離散化；不改 ADC step `delta`。 |
| B-012 | PMF amplitude scaling | `policy.pmf_scaling_method` | `mass_deposit`：縮放後重新 deposit probability mass | `interpolate_ordinates`：在縮放座標上插值 ordinates | `Pmf1D.scale_x()` 的呼叫者明示方法。不得作為通用隱藏 default 影響未選取的 stage。 |
| B-013 | Final COM/MLSD PMF grid | `policy.final_pmf_grid` | `fine`：`min(dy_abs_max, dy_rel_As*As)` | `relative_As`：使用 `dy_rel_As*As` | `_resolve_final_com_pmf_config()` 擁有 final-domain grid。pre-DTE grid 仍由 run config 與 `_resolve_adc_input_pmf_config()` 控制。 |
| B-014 | Gaussian support | `policy.gaussian_n_sigma_override` | `None`：使用 `COMPMFConfig.gaussian_n_sigma` | reference preset：`NormalDist().inv_cdf(1-DER_0)` | 只控制 Gaussian PMF support；不改 sigma、dy 或 tail probability 定義。 |
| B-015 | Final ADC PMF projection | `policy.final_adc_pmf_projection` | `annex_d3` | `reference_support`：reference support/tap projection | 只在 final ADC quantization PMF 生效，且必須搭配 B-007 reference convention；不得影響 pre-DTE ADC。 |
| B-016 | MLSD added-noise PDF | `policy.added_noise_pdf` | `gaussian_addition`：依 Annex 加入 Gaussian component | `scaled_total_pdf`：縮放完整 DFE PDF 後求 `g_an` | `solve_g_an()` orchestration 選 `_build_scaled_total_pdf_added_noise()` 或 Annex flow。不得改 `S_isi`、`S_ni` 的定義。 |
| B-017 | MLSD sequence termination | `policy.sequence_termination` | `fixed_length_sum`：固定 `trunc_len` 的 sequence contribution sum | `matlab_relative_tail`：reference CDF 與獨立 truncation-tail realization | `calculate_der_mlsd()` 擁有 sequence recurrence/truncation。Eq. 178A-49 的 `(-1)^(j+1)` 是共同正確公式，不是分支。 |
| B-018 | MLSD reported DER | `policy.reported_der` | `raw_sequence_sum` | `baseline_pdf_re_evaluation`：以算得的 MLSD increment 回到 baseline DFE PDF 評估 reported DER | `calculate_COM_MLSD()` 只改報告值的形成；raw sequence DER 必須另行保存，不能覆寫。 |
| B-019 | Missing DC handling | `channel.missing_dc_policy` | project workbook：`skrf`；dataclass constructor default：`error` | `hold` 或其他合法 reader policy | S-parameter ingestion/extrapolation 擁有 DC 缺口處理。Execution profile 不控制；不得混入高頻 B-002。 |
| B-020 | Utility time-domain cascade | `cascade_ir(..., force_grid=...)` | COM 正式路徑使用 `True`：回到原 cfg，檢查 discarded tail | `False`：保留完整 linear-convolution record/grid | 屬 `LinkSegment`／`SampledResponse` utility。COM 不得偷偷 regrid；固定 grid overflow 目前依既有契約處理。 |
| B-021 | MLSD quantization PSD | `policy.mlsd_quantization_psd` | `pre_dte_filtered`：完整 pre-DTE `S_n` 經完整 `|H_rxffe|²` | `main_tap_white`：非量化噪聲經完整 `|H_rxffe|²`，`S_qn` 保持 white 並只乘 `|w[d_w]|²` | `build_mlsd_noise()` 擁有 Eq. 178A-54 組合邊界。不得改 MMSE 的 `S_qn/R_n`、RxFFE taps、`S_an`、`S_isi` 或 DER solver。MLSD status 必須保存實際使用的 `S_qn`。 |

## 執行與數值分支

| ID | Stage | Control | Default／選項 | 責任邊界 |
|---|---|---|---|---|
| E-001 | Pipeline gate | `COMRunConfig.target` | `dfe`；可選 `mse/dfe/mlsd/full` | 只決定執行到哪個 stage，不改已執行 stage 的公式。 |
| E-002 | Pre-DTE ADC | `pre_dte_pmf_method` | `gaussian_approx`／`pmf_exact` | 選擇 `V_qc` 的近似或完整 PMF flow；reference preset 選 exact。 |
| E-003 | PMF grid quality | `pmf_grid_quality` | `fine`；search sweep 可用 `coarse` | 交由 PMF config resolver 決定 dy；不得改物理公式。 |
| E-004 | PMF numerical convergence | `pmf_keep_mass`, `pmf_dy_override` | `1-1e-5`, `None` | 控制截尾與明示 dy。override 非空時直接取代 derived dy；reference preset 使用 `keep_mass=1`、`dy_override=None`。 |
| E-005 | Floating FFE solve | `floating_mode` | `heuristic`；另有 `simplified/spec-defined` | `COM_MMSE_DTE.run()` 選 floating tap/group flow；不改固定 tap limiter 定義。 |
| E-006 | Sampling-phase search | `pos_sweep_method`, `pos_coarse_stride` | `each_phase`, `4`；另有 `coarse_fine` | `_initial_pos_sweep_indices()`／`_fine_pos_sweep_indices()` 只決定評估哪些 phase；每個候選仍送相同 MMSE solver。 |

## 不是分支的項目

| 項目 | 分類與原因 |
|---|---|
| `channel.sparam_frequency_limit_Hz` | **輸入邊界**。描述實際送入 reader 的有效量測上限；execution profile 不得把任意 100 GHz 檔案暗中裁成 67 GHz。B-002 只決定此邊界外如何處理。 |
| `policy.xtalk_pmf_accumulation` | **固定行為**。目前唯一合法值是 `pathwise_convolution`，沒有 A/B 分支能力；保留是待清理的 API 欄位。 |
| TX FFE discrete filter 與 `LinkSegment.cascade_ir()` | **等價實作**。對 oversampled pulse 做 shift-sum／convolution，不屬 CTLE branch。 |
| sinc／boxcar unit-pulse 表示 | **等價表示**。對齊 transfer function 與時間原點後不建立平行算法。 |
| RX package `reverse_ports()` | **共同正確流程**。die-to-channel network 建立後交換 two-port port orientation，不提供錯誤舊法作分支。 |
| Eq. 178A-49 `(-1)^(j+1)` | **共同公式修正**。不是 Annex/reference 平行方法。 |
| `SampledPSD.filtered_by()` grid matching | **固定 utility contract**。輸入 grid 不一致即由 caller 先處理；沒有隱藏 auto-regrid branch。 |

## 實作入口與驗證證據

| 範圍 | 主要實作入口 | 主要驗證 |
|---|---|---|
| Preset 展開與 provenance | `io/com_excel_io_178A.py::_resolve_project_profile_178A()` | `tests/test_com_model_178A_policy_branches.py` |
| Channel renormalization | `utilities/sparam.py::SparamModel.from_touchstone()/from_network()` | `tests/test_channel_renormalization.py` |
| High-frequency handling | `SparamModel.to_LinkSegment()`、`utilities/link.py::resample_tf()` | `tests/test_sparam_out_of_measured.py` |
| CTLE pulse realization | `_realize_ctle_response()` | `tests/test_com_model_178A_ctle_pulse.py` |
| RX FFE record | `_apply_rxffe_response()` | `tests/test_com_model_178A_post_ffe.py`、CTLE pulse tests |
| Noise grid／MMSE inputs | `COMPolicyConfig.resolve_noise_grid()/fit_noise_response()`、noise PSD builders | policy tests、`tests/test_com_model_178A_mlsd_noise.py` |
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
