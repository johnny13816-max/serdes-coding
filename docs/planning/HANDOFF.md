# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-12 Asia/Taipei
Source branch: main
Source revision: 82636b8 plus isolated future-idea commit a9ab622; this snapshot is committed by the NUM-003 closure commit
Active task: CP-BR ownership second review — SRCH-001
Current phase: ALG-002／003／004／006／007 and NUM-003 are Closed; SRCH-001 source/consumer ownership review begins
Collaboration mode: Co-Build architecture review
Approved boundary: coding layers are COM root, L0 stage set, L1 stage, L2 function set, L3 functional block, L4 model auxiliary, L5 generic utility/kernel. A branch owner is the lowest layer that unavoidably must know the selected behavior; ownership is not fixed at L3.
Completed: NUM-003 second review confirms the shared L3 impairment-record realization block as semantic owner. Its L4 functions are _resolve_eq_ch_imp_record_cfg(), _resolve_post_ffe_imp_record_cfg(), _realize_eq_ch_imp_record(), and _build_eq_ch_imp_psd().
NUM-003 boundary: full preserves the complete source record for PSD construction; truncated crops or zero-pads to num_trunc_ui. It does not change Stage 1 responses, XT phase selection, RX FFE solve, or ALG-011 response realization/grid.
Implemented change: NUM-003 production behavior and config unchanged; ownership documentation only.
Independent future idea: adaptive Stage 1 short/long response-grid classification is recorded in future_ideas.md and isolated in commit a9ab622. It has no branch ID and must not be coupled to NUM-003.
In progress: SRCH-001 second ownership review has not started source mapping.
Paused: NUM-006 remains paused. Prior ADC-only/global-PMF owner proposals remain undecided.
Blocked: none.
Next recommended action: map SRCH-001 each_phase/coarse_fine selector resolution, visited-phase generation, Stage 4 consumption, and profile/workbook parameters.
Next action owner: Codex performs read-only source/consumer review and presents required changes before implementation.
Post-review cleanup: after every second-review branch is complete, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: do not modify SRCH-001 until its owner/scope conclusion is discussed or explicitly approved; do not resume NUM-006 until all second-review branches are complete.
NUM-003 evidence: existing policy tests cover full identity, 4096-UI truncation, short-record zero-padding, conditional parameter validation, and full/truncated ALG-011 grid interaction. Prior fixed evidence remains 187 passed, 1 deselected, 2 subtests passed; production code was unchanged, so no baseline rerun was required.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/call_tree.md;
                docs/models/178A/stages/pre_dte.md;
                docs/models/178A/stages/post_ffe.md;
                docs/planning/tc022_mmse_noise_grid.md;
                src/serdes_coding/models/com_model_178A.py
Dirty-state summary: NUM-003 closure documentation only; no production-code change is pending.
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
