# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-11 Asia/Taipei
Source branch: main
Source revision: 114e7bf; this snapshot is committed by the ALG-004 closure-state commit
Active task: CP-BR ownership second review — ALG-006
Current phase: ALG-002, ALG-003 and ALG-004 are Closed; ALG-006 source/consumer ownership review begins
Collaboration mode: Co-Build architecture review
Approved boundary: coding layers are COM root, L0 stage set, L1 stage, L2 function set, L3 functional block, L4 model auxiliary, L5 generic utility/kernel. A branch owner is the lowest layer that unavoidably must know the selected behavior; ownership is not fixed at L3.
Completed: ALG-004 is Closed. L5 Pmf1D.scale_x() is the confirmed owner; Stage 7 _build_scaled_total_pdf_added_noise() and calculate_der_mlsd() are direct injectors. Signed interpolate_ordinates uses one abs(scale) grid and mirrors negative ordinates. Implementation/docs 114e7bf is pushed. ALG-002 and ALG-003 remain Closed.
In progress: ALG-006 second ownership review. Current registry proposal is L5 resample_tf(); analysis-grid H21, bilinear finite records and victim TX-noise consumers require source confirmation.
Implemented change: none pending for ALG-006.
Paused: NUM-006 remains paused. Prior ADC-only/global-PMF owner proposals remain undecided.
Blocked: none.
Next recommended action: map all ALG-006 production consumers and distinguish out-of-measured policy ownership from case frequency-limit input.
Next action owner: Codex performs read-only source/consumer review and presents required changes before implementation.
Post-review cleanup: after every second-review branch is complete, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: do not modify ALG-006 until its owner/scope conclusion is discussed or explicitly approved; do not resume NUM-006 until all second-review branches are complete.
Validation completed: ALG-002 focused 47 passed and fixed golden passed. ALG-003 focused 47 passed; Python 3.7 export validation passed; fixed SiCoPR golden 1 passed with existing MSE/COM_DFE/final-COM tolerances and all three digests passing. Initial ALG-003 focused run had 7 Temp setup errors; the identical suite passed with a dedicated percent-TEMP basetemp.
ALG-004 focused PMF/MLSD/profile tests 49 passed with 2 subtests; Python 3.7 export validation passed; fixed SiCoPR golden 1 passed with existing MSE/COM_DFE/final-COM tolerances and all three digests passing.
Evidence links: docs/architecture/documentation_contract.md;
                docs/architecture/branch_behavior_contract.md;
                docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/call_tree.md;
                src/serdes_coding/utilities/pmf.py;
                src/serdes_coding/models/com_model_178A.py
Dirty-state summary: closure-state documentation only; ALG-004 implementation is integrated and no production-code change is pending.
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
