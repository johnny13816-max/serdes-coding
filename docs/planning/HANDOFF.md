# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-17 Asia/Taipei
Source branch: main
Source revision: local main includes the isolated CP-BR closure boundary; origin/main 45dae92; remote sync pending
Active task: CP-BR branch review closure integration
Current phase: Review complete; authoritative state and local boundary are complete; remote integration pending
Collaboration mode: Co-Build architecture review
Approved boundary: Stage 1–7 are retained as runtime-sequence/navigation labels but are not ownership coordinates. Use COM root runtime flow separately from Stage-numbered L1 domain/control function sets, then functional blocks and operations/helpers. Dataclass/physical goal defines domain ownership; loop/caller relationships do not transfer ownership.
Completed: ALG-012 review closed in 2db1646; its S_in zero-coefficient question was explicitly deferred. NUM-009 implementation 15823b6 and review closure 45dae92 are on origin/main.
Completed: production selectors、retired behaviors、registry ownership 與既有 validation evidence 已逐一核對；未發現新的未審 selectable behavior。ALG-012 tracker 已依 bounded closure evidence 收斂；active state 與 roadmap 已移除過期 next-task 結論。
Current issue: unrelated adaptive-grid、rule lifecycle 與 plot normalization dirty changes remain preserved and excluded from the CP-BR closure boundary。
Queued: CP-BR 沒有剩餘 branch review；P4–P8 非 branch 章節維持暫停，等待使用者選定下一目標。
Blocked: remote integration pending。Local main 比 `origin/main` 多五個既有 rule commits（`b200d8e`…`b536855`）；未取得一併 push 的明確授權前不得推送。
Next recommended action: resolve whether the five prior rule commits and the CP-BR closure commit may be pushed together。
Next action owner: 使用者決定 remote authorization；Codex 執行獲准的 push 與 remote verification。
Stop point: campaign state is Review complete；do not mark remote sync complete until `origin/main` contains the closure commit.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/stages/pre_dte.md;
                docs/models/178A/stages/post_ffe.md;
                docs/planning/active_contracts.md
Dirty-state summary: multiple pre-existing code and documentation changes plus untracked files; preserve them. Inspect git status and isolate task-specific hunks before any commit.
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
