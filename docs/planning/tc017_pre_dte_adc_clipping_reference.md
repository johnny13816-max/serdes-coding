# TC-017 — 178A pre-DTE ADC clipping 的 MATLAB 4.17 對照分支

**狀態：2026-10-11 使用者已在逐段審核程式位置與分支邊界後明確核准；工作樹已實作，固定候選、single-run 與完整回歸通過，待隔離提交。** 關聯 G-004。此分支僅供與 COM MATLAB 4.17.0／SiCoPR 的固定案例比較，**不是 general method，也不宣稱取代所持 178A D3.0 Annex**。取得新版規範或釐清公式後，重新審查並以另一份 contract 決定是否合併為單一方法。

## 目標、證據與目前資料流

所持 IEEE P802.3dj/D3.0 Annex 178A.1.7.6 Eq. (178A-26)–(178A-29) 為現行預設依據：ADC clipping 的 Gaussian noise PSD 含完整 jitter `S_jn`，由 `P_sn` 的 `P_qc/2` 左尾求 `V_qc`。本地 COM MATLAB 4.17.0 `release/com_ieee8023_4p16p0.m` 的 `get_PSDs` 路徑則用 random-jitter-only 項建立 clipping Gaussian `P_n`，以 `CDF=P_qc` 求 `V_qc`；完整 jitter 仍用於 MMSE 的 noise PSD。已擷取的 SiCoPR fixed candidate 亦呈現同一組差異。新版規範尚未取得，因此兩者暫列平行比較，不以 SiCoPR 輸出反證 D3.0。

目前 `src/serdes_coding/models/com_model_178A.py::calculate_pre_dte_imp_at_pos()` 先由 `_build_psd_tx_jitter()` 算完整 `S_jn`，令 `S_ga=S_rn+S_xn+S_tn+S_jn`，把 `sqrt(integral(S_ga))` 送 `_build_psd_adc_qn()`；`_calculate_V_qc()` 和 `_calculate_V_qc_gaussian_approx()` 都用 `P_qc/2`。其後 `S_total=S_ga+S_qn`，轉成 `R_n`。目前 clipping 與 MMSE covariance 共用同一 Gaussian PSD。

## 提議的責任邊界與數學資料流

新增 178A fixed-config `pre_dte_adc_clipping_convention: Literal["annex_d3", "matlab_4_17_reference_only"]`，預設 `annex_d3`。它只控制 **pre-DTE clipping PMF 的 Gaussian sigma 與左尾門檻**；`pre_dte_pmf_method`、`pmf_dy_override`、`pmf_keep_mass` 仍是 run-config 精度／速度設定，不用兩個可獨立切換的 boolean 拼湊混合公式。

```text
S_jn_full = sigma_X² (A_DD² + sigma_RJ²) |DFT(h_J)|² / fb
S_jn_RJ   = sigma_X² sigma_RJ² |DFT(h_J)|² / fb

S_noise_for_MMSE = S_rn + S_xn + S_tn + S_jn_full + S_qn  # 兩分支相同定義

annex_d3:
    sigma_clip² = integral(S_rn + S_xn + S_tn + S_jn_full)
    V_qc = -CDF_inverse(P_sn, P_qc/2)

matlab_4_17_reference_only:
    sigma_clip² = integral(S_rn + S_xn + S_tn + S_jn_RJ)
    V_qc = -CDF_inverse(P_sn, P_qc)

delta = 2 V_qc / (2^N_qb - 1)
S_qn = (delta²/12)/fb
R_n = IFFT(S_noise_for_MMSE)
```

`S_jn_RJ` 由現有 `_build_psd_from_DFT_response(h_J, link_cfg, sigma_X²*sigma_RJ²)` 建立，不在 PSD／PMF utility 隱藏 policy。`P_s` 的構造與 PMF bin 規則不變。`COMAdcInputPMF` 增加獨立的 `clipping_convention` metadata，不能覆用既有 `method`（其意義是 `pmf_exact`／`gaussian_approx`）。`gaussian_approx` 保持專案近似法，但遵守所選的 sigma／tail；與 SiCoPR 的量化對照只用 `pmf_exact`。後續 **post-FFE final COM 的 ADC PMF** 現有計算不屬本契約，仍以 D3.0 路徑運作；此 selector 明確稱為 `pre_dte_...`，不宣稱整體 COM 已切成 MATLAB 版本。後級若要對齊，另行審查該級的來源與公式。

## 精確修改範圍

| 層級 | 檔案與函式／位置 | 變更 |
| --- | --- | --- |
| 178A protected kernel | `src/serdes_coding/models/com_model_178A.py::COMConfig.__post_init__`、`COMAdcInputPMF`、`COMModel178A.calculate_pre_dte_imp_at_pos()`、`_calculate_V_qc()`、`_calculate_V_qc_gaussian_approx()`、`_build_psd_adc_qn()` | 固定 policy 驗證與狀態記錄；clipping sigma／tail 選擇；MMSE 完整 jitter 不動 |
| 178A workbook adapter | `src/serdes_coding/io/com_excel_io_178A.py::_project_excel_to_com_config_178A()` | 讀 fixed-config selector，舊 workbook 缺欄時使用 `annex_d3` |
| conversion 分類 | `src/serdes_coding/io/conversion/mapping_rules.py::POLICY_FIXED_178A` | 列為 project-owned policy，不從 Ad Hoc intrinsic 映射 |
| workbooks | `cases/_templates/178A/config.xlsx`、`cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx` 的 `fixed_config` | 模板 `annex_d3`；SiCoPR 對照 case 明選 reference-only；不得覆蓋其他欄位 |
| tests | `tests/test_com_model_178A_policy_branches.py` 及必要的固定案例測試 | 兩分支 clipping、`R_n` 僅透過 `S_qn` 改變、舊預設、invalid selector、single/search 共用 fixed policy |
| docs | `docs/models/178A/config_tree.md`、`docs/models/178A/stages/pre_dte.md`、`docs/architecture/adhoc_mapping_fields.md`、`docs/validation/mmse_input_akinwale_178A.md`、本契約、`docs/planning/active_contracts.md`、`docs/planning/reference_alignment_contracts.md` | 記錄適用邊界、非 general 標籤、fixed-case 證據與待釐清的規範版本 |

GUI 使用現有 fixed-config workbook 欄位，無 GUI 程式或 utility 修改。若實作發現需要變更上述之外的核心函式、post-FFE 或 93A，先修訂契約並取得新核准。

## 應變與不變量、驗收與回退

預期改變：clipping `sigma_clip`／`P_n`／`P_sn`、`V_qc`、`delta`、`S_qn`、`R_n`、FFE／DFE／MSE。應保持：`h_dsamp`、`P_s`、`S_rn`、`S_xn`、`S_tn`、完整 `S_jn`、ADC 前 `S_rn+S_xn+S_tn+S_jn`、MMSE solver 方程、channel/package/filter、93A、post-FFE 公式。若參數 `N_qb/P_qc` 停用，兩分支結果相同。

固定驗證以 `cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx`、同一 locked candidate、`pmf_exact`、`pmf_dy_override=10 µV`、`pmf_keep_mass=1` 與相同 67 GHz measured-boundary／時間對齊為比較邊界。先核對 `P_s` 不變、reference-only `sigma_clip` 接近 SiCoPR `0.648880 mV`（允許已知 waveform 殘差 `≤0.002 mV`）、`V_qc` 接近 `41.62 mV`（`≤0.02 mV`），並驗證 D3 預設保留原 `41.94 mV` 至一個 10 µV bin。精確比較 `h_dsamp` 全向量、`R_n[0:86]` 各來源、normalized 87-tap FFE、DFE、MSE；`R_n` 的非量化項應逐點不變至 floating-point roundoff。SiCoPR source-fed solver 既有 MSE `0.006191261024524671` 為核對值；若實際 reference-only MSE 差仍大於 `5e-6`（約 0.081%）或無法由剩餘 `h_dsamp`／非量化 `R_n` 殘差解釋，暫不進下一 stage，直接定位本級殘差。這個 gate 是本案例 debug 門檻，不是 general compliance 容差。

先做 equation-level unit tests，再執行 fixed single-run，最後確認 search profile 沿用同一 fixed policy；93A／178A 回歸通過後才視為完成。所有模擬暫存資料放 `%TEMP%` 專用子目錄。現有工作樹含多項既有未提交修改；實作前保存上述檔案的修改前 patch／副本，僅將 TC-017 的 kernel hunk 放入獨立 commit。回退界線是該專用 commit／patch，不能還原他人既有修改。

## 固定候選實測（2026-10-11）

正式 policy 以 `COMConfig` 選取，pre-DTE stage 才分出 clipping 用的 random-jitter PSD；`S_ga` 的完整 jitter 保留供 MMSE covariance。`_build_psd_adc_qn()` 只接已決定的 `cdf_tail`，不自行選 policy。兩種 PMF method 的 stage invariant test 已通過；完整數值見 [MMSE input audit](../validation/mmse_input_akinwale_178A.md)。

同一 locked 67 GHz 比較邊界下，reference-only `P_n` 標準差 `0.648785 mV`（SiCoPR `0.648880 mV`）、`V_qc=41.61 mV`（SiCoPR `41.62 mV`），量化 RMS `0.381326106 mV`（SiCoPR `0.381417749 mV`），MSE `0.006192538895`（SiCoPR `0.006191261025`），差 `1.277871e-6 < 5e-6`。相同輸入改回 `annex_d3` 重現舊 `V_qc=41.94 mV`、MSE `0.006206638174`。剩餘 FFE 最大差 `2.688959e-4`、DFE 最大差 `1.197153e-5`，故 stage gate 僅表示可以依序檢查下一級，不是 MMSE 向量完全相同。

原始 100 GHz case、`single_run.target=mse` 的 32-phase 執行選 `pos=23`、`ts=163991`、87 個 FFE tap，MSE `0.006196571745350858`、`V_qc=41.60 mV`。這個 single-run 不直接與 67 GHz locked candidate 的 reference MSE 相減。專案 `.venv` 完整回歸 `111 passed, 2 subtests passed`；固定 policy 測試 `12 passed`。修改前檔案快照、TC-017 kernel-only patch、固定比較 JSON、single-run JSON 與 pytest 暫存均在 `%TEMP%/serdes-tc017-20261011/`。現有 `com_model_178A.py` 仍含其他先前未提交修改，因此不得把整檔直接提交成 TC-017 commit；隔離提交保留為待辦。
