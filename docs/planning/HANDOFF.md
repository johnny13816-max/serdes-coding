# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-07 Asia/Taipei
Source branch: main
Source revision: ALG-005 closure boundary on origin/main; see latest Git commit
Active task: CP-BR; Stage 1 next review is ALG-006
Current phase: ALG-005 retired as fixed/input-dispatch behavior; ready to introduce ALG-006 Out-of-measured transfer
Collaboration mode: Co-Build branch review
Approved boundary: none for ALG-006; review introduction and evidence-boundary definition only.
Completed: ALG-001, ALG-002, ALG-003, ALG-004, EXE-001, ALG-011, NUM-003, NUM-004 and NUM-005. Former NUM-001, NUM-002 and ALG-005 retired as non-branch behaviors.
In progress: none; ALG-006 review has not started.
Blocked: none.
Next recommended action: introduce ALG-006 Out-of-measured transfer in plain language, then restate cosine-decay／zero-padding semantics, scalar H21 owner, reference evidence and impact boundary.
Next action owner: Codex presents the ALG-006 review introduction; user confirms the review boundary.
Stop point: do not modify ALG-006 or another pending control before its review contract is approved.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/models/178A/call_tree.md;
                docs/planning/178A_algorithm_branch_matrix.xlsx; tests/test_com_model_178A_golden.py
Dirty-state summary: clean after ALG-005 implementation and closure-document commits.
```

ALG-005 closure evidence: owner fixed at `_build_channel_under_test()`；D3.2
S4P path is mandatory, native S2P is strict input representation dispatch, and
the selector has no compatibility alias；focused tests `52 passed`；9 tracked
178A case/template workbooks have selector matches 0 and the branch matrix has formula errors 0；
fixed SiCoPR golden `1 passed`，
`COM_DFE=1.5247607834259893 dB` and final `COM=2.895898684873246 dB` unchanged.

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
