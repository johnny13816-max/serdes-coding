# TC-023 — 178A MLSD reference realization

## 狀態

已核准並完成工作樹實作與 Akinwale 固定案例驗證；待在乾淨邊界隔離提交。

## 目的與分類

- **模型錯誤**：Eq. 178A-49 最後一項位於 spec index `i=j+1`，因此為
  `(-1)^(j+1) b_lim(1)`。Python 儲存在 `u_j[j]` 不會改變公式指數。
  此項直接修正，不建立平行分支。
- **reference realization**：MATLAB 4.17／SiCoPR 對 added-noise PDF、sequence
  truncation 與 published DER 採用不同的數值流程。保留具名方法，project
  workbook 的 `align_to_ref=True` 只在 adapter 展開它們。

## 修改範圍

- `models/com_model_178A.py`
  - 新增 `COMPolicyConfig`。
  - 修正 `_build_mlsd_sequence_vector()` 的 Eq. 178A-49 末項。
  - `scaled_total_pdf` 以完整 DFE PDF 的 x 軸縮放建立 `p_an`，再由變異數差求
    `g_an` 與 `S_an`。
  - `calculate_der_mlsd()` 明示 PMF scaling 與 MATLAB truncation penalty。
  - `COMMLSDStatus` 分開保存 sequence DER、Eq. 178A-47 使用的 DER 與 reference
    重新評估的 published DER。
- `io/com_excel_io_178A.py`
  - `align_to_ref=True` 展開 `scaled_total_pdf`、`matlab_relative_tail`、
    `baseline_pdf_re_evaluation`；workbook 不新增細節欄位。
- MLSD focused tests、stage 文件及 branch inventory。

## 保持不變

- 93A、path/MMSE/post-FFE/COM_DFE 數值流程。
- `align_to_ref=False` 的 Annex added-noise 建構。
- workbook 對外欄位；直接 Python API 可用具名 `COMPolicyConfig`。

## Akinwale 驗證

SiCoPR：`COM_DFE=1.5247607834259944 dB`、`delta_COM=1.3711379014472647 dB`、
`COM=2.8958986848732593 dB`。

Project reference profile：

- `COM_DFE=1.5247607834259893 dB`
- `g_an=6.353345786039307`
- `R_ni[0]=0.011852245254906692`
- sequence DER `2.4246607887464232e-4`
- published DER `3.6077916391236006e-7`
- `delta_COM=1.3562902232368024 dB`
- `COM_MLSD=2.8810510066627915 dB`

最終差 `-0.0148476782104678 dB`，通過既定 reference COM `0.05 dB` 對齊門檻；
未通過本契約原先設定的 `0.01 dB` 診斷目標。殘差恰為 Eq. 178A-47 amplitude
grid 的兩個 bin（Project 1169、reference 1171），目前沒有證據可把它歸因為
另一個已知公式錯誤。後續若要求小於 `0.01 dB`，應先取得 reference `p_an`／
raw sequence DER dump，再決定是否新增 CDF/grid method；不得用常數補償。

## 回復邊界

TC-023 應以獨立 kernel commit 回復。現有工作樹包含較早已核准契約的重疊修改，
因此本輪不以 broad commit 混入其他變更。
