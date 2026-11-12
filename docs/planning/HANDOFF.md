# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-12 Asia/Taipei
Source branch: main
Source revision: current main plus the isolated ALG-008 closure commit
Active task: CP-BR ownership second review — NUM-004
Current phase: ALG-002／003／004／006／007／008, NUM-003 and SRCH-001 are Closed; NUM-004 is next
Collaboration mode: Co-Build architecture review
Approved boundary: coding layers are COM root, L0 stage set, L1 stage, L2 function set, L3 functional block, L4 model auxiliary, L5 generic utility/kernel. A branch owner is the lowest layer that unavoidably must know the selected behavior; ownership is not fixed at L3.
Completed: ALG-008 second review confirms Stage 2 L3 COM._build_pre_dte_psd() as the sole selector owner; required correction is documentation-only ownership relocation.
ALG-008 boundary: owner selects full-jitter/P_qc/2 or RJ-only/P_qc clipping input, calls fixed exact-PMF/quantization helpers, and forms S_total/R_n with full jitter retained for MMSE.
Non-owners: calculate_pre_dte_imp_at_pos() is the per-phase caller; _build_psd_adc_qn() and _calculate_V_qc() consume concrete sigma_ga/cdf_tail; Stage 4 and reporting only consume results.
Independent future idea: adaptive Stage 1 short/long response-grid classification is recorded in future_ideas.md and isolated in commit a9ab622. It has no branch ID and must not be coupled to NUM-003.
In progress: NUM-004 second ownership review has not started source mapping.
Paused: NUM-006 remains paused. Prior ADC-only/global-PMF owner proposals remain undecided.
Blocked: none.
Next recommended action: map NUM-004 ADC-input PMF-grid resolution, direct consumers, status evidence, and independence from NUM-005/006.
Next action owner: Codex performs read-only source/consumer review and presents required changes before implementation.
Post-review cleanup: after every second-review branch is complete, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: do not modify NUM-004 until its owner/scope conclusion is discussed or explicitly approved; do not resume NUM-006 until all second-review branches are complete.
ALG-008 evidence: AST selector-read audit found only _build_pre_dte_psd(); current focused 2 passed. Production path is unchanged, so golden was not rerun; prior fixed golden evidence remains applicable.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/call_tree.md;
                docs/models/178A/stages/pre_dte.md;
                docs/planning/tc017_pre_dte_adc_clipping_reference.md;
                src/serdes_coding/models/com_model_178A.py
Dirty-state summary: ALG-008 authoritative documentation and one source comment are ready for isolated commit.
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
