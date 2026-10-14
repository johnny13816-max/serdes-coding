# TC-006 — 178A victim／XT scalar-VTF 高頻政策（歷史契約）

**已由 [TC-006 邊界修訂](tc006_out_of_measured_boundary_revision.md) 取代。** 下文 `high_frequency_policy`／`high_frequency_f_stop_Hz` 是當時的欄位，不是現行 API。

**狀態：2026-10-10 使用者明確要求執行；工作樹已實作、固定候選與完整回歸（102 passed、2 subtests passed）通過，提交隔離待處理。** 本案是一條與現行量測頻帶作法平行的 reference 比較政策，不主張 67 GHz 補零是 178A 唯一正確作法。受控數值見 [`../validation/mmse_input_akinwale_178A.md`](../validation/mmse_input_akinwale_178A.md)。

1. **原因**：SiCoPR 本案 `flim=67 GHz` 並 zero-pad；本專案保留 67–100 GHz 量測內容。相同 channel renormalization 及時間對齊後，NEXT 主導 `S_xn` 差。需要可配置的平行方法，讓後續 MMSE audit 固定同一高頻政策。
2. **依據**：本地 IEEE P802.3dj/D3.0 Annex 178A.1.3、178A.1.6 Eq. (178A-12) 的取樣／IFFT 邊界說明；SiCoPR Case1 `flim`、`ZERO_PAD` 及 `s21_to_impulse_DC` 實作為 reference 行為依據。178A 不強制所有 case 在 67 GHz 補零。
3. **現況**：`_build_path()` 先算 `S_tx → S_ch → S_rx`，`S_all.to_LinkSegment()` 用終端反射求 `H_21`，`LinkSegment.from_tf()`／`resample_tf()` 在量測頻帶內插值，超過量測上限才 phase 外推與 cosine taper。本案量測至 100 GHz，67–100 GHz 因而進入 victim 和 XT pulse。
4. **提案**：178A fixed-config 增加 `high_frequency_policy`（`measured_cosine`／`truncate_zero`；預設 `measured_cosine`）及 `high_frequency_f_stop_Hz`（可選；預設 `None`；`truncate_zero` 時必須為正且不高於 Nyquist）。runtime 建立 `S_all`、terminated scalar `H_21` 後，在其分析 grid 上將 `f>f_stop` 的複數值設為零，再照原流程計算 `H_all`／pulse；`f=f_stop` 保留。`measured_cosine` 完全沿用現行行為。所有 victim、NEXT、FEXT 套同一組政策；不裁切 S4P、`S_ch` 或 `S_all` 矩陣，也不在共用 utility 寫死 67 GHz。本案 reference profile 使用 `truncate_zero`、`67e9 Hz`。
5. **確切檔案／函式**：受保護核心僅 `src/serdes_coding/models/com_model_178A.py` 的 178A config 型別及 `_build_path()`；不修改 `com_model_93A.py`、`utilities/link.py` 或 `utilities/sparam.py`。映射另改 `src/serdes_coding/io/com_excel_io_178A.py` 的 `_project_excel_to_config_178A()`，增加 `cases/_templates/178A/config.xlsx` 及本案 `cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx` 的 fixed-config `policy` rows；更新 `docs/models/178A/config_tree.md`、本驗證文件與新增高頻分支測試。GUI 不改，僅使用既有 policy row 呈現。
6. **預期改變**：選 `truncate_zero` 時，`H_21` 的高頻分析 grid、`H_all`、victim／XT pulse、`h_dsamp`、`S_xn/S_tn/S_jn`、ADC PMF／`S_qn`、`R_n`、MSE、COM 可能變動；`S_rn` 不應變。高頻補零造成 pulse 時域變動，不再把所有殘差歸因於 renormalization。
7. **必須維持**：原始／renormalized `S_ch` 四參數、TX/RX package 四參數、`S_all` 四參數、終端公式及 `H_21` 截止以下值、所有既有 `measured_cosine` case 的輸出、93A、Ad Hoc intrinsic 映射、MMSE 方程。PMF 的 `keep_mass`／tap 門檻另由現有配置控制，不混入此核心修改。
8. **驗證與驗收**：固定 Akinwale locked candidate，使用相同暫存 S4P-first renormalization／相同時間對齊，`truncate_zero,67e9` 應重現主游標 `14.316792205 mV`、`S_xn` RMS `0.333390254 mV`、`S_tn` `0.399761987 mV`、`S_jn` `0.325549358 mV`；各 RMS 誤差限 `1e-6 mV`，主游標誤差限 `1e-6 mV`。`f>67 GHz` 的 scalar H21 嚴格為零；截止以下複數值、S 矩陣與原模式一致至浮點誤差。原模式固定 golden、config round-trip、single-run、search-run 與相關單測通過。對 SiCoPR 的殘差是診斷結果，不是強制追零的驗收門檻。
9. **版本／執行影響**：93A 無影響；178A single-run、search-sweep、search-final 均讀同一 fixed policy。預設模式維持舊值，僅本案選 reference profile 後改變。`pmf_keep_mass` 繼續屬於各 execution profile。
10. **回退邊界**：批准後先把核心行為與其直接測試隔離為專用提交，再以另一提交納入 parser、template、case 與文件；回退前者的專用提交即移除數學行為，後者撤銷配置入口。開始前記錄兩提交 SHA 與 parent；目前工作樹有大量既有未提交修改，不能以 `git reset` 或整檔還原作回退。

**範圍邊界**：上述 178A scalar-VTF 高頻平行分支與 fixed-config 接線。S4P-first renormalization 和 pulse 時間原點仍是獨立比較政策，不在本契約內。
