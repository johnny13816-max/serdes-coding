# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-12 Asia/Taipei
Source branch: main
Source revision: current main plus the isolated SRCH-001 closure commit
Active task: CP-BR ownership second review — ALG-008
Current phase: ALG-002／003／004／006／007, NUM-003 and SRCH-001 are Closed; ALG-008 is next
Collaboration mode: Co-Build architecture review
Approved boundary: coding layers are COM root, L0 stage set, L1 stage, L2 function set, L3 functional block, L4 model auxiliary, L5 generic utility/kernel. A branch owner is the lowest layer that unavoidably must know the selected behavior; ownership is not fixed at L3.
Completed: SRCH-001 second review and code convergence establish Stage 3 L2 COM.calculate_sampling_phase() as the sole selector owner.
SRCH-001 boundary: owner resolves each_phase/coarse_fine and stride, generates visited phases, records per-phase MSE/errors, and returns one strict-minimum-MSE complete bundle. Exact ties retain the earlier candidate; COMMainCursorError skips only that phase.
Implemented change: _run_once() only calls the L2 owner and atomically commits its returned bundle. Index helpers receive concrete method/stride/per_ui and do not read project config. calculate_pos_candidate() and Stage 4 remain fixed evaluators/non-owners.
Independent future idea: adaptive Stage 1 short/long response-grid classification is recorded in future_ideas.md and isolated in commit a9ab622. It has no branch ID and must not be coupled to NUM-003.
In progress: ALG-008 second ownership review has not started source mapping.
Paused: NUM-006 remains paused. Prior ADC-only/global-PMF owner proposals remain undecided.
Blocked: none.
Next recommended action: map ALG-008 clipping selector resolution, V_qc/delta/S_qn/R_n consumers, and verify its current Stage 3 owner boundary.
Next action owner: Codex performs read-only source/consumer review and presents required changes before implementation.
Post-review cleanup: after every second-review branch is complete, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: do not modify ALG-008 until its owner/scope conclusion is discussed or explicitly approved; do not resume NUM-006 until all second-review branches are complete.
SRCH-001 evidence: static ownership test permits selector reads only in calculate_sampling_phase(); focused 53 passed; SiCoPR golden 1 passed with selected phase, MSE, COM values and three stage digests unchanged. Initial focused run had 9 fixture-setup errors solely because sandbox system Temp could not create pytest directories; the same selection passed with workspace --basetemp.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/call_tree.md;
                docs/models/178A/stages/sampling_phase.md;
                src/serdes_coding/models/com_model_178A.py
Dirty-state summary: SRCH-001 implementation, tests and authoritative documentation are ready for isolated commit.
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
