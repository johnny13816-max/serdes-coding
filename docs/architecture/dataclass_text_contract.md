# COM dataclass 文字介面契約

本文件定義 COM config/status dataclass 的人類易讀文字介面。文字介面用於互動檢查、
log 與固定摘要；它不是 serialization format，也不取代數值 array export 或 COMReport。

## 介面

支援此契約的 dataclass 提供：

```text
to_string()       多行、語意化、有單位且長度有界的摘要
print(file=None)  將同一份摘要輸出至 stdout 或指定 text stream
__str__()         等同 to_string()
__repr__()        單行、長度有界的除錯識別
```

`COMDataclassText` 只擁有縮排、數值格式、nested object 與 bounded array formatting。
每個 dataclass 必須自行實作 `_text_sections()` 與 `_repr_fields()`，明確選擇工程名稱、
欄位順序、section、stored unit、display unit 與換算比例。禁止用
`dataclasses.fields()` 自動傾印全部欄位來代替語意設計。

## 單位

每個顯示欄位必須標示物理單位或明確的 domain 分類，例如 `dimensionless`、
`sample index`、`tap count`、`probability`、`policy` 或 `status`。stored unit 與 display
unit 不同時，dataclass 必須明確提供 scale；formatter 不依欄位名稱猜測換算。

常用顯示換算包括：

| Stored | Display | Scale |
|---|---|---:|
| Hz | GHz | `1e-9` |
| s | ps | `1e12` |
| V | mV | `1e3` |
| V² | mV² | `1e6` |
| F | fF | `1e15` |
| H | pH | `1e12` |

PSD 保留 `V²/Hz`；COM、gain 與 penalty 依其定義標示 `dB`；FFE/DFE coefficients
標示 `dimensionless`。

## 大型物件

大型 ndarray 顯示 shape、dtype、有限值範圍與固定數量的 head/tail。solver matrix 可由
owner 選擇只顯示 shape。PSD、sampled response、PMF 與 S-parameter object 顯示型別和
核心 array shape，不傾印完整資料。精確數值仍由既有 export boundary 保存。

## Ownership

```text
178A dataclass
└── _text_sections() / _repr_fields()  工程語意、單位、選取與順序
    ↓
models/com_dataclass_text.py           通用且無 COM stage 語意的排版機制
    ↓
to_string / print / str / repr
```

目前 178A-owned config/status/search dataclass 採用此契約。93A 與暫時共用的
`COMPath`、`COMPMFStatus`、`COMSearchCandidate` 保留既有介面，待 93A review 再決定
是否遷移。reporting 只消費 config/status；統一 plot mapping 屬於獨立 contract。

## 修改規則

新增或修改 dataclass field 時，必須同步：

1. `_text_sections()` 的語意名稱、位置、單位與摘要方式；
2. 必要時更新 `_repr_fields()`；
3. config/status tree；
4. semantic text tests；
5. 若欄位代表新算法分支，另外更新 branch behavior registry。

文字介面不得重新計算 COM quantity、觸發 stage、建立 plot 或寫入 artifact。
