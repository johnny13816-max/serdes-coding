# Document lifecycle registry

狀態：**authoritative lifecycle inventory**。本表只擁有文件 metadata，不擁有各文件內的
技術結論。Lifecycle 定義、transition 與 closure gate 見
[Documentation contract](architecture/documentation_contract.md#lifecycle-registry)。

## Registry contract

- Coverage：Git 追蹤的 `AGENTS.md`、repository `README.md`、`docs/**/*.md`、
  `docs/**/*.xlsx` 必須各有一筆。
- `owner=self` 表示該文件仍擁有自身內容；其他 path 表示 current content owner。
- `historical-frozen` 只保存 dated evidence／decision history，不作為 current behavior。
- `paused-temporary` 只有使用者恢復對應 boundary 才可更新。
- 新增、改名、搬移、改 lifecycle 或 disposition 時，在同一 commit 更新本表。
- 機械性驗證：`python scripts/check_document_lifecycle.py`。

## Lifecycle inventory

| Path | Authority | Lifecycle | Content owner | Update trigger | Closure disposition |
|---|---|---|---|---|---|
| `AGENTS.md` | `rule` | `live` | `self` | `authorized-rule-change` | `maintain` |
| `docs/architecture/adhoc_mapping_contract.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/adhoc_mapping_fields.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/branch_behavior_contract.md` | `rule` | `live` | `self` | `authorized-rule-change` | `maintain` |
| `docs/architecture/collaboration_contract.md` | `rule` | `live` | `self` | `authorized-rule-change` | `maintain` |
| `docs/architecture/configuration_architecture.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/contract_migration_inventory.md` | `architecture` | `migration-inventory` | `self` | `migration-only` | `promote-then-retire` |
| `docs/architecture/cross_version_reporting.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/dataclass_text_contract.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/documentation_contract.md` | `rule` | `live` | `self` | `authorized-rule-change` | `maintain` |
| `docs/architecture/evolution_strategy.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/project_structure.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/project_workflow.md` | `rule` | `live` | `self` | `authorized-rule-change` | `maintain` |
| `docs/architecture/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/architecture/reference_change_workflow.md` | `rule` | `live` | `self` | `authorized-rule-change` | `maintain` |
| `docs/architecture/reporting_architecture.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/repository_cleanup_audit.md` | `architecture` | `historical-frozen` | `self` | `frozen` | `retain-dated-evidence` |
| `docs/architecture/software_layers.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/sparameter_model_contract.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/architecture/utility_grid.md` | `architecture` | `live` | `self` | `affected-boundary` | `maintain` |
| `docs/document_registry.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/models/178A/artifacts/single_run_stage_io.xlsx` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/branch_behavior_registry.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/call_tree.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/config_tree.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/design_review.md` | `model` | `paused-temporary` | `self` | `user-resume` | `resume-or-converge` |
| `docs/models/178A/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/models/178A/stages/com_dfe.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/stages/com_mlsd.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/stages/mmse_dte.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/stages/path_construction.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/stages/post_ffe.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/stages/pre_dte.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/stages/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/models/178A/stages/sampling_phase.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/178A/status_tree.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/93A_vs_178A.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/93A/config_tree.md` | `model` | `live` | `self` | `affected-model-boundary` | `maintain` |
| `docs/models/93A/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/models/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/operations/config_gui.md` | `operations` | `live` | `self` | `supported-execution-change` | `maintain` |
| `docs/operations/github_ssh_setup.md` | `operations` | `live` | `self` | `supported-execution-change` | `maintain` |
| `docs/operations/manual_execution.md` | `operations` | `live` | `self` | `supported-execution-change` | `maintain` |
| `docs/operations/python36_utility.md` | `operations` | `live` | `self` | `supported-execution-change` | `maintain` |
| `docs/operations/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/operations/search_execution.md` | `operations` | `live` | `self` | `supported-execution-change` | `maintain` |
| `docs/operations/v1_0_release_gate.md` | `operations` | `live` | `self` | `supported-execution-change` | `maintain` |
| `docs/planning/178A_adaptive_grid_change_contract.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/178a_branch_inventory.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/active_contracts.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/alg001_missing_dc_completion.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/alg006_out_of_measured_transfer.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/alg011_rxffe_record_realization.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/comconfig_domain_migration.md` | `working` | `historical-frozen` | `docs/architecture/configuration_architecture.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/company_platform_cp1_gap_map.md` | `working` | `historical-frozen` | `docs/planning/v1_0_rebaseline.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/company_platform_cp2_contract_draft.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/document_disposition_manifest.md` | `working` | `historical-frozen` | `docs/document_registry.md` | `frozen` | `retain-dated-evidence` |
| `docs/planning/e003_pmf_grid_numerical_control.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/future_ideas.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/HANDOFF.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/NOTES.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/num002_gaussian_support.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/open_issues.xlsx` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/planning/reference_alignment_contracts.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/rule_changes.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/tc005_pmf_run_grid_policy.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/tc006_channel_high_frequency_policy.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/tc006_out_of_measured_boundary_revision.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc016_channel_renormalization_order.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc017_pre_dte_adc_clipping_reference.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc018_final_adc_quantization_reference.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc019_align_to_ref_profile.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/tc019r_reference_preset_resolution.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/tc020_ctle_pulse_realization.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc021_channel_frequency_limit.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/tc022_mmse_noise_grid.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc023_mlsd_reference_realization.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/tc024_mlsd_quantization_psd.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc025_alg003_gaussian_support.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/tc026_alg004_signed_scaling.md` | `working` | `historical-frozen` | `docs/models/178A/branch_behavior_registry.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/util_eye_001_linksegment_eye.md` | `working` | `paused-temporary` | `self` | `durable-owner-promotion` | `promote-before-freeze-or-retire` |
| `docs/planning/util_snp_001_sparam_representation.md` | `working` | `historical-frozen` | `docs/architecture/sparameter_model_contract.md` | `frozen` | `review-retention-in-convergence` |
| `docs/planning/utility_grid_contract_draft.md` | `working` | `paused-temporary` | `self` | `user-resume` | `resume-promote-or-retire` |
| `docs/planning/v1_0_rebaseline.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/planning/v1_0_roadmap.md` | `state` | `live` | `self` | `owned-state-change` | `maintain` |
| `docs/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `docs/validation/178A_actions_2026-09-15.md` | `evidence` | `historical-frozen` | `self` | `frozen` | `retain-dated-evidence` |
| `docs/validation/178A_adaptive_grid_evidence.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/178a_architecture_regression_anchor.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/178a_full_search_run_29.md` | `evidence` | `historical-frozen` | `self` | `frozen` | `retain-dated-evidence` |
| `docs/validation/178A_pmf_convolution_evidence.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/93a_architecture_regression_anchor.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/algorithm_branch_boundaries_178A.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/arc_178a_004a.md` | `evidence` | `historical-frozen` | `self` | `frozen` | `retain-dated-evidence` |
| `docs/validation/arc_178a_004b.md` | `evidence` | `historical-frozen` | `self` | `frozen` | `retain-dated-evidence` |
| `docs/validation/arc_178a_004c.md` | `evidence` | `historical-frozen` | `self` | `frozen` | `retain-dated-evidence` |
| `docs/validation/channel_renormalization.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/mmse_input_akinwale_178A.md` | `evidence` | `live` | `self` | `new-applicable-evidence` | `maintain` |
| `docs/validation/README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
| `README.md` | `index` | `live` | `self` | `indexed-set-or-lifecycle-change` | `maintain` |
