# TC-019R — 178A reference preset 在 project→runtime 邊界展開

**Core Model Change Contract；已核准並在工作樹實作。** 本契約是已實作 TC-019 的責任邊界修訂，保留其算法選擇和數值結果；**不包含 TC-020 的 CTLE 新算法**。關聯 G-001／002／004／006／008 與使用者 2026-10-12 指定的 config 邊界。

## 結論與需要的決策

`fixed_config.align_to_ref` 只作為 project workbook 的 preset 開關。在 `excel_to_config_178A()` 建立 runtime `COMConfig` 前展開所有已驗證的 SiCoPR 方法；每個算法選項在 runtime 仍有具名欄位。模型、PMF helper、S-parameter utility 與 search 均不得再以 `align_to_ref` boolean 選數值路徑。現有名稱 `align_to_ref` 不改成 `aligned_to_ref`，避免 workbook migration；若需改名須修訂本契約。

## 依據與目前資料流

- 依據：使用者已批准的 TC-016／017／018／019 分支及 2026-10-12 project→runtime 設計決定；D3.0 Annex 為一般模式，SiCoPR／MATLAB 4.17 是 reference 比較方法。這是**選擇邊界重整**，不修改任何規範方程、PMF 數學、S-parameter 轉換或 MMSE solver。
- 修改前 `io/com_excel_io_178A.py::_project_excel_to_config_178A()` 將 workbook `align_to_ref` 傳給 `COMConfig`，由 model runtime 覆蓋方法與 PMF 設定。修改後 `_resolve_project_profile_178A()` 在 adapter 一次展開具名方法、execution profiles 與 provenance；runtime config 不再含此 boolean。

## 擬議資料流與具名方法

```text
project workbook fixed_config/run_config/channels
  → io/com_excel_io_178A.py 解析並記錄 raw 值
  → 若 align_to_ref=True，套用單一可稽核的 178A reference preset
  → 建構已展開的 COMConfig + 三個 effective COMRunConfig
  → single/search 複製或使用該 runtime config
  → model/utility 只讀具名方法，不讀 preset boolean
```

Runtime 的具名方法至少包含：既有 `out_of_measured`、`channel_renormalization_order`、`pre_dte_adc_clipping_convention`、`final_adc_quantization_convention`；新增可直接由 Python 設定、驗證的 178A PMF method config，具名描述 `discrete_pmf_placement`、`interference_pmf_method`（binned-signal FIR／原子卷積）、`xtalk_pmf_accumulation`（合併路徑／逐路徑卷積）、`gaussian_pmf_method`、`uniform_pmf_method`、`final_adc_pmf_projection`（包含縮放與 support/tap 門檻）、`final_pmf_grid`、`gaussian_n_sigma` 支撐 policy。方法名稱應描述數學／數值操作，而非稱為 `reference=True`。PMF utility 的既有通用操作不修改。

Adapter 的 reference preset 將上述具名方法直接展開至 `COMConfig.policy`：`zero_padding`、`s4p_first`、兩個 MATLAB 4.17 ADC convention、最近格點離散 tap、原子卷積／逐 XT 路徑、Gaussian grid sample、uniform nearest-centers、ordinate interpolation 與 reference support、`relative_As` final grid、依 `DER_0` 決定的 Gaussian support。三個 run profile 的有效設定為 `pmf_exact`、`fine`、`keep_mass=1`、`pmf_dy_override=None`；這四項明列為 execution preset，不假裝是物理公式。

`align_to_ref=False` 時保留 workbook 已有個別欄位與全部 run values；缺少細節欄位時使用現行一般模式預設。舊 workbook 如同時有 `align_to_ref=True` 和個別方法值，adapter 依本契約強制 reference 值，並在匯出紀錄逐項列 raw／effective／overridden-by-profile；不得默默覆蓋。新版模板仍只曝露 `align_to_ref` 這一個 reference 總開關（已存在）；不新增 PMF 細節列。直接 Python 建構 `COMConfig` 時明確傳入具名方法，不需 Excel preset 即可重現相同 runtime 結果。Runtime `COMConfig` 不保留作數值開關的 `align_to_ref` 欄位；adapter 可附 `applied_config_profile` 與 raw／effective 覆蓋紀錄作**純 provenance**，model 不以它分支。

原始 S4P 檔案、port order、R0 和最高量測頻率不由 preset 改寫。SiCoPR 本案的 67 GHz 輸入仍須由可追溯的 case 輸入提供；100 GHz 原檔選 zero padding 只在 100 GHz 後補零。

## 預計修改檔案、函式與責任層級

| 層級 | 檔案／函式 | 修改 |
| --- | --- | --- |
| project→runtime adapter | `src/serdes_coding/io/com_excel_io_178A.py::excel_to_config_178A()`、`_project_excel_to_config_178A()`、`_read_project_execution_config()`；新增同檔私有 preset 展開 helper | 解析開關，在構造 `COMConfig` 前產生具名 method config、有效 execution profiles 及覆蓋 provenance。`com_excel_common.py` 不承擔 178A 專用 policy。 |
| protected 178A config | `src/serdes_coding/models/com_model_178A.py::COMPolicyConfig`、`COMConfig`、`COMConfig.__post_init__()`、`resolve_run_cfg()`、`to_export_dict()` | 所有算法選擇、noise-grid 欄位及 preset provenance 平放在唯一的 `COMConfig.policy`；不保留 nested policy dataclass 或具名方法的 top-level alias。 |
| protected path／pre-DTE | 同檔 `_build_paths()`、`COM.build_all_paths()`、`_calculate_V_qc()`、`_build_psd_adc_qn()`、`COM._effective_run_cfg()`、`COM.calculate_pre_dte_imp_at_pos()` | 傳具名方法；run config 直接使用 adapter 已展開值，不在 run 中覆蓋。 |
| protected PMF／post-FFE／MLSD | 同檔 `_resolve_final_com_pmf_config()`、`_build_pmf_pam_L()`、`_build_pmf_interference_178A()`、`_build_pmf_w_XT_all()`、`_build_adc_input_pmf_exact()`、`_build_pmf_G()`、`_final_adc_clip_reference_only()`、`evaluate_delta_com_an()`、`solve_g_an()`、`COM.calculate_post_ffe_imp()`、`COM.calculate_COM_DFE()`、`COM.calculate_COM_MLSD()` 及其直接傳值點 | 把 boolean 條件替換為對應的具名方法；保留每一支目前的數值順序、threshold、support、grid、PMF 公式。若發現某 boolean 條件無法唯一映射到已列方法，須先修訂契約，不以臨時 boolean 代替。 |
| 測試 | `tests/test_com_model_178A_policy_branches.py`、`tests/test_com_model_178A_mlsd_eq47.py`；必要時新增 `tests/test_178a_reference_preset_boundary.py` | 逐欄核對 raw→effective；`False`、`True`、legacy 衝突、直接 Python 具名設定、single/search copy、export；前後 stage golden。 |
| 權威文件 | `docs/models/178A/config_tree.md`、`call_tree.md`、`stages/path_construction.md`、`stages/pre_dte.md`、`stages/com_dfe.md`，以及 `docs/architecture/configuration_architecture.md` | 更新 project→runtime 邊界與各 stage 具名方法；不提前更改數學主張。 |
| 規劃文件 | 本契約、`docs/planning/active_contracts.md`、`docs/planning/178a_branch_inventory.md`、`docs/planning/tc019_align_to_ref_profile.md` | 記錄批准、驗證與結案。 |

不修改 `src/serdes_coding/utilities/pmf.py`／`sparam.py`／`link.py`、93A、COM 方程、GUI、conversion registry、case S4P、既有 workbook 二進位檔或 CTLE。Search 模組的 `_config_with_candidate()` 只會複製已解析 config；預期無須修改 `com_search_178A.py`，但需測試其不重新展開 preset。若必須改 search 或 workbook，先修訂此檔案清單。

## 應變／不變、驗證與影響

- **應變**：config 型別與解析位置、直接 Python API 的 PMF method 欄位、匯出的 raw/effective/provenance 內容；模型/helper signature 不再收 `align_to_ref`。從 adapter 讀取的兩種 profile 數值**不應變**。
- **必須不變**：True／False 各自的 `S_ch/S_all/H_21/pulse`、ADC `P_s/P_n/V_qc/S_qn`、`S_rn/S_xn/S_tn/S_jn/R_n`、phase、FFE、DFE、MSE、post-FFE 各 PMF、COM_DFE／COM_MLSD；93A 全部行為。CTLE 仍只有現行 continuous-TF 方法。相同具名 runtime config 由 workbook 或 Python 產生時應給相同輸出。
- **固定 case／容差**：`sicopr_akinwale_vendorx_22db` 的正式 workbook，以及相同 case 關閉開關的副本；固定 67 GHz 暫存輸入與鎖定候選沿用 TC-019。舊 reference profile phase22 MSE `0.006192113355325546` 是比較基線，不應因本次重整變動。各有效設定欄位逐項相等；可比陣列逐點 `rtol=0, atol=0`，浮點重組處最多 `rtol=1e-12`；`V_qc` 不跨 10 µV bin；MSE 差 `<1e-12`、COM 差 `<1e-9 dB`。現有 policy 專項基線 `15 passed`，之後跑相關、完整 178A／93A regression，再做 fixed single/search smoke。原始 100 GHz 的 XT3 fixed-grid guard 不屬本契約，不能以它失敗宣稱 preset migration 改變數值。
- **single/search/API**：178A single、search_sweep、search_final 均拿已展開的 execution profiles；search candidate 複製應保留方法名。93A 不變。新版 workbook 繼續只有一個 reference 總開關；直接 Python runtime 改用明名方法設定，而非 `COMConfig(align_to_ref=True)` 啟動 profile，此相容性改動須在測試與文件明示。

## 提交與回退邊界

既有 canonical 工作樹的 `com_model_178A.py`、adapter、測試與文件有未提交修改，不得覆蓋、還原或整檔混入本契約。批准後先在 `%TEMP%/serdes-tc019r-<date>/` 保存精確修改前副本與 kernel-only patch，再做改動；protected config/dispatch 行為與對應測試／權威文件隔離提交。回退該 TC-019R 專用 commit 或已保全的精確 patch，恢復 TC-019 目前展開方式；TC-020 另立提交。無法安全隔離時標「待隔離提交」，不可宣稱結案。

## 2026-10-12 實作與驗證

- `com_excel_io_178A._resolve_project_profile_178A()` 現在是唯一 preset 展開點；
  `COMConfig` 不含 `align_to_ref`，新增 `COMPolicyConfig` 與純 provenance
  欄位。model/helper 全部以具名方法執行。
- workbook adapter 測試逐項驗證四個 top-level methods、八個 PMF methods、
  Gaussian support、三組 execution profiles、raw/effective export，以及直接
  Python 具名 config 可形成相同 runtime policy。
- 固定 67 GHz、phase 22 重算 MSE 為 `0.006192113355325546`，與修改前
  TC-019 golden 完全相同；主游標 `14.31679220487629 mV`、
  `V_qc=41.60000000000001 mV`。SiCoPR MSE 差仍為
  `+8.523308008753783e-7`，證明本次只搬移責任邊界。
- 專項 `16 passed, 2 subtests passed`；完整回歸
  `120 passed, 2 subtests passed`。CTLE 無修改。
- 修改前副本與重算腳本位於 `%TEMP%/serdes-tc019r-20261012/`。既有工作樹
  含其他未提交核心修改，專用 commit 目前無法安全建立，狀態為待隔離提交。
