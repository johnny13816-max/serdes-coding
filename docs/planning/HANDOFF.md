# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: IDLE
Generated at: 2026-11-17 Asia/Taipei
Source branch: main
Source revision: local main and origin/main include plot_ir normalization boundary 7bd6a19 and this closure-state reconciliation
Active task: none — plot_ir normalization boundary Closed 2026-11-17
Current phase: implementation, focused validation, contract documentation and remote integration complete
Collaboration mode: Co-Build architecture review
Approved boundary: none — the plot_ir normalization boundary is closed; adjacent adaptive-grid and rule-lifecycle changes remain excluded.
Completed: `LinkSegment.plot_ir()` 可選 display-only main-cursor normalization；`SparamModel.plot_ir()` 轉發選項。原 IR／TF state 不變，精確零值或非有限尺度報錯，focused tests 5/5 passed。
Current issue: unrelated adaptive-grid 與 rule lifecycle dirty changes remain preserved and excluded from this boundary。
Queued: none — 等待使用者選定下一個獨立目標。
Blocked: none.
Next recommended action: 使用者選定下一個非 branch review、reporting、93A、C2M 或 release 目標後另立 boundary。
Next action owner: 使用者選擇目標；Codex 執行對應 preflight。
Stop point: plot_ir normalization 已關閉；不得自動納入 adaptive-grid、rule lifecycle、P4–P9、93A、reporting 或 C2M migration。
Evidence links: docs/architecture/contract_migration_inventory.md;
                tests/test_plot_ir_normalization.py
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
