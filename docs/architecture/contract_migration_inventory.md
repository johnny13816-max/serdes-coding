# SerDes Coding Project Contracts

## 目的

這份文件記錄目前程式的 module 邊界與整理方向。原則是：

- `COM` algorithm 相關內容留在 COM domain。
- 通用 signal processing / S-parameter / PMF 工具獨立成可重用 module。
- Excel template 與 reference-data adapter 不放進 COM algorithm 本體。
- 先固定 contract，再搬 code。

## 目前檔案狀態

### `com_model_93A.py` / `com_model_178A.py`

兩個 versioned module 保留 COM algorithm 相關責任：

- COM 93A / 178A algorithm orchestration
- COM config/status dataclasses
- version-specific package/filter/S-parameter formula
- path build helpers
- DFE / sampling phase / imp / PMF helpers
- 不提供 legacy script entry；執行端由 notebook、test 或後續明確定義的 runner 呼叫 package API。

### Versioned COM Excel I/O

COM workbook I/O 分成四個 module：

- `com_excel_common.py`：只負責 sheet/table、scalar/sequence/bool、channel path 等共用格式解析，不做 93A/178A 欄位語意 mapping。
- `com_excel_io_93A.py`：負責 project workbook 與 legacy Ad Hoc workbook 到 93A runtime dataclass 的 mapping。
- `com_excel_io_178A.py`：負責 project workbook、run_config、178A package/filter/search 到 178A runtime dataclass 的 mapping；不接受 93A `f_z/f_LF` fallback。
- `com_excel_io.py`：compatibility facade，保留既有 public import；未加版本後綴的入口仍是 93A alias。

正式入口：

```python
from serdes_coding.io.com_excel_io import (
    excel_to_config_93A,
    excel_to_config_178A,
    excel_to_search_config_93A,
    excel_to_search_config_178A,
)
```

### `utilities/`

通用 signal-processing utilities 集中於 `utilities/`，不屬於特定 COM version：

- `link.py`
  - `LinkConfig`
  - `LinkSegment`
  - `SampledResponse`
- `psd.py`
  - `ContinuousPSD`
  - `SampledPSD`
  - `OneSidePSD`
- `sparam.py`
  - `SparamModel`
  - `SparamProcessor`
- `pmf.py`
  - `Pmf1D`

重要邊界：

- `LinkConfig`、`LinkSegment`、`SampledResponse` 共用 continuous/discrete grid contract，放在 `link.py`。
- `SparamModel` 與 `SparamProcessor` 的實作由 `sparam.py` 持有；其依賴 `LinkConfig`／`LinkSegment`，因為 S-parameter 轉 scalar response 是明確的單向資料流。
- `ContinuousPSD` / `SampledPSD` / `OneSidePSD` 的實作由 `psd.py` 持有；`psd.py` 不可 runtime import `link.py`，只以頻率 grid 與 response 的結構性 contract 運作，避免 PSD 與 link-response layer 形成循環依賴。
- `Pmf1D` 以 `pmf.py` 作為 PMF utility 入口。
- 舊的 `link_segment.py`、`pmf_handler.py` 保留為相容轉接層。

### PMF utility (`utilities/pmf.py`)

目前包含：

- `Pmf1D`
- PMF transform methods
- PMF helper functions
- 保留中的 module-level `fir_filtered_pmf()` 不得回傳 placeholder；未實作時必須明確拋出 `NotImplementedError`。`Pmf1D.uniform()` 已是完整的 bin-integrated uniform PMF constructor。

目前邊界：

- `Pmf1D` 保持獨立 module。
- `fir_filter()` / `combine()` 等 immutable transform 保留在 `Pmf1D`。
- 只被單一 method 使用的檢查邏輯留在 method 內部或 private nested function。
- module-level helper 只保留多個 function/class 會共用的東西。

## 目前 utility 目標結構

```text
serdes_coding/
  __init__.py
  utilities/
    __init__.py
    link.py
    psd.py
    sparam.py
    pmf.py
  link_segment.py       # compatibility shim
  pmf_handler.py        # compatibility shim
  models/
    __init__.py
    com_model_93A.py
    com_model_178A.py
  io/
    __init__.py
    com_excel_io.py
  search/
    __init__.py
    com_search_178A.py
    com_search_gui_178A.py
  reporting/
    __init__.py
    com_report_178A.py
```

目前只完成 utility layer 的第一階段整理；COM 大型 module 尚未拆分。後續優先順序是：

1. Excel input 與 PyChOpMarg adapter 已移到 `com_excel_io.py`。
2. 再把 COM dataclasses 拆成 `config.py` / `status.py`。
3. 再把 93A formula helpers 拆成 `formulas_93a.py`。
4. 再評估是否將 `utilities/link.py` 內部實作進一步拆成獨立 implementation modules。
5. 之後另行設計 Python 3.7 相容版 utilities，不與目前版本混放。

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

- `SparamModel.write_touchstone_s2p(path, form="ri")` 使用 scikit-rf 將目前的 differential Sdd two-port 輸出成標準 Touchstone 1.0 `.s2p`。兩個 port 分別代表 differential input/output，reference impedance 沿用 internal differential `z0`；輸出不會合成 single-ended S4P，也不會改動原模型。為避免 Touchstone 1.0 隱含錯誤，輸出只接受所有 frequency/port 共用的 real differential `z0`，且 path 必須明確以 `.s2p` 結尾。

## LinkSegment Contract

`LinkSegment` 代表已對齊 `LinkConfig` FFT grid 的 transfer/impulse/step/bit response。

重要假設：

- `tf` 使用 one-sided rFFT frequency grid。
- `raw_ir` 是 frequency-domain IFFT 的直接結果。
- `causal_ir` 是 raw IR circular shift 後、依 causality contract 得到的分析結果。
- `from_tf()` 對每個 circular shift 計算頭尾各 5% record 的能量和，選最小值；`causal_shift_samples` 保存 raw→causal shift。
- plot / cascade / COM path 使用 `causal_ir`。
- `ir2tf()` 預設使用 `raw_ir` 保留 round-trip definition。
- `to_sampled_response(pos=0, source="causal")` 將 CT response 轉為 symbol-rate `SampledResponse`。它以所選的 raw/causal IR 回推 CT TF，再對完整 two-sided DFT 做 alias sum；在 `Nfft % per_ui == 0` 時，結果必須與 `source_ir[pos::per_ui]` 再 `SampledResponse.from_ir()` 相同。
- `source="causal"` 是 COM 預設，對齊 `pulse.ir[pos::per_ui]`；`source="raw"` 僅用於維護 TF round-trip 的 time reference。

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
- `from_ir(ir, cfg)` 使用 `np.fft.rfft()`，並由 `cfg.sampled_nfft` zero-pad、由 `cfg.theta` 定義 sampled-domain grid。
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

目前不提供 `com_model.py` 或其他 module-level script entry。單次 run/search 由 notebook、test 或呼叫端明確建立 config 後使用 `COM(...).run(...)`。

預設 case-owned config:
- `cases/<case_id>/config/config_93A.xlsx`
- `cases/<case_id>/config/config_178A.xlsx`

入口模式:
- `spec_version = "93A"` 或 `"178A"`：選擇 spec implementation。
- `run_kind = "single_run"`：讀 `fixed_config`，執行單次 COM run。
- `run_kind = "search_run"`：讀 `fixed_config` + `search_config`，執行 search。

預設輸出:
- `cases/<case_id>/report/<spec_version>/<run_kind>/`

PyChOpMarg reference Excel 只作為 reference comparison 使用，不是 runtime input。

## COM Case Folder Contract

每個 COM study case 由 `cases/<case_id>/` 管理。case folder 同時保存 config、channel files、以及該 case 的 run output。

標準結構：

```text
cases/<case_id>/
  config/
    config_93A.xlsx
    config_178A.xlsx
  channels/
    victim_thru.s4p
    next_*.s4p
    fext_*.s4p
  report/
    93A/
      single_run/
      search_run/
    178A/
      single_run/
      search_run/
```

Workbook contract：
- `config_93A.xlsx` 使用 `excel_to_config()`，對應 `COMConfig`。
- `config_178A.xlsx` 使用 `excel_to_config_178A()`，對應 `COMConfig_178A`。
- 兩個 workbook 都應包含 `fixed_config`、`channels`，並可選擇包含 `search_config`。
- `fixed_config` 填 COMConfig/COMConfig_178A 的 fixed parameters。
- `search_config` 填 COMSearchConfig 的 search-space values。
- `channels` 填 victim / NEXT / FEXT S4P file location；路徑可以指向本 case 的 `channels/` 或穩定的 `reference_data/`。

Report contract：
- 新 run 不再輸出到 top-level `reports/`。
- 93A single run 輸出到 `cases/<case_id>/report/93A/single_run/`。
- 93A search run 輸出到 `cases/<case_id>/report/93A/search_run/`。
- 178A single run 輸出到 `cases/<case_id>/report/178A/single_run/`。
- 178A search run 輸出到 `cases/<case_id>/report/178A/search_run/`。
- report 內容是 local generated artifact，不納入 Git；repo 只用 `.gitkeep` 保留資料夾結構。

## COM Package Config Contract

`COMConfig` 不再使用單一共用 `pkg`。package model 拆成四組：
- `txpkg_victim`: victim path 的 TX package。
- `txpkg_fext`: FEXT aggressor path 的 TX package。
- `txpkg_next`: NEXT aggressor path 的 TX package。
- `rxpkg`: 所有 paths 共用的 RX package。

178A 的 `COMPkgConfig` 採 nested composition：

```text
COMPkgConfig
  device_term: COMDeviceTermConfig
  device_pkg: COMDevicePackageConfig
  partial_host: COMPartialHostConfig
  R0
```

- 各 sub-config 在自己的 `__post_init__()` 驗證並正規化公式參數；`COMPkgConfig` 只驗證 sub-config type 與共享 `R0`。
- TX package 串接為 `device termination -> device package -> partial host channel`。
- RX package 串接為 `partial host channel -> device package -> device termination`；`partial_host.enable=False` 時 partial-host block 是 identity two-port。

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

## LinkSegment Causality Guard Contract

- TF-originated `causal_ir` is selected by minimizing the combined energy in the first and final 5% of the IFFT record; it does not use a fixed main-cursor UI target.
- Purpose: reduce circular wrap-around at the record boundary without changing `raw_ir`, which remains the TF round-trip representation.
- `validate_causal_ir()` checks whether significant tail energy remains after causality handling.
- `COM` applies this guard to victim `H_21` and victim `pulse`.
- Xtalk paths are not forced to share this guard because their phase/reference selection is different from the victim ISI/DFE path.

## 178A Main-Cursor And Runtime Contract

- `COMMainCursorError` 表示某個 sampling phase 不可作為 178A DTE candidate：輸入 `h_dsamp` 的 dominant cursor 必須為正，且 final limited FFE output `h_w` 必須滿足 `argmax(abs(h_w)) == d`。
- 此 guard 在 `calculate_pre_dte_imp_at_pos()`、`COM_MMSE_DTE.run()` input validation、以及 DTE output validation 各執行一次；不自動 polarity flip 或修正 phase。
- `COM._run_once()` 的 pos sweep 只 catch `COMMainCursorError`：該 pos 的 `mse_by_pos[pos]` 保留 `None`、錯誤文字記於 `main_cursor_error_by_pos[pos]`，其他 exception 一律向外拋出。
- `COMRunStatus` 是單次 run 的 runtime record，目前保存 phase sweep 的 MSE/error arrays；178A selected solution 保存在 `COMStatus.dte: COMDTEStatus`。93A legacy `COMStatus.dfe` 僅屬於 93A model contract。

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

- 93A/178A 的 frequency-domain plot 預設顯示到 `1.1*baud_rate`，並以實際 available frequency 上限為界；annotated Nyquist point 不另外縮短 x-axis。annotation 依所在半邊向圖內展開。S-parameter absolute insertion loss 統一標示為 `IL@<frequency> = <value> dB`，scalar transfer function 則標示為 `Gain@<frequency> = <relative value> dB`。

- 93A single-run plot 採與 178A 相同的 presentation convention：frequency-domain 使用 log x-axis 並以 `f_nyq=fb/2` 標示；victim path folder 為 `path_victim/`；另輸出 channel/augmented-path IL、CT pulse 與 selected DT samples、impairment variance proportion、PMF component moments，以及含 `DER_0/A_ni/COM` 標示的 logarithmic combined CDF。93A status 沒有保存 178A 的 per-phase MSE trace 或 MMSE matrices，因此不產生沒有來源資料的對應圖。

- `LinkSegment.plot_tf(x_scale="log")` 預設使用 logarithmic frequency axis，顯示第一個正頻率 bin `df ~ fb` 的 in-band view；DC 保留在資料中，但不能顯示在 log axis。
- `LinkSegment.plot_tf(x_scale="linear")` 顯示原本的 `0 ~ fb` in-band view。
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
- 新 public module 使用版本化檔名：`com_model_93A.py`、`com_model_178A.py`。
- 在版本化 module 內，public class/function/method 不再需要 `_93A` 或 `_178A` postfix。
- package-level import 提供 `COM93A`、`COM178A` 作為簡潔入口。
- legacy `com_model.py` 已移除；93A / 178A runtime 只使用各自的 versioned module。
- 共用 infrastructure 不加版本後綴，例如 `COMStatus`、`COMReport`、`SparamModel`、`LinkSegment`、`Pmf1D`。

Public import contract：

```python
from serdes_coding.models.com_model_93A import COM, COMConfig
from serdes_coding.models.com_model_178A import COM, COMConfig

from serdes_coding import COM93A, COM178A
from serdes_coding.io.com_excel_io import excel_to_config_93A, excel_to_config_178A
```

目前拆分狀態：
- 不使用 `com_common.py`。版本關係固定為：`com_model_178A.py` 可 import `com_model_93A.py` 的穩定 v1 基礎；93A 不依賴 178A。
- `com_model_93A.py` 已擁有 93A config/status/pipeline；`com_model_178A.py` 已擁有 178A config/status/PSD/MMSE-DTE/pipeline。
- 178A 目前從 93A 取得共用 path/status/report/search 基礎。

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

Legacy import contract 仍保留：

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
- `COM_178A._run_once()` 的 single-run stage 順序為：
  ```text
  build_all_paths()
    -> calculate_pre_dte_imp_common(victim, h_XTs)
  -> for pos in range(link_cfg.per_ui)
         -> calculate_pre_dte_imp_at_pos(victim, pos, common)
         -> calculate_MMSE_DTE_178A(victim, imp_pre, pos)
    -> select best candidate
    -> calculate_post_ffe_imp(best_imp_pre, best_dte, h)
    -> optional calculate_COM_DFE(best_imp)
    -> calculate_pre_mlsd_imp() [reserved]
    -> calculate_COM_MLSD() [reserved]
  ```
- 178A `_run_once()` 採 incremental status contract：一開始建立 `self.status = COMStatus()`，每個 stage 先顯式輸出一個物件，再 merge/assign 進 `self.status`。如果中途錯誤，已完成的 `paths`、`imp`、`dfe` 等部分結果仍留在 `self.status`，方便 debug。
- 178A final impairment status 以 receiver-processing stage 分組：
  ```text
  status.imp.pre_dte: COMImpStageStatus
  status.imp.post_ffe: COMImpStageStatus
  status.imp.pre_mlsd: COMImpStageStatus

  COMImpStageStatus
    .psd: COMPSDStatus
    .eq_ch: COMEqChannelStatus
    .adc_input: COMAdcInputPMF
  ```
- `pre_dte_imp_common` 是 `_run_once()` 內的 run-local cache：`calculate_pre_dte_imp_common()` 回傳 `(COMPSDStatus, h_XTs_dsamp)`，供每個 `pos` 重用；選出 phase 後，common terms 會包含於 `status.imp.pre_dte.psd`，但 cache 本身不是獨立 status stage。
- `COMPSDStatus` 只存 PSD objects、PSD-derived sigma、PSD-derived scalar metadata。
- `COMEqChannelStatus` 只存 `h_xx` sampled/equivalent-channel sequences。
- `COMAdcInputPMF` 只存 ADC quantization clipping/noisy-signal PMF intermediate。
- 178A pos sweeping contract：每個 `pos` 以 common cache 與 `h_XTs_dsamp` 產生 `pre_dte_imp: COMImpairmentStatus` 與 `dte_status: COMDTEStatus`，loop 結尾以 `dte_status.mse` 和歷史最佳值比較，更新 `best_dte` / `best_imp_pre`。
- `calculate_COM_DFE()` 是 post-FFE 後的 DFE-based final COM stage；`calculate_COM_MLSD()` 已保留為顯式 stage placeholder，尚未實作 MLSD。
- `calculate_pre_dte_imp_common()` 是 run-local cache，不是 `status.imp` 的 field。它只建立並快取不依賴 victim `pos` 的 `sigma_X`、`S_rn/sigma_rn`、`S_xn/sigma_xn` 與各 crosstalk path 的 worst-phase `h_XTs_dsamp`，避免每個 `pos` 重複運算。
- `calculate_pre_dte_imp_at_pos()` 不吃 DFE/DTE result；它吃 `pos`、common cache 與 `h_XTs_dsamp`。它在 `status.imp.pre_dte.psd` 產生 `S_tn`、`S_jn`、`S_qn`、`S_total`、對應 sigma 與 `R_n`；在 `status.imp.pre_dte.eq_ch` 產生 `h_dsamp/h_tn/h_J/h_XTs_dsamp`；在 `status.imp.pre_dte.adc_input` 保存 pre-DTE quantization material。`pos/ts` 是 sampling/DTE metadata，不屬於 impairment status；MMSE DTE solver 由 `h_dsamp` 推導 `ts = pos + d_h * per_ui` 後唯一保存在 `COMDTEStatus`。
- `calculate_post_ffe_imp()` 吃 selected pre-DTE impairment、selected DTE result、oversampled victim pulse `h`，負責 FFE/DFE 後的 finalization；在 all-stage shared `status.imp.eq_ch` 建立 `h_w/h_XTs_w/h_ISI/h_w_J`，在與 `h_w` 對齊的 post-DTE grid 建立供 93A-aligned reporting 使用的 `S_rn/S_xn/S_tn/S_jn/S_qn/S_total`，並保存 `A_s/sigma_ISI/sigma_G`。selected ADC-input exact PMF material 保存在 `status.imp.post_ffe.adc_input`。raw `COMDTEStatus.w_lim` 用於 coefficient report；`status.imp.H_rxffe` 是相同 FIR 在 expanded post-DTE grid 的 `SampledResponse`。
- 178A residual ISI follows Eq. 178A-40: `h_ISI[d + 1]` is always set to zero because the normalized desired cursor is not ISI; DFE feedback subtraction is then applied at `d+2 ... d+N_b+1`.
- 178A `A_s` 依 Eq. 178A-37 定義為 `R_LM / (L - 1)`；因為 MMSE DTE 解已將 equalized pulse main cursor 正規化為 1，所以不再乘 `h_main`。正式 `A_s` 在 `calculate_post_ffe_imp()` 產生，供 final PMF/COM 使用。
- `calculate_MMSE_DTE_178A()` 是 178A.1.8 receiver FFE/DFE MMSE solve 的正式入口，取代舊的 `find_pos_and_dfe_178A()` 名稱；它輸出 `COMDTEStatus(ts, pos, d, w_lim, b_lim, pruned_index, mse, ...)`。
- 178A `COM_MMSE_DTE.run()` 採明確五步：Step 1 建立 full MMSE matrices；Step 2 依 runtime profile 的 `floating_mode` 選擇 fixed-plus-floating `pruned_index`；Step 3 解該 tap placement 的 MMSE system；Step 4 套用 DFE/FFE limiter 與 FFE refinement；Step 5 計算 final MSE 並建立 `COMDTEStatus`。
- `floating_mode="heuristic"` 以 channel ISI group energy 選 non-overlapping floating FFE groups；`"simplified"` 先進行一次 full-FFE MMSE solve，再以 raw FFE group energy 選 group；`"spec-defined"` 會列舉全部合法的 floating FFE group placement，對每組完成 Eq. 178A-31 至 Eq. 178A-35，並以套用 limiter 後的 final MSE 最小者為結果；不可 fallback 到 heuristic 或 simplified。
- 178A floating groups 的合法條件：每個 group 恰有 `N_wf` taps、位於 `[N_fix, N_max)`、groups 彼此不重疊。selector 回傳固定 taps 在前、floating taps 在後的 ascending `pruned_index`；`pruned_index` 只保存 solver placement / matrix-column 的診斷資訊。`COMDTEStatus.w_lim` 與 `w` 已在 `_build_dte_status()` scatter 回固定 `(N_max,)` 的 raw zero-filled vector，不需再依 `pruned_index` 重建。
- 178A outer TXFFE/CTLE search 以每個 candidate 的最小 valid limited-DTE `MSE` 作為唯一 selection metric；不定義或計算 93A-style FOM。`COMSearchRow.mse` 的單位為 `V^2`，排序方向為由小到大。93A 的 FOM search contract 保持獨立不變。
- `COMFilterConfig.c_0_min` 是 Ad Hoc `param.tx_ffe_c0_min` 的 runtime mapping。config 只負責保存 candidate；實際建立 `H_ffe` 時才計算 `c(0)=1-sum(abs(c(i)), i!=0)`。若 `c(0) < c_0_min` 或 `c(0)` 不是最大幅度 tap，則拋出 `COMTxfirMainCursorError`。178A partial search 將此類 candidate 寫為 `status="infeasible"`，保留原因並直接進入下一個 candidate，不受 `continue_on_error` 控制。一般執行錯誤仍使用 `status="error"`。
- `IEEECOMsparam` 已建立 178A S-parameter builders：
  - `device_termination_178A()`：Eq. 178A-7 N-stage LC ladder，輸入 L/C vectors 與 bump capacitance。
  - `device_package_178A()`：Eq. 178A-9 N-stage package transmission line，輸入 TL length / impedance vectors 與 package capacitance。
  - `partial_host_channel_178A()`：Eq. 178A-10 synthetic partial host channel，輸入 C0 / C1 / TL parameters。
- `IEEECOMFilter.rx_equalizer_178A()` 使用 178A spec-facing `f_z1/f_z2/f_p1/f_p2/f_p3` interface。由 aligned 93A Ad Hoc mapping 時，`f_HP_PZ` 同時映射到 `f_z2` 與 `f_p3`，保留 93A `f_LF` 同時出現在 numerator/denominator 的數學角色。
- `calculate_pre_dte_imp_at_pos()` 已建立 178A.1.7 sampled-domain PSD flow：
  - `S_rn`: receiver input noise PSD, Eq. 178A-17。
  - `S_xn`: crosstalk PSD summed over all aggressor paths, Eq. 178A-18；每條 crosstalk path 使用自己的 `t_s^(k)`，並選擇使 `sum_n [h_xn^(k)(n)]^2` 最大的 worst-case phase，不跟 victim candidate `pos` 綁定。
  - `S_tn`: transmitter output noise PSD, Eq. 178A-19 / 178A-20。
  - `S_jn`: transmitter jitter-induced noise PSD, Eq. 178A-21 / 178A-22；finite difference 使用 `Delta t = link_cfg.dt`，並輸出 V/UI 的 sampled jitter sensitivity。
- `S_qn`: Eq. 178A-26 to Eq. 178A-28。`N_qb/P_qc` 未提供時關閉量化雜訊；runtime profile 的 `pre_dte_pmf_method="gaussian_approx"` 只保存 `p_sig/V_qc/delta`；`"pmf_exact"` 保存 `p_sig/p_s/p_ga/p_sn/V_qc/delta`，再建立 white `S_qn`。ADC PMF intermediate 屬於 `status.imp.pre_dte.adc_input`。
- 178A quantization contract 分成兩層：runtime profile 的 `pre_dte_pmf_method` 只控制 pre-DTE `S_qn`，供 MMSE 建立 `S_total/R_n`；選定 pos 後，`calculate_post_ffe_imp()` 以 selected pre-DTE signal、XT、DDJ 與 Gaussian noise 建立 `method="pmf_exact"` 的 ADC-input PMF material，保存 `p_sig/p_s/p_XT/p_DD/p_ga/p_n/p_sn/V_qc/delta` 至 `status.imp.post_ffe.adc_input`。post-DTE reporting `S_qn` 由同一 `delta` 的 white ADC PSD 通過 `H_rxffe` 建立。`calculate_COM_DFE()` 讀取此 exact `delta` 建立 FFE-filtered `p_qn`，不重算 `V_qc`；兩者 RMS 必須在 PMF discretization tolerance 內一致。
  - `S_total`: sum of enabled PSD components on `cfg.theta`。
  - `R_n`: sampled-domain noise autocorrelation derived from `S_total` for MMSE use。
- Interference source Eq. 178A-24/25 is intentionally ignored in the current project scope and is not represented as a status field。
- 178A residual ISI is not finalized in `calculate_pre_dte_imp_at_pos()` and is not stored in `COMDTEStatus`; it belongs to `calculate_post_ffe_imp()` / `status.imp.post_ffe` and later PMF flow。
- 178A PMF 需要先以 post-FFE `A_s` 呼叫 `COMPMFConfig.resolve(A_s)`；所有 PMF helper 應使用 `COMPMFRuntimeConfig`，不能直接把 unresolved `COMPMFConfig` 傳入需要 `dy/tap_abs_th` 的函式。
- 若 DTE 有 floating tap gap，`COMDTEStatus.w_lim` 仍是固定長度的 raw zero-filled FIR vector；`_build_dte_status()` 已完成 scatter。post-FFE stage 以 origin grid 的 FIR response 建立完整 linear-convolution `h_w/h_XTs_w/h_w_J`，再將同一 FIR 表示於 expanded post-DTE grid 作為 `H_rxffe`，供 post-DTE reporting PSD filtering。MMSE、final quantization PMF FIR 與 coefficient report 一律使用 raw vector。
- 178A `COMDTEConfig` 的 project-facing limiter 都是 scalar：`w_pre1_max`、`w_post1_max`、`w_fixed_rest_max`、`w_float_min/max`、`b_first_min/max`、`b_rest_min/max`。`__post_init__()` 依 `d_w`、`N_fix`、`N_max` 展開 solver 使用的 full FFE index-domain `w_upper/w_lower`，並依 `N_b` 展開 DFE `b_upper/b_lower`；main FFE tap `d_w` 強制為 `1.0`。每個 placement 以 `cfg.w_lower[pruned_index]`、`cfg.w_upper[pruned_index]` 取得 limiter。這與 93A 的 floating DFE feedback limiter 不共用。
- 178A project workbook 保留 Ad Hoc 的 limiter 分類：`w_pre1_max` 對應 `ffe_pre_tap1_max`，`w_post1_max` 對應 `ffe_post_tap1_max`，`w_fixed_rest_max` 對應 `ffe_tapn_max`；`b_first_*` / `b_rest_*` 分別描述第一個與後續 DFE feedback tap。fixed FFE lower limit 預設為其 upper limit 的負值，符合目前 Ad Hoc FFE limiter 的對稱表示；若未來出現非對稱 FFE limit，再明確新增 scalar 欄位。`floating_mode` 是 project runtime method，不是 Ad Hoc config 的 direct mapping。
- `COMImpairmentConfig.eta_0` is stored in internal SI units `V^2/Hz`; IEEE 178A Table 178A-9 lists `eta_0` in `V^2/GHz`, so Excel/reference adapters must convert before constructing `COMImpairmentConfig`。
- 目前可直接呼叫 `COM_178A(cfg).build_all_paths()` 檢查 178A path-building；`COM_178A.run(search)` 會以 MSE 選擇 TXFFE/CTLE candidate，下一個主要風險在 final PMF/COM flow 的數值驗證。
- 正式 178A case 必須從各 case 的 `config/config_178A.xlsx` 載入，不再由 93A config 轉換。
- 178A runtime profile 的 `pre_dte_pmf_method` 控制 pre-DTE `S_qn` 的 `V_qc` 計算方式：`"gaussian_approx"` 用 signal variance + Gaussian noise variance 快速近似 noisy signal CDF；`"pmf_exact"` 保留 spec-like `p_sn=conv[p_s,p_ga]` 的慢速 reference 路徑。
- `COMReport178A(cfg, status)` 是 178A single-run 的 presentation-only layer：不重算或修改任何 COM quantity。文字檢視直接使用 `print(status)`；圖像輸出依 status stage 分組為 `path_victim/`、`phase_dte/`、`imp_pre_dte/`、`imp_post_ffe/`、`pmf/`。報表優先呼叫 `SparamModel`、`LinkSegment`、`SampledPSD`、`Pmf1D` 既有 plot method，只在報表層補上 stage title、config annotation 與多圖組合。`path_victim/` 的所有頻率域圖使用 logarithmic x-axis 並排除 DC bin；時域 response 維持線性時間軸。所有 report 的 discrete-time sequence 預設以主游標為零點，顯示 `[-5, 20] UI`；`phase_dte/` 另輸出 `dte_coefficients.png`（limited FFE `w_lim` 與 feedback-subtracted `-b_lim`）及 `unlimited_dte_coefficients.png`（unlimited FFE/DFE 與 limiter mask；FFE mask 依 unlimited main coefficient 縮放）。
- 178A `pre_dte_pmf_method="gaussian_approx"` 不建立 exact `p_s` / `p_sn` convolution；它以 `var_symbol * sum(h_dsamp^2) + sigma_ga^2` 建立近似 Gaussian ADC-input PMF，供 `V_qc` 與 `S_qn` 的快速估算。報表在此模式只畫該近似 `p_sn`，避免將 normalized `p_sig` 與 voltage-domain `V_qc` 畫在同一條 amplitude axis。`pmf_exact` 的 ADC-input report 改為兩張圖：`adc_input_components.png` 上/下子圖分別為 `p_s` 與 `p_n`（pre-DTE 若沒有獨立 `p_n`，以同一計算中的 `p_ga` 呈現）；`adc_input_distribution.png` 上/下子圖分別為 `p_sn` PDF 與 CDF，並標示雙側 `+/-V_qc`、`P_qc`、兩端 CDF 值。
- `Pmf1D.fir_filter()` 與 `Pmf1D.combine()` 保持既有 uniform-grid PMF contract，統一使用 `scipy.signal.fftconvolve`，並只消除 FFT round-off 造成的極小負 mass、重新正規化 total mass。此 backend 不改變 `dy`、PMF support/grid index 或 `keep_mass` 截斷規則。
- 178A single-run debug entry 位於 `models/com_model_178A.py` 最下方的 `if __name__ == "__main__"`。以 `python -m serdes_coding.models.com_model_178A` 執行；只需修改 `CASE_ID`，其餘路徑固定為 `cases/<case_id>/config/config_178A.xlsx` 與 `cases/<case_id>/report/178A/single_run/`。此入口依序載入 config、執行 `COM(cfg).run()`、`print(status)`、呼叫 `COMReport178A`。
- 178A debug entry 使用 canonical module path；不再支援 root-level `com_model_178A.py` facade 的 direct script execution。IPython 請使用 `%run -m serdes_coding.models.com_model_178A` 或以 package module 執行。
- `COM.run(progress=True)` 僅適用於 interactive single run。它會以 wall-clock 時間印出 build paths、pre-DTE common、每個 `pos` 的 `pre_dte_imp_at_pos` 與 `MMSE_DTE`、post-FFE 與 COM DFE stage；不改變 status、計算結果或 search 的 file-backed logging。
- package root 的 178A model、report、search、Excel public helpers 採 lazy import，避免 debug entry 與 Excel parser 載入兩份 versioned dataclass。對外的 `from serdes_coding import COM178A, excel_to_config_178A` 介面保持可用。

178A Excel / search contract：
- 每個 case 同時保留 `config/config_93A.xlsx` 與 `config/config_178A.xlsx`；兩者是獨立 versioned input，不互相轉換。
- `excel_to_config_178A()` 接受 project-owned 178A workbook 的 `fixed_config`、`run_config` 和 `channels` sheets。`fixed_config` 描述物理模型；`run_config` 描述一次執行的計算策略。欄位名稱必須直接對應 `COMConfig_178A` 與 nested `COMPkgConfig`：`device_term`、`device_pkg`、`partial_host`。
- `excel_to_search_config_178A()` 只讀取 `search_config` 的 native search fields：`c_m2`、`c_m1`、`c_1`、`g_1`、`g_2`。
- 178A parser 不接受 `g_DC/g_DC2`、93A `H_ctf` 欄位、單級 `C_d/L_s/z_p/Z_c` 或任何 93A fallback/default mapping；缺少 required field 必須直接報錯。
- COM Ad Hoc workbook 仍是 source reference，不是 runtime input。其 package profile、單位及 search range 先人工/前處理映射到 project-owned `config_178A.xlsx`，再由上述 parser 建立 dataclass。
- `excel_to_search_config()` 仍使用共用 `COMSearchConfig`，Excel 欄位保持 `c_m2/c_m1/c_1/g_DC/g_DC2`；在 `COM_178A` search 內部，`g_DC/g_DC2` 會 mapping 到 178A CTF 的 `g_1/g_2`。
- `COMRunConfig` 定義單一 execution profile：`target in {"mse", "dfe", "mlsd", "full"}`、`pre_dte_pmf_method in {"gaussian_approx", "pmf_exact"}`、`pmf_grid_quality in {"coarse", "fine"}`、`floating_mode in {"heuristic", "simplified", "spec-defined"}`、`pos_sweep_method in {"each_phase", "coarse_fine"}`，以及正整數 `pos_coarse_stride`。
- `COMExecutionConfig` 固定持有 `single_run`、`search_sweep`、`search_final` 三個 `COMRunConfig`，以及 `search_group_size`、`search_top_k`。178A `COMConfig` 將它作為 `execution` 欄位；物理 `COMImpairmentConfig` 與 `COMDTEConfig` 不再持有 execution method。
- `run_full_search_178A.py --phase-sweep each_phase` 可在不修改 fixed/search space 的前提下，將此次 full search 的 `search_sweep` 強制改為 exhaustive phase sweep；`prepare`、`partial`、`finalize` 三個 job 必須使用同一值，才能進行 coarse/fine 與 each-phase A/B 比較。
- `run_config` sheet 的欄位為 `Profile/Parameter/Value/Unit/Description`。目前 case 預設：single run 與 final 都使用 `target="dfe"`、`pre_dte_pmf_method="pmf_exact"`、`pmf_grid_quality="fine"`、`pos_sweep_method="each_phase"`；sweep 使用 `target="mse"`、`pre_dte_pmf_method="gaussian_approx"`、`pmf_grid_quality="coarse"`、`pos_sweep_method="coarse_fine"`；三者均使用 `heuristic`；`pos_coarse_stride` 為 4，group size 為 100，top-K 為 10。
- 178A `COM.run()` 在 single run 時使用 `execution.single_run`；outer search 的 candidate sweep 使用 `execution.search_sweep`，最佳 candidate re-run 使用 `execution.search_final`。profile 會顯式傳入 pre-DTE quantization 與 MMSE-DTE，不允許 stage 偷讀 `single_run`。
- 178A `_run_once(run_cfg=...)` 的 target contract：`"mse"` 完成 path/pre-DTE/best-DTE 後返回；`"dfe"` 再完成 post-FFE 與 DFE COM PMF；`"mlsd"` 或 `"full"` 會進入保留的 MLSD stage。目前 MLSD 尚未實作，會拋出 `NotImplementedError`，不會產生假結果；此前已完成的 incremental status 仍保留在 COM instance。
- 178A phase-sweep contract：`each_phase` 評估 `0..per_ui-1` 全部 phase；`coarse_fine` 先以 `range(0, per_ui, pos_coarse_stride)` 評估，再以 coarse 最佳 phase 為中心評估未訪問的 circular fine window。每一個 phase 都由 `calculate_pos_candidate(pos=...)` 明確產生 `(imp_pre, dte_status)`；`COMRunStatus.mse_by_pos` 以 `None` 保留未訪問或 main-cursor error 的 phase，`coarse_pos` 與 `fine_pos` 保存兩階段實際評估的 phase index，供 report 區分繪圖。
- 178A outer-search orchestration 位於 `com_search_178A.py`。`com_model_178A.py` 只保留單一 candidate 的 spec pipeline 與一行 delegation；不保留 manifest、CSV、group、top-K 或 GUI 邏輯。
- `create_search_plan(cfg, search, report_dir)` 產生 `full_search_manifest.csv` 與 `group_plan.csv`。manifest 的 `search_index` 是固定 candidate identity；group 的 `start/stop` 採 Python slice convention，`stop` 為 exclusive。
- `run_partial_group(cfg, search, report_dir, group_id)` 只執行一個 group，使用 `execution.search_sweep` 的 `target="mse"`，輸出 `group_results/group_XXX.csv`。每列保存 search candidate、`status/error`、`mse/mse_dB/ts/pos`；`mse` 單位為 V^2，`mse_dB` 定義為 `10*log10(A_s^2/mse)`，其中 `A_s=R_LM/(L-1)`，不代表額外執行 post-FFE。
- `merge_partial_results(report_dir)` 會檢查每個 planned group 存在，且所有 `search_index` 對 manifest 恰好覆蓋一次，再輸出 `merged_partial_results.csv`。
- `finalize_search(cfg, search, report_dir)` 依 MSE 選前 `execution.search_top_k` 個 successful candidates，以 `execution.search_final` 重跑；每個 final status 寫入 `top_K/<search_index>/`。`full_search_results.csv` 會保留前 `10 * execution.search_top_k` 個 successful partial candidates；只有前 `search_top_k` 筆填入 `final_status/final_error/COM_dB`，其餘 final 欄位留白，供比較 partial ranking 與完整 COM 結果。若某個 final candidate 失敗且 `continue_on_error=True`，會記錄錯誤並嘗試下一個 MSE candidate。
- `run_full_search(...)` 只是上述四個 action 的 sequential convenience API。手動分散運算、日後 GUI 或多台機器都應直接呼叫各 action，不需要依賴 `COM` instance state。
- `COM.run(search=..., report_dir=...)` 保留 convenience delegation；178A search 因必須有可合併檔案，未提供 `report_dir` 時會直接報錯。標準輸出位置是 `cases/<case_id>/report/178A/search_run/`。
- `com_search_gui_178A.py` 是手動 split-search GUI：只接受 `<case>/config/config_178A.xlsx`，只輸出到 `<case>/report/178A/search_run/`。它提供 Load case、Create Manifest、Run Group、Merge Results、Finalize Top-K、Run Full Search；background thread 只負責呼叫 `com_search_178A.py` public actions，GUI 不含 COM 演算法或 candidate loop。
- GUI 啟動方式：`python -m serdes_coding.search.com_search_gui_178A --case cases/<case_id>`。不帶 `--case` 時可在 GUI 內 Browse case folder。
- 178A search status/export 使用 `mse`、`best_row_mse`、`search_mse_trace.png` 與 `search_top_candidates.png`，不重用 93A 的 FOM label 或排序。

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
- 178A COM 邏輯中的陣列長度、path 數量、shape 與 sampled DFT window 不符合時，統一拋出 `COMLengthMismatchError`；不可藉由隱式截斷或 padding 掩蓋長度契約錯誤。
- `COMImpairmentStatus.eq_ch` 是 all-stage shared equivalent-channel status；`COMImpStageStatus` 只保存該 stage 的 PSD 與 ADC-input PMF，不再各自保存 legacy `eq_ch`。
- 178A 的 `h_dsamp` 是 `SampledResponse`；DTE `w_lim` 是 fixed `(N_max,)` raw FFE vector。post-FFE stage 以 raw `w_lim` 建立 `H_rxffe: SampledResponse`，並以它與 `h_dsamp.cascade_ir()` 產生完整 linear-convolution `h_w`；其他 post-FFE response 使用相同 expanded sampled grid。
- COM DFE 的 Gaussian noise PMF 直接使用 `sigma_G`。`sigma_G` 由 selected pre-DTE `S_rn + S_tn + S_jn_RJ` 在 origin grid 通過 RX FFE 一次後積分取得；post-DTE display PSD component 的 grid、插值或繪圖定義不得改變 DFE COM。
- `ContinuousPSD.to_sampled(fb, theta=..., theta_points=...)` 以 one-sided direct aliasing sum 產生 `SampledPSD`；若要與 `LinkConfig` 對齊，caller 應傳入 `cfg.theta`。

- `SampledPSD.plot(x_axis="CT")` 預設以等效 baseband `f = theta*fb/(2*pi)` 的 Hz 軸繪圖；傳入 `x_axis="DT"` 才顯示 `theta`（rad/sample）。兩種選項都不改變 PSD 數值或其 `quantity^2/Hz` 單位；CT 軸不是未 alias 的原始 broadband CT PSD。
