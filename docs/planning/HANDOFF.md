# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-05 Asia/Taipei
Source branch: main
Source revision: 6d0c7df
Active task: CP-BR E-003 pre-DTE PMF grid numerical-control review
Current phase: normal review; define reference behavior, scope, and override semantics
Collaboration mode: Co-Build branch review
Approved boundary: B-013 is closed no-code. E-003 owns pre-DTE/selected-phase ADC-input grid
                   resolution and explicit dy override; E-004 retains separate PMF mass control.
Completed: B-008, B-010/B-011 and B-012 are remote-synced; B-013 is closed no-code.
In progress: compare project coarse/fine/explicit dy behavior with SiCoPR pre-DTE `OP.BinSize`.
Blocked: none.
Next recommended action: decide whether the reference profile should use a derived grid or explicit fixed dy.
Next action owner: User selects E-003 reference-alignment behavior after evidence review.
Stop point: do not modify pre-DTE runtime controls before the E-003 decision.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/models/178A/stages/pre_dte.md;
                docs/models/178A/stages/post_ffe.md;
                tests/test_com_model_178A_policy_branches.py
Dirty-state summary: B-013 closure record pending this documentation commit; no production-code change.
```

B-013 closed with no production change: SiCoPR `dy≈5.3743 uV` maps through the
project's unnormalized post-FFE gain to `≈316.667 uV`, exactly `relative_As`.
E-003 now reviews the separate pre-DTE grid consumers; E-004 `pmf_keep_mass` is excluded.

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
