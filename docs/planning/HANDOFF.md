# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: IDLE
Generated at: 2026-11-17 Asia/Taipei
Source branch: main
Source revision: local main and origin/main at 5ad6845 (Boundary B disposition execution)
Active task: none — Boundary B deletion slice completed and integrated 2026-11-17
Current phase: approved document dispositions and lifecycle registry reconciliation complete
Collaboration mode: project maintenance
Approved boundary: none.
Completed: 已刪除 manifest 核准的三項 legacy/superseded 文件；registry、execution evidence、commit 與 origin/main 已同步。
Current issue: 既有 adaptive-grid technical-document changes 仍保留為未提交 hunks，未納入 Boundary B commit。
Queued: broader branch-review 文件收斂；RC-20261115-001 由規則專用對話確認 closure。
Blocked: none.
Next recommended action: 先核對既有 adaptive-grid dirty hunks 的 owner／validation，再決定是否形成獨立 technical-document commit。
Next action owner: 使用者選定技術文件收斂或規則 closure；Codex 依所選 boundary 執行。
Stop point: 不得將既有 adaptive-grid hunks 與規則 closure 或其他 project-maintenance commit 混合。
Evidence links: docs/document_registry.md;
                docs/planning/document_disposition_manifest.md;
                commit 5ad6845
Dirty-state summary: branch registry、com_dfe、post_ffe、active_contracts 與 future_ideas 有既有未提交修改；preserve and isolate before commit.
```

93A、reporting、C2M migration 與 release 項目維持暫停。本次 utility closure 不構成
COM 數值驗證或 v1.0 release claim。

## New-session resume checklist

1. Verify canonical cwd, Git root, branch, HEAD and dirty state.
2. Read `AGENTS.md`, this snapshot, `active_contracts.md`, roadmap, and the task-owning document.
3. Report resumable task, stale/conflicting state, and next gate before execution.
4. Classify task/model/mode and show the scope tree before modification.
5. Replace this snapshot on the next `/handoff`, active-task switch, pause/block, or closure.

## Closure slimming

After an item closes, remove its implementation history from this file. Keep only the next active task, phase, mode,
approved boundary, next owner and stop point. Commit history, closed contracts and validation documents preserve history.
