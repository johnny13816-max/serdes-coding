# Utility grid 契約

`LinkConfig(fb, per_ui, target_df)` 描述一個 concrete grid；fixed run 可共用
單一物件，178A adaptive run 可有 victim／XT／report grids。每個
`LinkSegment`、`SampledResponse` 與 `SampledPSD` 維持自己所屬 cfg；
`ContinuousPSD` 的原始任意量測 grid 可以尚未綁定 cfg。
`SampledPSD.filtered_by()` 只接受相同格點，不暗中 regrid。

`cascade_ir(..., force_grid=True)` 先計算完整線性卷積；連續時間
`LinkSegment` 仍乘 `dt`，離散時間 `SampledResponse` 不乘 `dt`。正式輸出保留
原 `cfg`，不建立新的 NFFT。對超出原 grid 的部分，必須同時滿足：

```text
max(abs(tail)) / max(abs(full)) <= 2e-3
sum(tail**2) / sum(full**2) <= 1e-6
```

當兩個輸入的精確有限支撐可由尾端零填充判定時，完整支撐長度若超過
grid，無論尾端大小都直接報錯。量測響應才使用上述數值界限。零響應的
兩個比值視為零。任一界限超出時拋出 `GridOverflowError`，包含 grid
長度、完整卷積長度及兩個實測比值。界限是工程數值品質政策，不是 IEEE 規範
或普遍的 COM 誤差保證。`force_grid=False` 可回傳完整卷積的新 grid，或在 caller
明示 `output_cfg` 時保存到該共同 grid；這是 diagnostic/caller-owned utility
contract，不是獨立 selectable branch。量測 TF/IFFT 尾端未必精確為零，因此通過檢查只表示
目前記錄的裁除量在政策內，不證明未量測的物理尾端為零。

同 grid 的 TF 串接與固定 grid 的 IR 串接，僅在卷積完整落入 grid、時間
原點一致時逐頻閉環。TF-originated `LinkSegment.ir` 可能是已移位的 causality
view；比較複數 TF 前須對齊 `raw_ir` 與該 shift。PSD 功率閉環為
`SampledPSD.to_sigma()**2 == to_autocorrelation()[0]`；連續時間 PSD 的
sampling aliasing 不宣稱可逆。

178A Stage 5 使用 fixed circular shift-sum，每條 response 保留自己的 input
cfg，不套用 `cascade_ir` 的 linear overflow guard。Stage 2 與 Stage 7 的
NUM-003 PSD owner 分別決定 PSD record；`full` 容納所有輸入，較短者補零。
一般 utility 若拋出 `GridOverflowError`，search 的失敗處理仍適用；這不代表
Stage 5 circular FFE 會產生 linear overflow。

## Effective IR range

`LinkSegment.effective_range()` 以目前 `.ir` 的時間參考檢測雙邊 amplitude
範圍，回傳 sample 半開區間 `[start, stop)`；`effective_length()` 回傳其
sample 數。兩者接受 optional relative／absolute threshold，須 finite 且
非負；relative 以同一 response peak amplitude 為準。兩者啟用時採 OR，
嚴格大於任一門檻為有效；未啟用任何 threshold 時回傳完整 record，沒有
sample 通過時回傳空範圍及零長度。工具不決定 COM grid、FFE margin 或
跨 response 時間對齊。
TF-originated `raw_ir` 只計算與驗證未平移的 IFFT，不會因此選擇 causal
shift；只有讀取 `ir`／`causal_ir` 才依既有邏輯進行 causal alignment。

## SBR-to-eye contract

`LinkSegment.eye_traces()` 將 caller 提供的實際 symbol amplitudes 以 `cfg.per_ui`
間隔放入 impulse train，再與 `LinkSegment.sbr` 做完整線性卷積：

```text
y[n] = sum(symbols[k] * sbr[n - k*per_ui])
```

它只負責 deterministic LTI waveform reconstruction 與 UI-window folding；不產生
隱藏 PRBS，不加入 noise、jitter、CDR、BER contour 或 statistical eye。輸入記錄以
零 symbol prehistory/posthistory 處理。`alignment="main_cursor"` 以
`argmax(abs(sbr))` 對齊 eye 中央；`record_start` 以每個 symbol launch 對齊。
`discard_ui` 由 caller 明確決定，不使用 tail threshold 猜測 channel memory。

`plot_eye()` 只呼叫 `eye_traces()` 並呈現同一組資料，不重算另一條 waveform path。
