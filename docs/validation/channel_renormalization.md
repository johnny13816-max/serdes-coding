# 178A channel representation normalization

狀態：**ALG-005 retired as non-branch（2026-11-07）**

## 規範依據與決策

IEEE P802.3dj/D3.2 Annex 178A.1.3 先要求 measured single-ended
S-parameters 使用／轉換至 single-ended `R0`，再由 single-ended matrix
轉為 mixed-mode Sdd。D3.0 的 measured differential S-parameter
renormalization 契約仍保留為歷史證據，但不再是 178A measured S4P 的
平行合法算法。

因此移除 `policy.channel_renormalization_order`：

```text
measured S4P
  -> renormalized(R0) on all four single-ended ports
  -> optional measured-frequency limit
  -> s4p_to_s2p(port_order)

native differential S2P
  -> optional measured-frequency limit
  -> renormalized(2*R0)
```

S2P 路徑是 input representation dispatch，不是任意 fallback。只要檔案
具有四埠資訊，就必須走 D3.2 S4P 流程；S4P 解析、port count 或轉換失敗
必須報錯。

## Ownership contract

- 唯一語意 owner：`models/com_178a/path_stage.py::_build_channel_under_test()`。
- `SparamModel.from_touchstone()` 只偵測 representation；`renormalized()` 與
  `s4p_to_s2p()` 執行具名數值操作。
- `COM.build_all_paths()` 不傳 selector；`_build_path()` 不得對完成的 `S_ch`
  再做 renormalization。
- victim、NEXT、FEXT 可各自是 S4P 或 native S2P，之後仍共同對齊 measured
  intersection grid。
- `*_s4p_path` 暫時保留為 legacy-compatible 欄位名稱；檔案實際 port count
  才決定 representation。
- 93A 的 Sdd-first 契約不在本次變更範圍。

## Compatibility and claim boundary

- `COMPolicyConfig`、reference preset、conversion mapping 與 selectable-control
  matrix 不再暴露 `channel_renormalization_order`。
- 舊 178A workbook 若仍帶該欄位會收到 migration error，不會靜默忽略。
- tracked 178A templates/cases 原本已無該欄位，無需重寫。
- 此結案證明 178A ingestion order 對齊 D3.2 的上述條文；不宣稱整個 model
  已取得 IEEE compliance、官方工具等價或 silicon correlation。

## Validation evidence

- equation／owner／profile／path focused tests：`52 passed`。
- S4P oracle、native S2P oracle、mixed S4P/S2P collection、unsupported port
  count no-fallback、legacy selector migration error 均有專項測試。
- SiCoPR production golden：`1 passed`；`COM_DFE=1.5247607834259893 dB`，
  final `COM=2.895898684873246 dB`，MSE 與 intermediate digests 不變。
- Python 3.7 standalone utility export rebuild／validator：passed。
- 9 份 tracked 178A case/template workbook selector scan：0；branch matrix
  已移除 ALG-005，formula-error scan：0，重新匯出與視覺檢查通過。

歷史 D3.0 修正與 TC-016 A/B 證據仍可從 Git history 與
`docs/planning/tc016_channel_renormalization_order.md` 追溯；不得將其舊
selector 說明當成目前 runtime contract。
