# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-05 Asia/Taipei
Source branch: main
Source revision: E-003 closure commit on main (current HEAD)
Active task: CP-BR; next item E-004 PMF mass-retention review
Current phase: E-003 closed; E-004 introduction not started
Collaboration mode: Co-Build branch review
Approved boundary: E-003 separates ADC-input and final PMF-grid numerical controls while retaining
                   their existing resolver owners. E-004 retains separate PMF mass control.
Completed: B-008, B-010/B-011, B-012 and E-003; B-013 is closed no-code/config-migrated with E-003.
In progress: none; E-004 has not entered technical review.
Blocked: none.
Next recommended action: introduce E-004 in plain language, then show its scope tree, branch options,
                         coding layer, current project behavior and SiCoPR evidence.
Next action owner: Codex presents E-004 review opening; user decides its contract.
Stop point: do not modify `pmf_keep_mass` or its consumers before E-004 approval.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/models/178A/stages/pre_dte.md;
                docs/models/178A/stages/post_ffe.md; docs/planning/e003_pmf_grid_numerical_control.md;
                tests/test_com_model_178A_policy_branches.py; tests/test_com_model_178A_golden.py
Dirty-state summary: clean after the E-003 closure commit/push.
```

E-003 closure evidence: focused policy/text tests `37 passed`; fixed SiCoPR golden
`COM_DFE=1.5247607834259893 dB` and final `COM=2.895898684873246 dB` unchanged.
Workbook inspection confirms eight canonical grid fields, no legacy run-level shared grid rows,
and no formula errors. E-004 `pmf_keep_mass` remains excluded and unmodified.

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
