# TC-022／TC-022A — MMSE noise-correlation record grid

**狀態：NUM-003（legacy B-005）closed（2026-11-01）；本文保留歷史驗證與 closure evidence。**

## 契約

channel／pulse 仍使用 `COMConfig.link`。目前正式名稱為
`COMConfig.num.eq_ch_imp_len` 與 conditional parameter
`COMConfig.num.num_trunc_ui`：
`full` 使用完整 one-sample/UI impairment response；`truncated` 在 PSD 前以
明示 UI 長度建立共同 record。所有 `S_rn/S_xn/S_tn/S_jn/S_qn` 必須在同一
PSD grid 相加，不能只替 `S_xn` 特判或修改 `LinkConfig`。

`truncated` 在 DFT 前明確截斷或補零 sampled response。crosstalk 必須先以
完整 oversampled pulse 選 Eq. 178A-18 worst phase，形成完整 one-sample/UI
`eq_ch_XT`，之後才由 Stage 2 `_build_pre_dte_psd()` 決定是否截短並建立
`S_xn`。完整 path
waveform、`h_dsamp` 與 status 內 full equivalent-channel responses 不變。

## Config 邊界

- project policy 欄位 `eq_ch_imp_len=full|truncated`；`num_trunc_ui` 只在
  `truncated` 時必填，且必須是合法偶數 UI 長度。
- 新 178A template 獨立曝露兩欄，預設 `full/blank`。
- 此欄位是 project policy，不由 Ad Hoc `num_ui_RXFF_noise` 映射。converter
  從 project template 自動產生該列與其預設空值；Akinwale case 明示保存 4096。
- `sicopr_reference_v1` 展開為 `truncated/4096`。model 不讀 profile selector。

Python 直接建立 `COMConfig` 時，`num` 的
`default_factory=COMNumericalControlConfig` 產生 `full / num_trunc_ui=None`。
由 template 建立的新 workbook 自動保留同一個
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

## NUM-003 closure evidence (legacy B-005)

2026-11-12 二次 ownership review 的最終修正確認兩個 semantic owners：Stage 2
`COM._build_pre_dte_psd()` 建立 pre-DTE `S_total/R_n`；Stage 7
`COM.build_mlsd_noise()` 建立 MLSD `S_ni/R_ni`。兩者都在各自 PSD 真正加總前
解析 record。舊 shared-state／forwarding helpers 已移除；Stage 3 不建 PSD，
Stage 5 只在既有 pre-DTE record 上建立 reporting transforms。

- XT phase selection 改為一律先讀完整 oversampled response；SiCoPR 五條 XT
  phase 在新舊順序下相同：`23, 7, 6, 31, 0`。
- production golden 保持 selected phase `5`、MSE
  `0.0061912610245255335 V²`、DFE COM `1.5247607834259893 dB`、final
  COM `2.895898684873246 dB`；`w`、`h_dsamp`、`R_n` digest 未變。
- Static ownership test 確認 `eq_ch_imp_len/num_trunc_ui` 在 `COM` production
  methods 中只由上述兩個 owners 讀取；focused `54 passed`、non-GUI
  `212 passed, 17 skipped, 2 subtests passed`、production golden `1 passed`，
  且未修改 golden。完整 collection 的 7 failures 是缺少外部 Hansel workbook、
  sandbox system temp 與 repo-internal basetemp provenance，未進入 NUM-003 path。
- template workbook 預設 `full/None`；SiCoPR workbook 明示
  `truncated/4096`。兩者保留獨立 project-config control。

