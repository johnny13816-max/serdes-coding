# TC-020 — 178A CTLE pulse realization 具名分支

狀態：**已核准、工作樹實作中；共用 CTLE 物件與 CTLE/unit-pulse 責任邊界已完成，raw impulse
準備／截尾／tail policy 尚未納入核准範圍。** 問題分類為
`G-009 / design diff`。本項保留 Eq. 178A-14 的 continuous-frequency CTLE，
另提供 COM MATLAB 4.17／SiCoPR 的 causal bilinear-IIR pulse realization。

## Goal:

新增 runtime 具名方法
`ctle_pulse_realization: Literal["continuous_tf", "bilinear_iir"]`。
一般模式預設 `continuous_tf`；project workbook 的 `align_to_ref=True` 由
`com_excel_io_178A` 展開為 `bilinear_iir`。runtime/model 不讀取 preset
boolean。

兩種方法共用同一個 Eq. 178A-14 `H_ctf`。`H_all` 與 VTF 報告永遠使用
continuous-frequency transfer；分支只決定 signal pulse 和無 TX FFE 的
TX-noise pulse 如何套用 CTLE。這是 reference 對齊方法，不宣稱現行
continuous 方法錯誤，也不建立 boxcar／時間原點分支。

## Allowed changes:

| 層級 | 檔案／位置 | 允許修改 |
| --- | --- | --- |
| project→runtime adapter | `src/serdes_coding/io/com_excel_io_178A.py::_resolve_project_profile_178A()` | reference preset 將 `ctle_pulse_realization` 覆蓋為 `bilinear_iir`，並逐項輸出 raw/effective/profile provenance。模板不新增細節欄位。 |
| protected runtime config | `src/serdes_coding/models/com_model_178A.py::COMConfig.policy` | 驗證 `continuous_tf/bilinear_iir` 具名欄位；直接 Python API 可獨立選擇。 |
| 178A filter math | 同檔 `IEEECOMFilter` | 新增 178A bilinear section coefficient builder 與 causal IR filtering method。不得把方法放進 generic `LinkSegment`。 |
| candidate status | 同檔 `COMBilinearCTLE`、178A `COMSharedPath.ctle_iir` | `COMBilinearCTLE` 直接保存兩段 `b/a` 係數與 `Fs`；每個 filter candidate 建立一次，由 victim/NEXT/FEXT/TX-noise 共用。不增加額外 status wrapper，也不在 root `COMStatus` 重複保存。 |
| CTLE realization orchestration | 同檔新增 `_realize_ctle_response()`；修改 `_build_path()`／`_build_paths()` 直接傳具名方法 | helper 只把已建立的 pre-CTLE response 轉成 post-CTLE response；`continuous_tf` 使用 `H_ctf`，`bilinear_iir` 使用兩段 causal IIR。TX FFE、channel/package、`H_r` 與 unit pulse 均在此責任邊界之外。`H_all` 仍使用 continuous `H_ctf`。 |
| common unit pulse | 同檔新增 `_apply_rectangular_unit_pulse()` | 對 post-CTLE response 套用同一個一 UI rectangular symbol pulse；frequency response 維持 frequency-domain cascade，causal-IIR response 維持 causal moving sum。domain 只保存數值表示法，不是另一個 project policy。 |
| TX noise | 同檔 `_build_psd_tx_noise()` 及呼叫點 | 先建立不含 TX FFE 的 pre-CTLE response，再使用同一 CTLE realization 與 unit-pulse helpers，確保 signal、XT、jitter 與 `h_tn/S_tn` 採相同 CTLE 方法。 |
| tests | 新增 `tests/test_com_model_178A_ctle_pulse.py`；更新 policy boundary test | 驗證係數、穩定性、time filtering、adapter 展開、三種 path、TX noise、固定 candidate 與一般模式不變。 |
| docs/status | `docs/models/178A/config_tree.md`、`stages/path_construction.md`、`stages/pre_dte.md`、`docs/planning/active_contracts.md`、`reference_alignment_contracts.md`、本檔 | 記錄 runtime method、`H_all`/`pulse` 語義、證據與結案狀態。 |

Bilinear section 明確採 MATLAB `TD_CTLE` 的獨立公式。令
`K=2*Fs`、`p_i=-2*pi*f_pi`、`z=-2*pi*f_z*10^(g/20)`，並以
`x_d=(K+x)/(K-x)` 映射 pole/zero。第一段使用
`(f_z1, f_p1, f_p2, g_1)` 的二階 section；第二段使用
`(f_z2, f_p3, g_2)` 的一階極限式，不用 `1e100` 假 pole。兩段以
causal `scipy.signal.lfilter` 依序處理，所有 pole 必須在 unit circle 內。

## Forbidden changes:

- 不修改 Eq. 178A-14 continuous `rx_equalizer()`、`H_ctf`、`H_all` 或 VTF。
- 不修改 S-parameter/package/channel、renormalization、out-of-measured、
  unit-pulse normalization、TX time origin、receiver-noise `S_rn` 或 MMSE solver。
- 不修改 generic `LinkSegment`／`SampledResponse`／PSD／PMF utility、93A、
  GUI、Ad Hoc mapping、workbook binary、case S4P 或 TC-013 grid contract。
- 不讓 `_build_path()`、`_build_psd_tx_noise()` 或 utilities 判斷
  `align_to_ref`；只接受 `ctle_pulse_realization` 具名值。
- 不用 frequency-domain circular product 假裝 causal IIR。bilinear branch
  必須以 causal time filtering 建 pulse，保留完整 fixed-grid 長度並通過既有
  causality/tail guard；容量不足沿用既有錯誤／警告契約，不靜默 wrap。
- 不把 SiCoPR 的 12 ps TX 座標差或 67 GHz case 輸入邊界寫進此分支。

## Top-level flow to preserve:

```text
project workbook align_to_ref
  → com_excel_io_178A expands named ctle_pulse_realization
  → COMConfig stores effective method; model never sees preset boolean

shared.H_ctf = continuous Eq. 178A-14
shared.ctle_iir = optional COMBilinearCTLE       # one per candidate
H_pre_ctle = H_ffe → H_t → H_21 → H_r           # TX FFE remains upstream
H_all = H_pre_ctle → shared.H_ctf                 # both methods; VTF/report

continuous_tf pulse:
  H_pre_ctle → continuous H_ctf
             → common unit-pulse application

bilinear_iir pulse:
  H_pre_ctle.ir/Fs causality-corrected normalized discrete kernel
           → bilinear section 1 → section 2
           → common unit-pulse application
           → same-LinkConfig pulse object

TX noise:
  H_t → H_21 → H_r → the same selected pulse realization
  → phase sampling → h_tn → Eq. 178A-19/20 S_tn
```

Victim、NEXT、FEXT 使用相同 realization。`h_dsamp`、XT、jitter、TX noise
及後續 MMSE/PMF 都從該 pulse 自然傳遞；`S_rn` 繼續使用 continuous
`H_r*H_ctf`。

TX FFE 不屬於 `ctle_pulse_realization` 分支。Victim/FEXT 使用既有
`shared.H_ffe`，NEXT 使用既有 unity `shared.H_ffe_next`；兩者都在形成
`H_pre_ctle` 時完成，CTLE selector 不建立、選擇或修改 TX FFE。

## Validation:

修改前在 `%TEMP%/serdes-tc020-20261012/` 備份 protected files 與本次
kernel-only patch；不使用 OneDrive。

1. **filter unit tests**：兩段 digital poles `abs(p)<1`；DC gain對應
   `10^((g_1+g_2)/20)`；第一段 Nyquist 為零；第二段一階極限式對
   MATLAB `f_p2→∞` 公式；causal output 對獨立 `scipy.signal.lfilter`
   oracle，`rtol=1e-13, atol=1e-15`。
2. **責任邊界**：`align_to_ref=True` 的 adapter effective method 為
   `bilinear_iir` 並有 provenance；False 為 `continuous_tf`。直接 Python
   具名設定得到相同 runtime 結果。model/helper/source 搜尋不得殘留
   `align_to_ref` 數值分支。
3. **path invariants**：兩方法的六條 `S_tx/S_ch/S_rx/S_all/H_21/H_all`
   逐元素相同；一般模式 pulse 對修改前逐點相同。bilinear pulse 對已擷取
   reference 主峰窗最大差 `<1e-9 mV`；三類 path 都檢查 peak、UI samples。
4. **pre-DTE components**：reference branch 逐項比較 `h_dsamp`、六路 XT、
   `h_tn/S_tn`、`h_J/S_jn`、`S_xn`、`S_qn` 與 `R_n`。`S_rn` 必須逐點
   不變。不得只用總 MSE 驗收。
5. **固定 Akinwale 67 GHz candidate**：目前正式 bilinear branch 的受控 A/B
   主游標 `14.317745659 mV`（SiCoPR `14.3177242 mV`），MSE
   `0.0061912775566626745`，相對 SiCoPR `0.0061912610245246705` 的殘差
   `+1.6532138004e-8`（`0.0002670%`）；驗收門檻主游標 `<5e-5 mV`、
   MSE `<5e-8`。normalized FFE 最大差 `2.77969e-5`，DFE 最大差
   `1.76191e-5`。
   67 GHz 與時間對齊只存在暫存驗證輸入，不寫入正式 branch。
6. **regression**：一般模式與 93A 不變；跑 targeted、完整 pytest，之後
   才做 single/search smoke。原始 100 GHz case 的既有 XT3 grid guard
   另案記錄，不把它誤判成 TC-020 算法失敗。

唯讀證據：相同 pre-CTLE complex `H` 對 reference 最大差 `8.51e-13`；
continuous pulse 主峰差 `-0.0006083 mV`，bilinear causal pulse `<8e-14 mV`；
同輸入 PMF/solver 已對到浮點精度。證據位於
`%TEMP%/serdes-pre-post-audit-20261012/`。

2026-10-12 責任邊界修訂將舊 `_build_ctle_pulse()` 拆成
`_realize_ctle_response()` 與 `_apply_rectangular_unit_pulse()`。前者只選擇
CTLE realization；後者只處理共用 symbol pulse。TX FFE 明確維持在
pre-CTLE 上游。拆分後 targeted `21 passed`，完整回歸 `126 passed,
2 subtests passed`；數值 invariant 由逐點 continuous cascade 與獨立 causal
IIR/moving-sum oracle 驗證。

2026-10-13 以相同 fixed candidate、reference preset 與完整線性 post-FFE
卷積重算，`COM_DFE=1.5247607834259893 dB`，與 SiCoPR 完整值相同到目前
保存精度；對發布截短值 `1.524760783 dB` 的差為 `4.26e-10 dB`。正式
`calculate_post_ffe_imp()` 仍因 XT3 固定 grid 溢出停止：`grid=10626`、
`full=10653`、tail peak ratio `0.00370678`（limit `0.002`）、tail energy
ratio `3.90894e-6`（limit `1e-6`）。因此這是受控 COM_DFE audit，不是正式
pipeline 已端到端通過。證據在 `%TEMP%/serdes-tc020-dfe-20261013/` 與
`%TEMP%/serdes-tc020-mmse-20261013/`。

## Open questions:

2026-10-13 核准 TC-020R2 後，`bilinear_iir` 已完成為單一具名方法：
measured composite pre-CTLE TF → reference frequency grid → raw IFFT（不做
causality correction）→ 固定 `1e-3` peak 截尾 → shared two-section IIR →
boxcar unit pulse。沒有新增 impulse-source、truncation-method、threshold 或
stop-frequency 控制項。post-FFE record 邊界另由
`rxffe_record_realization` 選 `linear_convolution` 或
`finite_record_circshift`；reference preset 選後者。

受控 67 GHz input 與已知 3Tr 時間原點下，victim pulse 對 SiCoPR 的 peak
差 `1.89e-13 mV`、主峰前 100 UI 至後 257 UI 最大差 `2.80e-13 mV`。
同一 project noise flow 的 MSE 為 `0.006191712423925738`，對 reference
`0.0061912610245246705` 差 `+4.51399e-7`；pulse 已到浮點精度，殘差不再
歸因於 CTLE pulse realization。

SiCoPR workbook 的 `flim=67 GHz` 輸入邊界已由
[TC-021](tc021_channel_frequency_limit.md) 在 channel ingestion 正式建模：
原始 100 GHz S4P 保留 provenance，case config 明示 67 GHz effective boundary，
其後 `out_of_measured="zero_padding"` 才從 67 GHz 以上補零。這個輸入欄位不屬於
CTLE method，也不由 `align_to_ref` 寫死。

既有 canonical 工作樹含其他未提交修改；無法安全建立專用 commit 時，
狀態維持「待隔離提交」，不得提交或還原其他修改。

2026-10-13 正式 `calculate_post_ffe_imp()` 已改由
`finite_record_circshift` 執行 victim、DDJ 與全部 5 條 XT，原先 XT3
固定 grid overflow 不再發生。相同受控輸入的正式結果為
`COM_DFE=1.5247607834259893 dB`、`MSE=0.006191712423925738`；後者相對
SiCoPR `0.0061912610245246705` 仍差 `+4.5139940107e-7`。由於同一次執行的
victim pulse 最大差只有 `2.80e-13 mV`，這筆 MSE 殘差歸入 noise／`R_n`
後續稽核，不再歸入 TC-020R2。targeted 測試 `27 passed`；完整回歸
`127 passed, 2 subtests passed`。
