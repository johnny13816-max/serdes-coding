# Reference 驗證待結案 Contracts

本檔追蹤問題的方案與驗收，不是目前模型行為的權威說明。
每次發現問題，記錄方案、範圍、待決策與 close 條件；未批准不修改核心。

## Debug 回報格式

每個 stage 先說明「要做什麼」，依序列出目前專案的算法與實作位置、
reference 的算法與 case 設定、spec 的強制要求或允許選項、建議方案
（含預設值是否改變）、受控驗證及待決策。數值 gap 放在算法與方案之後，
避免把 reference 差異直接稱為 spec defect。

## 對齊問題分類與處理規則（2026-10-08 起）

每個新 gap 必須有編號、第一個不同的 stage、共同輸入／設定、分類、
處理方案、驗收與狀態。尚無足夠證據時標為「待分類」，不得因 final COM
不同就推定公式錯誤；也不得只報數值而不留下可結案的處置。

1. **設計／實作有誤**：違反適用 spec、已批准模型 contract、物理不變量，
   或固定輸入下的數值收斂要求。發現後立即準備可執行的修正與驗收。
   一般非核心修正直接實作；若涉及 `AGENTS.md` 保護的模型 kernel，
   必須先提交該項具體 Core Model Change Contract，取得明確批准後立即
   以獨立 commit 修正並逐 stage 驗證。不得以「繼續 debug」代替批准。
2. **Design diff**：兩種算法均可能符合 spec，或 SiCoPR 為特定 case
   選了不同 policy。先固定相同輸入，將各個 policy 旋鈕分開做 A/B，
   同時記錄 spec 依據、物理／數值理由、跨 case 敏感度與效能。優先
   決定一個專案 canonical default；僅在兩種做法各有明確用途且單一
   預設不能滿足時，保留明確命名的選用 policy／reference profile。
   不因單一 SiCoPR 數值較近就改預設，也不無故增加 GUI 選項。
3. **比較條件差異**：候選、設定、單位、相位或輸出邊界不同。先修正
   比較方法，重跑同邊界；不是模型修正。
4. 主狀態與結案關卡以 [`../architecture/reference_change_workflow.md`](../architecture/reference_change_workflow.md)
   為準；當前狀態只在 [`active_contracts.md`](active_contracts.md) 更新。
   關閉時必須附 stage 證據、測試及適用的獨立 commit。

### 已確認的設計／實作有誤

| ID | 問題 | 處理與狀態 |
| --- | --- | --- |
| E-001 | termination gamma 未由 `R_0/R_d_tx/R_d_rx` 一致推導 | 已修正，commit `c8809b5`，已結案 |
| E-002 | RX package die-to-channel two-port 未交換到 channel-facing orientation | 已修正，commit `b437341`，已結案 |
| E-003 | measured Sdd 只改 impedance metadata，沒有依 Eq. 178A-4 renormalize | 已修正，commit `68af9b8`，已結案；與 SiCoPR 的四埠做法差異另見 G-001 |
| E-004 | pre-DTE `pmf_exact` 的 tap／mass pruning 對 `P_qc=1e-7` 尾端不收斂 | TC-005 完整草案待該項批准；不等同於 SiCoPR 的 ADC 公式差異 |
| E-005 | 178A Ad Hoc 的 RX FFE precursor／fixed postcursor／floating 範圍轉換少算 tap | TC-007 已完成本地修正與 runtime 驗證；source-fed SiCoPR MMSE golden 仍待可重現輸入 |
| E-006 | MLSD Eq. 178A-54 的 `S_ni` 應從 Eq. 178A-15 的 pre-FFE `S_n` 經 RX FFE 建立；原本只取 post-FFE `S_rn` | TC-009 已核准並在工作樹實作，Eq. 178A-54 不變量與固定候選驗證通過；待獨立提交 |
| E-007 | MLSD Eq. 178A-47 的 COM 增量分母原本錯用 `A_ni`，應為 `A_s`，導致 DFE COM 被重複計入 | TC-011 已核准並在工作樹實作；固定候選公式不變量驗證通過，待獨立提交 |
| E-008 | MLSD Eq. 178A-54 的 `S_isi` 原本以雙邊 PSD 值直接建成要求 one-sided equivalent 的 `SampledPSD`，內部頻點少一倍 | TC-009 已核准並在工作樹實作；固定候選 `sigma_isi` 從 33.790771 mV 修正為 47.759096 mV；待獨立提交 |
| E-009 | MLSD Eq. 178A-52 對 `p_an` 的第一項縮放應為 `+b_lim(1)`，原本為 `scale_x(-b_lim_1)` | TC-012 已核准並在工作樹實作；非對稱 PMF 專項與固定候選驗證通過，待獨立提交 |

### 已確認的 design diff

| ID | 算法邊界 | 處理與狀態 |
| --- | --- | --- |
| G-001 | Sdd 二埠 renormalization vs SiCoPR 四埠 single-ended 先 renormalize | 使用者核准的 [TC-016](tc016_channel_renormalization_order.md) 已在工作樹實作；舊個別 policy 可讀，新模板由 `align_to_ref` 統一選擇。六路徑正式 S_ch 對舊 reference-only reader 差 0，後者對 SiCoPR dump 最大複數差 `2.78e-15`；仍待隔離提交。 |
| G-002 | 100 GHz 量測＋cosine 延伸 vs SiCoPR `flim=67 GHz`＋zero-pad | [TC-021](tc021_channel_frequency_limit.md) 已把 `flim` 正式映射為 optional case-level measured-frequency limit；[TC-006](tc006_out_of_measured_boundary_revision.md) 保留具名 boundary-extension policy。Akinwale case 明示 67 GHz＋zero-pad；一般模板留白且不由 `align_to_ref` 寫死。 |
| G-003 | TX transition 時間 delay／連續 sinc pulse vs SiCoPR 的時間位移／M 點離散累加 | 已確認 boxcar／sinc 對應同一 `X(f)H(f)` 脈衝操作；純時間原點在比較座標中處理，不建立平行算法分支。 |
| G-004 | ADC `P_qc/2`＋完整 jitter vs SiCoPR `P_qc`＋random jitter | [TC-017](tc017_pre_dte_adc_clipping_reference.md) 已核准並於 pre-DTE 建立 reference-only 分支；所持 D3.0 仍為預設。固定 67 GHz 比較的 MSE 差降至 `1.277871e-6`；final COM ADC PMF 不在 TC-017 範圍，完整端到端驗證未結案 |
| G-005 | sampled PSD/相關長度約 10626 UI vs SiCoPR `num_ui_RXFF_noise=4096` | [TC-022／TC-022A](tc022_mmse_noise_grid.md) 已核准並在工作樹實作。`COMConfig.policy` 的 `noise_grid_method/noise_grid_num_ui` 保留一般 analysis grid 與 fixed-UI 分支；`noise_grid_num_ui` 為 optional project policy，新模板空值、reference preset 預設 4096。正式 Akinwale total `R_n[0:87]` 最大差 `3.71e-21 V²`，MSE 差 `8.63e-16`。 |
| G-006 | 178A Eq. 178A-44 對所有 RX FFE tap 加入 ADC quantization PMF；SiCoPR final PDF 跳過主 tap | [TC-018](tc018_final_adc_quantization_reference.md) 已獲核准並在工作樹建立獨立 final policy；D3 保持預設，reference-only 固定候選驗證中 |
| G-007 | Eq. 178A-50/51 應追加 receiver Gaussian noise 重建 `p_an`；SiCoPR `scaleCDF` 直接縮放完整 PDF | TC-008：本地依 draft 重建 PMF，SiCoPR 實作差異先留在 reference 對齊診斷，不改本地預設；定量 A/B 待做 |
| G-008 | 離散 tap PMF 最近格點、Gaussian grid sampling、ADC uniform 最近端點及 `scalePDF` ordinate interpolation vs 專案各自的既有數值方法 | [TC-019](tc019_align_to_ref_profile.md) 已核准；以單一 `align_to_ref` profile 選擇、保留既有一般模式。相同輸入的 Gaussian／quantization PMF 已逐格核對至浮點精度；固定 67 GHz 暫存 phase 22 的 COM 對到 `4.3e-10 dB`，但 `As`／`A_ni` 各有微小差異、原始 case 端到端受既有 fixed-grid guard 阻擋。 |
| G-009 | CTLE 後 pulse／TX-noise：專案以連續 `H_ctf(f)` 相乘，SiCoPR 對 impulse 使用 bilinear 離散 CTLE；reference VTF 仍用連續 CTLE | [TC-020R2](tc020_ctle_pulse_realization.md) 已核准並實作。`bilinear_iir` 已包含 measured TF、reference grid、raw IFFT、停用 causality correction、`1e-3` 截尾、兩級 IIR 與 unit pulse；post-FFE finite-record shift-sum 為獨立具名 method。67 GHz victim pulse 最大差 `2.80e-13 mV`；該輸入邊界已由 TC-021 正式建模。 |

TC-003 的搜尋最佳候選與本地 single-run 不同屬比較條件差異。
任何新 gap 先加入本表或獨立臨時 contract，不能只留在口頭結論。

### 待分類的實作邊界

| ID | 第一個不同的 stage | 暫存處置 |
| --- | --- | --- |
| T-001 | 固定 phase=23 的 pre-DTE clipping `V_qc=40.95 mV`，post-FFE final-PMF 路徑重新算得 `40.44 mV`；相應 `S_qn` 不同 | 稽核 Eq. 178A-26 至 29 在 pre／post 兩條路徑的 PMF/PSD 定義，與 E-004 的數值收斂及 G-004 的 reference policy 分開；不以 post `S_total` 代替 Eq. 178A-15 的 pre `S_n`，分類／修正另立契約 |
| T-003 | DER Eq. 178A-48 是無窮和，本地固定截在 `trunc_len`（本案 128） | TC-009 後固定 phase=23 候選的 65–128 項總和僅 `2.05e-18`、第 128 項 `1.24e-30`，此案 128 項已數值收斂；跨 case 與 128→更大上限仍待驗，超過驗收才提出數值策略契約 |

## CR-001：spec-defined channel renormalization

- 狀態：已結案（2026-10-07）；獨立 commit 見 Git history。
- 原因：S4P ingestion 只指定目標 impedance metadata，沒有轉換 measured Sdd。
- 方案／依據：178A.1.3／Eq. 178A-4，先取 measured Sdd，再二埠 renormalize。
- 範圍：`utilities/sparam.py::from_network()` S4P 分支、相關 docstring、
  `tests/test_channel_renormalization.py` 與中文 contract 文件。
- 可能改變：S_ch 與下游 H21、pulse、phase、MSE、COM；93A／178A single/search 共用。
- 不變：Sdd/array constructors、來源 Network、package、gamma、filters、GUI、workbook。
- close：專用測試、相關 regression、固定 case 公式與 VTF 驗收通过；獨立 commit。
- 驗收與 rollback：[channel contract](../validation/channel_renormalization.md)。
- 驗證：專用及 termination/orientation 測試 25 passed；非 GUI suite
  初跑 58 passed／1 個預期 MSE 基準變動。修改前 ingestion 控制重跑通過；
  更新 golden MSE 後該 post-FFE 測試檔 4 passed，原失敗已結案。
- SiCoPR 固定 single run：pos=19、MSE=0.007175987507961828、
  COM_DFE=0.5762414804798679 dB。下游 reference 等價驗證仍是下一個小目標。

## 下一個小目標：pulse 邊界驗證

- 狀態：待進行診斷；尚未確認需修改核心。
- 檢查：complex filters、frequency cutoff/extension、IFFT、time origin、pulse normalization。
- 輸出：第一個需要修改的具體問題與獨立 Core Model Change Contract。
- 不預先授權 filter、FFT 或 MMSE 修改。

## TC-002：pulse 前處理邊界（待確認、未批准修改）

- 狀態：暫存 Contract；未判定為 spec defect，不更動核心。
- 已確認差異：SiCoPR TX transition 含 3Tr 線性 delay；以 M 點離散累加形成 pulse；
  發布 CSV 的 fstop/flim 為 67 GHz。自家採連續 sinc、未加該 delay、使用 100 GHz channel。
- 建議方案：先在外部 audit 對齊時間原點及 sampled grid，比較完整 waveform 與 MMSE 輸入；
  若需正式改 frequency/pulse policy，先核對 spec 並提出精確 files/functions 合約。
- 驗證：相同 reference-channel 輸入，未加 CTLE pulse peak：reference-style 100 GHz
  60.090371 mV，67 GHz 60.088592 mV，自家 policy 60.086127 mV；
  發布 reference 60.090042 mV。此為控制試算，不是完整 SiCoPR engine run。
- CTLE：0–67 GHz 最大複數差 5.56e-16；Nyquist 的差異為 real-edge constraint。
- close 條件：對齊 common input 與 time origin 後，提供完整 pulse、sampled response、
  MSE 敏感度結果；確認無需修改後記錄理由，或另提批准的核心修改與驗收。
- 目前不授權：LinkSegment、FFT、filter、GUI、workbook 修改。
- 下一小目標：sampled pulse／noise autocorrelation／MMSE input；時間原點差異仍待釐清。

## TC-003：SiCoPR 最佳候選與本地 single-run 條件對齊

- 狀態：已發現的比較條件問題；先做唯讀 candidate reconstruction。
- 證據：發布 SiCoPR CSV 的 `itick=-6`、TXLE taps `[0,0,1,0]`、
  `g_DC=-20 dB`、`g_DC_HP=-2 dB`、RX FFE 的非零係數向量、COM 2.895899 dB。
  本地剛才執行的是 config workbook 的固定 single-run profile，pos=19、
  MSE=0.007175988、COM_DFE=0.576241 dB；該呼叫不等於 SiCoPR 完成搜尋後的最佳候選。
- 方案：先解讀 `itick` 相對取樣相位定義，將 reference 的 TXLE、CTLE、RX FFE
  及相位映射到本地明確候選。CSV 的 `RxFFE` 是正規化且列印精度有限的輸出，
  無法單獨重建完整 MMSE 解。於固定版本 SiCoPR 的獨立暫存副本擷取最佳候選的
  `sbr`、`cursor_i`、`PSD_results.S_n`、`h`、`Rn`、`H`、`Rnn`、原始 `w`、
  `sigma_e`、`FOM`、`C` 與 DFE 限制/結果；對同一候選逐項比本地 MMSE 輸入、
  矩陣、解、MSE、COM。搜尋只負責選候選；輸入與限制一致時，MMSE 解與誤差
  也應一致，不能以 single-run 與搜尋的名稱解釋數值差距。
- 驗收：候選設定映射逐欄有來源；固定候選輸入一致後，找到第一個數值分歧 stage，
  並提供輸入／輸出證據。
- 未授權：不得為了吻合 CSV 修改模型方程、search 策略、workbook 或 GUI；
  若映射揭露真實核心 defect，另提精確 Change Contract。

## TC-004：MMSE 前 impairment 大小與 ADC clipping 比較邊界

- 狀態：暫存驗證 Contract；尚未判定模型 defect，未批准核心修改。
- 本地固定 case、pos=19：pre-DTE RMS（mV）為 receiver 0.358829、
  crosstalk 0.336085、TX 0.399457、jitter 0.327836、quantization 0.377569；
  total 0.807039。`R_n[0]` 與各項 variance 總和均為 6.5131156347e-7 V²。
- 已核實 reference 有效設定：`4p16p0`、`Clip Method=Slow`、`PSDRXCAL=false`、
  6-bit ADC、`P_qc=1e-7`、`S_tn_w_AM=0`。Fast clipping 疑慮已排除。
  公開 CSV 的 post-FFE noise 數值不可直接當作 MMSE 前 PSD/RMS。
- 固定 SiCoPR 公開最佳候選（TXLE `[0,0,1,0]`、`g_DC=-20`、`g_DC_HP=-2`、
  `itick=-6`）重跑得到 FOM 12.094255868167913 dB、COM 2.895898684873259 dB，
  與發布值一致。MMSE 前 reference RMS（mV）：receiver 0.358829、crosstalk
  0.333528、TX 0.399800、jitter 0.325626、quantization 0.381418、total 0.807063；
  `S_in=0`。各項 variance 和、`S_n` 積分及 `R_n[0]` 均為 6.51350248646e-7 V²。
- 將 reference `sbr` 與本地 victim pulse 相關對齊，取得本地相位 23；此相位的本地
  RMS（mV）：receiver 0.358829、crosstalk 0.336085、TX 0.399798、jitter
  0.325274、quantization 0.375278、total 0.805100。相對 reference 的差異
  分別為 0%、+0.767%、-0.00035%、-0.108%、-1.610%、-0.243%。本地
  `V_qc=40.95 mV`，由 reference `S_qn` 反算為 41.62 mV；本地/參考
  sampled PSD 長度分別為 10626/4096 UI。兩邊 waveform 尚有約 0.97% L2 差。
- 控制試算：僅將本地六條 channel 換成 SiCoPR 四埠預處理結果時，crosstalk RMS
  由 0.336085 降為 0.335654 mV，仍高於 reference 0.333528 mV；故 channel
  renormalization 不是此差距的唯一來源。把本地 crosstalk waveform 限在 reference
  4096-UI 視窗，RMS 只由 0.336085 降為 0.336062 mV，單靠視窗長度也無法解釋。
- 公式分離結果：把五條 SiCoPR `h_xn^(k)` 逐條送進本地 PSD 公式，五項 RMS
  均與 reference 到浮點精度相同；本地 jitter 公式吃同一 reference `sbr`
  時也重現 0.325625867410 mV。剩餘 crosstalk 差異來自 path waveform 輸入，
  主要是 NEXT2（reference 0.312458、本地 0.314804 mV）及 NEXT1
  （0.073110、0.074689 mV），不是已測的 PSD 公式。
- ADC 公式分離：reference `Slow` 以 `CDF=P_qc`、Gaussian 僅用 random jitter；
  本地以 `CDF=P_qc/2`、Gaussian 用完整 jitter。所持 D3.0 draft
  Annex 178A.1.7.6、Eq. 178A-27 至 29 明定 `P_sn(-V_qc)=P_qc/2` 且
  `sigma_ga` 納入 `S_jn`；因此這兩項應保留本地 spec 公式，不為了吻合
  SiCoPR 改成 reference 公式。
- 本地確有獨立數值精度問題：`pmf_exact` 在此 case 使用 tap 門檻
  0.3167 mV、每次卷積保留質量 0.99999，卻求 1e-7 clipping tail；
  同一 SiCoPR pulse 上，本地預設 PMF 用 reference 的 random-only Gaussian
  得 `V_qc=40.87 mV`，把門檻降至 0.01 mV、保留質量設為 1 並暫以
  reference 的 `CDF=P_qc` 查表時得 41.61 mV，reference 是 41.62 mV。
  保留 spec 的 `P_qc/2` 與完整 jitter 時，同一 pulse 的精度控制值為
  41.95 mV；本地實際 pulse 的控制值為 41.93 mV（目前 40.95 mV）。
- 敏感度：只把本地 pos=23 的 quantization RMS 改成 reference 0.381418 mV，
  MMSE MSE 由 0.00763326145 變為 0.00766021937；故 ADC 差異是真實問題，
  但不足以單獨解釋主要 MMSE 落差。
- 下一步：依 TC-005 處理本地 PMF tail 精度；另在外部 audit 對齊 NEXT
  path waveform、reference 原點及 `R_n` 所需 lags，定位剩餘 MMSE 落差。
- close 條件：逐項確認單位、積分/RMS、加總及矩陣一致；若是配置或 reference
  policy 差異，記錄比較方案；若是專案的 spec defect，另提 Core Model Change Contract。

## TC-005：pre-DTE ADC PMF tail 精度（Core Model Change Contract 草案；未批准）

1. 原因：`pmf_exact` 的 tap/mass pruning 對 `P_qc=1e-7` 的尾端機率過粗，
   固定 case 的 `V_qc` 對數值政策敏感約 0.98 mV。
2. 依據：本地 IEEE P802.3dj/D3.0 Annex 178A.1.7.6、Eq. 178A-27 至 29
   與 93A.1.7.1；SiCoPR/Ad Hoc `get_PSDs` 僅作數值比較，不覆蓋 spec 定義。
3. 現況：`calculate_pre_dte_imp_at_pos` 將完整 `S_jn` 加入 `sigma_ga`，
   `_calculate_V_qc` 用 `P_qc/2` 查 PMF；但 `pmf_cfg.tap_abs_th=0.3167 mV`、
   `keep_mass=0.99999` 讓 `_build_pmf_interference_93A` 每步裁切訊號 PMF。
4. 提案：只在 178A pre-DTE `pmf_exact` 的訊號 PMF 計算，改用
   `tap_abs_th=min(pmf_cfg.tap_abs_th, pmf_cfg.dy)` 與 `keep_mass=1`；
   保留 spec 的 `P_qc/2`、完整 `S_jn` 與原量化 PSD 公式。外部控制已用
   10/5/2.5 µV grid 與相同 tap 門檻收斂，`V_qc` 均為 41.95 mV
   （SiCoPR pulse、spec tail/完整 jitter）；不以 reference 的 41.62 mV
   作 spec 驗收值。
5. 預計僅改 `src/serdes_coding/models/com_model_178A.py` 的
   `_calculate_V_qc()` PMF 建構政策；若收斂試驗不通過，修訂本 contract
   再討論，不擴大修改 `utilities/pmf.py` 或 GUI。
6. 預期改變：pre-DTE `p_s/p_sn`、`V_qc`、`delta`、`S_qn`、`S_total`、
   `R_n`、MMSE tap/MSE，及其下游結果。
7. 保持：`h_dsamp`、`S_rn/S_xn/S_tn/S_jn`、`sigma_ga`、`P_qc/2`、
   93A、post-FFE PMF、channel/package/GUI/workbook 行為。
8. 驗證：固定 case pos=23，在目前 `dy=10 µV` 下控制試算
   `V_qc≈41.93 mV`（容許一個 bin）；將 dy/tap 門檻再減半時確認
   `V_qc` 收斂於 0.05 mV 內，並核對 `delta²/12`、各 PSD/RMS、
   `R_n[0]`、MMSE MSE；再跑相關單測與固定 single-run。
9. 影響：93A 不變；178A single-run 與 search-final 若選 `pmf_exact`
   才受影響；預設 `gaussian_approx` search-sweep 不變，需量測耗時。
10. 回退：若獲批准，單獨提交核心改動；回退邊界為該提交的 parent
    （目前 HEAD `68af9b8`，不包含既有未提交修改）。

## TC-006：NEXT 頻率上限與 pulse 延伸（暫存診斷 Contract；未批准）

- 原因：固定候選的 NEXT1／NEXT2 crosstalk RMS，本地為 0.074689／
  0.314804 mV，SiCoPR 為 0.073110／0.312458 mV；逐路相同 waveform
  輸入的 PSD 公式已對齊，因此追查 pulse 上游。
- 已隔離的邊界：SiCoPR 的 `sdd21` 頻率軸止於 67 GHz，該 case 設定
  `ZERO_PAD=true`、`zero_pad_tukey_window_in_fb=0`，故 67 GHz 以上
  在 `s21_to_impulse_DC` 的 FFT 輸入歸零。本地 `resample_tf()` 在來源
  上限後以 25% 頻寬 taper，實際 path 並使用到 100 GHz 的量測資料。
  對相同的 SiCoPR `sdd21`，67 GHz 以下複數頻譜相同至約 1e-15 以下；
  本地延伸區的頻譜能量占 NEXT1／NEXT2 全頻能量 21.52%／4.72%。
- 受控因果試算：相同 `sdd21` 走兩種延伸政策，未等化 impulse 的相對
  L2 差為 NEXT1 52.37%、NEXT2 22.26%；SiCoPR 政策重建其擷取
  `uneq_imp_response` 至浮點精度。只在外部試算把本地 path pulse
  的 67 GHz 以上設零，NEXT1／NEXT2 RMS 變成 0.072970／0.312661 mV，
  總 crosstalk 由 0.336085 變成 0.333697 mV，接近 SiCoPR 的
  0.333528 mV。剩餘 0.000170 mV 仍須逐路查，不宣稱完全對齊。
- 目前算法：S4P 經 Sdd／renormalize 與 package cascade 後，
  `S_all.to_LinkSegment()` 才把 terminated `H_21` 送入
  `LinkSegment.from_tf()`；`resample_tf()` 在量測頻帶內對 magnitude
  和 unwrapped phase 線性插值，超出最後一點後以末端 10% 資料
  的 phase 斜率延伸，magnitude 以 cosine taper 在最後頻率的
  125% 歸零。此 case 的量測／本地 cascade 到 100 GHz，故
  67–100 GHz 的量測內容仍參與 pulse。
- spec 核對：本地 P802.3dj/D3.0 Annex 178A.1.3 建議均勻頻率步進、
  起點不高於 10 MHz、終點至少 67 GHz；178A.1.6 Eq. 178A-12
  附註指出 IFFT 可能需向 DC 和 Nyquist 延伸，延伸方法應慎選以限制
  COM 誤差。沒有「67 GHz 以上必須補零」的強制規則。67 GHz 是
  此 SiCoPR workbook 的 `flim` 設定，不是通用上限。
- 具體方案候選：新增 178A pulse／scalar-VTF 轉換邊界的可選
  `f_stop` 與 `high_frequency_policy`（現有 cosine taper、直接
  zero-pad），讓 reference profile 使用 `f_stop=67 GHz`、zero-pad；
  先保持現有預設值，不直接刪除 67–100 GHz 的實測 S-parameter。
  此方案需獨立 Core Model Change Contract 批准後才能實作；
  不在共用 `LinkSegment` 寫死 67 GHz，也不把 reference policy
  宣稱為唯一正確的 spec 算法。
- 待驗證：檢查 67–100 GHz 量測品質，並比較兩種 policy 對 victim、
  FEXT、NEXT、TX／jitter、`R_n`、MSE、COM 的影響，再決定專案預設
  policy 是否有物理或數值理由改變。
- 兩旋鈕受控 A/B（只在 `%TEMP%` 建構 alternative pulse，未修改核心；
  相同本地 S_all/H21 與其餘 filters，單位 mV）：

  | `f_stop` | 截止後 policy | NEXT1 | NEXT2 | XT total |
  | --- | --- | ---: | ---: | ---: |
  | 100 GHz | cosine（現行） | 0.074689 | 0.314804 | 0.336085 |
  | 100 GHz | zero-pad | 0.074689 | 0.314804 | 0.336085 |
  | 67 GHz | cosine | 0.075748 | 0.314112 | 0.335723 |
  | 67 GHz | zero-pad | 0.072970 | 0.312661 | 0.333697 |

  SiCoPR XT total 為 0.333528 mV。僅在 100 GHz 改 zero-pad 幾乎無效；
  67 GHz 與直接補零兩個條件都要指定，不能把此 gap 歸因於單一
  `resample_tf()` taper 公式。此 A/B 尚未證明應更改專案預設。
- close：完成受控 A/B 與 spec-first 決策；若須改核心，先取得獨立
  contract 批准。此項尚未授權核心、GUI 或 workbook 變更。

## TC-007：178A RX FFE tap-layout 映射（Core Model Change Contract；本地修正與驗證完成）

1. **原因**：Ad Hoc 的 `ffe_pre_tap_len=6`、`ffe_post_tap_len=8`、`N_f=80`
   目前被轉成 `d_w=5`、`N_fix=12`、`N_max=86`，使 RX FFE 主 tap、固定
   postcursor、floating 搜尋範圍與 SiCoPR／178A 定義不一致。這是第一個
   已定位、可重現的重大 MMSE gap；屬 E-005 設定映射錯誤，不是改選
   SiCoPR policy。
2. **依據**：本地 IEEE P802.3dj/D3.0 Annex 178A.1.8.1、Table 178A-10
   與 Eq. 178A-30/31：`d_w` 是 precursor 數，固定 postcursor 數是
   `N_fix-d_w-1`，最後可選 floating postcursor 位置是
   `N_max-d_w-1`。參考 Ad Hoc workbook 的三個源值，以及 SiCoPR
   實際 MMSE 設定 `RxFFE_cmx=6`、`RxFFE_cpx=8`、`N_bmax=80`，共同
   支持目標 `d_w=6`、`N_fix=15`、`N_max=87`。
3. **目前方程／資料流**：`io/conversion/mapping_rules.py::rules_for('178A')`
   採 `d_w=pre-1`、`N_fix=pre+post-2`、`N_max=pre+N_f`；寫入 178A
   case workbook 後由 `com_excel_io_178A.py` 讀入 `COMDTEConfig`。
   `COM_MMSE_DTE` 本身把 `d_w` 作 precursor 數、`N_fix` 作固定 tap
   數、`N_max` 作 FFE 向量長度與 exclusive index bound。兩側語義不同。
4. **提案方程／資料流**：僅在 178A Ad Hoc 轉換邊界改成
   `d_w=pre`、`N_fix=pre+1+post`；有 floating group (`N_bg>0`) 時
   `N_max=pre+N_f+1`，沒有 floating group (`N_bg=0`) 時依
   178A.1.8.1 設 `N_max=N_fix`。確認來源值為整數且轉換後
   `N_max>=N_fix`。用修正後的映射重產本 SiCoPR
   case 的三個欄位，保留 workbook 其餘欄位與 channel references。
   不改 MMSE 求解式或 `COMDTEConfig` 的現有索引語義。
5. **限定檔案／函數**：`src/serdes_coding/io/conversion/mapping_rules.py`
   的 `rules_for('178A')` 這三條規則；
   `cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx` 的上述三個
   `fixed_config` 值與對應 conversion audit；`tests/test_mapping_contract.py`
   新增映射不變量與固定 case 驗證；同步修正
   `docs/architecture/adhoc_mapping_fields.md`、`docs/models/178A/config_tree.md`
   的三條數學契約。這些來源與 workbook 目前是既有 untracked 工作，
   修改前先逐檔備份到專用 `%TEMP%`，提交時只納入本 contract 所核准
   的差異；若無法隔離既有內容，不把整份既有 untracked 工作混入 commit。
6. **預期改變**：轉換輸出的 `d_w/N_fix/N_max`、FFE bound arrays、
   main/fixed/floating tap indices、`w_lim`、`b_lim`、MSE，及下游
   post-DTE impairment／COM；搜尋候選排序亦可能變動。
7. **必須不變**：Ad Hoc 原始 workbook、93A 映射、178A TX FFE、
   S-parameter/package/channel/cascade、victim 與 aggressor pulse、
   pre-DTE PSD 與 `R_n`、MMSE 方程及其他 case workbook。
8. **驗收**：映射單測確認本案 `6/8/80` 且 `N_bg=2` 時為
   `6/15/87`，`N_fix-d_w-1=8`、`N_max-d_w-1=80`；另驗
   `N_bg=0` 時 `N_max=N_fix`；以相同 SiCoPR `sbr[5::32]`
   與 `ifft(S_n)×f_b` 作固定 MMSE A/B，目標 MSE
   `0.0061912610245246705`，絕對誤差 `<=1e-12`，`b_lim≈0.84201083`
   （容差 `1e-7`），`N_max=87`；再跑映射／runtime 相關測試與
   固定 single-run，逐 stage 記錄改變項。不以 final COM 對齊作本
   映射修正的唯一驗收。
9. **影響範圍**：93A 不變；178A 新轉換的 single-run 與 search-run
   都使用新 layout；既有 case workbook 不自動批次改寫，僅明確列出
   需重轉的案例，本 contract 只重產上述 SiCoPR case。
10. **回退邊界**：當前 HEAD `68af9b8` 加上修改前逐檔 `%TEMP%`
    備份及差異記錄；若批准實作，模型行為修正獨立提交，不納入其他
    未提交修改。若 untracked 來源無法乾淨隔離，先保留補丁與驗證，
    不提交混合內容，回報具體版本控制障礙。

2026-10-09 已獲核准並完成。converter 已依本 contract 改為 tap-count mapping；
指定 SiCoPR workbook 與 conversion audit 分別只更新 `d_w/N_fix/N_max` 三個
欄位／三筆記錄為 `6/15/87`，其餘 workbook cell 不變。固定 `target="mse"`
runtime 驗證得到 selected phase `24`、MSE `0.006170581277695888`、
`b_lim[0]=0.84196873`、`len(w_lim)=87`；`test_mapping_contract.py` 與
`test_channel_renormalization.py` 共 23 項通過。由於本地沒有可重現的 SiCoPR
`sbr` 與 `S_n` 陣列，驗收第 8 點的 source-fed golden 尚不能執行；它保留為
reference evidence 的待辦，不改變本 contract 已完成的 mapping 修正。既有
conversion stack 是 untracked 工作，尚不能安全建立只含 TC-007 的 commit。

### TC-007 固定候選端到端唯讀 A/B（2026-10-08）

相同 canonical case／TX FFE／CTLE／channel、現行 100 GHz pulse 與
178A `single_run` 設定；只在記憶體中將 `d_w/N_fix/N_max` 從
`5/12/86` 改為 `6/15/87`。共用同一組 `build_all_paths` 與 phase-independent
pre-DTE cache，兩邊各掃描 32 個 phase，之後執行 post-FFE PMF、DFE COM
及 MLSD。沒有更改任何 workbook 或 model。

| 量 | 現況 | FFE 修正試算 | 差異 |
| --- | ---: | ---: | ---: |
| 選定 phase（0-based） | 19 | 23 | +4 samples |
| MSE | 0.007175987508 | 0.006170581278 | -0.001005406230 |
| `COM_DFE` (dB) | 0.576241480 | 1.219709685 | +0.643468205 |
| `delta_COM_MLSD` (dB) | 0.979365755 | 1.683372145 | +0.704006389 |
| `COM_MLSD` (dB) | 1.555607236 | 2.903081830 | +1.347474594 |

公開 SiCoPR 同一固定候選輸出：`COM_orig`（DFE）=1.524760783 dB、
`delta_COM`=1.371137901 dB、最終 `COM_dB`=2.895898685 dB。
本地修正後最終僅高 0.007183145 dB，但 DFE 基線低 0.305051098 dB、
MLSD 加成高 0.312234243 dB；兩項抵消，不能把 final COM 的近似
當成 impairment／MLSD stage 已對齊。固定 phase=23 的 pre-DTE
receiver/XT/TX/jitter/quantization RMS 依序為
0.358829/0.336085/0.399798/0.325274/0.375278 mV；
FFE 設定本身不改這些 phase 固定的 pre-DTE 公式。

相同 SiCoPR `sbr`／`S_n` 餵本地修正配置時，MSE 與 reference 差
約 6e-16，歸一化 `w_lim` 對 SiCoPR `C` 的最大 tap 差
約 3.7e-13；MMSE solver 方程在這個受控邊界對齊。

## TC-008：post-FFE quantization／MLSD stage 差異（唯讀診斷；待分類）

- 第一個明確算法差異：本地 `calculate_COM_DFE()` 用完整 `w_lim`
  對 ADC input uniform PMF 做 FIR；所持 IEEE P802.3dj/D3.0
  Annex 178A Eq. 178A-44 指出對 FFE tap index vector `i` 的所有
  coefficient 重複量化卷積。SiCoPR `adjust_Rx_noise_for_quantization()`
  的 loop 明確略過 `cursor_tap`，僅加入其他 RX FFE taps。歸類 G-006，
  不是本地 spec defect。
- 外部受控 A/B：保持 FFE 修正後 phase=23 的相同 post-FFE 輸入及所有
  其他 PMF 項，只在組合 final PDF 時去除 ADC quantization 的主 tap。
  本地 `COM_DFE` 從 1.219709685 升為 1.555327636 dB
  （+0.335617951 dB）；SiCoPR DFE 是 1.524760783 dB。此 A/B
  解釋了 DFE 基線 gap 的主要部分，但不能以 reference 數值取代
  Eq. 178A-44。對同一修改再跑本地 MLSD 時，最終 COM 變成
  3.607797410 dB，顯示 final 2.903≈2.896 是 stage 抵消，
  不是一致驗證。
- 修正 FFE 後、本地 post-PMF 除以 RX FFE 主 tap gain 59.0662
  的參考邊界：signal amplitude 5.3612 mV（SiCoPR 5.3743），
  ISI 單項 tail 2.8080 mV（2.8000）、XT 單項 tail 1.6184 mV
  （1.6284）、Gaussian RMS 0.7135 mV（0.7164）。這些接近，
  但不同 pulse/ADC policy／量化網格尚未完全對齊。
- final-PMF tap threshold 從 0.3167 mV 降至 0.1／0.03 mV 時，
  `COM_DFE` 從 1.219710 變 1.204257／1.201737 dB；有
  約 0.018 dB 數值敏感度，無法單獨解釋 0.305 dB 基線 gap。
- MLSD 的已確認比較邊界：本地 `DER_MLSD=0.001182989` 是
  Eq. 178A-47 逐 `j` 項的原始和；SiCoPR `MLSE_U1_c_178A()`
  先計算原始和，隨後把 `DER_MLSE` 欄位覆寫為原始 PDF 在
  `A_s*10^(delta_com_notrunc/20)` 的 CDF 值。因此發布欄位
  `DER_MLSE=3.526101e-7` 不能與本地原始和相減作為模型 gap；
  先前此項對比無效。可比較的 SiCoPR `delta_COM=1.371138 dB`，
  本地為 1.683372 dB，但兩邊 `p_an`／`R_ni` 算法仍不同。
- G-007：本地 `evaluate_delta_com_an()` 依 178A.1.10.1 與
  Eq. 178A-50/51，只增加 Gaussian receiver noise 的方差，保留
  ISI／XT／DDJ／quantization PMF，再重建 `p_an` 並求 `g_an`。
  SiCoPR `MLSE_U1_c_178A()` 呼叫 `scaleCDF()`，直接將完整
  DFE PDF 的振幅軸按 `10^(delta_COM_an/20)` 放大，連非 Gaussian
  impairment 都一同縮放，再由方差差值反推 `g_an`。這是 reference
  演算法差異；本地做法符合所持 D3.0 draft，先保留，另做受控 A/B。
- E-006：本地 `initialize_mlsd_status()` 將 Eq. 178A-54 的
  `S_ni` 算成 `S_rn + S_an + S_isi`。所持 D3.0 draft
  Eq. 178A-15 的 `S_n` 是 quantizer output／RX FFE input 的
  總 PSD；Eq. 178A-54 明定
  `S_ni = S_n|H_rxffe|² + S_an + (sigma_X²/f_b)|DFT(h_ISI)|²`。
  因此正確來源是 `pre_dte.psd.S_total` 再乘 RX FFE 頻響。
  先前只在 `%TEMP%` 以 post-FFE `S_total` 替換 `S_ni`，
  保持 phase=23、FFE、DFE PDF、`p_an/g_an` 不變：
  `sigma_ni` 89.469804→104.822499 mV，`R_ni[0]`
  0.008004846→0.010987756 V²，原始 DER 0.001182989→0.000866181，
  `delta_COM` 1.683372→1.943375 dB，最終 MLSD COM
  2.903082→3.163085 dB。這僅證明漏項有影響，並非
  Eq. 178A-54 的正確替換。本案 `pre S_n` 重格點再乘 FFE
  的 sigma 為 62.367061 mV，post-FFE reporting `S_total`
  為 62.196967 mV；其量化項 RMS 分別 29.256098／
  28.891740 mV，因 pre／post `V_qc` 為 40.95／40.44 mV。
  兩者不相同，不能把 post `S_total` 當成 spec `S_n|H|²`。
  以上 final 數值也仍含 E-007 公式錯誤及 E-008 的 `S_isi`
  one-sided 正規化錯誤，不是 spec-valid 結果。
- E-007：所持 D3.0 draft Eq. 178A-47 的增量分母為 `A_s`；
  本地 `calculate_COM_MLSD()` 使用 `A_ni`。由於
  `COM_DFE=20log10(A_s/A_ni)`，現行 raw final 比 Eq. 178A-47
  多出一整個 `COM_DFE`。固定候選在 E-006 修正前／後，
  若僅以正確 Eq. 178A-47 後處理，raw/floored MLSD COM
  分別為 1.683372／1.943375 dB；這是代數試算，尚未改核心。
- 下一個小目標：取得同一 normalized post-FFE pulse/FFE/ADC input，
  分別比較 `p_ISI/p_XT/p_DD/p_G/p_qn`、combined CDF 的 DER quantile，
  再比較 MLSD added noise、`R_ni`、逐 `j` DER term 和 `delta_COM`。
  E-006 的具體 Core Model Change Contract 見 TC-009。

## TC-009：MLSD Eq. 178A-54 從 pre-FFE `S_n` 濾波（Core Model Change Contract；已核准、工作樹實作待獨立提交）

實作驗證（2026-10-08）：固定 SiCoPR phase=23、FFE 6/15/87，
`S_n_filtered` RMS 62.367061 mV、`S_isi` RMS 47.759096 mV、
`R_isi[0]` 0.002280931243 V²，與時域能量相等；
`S_ni` RMS 110.218233 mV、`R_ni[0]` 0.012148058995 V²。
`MSE=0.006170581277695888`、`COM_DFE=1.219709685032426 dB` 維持基線。
TC-009 單項驗收當時尚未修正 Eq. 178A-47，故記錄
`DER_MLSD=0.0008488189507241757`、`COM_MLSD=3.179473201716693 dB`
與全套 `76 passed`；後續 TC-011／TC-010／TC-012 已分別執行，
目前 final 值與測試結果以各自段落為準。核心檔案與 index 仍有其他既有
未提交修改，須先隔離各項變更才可依契約做獨立 commit。
TC-010 重整後，本項 Eq. 178A-54 的現行函式名稱是 `COM.build_mlsd_noise()`；
下方原契約沿用提出時的 `initialize_mlsd_status()` 名稱作變更記錄。

1. **原因**：`initialize_mlsd_status()` 把 Eq. 178A-54 的
   `S_n|H_rxffe|²` 誤換為只有 post-FFE receiver noise 的
   `S_rn`。先前提案直接替換為 post-FFE reporting `S_total`
   也不嚴格正確：它的 ADC clipping／`S_qn` 與 pre-FFE
   Eq. 178A-15 `S_n` 不同，固定候選已實測不等價。另外
   `S_isi` 直接以 spec 雙邊公式值建立 one-sided PSD，
   漏了內部頻點的 2 倍轉換（E-008）。
2. **依據**：所持 IEEE P802.3dj/D3.0 Annex 178A.1.7
   Eq. 178A-15 將 `S_n` 定義在 quantizer output／RX FFE
   input；Annex 178A.1.10.3 Eq. 178A-54 明定先乘
   `|H_rxffe|²`，再加 `S_an` 與殘留 ISI PSD。SiCoPR 的
   `S_ni=S_isi+S_n+S_an` 使用其 FFE 後的 `S_n`；變數名
   的位置須依呼叫階段判讀，不能反過來覆蓋規格公式。
3. **現行公式與資料流**：`calculate_pre_dte_imp_at_pos()` 已形成
   `pre_dte.psd.S_total=S_rn+S_xn+S_tn+S_jn+S_qn`，供 MMSE
   `R_n`；`initialize_mlsd_status()` 卻採 post-FFE
   `S_rn+S_an+S_isi`，其中 `S_isi` 用
   `(sigma_X²/f_b)|DFT(h_ISI)|²` 直接填入只存單邊頻率的
   `SampledPSD`，再做 `to_autocorrelation()`。
4. **擬議公式與資料流**：選定候選的 `pre_dte.psd.S_total`
   作為 Eq. 178A-15 的 `S_n`；將它放到 `H_rxffe`／
   `h_ISI` 的共用 theta/fb grid，逐頻乘 `|H_rxffe|²`，
   用 spec 雙邊 `(sigma_X²/f_b)|DFT(h_ISI)|²` 建構
   one-sided equivalent `S_isi`（內部 rfft 點乘 2，DC／
   Nyquist 不乘），再採 `S_ni=S_n_filtered+S_an+S_isi`，
   以相同 PSD 的 `to_autocorrelation()` 取得 `R_ni`。
   驗證 grid、單位與 Parseval；不得使用 post-FFE
   reporting `S_total` 作 spec 公式的隱含替代。
   現有支援情境 `S_in=0`；若啟用 spec 的外加 interference
   source，需另立該 source 的實作契約。
5. **檔案／函式**：僅 `src/serdes_coding/models/com_model_178A.py::
   COM.initialize_mlsd_status()` 的 `S_n` 選源、`S_isi`
   one-sided 建構與輸入檢查；若 TC-010 先
   獲批准並實作，此函式改名為 `COM.build_mlsd_noise()`，本契約
   只處理其中的 Eq. 178A-54 公式，不再改介面。新增或調整
   `tests/` 的 Eq. 178A-54 單元不變量與固定 case 驗證；更新
   `docs/models/178A/` 對應 contract。不得順帶改 `p_an`、
   quantization、FFE mapping、GUI 或 search policy。
6. **預期改變**：`S_n_filtered`、`S_isi/sigma_isi` 的 MLSD
   中間值、`S_ni/sigma_ni`、`R_ni`、逐 `j` DER term、`DER_MLSD`、
   `delta_COM`、`COM_MLSD`；TC-008 的 post-S_total 試算
   僅是漏項敏感度，不能當本契約的 final golden。
7. **必須不變**：path/H21/pulse、pre-DTE PSD 與 `R_n`、phase、
   `w_lim/b_lim`、MSE、post-FFE 各分量 PSD 與 `S_total`、
   ADC `V_qc/delta`、DFE PMF 與 `COM_DFE`、`p_an/g_an/S_an`。
8. **驗證與驗收**：人工頻譜單元測試逐點驗證
   `S_n_filtered = regrid(pre_dte.S_total)*|H_rxffe|²` 以及
   `S_ni = S_n_filtered+S_an+S_isi`（相對容差 1e-12），
   並逐點核對 `S_isi` 的 one-sided 轉換（DC／Nyquist 不倍增、
   內部點倍增），`R_isi[0] == sigma_X²*sum(h_ISI²)`，
   `R_ni == S_ni.to_autocorrelation()`；刻意給不同
   theta/fb grid 時須明確處理或報錯。固定 phase=23、FFE
   6/15/87 的 case，唯讀試算 `S_n_filtered` sigma 為
   62.367061 mV、`R_n_filtered[0]` 為 0.003889650346 V²，
   與 post reporting `S_total` 的 62.196967 mV／
   0.003868462716 V² 不同；`S_isi` sigma 應為
   47.759096 mV、`R_isi[0]` 為 0.002280931243 V²，
   舊法只有 33.790771 mV／0.001141816235 V²。
   完整 `S_ni/R_ni` 應以本契約
   路徑重算後建立 golden。DFE/MSE、pre `S_n/R_n` 必須不變。
   跑 MLSD 專項與相關 178A regression；不以 final SiCoPR COM
   接近程度當成通過條件。
9. **影響**：93A 完全不變；178A 的 MLSD-enabled single run
   及 search-final 受影響；DFE-only single/search 不變。
10. **回退邊界**：修改須獨立提交，只包含核准的 kernel、測試與
    contract 文件；回退該單獨 commit 即還原此變更。實作前
    保全目前 HEAD `68af9b8` 與既有未提交修改，不能覆蓋或混入。

## TC-010：MLSD top flow 與 DER 純計算介面（Core Model Change Contract；已核准、工作樹實作待獨立提交）

執行基線：TC-009／TC-011 已先於本項在工作樹完成；本契約的「數值不變」
一律指它們之後的 Eq. 178A-54 與 Eq. 178A-47 現行結果。舊稿中
「維持 E-006／E-007 舊數值」是已過時的先後順序描述，不能回退已核准公式。
固定 phase=23、FFE 6/15/87 候選的 TC-010 前後逐行輸出完全相同，
包括 MSE、COM_DFE、`S_n_filtered`、`S_isi/R_ni`、DER、`A_MLSD` 與
`COM_MLSD=1.9597635166842666 dB`；純 DER 函式的輸入不變性測試通過。
TC-010 後全套 regression `78 passed`。

1. **原因**：目前 `calculate_der_mlsd()` 收到尚未完成的
   `COMMLSDStatus`，只讀其中 `added_noise.p_an` 與 `R_ni`，
   又修改同一 status 並重複回傳 DER；MLSD 三個主要 block
   的輸入／輸出在 top flow 中不夠明確。此項是介面與資料所有權
   調整，不更動已完成的 E-006/E-007 公式修正。
2. **依據**：所持 P802.3dj/D3.0 Annex 178A.1.10：
   178A.1.10.1／Eq. 178A-50/51 是 added-noise calibration；
   178A.1.10.3／Eq. 178A-54 是 MLSD PSD/autocorrelation；
   Eq. 178A-48/49/52/53 是 DER 計算，Eq. 178A-47 是 final COM。
   本契約僅重排程式責任及標示公式，不更動上述數學定義。
3. **現行流程**：`calculate_COM_MLSD()` → `solve_g_an()` →
   `initialize_mlsd_status()`（回傳部分填妥的 `COMMLSDStatus`）→
   `calculate_der_mlsd(status,...)`（讀與改同一 status）→
   final COM 後處理與 `_assign_mlsd()`。
4. **擬議流程**：top flow 顯式依序呼叫 `solve_g_an()`、
   `build_mlsd_noise()`、`calculate_der_mlsd()`；第一項回傳
   `COMAddedNoiseStatus`，第二項回傳獨立的 MLSD noise 結果
   （`S_isi/sigma_isi/S_ni/sigma_ni/R_ni`），第三項只接收
   `p_an, R_ni, L, As, b_lim_1, trunc_len` 並回傳
   `(DER_MLSD, der_by_j)`，不得修改輸入。總控做 Eq. 178A-47
   後處理、組裝現有平坦欄位的完整 `COMMLSDStatus`，最後才指派
   `status.mlsd`。函式/運算處逐段標明 Eq. 178A-47 至 54，
   Eq. 178A-54 保留 TC-009 已修正的 pre-FFE `S_n` 與 one-sided
   `S_isi` 路徑，Eq. 178A-47 保留 TC-011 的 `A_s` 分母。
5. **檔案／函式**：僅 `src/serdes_coding/models/com_model_178A.py`
   的 MLSD noise 結果型別、`COM.initialize_mlsd_status()` 改名為
   `COM.build_mlsd_noise()`、`calculate_der_mlsd()`、
   `COM.calculate_COM_MLSD()`、必要的 `__all__`；更新
   `docs/models/178A/call_tree.md`、`status_tree.md`、
   `stages/com_mlsd.md` 與對應 `tests/`。不改報表欄位、GUI、
   config、其他 COM stages；repo 內無舊 helper 的外部呼叫。
6. **預期改變**：Python function signature、暫態結果型別與
   call tree；`COMMLSDStatus` 仍為最終輸出，報表讀取的既有欄位
   名稱不變。不得藉此調整任何數值公式或 PMF/PSD 計算順序。
7. **必須不變**：`g_an/S_an/p_an`、`S_isi/S_ni/R_ni`、各
   `der_by_j`、`DER_MLSD`、`A_MLSD`、`delta_COM`、
   `COM_MLSD`、DFE 狀態與所有 93A 行為；數值基準為
   TC-009／TC-011 實作後的固定候選。
8. **驗證與驗收**：以固定 synthetic `p_an/R_ni` 比較重整前後
   `der_by_j` 與總 DER（相對容差 1e-12），驗證 DER 函式不
   mutate `p_an/R_ni`；固定 phase=23、FFE 6/15/87 的
   SiCoPR case 比較三 block 全部輸出及 final COM，數值不變
   （相對容差 1e-12，dB 絕對容差 1e-12）。報表所需 status
   欄位全數存在；跑相關 178A regression。專項測試要驗證
   `build_mlsd_noise()` 的中間結果與 DER 純函式的輸出責任。
9. **影響**：93A 不變；178A MLSD-enabled single/search-final
   執行經新介面但數值不變；DFE-only 流程不變。
10. **回退邊界**：獨立提交本介面／註解／測試／權威 stage 文件；
    回退該提交即恢復舊介面。實作前保全 HEAD `68af9b8`
    與工作樹既有未提交修改；不得混入 TC-009/TC-011 公式改動。

## TC-011：MLSD Eq. 178A-47 的分母（Core Model Change Contract；已核准、工作樹實作待獨立提交）

TC-009 後固定 phase=23 候選的唯讀後處理：`A_s=0.31666666666666665 V`、
`A_ni=0.27518 V`、`A_MLSD=0.3448300000000002 V`；現有
`delta_COM=1.9597635166842666 dB`、`COM_MLSD=3.179473201716693 dB`。
若只依 Eq. 178A-47 將分母改為 `A_s`，`delta_COM=0.7400538316518406 dB`、
`COM_MLSD=1.9597635166842666 dB`，差恰為本案 `COM_DFE=1.219709685032426 dB`。
TC-011 實作後固定候選重跑符合上述唯讀預測：`S_isi` RMS
`47.75909591966955 mV`、`R_ni[0]=0.012148058995098972 V²`、
`DER_MLSD=0.0008488189507241757`、`COM_DFE=1.219709685032426 dB`
維持 TC-009 後基線；只有 `delta_COM` 與最終 MLSD COM 改變。
人工 PMF 的正增量及 DFE floor 不變量測試通過；全套 regression
`77 passed`（另有 `2 subtests passed`）。待獨立提交。

1. **原因**：`calculate_COM_MLSD()` 目前用
   `20log10(A_MLSD/A_ni)` 作為加在 `COM_DFE` 後的增量；
   Eq. 178A-47 明定分母為 `A_s`，現況重複計入一個
   `COM_DFE=20log10(A_s/A_ni)`。
2. **依據**：所持 IEEE P802.3dj/D3.0 Annex 178A.1.10
   Eq. 178A-47；SiCoPR `MLSE_U1_c_178A()` 也以
   `A_s` 計算 MLSD COM 增量。
3. **現行公式**：`A_MLSD=-p_an.quantile(DER_MLSD)`；
   `delta_COM=20log10(A_MLSD/A_ni)`；
   `COM_MLSD_raw=COM_DFE+delta_COM`，再以 DFE COM 設下限。
4. **擬議公式**：保留同一 `A_MLSD`、DER 與 DFE 基線，改為
   `delta_COM=20log10(A_MLSD/As)`；
   `COM_MLSD_raw=COM_DFE+delta_COM`，下限規則不變。
5. **檔案／函式**：僅 `src/serdes_coding/models/com_model_178A.py::
   COM.calculate_COM_MLSD()` 的 Eq. 178A-47 後處理與相應註解；
   新增 Eq. 178A-47 不變量與固定 case 測試，更新
   `docs/models/178A/stages/com_mlsd.md`。若 TC-010 已實作，
   使用其明確的 final assembly；本項不改其三 block 介面。
6. **預期改變**：`delta_COM`、`COM_MLSD_raw`、可能的
   `COM_MLSD`；後者仍由 `max(COM_DFE, raw)` 決定。
7. **必須不變**：`A_ni/As/COM_DFE`、`p_an/g_an/S_an`、
   `S_isi/S_ni/R_ni`、`DER_MLSD/der_by_j`、`A_MLSD`、
   所有前級 path／impairment／MMSE／DFE 結果。
8. **驗證與驗收**：人工 PMF/DER 單元測試直接核對
   `COM_MLSD_raw-COM_DFE == 20log10(A_MLSD/As)`，以及
   下限規則。固定 phase=23、FFE 6/15/87 的 case，若
   TC-009 尚未執行，預期 final 約 1.683372 dB；若 TC-009
   已執行，須用正確的 pre-FFE `S_n` 路徑重算 DER 與 final，
   先前 post-FFE `S_total` 替換所得的 1.943375 dB 不可用作
   golden。實作時以完整精度重算，容差 1e-6 dB；
   `DER_MLSD` 與 `R_ni` 必須完全維持該順序的前態。
9. **影響**：93A 與 DFE-only 不變；178A MLSD-enabled
   single/search-final 的 final COM 可能變更，報表欄位不變。
10. **回退邊界**：獨立提交本 Eq. 178A-47 公式、測試與
    stage 文件；回退該提交恢復先前後處理。不得混入
    TC-010 介面或 TC-009 PSD 修改，並保全既有 dirty 工作樹。

## TC-012：MLSD Eq. 178A-52 第一項 PMF 縮放符號（Core Model Change Contract；已核准、工作樹實作待獨立提交）

TC-010 後固定 phase=23、FFE 6/15/87 候選由負號改正號，
`DER_MLSD` 從 `0.0008488189507241757` 到 `0.0008488189507225543`
（差 `-1.62e-15`），`COM_MLSD=1.9597635166842666 dB` 不變；
`S_ni/R_ni`、DFE COM 與前級結果不變。非對稱人工 PMF 的
`P_1(-0.3)=0.81`，舊符號為 `0.09`，專項測試通過；
TC-012 後全套 regression `79 passed`。

1. **原因**：現行 `calculate_der_mlsd()` 以 `scale_x(-b_lim_1)` 建立
   `p_1_term`，規範 Eq. 178A-52 的第一項為
   `p_an(y/b_lim(1))/|b_lim(1)|`，即 `+b_lim(1)` 的隨機變數縮放。
   真實固定候選的 `p_an` 幾乎對稱，因此此案差異被遮蔽；此等價
   不能擴張到任意非對稱輸入。
2. **依據**：所持 P802.3dj/D3.0 Annex 178A.1.10.2 Eq. 178A-52
   與 `Pmf1D.scale_x()` 的 `Y=scale*X` 契約；Eq. 178A-53 的後續
   `1-b_lim(1)` 縮放不在本項修改範圍。
3. **現行公式與資料流**：`p_1=conv(p_an,scale(p_an,-b_1))`，
   之後每個 `j` 都由此 `p_1` 迭代得到；`p_j` 供 Eq. 178A-48
   的 CDF 門檻查詢。
4. **擬議公式與資料流**：僅第一項改為
   `p_1=conv(p_an,scale(p_an,+b_1))`；保留 Eq. 178A-53 的
   `scale(p_an,1-b_1)`、PMF 投影網格、卷積與 DER 權重。
5. **檔案／函式**：僅
   `src/serdes_coding/models/com_model_178A.py::calculate_der_mlsd()`
   的 `p_1_term` 縮放係數與 Eq. 178A-52 註解；相應 `tests/`
   與 `docs/models/178A/stages/com_mlsd.md`。不改 PSD、`R_ni`、
   Eq. 178A-47、TC-010 介面、GUI 或其他 COM stage。
6. **預期改變**：非對稱 `p_an` 的 `p_1/p_j`、逐項 DER、總 DER
   與最終 MLSD COM；本固定 SiCoPR 候選的數值變化應接近浮點誤差。
7. **必須不變**：`g_an/S_an/p_an`、`S_ni/R_ni`、`u_j/V_j`、
   `COM_DFE`、前級 path／impairment／MMSE、所有 93A 行為。
8. **驗證與驗收**：非對稱人工 PMF 的 `p_1` 與 Eq. 178A-52
   手算卷積逐點一致；例如質點 `[-0.2,0.4]`、機率
   `[0.9,0.1]`、`b_1=0.84`、`dx=0.001` 時，
   `P_1(-0.3)` 正號為 `0.81`、舊負號為 `0.09`。固定
   phase=23、FFE 6/15/87 的 `p_an` 鏡像最大誤差
   `5.83e-19`、第一項 DER 正負號差 `1.00e-15`；本案
   `DER_MLSD` 與 COM 應在數值容差內維持。跑 MLSD 專項
   及 178A regression，不以 reference COM 接近度替代公式驗收。
9. **影響**：93A 與 DFE-only 不變；178A MLSD-enabled
   single/search-final 在 `p_an` 不對稱時可有數值變化。
10. **回退邊界**：獨立 commit 僅包含本 Eq. 178A-52 符號、
    對應測試與 stage 文件；回退該 commit 即恢復舊符號。
    保全既有工作樹修改，不得混入 TC-009／TC-010／TC-011。

## Ad Hoc → project config 映射語義稽核（唯讀進行中）

- 2026-10-08 盤點：178A registry 有 132 條規則：10 derived、72 converted、
  50 direct。`mapping_rules.py` 與欄位表目前均為既有 untracked 工作，
  Git 沒有這三條 FFE 公式的提交歷史；無法證實當初採用 `-1/-2`
  的原始理由。「混淆 tap 數量與 1-based/0-based index」只是推論。
- 本案 conversion audit 實際記錄 `ffe_pre_tap_len=6`、
  `ffe_post_tap_len=8`、`N_f=80` 被算成 `5/12/86`。既有測試只核對
  來源 `ffe_pre_tap_len=6`，未核對三個衍生結果與 spec 的 tap-count
  等式。匯出驗證確認值型別及 runtime 可建構，不能證明來源語義正確。
- 已逐項核對 10 條 derived 的語義：除 TC-007 三條 FFE 規則外，
  `fr=f_r×f_b`、固定 TX cursor index `num_pre=3`、
  `w_float_min=-bmaxg`，以及四組 `Include PCB` enable 規則在本案
  來源／參考實作下未發現同類錯誤；這不等於跨 case 數值驗收。
- 已檢查本案高風險 converted 邊界：`f_b/Delta_f/T_r/eta_0`
  的量綱轉換、TX/RX `R_d` profile 選擇、`C_d/L_s` 的 TX/RX row、
  `package_Z_c` 的 segment×side 軸與 `z_p` testcase column，
  未找到另一個已證實的錯映射。其餘 converted/direct 規則仍待
  用獨立參考值及不同 profile／testcase 逐項查，不以同一規則重算
  當作驗證。
- 下一個可關閉的小目標：先取得 TC-007 核准並修正 FFE layout；
  接著針對其餘 high-impact 映射製作 source→project→runtime→SiCoPR
  欄位對照，至少覆蓋非對稱 TX/RX profile、不同 package testcase、
  `Include PCB=1/2`、`N_bg=0/>0`、DFE bounds 與各單位。發現
  新錯誤時另立 E 編號／獨立 contract，避免擴大 TC-007 範圍。
