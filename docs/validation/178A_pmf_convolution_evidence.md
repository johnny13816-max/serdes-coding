# 178A PMF 卷積方法驗證

NUM-007 使用 `cfg.num.pmf_convolution_method` 選擇 `fft` 或 `linear`。
Project 預設及 93A 未指定參數時為 `fft`；`sicopr_reference_v1` 為 `linear`。
兩個 L5 operation owners 是 `Pmf1D.fir_filter()` 和 `Pmf1D.combine()`；
shared helper 只執行選定卷積。Projection、grid、keep mass 與 tap threshold 不變。

## 驗證結果

- `.venv` Python 3.14、NumPy 2.5.3、SciPy 1.18.1；focused PMF、178A policy
  與 MLSD tests：78 passed、2 subtests passed；另含微小機率尾端的 PMF tests
  27 passed。
- 固定案例 `sicopr_akinwale_vendorx_22db`、`all_enabled`、phase 5：明確選
  `fft` 的既有 golden 通過，MSE `0.006191300963670364`、DFE COM
  `1.5247607834259893 dB`、final COM `2.895898684873246 dB`。
- 同一案例 reference profile `linear` 完整 run 95.30 s：phase 5、MSE
  `0.006191300963670364`、DFE COM `1.5247607834260184 dB`、final COM
  `2.895898684873275 dB`。公開 SiCoPR 對照為 `2.8958986848732575 dB`；
  兩種方法的 final COM 差異均在浮點精度等級，不宣稱 linear 的此數值明顯更接近。
- 直接呼叫 SiCoPR Python 1.2.1 `_conv1d`，使用三組共同 dense、含兩側零、
  sparse 輸入，正常化後與本專案 `linear` 的最大絕對差皆為 0。此為有限輸入
  的 operation-level evidence，不代表所有 PMF 或完整 COM 全面對齊。
- 合成 Gaussian PMF 自身卷積的低機率 CDF 測試，在 `2e-4`、`1e-9`、
  `1e-12`、`1e-15` 四個門檻，SiCoPR direct bins 分別為 1199、921、804、702；
  本專案 linear 相同，FFT 分別為 1199、921、804、699。這是合成資料，
  不是原 fixed case 最終 PMF 的重跑。

原 reference case 的 XT PSD window 仍採專案設計，這是獨立差異。極低機率
CDF 與其他 case 的更廣泛對照不由上述單一案例證明。
