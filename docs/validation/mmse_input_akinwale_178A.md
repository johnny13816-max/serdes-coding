# 178A Akinwale locked candidate：MMSE 輸入對照（2026-10-10）

## 2026-10-11 TC-017：pre-DTE clipping 對照分支

本節使用正式 `pre_dte_adc_clipping_convention=matlab_4_17_reference_only`，仍以同一 locked candidate、67 GHz 暫存 S-parameter measured boundary、已知時間原點對齊、`pmf_exact`、`dy=10 µV`、`keep_mass=1` 比較；**不代表原始 100 GHz case 的整體 COM 已對齊**。分支只改 pre-DTE clipping 的 random-jitter-only Gaussian sigma 與左尾 `P_qc`；`R_n` 的完整 jitter 項及 MMSE solver 不變。模板及舊 workbook 缺欄時仍用 `annex_d3`。

| 固定候選指標 | SiCoPR | 專案 Annex D3 分支 | 專案 MATLAB 4.17 對照分支 |
| --- | ---: | ---: | ---: |
| `V_qc` (mV) | 41.62 | 41.94 | 41.61 |
| `P_n` standard deviation (mV) | 0.648880 | 0.711125 | 0.648785 |
| quantization RMS (mV) | 0.381417749 | 0.384350322 | 0.381326106 |
| total `R_n[0]` 差 (V²) | 基準 | +2.074129e-9 | −2.414418e-10 |
| MSE | 0.006191261025 | 0.006206638174 | 0.006192538895 |
| MSE 差 | 基準 | +1.537715e-5 | +1.277871e-6 |
| normalized FFE 最大 tap 差 | 基準 | 1.232657e-4 | 2.688959e-4 |
| DFE 最大 tap 差 | 基準 | 1.093990e-4 | 1.197153e-5 |

reference-only 分支的主游標差仍為 `−0.000932026 mV`，前 100 至後 256 UI 視窗最大差 `0.001848009 mV`。`R_n[0]` 剩餘分量差：receiver `0`、XT `−9.166430e-11`、TX `−3.005633e-11`、完整 jitter `−4.982114e-11`、quantization `−6.990006e-11 V²`；總差為 `−2.414418e-10 V²`。這些小殘差不能稱為完全對齊，但本固定候選 MSE 差低於 TC-017 的 `5e-6` stage gate。FFE 最大差沒有隨 MSE 單調減少，因此進入下一 stage 時仍保留完整向量對照。

原始數值與受控腳本存放在 `%TEMP%/serdes-tc017-20261011/` 的 `fixed_67_s4p_first.py`、`fixed_67_s4p_first.json`、`pmf_input_compare.json`、`mmse_input_compare.json`、`mmse_solution_compare.json`；Annex D3 重算在其 `annex_d3/` 子目錄。這是固定比較邊界，未將 67 GHz 直接寫入正式 case workbook。

原始 100 GHz 正式 single-run（`target=mse`）選 `pos=23`、`ts=163991`，MSE `0.006196571745350858`、`V_qc=41.60 mV`、FFE 87 tap。其數值記於同一 TEMP 目錄 `single_run_result.json`；不可直接與上表的 67 GHz locked candidate 比值解讀。完整回歸為 `111 passed, 2 subtests passed`。

閱讀順序：下列 67 GHz scalar-VTF 分支與數值是歷史受控比較。現行 `out_of_measured` 接口以**原始輸入最高量測頻率**為邊界；本案原始 S4P 到 100 GHz。兩組數值不可混當同一 baseline。現行實作見 [TC-006 修訂](../planning/tc006_out_of_measured_boundary_revision.md)。

2026-10-11：TC-016 已將 S4P-first renormalization 升格為 178A 正式選項。本案 workbook 選此方法；以正式 reader 配合暫存 67 GHz 輸入與比較用時間對齊，重現下文舊 oracle 的 `h_dsamp`、`R_n` 與 MSE，最大差均為 0。原始 100 GHz case 仍須與 67 GHz 比較條件分開。詳細記錄見 [TC-016](../planning/tc016_channel_renormalization_order.md)。
正式 branch 對 SiCoPR locked solver input 的新比較數據存於 `%TEMP%/serdes-tc016-20261011/mmse_input_compare.json`：主游標差 `−0.000932026 mV`，總 `R_n[0]` 差 `+2.074129e-9 V²`，其中量化項差 `+2.245671e-9 V²`；固定相位 MSE 差 `+1.537715e-5`。此組數值與下文舊受控比較完全重現，並非改變 solver 方程。

現行實作的原始 100 GHz S4P 固定候選，`cosine_decay`／`zero_padding` 分別得到主游標 `14.249846053839374`／`14.24984605403704 mV`，MSE `0.006216109903225285`／`0.0062161098672533195`；zero mode 六條 `H_21` 在 100 GHz 以上均嚴格為零。此測試未使用下文的暫存 S4P-first renormalization 與時間平移，因此數字不能和歷史 67 GHz oracle 直接相減。完整數據在 `%TEMP%/serdes-out-of-measured-20261010/fixed_candidate.json`。

## 比較邊界與候選

- 來源：`reference_data/COM_adhoc_config/sicopr/` 的 Case1 workbook、同一組六條 S4P。SiCoPR 原始碼的 `MMSE()` 入口擷取 `sbr`、六項 `S_n` 分量與解；重跑最終 COM `2.895898684873259 dB`，與 locked MAT 相同。擷取候選 `cursor_i=38149`（0-based）、FOM `12.094255868167913 dB`、87 個 RX FFE tap 與 MAT 逐點完全相同。
- 專案：固定 TX FFE `[0,0,1,0]`、CTLE `g_1=-20 dB`、`g_2=-2 dB`、同一六條 S4P；只在暫存比較中使用 SiCoPR 的 S4P-first channel renormalization。將已知的 TX transition `3T_r` 與 boxcar 中心延遲合計 `16.5588235294 ps` 加在暫存 path 副本，令主游標同為 pulse peak 前 6 samples。專案為 `pos=22`、`ts=163990`；未改核心模型。
- 比較的是 **pre-RXFFE** 的 MMSE 入口。SiCoPR 的 symbol-rate DFT 為 4096 點，專案 sampled grid 為 10626 點；各 `R_n` 分量以各自 PSD 做 `f_b × IFFT`，比較 lag 0–86（覆蓋本案 87-tap RX FFE）。單位 V²。

## 結論

離散通道包含振幅 **近似但不完全對齊**；主游標 SiCoPR `14.317724231 mV`、專案 `14.316191682 mV`，差 `−0.001532550 mV`（`−0.010704%`）。共同原始波形支援的 3424 個 UI，最大絕對差 `0.002133206 mV`，相對主游標 `0.01490%`；主游標前 100 至後 256 UI 的最大差 `0.001579636 mV`。SiCoPR 將此向量補零到 4096 UI，專案在對應尾部仍有非零值：最大 `0.009327656 mV`（主游標的 `0.06515%`）。因此不能稱整個 solver `h` 向量精確相等。

`R_n` **未對齊**。總 lag-0 變異數 SiCoPR `6.513502486e-7 V²`、專案 `6.489211155e-7 V²`，差 `−2.429133116e-9 V²`；等效 RMS `0.807062729` 對 `0.805556401 mV`。各來源 lag 0–86 最大絕對差如下；本案各最大值均在 lag 0。

| 來源 | SiCoPR RMS (mV) | 專案 RMS (mV) | 專案−SiCoPR (mV) | ΔR[0] (V²) |
| --- | ---: | ---: | ---: | ---: |
| receiver `S_rn` | 0.358828811 | 0.358828811 | 0 | 0 |
| crosstalk `S_xn` | 0.333527698 | 0.335753963 | +0.002226265 | +1.489998388e-9 |
| TX noise `S_tn` | 0.399799578 | 0.399767564 | −0.000032014 | −2.559725198e-11 |
| jitter `S_jn` | 0.325625867 | 0.325512260 | −0.000113608 | −7.397432927e-11 |
| ADC quantization `S_qn` | 0.381417749 | 0.376377390 | −0.005040359 | −3.819559923e-9 |
| input noise `S_in` | 0 | 0 | 0 | 0 |
| **total** | **0.807062729** | **0.805556401** | **−0.001506328** | **−2.429133116e-9** |

`R_n` 差值可由上述六項相加重建；receiver 完全相同，主要相反方向的貢獻來自 ADC quantization 和 crosstalk。量化分歧在 ADC clipping 幅度已存在：SiCoPR `41.62 mV`、專案 `41.07 mV`。SiCoPR `get_PSDs()` 使用 `P_qc` CDF 門檻；專案 `_calculate_V_qc()` 使用 `P_qc/2` 並經 PMF 投影／截尾。此處只證明不同，不以數值接近度判定哪一個公式正確；既有 ADC PMF 收斂問題需按獨立錯誤項處理。

五條 crosstalk 的 lag-0 差值分解如下（專案−SiCoPR）：

| 路徑 | SiCoPR RMS (mV) | 專案 RMS (mV) | ΔR[0] (V²) |
| --- | ---: | ---: | ---: |
| FEXT1 | 0.067089711 | 0.067202727 | +1.517720e-11 |
| FEXT2 | 0.040565725 | 0.040419082 | −1.187585e-11 |
| FEXT3 | 0.046032830 | 0.046009460 | −2.151038e-12 |
| NEXT1 | 0.073110448 | 0.074827532 | +2.540220e-10 |
| NEXT2 | 0.312457932 | 0.314427711 | +1.234826e-9 |

NEXT2 佔 crosstalk `ΔR[0]` 的大部分。兩邊已知使用不同的高頻與 waveform 截窗政策；此表定位來源，**不宣稱已證明唯一根因**。下一個必要判斷是以相同高頻／截窗政策重算 NEXT2 與 ADC PMF 門檻，將 policy 差與真正的公式錯誤分開。

## 錯誤與平行作法的歸類

**已證實的專案數值錯誤（E-004／TC-005 草案）**：pre-DTE `pmf_exact` 要求 `P_qc=1e-7` 的尾部機率，卻用 `tap_abs_th=0.316667 mV` 跳過小 tap，並在每次 PMF 卷積只保留 `0.99999` 質量。同一個本次 time-aligned 專案 `h_dsamp` 與 `sigma_ga`，僅將 tap 門檻收緊至 `dy=0.01 mV`、保留質量改為 1，`V_qc` 即由 `41.07` 變成 `41.94 mV`；其餘 spec 公式與輸入不變。這證明目前 `S_qn` 有自身數值精度問題。相應 RMS 控制值約 `0.384350 mV`，甚至高於 SiCoPR 的 `0.381418 mV`，故不能把「向 reference 靠近」當作修正標準。核心修正須依已列出的 TC-005 獨立批准。

**平行／reference policy 差異**：SiCoPR Slow clipping 用 `CDF=P_qc` 與 random-only jitter，專案按所持 D3.0 Eq. 178A-27 至 29 用 `CDF=P_qc/2` 與完整 `S_jn`。這兩項不能為了追齊 SiCoPR 而當作專案錯誤修改。SiCoPR 本案 `flim=67 GHz` 後 zero-pad，專案保留至 100 GHz 量測並使用既有延伸；先前受控 A/B 已把這個差異定位為 NEXT1／NEXT2 waveform 的主要來源。SiCoPR 的離散 MMSE PSD／SBR 使用 4096-UI 視窗，專案使用 10626-UI sampled grid；此差異也使完整 solver 向量尾部不相同。SiCoPR 的 boxcar pulse 與 3T_r 延遲、專案的連續 sinc pulse 與現行時間原點，則以比較用時間對齊處理，剩下的振幅差仍需保留在證據中。

**未判定為新錯誤**：TX noise 與 jitter 各有小幅殘差；相同 source-fed jitter waveform 已能重現 SiCoPR PSD，現有資料沒有證明這兩項的公式錯誤。Receiver noise 完全對齊，無待修正項。

暫存擷取與逐項數據：`%TEMP%/serdes-mmse-input-audit-20261010/` 的 `candidate_4.npz`、`project_time_aligned.npz`、`comparison.json`、`xt_paths.json`。這些是本機驗證產物；正式模型與 GUI 未修改。

## 2026-10-10 追加：PMF 精度與 67 GHz 高頻分支控制

本節是同一 locked candidate 的暫存 A/B；未修改模型、正式 case workbook 或 GUI。SiCoPR 使用原始 Case1 設定。專案仍使用暫存 S4P-first renormalization 與上述時間對齊；所有 victim/NEXT/FEXT path 在 terminated `H_21` 轉成 pulse 前，才於 67 GHz 以上補零。`S_ch`、`S_all` 的四個 S 參數仍保留量測值。暫存腳本和完整數值在 `%TEMP%/serdes-mmse-input-audit-20261010/` 的 `capture_project_67zero_precise.py`、`keep_mass_sweep.json`、`comparison_67zero_precise.json`。

### ADC PMF 兩個獨立控制量

以原本相同的離散通道、`dy=0.01 mV` 和 Gaussian noise 固定輸入，只改 `keep_mass`：當 `tap_abs_th=0.316667 mV`（project 預設）時，`keep_mass=0.99999` 得 `V_qc=41.07 mV`，改成 `1.0` 只到 `41.09 mV`。因此 **單靠 `keep_mass` 無法消除本地 PMF 截尾差**。當 `tap_abs_th=0.01 mV` 時，`keep_mass=0.9999999/0.99999999/0.999999999/0.9999999999/1.0` 分別得 `41.59/41.83/41.92/41.94/41.94 mV`。套用 67 GHz 補零後，再核對 `0.999999999/0.9999999999/1.0` 分別得到 `41.91/41.94/41.94 mV`。本 case 若以一個 PMF bin（0.01 mV）為收斂準則，最小實測 `keep_mass=0.9999999999`；跨 case 的保守精度設定為 `1.0`。`tap_rel_As` 是 fixed-config policy；本 case 在 `As=0.316667 V` 下要使門檻為 `0.01 mV`，可設為約 `3.1579e-5`。`pmf_keep_mass` 是 run-config execution policy；兩者在暫存物件上設定，尚未寫回 workbook。

### 67 GHz 後補零且精細 PMF 的 MMSE 入口

同一 candidate 下，`h_dsamp` 主游標 SiCoPR `14.317724231 mV`、專案 `14.316792205 mV`，差 `−0.000932026 mV`（`−0.006510%`）；主游標前 100 至後 256 UI 的最大／RMS 波形差為 `0.001848009/0.000158875 mV`。離散視窗尾部仍屬獨立比較政策，未用來解釋目前主要差異。

| `R_n` 來源 | SiCoPR RMS (mV) | 專案 RMS (mV) | ΔR[0] (V²) |
| --- | ---: | ---: | ---: |
| receiver `S_rn` | 0.358828811 | 0.358828811 | 0 |
| crosstalk `S_xn` | 0.333527698 | 0.333390254 | −9.166430e-11 |
| TX noise `S_tn` | 0.399799578 | 0.399761987 | −3.005633e-11 |
| jitter `S_jn` | 0.325625867 | 0.325549358 | −4.982114e-11 |
| ADC quantization `S_qn` | 0.381417749 | 0.384350322 | +2.245671e-9 |
| input noise `S_in` | 0 | 0 | 0 |
| **total** | **0.807062729** | **0.808346694** | **+2.074129e-9** |

各列 `ΔR[0]` 也是其 lag 0–86 的最大絕對差。`S_xn` 的 RMS gap 從原本 `+0.002226265 mV` 變為 `−0.000137445 mV`，確認 67 GHz 分支消去主要 XT gap。精細 PMF 讓 `V_qc=41.94 mV`，但 SiCoPR 是 `41.62 mV`，兩邊的 clipping tail/jitter 方法仍不同；不得把 `S_qn` 殘差當作高頻分支錯誤或以數值接近度反推 spec 正確性。

若只將高頻設為 67 GHz 補零、`keep_mass=1.0` 而保持 project 預設 `tap_abs_th=0.316667 mV`，則 `V_qc=41.09 mV`、`S_qn` RMS `0.376560676 mV`、total RMS `0.804672076 mV`。這個並列值清楚分離了高頻與 PMF tap 精度兩個控制量。

### dy 收斂與 MMSE source-fed 控制

同一 67 GHz 暫存 branch、`tap_abs_th=dy`、`keep_mass=1` 下，`dy=20/10/5/2.5 µV` 得到 `V_qc=41.940/41.940/41.945/41.945 mV`。因此 10 µV 已在一個 bin 內收斂；再縮小 `dy` 不會趨近 SiCoPR 的 `41.62 mV`。專案的同一 PMF 若暫時改用 `CDF=P_qc`，則 `V_qc=41.75 mV`，仍與 SiCoPR 差 0.13 mV；SiCoPR 的 input PDF／noise composition 也不同。不可用刻意粗化 `dy` 讓單一數值碰巧一致來當作算法對齊。

SiCoPR 原始 `h_dsamp`、完整 `R_n` 直接送進專案 `COM_MMSE_DTE.run()`，其 `MSE=0.006191261024524053`，與 SiCoPR `sigma_e²=0.006191261024524671` 差 `6.18e-16`；正規化後 87 個 FFE tap 最大差 `3.68e-13`，DFE 相同至輸出精度。因此 MMSE 求解器在相同輸入下對齊。其餘受控情況（同一選定 phase、`spec-defined` floating 模式）如下；FFE 以主 tap 正規化後比較 SiCoPR `C`：

| 求解輸入 | MSE | 相對 SiCoPR MSE 差 | DFE | FFE 最大絕對差 |
| --- | ---: | ---: | ---: | ---: |
| SiCoPR h + SiCoPR R（source-fed） | 0.006191261025 | ≈0 | 0.84201083 | 3.68e-13 |
| 專案 h + 專案 R（67 GHz、精細 PMF） | 0.006206638174 | +1.537715e-5 | 0.84190143 | 1.232657e-4 |
| 專案 h + 專案其他 R + SiCoPR quantization R | 0.006192964536 | +1.703511e-6 | 0.84199591 | 2.644918e-4 |
| 專案 h + SiCoPR 完整 R | 0.006193900642 | +2.639617e-6 | 0.84202356 | 2.986852e-4 |
| SiCoPR h + 專案其他 R + SiCoPR quantization R | 0.006190325296 | −9.357288e-7 | 0.84198316 | 4.498617e-5 |

只替換 quantization R 已將 MSE 差從約 0.248% 降至約 0.0275%。剩下的 channel／其他 R 差在本案 debug 排序可暫時降低優先度，但不能稱為完全相同或從結案證據中刪去。上述只是 solver input substitution；未改正式核心或 workbook。

## 2026-10-10 正式分支落地與固定候選複核

上節為實作前的暫存 A/B 紀錄；**本節的 67 GHz 正式分支描述也已成歷史**，由 TC-006 measured-boundary 修訂取代。當時 runtime 在 terminated scalar `H_21` 分析 grid 上將 `f>67 GHz` 設為零，且同一設定套用 victim、NEXT、FEXT。`S_ch` 和 `S_all` 保留完整四參數。`pmf_dy_override=1e-5 V` 仍接至單跑與 search profile，直接取代 PMF dy 推導；本案 workbook 另設 `pmf_keep_mass=1` 與約 10 µV 的 tap 門檻。未啟用 override 時仍使用舊 dy 推導。

固定 candidate 重算使用正式高頻／dy 設定，僅 S4P-first renormalization 與時間原點對齊保留為暫存比較控制。所得 `h_dsamp` 主游標 `14.31679220487629 mV`、MSE `0.006206638173753554`、`V_qc=41.94 mV`；相對先前全暫存 oracle，`h` 最大差 `1.29e-18 V`，各 `R_n` 來源最大差不超過 `1.06e-22 V²`，`w_lim` 最大差 `7.3e-12`，`b_lim` 最大差 `8.4e-14`。這證實正式政策接線重現既有受控結果。尚餘的主要 MMSE 殘差為量化項的 tail／noise 定義差；`dy=10 µV` 已收斂，不能再藉縮小 dy 消除 `V_qc` 的 `0.32 mV` 差。S4P-first 比較控制仍屬獨立分支，不能把本次固定候選數字誤述為純正式 config 的 reference 對齊。

## 2026-10-10 補充：`V_qc` 上游 `P_s`／`P_n` 隔離

同一 locked candidate，取已擷取的 SiCoPR `sbr`、`cursor_i`、五項 PSD RMS 與 random-jitter PSD，在只讀 SiCoPR `get_PSDs()` 的 `Slow` clipping 程式路徑重建 `P_s`、`P_n`；`PDF bin size=10 µV` 由原始 workbook 確認。重建得到 `V_qc=41.62 mV`，與原始 SiCoPR 擷取值完全一致。專案用正式 67 GHz／dy policy、相同暫存 S4P-first 與時間對齊比較。

| PMF／來源 | SiCoPR | 專案實際輸入 | 相同 source input 下的專案 PMF |
| --- | ---: | ---: | ---: |
| `P_s` 標準差 (mV) | 14.101427 | 14.098123 | 14.099474（注入 SiCoPR sampled `h`） |
| `P_n` Gaussian `sigma` (mV) | 0.648880 | 0.711125 | 0.648880（注入 SiCoPR `sigma`） |
| `P_s` L1 mass 差 | 基準 | 2.3350e-4 | 1.3689e-4 |
| `P_n` L1 mass 差 | 基準 | 8.8604e-2 | 9.5780e-6 |

SiCoPR `P_n` 的 Gaussian `sigma` 用 receiver、XT、TX、input 與 **random jitter** PSD RMS 合成；本專案 pre-DTE `_calculate_V_qc()` 前的 `S_ga` 用 `S_rn+S_xn+S_tn+S_jn`，其中 `S_jn` 同時含 **Dual-Dirac 與 random jitter**。本案專案 total jitter RMS `0.325549 mV`，其 random-only 部分 `0.145590 mV`；只用 random-only 重算 Gaussian `sigma` 為 `0.648778 mV`，接近 SiCoPR `0.648880 mV`。SiCoPR 在 `P_s.x` 上取樣 Gaussian PDF 乘 `dy`，專案以 bin-integrated Gaussian 建 PMF；注入相同 `sigma` 時，兩者 `P_n` 的 L1 差僅 `9.5780e-6`，且 `V_qc` 量化到 10 µV 時相同。未據此判定兩種 jitter domain 哪個符合 178A；需對照 spec 後才可更動核心。

交叉代入得到的 `V_qc`（mV）：

| `P_s` | `P_n` | `CDF=P_qc=1e-7` | `CDF=P_qc/2=5e-8` |
| --- | --- | ---: | ---: |
| SiCoPR | SiCoPR | 41.62 | 41.80 |
| 專案實際 | SiCoPR | 41.61 | 41.79 |
| SiCoPR | 專案實際 | 41.76 | 41.95 |
| 專案實際 | 專案實際 | 41.75 | 41.94 |

因此 0.32 mV 總差**不是只有 tail rule**：實際 `P_s` 對本候選約 `−0.01 mV`；較寬的 `P_n` 在相同 `P_qc` 下約 `+0.14 mV`；將門檻從 `P_qc` 改為 `P_qc/2` 再增加約 `0.19 mV`（以專案雙 PMF 為準）。重建腳本、PMF 陣列與逐格比較在 `%TEMP%/serdes-mmse-input-audit-20261010/` 的 `derive_ref_ps_pn_from_locked_input.py`、`compare_ps_pn_locked.py`、`ps_pn_comparison.json`。這些是只讀稽核資料，未修改核心模型。
