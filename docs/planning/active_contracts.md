# 當前契約狀態

此文件只保留目前執行焦點、排隊項目與最近完成的責任邊界。完整歷史與
E/G/T 證據見 [`reference_alignment_contracts.md`](reference_alignment_contracts.md)，
v1.0 release 狀態見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

## Workflow state

本輪規則維護已結案，沒有 active rule change；決策與 commit evidence 見
[rule_changes.md](rule_changes.md)。RC-004 保留 Proposed，由規則專用對話另行評估，
不阻擋 technical queue，也不交由專案更新對話處理。使用者指定新專案對話先唯讀評估歷史遺留錯誤，
完成 evidence、impact、disposition 與未解項目記錄後，再恢復下列未完成的 v1.0 review；不直接授權修正。

`GOV-V1-002` 已完成當時的 governance 文件整理，但其「178A 九章全面 PASS」結論在
2026-10-28 重新審查後判定過度擴張。P1/P2 保持完成，P3–P9 依
[`v1_0_roadmap.md`](v1_0_roadmap.md) 重開。現在沒有 `Approved` 或 `Implemented` 中的項目。

歷史評估可唯讀檢查 93A legacy 問題，但不啟動 93A 實作。評估後依 workflow integrity gate，
以 read-only、半代理 review 恢復 178A P3 workbook/config interface；發現修改需求後另依責任邊界提出 contract。

## Current queue

| ID／名稱 | 狀態 | 邊界 | 下一個關卡 |
| --- | --- | --- | --- |
| GOV-V1-002 — 178A review 與 v1.0 狀態收斂 | **Closed with corrected claim** | governance 文件已提交；全面 PASS claim 已撤回，P1/P2 evidence 保留 | 以 roadmap 逐章完成剩餘 review |
| 178A P3 — Workbook/config interface review | Open／next review | Read-only 檢查 Ad Hoc → project → runtime、profile、UX 與 provenance | 新對話先展示完整 mapping tree；不修改 code |
| ARC-CROSS-001 — Current-schema 93A golden case | Open／queued after 178A | 新增或遷移一個可維護的 93A workbook 與數值 baseline；不改 93A equations | 等 178A review 通過後再提出正式 contract |
| ARC-REPORT-001 — Cross-version report plot refinement | Open／non-blocking | 收集並修正 presentation 問題；共用 renderer 與 version composition 分開處理 | 在 G9 documentation/report quality 結案前完成；不阻擋 93A golden-case foundation |

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

## Status rules

- `Open` 只表示已記錄，不表示可開始修改。
- `Approved`／`Implemented` 同一時間最多一項。
- 新提案不會自動中斷 active contract；切換前必須完成或明確記錄 pause/cancel。
- `Closed` 必須具備 scoped implementation、validation、required documentation、
  tracker reconciliation 與 isolated commit；需要 GitHub synchronization 時也必須完成 push。
