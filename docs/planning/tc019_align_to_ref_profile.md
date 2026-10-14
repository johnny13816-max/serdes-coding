# TC-019 — 178A 單一 reference 對齊模式

狀態：已核准，工作樹實作與相關回歸通過；固定 case 端到端驗收尚未通過。

## 目標與邊界

- 新版 178A `fixed_config` 僅顯示 `align_to_ref`，預設 `False`。
- `True` 集中解析已核實的 SiCoPR／COM MATLAB 4.17 方法；D3.0
  一般模式與 93A 數值保持不變。舊 workbook 個別 policy 仍可讀。
- `Pmf1D` 實作通用方法（最近格點、Gaussian 取樣、uniform 端點、
  ordinate interpolation）；依 [TC-019R](tc019r_reference_preset_resolution.md)，
  只有 178A Excel adapter 知道 reference profile，model 只接收具名方法。
- Case 輸入的 S4P、截止頻率和 reference provenance 必須另外一致；
  `align_to_ref` 不會偷偷裁切原始 100 GHz S4P。
- pre-DTE 使用 fine-grid 規則；final COM／MLSD 使用未正規化 RX FFE
  座標的 `dy_rel_As*As`，除以主 tap gain 後等於 reference grid。

## 驗收

以 `sicopr_akinwale_vendorx_22db` 的固定候選比對 `P_s`、`P_n`、
ISI／XT／DD／Gaussian／quantization PMF、`V_qc`、`R_n`、MSE 與 COM。
先核對每種 PMF 方法的中間陣列，再評估最後 COM。`False` 必須維持
既有回歸；93A 不變。若 fixed-grid overflow guard 擋住端到端執行，
使用 `%TEMP%` 專用稽核資料分離驗證 PMF，不修改 guard 或宣稱端到端通過。

2026-10-11 中間驗證：相同輸入的 Gaussian PMF 長度 1889，逐格最大
機率差 `2.02e-16`；量化 PMF 長度 32699，逐格最大機率差 `7.98e-17`。
固定 67 GHz、phase 22 的暫存 post-FFE 響應餵入正式 final PMF 方法，
得到 `COM_DFE=1.5247607834259893 dB`；SiCoPR 為 `1.524760783 dB`。
此相等含比值抵消：模型／reference 的正規化 `As` 分別為
`5.372706/5.374290 mV`，`A_ni` 分別為 `4.507700/4.509030 mV`。
相同 phase 的 MSE 仍差 `1.277871e-6`。原始 case 的完整 single-run
在 `post_ffe XT3` fixed-grid overflow guard 停止；因此尚未通過正式
端到端驗收。

完整 `tests/` 回歸：`120 passed, 2 subtests passed`。原有大量未提交的模型與
文件修改使 TC-019 無法安全地單獨提交；目前以 `%TEMP%` 的修改前
備份界定本次增量，未把其他修改混入提交。

2026-10-12 補充：上述 `MSE` 與 `COM_DFE` 是只在 final PMF 套用
TC-019 的較早比較，不能當作完整 profile 的 before/after。固定 67 GHz、
phase 22，從 pre-DTE 起啟用 `align_to_ref=True` 的 MSE 為
`0.006192113355325546`，SiCoPR 同候選為 `0.0061912610245246705`
（差 `+8.523308e-7`）。同輸入的 `P_s` L1 差 `6.97e-15`、`P_n`
最大 CDF 差 `3.14e-11`；使用專案自己的 waveform 才出現 PMF 差。
第一個已定位的算法分歧是 [G-009／TC-020](tc020_ctle_pulse_realization.md)
的 CTLE pulse realization，並非已驗證的 PMF 建構錯誤。

回退邊界：`%TEMP%/serdes-tc019-20261011` 的修改前備份；待既有
未提交核心修改整理後才建立 TC-019 隔離 commit。
