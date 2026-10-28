# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: READY
Generated at: 2026-10-28 Asia/Taipei
Source branch: main
Source revision: HEAD containing the handoff-rule update and this snapshot
Active task: project-governance rule validation through user Q&A
Current phase: handoff mechanism implemented; current session must stop after verification
Collaboration mode: Full-Agent for governance documentation
Approved boundary: governance/rule documents only; no code or COM-model changes
Completed: layered governance, task/model taxonomy, collaboration modes, structure-first communication,
           active-item document lifecycle, and explicit /handoff write/new-session read behavior
In progress: none after this snapshot
Blocked: none
Next recommended action: continue project-rule Q&A in a new conversation; alternatively resume 178A P3 review
Next action owner: user selects the next question or task in the new conversation
Stop point: do not begin 93A work, protected COM changes, or another task in this session
Evidence links: AGENTS.md; docs/architecture/project_workflow.md;
                docs/architecture/collaboration_contract.md; docs/planning/v1_0_roadmap.md
Dirty-state summary: pre-existing reference_data deletions/additions and results/ remain outside governance scope
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
