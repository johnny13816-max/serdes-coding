# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-01 Asia/Taipei
Source branch: main
Source revision: HEAD 7902cc8 plus CP-BR closure commit
Active task: CP-BR B-006 pre-DTE ADC clipping convention review
Current phase: B-005 closed; B-006 discussion only
Collaboration mode: Co-Build branch review
Approved boundary: explain and decide B-006 behavior, ownership, config exposure and validation; no B-006 code change before decision
Completed: B-002, B-003, Stage 2/3 boundary, B-005 implementation and closure
In progress: B-006 behavior review
Blocked: none
Next recommended action: compare annex_d3 and matlab_4_17_reference_only clipping inputs and decide whether both remain independently exposed
Next action owner: Agent explains; user decides
Stop point: do not enter B-007/B-008 or modify B-006 until the user accepts its formal change contract
Evidence links: docs/models/178A/stages/README.md; docs/models/178A/stages/pre_dte.md;
                docs/models/178A/branch_behavior_registry.md; docs/planning/tc022_mmse_noise_grid.md
Dirty-state summary: existing reference_data deletions/additions and results/ untouched; do not mix into commits
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
