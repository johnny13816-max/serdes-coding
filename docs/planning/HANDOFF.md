# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-05 Asia/Taipei
Source branch: main
Source revision: a1dbc2d
Active task: CP-BR B-013 final PMF grid numerical-control review
Current phase: review complete; evidence supports no production change
Collaboration mode: Co-Build branch review
Approved boundary: B-013 is a final DFE/MLSD numerical control. SiCoPR's grid is mapped
                   into the project's unnormalized post-FFE voltage domain; pre-DTE remains independent.
Completed: B-008, B-010/B-011 and B-012 are committed and remote-synced; obsolete reference data removed.
In progress: user closure decision for B-013; no Core Model Change Contract is warranted.
Blocked: none.
Next recommended action: close B-013 as no-code alignment and introduce the next branch review.
Next action owner: User confirms B-013 closure.
Stop point: do not change the correct `relative_As` reference-profile selection.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/models/178A/stages/com_dfe.md;
                tests/test_com_model_178A_policy_branches.py
Dirty-state summary: only rule-session governance changes remain; project changes are committed.
```

B-013 reference evidence confirms that SiCoPR `A_s≈5.3743 mV` resolves `dy≈5.3743 uV`.
Mapping through the project's unnormalized post-FFE gain gives `dy≈316.667 uV`, exactly
the current `relative_As` setting. Applying the project-domain `10 uV` cap would not align.

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
