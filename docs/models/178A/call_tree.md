# 178A call tree

> **Status: authoritative structural call reference.** This document records current entry points, orchestration calls, execution-policy boundaries, and status handoffs. It does not validate model equations; those belong to reviewed stage documents.

## Scope and sources

The maintained sources are:

- `src/serdes_coding/models/com_model_178A.py` for the manual entry and one-candidate model pipeline;
- `src/serdes_coding/io/com_excel_io_178A.py` for workbook-to-config construction;
- `src/serdes_coding/search/com_search_178A.py` for file-backed search orchestration;
- `scripts/run_full_search_178A.py` and `.github/workflows/run_full_search_178A.yml` for distributed GitHub Actions execution;
- `src/serdes_coding/reporting/com_report_178A.py` for the reporting boundary.

Configuration ownership is defined in [Configuration tree](config_tree.md). Produced objects and legal partial states are defined in [Status tree](status_tree.md).

The 178A `COM` orchestrator is standalone and does not inherit the 93A `COM`
class. It owns the 178A stage order, root status lifecycle, victim-alignment
guard, and status accessors. File-backed search and reporting remain downstream
consumers rather than inherited model methods.

## Public execution choices

```text
RUN_MODE
├── single_run
│   └── execution.single_run
└── search_run
    ├── execution.search_sweep
    └── execution.search_final
```

`RUN_MODE` chooses the user-visible operation. The two search profiles are internal steps of one `search_run`; they are not additional run modes. Search ranges come from the workbook `search_config` sheet. The manual `EXEC_POLICY` dictionary may replace fields of the three existing execution profiles, but it does not replace fixed config or search ranges.

178A `run_config.control.execution_profile` 是 workbook facade selector。
`excel_to_config_178A()` 在建立 `COMConfig` 前把它展開為具名算法和三組
有效 execution profile。`COM._effective_run_cfg()` 只回傳已解析的 profile；
model 不判斷 selector。有效方法、profile 名稱及 raw/effective override
隨 config snapshot 輸出。
`COM.__init__()` 另由 `COMPolicyConfig` 建立共享 MMSE noise grid；它不改動
channel／pulse 使用的 `COMConfig.link`。

## Manual file entry

Executing `com_model_178A.py` directly or through `%run com_model_178A.py` follows this tree:

```text
__main__
├── resolve PROJECT_ROOT / CASE_ID / 178A
├── validate RUN_MODE and config.xlsx
├── excel_to_config_178A(config.xlsx)
│   ├── read fixed config plus execution_profile and all run profiles
│   ├── expand the versioned preset into named effective values
│   └── construct COMConfig without the workbook selector
├── apply validated EXEC_POLICY overrides
└── branch by RUN_MODE
    ├── single_run
    │   ├── COM(cfg).run(progress=True)
    │   │   └── COM._run_once(run_cfg=execution.single_run)
    │   └── COMReport178A(cfg, status).export_single_run(report_path)
    │       └── COMReportBase.plot_single_run()
    │           ├── plot_overview()
    │           ├── plot_paths()
    │           ├── plot_equalizer()
    │           ├── plot_impairments()
    │           ├── plot_pmf()
    │           └── plot_mlsd()
    └── search_run
        ├── excel_to_search_config_178A(config.xlsx)
        └── COM(cfg).run(search=search_cfg, report_dir=report_path)
            └── run_full_search(cfg, search_cfg, report_path)
```

The model returns status. Reporting receives the completed config and status and remains a downstream consumer.

## One-candidate model pipeline

`COM.run(search=None)` selects `execution.single_run` and delegates to `_run_once()`. Search code calls `_run_once()` directly with its own profile.

```text
COM._run_once(run_cfg)
├── initialize COMStatus and target checks
├── build_all_paths()
│   ├── _build_channel_under_test(channel config)
│   ├── _build_shared_path(config, frequency grid)
│   └── _build_paths(config, shared blocks, channels)
│       └── _build_path(...) for victim, NEXT, and FEXT paths
│           ├── continuous_tf: frequency-domain CTF + unit pulse
│           └── bilinear_iir
│               ├── _evaluate_pre_ctle_on_measured_grid(...)
│               ├── _reference_fd_to_td_record(...)
│               ├── _realize_ctle_response(...)
│               └── _apply_rectangular_unit_pulse(...)
├── calculate_pre_dte_imp_common(victim, xtalk pulses)
│   ├── build all common PSDs on the resolved noise grid
│   └── return run-local common PSD/cache data
├── initialize COMRunStatus
├── choose initial phase indices
├── evaluate each requested phase
│   └── calculate_pos_candidate(...)
│       ├── calculate_pre_dte_imp_at_pos(...)
│       └── calculate_MMSE_DTE(...)
│           └── COM_MMSE_DTE(...).run(...)
├── optionally choose and evaluate fine phase indices
├── select minimum-MSE valid phase
├── assign selected DTE and pre-DTE impairment status
└── branch by run_cfg.target
    ├── mse
    │   └── return selected pre-DTE/DTE status
    ├── dfe
    │   ├── calculate_post_ffe_imp(...)
    │   │   └── _apply_rxffe_response(...) using resolved record realization
    │   ├── calculate_COM_DFE(...)
    │   └── return DFE COM status
    ├── mlsd
    │   ├── calculate_post_ffe_imp(...)
    │   ├── calculate_COM_DFE(...)
    │   ├── calculate_COM_MLSD()
    │   └── return DFE plus MLSD status
    └── full
        ├── calculate_post_ffe_imp(...)
        ├── calculate_COM_DFE(...)
        ├── calculate_COM_MLSD() when cfg.mlsd.enable is true
        └── return requested completed status
```

A `COMMainCursorError` rejects only that phase in the sampling loop. Other exceptions leave `_run_once()` and preserve any status already assigned, as described in the status lifecycle.

## DTE solver call boundary

```text
calculate_MMSE_DTE(...)
└── COM_MMSE_DTE.run(...)
    ├── validate input
    ├── build full solver matrices
    ├── select tap placement according to floating_mode
    ├── solve selected system
    ├── apply coefficient limits and refinement
    ├── calculate candidate MSE
    ├── build COMDTEStatus
    └── validate equalized main cursor
```

The detailed numerical meaning of these operations belongs in the reviewed DTE stage document. This tree only fixes ownership: `COM_MMSE_DTE` owns the candidate solver and returns one `COMDTEStatus`; `_run_once()` owns phase comparison and selection.

## DFE COM and MLSD branches

```text
calculate_COM_DFE(imp_status, dte_status)
├── resolve final-COM PMF runtime config
├── build component PMFs from stored post-FFE results
├── combine PMFs
└── return COMPMFStatus

calculate_COM_MLSD()
├── require completed impairment, DTE, and DFE PMF status
├── solve_g_an(...)
├── build_mlsd_noise(...) -> COMMLSDNoiseStatus
├── calculate_der_mlsd(p_an, R_ni, ...) -> DER_MLSD, der_by_j
├── assemble complete COMMLSDStatus using Eq. 178A-47
└── assign status.mlsd
```

`calculate_COM()` is a compatibility alias for `calculate_COM_DFE()`.

## Local file-backed search

`run_full_search()` is the sequential convenience entry used by the manual search path.

```text
run_full_search(cfg, search, report_dir)
├── create_search_plan(...)
│   ├── search.candidates(cfg.filter)
│   ├── write candidate_manifest.csv
│   └── write group_plan.csv
├── for every planned group
│   └── run_partial_group(...)
│       ├── reconstruct candidate
│       ├── apply candidate to a copied config
│       ├── COM(candidate_cfg)._run_once(execution.search_sweep)
│       └── write group_NNN.csv
└── finalize_search(...)
    ├── merge_partial_results(...)
    ├── rank successful rows by MSE
    ├── rank rows and seek execution.search_top_k valid final results
    ├── for each attempted row, backfilling after grid overflow
    │   ├── COM(candidate_cfg)._run_once(execution.search_final)
    │   ├── COMStatus.export(...)
    │   └── if include_plots: COMReport178A(candidate_cfg, status).export_single_run(...)
    ├── write full_search_results.csv
    ├── export config and COMSearchStatus
    ├── if include_plots: COMReport178A(best_cfg, search_status).export_search_run(...)
    └── return COMSearchStatus
```

`search_sweep` produces the comparison metric for every candidate. `search_final` attempts candidates in MSE order until it has top-K valid final results or exhausts the candidates. A fixed-grid overflow is recorded and excluded from final ranking.

## Distributed GitHub Actions search

The workflow splits the same file-backed search functions across jobs; it does not define a separate model path.

```text
workflow_dispatch(selected Git ref, case_id input)
├── prepare job
│   └── run_full_search_178A.py prepare
│       ├── load workbook config and search config
│       ├── fingerprint workbook and referenced channel files
│       ├── create_search_plan(...)
│       └── write execution_plan.json and worker matrix
├── partial_search matrix jobs
│   └── run_full_search_178A.py partial
│       ├── verify input fingerprint
│       └── run_partial_group(...) for assigned group IDs
├── finalize job
│   └── run_full_search_178A.py finalize
│       ├── verify input fingerprint
│       ├── finalize_search(..., include_plots=True)
│       └── verify_outputs(...)
└── verify_artifact job
    └── run_full_search_178A.py verify
        └── verify final rows, top-K coverage, plot manifests, sizes, and hashes
```

Infrastructure grouping and worker assignment change scheduling only. Candidate definition and the two model execution policies remain workbook/config owned.

## Search error boundary

- `COMTxfirMainCursorError` becomes an `infeasible` partial row and does not depend on `continue_on_error`.
- Other partial exceptions become `error` rows only when `continue_on_error` is enabled; otherwise they propagate.
- Finalization records a `grid_overflow` warning with tail metrics and backfills from the next MSE-ranked candidate. Overflow rows have no valid COM and cannot become best. If none fits the grid, finalization raises after writing the CSV.
- Non-grid final failures retain the existing error behavior: record the error, write the CSV, then raise.
- Missing or duplicate group coverage is rejected during `merge_partial_results()`.

## Ownership summary

| Layer | Owns |
|---|---|
| workbook reader | project config and search-range construction |
| manual entry | case selection, run-mode choice, optional execution-policy override |
| `COM._run_once()` | one concrete candidate and its stage/status lifecycle |
| `COM_MMSE_DTE` | one phase candidate's DTE solve |
| search module | candidate manifest, grouping, partial rows, ranking, top-K finalization |
| workflow script | distributed scheduling, input identity, artifact verification |
| report module | plots and report files from completed status |
