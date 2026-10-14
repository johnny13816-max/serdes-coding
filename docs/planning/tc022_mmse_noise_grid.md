# TC-022／TC-022A — MMSE noise-correlation record grid

**狀態：已核准並在工作樹實作。**

## 契約

channel／pulse 仍使用 `COMConfig.link`。MMSE noise PSD 與 correlation 由
`COMConfig.policy.noise_grid_method` 與 `noise_grid_num_ui` 控制：`analysis_grid` 沿用 path grid；`fixed_ui`
以明示 `num_ui` 建立共同 PSD grid。所有 `S_rn/S_xn/S_tn/S_jn/S_qn` 必須
在同一 noise grid 相加，不能只替 `S_xn` 特判或修改 `LinkConfig`。

`fixed_ui` 在 DFT 前明確截斷或補零 sampled response。crosstalk 在
oversampled pulse 截至 `num_ui*per_ui` 後選 Eq. 178A-18 worst phase，再以
`num_ui` 點 circular DFT 建立 `S_xn`。完整 path waveform 與 `h_dsamp`
保持原 analysis grid。

## Config 邊界

- project policy 欄位 `noise_grid_num_ui`：留白代表 `analysis_grid`；正偶數代表
  `fixed_ui`。
- 新 178A template 自動包含此欄位且預設留白，因此一般模式保留既有輸出。
- 此欄位是 project policy，不由 Ad Hoc `num_ui_RXFF_noise` 映射。converter
  從 project template 自動產生該列與其預設空值；Akinwale case 明示保存 4096。
- `align_to_ref=True` 在 adapter 展開 `fixed_ui`；若 workbook 未提供數值，
  reference preset 使用 4096。model 不讀 `align_to_ref`。

Python 直接建立 `COMConfig` 時，`policy` 的 `default_factory=COMPolicyConfig` 產生
`analysis_grid / num_ui=None`。由 template 建立的新 workbook 自動保留同一個
空值 default；converter 將該列分類為 optional project policy，而非 Ad Hoc
mapping。這三個入口因此具有同一個一般模式 default。

## 驗證結果

正式 Akinwale reference profile selected phase 為 5，`h_dsamp` 不變。專案
自己的五條 crosstalk pulse 經 4096-UI noise grid 後：

- `R_xn` 對 SiCoPR 最大差 `2.69e-21 V²`；
- total `R_n[0:87]` 最大差 `3.71e-21 V²`；
- MSE `0.0061912610245255335`，對 reference 差 `8.63e-16`；
- normalized FFE 最大差 `2.50e-13`；DFE 差 `-1.42e-13`。
- 正式 DFE run：`A_s=0.31666666666666665 V`、
  `A_ni=0.2656833333333335 V`、`COM_DFE=1.5247607834259893 dB`。
- 完整 regression：`129 passed`、`2 subtests passed`。

修改前 reference profile 使用 10626 UI，MSE 差 `+4.513994e-7`。差異來自
4096 UI 之後的 crosstalk tail 被納入 covariance；不是 S-parameter、filter、
`h_dsamp` 或 MMSE 方程差異。暫存稽核資料位於
`%TEMP%/serdes-tc021-rn-audit/`，修改前備份位於
`%TEMP%/serdes-tc022-20261013/`。

