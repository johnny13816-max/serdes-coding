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
| S2P operation | `to_LinkSegment()` | 進入 scalar response/grid boundary。 |
| Output | `write_touchstone_s2p()` | 輸出 differential `.s2p`。 |
| Output | `write_touchstone_s4p()` | 輸出 single-ended `.s4p`。 |

S2P-only method 收到 S4P 時必須報錯並要求先呼叫 `s4p_to_s2p()`；不得自動丟棄
common-mode 或 mode-conversion 資訊。

## COM channel ingestion

COM path stage 最後仍接收 Sdd/S2P。93A 與 178A 必須顯式建立轉換流程：

```text
sdd_first:
raw S4P -> optional frequency limit -> S4P-to-Sdd -> differential renormalization

s4p_first:
raw S4P -> single-ended renormalization -> optional frequency limit -> S4P-to-Sdd
```

`from_touchstone()` 不知道 COM policy；stage 負責選擇順序，utility 只執行具名操作。

## Synthetic S4P

`s2p_to_synthetic_s4p(port_order, z0_diff)` 建立 canonical mixed-mode matrix：

\[
S_{mm}=\begin{bmatrix}S_{dd}&0\\0&0\end{bmatrix}
\]

因此 `Sdc=Scd=Scc=0`，single-ended reference impedance 為 `z0_diff/2`。它只保證
用相同 `port_order` 重新取得相同 Sdd，不代表原始量測 S4P 的 common-mode 行為。
輸出 Touchstone 必須帶有 synthetic 說明。

## Validation invariants

- raw S4P 的四個 single-ended ports、z0 與 frequency grid 在讀取後保持不變；
- synthetic S4P 經 Touchstone 寫出／重讀／`s4p_to_s2p()` 後，四個 Sdd 元素皆閉環；
- 93A 與 178A 固定 golden COM 值不得因 representation refactor 改變；
- `sdd_first` 與 `s4p_first` 的操作順序及既有數值結果保持不變。
