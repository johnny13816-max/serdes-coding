# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: READY
Generated at: 2026-10-28 Asia/Taipei
Source branch: main
Source revision: rule boundary b6dee0f; snapshot included in subsequent closure commit
Active task: none; next project item is 178A P3 workbook/config interface review
Current phase: rule maintenance closed; ready for project-only conversation
Collaboration mode: Co-Build for the next 178A P3 read-only review
Approved boundary: project read-only review; no rule, code or protected-model modification authorized
Completed: rule maintenance RC-001/002/003/005/006; evidence in rule_changes.md
In progress: none
Blocked: none
Next recommended action: preflight then show Ad Hoc -> project workbook -> runtime mapping tree for P3
Next action owner: new project conversation; do not resume rule-maintenance tasks
Stop point: report findings; rule gaps become proposals only; modifications need their applicable approval
Evidence links: AGENTS.md; docs/architecture/project_workflow.md;
                docs/planning/rule_changes.md; docs/planning/active_contracts.md
Dirty-state summary: existing reference_data deletions/additions and results/ untouched; do not mix into commits
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
