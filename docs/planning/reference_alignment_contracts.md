# Reference 驗證待結案 Contracts

本檔追蹤問題的方案與驗收，不是目前模型行為的權威說明。
每次發現問題，記錄方案、範圍、待決策與 close 條件；未批准不修改核心。

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
