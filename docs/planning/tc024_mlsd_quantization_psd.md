# TC-024 — MLSD quantization PSD realization

狀態：**closed**。已核准、已實作，current-working-tree golden 與完整回歸通過；使用者於 2026-10-15 驗收結案。提交狀態另由 repository workflow 管理，不重新開啟模型契約。

## 目的

一般模式依 Eq. 178A-54，將完整 pre-DTE `S_n` 經完整 RxFFE response filtering。
reference 模式重現 SiCoPR：`S_rn/S_tn/S_xn/S_jn` 經完整
`|H_rxffe|²`，`S_qn` 維持 white，只乘 RxFFE main tap `|w[d_w]|²`。

```text
pre_dte_filtered:
  S_ni = (S_rn + S_tn + S_xn + S_jn + S_qn)|H_rxffe|² + S_an + S_isi

main_tap_white:
  S_ni = (S_rn + S_tn + S_xn + S_jn)|H_rxffe|²
       + |w[d_w]|² S_qn + S_an + S_isi
```

## 責任邊界

- runtime control 為 `COMPolicyConfig.mlsd_quantization_psd`。
- `build_mlsd_noise()` 擁有 MLSD PSD 組合；不得回寫 pre-DTE／MMSE PSD。
- `align_to_ref=True` 由 workbook adapter 展開成 `main_tap_white`；model 不讀
  `align_to_ref`。
- workbook 不增加獨立 method row。
- `COMMLSDNoiseStatus` 保存本次實際使用的 `S_qn/sigma_qn`。

## Counterfactual evidence

固定 Akinwale case 只替換 MLSD `S_qn` 後：

| Result | Project counterfactual | SiCoPR | Gap |
|---|---:|---:|---:|
| delta COM | 1.371137901443 dB | 1.371137901447 dB | -4.00e-12 dB |
| COM MLSD | 2.895898684869 dB | 2.895898684873 dB | -4.01e-12 dB |

## Current-working-tree golden evidence

正式 `align_to_ref=True`、`target=full` run：selected position `5`、MSE
`0.0061912610245255335`、COM DFE `1.5247607834259893 dB`、delta COM
`1.3711379014472564 dB`、COM MLSD `2.895898684873246 dB`。相對 SiCoPR
COM MLSD gap 為 `-1.29e-14 dB`。focused validation：27 passed、2 subtests
passed；完整 regression：133 passed、2 subtests passed。

正式 artifact 位於 `%TEMP%/serdes-mlsd-qpsd-20261015/tc024_working_tree_result.json`。
使用者已依上述 working-tree evidence 驗收結案。
