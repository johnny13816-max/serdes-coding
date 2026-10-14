# Channel Sdd renormalization contract 與驗證

批准日期：2026-10-07。範圍：S4P ingestion；93A／178A 共用。

## 邊界與依據

178A D3.0（2026-02-16）178A.1.3／Eq. 178A-4：measured differential-mode
二埠 S 參數的 reference impedance 必須轉為 `2R_0`。
原始測量 impedance 為 `2R_m`；相同實數 port impedance 下，
`rho=(R_0-R_m)/(R_0+R_m)`，
`S=(S_measured-rho*I) @ inv(I-rho*S_measured)`。

當時的正式預設流程：S4P → 依 port order 取得原始 Sdd 與 measured differential z0 →
二埠 renormalization → measured grid alignment → package cascade。2026-10-11
核准的 TC-016 另提供正式 S4P-first 分支；模板與 93A 仍用此預設流程。
此修正共用於 93A 和 178A，不代表已重新查核其他 93A 方程。

## API contract

- `from_network(mode="s4p"/auto)` 與 `from_touchstone()`：明確傳入 `z0`
  時，該值是目標 differential impedance；轉換 S 數值而非只改 metadata。
- `z0=None`：保留原始 differential impedance。
- `from_s4p_array()`、`from_sdd_array()` 與 `from_network(mode="sdd")`：
  維持原有「輸入已正確 normalization，z0 為指定 metadata」語意。
- 不修改來源 Network，保留 subclass、source_type、port_order、frequency grid。
- 本節原契約的 Sdd-first 模式不改 common-mode reference；TC-016 新增的
  S4P-first 模式會先對完整四埠 renormalize，再取 Sdd。
- 保留既有 per-port impedance 表示；此驗證只涵蓋 COM 使用的相同實數
  single-ended reference impedance，不宣稱不平衡／complex port 的 mixed-mode 轉換已驗證。
- GUI、workbook schema、package、termination gamma、filters、等化公式不變。

## 驗收

`tests/test_channel_renormalization.py` 包含：直接矩陣公式、source 不變、
相同 impedance 不變、array/Sdd constructors 不變、四埠與二埠流程區別、
93A／178A 正式 channel builder 與固定 SiCoPR case。

固定 case：`sicopr_akinwale_vendorx_22db/178A/config.xlsx`。
全頻四個 S 參數對公式 `atol=1e-10, rtol=0`；合成資料 `atol=1e-12`。
同邊界 VTF（H21 × TX transition × RX Butterworth）在 53.125 GHz
loss-dB 內插為 `37.667089589791686 dB`，容差 `1e-6 dB`。
此數值是 renormalization 修正的驗收，不是最終 COM 等價宣告。

2026-10-07 驗證結果：公式與 integration 測試通過。原 post-FFE golden
MSE 由 `0.00620479434110295` 更新為 `0.006203013107434269`；
以修改前 ingestion 做記憶體控制重跑確認原值，保持原本 14 位小數斷言。
固定 SiCoPR single run：pos=19、MSE=0.007175987507961828、
COM_DFE=0.5762414804798679 dB；完整 run evidence 保存在此次 TEMP 子目錄。

## 回復與後續

核心修正隔離成專用 commit。修改前精確 snapshot 保存在此次
`%TEMP%/serdes-renormalization-fix-20261007/sparam.before.py`。
回復只處理本次 patch，不還原其他使用者未提交內容。
後續 reference audit 應先核對完整 complex filter chain 與 pulse 邊界。

## SiCoPR 順序的備用驗證分支（2026-10-10）

這是 reference-only A/B，**不改正式 `from_network(mode="s4p")` 契約**。
可重跑程式：[`../../scripts/validate_schannel_renormalization_178A.py`](../../scripts/validate_schannel_renormalization_178A.py)。
它在單次執行的記憶體中，把原始 single-ended S4P 先由 50 Ω
renormalize 到 `R_0=46.25 Ω`，再依 port order 轉成 92.5 Ω Sdd；
正式分支仍是先轉 100 Ω Sdd、再依 Eq. 178A-4 renormalize 到 92.5 Ω。
選用時只替換 channel reader，TX/RX package、cascade、filter、noise、
MMSE solver 和設定不改，執行後會還原 reader。

固定 Akinwale victim/NEXT/FEXT 六條路徑與 SiCoPR dump 比較，備用分支
的 `S_ch` 四個元素最大複數差 `2.78e-15`。同一 locked TXFFE/CTLE、
同一 pre-RXFFE pulse 邊界，在補償已確認的 12 ps transition-filter
時間原點和 4.56 ps boxcar 中心延遲後，UI-sampled SBR 對 reference
的最大正規化差：正式分支 `1.838e-4`、備用分支 `1.803e-4`。
此結果表示 renormalization 順序不是此 case 的主要 SBR 差異來源；
它也不判定哪條做法應成為專案預設。可由上述腳本的
`--reference-mat`、`--plot` 重建疊圖；圖與原始數值保存在本機
`%TEMP%/serdes-schannel-branch-audit-20261010/`。

同一 32-phase MSE 掃描，兩分支都選專案 phase=23／cursor=163991：
正式分支 `0.006170581278`，SiCoPR 順序分支 `0.006169233304`。
SiCoPR MAT 的 pulse peak=38155、游標=38149（0-based），即 peak 前
6 samples；專案兩分支的選定游標均在各自 peak 前 5 samples。
這是取樣選擇的 **1-sample 差異**，不能把兩個 phase 數字直接相等。
在各自最佳 phase，比 SiCoPR MAT 公布的 87 個 RX FFE tap，主 tap
正規化後最大絕對係數差：正式 `0.01759`、備用 `0.01743`；備用分支
並未消除該差異。強制專案取 peak 前 6 samples 時，備用分支 MSE
`0.006177839510`、tap 最大差 `0.04000`。SiCoPR 此 MAT 未輸出可直接
比較的 MMSE MSE，不能宣稱 MSE 已閉合。既有相同 SiCoPR `sbr/S_n`
source-fed 對照中，專案 solver 的 MSE 差約 `6e-16`、tap 最大差約
`3.7e-13`；下一個首差應檢查固定游標下的 **MMSE 輸入**（SBR、PSD、
自相關與量化），而非先改 solver。

上述數值是升格前的 reference-only 驗證紀錄。使用者已核准將 S4P-first
升格為正式平行方法；具體數值 owner、178A policy 入口與驗收見
[TC-016](../planning/tc016_channel_renormalization_order.md)。現行模板與
93A 保持 Sdd-first，178A SiCoPR case 選 S4P-first；其四埠運算在
`SparamModel.from_network()` 完成，不在 COM path 事後修改 S_ch。
任何新發現的模型錯誤須獨立提出並修正。
