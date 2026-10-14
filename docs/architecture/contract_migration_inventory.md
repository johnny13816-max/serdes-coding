> **Status: migration inventory; not authoritative.** Use the documents linked from `docs/README.md` for current rules. Items here remain only until they are source-checked and moved to their owning architecture, model, validation, or operations document.

# Contract migration inventory

## Purpose

This file is a temporary inventory from the former all-in-one project contract. It is not part of the authoritative reading order. Move an item only after checking it against current source and the documentation ownership rules.

- Project-wide boundaries move to `docs/architecture/`.
- Execution procedures move to `docs/operations/`.
- Version-specific config, status, calls, stages, equations, and limitations move to `docs/models/<version>/` only after the required model review.
- Validation claims move to `docs/validation/` with reproducible evidence.

Do not copy mathematical statements from this inventory into authoritative model documentation without the protected-model review required by `AGENTS.md`.

## Completed migrations

- Module ownership and helper placement moved to `software_layers.md` after source inspection.
- Manual and search execution moved to `docs/operations/`.
- Plot, export, Matplotlib, frequency-display, and artifact ownership moved to `reporting_architecture.md` after source inspection.
- The obsolete `debug_case_93a_style` workbook and its missing-channel validation note were removed; Git history retains the retired artifact.
- 178A configuration ownership and workbook mapping moved to `docs/models/178A/config_tree.md` after dataclass, mapper, and workbook inspection.
- 178A status ownership, lifecycle, and reporting/search consumers moved to `docs/models/178A/status_tree.md` after dataclass, assignment, and consumer inspection.
- 178A manual, single-candidate, local-search, and distributed-search calls moved to `docs/models/178A/call_tree.md` after model, search, script, and workflow inspection.
- 178A path construction moved to `docs/models/178A/stages/path_construction.md` after channel-loader, package/filter builder, path/status, and reporting-consumer inspection.
- 178A pre-DTE common cache, per-phase impairment, ADC-input policy, and status ownership moved to `docs/models/178A/stages/pre_dte.md` after model and reporting-consumer inspection.
- 178A phase scheduling and MMSE-DTE placement, limiter, selection, and status ownership moved to `docs/models/178A/stages/mmse_dte.md` after solver, orchestration, and reporting-consumer inspection.
- 178A post-FFE response, residual-ISI, Gaussian/ADC input, reporting-PSD boundary, and regression evidence moved to `docs/models/178A/stages/post_ffe.md` after model, test, and reporting-consumer inspection.
- 178A DFE final-PMF accuracy policy, component ownership, quantization handoff, combined PMF, status, and current regression evidence moved to `docs/models/178A/stages/com_dfe.md` after model, test, and reporting-consumer inspection.
- 178A MLSD enablement, added-noise solver/history, detector PSD/autocorrelation, truncated DER, final adjustment, and reporting consumers moved to `docs/models/178A/stages/com_mlsd.md` after model and reporting-consumer inspection.

## PMF utility notes awaiting review

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
- `SparamModel.from_touchstone()`／`from_network()` 的 optional `frequency_limit_Hz` 擁有 measured-record boundary。它保留第一個 `f >= limit` 的樣本；`limited_to_frequency()` 提供相同的 immutable 既有物件操作。S4P-first 的順序固定為 full S4P renormalization → limit → mixed-mode conversion。

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

## COM Downsample Debug Contract

`COM_93A` exposes these debug proxies after `COM_93A.run()` or `_run_once()`:

- `com.h_dsamp`: victim pulse sampled at the selected DFE sampling phase.
- `com.t_dsamp_ui`: discrete UI time axis for `h_dsamp` and `h_ISI`, with main cursor at 0.

Debug plot methods:

- `com.plot_h_dsamp(ax=None, save_path="", xlim_ui=(-5, 20), label=None)`
- `com.plot_h_ISI(ax=None, save_path="", xlim_ui=(-5, 20), label=None)`
- `com.plot_h_J(ax=None, save_path="", xlim_ui=(-5, 20), label=None)`

`h_J` uses its own reconstructed finite-difference UI axis because boundary samples may be skipped.

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


- `COMImpairmentConfig.eta_0` is stored in internal SI units `V^2/Hz`; IEEE 178A Table 178A-9 lists `eta_0` in `V^2/GHz`, so Excel/reference adapters must convert before constructing `COMImpairmentConfig`。
- `Pmf1D.fir_filter()` 與 `Pmf1D.combine()` 保持既有 uniform-grid PMF contract，統一使用 `scipy.signal.fftconvolve`，並只消除 FFT round-off 造成的極小負 mass、重新正規化 total mass。此 backend 不改變 `dy`、PMF support/grid index 或 `keep_mass` 截斷規則。
- package root 的 178A model、report、search、Excel public helpers 採 lazy import，避免 debug entry 與 Excel parser 載入兩份 versioned dataclass。對外的 `from serdes_coding import COM178A, excel_to_config_178A` 介面保持可用。



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
- 178A 的 `h_dsamp` 是 `SampledResponse`；DTE `w_lim` 是 fixed `(N_max,)` raw FFE vector。post-FFE stage 以 raw `w_lim` 建立 `H_rxffe: SampledResponse`，並以它與 `h_dsamp.cascade_ir()` 產生完整 linear-convolution `h_w`；其他 post-FFE response 使用相同 expanded sampled grid。
- `ContinuousPSD.to_sampled(fb, theta=..., theta_points=...)` 以 one-sided direct aliasing sum 產生 `SampledPSD`；若要與 `LinkConfig` 對齊，caller 應傳入 `cfg.theta`。

- `SampledPSD.plot(x_axis="CT")` 預設以等效 baseband `f = theta*fb/(2*pi)` 的 Hz 軸繪圖；傳入 `x_axis="DT"` 才顯示 `theta`（rad/sample）。兩種選項都不改變 PSD 數值或其 `quantity^2/Hz` 單位；CT 軸不是未 alias 的原始 broadband CT PSD。
