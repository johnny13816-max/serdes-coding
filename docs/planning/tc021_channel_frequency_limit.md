# TC-021：Channel measured-frequency limit

狀態：2026-10-13 使用者核准；工作樹已實作，Akinwale 正式 single-run 與
完整回歸通過，待隔離提交。

## Goal

將 COM reference 的 `flim` 建模為可追溯的 channel input boundary，而不是
CTLE、`_build_path()` 或 `out_of_measured` 的隱藏截止頻率。

## Contract

- Project workbook 欄位為 `sparam_frequency_limit_GHz`；runtime
  `COMChannelConfig` 欄位為 `sparam_frequency_limit_Hz`。空白／`None` 保留
  完整量測記錄。
- `SparamModel.from_touchstone()`／`from_network()` 執行數值限制。若輸入頻帶
  到達 limit，保留第一個 `f >= limit` 的量測點並捨棄後續點；若檔案在 limit
  前結束，完整保留檔案。
- S4P-first 流程為 full single-ended S4P renormalization → measured-frequency
  limit → mixed-mode Sdd conversion。所有 victim、NEXT、FEXT 使用同一
  `COMChannelConfig` 值。
- `out_of_measured` 只決定有效量測邊界外的 scalar `H_21` 處理；
  `align_to_ref` 不寫死 67 GHz。
- Ad Hoc converter 將 `flim` 轉為明確 GHz 欄位。本 Akinwale case 的值為
  67 GHz；一般 178A template 留白。
- config export 的 measured-grid summary 記錄 `raw_f_max`、requested limit 與
  `effective_f_max`。

## Files

- `src/serdes_coding/utilities/sparam.py`
- `src/serdes_coding/models/com_model_93A.py`
- `src/serdes_coding/models/com_model_178A.py`
- `src/serdes_coding/io/com_excel_common.py`
- `src/serdes_coding/io/conversion/mapping_rules.py`
- `cases/_templates/178A/config.xlsx`
- `cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx`
- 對應 tests 與 178A path/config 文件

## Evidence

- 六個原始 S4P 均為 0–100 GHz、10 MHz 間距、10001 點。
- 正式 case 解析 `67e9 Hz` 後，六條 channel 均為 0–67 GHz、6701 點。
- 正式 `align_to_ref` single-run：profile=`sicopr_reference`、
  `rxffe_record_realization=finite_record_circshift`、selected pos=5、
  `ts=38149`、MSE=`0.006191712423925738`、
  `COM_DFE=1.5247607834259893 dB`。
- SiCoPR MSE `0.0061912610245246705`；殘差 `+4.5139940107e-7` 已確認不來自
  channel frequency boundary 或 victim pulse。
- Targeted regression：54 passed。完整 regression：128 passed、2 subtests passed。

## Remaining

既有 canonical 工作樹含其他未提交修改，專用 commit 待安全隔離。下一個
數值 debug 邊界回到 noise／`R_n` 殘差。
