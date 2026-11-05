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
Current phase: review complete; protected-model implementation contract pending
Collaboration mode: Co-Build branch review
Approved boundary: B-013 is a final DFE/MLSD numerical control. SiCoPR alignment uses
                   `min(As/1000, 10 uV)`; pre-DTE PMF grid behavior remains independent and unchanged.
Completed: B-008, B-010/B-011 and B-012 are committed and remote-synced; obsolete reference data removed.
In progress: define the B-013 Core Model Change Contract for the final-grid profile correction.
Blocked: protected `com_model_178A.py` behavior cannot change before explicit contract approval.
Next recommended action: present and approve the minimal B-013 Core Model Change Contract.
Next action owner: Agent drafts contract; user approves protected-model scope.
Stop point: do not edit the final PMF resolver or reference profile before contract approval.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/models/178A/stages/com_dfe.md;
                tests/test_com_model_178A_policy_branches.py
Dirty-state summary: only rule-session governance changes remain; project changes are committed.
```

B-013 reference evidence confirms that final DFE/MLSD uses the capped relative grid;
the current aligned profile incorrectly selects relative-only spacing. The current fixed-case
COM golden remains the validation baseline; no B-013 production change has been made yet.

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
