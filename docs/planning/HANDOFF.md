# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-10 Asia/Taipei
Source branch: main
Source revision: local main after the CFG-178A A--F integration commit; not pushed
Active task: CP-BR — paused before NUM-006
Current phase: CFG-178A closed; waiting to resume NUM-006 boundary review
Collaboration mode: Co-Build architecture review
Approved boundary: one COM instance receives one resolved COMConfig; adapter selects run mode before construction; search orchestration remains outside COM; L3 owners read domain-qualified config directly.
Completed: ALG-009 retirement and prior CP-BR closures remain unchanged.
In progress: none; CFG-178A integration is complete.
Paused: NUM-006; prior ADC-only and global-PMF owner proposals are not accepted decisions.
Blocked: none.
Next recommended action: resume NUM-006 from production-consumer mapping and define its true owner boundary before any implementation.
Next action owner: user starts or approves the resumed NUM-006 discussion.
Stop point: do not implement or rename NUM-006 before its consumer scope and owner are reviewed.
Evidence links: docs/architecture/configuration_architecture.md;
                docs/architecture/branch_behavior_contract.md;
                docs/planning/comconfig_domain_migration.md;
                docs/models/178A/config_tree.md
Dirty-state summary: CFG-178A A--F is integrated as one local commit and the worktree is expected clean after this handoff update is amended. F removed runtime aliases and the converter draft `group` vocabulary, moved profile/override metadata out of `cfg.alg` into export-only adapter resolution, aligned split-search script/workflow/GUI paths, and revised architecture tests for intentional 178A source/path/search ownership. Eight populated cases load in all modes; partial-search smoke passed; focused integration `136 passed`, `3 deselected`, `2 subtests passed`; external-temp provenance `2 passed`; Python 3.7 validator and compileall passed. The three deselected converter tests require absent local-only Ad Hoc workbooks. Fixed SiCoPR golden `1 passed` with MSE `0.0061912610245255335`, COM_DFE `1.5247607834259893 dB`, final COM `2.895898684873246 dB`, and frozen digests unchanged. Formulas, ranking and NUM-006 remain unchanged.
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
