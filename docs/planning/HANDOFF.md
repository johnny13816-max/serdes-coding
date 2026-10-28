# HANDOFF

本文件只保存跨對話所需的最小即時狀態；Git、tracker、authoritative docs 才是事實來源。恢復工作時先
重新核對，不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Active task: none — coding implementation intentionally paused for governance redesign
Current phase: v1.0 platform review; P2 version decoupling complete, P3 configuration/workbook review next
Collaboration mode: unset until next task is selected
Approved boundary: no active code-change contract
Next action owner: user selects the next v1.0 review item in a new conversation
Stop point: do not start 93A work or protected COM changes before 178A platform review resumes and is reconciled
```

## Resume checklist

1. Verify canonical cwd, Git root, branch and dirty state.
2. Read `AGENTS.md`, `docs/architecture/project_workflow.md`, and the task-owning document.
3. Reconcile `open_issues.xlsx`, `active_contracts.md`, `v1_0_roadmap.md`, and current Git history.
4. Classify task/model/mode and show the scope tree before modification.
5. Replace this handoff block when the active task changes.

## Closure slimming

After an item closes, remove its implementation history from this file. Keep only the next active task, phase, mode,
approved boundary, next owner and stop point. Commit history, closed contracts and validation documents preserve history.
