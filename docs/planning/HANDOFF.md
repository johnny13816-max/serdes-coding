# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-12 Asia/Taipei
Source branch: main
Source revision: current main plus the isolated remaining-review classification correction
Active task: CP-BR complete initial branch review — ALG-010
Current phase: prior Closed items stay closed; every remaining item is reviewed from eligibility without relying on first/second-review labels
Collaboration mode: Co-Build architecture review
Approved boundary: coding layers are COM root, L0 stage set, L1 stage, L2 function set, L3 functional block, L4 model auxiliary, L5 generic utility/kernel. A branch owner is the lowest layer that unavoidably must know the selected behavior; ownership is not fixed at L3.
Completed: NUM-005 second review confirms L4 _resolve_final_com_pmf_config() as the sole final-domain grid-family owner; required correction is documentation-only scope clarification.
NUM-005 boundary: Stage 6 calculate_COM_DFE() is the complete direct consumer. Stage 7 gaussian_addition directly rebuilds p_G_an on the resolved final dy, while scaled_total_pdf indirectly inherits the Stage 6 PMFs and performs no new regrid.
Shared kernel: L5 COMPMFGridControl.resolve_dy() implements override/relative/capped-relative arithmetic for both NUM-004 and NUM-005 but owns neither domain identity.
Independent future idea: adaptive Stage 1 short/long response-grid classification is recorded in future_ideas.md and isolated in commit a9ab622. It has no branch ID and must not be coupled to NUM-003.
In progress: ALG-010 initial review has begun provenance and source mapping; branch eligibility, options, owner, tie behavior, validation and closure remain undecided.
Queued: NUM-006 and ALG-011–017 also require the same complete initial-review process; their historical approved/owner labels are not authoritative.
Blocked: none.
Next recommended action: decide ALG-010 branch eligibility and intended three-option behavior before approving owner or implementation changes.
Next action owner: Codex performs read-only source/consumer review and presents required changes before implementation.
Post-review cleanup: after every remaining complete initial review is closed, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: do not modify ALG-010 until its eligibility, options, owner and validation contract are discussed and explicitly approved.
Process correction evidence: no traceable ALG-010 first-review closure exists. Legacy E-005 was reused for both an RX FFE tap-layout mapping defect and floating-mode inventory, so it cannot establish prior approval.
NUM-005 evidence: static source audit found the final family read only in _resolve_final_com_pmf_config() and direct calls only from calculate_COM_DFE()/calculate_COM_MLSD(). Stage 7 source confirms direct gaussian_addition and indirect scaled_total_pdf consumption; current focused tests are 9 passed. Production path is unchanged, so golden was not rerun.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/stages/mmse_dte.md;
                docs/validation/mmse_input_akinwale_178A.md;
                docs/planning/active_contracts.md
Dirty-state summary: remaining-review classification and queue wording are ready for isolated commit; no production code is changed.
```

93A、reporting、C2M migration 與 release 項目維持暫停。CP-BR 的完成不構成
v1.0 release claim。

## New-session resume checklist

1. Verify canonical cwd, Git root, branch, HEAD and dirty state.
2. Read `AGENTS.md`, this snapshot, `active_contracts.md`, roadmap, and the task-owning document.
3. Report resumable task, stale/conflicting state, and next gate before execution.
4. Classify task/model/mode and show the scope tree before modification.
5. Replace this snapshot on the next `/handoff`, active-task switch, pause/block, or closure.

## Closure slimming

After an item closes, remove its implementation history from this file. Keep only the next active task, phase, mode,
approved boundary, next owner and stop point. Commit history, closed contracts and validation documents preserve history.
