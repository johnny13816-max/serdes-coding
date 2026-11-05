# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-06 Asia/Taipei
Source branch: main
Source revision: ALG-011 implementation commit 565ccba on origin/main
Active task: CP-BR; next stage-ordered review not started
Current phase: ALG-011 closed; ready to introduce ALG-012
Collaboration mode: Co-Build branch review
Approved boundary: none for ALG-012; review introduction and boundary definition only.
Completed: ALG-001, ALG-002, ALG-003, ALG-004, ALG-011, NUM-003, NUM-004 and NUM-005. Former NUM-001 retired as non-branch utility behavior.
In progress: none; ALG-012 review has not started.
Blocked: none.
Next recommended action: introduce ALG-012 final-COM V_qc convention in plain language, then show options, impact scope, coding-layer tree and discussion items.
Next action owner: Codex presents the review introduction; user confirms the review boundary.
Stop point: do not modify ALG-012 or another pending control before its review contract is approved.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/planning/alg011_rxffe_record_realization.md;
                docs/models/178A/stages/post_ffe.md; tests/test_com_model_178A_golden.py
Dirty-state summary: clean after this closure-document synchronization.
```

ALG-011 closure evidence: Stage 5 owns all response realization and records its
response/PSD grids；Python 3.7 utility export validator passed；fixed SiCoPR
golden `1 passed`，`COM_DFE=1.5247607834259893 dB` and final
`COM=2.895898684873246 dB` unchanged. Implementation commit `565ccba` is on
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
