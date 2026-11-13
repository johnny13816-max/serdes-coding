# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-13 Asia/Taipei
Source branch: main
Source revision: current main includes the SRCH-001 Stage 3 ownership correction and restored Stage 1–7 navigation labels
Active task: CP-BR complete initial branch review — NUM-006
Current phase: prior Closed items stay closed; every remaining item is reviewed from eligibility without relying on first/second-review labels
Collaboration mode: Co-Build architecture review
Approved boundary: Stage 1–7 are retained as runtime-sequence/navigation labels but are not ownership coordinates. Use COM root runtime flow separately from Stage-numbered L1 domain/control function sets, then functional blocks and operations/helpers. Dataclass/physical goal defines domain ownership; loop/caller relationships do not transfer ownership.
Completed: SRCH-001 is owned by the complete L1 Stage 3 control block intentionally exposed in COM._run_once(); it controls phase sweeping and the locking point. Extraction would hide Pre-DTE/DTE domains or create a callback-only wrapper.
SRCH-001 structure: one shared initial/fine phase-batch loop directly calls calculate_pre_dte_imp_at_pos() and calculate_MMSE_DTE(); calculate_pos_candidate()/calculate_sampling_phase() were removed. COMRunStatus retains only the four diagnostic fields needed by mse_by_pos.png; PMF controls are read from cfg.num. prepare_pre_dte_phase_inputs() belongs to the Pre-DTE model.
SRCH-001 evidence: current focused Stage 3/status/reporting/policy 63 passed; previously established fixed SiCoPR golden 1 passed remains applicable. Static ownership audit finds only _run_once reads the selector fields. Numerical formulas and branch choices are unchanged.
Completed: ALG-010 full initial review retains heuristic/simplified/spec-defined; L3 COM_MMSE_DTE is semantic owner and COM_MMSE_DTE.run() is the concrete callable owner. Production code required no change.
ALG-010 boundary: COM.calculate_MMSE_DTE() only injects cfg.alg.floating_mode; the three strategy helpers are executors. The owner controls dispatch and the complete placement solve/limit/MSE/status lifecycle. Equal-score tie-break was explicitly outside this closure.
ALG-010 evidence: focused 7 passed covers the sole operational selector read, unique dispatch for all three strategies, N_wg=0 bypass under all modes, and coherent COMDTEStatus; combined policy run is 42 passed. Production numerical path is unchanged, so golden was not rerun and no equation/spec-equivalence claim is made.
Independent future idea: adaptive Stage 1 short/long response-grid classification is recorded in future_ideas.md and isolated in commit a9ab622. It has no branch ID and must not be coupled to NUM-003.
In progress: NUM-006 is next and has not begun technical review.
Queued: ALG-011–017 also require the same complete initial-review process; their historical approved/owner labels are not authoritative.
Blocked: none.
Next recommended action: begin NUM-006 from eligibility and map every production consumer of cfg.num.pmf_keep_mass before discussing ownership.
Next action owner: Codex performs read-only source/consumer review and presents required changes before implementation.
Post-review cleanup: after every remaining complete initial review is closed, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: NUM-006 remains read-only until eligibility, scope, options, owner and validation contract are discussed and explicitly approved.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/stages/mmse_dte.md;
                docs/validation/mmse_input_akinwale_178A.md;
                docs/planning/active_contracts.md
Dirty-state summary: clean after the isolated SRCH-001 Stage 3 ownership and COMRunStatus diagnostic-boundary correction commit.
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
