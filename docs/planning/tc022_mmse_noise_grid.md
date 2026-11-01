# TC-022／TC-022A — MMSE noise-correlation record grid

**狀態：B-005 closed（2026-11-01）；本文保留歷史驗證與 closure evidence。**

## 契約

channel／pulse 仍使用 `COMConfig.link`。目前正式名稱為
`COMConfig.policy.eq_ch_imp_len` 與 conditional parameter `num_trunc_ui`：
`full` 使用完整 one-sample/UI impairment response；`truncated` 在 PSD 前以
明示 UI 長度建立共同 record。所有 `S_rn/S_xn/S_tn/S_jn/S_qn` 必須在同一
PSD grid 相加，不能只替 `S_xn` 特判或修改 `LinkConfig`。

`truncated` 在 DFT 前明確截斷或補零 sampled response。crosstalk 必須先以
完整 oversampled pulse 選 Eq. 178A-18 worst phase，形成完整 one-sample/UI
`eq_ch_XT`，之後才由 Shared L3 決定是否截短並建立 `S_xn`。完整 path
waveform、`h_dsamp` 與 status 內 full equivalent-channel responses 不變。

## Config 邊界

- project policy 欄位 `eq_ch_imp_len=full|truncated`；`num_trunc_ui` 只在
  `truncated` 時必填，且必須是合法偶數 UI 長度。
- 新 178A template 獨立曝露兩欄，預設 `full/blank`。
- 此欄位是 project policy，不由 Ad Hoc `num_ui_RXFF_noise` 映射。converter
  從 project template 自動產生該列與其預設空值；Akinwale case 明示保存 4096。
- `sicopr_reference_v1` 展開為 `truncated/4096`。model 不讀 profile selector。

Python 直接建立 `COMConfig` 時，`policy` 的 `default_factory=COMPolicyConfig` 產生
`full / num_trunc_ui=None`。由 template 建立的新 workbook 自動保留同一個
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

## B-005 closure evidence

- XT phase selection 改為一律先讀完整 oversampled response；SiCoPR 五條 XT
  phase 在新舊順序下相同：`23, 7, 6, 31, 0`。
- production golden 保持 selected phase `5`、MSE
  `0.0061912610245255335 V²`、DFE COM `1.5247607834259893 dB`、final
  COM `2.895898684873246 dB`；`w`、`h_dsamp`、`R_n` digest 未變。
- 完整非 GUI regression：`187 passed`, `1 deselected`, `2 subtests passed`。
  deselected 項目只因目前 Python/Tk runtime 缺少可用 Tk library；其餘先前
  sandbox temp-path failures 已在 repository 外可寫 temp root 重跑通過。
- template workbook 預設 `full/None`；SiCoPR workbook 明示
  `truncated/4096`。兩者保留獨立 project-config control。

