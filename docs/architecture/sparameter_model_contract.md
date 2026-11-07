# S-parameter model contract

## 目的

`SparamModel` 是量測或合成 S-parameter 的 representation boundary。它可以保存：

- `representation="s4p"`：完整 single-ended four-port；
- `representation="s2p"`：COM-style differential two-port Sdd。

Constructor 只讀取並保存輸入 representation，不執行 port reorder、mixed-mode
conversion、frequency limit 或 renormalization。每個數值操作都由具名方法顯式執行，
回傳新物件並保留 `source` 與 `history`。

## Public method boundary

| 類別 | Method | 責任 |
|---|---|---|
| Constructor | `from_sdd_array()` | 從 differential Sdd 建立 S2P。 |
| Constructor | `from_s4p_array()` | 保留完整 single-ended S4P。 |
| Constructor | `from_network()` | 按 Network port 數保存 S2P 或 S4P。 |
| Constructor | `from_touchstone()` | 讀取 Touchstone，不隱含轉換或 renormalization。 |
| Representation | `port_reordered()` | 將 S4P 實體 ports 重新排列成 canonical role order。 |
| Representation | `s4p_to_s2p()` | 依 `(tx_p, tx_n, rx_p, rx_n)` 顯式取得 Sdd。 |
| Representation | `s2p_to_synthetic_s4p()` | 建立可 round-trip 的 differential-only S4P。 |
| Network operation | `renormalized()` | 對目前 representation 做 reference-impedance renormalization。 |
| Network operation | `limited_to_frequency()` | 套用 measured-record frequency boundary。 |
| Network operation | `resampled()` | 在量測頻帶內重新取樣。 |
| Network operation | `extrapolated_to_dc()` | 對目前 representation 補 DC。 |
| S2P operation | `cascade()` | 串接相同 grid／z0 的 differential two-port。 |
| S2P operation | `reverse_ports()` | 交換 differential input/output。 |
| S2P operation | `voltage_transfer_function()` | 計算 terminated H21。 |
| S2P operation | `completed_voltage_transfer_function()` | 依明示 policy 在 S-matrix 或 scalar H21 layer 補齊 missing DC，回傳 completed frequency grid 與 terminated H21。 |
| S2P operation | `to_LinkSegment()` | 進入 scalar response/grid boundary。 |
| Output | `write_touchstone_s2p()` | 輸出 differential `.s2p`。 |
| Output | `write_touchstone_s4p()` | 輸出 single-ended `.s4p`。 |

S2P-only method 收到 S4P 時必須報錯並要求先呼叫 `s4p_to_s2p()`；不得自動丟棄
common-mode 或 mode-conversion 資訊。

## COM channel ingestion

COM path stage 最後接收 Sdd/S2P。`from_touchstone()` 只偵測並保存實際 port
representation；stage 擁有規範順序，utility 只執行具名操作。

```text
178A measured S4P (D3.2):
raw S4P -> single-ended renormalization to R0 -> optional frequency limit -> S4P-to-Sdd

178A native differential S2P:
raw S2P -> optional frequency limit -> differential renormalization to 2*R0

93A measured S4P:
raw S4P -> optional frequency limit -> S4P-to-Sdd -> differential renormalization
```

178A 的兩條路徑是 input-representation dispatch，不是算法 selector。S4P
解析、port count 或轉換失敗時必須報錯，不得改走 S2P 流程。`*_s4p_path`
欄位名稱暫時保留相容性，但實際 representation 由 Touchstone port count 決定。

## Synthetic S4P

`s2p_to_synthetic_s4p(target_z0_diff, reader_port_order)` 先在需要時將
Sdd renormalize 到目標 differential impedance，再建立 canonical mixed-mode matrix：

\[
S_{mm}=\begin{bmatrix}S_{dd}&0\\0&0\end{bmatrix}
\]

因此 `Sdc=Scd=Scc=0`，single-ended reference impedance 為
`target_z0_diff/2`。`reader_port_order` 表示下游 reader 將 raw S4P 排成
`(tx_p, tx_n, rx_p, rx_n)` 時使用的順序；writer 使用其 inverse permutation
預先排列 raw ports。它只保證用該 reader order 重新取得 target-z0 Sdd，不代表
原始量測 S4P 的 common-mode 行為。
輸出 Touchstone 必須帶有 synthetic 說明。

## Validation invariants

- raw S4P 的四個 single-ended ports、z0 與 frequency grid 在讀取後保持不變；
- synthetic S4P 經 Touchstone 寫出／重讀／`s4p_to_s2p()` 後，四個 Sdd 元素皆閉環；
- 93A 與 178A 固定 golden COM 值不得因 representation refactor 改變；
- 178A S4P ingestion 必須符合 D3.2 single-ended-first 順序；native S2P
  只在確實沒有四埠資訊時使用 differential-domain normalization。
