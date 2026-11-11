# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-11 Asia/Taipei
Source branch: main
Source revision: c804e3c; this snapshot is committed by the ALG-003 closure-state commit
Active task: CP-BR integration — ALG-002
Current phase: ALG-003 second review is Closed; ALG-002 implementation/validation remains integration pending
Collaboration mode: Co-Build architecture review
Approved boundary: coding layers are COM root, L0 stage set, L1 stage, L2 function set, L3 functional block, L4 model auxiliary, L5 generic utility/kernel. A branch owner is the lowest layer that unavoidably must know the selected behavior; ownership is not fixed at L3.
Completed: ALG-003 is Closed. L5 Pmf1D.gaussian()/uniform() is the confirmed owner set; Gaussian support is an independent fixed ±8 sigma invariant. Protected implementation e65f644 is pushed and authoritative documentation c804e3c is committed.
In progress: ALG-002 integration. Its L5 public Pmf1D target-grid operation owner set and focused/golden evidence are confirmed; code/test remain uncommitted.
Implemented change: TC-025 changed Gaussian pmf_sample extent from 2*n_sigma to n_sigma and rebuilt the Python 3.7 export. ALG-002 removed full COMAlgorithmPolicyConfig forwarding from four model helpers in favor of concrete methods.
Paused: NUM-006 remains paused. Prior ADC-only/global-PMF owner proposals remain undecided.
Blocked: none.
Next recommended action: isolate and integrate the validated ALG-002 code/test boundary; then begin ALG-004 second review.
Next action owner: Codex performs scoped ALG-002 diff/staging and closure reconciliation.
Post-review cleanup: after every second-review branch is complete, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: do not mark ALG-002 Closed before traceable isolated integration; do not resume NUM-006 until all second-review branches are complete.
Validation completed: ALG-002 focused 47 passed and fixed golden passed. ALG-003 focused 47 passed; Python 3.7 export validation passed; fixed SiCoPR golden 1 passed with existing MSE/COM_DFE/final-COM tolerances and all three digests passing. Initial ALG-003 focused run had 7 Temp setup errors; the identical suite passed with a dedicated percent-TEMP basetemp.
Evidence links: docs/architecture/documentation_contract.md;
                docs/architecture/branch_behavior_contract.md;
                docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/call_tree.md;
                src/serdes_coding/utilities/pmf.py;
                src/serdes_coding/models/com_model_178A.py
Dirty-state summary: only ALG-002 model-helper code/test changes remain uncommitted; ALG-003 implementation and authoritative documentation are integrated.
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
