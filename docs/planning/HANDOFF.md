# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: IDLE
Generated at: 2026-11-17 Asia/Taipei
Source branch: main
Source revision: local main and origin/main include document lifecycle implementation b147050; closure-state reconciliation follows
Active task: none — RC-20261117-003 document lifecycle boundary Closed 2026-11-17
Current phase: lifecycle registry, enforcement, validation and remote integration complete
Collaboration mode: project maintenance
Approved boundary: none — rule boundary closed; Boundary B must start in a separate project-maintenance conversation.
Completed: 逐檔 lifecycle registry、owner/update/closure 規則、機械性 checker 與 quality gate 已建立；104 筆 registry coverage 驗證通過。
Current issue: unrelated adaptive-grid technical-document changes remain preserved and excluded from the rule boundary。
Queued: Boundary B — 執行已核准的三項刪除，並收斂 branch-review 文件與 active state。
Blocked: none.
Next recommended action: 在獨立 project-maintenance 對話啟動 Boundary B preflight，依 disposition manifest 執行核准處置。
Next action owner: Codex 依使用者已核准 manifest 執行；技術結論改動仍須另行確認。
Stop point: 本規則對話不得執行 Boundary B 刪除或混入既有 adaptive-grid dirty hunks。
Evidence links: docs/document_registry.md;
                docs/planning/document_disposition_manifest.md;
                docs/planning/rule_changes.md#rc-20261117-003--document-lifecycle-registry-and-enforcement
Dirty-state summary: multiple pre-existing code and documentation changes plus untracked files; preserve them. Inspect git status and isolate task-specific hunks before any commit.
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
