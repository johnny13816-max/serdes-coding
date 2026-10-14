# TC-006 修訂 — measured boundary 外插政策與 utility 責任邊界

狀態：已核准並在工作樹實作；回歸與獨立提交狀態見 [active_contracts](active_contracts.md)。本修訂取代[原 67 GHz scalar-VTF cutoff 契約](tc006_channel_high_frequency_policy.md)，保留原文作歷史紀錄。

## 目的與可觀察行為

178A fixed-config 僅有 `out_of_measured: Literal["cosine_decay", "zero_padding"]`，預設 `cosine_decay`。`zero_padding` 在輸入的最高量測頻率**以上**將 terminated scalar `H_21` 設為零；最高量測點與頻帶內複數值不變。兩種方法由同一 utility 提供，COM 對 victim、NEXT、FEXT 傳入同一選擇。原始 S4P、S_ch、TX/RX package 和 S_all 的四個 S 參數不變。

## 責任層級與呼叫鏈

| 層級 | 位置 | 責任 |
| --- | --- | --- |
| project config／workbook | `COMConfig.policy.out_of_measured`、`com_excel_io_178A.py`、178A template | 選擇與驗證政策；conversion registry 保留 project-owned 值 |
| COM path orchestration | `com_model_178A.py::_build_paths()`／`_build_path()` | 將同一選擇傳到每條路徑，組合 S_all；不修改已產生的 scalar response |
| S-parameter → link boundary | `sparam.py::SparamModel.to_LinkSegment()` | 從 terminated two-port 取得 measured-grid `H_21`，交由 link utility 轉 grid |
| numerical resampling | `link.py::LinkSegment.from_tf()`／`resample_tf()` | 在 analysis grid 執行 cosine decay 或 measured-frequency 後的 complex zero padding |

不得再在 `_build_path()` 對已轉好的 `H_21` 使用固定 cutoff 做事後補零。這項政策屬量測資料外的延伸方法，並非 IEEE 178A 的通用 67 GHz 截止公式。

## 驗證邊界

SiCoPR 本案以 `flim=67 GHz` 處理，而本案原始六條 S4P 的最高量測頻率是 **100 GHz**。因此在原始 S4P 上選 `zero_padding` 是 100 GHz 後補零，不能直接拿歷史 67 GHz 的主游標、R_n、MSE 作新政策的 golden。若要重現 SiCoPR 的 67 GHz 比較，須用有來源紀錄的暫存 67 GHz 截取輸入，再走同一 `to_LinkSegment()` 轉換；不得悄悄裁切正式原始 S4P。

已在 `%TEMP%` 做 67 GHz 截取輸入的等價性驗證：六條 channel 各取 `f<=67 GHz` 的 Sdd 複本（保留原 z0），再重新建立 package／S_all，使用 `zero_padding` 轉 grid。與「原始 100 GHz S_all 的 H21 在 `f>67 GHz` 事後補零」對照：六條路徑在 67 GHz 以下的 S_all 最大複數差、整個 analysis grid 的 H21 最大複數差、截取輸入在 67 GHz 以上的 H21 最大幅度，均為 **0**。腳本與 JSON 位於 `%TEMP%/serdes-out-of-measured-20261010/cropped_67_equivalence.*`。這僅證明頻率處理等價；未重新擷取 SiCoPR solver 輸入與 COM。

分層驗收：兩政策下 S_ch／S_all 四個 S 參數一致；measured 內 H21 一致；`zero_padding` 的 measured 以上 bins 嚴格為零；既有 cosine 預設與先前輸出一致。固定 case 以原始 100 GHz S4P、pos=22、ts=163990 做六條 path／MMSE 比較：cosine 與 zero 的主游標各為 `14.249846053839374`／`14.24984605403704 mV`，MSE 各為 `0.006216109903225285`／`0.0062161098672533195`。`S_xn` RMS 各為 `0.336085144934`／`0.336085133608 mV`；zero mode 六條 path 的 100 GHz 以上 H21 最大絕對值均為 0。上述差異很小，因測試只改 100 GHz 以上。完整回歸：`103 passed, 2 subtests passed`。驗證資料在 `%TEMP%/serdes-out-of-measured-20261010/fixed_candidate.json`；未做 SiCoPR 67 GHz 截取輸入重新對齊。回退邊界為同一暫存目錄的修改前 patch／檔案快照；因既有工作樹混有其他未提交變更，獨立 commit 須待安全隔離後建立。
