# Document disposition manifest

狀態：**Approved disposition — execution deferred to Boundary B**｜2026-11-17

本清單是 RC-20261117-003 的逐檔處置提案。它不改變任何模型、分支或驗證結論。
規則 boundary 只建立分類與 enforcement；實際 planning／branch 文件整理必須在後續
project-maintenance boundary 執行。使用者已於 2026-11-17 選擇方案 1，核准下列三項
全部刪除；Boundary A 只記錄決定，不跨界執行刪除。

## Decision rules

- `Maintain live`：仍擁有現行 state、queue、proposal inventory 或 navigation。
- `Paused`：有未完成 boundary 或明確 resume gate；未恢復前不得更新為 current behavior。
- `Retain historical`：保存 protected decision、dated evidence 或仍具獨有追溯價值；後續統一
  `Historical / non-authoritative` header 與 current-owner link。
- `Delete after confirmation`：沒有獨有 current ownership，內容已被權威 owner 取代；刪除在
  project-maintenance boundary 執行並同步 registry／references。

## Maintain live

| Path | Role / reason |
|---|---|
| `docs/planning/README.md` | planning navigation and lifecycle boundary |
| `docs/planning/active_contracts.md` | sole executable active-boundary state; must be slimmed |
| `docs/planning/future_ideas.md` | unresolved/deferred ideas only; implemented items must leave |
| `docs/planning/HANDOFF.md` | compact session recovery snapshot |
| `docs/planning/NOTES.md` | candidate reusable lessons |
| `docs/planning/open_issues.xlsx` | complete queue/history tracker; workbook contains the maintained Issues table |
| `docs/planning/reference_alignment_contracts.md` | reference-gap issue log and detailed history |
| `docs/planning/rule_changes.md` | rule proposal/decision log |
| `docs/planning/v1_0_rebaseline.md` | separated goals and paused inventory |
| `docs/planning/v1_0_roadmap.md` | platform direction and chapter status |

## Paused — resume only by user selection

| Path | Resume boundary |
|---|---|
| `docs/planning/alg006_out_of_measured_transfer.md` | ALG-006 contract/evidence follow-up |
| `docs/planning/company_platform_cp2_contract_draft.md` | company-platform CP-2 proposal |
| `docs/planning/tc005_pmf_run_grid_policy.md` | PMF run-grid policy integration audit |
| `docs/planning/tc006_channel_high_frequency_policy.md` | high-frequency reference policy audit |
| `docs/planning/tc019_align_to_ref_profile.md` | profile end-to-end acceptance |
| `docs/planning/tc019r_reference_preset_resolution.md` | preset-resolution integration audit |
| `docs/planning/tc021_channel_frequency_limit.md` | channel-frequency-limit integration audit |
| `docs/planning/tc023_mlsd_reference_realization.md` | MLSD reference integration audit |
| `docs/planning/util_eye_001_linksegment_eye.md` | deterministic-eye contract lacks a durable technical owner; promote before freezing or retiring |
| `docs/planning/utility_grid_contract_draft.md` | TC-013 remaining acceptance gates |

## Retain historical / non-authoritative

| Path | Current owner or retained value |
|---|---|
| `docs/planning/178A_adaptive_grid_change_contract.md` | protected adaptive-grid decision; current behavior in 178A registry/stage docs |
| `docs/planning/178a_branch_inventory.md` | TC-019R-era preset expansion history; current branches in 178A registry |
| `docs/planning/alg001_missing_dc_completion.md` | dated ALG-001 closure evidence |
| `docs/planning/alg011_rxffe_record_realization.md` | protected fixed circular-FFE decision record |
| `docs/planning/comconfig_domain_migration.md` | CFG-178A migration decision and validation history |
| `docs/planning/company_platform_cp1_gap_map.md` | dated read-only platform assessment |
| `docs/planning/e003_pmf_grid_numerical_control.md` | implemented PMF-grid decision history |
| `docs/planning/num002_gaussian_support.md` | NUM-002 closure evidence |
| `docs/planning/tc006_out_of_measured_boundary_revision.md` | superseding measured-boundary decision history |
| `docs/planning/tc016_channel_renormalization_order.md` | superseded protected A/B contract |
| `docs/planning/tc017_pre_dte_adc_clipping_reference.md` | protected clipping reference decision |
| `docs/planning/tc018_final_adc_quantization_reference.md` | superseded final-quantization decision history |
| `docs/planning/tc020_ctle_pulse_realization.md` | protected CTLE realization decision history |
| `docs/planning/tc022_mmse_noise_grid.md` | NUM-003 closure history |
| `docs/planning/tc024_mlsd_quantization_psd.md` | protected MLSD quantization decision history |
| `docs/planning/tc025_alg003_gaussian_support.md` | ALG-003 convergence evidence |
| `docs/planning/tc026_alg004_signed_scaling.md` | ALG-004 signed-scaling evidence |
| `docs/planning/util_snp_001_sparam_representation.md` | S-parameter representation implementation contract |

## Delete after user confirmation

| Path | Evidence and replacement | Proposed execution |
|---|---|---|
| `docs/planning/178A_algorithm_branch_matrix.xlsx` | Formula-linked legacy branch matrix; current branch registry owns classification. Workbook inspection also found corrupted legacy text, so it is not a reliable current source. | Delete in branch-document convergence; remove registry row. |
| `docs/planning/company_platform_cpbr_matrix.md` | Header already declares it a retired duplicate of the authoritative branch registry. | Delete in branch-document convergence; remove obsolete references. |
| `docs/planning/temp_contract_short_long_grid_178A.md` | Untracked 1,318-line superseded draft; durable adaptive-grid content is already in the formal contract, stage docs and validation evidence. | Delete only after explicit confirmation; remove `retire-pending` registry row. |

## Coverage gaps recorded, not auto-expanded

- 93A lacks the required branch registry、call tree、status tree and stage documents. This remains a paused
  coverage gap; do not create speculative documents until the user resumes 93A and production source is reviewed.
- `docs/architecture/contract_migration_inventory.md` remains `migration-inventory`; it may only shrink as
  source-checked content moves to current owners.
- `active_contracts.md` currently contains excess closed history. Slimming it and converging branch-review
  documents belong to the separate project-maintenance boundary after this rule boundary closes.
- Existing dirty changes in 178A registry/stage docs、`active_contracts.md`、`future_ideas.md` and the untracked
  adaptive draft are preserved; this rule boundary does not stage or rewrite their project content.
