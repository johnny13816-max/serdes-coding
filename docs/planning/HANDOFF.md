# HANDOFF

本文件由專案層級 `/handoff` command 寫入；每個新對話第一次處理本 repository 時依 `AGENTS.md` 自動讀取。
它只保存跨對話所需的最小即時狀態，Git、tracker 與 authoritative docs 才是事實來源。恢復工作時先核對，
不得只憑此文件執行。維持約 30–40 行內，完成或失效內容應刪除而非累積歷史。

```text
Handoff state: ACTIVE
Generated at: 2026-11-13 Asia/Taipei
Source branch: main
Source revision: current main includes the isolated NUM-006 owner-validation and documentation closure
Active task: CP-BR complete initial branch review — ALG-011
Current phase: prior Closed items stay closed; every remaining item is reviewed from eligibility without relying on first/second-review labels
Collaboration mode: Co-Build architecture review
Approved boundary: Stage 1–7 are retained as runtime-sequence/navigation labels but are not ownership coordinates. Use COM root runtime flow separately from Stage-numbered L1 domain/control function sets, then functional blocks and operations/helpers. Dataclass/physical goal defines domain ownership; loop/caller relationships do not transfer ownership.
Completed: NUM-006 keeps project 1-1e-5 and reference 1.0. L5 public Pmf1D.fir_filter() is the owner; after each tap convolution it symmetrically truncates to the target retained mass and renormalizes. Value 1.0 disables truncation.
NUM-006 boundary: Stage 2 Pre-DTE and Stage 5 Post-FFE are direct consumers. _resolve_adc_input_pmf_config() only injects the value and private _truncate_keep_mass() only executes it. Stage 6 final PMF fixes keep_mass=1.0 and is not a branch consumer. Grid spacing, projection, PDF discretization, clipping and PSD record controls stay independent.
NUM-006 evidence: public owner now rejects non-finite or out-of-range values; legal-input numerical behavior, project/reference values and Stage flows are unchanged. Focused PMF/policy suite 53 passed; golden was not rerun.
Independent future idea: adaptive Stage 1 short/long response-grid classification is recorded in future_ideas.md and isolated in commit a9ab622. It has no branch ID and must not be coupled to NUM-003.
In progress: ALG-011 is next and has not begun technical review.
Queued: ALG-011–017 require the same complete initial-review process; their historical approved/owner labels are not authoritative.
Blocked: none.
Next recommended action: begin ALG-011 by mapping current rxffe_record_realization options and every production consumer.
Next action owner: Codex presents the ALG-011 eligibility/scope review before any new implementation.
Post-review cleanup: after every remaining complete initial review is closed, remove all legacy branch IDs, legacy mappings and historical branch records from current authoritative/active documents; retain only the current branch design. Git history is not rewritten.
Stop point: ALG-011 remains read-only until eligibility, scope, options, owner and validation contract are discussed and explicitly approved.
Evidence links: docs/models/178A/branch_behavior_registry.md;
                docs/models/178A/stages/pre_dte.md;
                docs/models/178A/stages/post_ffe.md;
                docs/planning/active_contracts.md
Dirty-state summary: clean after the isolated NUM-006 owner-validation and documentation closure commit.
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
