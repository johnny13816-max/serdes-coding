# 當前契約狀態

此表是進行中事項的狀態入口；規則以
[`../architecture/reference_change_workflow.md`](../architecture/reference_change_workflow.md)
為準。完整歷史與 E/G/T 問題證據見
[`reference_alignment_contracts.md`](reference_alignment_contracts.md)。
「已實作」不等於「已驗證」或「已結案」。

**目前修改焦點：v1.0 foundation／CFG-001／SRCH-001。** 178A 已完成
SiCoPR reference production golden；現在將 workbook facade 收斂成 versioned
`execution_profile`，並要求 local／GitHub search 保存 resolved config、input hashes
與 code revision。完整 release gate 見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

| ID／名稱 | 類別 | 主狀態 | 已確認 | 下一個關卡 |
| --- | --- | --- | --- | --- |
| CFG-001 — Versioned execution profile workbook facade | config／workbook／adapter | **closed** | commit `945dd2b`；新模板與 Akinwale case 使用 `execution_profile`；legacy alias、fixed golden、local full-target search、136 tests／2 subtests 通過；不改 model equations | 無；SRCH-001 已解除 blocker |
| SRCH-001 — Akinwale full-target reference search | search／GitHub Actions | **ready to dispatch** | local lifecycle 通過；runner 保存 resolved config、input hashes、revision；2026-10-14 舊 run 為 DFE-only，不能代表本 gate | 提交／push current runner 後執行 232,848-candidate GitHub search並驗證 artifact |
| [TC-024 — MLSD quantization PSD realization](tc024_mlsd_quantization_psd.md) | MLSD／core／reference policy | **closed**（2026-10-15 使用者驗收） | 正式 reference profile：pos=5、MSE=`0.0061912610245255335`、`COM_MLSD=2.895898684873246 dB`，對 SiCoPR gap=`-1.29e-14 dB`；133 passed／2 subtests passed | 無模型關卡；提交狀態由 repository workflow 管理 |
| [TC-023 — 178A MLSD reference realization](tc023_mlsd_reference_realization.md) | MLSD／core／reference policy | 已核准、工作樹實作與回歸通過；待隔離提交 | Eq. 178A-49 `(-1)^(j+1)` 直接修正；Akinwale `COM_MLSD=2.8810510066627915 dB`，對 SiCoPR 差 `-0.0148476782 dB`，通過 0.05 dB reference gate | 若要壓到 0.01 dB，需取得 reference `p_an`／raw DER dump；不得用常數補償 |
| [TC-022／TC-022A — MMSE noise-correlation record grid](tc022_mmse_noise_grid.md) | G-005／core／project policy | 已核准、工作樹實作與完整回歸通過；待隔離提交 | template 自動提供 optional policy 欄位；一般模式為 `analysis_grid`，reference preset 為 `fixed_ui/4096`；Akinwale total `R_n` 最大差 `3.71e-21 V²`、MSE 差 `8.63e-16`、`COM_DFE=1.5247607834259893 dB`；129 passed／2 subtests passed | 回到 MLSD stage 對齊；既有髒工作樹使專用 commit 待安全隔離 |
| [TC-021 — Channel measured-frequency limit](tc021_channel_frequency_limit.md) | channel ingestion／core utility／config | 已核准、工作樹實作與完整回歸通過；待隔離提交 | Akinwale 六條 raw S4P 均為 100 GHz；runtime 全部限制為 67 GHz／6701 點；正式 reference profile selected pos=5、MSE `0.006191712423925738`、`COM_DFE=1.5247607834259893 dB`；128 passed／2 subtests passed | 原 residual 已由 TC-022 noise grid 收斂 |
| [TC-019R — reference preset 在 project→runtime 邊界展開](tc019r_reference_preset_resolution.md) | TC-019 責任邊界修訂／core config | 已核准、工作樹實作與回歸通過；待隔離提交 | adapter 一次展開具名 methods、三組 execution profiles 與 raw/effective provenance；model/helper 無 `align_to_ref`；固定 67 GHz phase22 MSE 精確重現 `0.006192113355325546`；120 passed、2 subtests passed | 以新邊界修訂 TC-020；既有髒工作樹使專用 commit 待安全隔離 |
| [TC-020R2 — 178A CTLE pulse 與 post-FFE record realization](tc020_ctle_pulse_realization.md) | G-009／core／reference policy | 已核准、工作樹實作與完整回歸通過；待隔離提交 | `bilinear_iir` 固定完成 measured TF→reference grid→raw IFFT→`1e-3` 截尾→IIR→unit pulse；`finite_record_circshift` 正式通過全部 5 條 XT；受控 67 GHz victim pulse 最大差 `2.80e-13 mV`、`COM_DFE=1.5247607834259893 dB`；targeted 27 passed、完整 127 passed／2 subtests passed | `flim` 輸入邊界已由 TC-021 接手；既有髒工作樹使專用 commit 待安全隔離 |
| [TC-019 — 178A 單一 reference 對齊模式](tc019_align_to_ref_profile.md) | reference policy／core／PMF utility | 已核准、工作樹實作與完整回歸通過 | 同輸入 `P_s` L1 差 `6.97e-15`、`P_n` 最大 CDF 差 `3.14e-11`；完整 reference profile 的固定 67 GHz 暫存候選 MSE 差 `+8.52331e-7`；TC-019R 已把 preset 展開移至 adapter 且數值不變 | 處理 G-009／TC-020；原始 case 端到端仍受既有 post-FFE XT3 grid guard 阻擋；隔離提交待處理 |
| [TC-005 — 178A PMF run-level dy 精度政策](tc005_pmf_run_grid_policy.md) | E-004／core／execution policy | 工作樹已實作、完整回歸通過 | 本案 `pmf_dy_override=10 µV`，`keep_mass=1`；`V_qc=41.94 mV`，縮小 dy 仍不會對齊 SiCoPR `41.62 mV`；source-fed MMSE solver 精確對齊 | 隔離提交；量化 tail／noise 方法殘差另行判定 |
| [TC-006 修訂 — measured boundary 外插政策](tc006_out_of_measured_boundary_revision.md) | G-002／utility／fixed-config policy | 工作樹已實作、待隔離提交 | 原始 case S4P 到 100 GHz；六條 `H_21` 在此以上嚴格補零；暫存 67 GHz 輸入重現舊截止結果，H21 最大差 0；固定候選 MSE `0.006216109867`；完整回歸 103 passed、2 subtests passed；[分支責任 audit](../validation/algorithm_branch_boundaries_178A.md) | 隔離提交；SiCoPR solver 輸入／COM 的新介面端到端複核留在 reference 驗證 |
| [TC-016 — 178A channel S4P/Sdd renormalization 順序正式分支](tc016_channel_renormalization_order.md) | G-001／protected utility／fixed-config policy | 工作樹已實作、待隔離提交 | 六路徑正式 `S_ch` 對舊 reference-only reader 差 0；固定 67 GHz 比較的 `h_dsamp`／`R_n`／MSE 對舊 oracle 差 0；正式 single-run pos=23、MSE `0.0062106134601428815`；108 passed、2 subtests passed | 隔離提交；完整 search 另行驗證 |
| [TC-017 — pre-DTE ADC clipping 的 MATLAB 4.17 對照分支](tc017_pre_dte_adc_clipping_reference.md) | G-004／core／fixed-config policy | 使用者已核准；工作樹實作與驗證通過，待隔離提交 | `V_qc` 41.94→41.61 mV；固定 MSE 對 SiCoPR 差 `1.537715e-5`→`1.277871e-6`，低於 `5e-6` gate；原始 100 GHz single-run MSE `0.006196571745`；111 passed、2 subtests passed | 可進下一 stage 審查 final COM ADC PMF；TC-017 kernel-only patch 待與既有未提交修改安全隔離提交 |
| [TC-018 — final quantization MATLAB 4.17 對照分支](tc018_final_adc_quantization_reference.md) | G-006／core／fixed-config policy | 使用者已核准；工作樹實作、固定候選驗證通過，待隔離提交 | 固定候選 reference-only `COM_DFE=1.511853360897216 dB`，比 SiCoPR 低 `0.012907422 dB`；完整回歸 113 passed，最後 PMF grid 修正後 targeted 6 passed | 隔離核心提交；剩餘 COM gap 另行定位 |
| [TC-013 — Run-level fixed grid 與 search overflow 補位](utility_grid_contract_draft.md) | utility／core／search | 暫緩 | 程式與文件已在工作樹；88 tests passed；固定 case 5 MHz 通過；search 補位測試通過 | 使用者決定恢復時，再做實際 search sweep、核對 warning／CSV 與候選補位，之後隔離 model commit |
| [TC-009 — MLSD Eq. 178A-54 pre-FFE noise 與 one-sided ISI](reference_alignment_contracts.md) | E-006／E-008 | review 中 | 已核准、工作樹實作及固定候選驗證 | 逐條公式／程式 review 後決定驗收與提交狀態 |
| [TC-010 — MLSD top flow 與 DER 純計算介面](reference_alignment_contracts.md) | 架構／core | review 中 | 已核准、工作樹實作及回歸驗證 | 逐條公式／程式 review 後決定驗收與提交狀態 |
| [TC-011 — MLSD Eq. 178A-47 分母](reference_alignment_contracts.md) | E-007 | review 中 | 已核准、工作樹實作及固定候選驗證 | 逐條公式／程式 review 後決定驗收與提交狀態 |
| [TC-012 — MLSD Eq. 178A-52 PMF 縮放符號](reference_alignment_contracts.md) | E-009 | review 中 | 已核准、工作樹實作及固定候選驗證 | 逐條公式／程式 review 後決定驗收與提交狀態 |
| [TC-007 — 178A RX FFE tap-layout 映射](reference_alignment_contracts.md) | E-005 | 本地修正與驗證完成；reference input 驗證待資料 | converter、指定 SiCoPR workbook/audit 僅更新為 `6/15/87`；workbook/audit diff 均僅三欄／三列；固定 `target=mse` runtime 得 phase 24、MSE `0.006170581277695888`、`b_lim[0]=0.84196873`、`len(w_lim)=87`；23 targeted tests passed | 取得可重現的 SiCoPR `sbr`、`S_n` 輸入後執行 source-fed golden；既有 untracked conversion stack 可隔離後再建立 TC-007 commit |

其他暫存 TC 與未結案 E/G/T 留在歷史登記簿；開始處理前先把該項加入此表，
填入名稱、檔案範圍及下一個關卡。此表不把先前的 `88 passed` 當作之後
任何修改的測試結果。
