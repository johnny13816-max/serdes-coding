# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-09 Asia/Taipei
Source branch: main
Source revision: ALG-009 retirement 5dd16f8 on origin/main
Active task: CP-BR; Stage 3 next review is NUM-006
Current phase: ALG-009 retired; ready to introduce NUM-006 PMF retained-mass control
Collaboration mode: Co-Build branch review
Approved boundary: none for NUM-006; review introduction and evidence-boundary definition only.
Completed: ALG-001, ALG-002, ALG-003, ALG-004, ALG-006, ALG-007, ALG-008, EXE-001, ALG-011, NUM-003, NUM-004 and NUM-005. Former NUM-001, NUM-002, ALG-005 and ALG-009 retired as non-branch behaviors.
In progress: none; NUM-006 review has not started.
Blocked: none.
Next recommended action: introduce NUM-006 `pmf_keep_mass` in plain language, then confirm cost/accuracy semantics, owner, affected PMF convolutions and reference setting.
Next action owner: Codex presents the NUM-006 review introduction; user confirms the review boundary.
Stop point: do not modify NUM-006 or another pending control before its review contract is approved.
Evidence links: docs/models/178A/branch_behavior_registry.md; docs/models/178A/call_tree.md;
                docs/models/178A/stages/pre_dte.md; tests/test_com_model_178A_golden.py
Dirty-state summary: expected clean after ALG-009 closure snapshot commit.
```

ALG-009 closure evidence: `_build_psd_adc_qn()` 固定直接執行 exact PMF；
`pre_dte_pmf_method` 已從 runtime config 與 tracked workbook 移除。Legacy
`pmf_exact` row 可讀，`gaussian_approx` 明確拒絕。Focused tests `45 passed`；
fixed SiCoPR golden `1 passed`，pre-DTE `V_qc=0.04162 V`、
`delta=0.0013212698412698415 V`、MSE `0.0061912610245255335`、
`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。
Implementation `5dd16f8` 已推送至 `origin/main`。

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
