# 當前契約狀態

此文件只保留目前執行焦點、排隊項目與最近完成的責任邊界。完整歷史與
E/G/T 證據見 [`reference_alignment_contracts.md`](reference_alignment_contracts.md)，
v1.0 release 狀態見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

## Workflow state

`GOV-V1-002` 已完成 178A design-review closure：實作提交、驗證證據、架構文件、
tracker 與 release gate 已重新核對。178A architecture review 結論為 **PASS**；這不等於
整個 v1.0 release 已完成。現在沒有 `Approved` 或 `Implemented` 中的項目。

依 workflow integrity gate，下一項不得直接進入實作。應先為
`ARC-CROSS-001` 提出並核准獨立 contract，再建立 current-schema 93A golden case。

## Current queue

| ID／名稱 | 狀態 | 邊界 | 下一個關卡 |
| --- | --- | --- | --- |
| GOV-V1-002 — 178A review 與 v1.0 狀態收斂 | **Closed** | 只整理 governance、architecture、validation 與 release 文件；不改模型或數值流程 | 無；本文件、design review、tracker 與 release gate 為 closure evidence |
| ARC-CROSS-001 — Current-schema 93A golden case | Open／next proposed | 新增或遷移一個可維護的 93A workbook 與數值 baseline；不改 93A equations | 先確認 canonical source case 與 schema migration，提出正式 contract |
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
