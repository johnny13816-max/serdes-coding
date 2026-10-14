# TC-018 — 178A final quantization MATLAB 4.17 對照分支

狀態：使用者已核准；工作樹實作、固定候選驗證通過，待隔離提交。關聯 G-006。

## 目的與來源

所持 D3.0 Annex 178A 的 final quantization 以 selected-phase ADC-input
`V_qc`／`delta` 及 Eq. 178A-44 的全部 RX FFE tap 建立 PMF。公開
SiCoPR／MATLAB 4.17 在 final PDF 另用 `P_qc` 左尾決定 clipping，且
量化 PMF 略過 RX FFE 主 tap。兩者屬已確認的算法分支；reference 路徑
僅供校準，不能以數值接近宣稱它取代 D3.0 公式。

## 修改範圍與責任

| 層級 | 檔案／函式 | 行為 |
| --- | --- | --- |
| fixed policy | `src/serdes_coding/models/com_model_178A.py::COMConfig` | `final_adc_quantization_convention`，預設 `annex_d3` |
| workbook adapter | `src/serdes_coding/io/com_excel_io_178A.py` | 讀取同名 fixed-config 欄位 |
| converter registry | `src/serdes_coding/io/conversion/mapping_rules.py` | 分類為不從 Ad Hoc 映射的 policy |
| final COM 數值 owner | `src/serdes_coding/models/com_model_178A.py::_final_adc_clip_reference_only()`、`COM.calculate_COM_DFE()` | 組 reference clipping PMF，選 CDF 左尾，量化 PMF 略過主 tap |
| workbook | `cases/_templates/178A/config.xlsx`；`cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx` | 各增一個 policy row；模板為 D3，對照 case 為 reference-only |
| 測試／文件 | `tests/test_com_model_178A_policy_branches.py`、`tests/test_com_model_178A_post_ffe.py`、本契約、178A config/stage 文件 | policy 驗證與 final-stage invariant |

`COMConfig` 只選演算法；workbook adapter 只讀設定；數值操作留在
`calculate_COM_DFE()` 與其 module-level helper。`pre_dte_adc_clipping_convention`
是獨立旋鈕，不被 final policy 覆蓋。

## 資料流與不變量

- `annex_d3`：沿用 `calculate_post_ffe_imp()` 的 `delta`；uniform PMF
  對完整 `w_lim` 做 FIR（Eq. 178A-44）。這是預設與回退邊界。
- `matlab_4_17_reference_only`：pre-FFE victim `P_s` 加上除以主 tap gain
  的 post-FFE `P_ISI`、`P_XT`、`P_DD`、`P_G`；以 `CDF=P_qc` 求
  `V_qc`；由 `2V_qc/(2^N_qb-1)` 得 `delta`；uniform PMF 只通過
  非主 tap 的 RX FFE 係數。final PDF 的電壓 grid 屬 post-FFE domain；
  clipping 輸入的 grid／tap threshold 同時除以主 tap gain，避免
  正規化響應卻使用未正規化的 PMF 格點。uniform 誤差在 ADC input
  grid 上建立，各 tap 縮放後才投影到 final PDF grid，保留 ADC
  階梯解析度。
- `h_dsamp`、各 `R_n`、phase、FFE/DFE、MSE、post-FFE reporting PSD、
  ISI／XT／DDJ／Gaussian final PMF 及 93A 均不受此 policy 影響。
  178A single-run 與 search-final 共用同一 final DFE stage；
  `target=mse` 不執行此 stage。

## 驗證與回退

固定 `sicopr_akinwale_vendorx_22db` 的 67 GHz、pos 22、相同 FFE／DFE
與線性卷積中間量；reference 比較的 ADC-input grid 為
`5.374290304016261 µV`，final PDF grid 依主 tap gain 58.93988
換算為約 `316.7 µV`，完整 PMF 質量。這兩個數值分屬不同電壓 domain，
不能把前者直接套在未正規化的 final PDF 上。
先比 `V_qc`、`delta`、量化 PMF RMS、`A_ni`、COM_DFE，再比 SiCoPR
`COM_orig=1.524760783 dB`。D3 路徑應重現既有結果至 PMF bin 精度；
reference 分支的殘差需如實記錄，不能以 final COM 相消替代驗證。
另跑 policy／post-FFE 單元測試與原始 100 GHz single-run。

本次固定候選使用舊 67 GHz 比較邊界；正式 `force_grid=True` 對
XT3 的尾端會報 overflow，因此驗證沿用已記錄的完整線性卷積中間量，
而非把 overflow 悄悄截斷。相同 phase、FFE／DFE、non-QN PMF 與
output-domain grid 下，`annex_d3` `COM_DFE=1.107785639131481 dB`；
`matlab_4_17_reference_only` `COM_DFE=1.511853360897216 dB`；
SiCoPR `COM_orig=1.524760783 dB`，reference-only 殘差
`−0.012907422102785 dB`。reference-only 結果與先前獨立暫存
normalized-domain A/B 的 `1.511853360897217 dB` 差小於 `2e-15 dB`。
仍未達 SiCoPR 比對程式的 `1e-6 dB` EXACT 分類；此殘差不由 TC-018
量化分支單獨消除，不能宣告端到端對齊。D3 的 `1.10779 dB` 是這次
共同 output-domain grid 下的值；先前 normalized-domain A/B 的 D3
值因 input uniform PMF 的離散 grid 不同，不應直接相減。

回退精確邊界：移除此 policy、helper、`calculate_COM_DFE()` 的 reference
分支及上述 workbook row，保留既有 D3 路徑。當前 `com_model_178A.py`
已有其他尚未提交的模型修改，因此本契約須隔離 patch 後獨立提交；
不得以整檔或既有 index 建立混合 commit。
