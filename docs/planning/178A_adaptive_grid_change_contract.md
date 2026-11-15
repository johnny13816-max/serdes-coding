# 178A Adaptive Response Grid 修改契約

狀態：**待使用者審閱／尚未核准實作**｜2026-11-14

本文件定義擬議修改，不描述目前 production 已實現的行為。它是受保護的 COM
數值流程變更契約；核准與實作後，依專案文件權責將有效內容併入各權威文件。
現有程式、registry 與既有驗證在實作完成前仍是目前狀態的依據。

## 目的與邊界

Stage 1 支援使用者指定單一 grid，以及依 response 有效範圍自動選擇 grid。
Stage 2–7 消費 Stage 1 的結果，不得讀取、接收或判斷 grid mode selector。
Stage 5 固定以輸入 grid 執行 circular RX FFE，移除 ALG-011 選擇。

本契約不實作 XT 合併分支、不改動 93A、PMF 數學、其他現有演算法選擇，
也不將 NUM-003 的 PSD record 控制擴展到原始 equivalent-channel response。
所有實作應優先採用功能完整、責任清楚的函數；不新增純轉發或純組裝 wrapper。

## Stage 與資料流

```text
_run_once()
├─ Stage 1  build_all_paths()：fixed / adaptive grid owner
│  ├─ fixed：使用者指定單一 cfg
│  └─ adaptive：victim 兩輪 → XT 兩輪 → paths
├─ Stage 2  response 抽樣與 pre-DTE PSD
├─ Stage 3  phase search
├─ Stage 4  MMSE DTE
├─ Stage 5  post-FFE response 與 impairment
├─ Stage 6  DFE COM / PMF
└─ Stage 7  MLSD PSD / DER
```

### Grid mode 與輸出

`COM.build_all_paths()` 是 Stage 1 grid mode 的 semantic 與 callable owner：
以兩個可直接辨識的主要分支執行完整 path 建立並回傳；可共用的運算放在
分支外。各分支結果均維持 victim、NEXT、FEXT 的既有次序。

| 模式 | 輸入／行為 | Stage 1 檢查 |
| --- | --- | --- |
| fixed-grid | 使用者提供的單一 `LinkConfig` 建立 paths | 保留 victim `H_21`、`pulse`、`pulse_no_txffe` 既有尾端 guard |
| adaptive-grid | 使用 fine grid 評估，再建立 victim 與 XT production grids | 不額外執行上述 guard；`LinkSegment.from_ir()` 的既有檢查不因此改動 |

Adaptive 輸出的 `LinkSegment` 僅使用 `victim_cfg`、`xtalk_cfg` 或
`report_cfg`；沒有 XT 時不建立 `xtalk_cfg`。`report_cfg` 的目標 df 約
100 MHz，用於報表相關 response 和 shared objects。fine grid 僅限 Stage 1
內部，最終輸出不得透過物件或 array view 持有大型 fine-grid 暫存。
三種輸出 cfg 與 fine cfg 共用 `fb`、`per_ui`；相互關係不由名稱推定長短。

Grid mode 是 Stage 1 的數值實現選擇；threshold 數值與 fine-grid df 是其
控制參數，不因可設定便自動取得獨立 branch identity。新增選擇須在實作時
同步 config inventory、runtime resolution 與 version registry；最終 selector
名稱、預設與 profile 必須先與現有 configuration contract 核對，不可虛構。

### 178A configuration inventory（implementation target）

| 候選 runtime 欄位 | domain / exposure | 預設與合法值 | owner / effect / scope |
| --- | --- | --- | --- |
| `path_grid_mode` | numerical_control / advanced | `fixed`（維持既有 grid 選擇）或 `adaptive`；預設 `fixed` | Stage 1 `COM.build_all_paths()`；method、accuracy、cost；不由後續 stages 讀取 |
| `fine_grid_df` | numerical_control / advanced | 正 finite Hz；預設 `1e6` | Stage 1 adaptive；accuracy、cost；fixed 忽略 |
| `relative_threshold` | numerical_control / advanced | `None` 或有限非負數；預設 `1e-3` | Stage 1 adaptive 注入 `LinkSegment`；accuracy、cost；fixed 忽略 |
| `absolute_threshold` | numerical_control / advanced | `None` 或有限非負數；預設 `None` | Stage 1 adaptive 注入 `LinkSegment`；accuracy、cost；fixed 忽略 |

上述名稱與 profile mapping 屬實作目標，並非宣稱 workbook 已暴露。兩種
threshold 在 adaptive 至少一項啟用；raw 值由 API／workbook 提供，effective
值由 adapter 的 preset/profile 解析後寫入 `COMConfig.num`，每個欄位的 raw、
effective、source 與 override 依既有 adapter provenance 機制輸出。未明訂
profile 的欄位繼承 project 值；既有 SiCoPR profile 未額外覆寫 grid mode，
因此預設採 fixed，也可由使用者明示 adaptive 進行比較；整體數值相容仍需
驗證。介面正式暴露前應核對既有
workbook mapping、override 與 config inventory；不可將候選狀態誤記為已實作。

## Adaptive Stage 1

### Fine grid 與有效範圍

- 初始 fine-grid target df 預設以 1 MHz 作設計起點，允許 numerical control
  設定。此設計假設 1 MHz 足以涵蓋實務有效量測；實際容量以 cfg 計算。
- 以完整 oversampled response 逐條評估。相對與絕對 amplitude threshold
  可各自設定，`None` 表示不啟用；adaptive 第一版預設 relative `1e-3`、
  absolute `None`，至少啟用一項 threshold。`1e-3` 是暫定設定而非經驗證
  的精度標準。threshold 是 concrete input，不傳整個 COM policy 給工具。
- `LinkSegment.effective_length()` 回傳 samples 的整數長度；為保留起終點，
  可提供同判斷規則的 `effective_range()`，以 `[start, stop)` 表示範圍。
  兩者以同一套邊界邏輯實現，不用長度猜起點。
- 每項 threshold 為 finite、非負數值；relative threshold 乘各 response
  的 peak amplitude，absolute 使用 IR amplitude 的單位。兩項同時啟用時
  以 OR 判定，sample amplitude 嚴格大於啟用門檻之一即有效；兩項均為
  `None` 時保留完整 record。無 sample 通過時回傳空範圍、長度 0；Stage 1
  的錯誤／零 response 處理須與既有 `LinkSegment` 驗證相容，不得靜默建立
  無意義 path。實際 threshold 預設數值需以實驗確定，不假稱已驗證。

### FFE margin 與候選 grid

有效範圍需分別加上 RX FFE pre/post margin。已知 DTE layout 時採用
`d_w` 與 `N_max - 1 - d_w` UI；沒有 FFE 資訊時前後各 50 UI。實際索引
方向必須依既有 tap 與 convolution convention 核對。

每條 response 先將有效範圍起點向下、終點向上取至整數 UI，再加上
FFE margin，形成理想窗並檢查 fine-grid 邊界。選定各群的 cfg 長度後，
再將理想窗在邊界允許範圍內盡量置中延伸至完整 cfg 長度，作為裁切窗。

候選長度為 `2**k UI`，`k = 7..16`；對應 `Nfft = UI * per_ui`。選最小
能涵蓋有效範圍與 margin 的候選；超過最大候選時明確報錯，不默默裁短。
Fine-grid record 邊界與 zero padding 不得憑空引入未核准的 fallback。

### Victim：兩輪與共同時間參考

1. 第一輪建立 victim fine-grid response，以 actual `pulse` 的 causal IR
   判斷雙邊有效範圍，加入 margin，選擇 `victim_cfg` 及共同 window。
   window 長度採候選 UI，起點與終點均落在 fine-grid 的整數 UI。
2. Actual 與 `pulse_no_txffe` 使用相同 TXFIR 結構：前者採實際 coefficients，
   後者採 main-only preset。兩者須有共同原始時間參考及 pipeline delay。
3. 第二輪以相同 fine grid 重建；採 actual `pulse.causal_shift_samples`
   對 preset `raw_ir` 套用相同 circular shift。兩條 IR 使用完全相同的
   window 原樣複製，建立 `victim_cfg` responses，不以 production grid
   重新從 TF 計算 pulse，也不對 preset 再執行自己的 causal shift。
4. 將 window、shift 等只作局部中間資料；輸出完成後釋放 fine-grid 暫存。

Actual pulse 單獨決定 window 是明確設計；不得暗中改成 actual／preset
有效範圍的聯集。Preset 窗外能量須量測並記錄，不預稱一定為零。

### XT：獨立兩輪

Victim 完成後才開始 XT 群。第一輪逐條建立 fine-grid pulse，取得各自
有效範圍與 margin，以最大長度需求選共同 `xtalk_cfg`；不以不同 paths
的起點／終點取時間軸聯集。第二輪逐條重建，依各自的 window 裁切至
共同 grid 長度，完成一條即釋放其 fine-grid response。不同 XT 不要求
共用原點；每個 window 的起點與終點均落在 fine-grid 的整數 UI。目前是
各自選 worst sampling phase、各自處理後再合併。
若個別 XT 的有效範圍靠近 fine-grid 邊界而無法容納 margin，可整數 UI
平移該 XT 的時間參考以取得空間，不補零、不要求與其他 XT 對齊；不得
讓有效範圍平移後跨越 record 邊界。此平移與 threshold 以下資料的繞回
影響必須驗證；無法容納時明確報錯。

### 記憶體與時間語意

裁切時複製所選 samples，避免 output array view 持有 fine-grid array；
shared filters 與 report objects 不得將 fine-grid references 帶出 Stage 1。
`LinkSegment.from_ir()` 的現有長度、能量與 causal 檢查不自行放寬。
若這些檢查使有效資料無法輸出，先提供可重現數據，再討論修改範圍。

Continuous TF 與 bilinear IIR 都必須遵守 victim 共同時間參考；reference
`bilinear_iir` 保留既有 intermediate 截尾。新增 `bilinear_fine_grid` 不在
IIR 前截尾，以 actual pre-CTLE IR 決定 shift、preset 套用相同 shift，
XT 各自決定 shift；零 state IIR 和 unit pulse 等長處理。兩個方法各自
驗證；不把不同 grid 的 shift sample 數直接當成同一物理時間。

## Stage 2–7 介面與計算

| Stage | 契約 | 對目前實作的影響 |
| --- | --- | --- |
| 2 Pre-DTE | victim 抽樣 response 沿用 victim cfg；每條 XT 的 worst-phase `SampledResponse` 沿用其 `pulse.cfg`。PSD owner 依 NUM-003 選 record。 | 不再將 XT 降為失去 cfg 的 ndarray 後，以 `self.cfg.link` 統一包裝。 |
| 3 Sampling search | 保留既有 phase sweep、MSE 比較與最佳 bundle；共同 `per_ui` 不代表 response 必須等長。 | 調整 Stage 2 的呼叫接線，不增加 grid-mode 分支。 |
| 4 MMSE DTE | 以 victim `h_dsamp` 和 PSD autocorrelation `R_n` 計算；兩者不要求等長。`H_rxffe` 使用 PSD record cfg。 | 保留 solver；驗證各至少 `N_max`、cursor／DFE 需求。 |
| 5 Post-FFE | victim `h_w`、`h_ISI`、`h_w_J` 用 victim cfg；各 `h_XT_w` 沿用來源 XT cfg。所有 response 固定執行 circular convolution，輸出長度保持輸入 cfg 的 sampled length。 | 移除 ALG-011 selector 及單一 `response_cfg` guard；不讀 Stage 1 mode，也不執行 linear-convolution overflow guard。 |
| 6 DFE COM | ISI、XT、DDJ 分別建立 PMF 再合併，不要求輸入 response 等長。 | 核對主要與 clipping reconstruction 路徑，僅修改必要介面。 |
| 7 MLSD | 從 pre-DTE XT、TX-noise、jitter 及 post-FFE ISI 建立 PSD；NUM-003 的 record 選擇僅在 owner 內處理。 | `full` 以參與運算最長 response grid 為 record；移除單一 post-FFE cfg 依賴。 |

Pre-DTE 與 MLSD 各自為 NUM-003 PSD owner：`full` 使用本次參與 PSD 加總
的最長 response grid，較短者補零；`truncated` 使用 `num_trunc_ui`，依需
截切或補零。XT 先由完整 response 選 phase，再於兩個 PSD owner 各自選取
最大能量的 `num_trunc_ui` window；其他 response 仍取前段。同能量時取最早
window。原始 response 不修改。PSD record 與 victim／XT response grid
是不同用途；Stage 5 不重新選擇 NUM-003。

Adaptive 設計假設 threshold 與 FFE margin 已使 circular convolution 的
繞回部分不具顯著影響；此為待驗證假設，不保證所有 threshold、waveform
與 tap 組合都成立。Fixed-grid 的容量由使用者指定，grid 不足時 circular
wrap 可能有顯著影響。統一 circular 對應現有 SiCoPR profile 的 Stage 5
realization，但其他時間對齊及 grid 修改仍可能影響整體數值對齊。

## 影響的函數與文件

| 層級／對象 | 修改責任 |
| --- | --- |
| L1 `COM.build_all_paths()` | grid mode 唯一 owner，組織兩種完整 path 建立。 |
| L2 path builders | 依 concrete cfg 建立 path／shared，配合逐組兩輪與 production output。 |
| L5 `LinkSegment` | 有效範圍／長度 utility；現有 `from_ir()` contract 原則保留。 |
| L3 `COM._build_pre_dte_psd()`、`COM.build_mlsd_noise()` | 各自建立 NUM-003 PSD record 並加總。 |
| L2 `COM.calculate_post_ffe_imp()` | 每條 response 使用來源 cfg，固定 RX FFE 處理。 |
| `COMPostFFEEqChannelStatus` | 保存各自 response，不再要求共用單一 cfg；清理 ALG-011 status。 |
| Config／profile／registry／stage contracts | 新 grid mode 與 controls、移除 ALG-011、更新 consumer 與 call tree；以各文件既有權責為準。 |

實際私有 helper 名稱以清楚表達完整功能為原則，不因本表強制新增 wrapper。
具體 public config 欄位、預設與向現有 workbook／profile 的遷移應先核對
專案 configuration contract；不將此草案寫成目前已實裝的權威現況。

## 驗證與完成條件

1. 固定／adaptive 兩種 mode，selector 僅在 Stage 1 owner operational read；
   後續 stages 使用輸入 response cfg，且輸出不持有 fine-grid references。
2. 有效範圍雙邊界、門檻組合、FFE margin、候選長度、整數 UI window、
   上限與無 XT；victim 共同 shift／window，XT 各自 window，兩輪可重現。
3. Continuous／bilinear 時間對齊、preset TXFIR、preset window 外能量、
   既有 `from_ir()` checks 與 bilinear 早期截尾之影響；量測 peak memory。
4. Stage 2、5 的 cfg preservation；fixed／adaptive 皆採相同 circular FFE，
   比較現有 SiCoPR circular 實現並量測 adaptive 繞回影響；NUM-003 `full`
   補零和 `truncated` 截切，不修改原 response。
5. Stage 4 長度／cursor、Stage 6 clipping 與不同長度 PMF、Stage 7
   `R_ni` 至少 `trunc_len + 1`、各種 execution target 的相應邊界。
6. 核對適用 fixed case 的 baseline、預期數值變動與容許差異後，執行
   focused tests、適用 regression 和 intermediate／final COM 檢查；不得
   修改 golden 或放寬 tolerance 只為通過。資料不足時停止等候決策。
7. 同步 config、registry、stage/call tree 與 validation 權威文件；確認
   ALG-011 清理及 branch review 狀態，依專案流程完成隔離整合與驗證。

本契約不主張現有 production 已符合上述行為，也不主張 IEEE compliance、
完整 SiCoPR 等價或任何尚未取得的數值驗證結果。
