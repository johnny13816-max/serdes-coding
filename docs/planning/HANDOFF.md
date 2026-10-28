# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: READY
Generated at: 2026-10-28 Asia/Taipei
Source branch: main
Source revision: rule boundary a1f592c; snapshot included in subsequent closure commit
Active task: none; RC-001/002/005 Closed
Current phase: read truncation recovery rule committed and verified; awaiting user selection
Collaboration mode: Full-Agent for authorized rule maintenance in the current conversation
Approved boundary: current conversation only; new sessions need explicit rule-change authorization
Completed: authorized rule maintenance gate and centralized rule_change lifecycle
In progress: none
Blocked: none
Next recommended action: user selects RC-003 or RC-004 for evaluation; technical queue remains 178A P3
Next action owner: user selects next proposal; unauthorized sessions may only submit proposals
Stop point: no automatic proposal execution, 93A work, or protected COM changes
Evidence links: AGENTS.md; docs/architecture/project_workflow.md;
                docs/planning/rule_changes.md; docs/planning/active_contracts.md
Dirty-state summary: existing reference_data deletions/additions and results/ untouched and outside governance scope
```

## New-session resume checklist

1. Verify canonical cwd, Git root, branch, HEAD and dirty state.
2. Read `AGENTS.md`, this snapshot, `active_contracts.md`, roadmap, and the task-owning document.
3. Report resumable task, stale/conflicting state, and next gate before execution.
4. Classify task/model/mode and show the scope tree before modification.
5. Replace this snapshot on the next `/handoff`, active-task switch, pause/block, or closure.

## Closure slimming

After an item closes, remove its implementation history from this file. Keep only the next active task, phase, mode,
approved boundary, next owner and stop point. Commit history, closed contracts and validation documents preserve history.
