# 當前契約狀態

此文件只保留目前執行焦點、排隊項目與最近完成的責任邊界。完整歷史與
E/G/T 證據見 [`reference_alignment_contracts.md`](reference_alignment_contracts.md)，
v1.0 release 狀態見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

## Workflow state

使用者已以「可帶入公司後持續擴充」為短期目標恢復 CP-BR stage-by-stage
branch review；93A、reporting、C2M migration 與 release 項目仍維持暫停。
規則維護已結案；RC-004 仍為 Proposed，僅由規則專用對話評估。

歷史評估與 178A P3 workbook/config interface review 已完成；P3 的完成範圍限於目前同步的
SiCoPR case。已完成／未完成事實、分離後的目標與恢復條件見
[v1_0_rebaseline.md](v1_0_rebaseline.md)。未經使用者選定新目標，不得自動恢復 P4、93A、
reporting、C2M migration 或 release 工作。

## Current queue

| ID／名稱 | 狀態 | 邊界 | 下一個關卡 |
| --- | --- | --- | --- |
| GOV-V1-002 — 178A review 與 v1.0 狀態收斂 | **Closed with corrected claim** | governance 文件已提交；全面 PASS claim 已撤回，P1/P2 evidence 保留 | 以 roadmap 逐章完成剩餘 review |
| CP-BR — 178A stage-by-stage branch review | **E-003 closed；next E-004 review not started** | ADC-input 與 final PMF grid numerical controls 已分離；既有 resolver owner 與數值公式不變。B-012 邊界不變；`pmf_keep_mass` 留待 E-004。 | 依 algorithm-review 開場流程介紹 E-004、scope tree、options 與 reference evidence；未核准前不修改 |
| B-005 — Eq-channel impairment length | **Closed 2026-11-01** | Shared L3 供 Stage 2/3/5/7；`full/truncated`；workbook 獨立控制 | Golden COM 不變；closed evidence 見 `tc022_mmse_noise_grid.md` |
| 178A P4–P8 — Remaining design-review chapters | Paused / superseded where CP-BR overlaps | 不重複 CP-BR ownership work；非 branch 章節仍維持暫停 | 完成 CP-BR 後重新盤點 |
| P9 / release preparation | Paused | release candidate、claim boundary、regression/CI、package/tag | 使用者選擇 Goal C |
| ARC-CROSS-001 — Current-schema 93A golden case | Paused | 選定 source case、schema strategy、baseline 與 validation level；不改 93A equations | 使用者選擇 Goal B |
| ARC-REPORT-001 — Cross-version report plot refinement | Paused | 收集具體 plot defect；renderer 與 version composition 分開處理 | 使用者選擇 Goal D |

## Recently closed boundaries

| Boundary | Evidence |
| --- | --- |
| ARC-178A-001 — standalone 178A COM roots | `cc5339e` |
| ARC-178A-002 — semantic dataclass text | `149bbd6` |
| ARC-178A-003 — shared reporting orchestration | `e5b0b2b` |
| ARC-178A-004 — remove 178A implementation dependency on 93A | `4e21aca`, `313cf6b`, `13d1018`, `40470e8` |
| UTIL-SNP-001 — explicit S2P/S4P representations | `d9a2c6e` |
| UTIL-EYE-001 — deterministic LinkSegment eye plotting | `e7e1612` |
| COMPAT-PY37-001 — Python 3.7 utility export | `f774487` |
| UTIL-SNP-002 — synthetic S4P target semantics | `94e5613` |
| 178A P3 — Workbook/config interface review | current SiCoPR scope complete；evidence in `docs/models/178A/design_review.md` |
| B-005 — Eq-channel impairment length | SiCoPR golden DFE COM `1.5247607834259893 dB`、final COM `2.895898684873246 dB`；`187 passed`, `1 deselected`, `2 subtests passed` |
| B-008 — Discrete-amplitude PMF projection | `Pmf1D` 不保存 projection policy；`policy.pmf_projection_method` 只明示注入 projection operation。PMF／policy 專項 `35 passed`；SiCoPR golden DFE COM `1.5247607834259893 dB`、final COM `2.895898684873246 dB` 不變。 |
| B-010/B-011 — PDF→PMF discretization | User-approved technical closure 2026-11-03。`policy.pdf_to_pmf_method` 統一 `bin_integral/pmf_sample`；涵蓋 pre-DTE exact/approx、final COM、MLSD。focused tests `29 passed`、Python 3.7 export passed、SiCoPR golden final COM `2.895898684873246 dB` 不變。PMF policy migration `4870669` 已推送至 `origin/main`。 |
| E-003 — PMF grid numerical controls | ADC-input/final families、workbook 與 provenance 已 canonicalized；owners 保持 `_resolve_adc_input_pmf_config()`／`_resolve_final_com_pmf_config()`。focused tests `37 passed`；workbook formula-error scan 0；SiCoPR golden `COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。 |

## Status rules

- `Open` 只表示已記錄，不表示可開始修改。
- `Approved`／`Implemented` 同一時間最多一項。
- 新提案不會自動中斷 active contract；切換前必須完成或明確記錄 pause/cancel。
- `Closed` 必須具備 scoped implementation、validation、required documentation、
  tracker reconciliation 與 isolated commit；需要 GitHub synchronization 時也必須完成 push。
