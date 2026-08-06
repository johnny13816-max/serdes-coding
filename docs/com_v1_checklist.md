## Current Package Config Note

`fixed_config` 的 package 參數已拆成四組：
- `txpkg_victim.*`
- `txpkg_fext.*`
- `txpkg_next.*`
- `rxpkg.*`

這是 COM v1.0 的輸入 contract。PyChOpMarg legacy workbook 若只有一組 package 參數，adapter 會複製到四組 config，方便和 reference case 做一致性檢查。

# COM v1.0 Checklist

## v1.0 Scope

目前 v1.0 目標是建立 93A-only COM algorithm layer。

v1.0 包含：

- 使用 project-owned Excel template 輸入 fixed/search/channel 設定
- 使用 S4P channel files 建立 victim / NEXT / FEXT paths
- 使用 93A.1.6 search space 做 Cartesian product sweep
- search 階段先以 FOM 選最佳候選
- winner 再進入 93A.1.7 PMF / COM calculation
- 保留 single-run debug/study mode 的完整 `COMStatus`

v1.0 不包含：

- 178A / 802.3ck extension
- higher-level package/channel/imp search
- 官方 IEEE COM correlation claim
- 任意外部 Excel 格式的完整自動解析

## Input Contract

### Project-Owned Excel

COM Python code 的正式入口是：

```text
excel_to_config(excel_path)
excel_to_search_config(excel_path)
```

正式支援的 workbook 只有三張表：

```text
fixed_config
search_config
channels
```

使用流程：

1. 手動修改 Excel 內的固定參數、search range、channel paths。
2. Python 直接呼叫 `excel_to_config()` 建立 `COMConfig`。
3. Python 直接呼叫 `excel_to_search_config()` 建立 `COMSearchConfig`。
4. 執行 `COM(cfg).run(search)`。

### Preprocess Boundary

外部來源可能有各種格式，例如 PyChOpMarg、公司內部表格、spec-style 表格。

這些格式轉成 project-owned Excel 的流程屬於前處理：

```text
read_customized_excel()
params_to_excel()
```

這部分由 Codex 協助維護，不視為 COM algorithm layer 的核心 study scope。

### fixed_config

`fixed_config` 儲存非 search 的固定參數。

欄位：

```text
Domain
Parameter
Value
Unit
Description
```

目前 parser 依照 `Parameter` 欄位 mapping，不依賴固定 cell address。

### search_config

`search_config` 儲存 93A.1.6 variable equalizer search parameters，以及 search output policy。

支援 search parameters：

```text
c_m2
c_m1
c_1
g_DC
g_DC2
```

支援 settings：

```text
keep_top_n
keep_all_rows
continue_on_error
```

`Values` 支援：

```text
start:step:stop
comma,separated,list
single_value
```

如果某個 search parameter 的 `Enabled` 是 `FALSE`，該參數會使用 `COMConfig` 裡的 fixed default。

### channels

`channels` 儲存 victim / NEXT / FEXT channel S4P paths。

欄位：

```text
Kind
Index
S4P Path
Port Order
R0 Ohm
Gamma Source
Gamma Load
Use
Description
```

目前規則：

- 必須剛好一條 enabled `victim`
- 可有任意數量 enabled `next`
- 可有任意數量 enabled `fext`
- disabled row 不會被讀入
- blank path 不會被讀入
- 相對路徑會相對於 Excel 所在資料夾、project root、或目前工作目錄解析
- v1.0 的 `COMChannelConfig` 仍假設所有 enabled channel 共用同一組 `Port Order`、`R0 Ohm`、`Gamma Source`、`Gamma Load`

因此，如果你把 3 NEXT / 2 FEXT 改成 4 NEXT / 3 FEXT，只要新增或啟用對應 row、填入有效路徑，`excel_to_config()` 會讀入。限制是這些 row 目前必須共用同一組 channel-level settings。

## Output Contract

### Single Run / Study Mode

沒有傳入 search object 時：

```text
COM(cfg).run()
```

輸出完整 `COMStatus`，用於 debug/study。

目標保留：

- paths / S-domain / TF-domain / pulse
- sampling phase / DFE
- imp components
- PMF components
- final COM

durable export 格式尚未定案，候選包含 pickle / npz / json / Excel summary。

### Search Mode

有傳入 search object 時：

```text
COM(cfg).run(search)
```

輸出 `COMSearchStatus`。

search mode 不保留每個 candidate 的完整 `COMStatus`，只保留 lightweight summary rows，以及 best-FOM candidate 的完整結果。

## Must-Have Before v1.0

1. Project-owned Excel input format 完成
2. `excel_to_config()` / `excel_to_search_config()` 完成
3. Excel search 能跑 reference case
4. Search performance cache
5. FOM 對照 93A.1.6 sanity check
6. PMF 對照 93A.1.7 sanity check
7. Single-run output/export contract
8. Full debug plot set

## Known Open Questions

1. Package model v1.0 是否只鎖定 93A 修訂版定義
2. Single-run durable output 要使用哪個格式
3. Full debug plot set 要包含哪些固定圖
4. v1.0 validation baseline 要使用 PyChOpMarg、MATLAB、或自建 sanity case
