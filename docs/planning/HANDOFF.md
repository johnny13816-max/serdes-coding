# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-05 Asia/Taipei
Source branch: main
Source revision: ALG-001 implementation commit 7c256b2 on origin/main
Active task: CP-BR; next stage-ordered review not started
Current phase: ALG-001 closed; ready to introduce NUM-001
Collaboration mode: Co-Build branch review
Approved boundary: none for NUM-001; review introduction and boundary definition only.
Completed: ALG-001, ALG-002, ALG-003, ALG-004, NUM-004 and NUM-005.
In progress: none; NUM-001 review has not started.
Blocked: none.
Next recommended action: introduce NUM-001 in plain language, then show options, impact scope and discussion items.
Next action owner: Codex presents the review introduction; user confirms the review boundary.
Stop point: do not modify NUM-001 or another pending control before its review contract is approved.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/planning/alg001_missing_dc_completion.md;
                docs/models/178A/stages/path_construction.md; tests/test_com_model_178A_golden.py
Dirty-state summary: ALG-001 closure-document update pending one documentation-only commit.
```

ALG-001 closure evidence: focused tests `59 passed`; Python 3.7 utility export
validator passed；fixed SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`
and final `COM=2.895898684873246 dB` unchanged. Boundary commit `7c256b2` is on
`origin/main`.

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
