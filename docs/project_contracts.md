# SerDes Coding Project Contracts

## 目的

這份文件記錄目前程式的 module 邊界與整理方向。原則是：

- `COM` algorithm 相關內容留在 COM domain。
- 通用 signal processing / S-parameter / PMF 工具獨立成可重用 module。
- Excel template 與 reference-data adapter 不放進 COM algorithm 本體。
- 先固定 contract，再搬 code。

## 目前檔案狀態

### `com_model.py`

目前保留 COM algorithm 相關責任：

- COM 93A algorithm orchestration
- COM config/status dataclasses
- 93A-specific package/filter/S-parameter formula
- path build helpers
- DFE / sampling phase / impairment / PMF helpers
- smoke test

整理方向：

- 保留 COM algorithm、COM config/status、93A formula helpers。
- 移出 smoke test 到 `examples/` 或 `tests/`。

### `com_excel_io.py`

目前負責 COM input workbook adapter：

- `excel_to_config()`
- `excel_to_search_config()`
- project-owned workbook parser
- PyChOpMarg-style workbook fallback adapter

`com_model.py` 仍保留同名 wrapper，目的是維持既有 import path 相容。

正式新入口應優先使用：

```python
from serdes_coding.com_excel_io import excel_to_config, excel_to_search_config
```

### `link_segment.py`

目前包含：

- `LinkConfig`
- `LinkSegment`
- `SparamModel`
- `SparamProcessor`
- `OneSidePSD`
- FFT / IFFT / resample / plot helpers

整理方向：

- `LinkConfig` + `LinkSegment` 可以保留為 core signal-grid domain。
- `SparamModel` 與 S4P/Sdd 處理適合移到 `sparam_model.py`。
- `SparamProcessor` 適合移到 `sparam_preprocess.py`。
- `OneSidePSD` 適合移到 `psd.py`。
- plot helper 可先留在 class，等 API 穩定後再考慮 `plotting.py`。

### `pmf_handler.py`

目前包含：

- `Pmf1D`
- PMF transform methods
- PMF helper functions
- 少數未完成或殘留 API，例如 module-level `fir_filtered_pmf()` 與 `Pmf1D.uniform()`

整理方向：

- `Pmf1D` 保持獨立 module。
- `fir_filter()` / `combine()` 等 immutable transform 保留在 `Pmf1D`。
- 只被單一 method 使用的檢查邏輯留在 method 內部或 private nested function。
- module-level helper 只保留多個 function/class 會共用的東西。

## 建議目標結構

```text
serdes_coding/
  __init__.py
  link_segment.py
  sparam_model.py
  sparam_preprocess.py
  psd.py
  pmf_handler.py
  com/
    __init__.py
    config.py
    status.py
    model_93a.py
    formulas_93a.py
    excel_io.py
    reference_adapters.py
```

短期不一定一次做到這個結構。近期優先順序是：

1. 先把 Excel input 與 PyChOpMarg adapter 從 `com_model.py` 移出。
2. 再把 COM dataclasses 拆成 `config.py` / `status.py`。
3. 再把 93A formula helpers 拆成 `formulas_93a.py`。
4. 最後處理 `link_segment.py` 的 Sparam / PSD 分離。

## Helper 放置規則

已採用的規則：

- 多個 module 與多個 class 會共用：module-level public/helper function。
- 同一個 class 內多個 method 會共用：class-level private/static helper。
- 只服務單一 method：nested function 或 method 內部邏輯。

此規則優先用於新 code；舊 code 會在整理時逐步對齊。

## COM Class Contract

`COM` 是 COM pipeline 的 orchestration class。

輸入：

- `COMConfig`
- optional `COMSearchConfig`

輸出：

- single run: `COMStatus`
- search run: `COMSearchStatus`

`COM.run()` contract：

- `search is None`：跑一組完整 pipeline，包含 PMF/COM。
- `search is not None`：掃描 search candidates，用 FOM 找 best candidate，再對 best candidate 跑完整 PMF/COM。

## COM Plot Contract

報告型 plot 放在 result/status object，不放在 `COM` calculator。

目前入口：

```python
status.plot_summary(save_path="report/single_run")
search_status.plot_summary(save_path="report/search_run")
```

`save_path` contract：

- 空字串：互動式顯示 figure。
- 資料夾路徑：輸出固定檔名的一組 PNG。
- 單一 plot method 也可接受檔案路徑，例如 `path_pulses.png`。

`COMStatus.plot_summary()` 目前輸出：

- `path_pulses.png`
- `path_sbr.png`
- `dfe_summary.png`
- `impairment_summary.png`
- `pmf_summary.png`

`COMSearchStatus.plot_summary()` 目前輸出：

- `search_fom_trace.png`
- `search_top_candidates.png`
- `best/` 裡的 single-run summary plots。

## COM Export Contract

數值輸出也放在 status object，不放在 `COM` calculator。

Single-run export：

```python
status.export("report/single_run", include_plots=True)
```

輸出：

- `summary.json`：可讀的 scalar metadata、path 階層、array keys。
- `arrays.npz`：所有大型 numpy arrays。
- `plots/`：如果 `include_plots=True`，輸出 standard plot set。

Search export：

```python
search_status.export("report/search_run", include_plots=True)
```

輸出：

- `search_summary.json`：search rows、best row、candidate settings。
- `best/summary.json`：best candidate 的完整 single-run summary。
- `best/arrays.npz`：best candidate 的完整 numeric arrays。
- `plots/`：search-level plots 與 best candidate plots。

目前 export 目標是 report/debug 與數值追蹤，不是正式 long-term binary checkpoint。未來若要完整重建 class instance，可以再新增 `load_status()`。

## COM Path Contract

`COMPath` 是單一 signal path 的狀態容器。

目前 path 類型：

- `victim`
- `next`
- `fext`

`COMPath` 保留：

- path-specific `S_tx`, `S_ch`, `S_all`
- path-specific `H_21`, `H_all`, `X`, `pulse`
- shared RX/filter objects through `shared`
- proxy properties 讓 `path.H_ffe`, `path.S_rx`, `path.H_ctf` 可直接存取

## S-Parameter Domain Contract

`SparamModel` 目前代表 differential 2-port Sdd model：

- port 0: input/source
- port 1: output/load

S4P port order 只應該出現在 S4P 轉 Sdd 的入口，例如 `from_s4p_array()` / `from_touchstone()`。

長期 debug/preprocess 需要保存 raw S4P / full mixed-mode 資訊時，應建立 `SparamPreProcess` 或新的 raw model，不應破壞 `SparamModel` 的 Sdd contract。

## LinkSegment Contract

`LinkSegment` 代表已對齊 `LinkConfig` FFT grid 的 transfer/impulse/step/bit response。

重要假設：

- `tf` 使用 one-sided rFFT frequency grid。
- `raw_ir` 是 frequency-domain IFFT 的直接結果。
- `aligned_ir` 是 causality/main cursor 對齊後的結果。
- plot / cascade / COM path 使用 `aligned_ir`。
- `ir2tf()` 預設使用 `raw_ir` 保留 round-trip definition。

## PMF Contract

`Pmf1D` 代表一維離散 PMF：

- x-axis grid spacing: `dx`
- start index: `st_idx`
- probability mass: `pmf`

Public transform methods 採 immutable style，回傳新的 `Pmf1D`：

- `shift_x()`
- `scale_x()`
- `resample_dx()`
- `fir_filter()`
- `combine()`

COM PMF pipeline 應以 chainable style 表達：

```python
p_combined = p_ISI.combine(p_G).combine(p_DD).combine(p_XT)
```

## PSD Contract

`OneSidePSD` 代表 one-sided PSD。

目前設計重點：

- 可建立 arbitrary frequency grid 的 PSD。
- 若 frequency grid 對齊 `LinkConfig.freqs`，則 `ifftable=True`。
- `to_sigma()` 回傳 integrated RMS。
- `filtered_by(LinkSegment)` 要求 PSD 與 filter frequency grid 相容或先 aligned/resampled。

## 近期整理原則

近期目標仍是完成 93A search + single-run full output，不進 178A。

因此整理順序以低風險為主：

1. 先整理文件與 module boundary。已完成。
2. 移出 Excel I/O，不改 COM algorithm。已完成。
3. 移出 reference adapter，不改 COM algorithm。已完成。
4. 清掉未使用/未完成 public API。
5. 再討論 single-run full output。
## COM Script Entry Contract

直接執行 `src/serdes_coding/com_model.py` 時，檔案底部的 `if __name__ == "__main__"` 是使用範例入口，不再是 PyChOpMarg smoke test。

預設 config:
- `templates/com_v1_params_template.xlsx`

入口模式:
- `run_mode = "single"`: 讀 `fixed_config`，執行單次 COM run，輸出完整 `COMStatus`。
- `run_mode = "search"`: 讀 `fixed_config` + `search_config`，執行 search，輸出 `COMSearchStatus` 與 best single-run status。

預設輸出:
- single run: `reports/single_run`
- search run: `reports/search_run`

PyChOpMarg reference Excel 只作為 legacy adapter / reference comparison 使用，不再是直接執行 `com_model.py` 的預設輸入。

## COM Package Config Contract

`COMConfig` 不再使用單一共用 `pkg`。package model 拆成四組：
- `txpkg_victim`: victim path 的 TX package。
- `txpkg_fext`: FEXT aggressor path 的 TX package。
- `txpkg_next`: NEXT aggressor path 的 TX package。
- `rxpkg`: 所有 paths 共用的 RX package。

Path build contract:
- `_build_shared_path()` 只建立 shared RX/filter blocks，`S_rx` 由 `cfg.rxpkg` 建立。
- `_build_path(kind="victim")` 使用 `cfg.txpkg_victim` 建立 `S_tx`。
- `_build_path(kind="fext")` 使用 `cfg.txpkg_fext` 建立 `S_tx`。
- `_build_path(kind="next")` 使用 `cfg.txpkg_next` 建立 `S_tx`。

Excel fixed_config contract:
- package 參數使用前綴命名，例如 `txpkg_victim.C_d`、`txpkg_fext.z_p`、`txpkg_next.Z_c`、`rxpkg.C_p`。
- PyChOpMarg legacy adapter 仍可讀舊 workbook；舊格式只有一組 package 時，會複製到四組 package config。
