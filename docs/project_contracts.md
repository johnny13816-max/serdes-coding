# SerDes Coding Project Contracts

本文件記錄目前程式架構的簡潔 contract。內容以快速回憶為主，不放長篇推導。

## COM Class

### 目的

`COM` 是單次 COM pipeline 的協調物件。它負責使用 `COMConfig` 建立 paths、DFE status、impairment status，後續也會接 PMF status。

### Last-Run Status

`COM.run()` 會回傳 `COMStatus`，同時保存到：

```python
com.status
```

因此 `COM` 內部 proxy 都是 run 後可用。若還沒呼叫 `run()` 就讀取 proxy，會 raise `RuntimeError`。

### Proxy

目前 `COM` 提供以下捷徑：

- `com.paths`: 等同 `com.status.paths`
- `com.victim`: 等同 `com.status.victim`
- `com.xtalks`: 等同 `com.status.xtalks`
- `com.h`: victim pulse response，等同 `com.victim.pulse.ir`
- `com.h_XT`: crosstalk pulse responses，等同 `[path.pulse.ir for path in com.xtalks]`
- `com.dfe_status`: 等同 `com.status.dfe`
- `com.impairment_status`: 等同 `com.status.impairment`
- `com.pmf_status`: 等同 `com.status.pmf`

### Helper Boundary

`_find_sampling_phase_93a()` 是 module-level helper，專門負責 93A Eq. 93A-25 的 sampling phase search。

`COM.find_pos_and_dfe()` 負責：

1. 呼叫 `_find_sampling_phase_93a()` 取得 `ts` 與 `pos`。
2. 根據 `ts/pos` 計算 fixed DFE taps。
3. 若啟用 floating DFE，計算 floating taps。
4. 建立 `COMDFEStatus`。

## COM PMF Domain

### 目的

`COMPMFConfig`、`COMPMFRuntimeConfig`、`COMPMFStatus` 對應 IEEE 802.3 Annex 93A.1.7 的 PMF-domain 計算流程。

### Config Boundary

`COMPMFConfig` 是 user/input policy，不保存本次 run 的 resolved 數值。

欄位：

- `dy_override`: 使用者強制指定 PMF amplitude grid step，單位 V；若為 `None`，由 `As` 推導。
- `dy_rel_As`: 相對 `As` 的 grid step 上限，預設 0.1%。
- `dy_abs_max`: 絕對 grid step 上限，預設 0.01 mV。
- `tap_abs_th_override`: 使用者強制指定 absolute tap threshold，單位 V；若為 `None`，由 `As` 推導。
- `tap_rel_As`: 忽略 pulse response 小 tap 的 threshold，預設 0.1% of `As`。
- `keep_mass`: PMF truncation 保留機率，預設 1.0。
- `gaussian_n_sigma`: Gaussian PMF 建構時的 sigma span。

固定 contract：

- Gaussian PMF 固定使用 `bin_integral`；`pdf_sample` 只保留在 `Pmf1D` 作為概念提醒與 debug 工具。
- Crosstalk phase 固定使用 spec 的 `max_variance` 規則，不開放成 config 選項。

### Runtime Config Boundary

`COMPMFRuntimeConfig` 是 `COMPMFConfig.resolve(As)` 的輸出，代表本次 run 已知 `As` 後的實際數值設定。

欄位：

- `dy`: resolved PMF amplitude grid step，單位 V。
- `tap_abs_th`: resolved absolute tap threshold，單位 V。
- `keep_mass`: 從 `COMPMFConfig` 帶入。
- `gaussian_n_sigma`: 從 `COMPMFConfig` 帶入。

PMF helper 只吃 `COMPMFRuntimeConfig`，不直接吃 `COMPMFConfig`。

### Status Boundary

`COMPMFStatus` 保存 93A.1.7 的中間 PMF 與 final metric：

- `dy`: 本次 run 實際使用的 PMF amplitude grid step。
- `tap_abs_th`: 本次 run 實際使用的 absolute tap threshold。
- `p_ISI`: ISI distribution。
- `p_G`: Gaussian noise distribution。
- `p_DD`: dual-Dirac jitter distribution。
- `p_XT`: combined crosstalk distribution。
- `p_combined`: final interference + noise distribution。
- `y0`: CDF inverse at `DER_0`。
- `A_ni`: `abs(y0)`。
- `COM`: final `20log10(As/A_ni)`。

### 下一步

PMF pipeline 下一個重點是確認 `p_sig` 的 symbol-level scaling 是否和 93A-39 / `As` 定義一致，避免 normalized level 與 voltage level 混用。

## Pmf1D

### Transform Contract

`Pmf1D` 的 public transform methods 採 immutable style，與 `LinkSegment` / `SparamModel` 的 cascade 風格一致。

以下 methods 都回傳新的 `Pmf1D`，不修改原本物件：

- `shift_x()`
- `scale_x()`
- `resample_dx()`
- `fir_filter()`
- `combine()`

因此 PMF pipeline 可以安全保存中間結果：

```python
p_combined = p_ISI.combine(p_G).combine(p_DD).combine(p_XT)
```

執行後 `p_ISI` 仍然代表純 ISI distribution，不會被改成 combined distribution。
