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
- DFE / sampling phase / imp / PMF helpers
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
- `OneSidePSD`（後續改名為 `ContinuousPSD`，並新增 `SampledPSD`）
- FFT / IFFT / resample / plot helpers

整理方向：

- `LinkConfig` + `LinkSegment` 可以保留為 core signal-grid domain。
- `SparamModel` 與 S4P/Sdd 處理適合移到 `sparam_model.py`。
- `SparamProcessor` 適合移到 `sparam_preprocess.py`。
- `ContinuousPSD` / `SampledPSD` 適合移到 `psd.py`。
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

`COM_93A.run()` contract：

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
- `path_S_all_IL.png`
- `path_H21_tf.png`
- `dfe_summary.png`
- `imp_summary.png`
- `pmf_summary.png`

`COMSearchStatus.plot_summary()` 目前輸出：

- `search_fom_trace.png`
- `search_top_candidates.png`
- `best/` 裡的 single-run summary plots。

## COM Export Contract

數值輸出也放在 status object，不放在 `COM` calculator。

Config export：

```python
cfg.export("report/single_run")
```

輸出：

- `config_summary.txt`：human-readable `COMConfig` summary，方便報告/debug 快速確認設定。

Single-run export：

```python
status.export("report/single_run", include_plots=False)
COMReport(cfg, status).plot_single_run("report/single_run/plots")
```

輸出：

- `report_summary.txt`：human-readable single-run scalar summary，包含 FOM/COM、path overview、DFE、imp、PMF 主要數值。
- `arrays.npz`：所有大型 numpy arrays。
- `plots/`：single-run detail plots。

Search export：

```python
search_status.export("report/search_run", include_plots=True)
```

輸出：

- `search_summary.json`：search rows、best row、candidate settings。
- `best/report_summary.txt`：best candidate 的 human-readable single-run summary。
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

PSD utility 之後分成兩個 domain class：

```python
ContinuousPSD
SampledPSD
```

目前程式已建立 `ContinuousPSD` 與 `SampledPSD` 骨架；`OneSidePSD` 暫時保留為
`ContinuousPSD` 的 backward-compatible alias，讓既有 93A code 不會立即破壞。

共同 convention：

- 兩個 class 都使用 one-sided PSD representation。
- `to_sigma()` 一律回傳 integrated RMS。
- PSD 數值不得為負值，frequency axis 必須單調遞增。
- filtering 使用 `S_out = S_in * |H|^2`。

`ContinuousPSD` contract：

- 代表 continuous-time one-sided PSD。
- `freqs` 單位為 Hz，範圍為 `f >= 0`。
- `psd` 單位為 quantity^2/Hz。
- `to_sigma()` 使用 `sqrt(integral_0^inf S_ct,1(f) df)`。
- `aligned_to(LinkConfig)` 將 PSD 對齊 `LinkConfig.freqs`，用於和 `LinkSegment` filter 相乘。
- `filtered_by(LinkSegment)` 要求 PSD 與 filter frequency grid 相同。
- `to_sampled(fb, theta=None, alias_kmax=None, theta_points=None)` 轉成 `SampledPSD`；sampling aliasing 是 method 內部責任，不提供 `alias=True/False` 開關。
- 當 `theta is None` 時，自動產生 uniform sampled-domain one-sided grid `np.linspace(0, pi, theta_points)`，保證包含 DC 與 Nyquist endpoint。
- 若 `theta_points is None`，預設使用 CT PSD 在 `[0, fb/2]` 內的 sample count，且至少為 2。
- 若 user 提供 `theta`，則使用 user-provided axis；只有當該 axis 實際包含 `0` 或 `pi` 時才做 endpoint correction。

`SampledPSD` contract：

- 代表 sampled/discrete-time one-sided PSD。
- `theta` 單位為 rad/sample，範圍為 `[0, pi]`。
- `fb` 是 sampling rate / baud rate，單位 Hz。
- `psd` 單位為 quantity^2/Hz，不是 quantity^2/rad。
- 這裡刻意對齊 IEEE 802.3 Annex 178A 的 convention：spec 用 `theta`
  當 sampled-domain frequency coordinate，但 Eq. 178A-17/18/19/22/28 的
  PSD density scale 仍是 per-Hz。
- 內部儲存 rfft-style one-sided equivalent：interior bins 已經相對 spec
  two-sided PSD 加倍，DC/Nyquist 不加倍。
- `freqs` 可以作為 debug property：`freqs = theta * fb / (2*pi)`。
- `from_constant(theta, psd_value, fb)` 的 `psd_value` 是 spec two-sided
  Hz-density value，例如 178A-18 的 `sigma_x^2/fb`；method 內部會轉成
  one-sided equivalent。
- `to_sigma()` 使用 `sqrt(df * sum(S_one_sided))`，其中
  `df = fb/Nfft`。
- `to_autocorrelation()` 先還原 spec two-sided Hz-density PSD，再用
  `R[n] = fb * ifft(S_two_sided)[n]`。
- 多個 178A.1.7 impairment PSD 應先轉成 `SampledPSD` 再相加。
- `to_continuous_baseband()` 只能回傳 baseband-equivalent `ContinuousPSD`；若前面做過 aliasing，不能恢復原本的 high-frequency continuous PSD。

`SampledResponse` contract：

- 代表 sampled/discrete-time LTI response。
- `theta` 單位為 rad/sample，使用 one-sided rfft-style grid：`0..pi`，且必須 uniform。
- `tf` 是 `H(e^jtheta)`；`ir` 是 discrete-time impulse response `h[n]`。
- `nfft` 是 even-length rfft FFT length；`len(tf) = nfft//2 + 1`。
- `from_tf(theta, tf, fb, nfft=None)` 使用 `np.fft.irfft()`；若 `nfft is None`，預設 `nfft = 2*(len(tf)-1)`。
- `from_ir(ir, fb, nfft=None)` 使用 `np.fft.rfft()`；若 `nfft is None`，預設 `nfft = len(ir)`，且目前要求 even length。
- 不做 continuous-time `Fs` scaling；這裡的 convolution 語意是 `y[n] = sum h[k]x[n-k]`。
- `SampledPSD.filtered_by(SampledResponse)` 使用 `S_out(theta)=S_in(theta)*|H(e^jtheta)|^2`。
- `SampledPSD.filtered_by(SampledResponse)` 嚴格要求 `fb` 相同且 `theta` grid 相同；不同 grid 先 raise error，之後再補 `aligned_to()`。
- `SampledPSD.add(other)` / `psd_a + psd_b` 用於相加互不相關的 sampled-domain PSD component；要求 `fb` 與 `theta` grid 完全相同，不做隱式 resample。
- 不取代 `LinkSegment`；`LinkSegment` 仍代表 continuous-time / rfft-Hz grid response。

178A sampled PSD 尺度規則：

```text
theta = 2*pi*f/fb
df = fb/(2*pi) d theta
f = theta*fb/(2*pi)
```

不要把 178A sampled PSD source 轉成 quantity^2/rad。程式採用
theta-indexed Hz-density：

```text
S_spec(theta): quantity^2/Hz, indexed by theta
power = df * sum(S_one_sided) = fb * mean(S_two_sided)
```

178A source PSD 在 code 中要照 spec scale 寫：

```text
S_rn(theta) = eta_0/2 * alias_sum(|H_rn(f_alias)|^2)
S_xn(theta) = sigma_x^2/fb * |DFT(h_xn[n])|^2
S_tn(theta) = 10^(-SNR_TX/10)/fb * |DFT(h_tn[n])|^2
S_jn(theta) = sigma_x^2*(A_DD^2+sigma_RJ^2)/fb * |DFT(h_J[n])|^2
S_qn(theta) = (Delta^2/12)/fb
```

混淆點：

```text
純數學 theta-density 會使用 quantity^2/rad，並在 PSD source 乘
fb/(2*pi)。這不是目前 SampledPSD contract。

因此 code 中不要出現：
sigma_x^2/pi
sigma_x^2/(2*pi)
eta_0/2 * fb/(2*pi)
```

`ContinuousPSD.to_sampled()` 的 aliasing sum 也不做 Jacobian scaling；它輸出
theta-indexed Hz-density。注意 `ContinuousPSD` 本身已經是 one-sided CT
PSD，因此這個入口和 `SampledPSD.from_constant()` 不同：

- `SampledPSD.from_constant(theta, psd_value, fb)` 的 `psd_value` 是 178A
  spec two-sided constant，例如 `sigma_x^2/fb`，method 內部會 double
  interior bins。
- `ContinuousPSD.to_sampled()` 的輸入已經是 one-sided CT PSD，所以 direct
  aliasing sum 已經是 one-sided equivalent；method 只對 DC/Nyquist 做
  rfft endpoint accounting，不再 double interior bins。

```text
f0 = theta*fb/(2*pi)
S_one_sided(theta) = sum_k S_ct,1(|f0 + k*fb|), 0 < theta < pi
S_one_sided(0)  *= 0.5
S_one_sided(pi) *= 0.5, if Nyquist bin exists
```

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
## Matplotlib Backend Contract

Plot/export helper 不得呼叫 `matplotlib.use(..., force=True)` 或改變全域 Matplotlib backend。

目前規則：
- `save_path=""`：使用使用者目前的 interactive backend，呼叫 `plt.show()`。
- `save_path` 有值：使用局部 `FigureCanvasAgg` 建圖與存檔，不改全域 backend。

原因：COM export/report 不能污染同一個 IPython / VS Code kernel，否則使用者後續手動畫 `SparamModel.plot_*()` 或 `LinkSegment.plot_*()` 會遇到 `FigureCanvasAgg is non-interactive`。

## LinkSegment Alignment Guard Contract

- TF-originated `aligned_ir` default main cursor is placed at 20 UI.
- Purpose: keep enough precursor margin before the main cursor and reduce the chance that precursor energy wraps to the vector tail.
- `validate_aligned_ir()` checks whether significant tail energy remains after alignment.
- `COM` applies this guard to victim `H_21` and victim `pulse`.
- Xtalk paths are not forced to share this guard because their phase/reference selection is different from the victim ISI/DFE path.

## COM Downsample Debug Contract

`COM_93A` exposes these debug proxies after `COM_93A.run()` or `_run_once()`:

- `com.h_dsamp`: victim pulse sampled at the selected DFE sampling phase.
- `com.t_dsamp_ui`: discrete UI time axis for `h_dsamp` and `h_ISI`, with main cursor at 0.

Debug plot methods:

- `com.plot_h_dsamp(ax=None, save_path="", xlim_ui=(-5, 20), label=None)`
- `com.plot_h_ISI(ax=None, save_path="", xlim_ui=(-5, 20), label=None)`
- `com.plot_h_J(ax=None, save_path="", xlim_ui=(-5, 20), label=None)`

`h_J` uses its own reconstructed finite-difference UI axis because boundary samples may be skipped.

## COM Report Plot Contract

New report entry:

```python
report = COMReport(cfg, status)
report.plot_single_run("reports/single_run/plots")
report.plot_COMPath(path_idx=0, save_path="reports/single_run/plots")
```

`COMReport` owns plots that need both `COMConfig` and `COMStatus`:
- config annotation on figures
- path detail figures
- DFE detail figures
- impairment detail figures
- PMF detail figures
- Matplotlib backend-safe plot helpers: `_plt`, `_subplots`, `_plot_save_path`, `_finish_figure`, path display labels

`COM` should remain computation-oriented. `COMStatus.plot_*()` remains for
backward-compatible compact summaries, but new detailed report work should go
through `COMReport`.

Export/helper boundary:
- JSON scalar/value conversion and JSON file writing belong to `_PrettyDataclass`.
- `COMConfig` owns its own config snapshot construction.
- `COMStatus` owns array metadata export plus S-parameter / LinkSegment / PMF export helpers.
- COM search-flow helpers belong inside the calculator class, e.g. `_config_with_search_candidate()`, `_search_row_from_status()`, `_select_search_rows()`, and `_format_duration()`.
- `IEEECOMsparam._cascade_sdd_93A()` owns the raw Eq. 93A-4 through Eq. 93A-7 Sdd cascade formula.
- These helpers should not be reintroduced as free module-level functions unless they become intentionally public APIs.

- `COMStatus.plot_dfe_summary()` plots residual `h_ISI` on a main-cursor-centered UI axis and defaults to `xlim_ui=(-5, 20)`.
- `LinkSegment.plot_tf()` supports `ylim=(min_db, max_db)`.
- `COMStatus.plot_path_H21_tf()` defaults to automatic in-band y-limit; explicit `ylim=(min_db, max_db)` is still supported.
- PMF FIR convolution uses `keep_mass=0.99999` by default to prevent long-tail convolution from dominating report x-axis range.

## Reference Case Contract

- `templates/com_v1_params_template.xlsx` 目前標記為 `debug_case_93a_style`。
- 這個 workbook 只作為 93A-style quick-run/debug case。
- 它使用 PyChOpMarg IEEE 802.3dj example2 channel family，但將 `fb` 改成 `53.125e9 Hz` 方便目前 93A pipeline debug。
- 不可把這個 case 當成正式 IEEE 93A validation、MATLAB COM correlation、或規格 compliance evidence。
- 詳細註記放在 `docs/reference_cases.md`。

## Frequency Plot Contract

- `LinkSegment.plot_tf()` 預設顯示 `0 ~ fb` 的 in-band view。
- `SparamModel.plot_*()` 支援 `xlim=(f_start, f_stop)`，COM report 預設傳入 `0 ~ fb`。
- 頻域圖的 automatic y-limit 只根據目前 x 軸範圍內的資料決定。
- 低於 `-300 dB` 的點視為 numerical floor，例如 ideal zero 或 high-frequency zero padding，不參與 automatic y-limit；原始曲線不會被 clipping。
- `SparamModel.plot_IL()` 可用 `annotate_f=fb` 標註 `IL@fb`。
- COM report 的 `S_all_IL` 圖會在 `fb` 落在 S-parameter measured grid 內時標註 `IL@fb`；若 `fb` 超出 measured band，只標示此限制，不外插假資料當作 IL。
- COM report detail plots should use figure-specific annotations. Filter plots show the relevant filter parameter in the subtitle, and channel/transfer plots mark `fb` or the first relative `-3 dB` point when available.
- Detail plot title style: main title uses larger font; parameter subtitle uses smaller gray text. Generic run-level config notes are reserved for overview plots, not every detail plot.

## COM Spec Version Contract

目前 93A 與 178A 要明確分流，避免不同 Annex 的公式與流程混在同一個 method 裡。

命名規則：
- 93A calculator 使用 `COM_93A`。
- 178A calculator 使用 `COM_178A`。
- 直接實作 spec 公式或 spec procedure 的 function/method 需要加版本後綴，例如 `_build_paths_93A()`、`calculate_imp_93A()`、`cascade_com_93A()`。
- 共用 infrastructure 不加版本後綴，例如 `COMConfig`、`COMStatus`、`COMReport`、`SparamModel`、`LinkSegment`、`Pmf1D`。

目前 `COM_93A` 的主流程：
```text
run()
  -> _run_once()
      -> build_all_paths_93A()
      -> find_pos_and_dfe_93A()
      -> calculate_imp_93A()
      -> _calculate_FOM_93A()
      -> calculate_COM_93A()
```

Public import contract：
```python
from serdes_coding import COM_93A, COM_178A
```

178A implementation status：
- `COM_178A` 已建立 class 與 run pipeline 接口。
- `COMConfig_178A`、`COMFilterConfig_178A`、`COMPkgConfig_178A` 已建立，用來承接 178A path-building 所需的 filter/package 參數。
- `COMConfig_178A` 使用 `dte: COMDTEConfig`，不再使用 93A-style `dfe` 欄位描述 178A receiver discrete-time equalizer。
- `build_all_paths_178A()` 已完成第一版接線：
  - `_build_channel_under_test_178A()` 讀取 measured-domain S4P，順序沿用 victim、NEXT、FEXT。
  - `_build_shared_path_178A()` 建立 shared blocks：`H_ffe`、`H_ffe_next`、`H_t`、`S_rx`、`H_r`、`H_ctf`。
  - `_build_path_178A()` 依 path kind 選擇 `txpkg_victim`、`txpkg_next`、`txpkg_fext`，再串接 `S_tx + S_ch + S_rx`，最後轉成 `H_21` / `H_all` / `pulse`。
- `COM_178A._run_once()` 與 `_run_search()` 的流程已明確包含 sampling phase outer loop：
  ```text
  build_all_paths_178A()
    -> calculate_psd_common_178A(victim, h_XTs)
  -> for pos in range(link_cfg.per_ui)
         -> calculate_psd_pre_dte_178A(victim, pos, common)
         -> calculate_MMSE_DTE_178A(victim, imp_pre, pos)
         -> calculate_psd_post_dte_178A(imp_pre, dte_status, h)
         -> _calculate_FOM_178A(imp_status, dte_status)
    -> select best candidate
    -> optional calculate_COM_178A(best_imp, best_dte)
  ```
- `calculate_psd_common_178A()` 計算 sampling-phase-independent PSD cache；目前包含 `S_rn`、`S_xn`、`sigma_N`、`sigma_XT`，避免每個 `pos` 重複建立 receiver noise PSD 與 crosstalk PSD。
- `calculate_psd_pre_dte_178A()` 不吃 DFE/DTE result；它吃 `pos` 與 `common`，用該 sampling phase 建立 178A.1.7 pre-DTE PSD status。`ts` 是 derived value：在 `h[pos::per_ui]` 上找 main cursor 後反推 `ts = pos + main_ui * per_ui`。已由 `COMImpairmentCommon` 持有的 PSD/status 欄位不在 `COMImpairmentAtPos` 重複宣告。
- `calculate_psd_post_dte_178A()` 吃 pre-DTE PSD status、selected DTE result、oversampled victim pulse `h`，負責 post-DTE finalization；其中 residual `h_ISI` / `sigma_ISI` 在這裡由 `w_lim`、`b_lim`、`pruned_index` 重建，不存放在 `COMDTEStatus`。
- 178A `A_s` 依 Eq. 178A-37 定義為 `R_LM / (L - 1)`；因為 MMSE DTE 解已將 equalized pulse main cursor 正規化為 1，所以不再乘 `h_main`。正式 `A_s` 在 `calculate_psd_post_dte_178A()` 產生，供 final PMF/COM 使用。
- `calculate_MMSE_DTE_178A()` 是 178A.1.8 receiver FFE/DFE MMSE solve 的正式入口，取代舊的 `find_pos_and_dfe_178A()` 名稱；它輸出 `COMDTEStatus(ts, pos, d, w_lim, b_lim, pruned_index, mse, ...)`。
- 178A PMF helpers `_build_pmf_*_178A()` 仍在接線中；目前 MMSE DTE 已直接由 `COM_178A.calculate_MMSE_DTE_178A()` 呼叫 `COM_MMSE_DTE`。MSE 只用在 178A DTE 內部，用來選 sampling phase 與 DTE coefficients；外層 TXFFE/CTLE search 的 `FOM` 保留 93A-style signal-to-RSS-impairment metric，不用 MSE 取代 FOM。
- `IEEECOMsparam` 已建立 178A S-parameter builders：
  - `device_termination_178A()`：Eq. 178A-7 N-stage LC ladder，輸入 L/C vectors 與 bump capacitance。
  - `device_package_178A()`：Eq. 178A-9 N-stage package transmission line，輸入 TL length / impedance vectors 與 package capacitance。
  - `partial_host_channel_178A()`：Eq. 178A-10 synthetic partial host channel，輸入 C0 / C1 / TL parameters。
- `IEEECOMFilter.rx_equalizer_178A()` 已建立三 pole / two zero 的 178A CTF formula interface。
- `calculate_psd_pre_dte_178A()` 已建立 178A.1.7 sampled-domain PSD flow：
  - `S_rn`: receiver input noise PSD, Eq. 178A-17。
  - `S_xn`: crosstalk PSD summed over all aggressor paths, Eq. 178A-18；每條 crosstalk path 使用自己的 `t_s^(k)`，並選擇使 `sum_n [h_xn^(k)(n)]^2` 最大的 worst-case phase，不跟 victim candidate `pos` 綁定。
  - `S_tn`: transmitter output noise PSD, Eq. 178A-19 / 178A-20。
  - `S_jn`: transmitter jitter-induced noise PSD, Eq. 178A-21 / 178A-22；finite difference 使用 `Delta t = link_cfg.dt`，並輸出 V/UI 的 sampled jitter sensitivity。
- `S_qn`: according to Eq. 178A-26 to Eq. 178A-28; current implementation flow is still being stabilized, but final `COMImpairmentStatus_178A` is assembled in `calculate_psd_post_dte_178A()`。
  - `S_total`: sum of enabled PSD components on `cfg.theta`。
  - `R_n`: sampled-domain noise autocorrelation derived from `S_total` for MMSE use。
- Interference source Eq. 178A-24/25 is intentionally ignored in the current project scope and is not represented as a status field。
- 178A residual ISI is not finalized in `calculate_psd_pre_dte_178A()` and is not stored in `COMDTEStatus`; it belongs to `calculate_psd_post_dte_178A()` / `COMImpairmentStatus_178A` and later PMF flow。
- 178A PMF 需要先以 post-DTE `A_s` 呼叫 `COMPMFConfig.resolve(A_s)`；所有 PMF helper 應使用 `COMPMFRuntimeConfig`，不能直接把 unresolved `COMPMFConfig` 傳入需要 `dy/tap_abs_th` 的函式。
- 若 DTE 有 floating tap gap，`w_lim` 不是連續 FIR impulse。需要先用 `pruned_index` 補成完整 `w_ir`，再用於 `h_w`、`h_XTs_w`、`h_w_J` 或 `SampledResponse.from_ir()`。
- `COMImpairmentConfig.eta_0` is stored in internal SI units `V^2/Hz`; IEEE 178A Table 178A-9 lists `eta_0` in `V^2/GHz`, so Excel/reference adapters must convert before constructing `COMImpairmentConfig`。
- 目前可直接呼叫 `COM_178A(cfg).build_all_paths_178A()` 檢查 178A path-building；呼叫完整 `COM_178A.run()` 已可通過 FOM selection，下一個主要風險在 final PMF/COM flow 的數值驗證。
- `com_model.py` 的 `run_mode="single_178A"` 是 debug/smoke-test 入口：目前用 `_debug_config_178A_from_93A()` 從 93A-style workbook 暫時轉成 `COMConfig_178A`，並以 `include_quantization=True`、`quantization_vqc_method="gaussian_approx"`、`calculate_pmf=False` 測試 path/PSD/MMSE/post-DTE/FOM 接線。這不是正式 178A Excel mapping，也不代表 final PMF/COM 已完成驗證。
- `COMImpairmentConfig.quantization_vqc_method` 控制 178A pre-DTE `S_qn` 的 `V_qc` 計算方式：`"gaussian_approx"` 用 signal variance + Gaussian noise variance 快速近似 noisy signal CDF；`"pmf_exact"` 保留 spec-like `p_sn=conv[p_s,p_ga]` 的慢速 reference 路徑。

178A-4 path transfer contract：
- Eq. 178A-4 與目前 `SparamModel.to_LinkSegment()` 的 reference mismatch / voltage transfer conversion 觀念相同。
- 不額外建立 `to_LinkSegment_178A()`，避免暗示 178A 有不同轉換公式。
- 178A path builder 之後應直接呼叫 `S_all.to_LinkSegment(link_cfg, gamma_src=..., gamma_load=...)`。

178A package primitive policy：
- 單顆 shunt C、series L、single TL primitive 先沿用 93A method 名稱，不額外複製 `_178A` primitive。
- 178A 的版本差異先放在 stage-level builder，例如 `device_termination_178A()` 與 `device_package_178A()`。
- 依照目前 IEEE 802.3dj COM adhoc config/code，N-stage package TL 的 `zp` 與 `Zc` 是 stage-specific，`gamma0/a1/a2/tau` 是 package-level shared propagation model。
- 若後續確認 178A 修改了單顆 primitive 的公式或單位，再新增對應 `_178A` primitive。
## PSD / Sampled Response Theta Contract

本節是目前 PSD / sampled-domain response 的有效命名與 grid contract。

- sampled-domain frequency axis 一律命名為 `theta`，單位是 rad/sample，範圍是 one-sided rFFT grid `[0, pi]`。
- `LinkConfig` 同時定義 continuous-time grid 與 sampled-domain grid：
  - `freqs`, `df`: continuous-time rFFT grid，單位 Hz。
  - `theta`, `theta_freqs`: sampled-domain rFFT grid，以及對應的 Hz baseband axis。
  - `sampled_nfft`, `sampled_df`: symbol-rate sampled-domain FFT 長度與 Hz spacing。
- 預設 `LinkConfig` 會讓 `Nfft` 對齊 `2*per_ui` 的倍數，因此 `sampled_df == df`。
- 在預設 `LinkConfig` 下，CT/DT grid 具有封閉性：`sampled_nfft == Nfft/per_ui`，且任意 phase 的 `h[pos::per_ui]` 長度都等於 `sampled_nfft`。因此從 `LinkSegment` impulse response downsample 出來的 sampled-domain response 可以直接使用 `SampledResponse.from_ir(h_dsamp, cfg)`。
- `LinkConfig.from_Nfft()` 用於 linear convolution 等任意長度結果；若長度無法剛好對齊 `per_ui`，則使用最接近的 even sampled-domain grid。
- `SampledResponse.from_ir(ir, cfg)` 使用 `cfg.sampled_nfft` zero-pad impulse response，並使用 `cfg.theta` 建立 `H(e^jtheta)`。
- `SampledPSD.filtered_by(SampledResponse)` 要求 `fb` 與 `theta` grid 完全相容；不同 grid 需要先明確 resample/aligned，不能隱式處理。
- `SampledPSD.add(other)` / `psd_a + psd_b` 只代表 uncorrelated PSD component 的功率相加；若 grid 不同要先明確對齊。
- `ContinuousPSD.to_sampled(fb, theta=..., theta_points=...)` 以 one-sided direct aliasing sum 產生 `SampledPSD`；若要與 `LinkConfig` 對齊，caller 應傳入 `cfg.theta`。

