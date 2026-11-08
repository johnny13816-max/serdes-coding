# TC-017 — 178A pre-DTE ADC clipping 的 MATLAB 4.17 對照分支

**狀態：ALG-008 closure review 於 2026-11-09 完成；D3.2 evidence、唯一 owner、impact boundary 與語意命名已收斂。** 關聯 G-004。`full_jitter_half_tail` 是 D3.2 支持的 project method；`rj_only_full_tail_reference` 僅供與 COM MATLAB 4.17.0／SiCoPR 的固定案例比較，**不是 general method**。

## 目標、證據與目前資料流

IEEE P802.3dj/D3.2 Annex 178A.1.7.6 Eq. (178A-29)–(178A-31) 確認：ADC clipping 的 Gaussian noise PSD 含完整 jitter `S_jn`，由 `P_sn` 的 `P_qc/2` 左尾求 `V_qc`。本地 COM MATLAB 4.17.0 `release/com_ieee8023_4p16p0.m` 的 `get_PSDs` 路徑則用 random-jitter-only 項建立 clipping Gaussian `P_n`，以 `CDF=P_qc` 求 `V_qc`；完整 jitter 仍用於 MMSE 的 noise PSD。已擷取的 SiCoPR fixed candidate亦呈現同一組差異，因此保留明確標示的 reference-only 對照分支。

目前 `src/serdes_coding/models/com_model_178A.py::calculate_pre_dte_imp_at_pos()` 是唯一 execution owner：先算完整 `S_jn`，令 `S_ga=S_rn+S_xn+S_tn+S_jn`，再把已選定的 clipping sigma／tail 送 `_build_psd_adc_qn()`；其後 `S_total=S_ga+S_qn`，轉成 `R_n`。D3.2 Eq. (178A-29) 至 Eq. (178A-31) 已確認 project method 使用完整 jitter 與 `P_qc/2`。

## 提議的責任邊界與數學資料流

178A fixed-config `pre_dte_adc_clipping_convention: Literal["full_jitter_half_tail", "rj_only_full_tail_reference"]`，預設 `full_jitter_half_tail`。它只控制 **pre-DTE clipping PMF 的 Gaussian sigma 與左尾門檻**；`pre_dte_pmf_method`、`pmf_dy_override`、`pmf_keep_mass` 仍是 run-config 精度／速度設定，不用兩個可獨立切換的 boolean 拼湊混合公式。

```text
S_jn_full = sigma_X² (A_DD² + sigma_RJ²) |DFT(h_J)|² / fb
S_jn_RJ   = sigma_X² sigma_RJ² |DFT(h_J)|² / fb

S_noise_for_MMSE = S_rn + S_xn + S_tn + S_jn_full + S_qn  # 兩分支相同定義

full_jitter_half_tail:
    sigma_clip² = integral(S_rn + S_xn + S_tn + S_jn_full)
    V_qc = -CDF_inverse(P_sn, P_qc/2)

rj_only_full_tail_reference:
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
| 178A config／protected kernel | `src/serdes_coding/models/com_178a/config.py::COMPolicyConfig`、`src/serdes_coding/models/com_model_178A.py::COM.calculate_pre_dte_imp_at_pos()`、`_calculate_V_qc()`、`_calculate_V_qc_gaussian_approx()`、`_build_psd_adc_qn()` | 固定 policy 驗證與狀態記錄；clipping sigma／tail 選擇；MMSE 完整 jitter 不動 |
| 178A workbook adapter | `src/serdes_coding/io/com_excel_io_178A.py::_project_excel_to_com_config_178A()` | 讀 fixed-config selector，舊 workbook 缺欄時使用 `full_jitter_half_tail` |
| conversion 分類 | `src/serdes_coding/io/conversion/mapping_rules.py::POLICY_FIXED_178A` | 列為 project-owned policy，不從 Ad Hoc intrinsic 映射 |
| workbooks | 現有 178A case/template workbooks | selector 未直接持久化；adapter 由 execution profile 展開 project／reference method |
| tests | `tests/test_com_model_178A_policy_branches.py` 及必要的固定案例測試 | 兩分支 clipping、`R_n` 僅透過 `S_qn` 改變、舊預設、invalid selector、single/search 共用 fixed policy |
| docs | `docs/models/178A/config_tree.md`、`docs/models/178A/stages/pre_dte.md`、`docs/architecture/adhoc_mapping_fields.md`、`docs/validation/mmse_input_akinwale_178A.md`、本契約、`docs/planning/active_contracts.md`、`docs/planning/reference_alignment_contracts.md` | 記錄適用邊界、非 general 標籤、fixed-case 證據與待釐清的規範版本 |

GUI 使用現有 fixed-config workbook 欄位，無 GUI 程式或 utility 修改。若實作發現需要變更上述之外的核心函式、post-FFE 或 93A，先修訂契約並取得新核准。

## 應變與不變量、驗收與回退

預期直接改變：clipping `sigma_clip`／`P_n`／`P_sn`、`V_qc`、`delta`、`S_qn`、`R_n`、FFE／DFE／MSE。phase／taps 若改變，可間接影響後續 COM；final ADC PMF 不讀取此 selector。應保持：`h_dsamp`、`P_s`、`S_rn`、`S_xn`、`S_tn`、完整 `S_jn`、ADC 前 `S_rn+S_xn+S_tn+S_jn`、MMSE solver 方程、channel/package/filter、93A、post-FFE 公式。若參數 `N_qb/P_qc` 停用，兩分支結果相同。

固定驗證以 `cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx`、同一 locked candidate、`pmf_exact`、`pmf_dy_override=10 µV`、`pmf_keep_mass=1` 與相同 67 GHz measured-boundary／時間對齊為比較邊界。先核對 `P_s` 不變、reference-only `sigma_clip` 接近 SiCoPR `0.648880 mV`（允許已知 waveform 殘差 `≤0.002 mV`）、`V_qc` 接近 `41.62 mV`（`≤0.02 mV`），並驗證 D3 預設保留原 `41.94 mV` 至一個 10 µV bin。精確比較 `h_dsamp` 全向量、`R_n[0:86]` 各來源、normalized 87-tap FFE、DFE、MSE；`R_n` 的非量化項應逐點不變至 floating-point roundoff。SiCoPR source-fed solver 既有 MSE `0.006191261024524671` 為核對值；若實際 reference-only MSE 差仍大於 `5e-6`（約 0.081%）或無法由剩餘 `h_dsamp`／非量化 `R_n` 殘差解釋，暫不進下一 stage，直接定位本級殘差。這個 gate 是本案例 debug 門檻，不是 general compliance 容差。

先做 equation-level unit tests，再執行 fixed single-run，最後確認 search profile 沿用同一 fixed policy；93A／178A 回歸通過後才視為完成。所有模擬暫存資料放 `%TEMP%` 專用子目錄。現有工作樹含多項既有未提交修改；實作前保存上述檔案的修改前 patch／副本，僅將 TC-017 的 kernel hunk 放入獨立 commit。回退界線是該專用 commit／patch，不能還原他人既有修改。

## 固定候選實測（2026-10-11）

正式 policy 以 `COMConfig` 選取，pre-DTE stage 才分出 clipping 用的 random-jitter PSD；`S_ga` 的完整 jitter 保留供 MMSE covariance。`_build_psd_adc_qn()` 只接已決定的 `cdf_tail`，不自行選 policy。兩種 PMF method 的 stage invariant test 已通過；完整數值見 [MMSE input audit](../validation/mmse_input_akinwale_178A.md)。

同一 locked 67 GHz 比較邊界下，reference-only `P_n` 標準差 `0.648785 mV`（SiCoPR `0.648880 mV`）、`V_qc=41.61 mV`（SiCoPR `41.62 mV`），量化 RMS `0.381326106 mV`（SiCoPR `0.381417749 mV`），MSE `0.006192538895`（SiCoPR `0.006191261025`），差 `1.277871e-6 < 5e-6`。相同輸入改回 `full_jitter_half_tail` 重現 `V_qc=41.94 mV`、MSE `0.006206638174`。剩餘 FFE 最大差 `2.688959e-4`、DFE 最大差 `1.197153e-5`，故 stage gate 僅表示可以依序檢查下一級，不是 MMSE 向量完全相同。

原始 100 GHz case、`single_run.target=mse` 的 32-phase 執行選 `pos=23`、`ts=163991`、87 個 FFE tap，MSE `0.006196571745350858`、`V_qc=41.60 mV`。這個 single-run 不直接與 67 GHz locked candidate 的 reference MSE 相減。歷史 TC-017 回歸為 `111 passed, 2 subtests passed`；ALG-008 closure rename 的 focused tests 為 `29 passed`，SiCoPR production golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。
