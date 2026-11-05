# 178A 近期算法分支：設定與數值責任 audit（2026-10-10）

> 本文件是 2026-10-10 的 validation snapshot。現行完整分支定義與責任邊界，以 authoritative [178A 分支行為登錄表](../models/178A/branch_behavior_registry.md) 為準。

本表回答「分支在哪裡選、在哪一層執行」，不以 reference COM 接近度判定方法正確。核心流程的審查、批准與隔離提交仍依 [reference change workflow](../architecture/reference_change_workflow.md)。

| 分支／控制量 | 設定入口 | 數值責任層 | 判定與後續 |
| --- | --- | --- | --- |
| `out_of_measured=cosine_decay/zero_padding` | 178A fixed-config `COMConfig`；victim/NEXT/FEXT 共用 | `SparamModel.to_LinkSegment()` 是 S-to-link 邊界，`LinkSegment.from_tf()`／`resample_tf()` 執行外插 | **本次已修正層級**。舊 `_build_path()` 的 67 GHz 事後補零已移除；高層僅傳 policy。原始 S4P 到 100 GHz，SiCoPR `flim=67 GHz` 屬不同輸入邊界，需另行審核暫存截取輸入。 |
| `missing_dc_policy` | `COMChannelConfig` fixed policy | `SparamModel.to_LinkSegment()` 呼叫 `extrapolated_to_dc()`；LinkSegment 做 grid 轉換 | **層級合理**：DC 是量測 S-parameter 缺口處理，COM 只傳設定。 |
| `numerical_control.adc_input_pmf_grid.*` | `COMConfig.numerical_control`；preset 展開到 selected `COMRunConfig` | `_resolve_adc_input_pmf_config()` 建 ADC-input runtime PMF grid | **NUM-004 canonical boundary**：rule、relative spacing、cap、override 只影響 pre-DTE/selected-phase ADC-input domain；reference preset 明示 `10 µV` override。 |
| `numerical_control.final_pmf_grid.*` | `COMConfig.numerical_control`；preset 展開到 selected `COMRunConfig` | `_resolve_final_com_pmf_config()` 建 final DFE/MLSD runtime PMF grid | **NUM-005 canonical boundary**：與 ADC-input family 獨立；reference preset 使用 `relative_As` 且不繼承 ADC override。 |
| `pmf_grid_quality`／`pmf_dy_override` | legacy workbook／direct-API compatibility fields | 只在 canonical family 未解析時進入相容 fallback | 新模板不再輸出；不得視為新的 user-facing control。`pmf_keep_mass` 仍是獨立 execution control。 |
| `tap_rel_As`／`gaussian_n_sigma` | `COMPMFConfig` algorithm policy | PMF tap/support algorithms | 與 NUM-004／NUM-005 grid spacing branches 分離。 |
| `pre_dte_pmf_method=pmf_exact/gaussian_approx` | `COMRunConfig` | 178A `_build_psd_adc_qn()` 選 `_calculate_V_qc()` 或 `_calculate_V_qc_gaussian_approx()`；共同以 Eq. 178A-27/26 形成 ADC step 與 `S_qn` | **目前層級合理**：是 COM 的 ADC-input 模型策略，不屬 generic `Pmf1D` 對外接口。兩法的適用性／預設仍需 spec 與跨 case 審查。 |
| `floating_mode=heuristic/simplified/spec-defined` | `COMRunConfig` | `COM_MMSE_DTE.run()` 選 floating FFE group 求解流程 | **目前層級合理**：選擇直接改變 MMSE 搜尋，應留在 solver 的明確入口。 |
| `pos_sweep_method=each_phase/coarse_fine` | `COMRunConfig` | 178A phase 搜尋流程選擇 sampling phase，候選送同一 MMSE solver | **目前層級合理**：屬搜尋政策，不應在 sampled response utility 中做相位篩選。 |
| `force_grid=True/False` | `LinkSegment.cascade_ir()`／`SampledResponse.cascade_ir()` 的 utility 參數；COM 正式路徑用 True | utility 計算完整卷積、檢查尾端、決定輸出 grid；search 將 overflow 當候選失敗並補位 | **責任分層合理，但 TC-013 驗證暫緩**；不把目前程式存在等同設計結案。 |
| `SampledPSD.filtered_by()` grid 契約 | 兩個物件的 `cfg` 與 theta 必須對齊；無自動 regrid 開關 | PSD utility 直接檢查並在相同 grid 濾波；必要的 grid 決策由呼叫端事先完成 | **無隱藏分支**。此前討論的「filtered_by 內自動 regrid」未採用，不應在 COM orchestration 私下補做。 |
| channel renormalization：spec-defined Sdd vs SiCoPR S4P-first | 178A `COMConfig.policy.channel_renormalization_order`；模板 `sdd_first`、SiCoPR case `s4p_first` | `SparamModel.from_network()`／`from_touchstone()` 在 S4P ingestion 邊界執行；COM 只轉送 | **[TC-016](../planning/tc016_channel_renormalization_order.md) 已實作並通過固定驗證**。`_build_path()` 不事後修改 S_ch；93A 繼續 sdd_first。 |
| unit pulse 的 boxcar／sinc 表示 | 無正式分支 | 兩者描述相同的輸入 pulse 頻域乘積 `X(f)H(f)`，比較時需對齊時間原點 | **不建立平行算法**。既有受控比較已排除 pulse 表示法造成的實質響應差；純時間位移僅作比較座標對齊。 |
| pre-DTE ADC clipping `P_s`／`P_n`／tail | `COMConfig.policy.pre_dte_adc_clipping_convention` | `calculate_pre_dte_imp_at_pos()` 選 clipping sigma／tail；`_calculate_V_qc()` 建 PMF；`_build_psd_adc_qn()` 建 `S_qn` | **[TC-017](../planning/tc017_pre_dte_adc_clipping_reference.md) 已實作**。D3 預設完整 jitter＋`P_qc/2`；reference-only 選 RJ＋`P_qc`，但 MMSE noise 仍保留完整 jitter。 |
| final DFE COM `V_qc` | `COMConfig.policy.final_com_vqc_convention` | `calculate_COM_DFE()`／`_reconstruct_final_vqc_sicopr()` | **ALG-011 pending D3p2 evidence**。`selected_phase_adc_input` 沿用 Stage 5 exact `V_qc/delta`；`sicopr_final_reconstruction` 依 SiCoPR composition 與 `P_qc` 重建。main-tap accumulation 不屬 ALG-011，已另列 deferred issue 並凍結 production ordering。 |

`S4P-first` 與兩個 stage 各自的 ADC policy 均已提供正式選項；boxcar／sinc 不建立分支。reference-only ADC 分支供校準，不等於通用 178A 合規方法。任何後續模型改動契約均須列出設定所有者、數值所有者、逐層呼叫鏈、預期變動的中間量與禁止高層事後修改的邊界。
