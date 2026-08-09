# 93A vs 178A COM 差異對照

這份文件用來快速對照目前 93A 實作與未來 178A 實作的主要差異。目標是輔助 code 架構拆分，不是完整 spec 筆記。

## Pipeline Step

| Pipeline step | 93A 目前做法 | 178A 需要修改的方向 | 影響程度 |
|---|---|---|---|
| `build_all_paths()` | 建立 victim / NEXT / FEXT path，使用 93A package + H21 + filters | channel / Tx S-param / Rx S-param model 都有新版定義；package、termination、partial host channel 都更複雜 | 高 |
| `find_pos_and_dfe()` | 先選 sampling phase，再用固定 DFE taps cancel post-cursor | 改成 receiver discrete-time equalizer，包含 FFE + feedback filter，用 MMSE / Wiener-Hopf 類方法求解 | 很高 |
| `impairment()` | 用 scalar RMS：`sigma_TX`, `sigma_ISI`, `sigma_J`, `sigma_XT`, `sigma_N` | 改成 PSD / autocorrelation domain；各 impairment 都用 PSD 加總，再進 MMSE equalizer | 很高 |
| `pmf()` | 用 93A PMF convolution：ISI, Gaussian, DD, XT | 仍保留 PMF 概念，但輸入改成 178A equalizer output 後的 residual ISI / crosstalk / DD / quantization / Gaussian noise | 中高 |

## Topic Detail

| Topic | 93A | 178A |
|---|---|---|
| Channel S-param | 讀 victim / xtalk S4P，轉 Sdd，接 package | 仍是 differential S-param，但有更明確的 Tx/Rx S-param model cascade |
| Tx package | 93A package model | 178A device termination + package + optional partial host channel |
| Rx package | 93A package model | 178A receiver S-param model：optional partial host + device package + device termination |
| H21 | 從 extended channel S-param 轉 voltage transfer function | 仍有 H21，但公式是 178A-3，reflection coefficient / termination 定義要對照 |
| H_txffe | 93A `c(-2)`, `c(-1)`, `c(1)` | 178A 一般化成 `c(n)`，且有係數 magnitude sum constraint |
| H_t | transition-time filter | 178A 直接 reference 93A input rise time filter，這部分可共用 |
| H_r | receiver noise filter | 178A reference 93A receiver noise filter，這部分可共用 |
| H_ctf | 93A Eq. 93A-22：`gDC`, `gDC2`, `fz`, `fLF`, `fp1`, `fp2` | 178A Eq. 178A-14：`g1`, `g2`, `fz1`, `fz2`, `fp1`, `fp2`, `fp3` |
| DFE | 固定 DFE taps + tap limit | Rx discrete-time equalizer：FFE + feedback filter，MMSE 求解 |
| Noise | RMS scalar | PSD on normalized frequency / autocorrelation |
| Jitter | slope-based RMS / PMF | PSD + slope / later PMF contribution |
| XT | sampled pulse variance + PMF | crosstalk PSD and later equalizer-output PMF |
| Quantization noise | 93A 沒有主要處理 | 178A 新增 quantization noise |
| COM optimization | maximize FOM | minimize MSE |
| Final COM | `20log10(As/Ani)` | 仍是 `20log10(As/Ani)`，但 `As` 和 `Ani` 來源不同 |

## Implementation Boundary

- 93A formula / procedure method 使用 `_93A` suffix。
- 178A formula / procedure method 使用 `_178A` suffix。
- 共用 container / utility 不加版本 suffix，例如 `COMConfig`, `COMStatus`, `COMReport`, `LinkSegment`, `SparamModel`, `Pmf1D`。
- 178A 初期先建立 skeleton interface，不應直接重用 93A method body 來假裝完成。
