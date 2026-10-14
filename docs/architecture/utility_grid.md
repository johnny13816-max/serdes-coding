# Utility grid 契約

`LinkConfig(fb, per_ui, target_df)` 在一次 COM run 只建立一次。正式的
`LinkSegment`、`SampledResponse`、`ContinuousPSD` 與 `SampledPSD` 運算沿用同一
物件；`ContinuousPSD` 的原始任意量測 grid 可以尚未綁定 `cfg`，對齊到 run-level
grid 後才綁定。`SampledPSD.filtered_by()` 只接受相同格點，不暗中 regrid。

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
或普遍的 COM 誤差保證。`force_grid=False` 回傳完整卷積及新 grid，僅用於診斷；
COM 正式流程不使用。量測 TF/IFFT 尾端未必精確為零，因此通過檢查只表示
目前記錄的裁除量在政策內，不證明未量測的物理尾端為零。

同 grid 的 TF 串接與固定 grid 的 IR 串接，僅在卷積完整落入 grid、時間
原點一致時逐頻閉環。TF-originated `LinkSegment.ir` 可能是已移位的 causality
view；比較複數 TF 前須對齊 `raw_ir` 與該 shift。PSD 功率閉環為
`SampledPSD.to_sigma()**2 == to_autocorrelation()[0]`；連續時間 PSD 的
sampling aliasing 不宣稱可逆。

178A post-FFE、MLSD 的正式物件沿用 `cfg.link`。若單一 run 發生 overflow，
該 run 報錯；search final 將 candidate 記為 `grid_overflow`、不給有效 COM，
並依 MSE 順序補位。所有候選均超界時才使整個 search 因 grid 容量失敗。
增大時間窗需從原始 channel／config 以較小 `target_df` 重跑，不得替舊 IR
補零宣稱為新量測結果。
