# Channel Sdd renormalization contract 與驗證

批准日期：2026-10-07。範圍：S4P ingestion；93A／178A 共用。

## 邊界與依據

178A D3.0（2026-02-16）178A.1.3／Eq. 178A-4：measured differential-mode
二埠 S 參數的 reference impedance 必須轉為 `2R_0`。
原始測量 impedance 為 `2R_m`；相同實數 port impedance 下，
`rho=(R_0-R_m)/(R_0+R_m)`，
`S=(S_measured-rho*I) @ inv(I-rho*S_measured)`。

正式流程：S4P → 依 port order 取得原始 Sdd 與 measured differential z0 →
二埠 renormalization → measured grid alignment → package cascade。
此修正共用於 93A 和 178A，不代表已重新查核其他 93A 方程。

## API contract

- `from_network(mode="s4p"/auto)` 與 `from_touchstone()`：明確傳入 `z0`
  時，該值是目標 differential impedance；轉換 S 數值而非只改 metadata。
- `z0=None`：保留原始 differential impedance。
- `from_s4p_array()`、`from_sdd_array()` 與 `from_network(mode="sdd")`：
  維持原有「輸入已正確 normalization，z0 為指定 metadata」語意。
- 不修改來源 Network，保留 subclass、source_type、port_order、frequency grid。
- common-mode reference 不改；不採 SiCoPR 的四埠先 renormalize 流程。
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
