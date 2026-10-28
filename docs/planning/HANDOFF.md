# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: READY
Generated at: 2026-10-28 Asia/Taipei
Source branch: main
Source revision: HEAD 6adda53 plus this handoff priority update
Active task: assess historical legacy errors before resuming unfinished v1.0 review
Current phase: rule maintenance closed; ready for project-only read-only assessment
Collaboration mode: Full-Agent for historical-error assessment; Co-Build when resuming v1.0 review
Approved boundary: project read-only review; no rule, code or protected-model modification authorized
Completed: rule maintenance RC-001/002/003/005/006; evidence in rule_changes.md
In progress: none
Blocked: none
Next recommended action: preflight; assess legacy errors and record disposition; then resume v1.0 at 178A P3
Next action owner: new project conversation; do not resume rule-maintenance tasks
Stop point: assessment complete means evidence, impact, disposition and unresolved items recorded, not fixes done
Evidence links: AGENTS.md; docs/architecture/project_workflow.md;
                docs/planning/rule_changes.md; docs/planning/active_contracts.md
Dirty-state summary: existing reference_data deletions/additions and results/ untouched; do not mix into commits
```

歷史問題先核對既有稽核發現：93A legacy adapter 的資料路徑／來源資料可用性、缺少的回歸覆蓋，
以及 tracker 與 roadmap 的狀態差異。重新驗證後分類處置；需要修改者另列 boundary 與核准關卡，
不得把評估完成當成已修正。規則問題只交付 rule_change，不由專案對話處理。

## New-session resume checklist

1. Verify canonical cwd, Git root, branch, HEAD and dirty state.
2. Read `AGENTS.md`, this snapshot, `active_contracts.md`, roadmap, and the task-owning document.
3. Report resumable task, stale/conflicting state, and next gate before execution.
4. Classify task/model/mode and show the scope tree before modification.
5. Replace this snapshot on the next `/handoff`, active-task switch, pause/block, or closure.

## Closure slimming

After an item closes, remove its implementation history from this file. Keep only the next active task, phase, mode,
approved boundary, next owner and stop point. Commit history, closed contracts and validation documents preserve history.
