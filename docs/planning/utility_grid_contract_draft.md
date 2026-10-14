# TC-013 — Run-level fixed grid 與 search overflow 補位

狀態：Core Model Change Contract 與 search overflow warning／補位政策已核准；固定 grid、overflow guard 與 search 補位已在工作樹實作。固定 case、utility 與 search 補位測試通過。使用者於 2026-10-09 指示停止實際 search 驗收並回到 COM model 對齊主線；本 TC 暫緩，實際 search sweep 與獨立 model commit 尚未完成，故未結案。現況入口見 [`active_contracts.md`](active_contracts.md)；現行行為以 `docs/architecture/utility_grid.md` 與版本 stage 文件為準。

## 本次批准的功能與檔案邊界

- **功能**：`LinkConfig` 由 run 建立一次；`SampledResponse`、`ContinuousPSD`、`SampledPSD` 可綁定同一 `cfg`；`cascade_ir(force_grid=True)` 先算完整線性卷積，再檢查固定 grid 尾端。`False` 僅供完整卷積診斷。178A post-FFE／MLSD 沿用 run grid；single run overflow 報錯；search final 記 warning 與 `grid_overflow`、留空 COM 並依 MSE 補位。
- **受保護的 utility／model**：`src/serdes_coding/utilities/link.py`（`GridOverflowError`、`SampledResponse`／`LinkSegment` 的 cfg、TF／IR cascade、完整卷積與溢出檢查）、`src/serdes_coding/utilities/psd.py`（兩種 PSD 的建構、filtering、addition 與 cfg 傳遞）、`src/serdes_coding/utilities/__init__.py`（error export）、`src/serdes_coding/models/com_model_178A.py`（pre-DTE PSD 建構、`calculate_post_ffe_imp()`、`build_mlsd_noise()` 的同 grid 流程）、`src/serdes_coding/models/com_model_93A.py`（noise PSD cfg 綁定）。僅限上述 grid 行為，不改 spec 公式或其他 impairment 定義。
- **search**：`src/serdes_coding/search/com_search_178A.py` 的 `finalize_search()`、status 與 CSV 欄位，僅限 typed overflow status、指標、warning 與 MSE 補位。
- **測試**：`tests/test_fixed_grid_contract.py`、`tests/test_com_search_178A_grid_overflow.py`、`tests/test_com_model_178A_mlsd_noise.py`。
- **文件**：`docs/architecture/utility_grid.md`、178A post-FFE／MLSD stage 與 call/status tree、相關索引及本契約狀態。既有其他檔案與搬移不屬 TC-013。
- **驗收與提交**：utility 公式／cfg identity／overflow 測試、固定 SiCoPR case 中間量、完整回歸和實際 search sweep；model 改動須獨立 commit，search orchestration 另行隔離。現有原檔與 index 有其他未提交修改，不能整檔提交。

以下保留 2026-10-08 的唯讀設計草案與當時未決問題；其中「現行」與「尚待決定」指**當時**狀態，不能覆蓋上方已核准與已實作的結論。未解項目只有顯式跨 grid PSD 對齊 API、共享 cfg 的可變性政策及跨 case／search 驗證，需另立範圍後處理。

<details>
<summary>展開 2026-10-08 設計過程與當時的待決問題</summary>

## 目標與範圍

核心目標：同一條 utility/model pipeline 不論以頻域 filter cascade 或時域 IR cascade 執行，從輸入到正式輸出都由**同一份 run-level `LinkConfig`** 管理；RX FFE 等中途 stage 不產生另一份 post-stage config。讓 `LinkSegment`、`SampledResponse`、`ContinuousPSD`、`SampledPSD` 的 grid 所有權與轉換前提明確。相同物理運算經 TF／IR 或 PSD 路徑表達時，對可閉環的路徑檢驗數值一致性；含 sampling、aliasing 或資訊丟失的路徑不宣稱可逆。

## 已同意的介面原則

1. COM run 繼續由既有 `fb`、`per_ui`、`target_df` 建立**一份** `LinkConfig`，由此固定 `dt`、NFFT、時間窗及 CT/sampled 對應 grid；時域與頻域正式輸出都沿用它。不加入自動推算或加長 NFFT。設定的時間窗不足時應明確失敗，由使用者調整 `df` 後重跑。
2. Utility 的正式 fixed-grid IR cascade 先計算完整線性卷積，再檢查放入既有 grid 會遺失的部分；超出明確數值界限就報錯，不循環折回、偷偷移動時間原點或更換 config。完整 `full` 結果仍可作為診斷／驗證輸出，不負責替 COM 決定新 grid。
3. TF cascade 與 PSD filtering 在同一 grid 上嚴格運算。`SampledPSD.filtered_by()` 不隱式 regrid；跨 grid 對齊使用有名稱、指定方法及量測積分功率變化的操作。
4. COM 正式路徑採單一 fixed-grid 策略，grid 容量由既有 `fb`／`df` 設定決定，utility 檢查是否足夠。`full` 僅供 utility 診斷和 fixed-grid 結果驗證；目前不新增 COM 使用者可切換的 grid policy 欄位。
5. IR 的有效支撐長度與 grid 容量分開描述。不能以 padded 陣列長度或「尾端剛好等於零」單獨判定有效物理支撐；頭端 precursor、時間原點和 CT/DT 縮放都需保留。

## 同一份 config 的驗收邊界

- `LinkSegment` 的 TF/IR cascade 輸入及正式輸出需維持同一個 `LinkConfig` 來源；不得以內容相似的新 `LinkConfig.from_Nfft()` 取代。跨 CT/sampled domain 時，使用原 config 已定義的 `freqs`／`theta`，不建立 stage-specific grid。
- 現行 `SampledResponse` 僅保存 `theta`／`fb`，`ContinuousPSD` 僅保存 `freqs`，`SampledPSD` 僅保存 `theta`／`fb`；它們目前沒有 `cfg` reference。因此「格點數值相同」尚不等於「物件沿用同一份 config」。後續 API 契約須決定這些物件如何顯式關聯 run-level config，不能靠隱式推斷。
- 閉環驗證除比較數值，也要檢查每個正式輸出仍歸屬原 config，以及 `freqs`、`theta`、NFFT／`sampled_nfft`、`fb` 與時間原點一致。config 共享後是否要禁止在建構後修改，亦須於實作契約決定。

## 固定 grid 的時域串接與容量檢查

- `LinkConfig` 繼續依 `fb`／`target_df` 建立 NFFT。對每次時域 cascade，utility 可暫時計算完整線性卷積以**檢查**容量，但正式輸出仍屬於原 grid。檢查不通過即報錯，指出目前 grid、溢出範圍及量測量；不替呼叫端選下一個 NFFT。
- 對真正有限長 taps，可用 `N_full = n_a + n_b - 1` 判斷精確容量；這是驗證量，不是新的 grid 決策機制。對量測 TF/IFFT 的有限記錄，尾巴未必精確為零，須檢查放入原 grid 時的溢出能量與峰值。該檢查僅保證**目前記錄**的卷積可放入 grid，不證明原始量測之外的物理尾巴已消失。
- 現行 `LinkSegment.cascade_ir()` 直接卷積兩個完整 padded IR 陣列；`SampledResponse.cascade_ir()` 先移除尾端的精確零值。兩者的長度增長規則不同，尚不能直接拿其中之一當通用的有效支撐定義。
- 若容量檢查不通過，COM 停止並要求調整現有 grid 設定；重跑時要由原始量測／模型輸入重新建構整條路徑，不得將已截斷的結果單純補零當成較長記錄。

## 預期閉環與非閉環

| 路徑 | 驗證關係 | 前提／邊界 |
| --- | --- | --- |
| `LinkSegment` TF → raw IR → TF | 同 grid 逐頻對齊 | 使用 raw IR、同一 CT FFT 與既有 `Fs` 縮放；causal view 的移位另行處理。 |
| `LinkSegment` → `SampledResponse` | 指定 phase/source 後與對應 IR downsample 對齊 | CT 與 symbol-rate grid 對齊；`raw` 和 `causal` 不可混用。 |
| sampled IR full convolution → 固定 grid TF；兩個 TF 直接相乘 | 逐頻對齊 | 有效卷積長度 `n_a + n_b - 1 <= sampled_nfft`，且時間原點一致。容量不足時 TF 乘法對應 circular convolution。 |
| `SampledPSD.to_sigma()²` ↔ `to_autocorrelation()[0]` | 同 grid 功率對齊 | one-sided rFFT 內部頻點與 DC/Nyquist 的權重一致。 |
| broadband `ContinuousPSD.to_sampled()` ↔ `SampledPSD.to_continuous_baseband()` | 不要求互逆 | sampling aliasing 丟失來源頻帶資訊；baseband view 不是 broadband inverse。 |
| CT PSD 先經 CT filter 再 sampling ↔ 先 sampling 再經 sampled filter | 不要求一般性可交換 | 多個 alias branch 的功率和與複數響應和，通常不能互換。 |

## 唯讀小案例證據（2026-10-08）

以專案 `.venv` 與 synthetic response 測試，未修改程式：

- CT TF → raw IR → TF 最大絕對誤差 `3.38e-16`；CT raw IR downsample 與指定 phase 的 sampled response 最大誤差 `3.19e-16`。
- 短 sampled IR：固定 `sampled_nfft=32`，卷積有效長度 4；TF 相乘與固定 grid 的 IR 卷積後 TF 最大絕對誤差 `2.29e-16`。現行 `SampledResponse.cascade_ir()` 回傳長度 4 的新 grid。
- 邊界案例：固定 grid 長度 32、完整卷積長度 33；TF 相乘的第 0 個 IR sample 為 `1.075`，完整線性卷積為 `1.0`。尾端 `0.075` 繞回，證明不能在容量不足時宣稱閉環。
- 平坦 `SampledPSD` 的 `to_sigma()²` 與 `to_autocorrelation()[0]` 均為 `1.0`；其 baseband `ContinuousPSD.to_sigma()²` 為 `0.96875`，後者不是已定義的逆向功率閉環。

## 尚待決定，不能由 utility 猜測

1. 有效支撐的表示：有限 taps 可用確切長度；CT channel 等非有限尾巴須定義時間原點、邊界能量與峰值檢查，不能單靠精確零值裁尾。
2. fixed-grid 容量檢查的數值界限：有限 taps 可精確檢查；量測響應須訂溢出能量、峰值與最終指標的容差。容差尚未指定，不能在實作時自行默認為安全裁切。
3. fixed-grid IR cascade 的 API 名稱、overflow error/report 結構、診斷用 `full` 結果形式，以及 CT `LinkSegment` 與 sampled response 是否共用 support 描述。
4. PSD 跨 grid 的顯式對齊方法與功率誤差報告；目前的 `np.interp` 不自動成為通用 utility 契約。
5. 對 93A／178A 的 pre/post impairment、MSE、PMF、MLSD 及 single/search run 逐邊界驗證後，再決定遷移次序。
6. `SampledResponse`／兩種 PSD 與 run-level `LinkConfig` 的關聯介面，以及共享 config 的可變性限制；目前只保存 grid arrays 的物件尚未滿足嚴格的同一 config 目標。

下一步先建立固定 `fb`／`df` grid 上的容量檢查案例、量測響應邊界診斷與固定 reference baseline，再提出列出檔案、函式、預期中間量、容差及 rollback 邊界的 Core Model Change Contract。此草案不授權修改 protected kernel。

</details>
