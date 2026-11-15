# 178A call tree

> **Status: authoritative structural call reference.** This document records current entry points, orchestration calls, execution-policy boundaries, and status handoffs. It does not validate model equations; those belong to reviewed stage documents.

## Scope and sources

The maintained sources are:

- `src/serdes_coding/models/com_model_178A.py` for the manual entry and one-candidate model pipeline;
- `src/serdes_coding/models/com_178a/config.py` and `status.py` for version-owned input/output contracts;
- `src/serdes_coding/models/com_178a/path_stage.py` for the complete path-construction stage;
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
│   └── adapter profile single_run → cfg.alg/num/srch/exe
└── search_run
    ├── adapter profile search_sweep → sweep_cfg
    └── adapter profile search_final → final_cfg
```

`RUN_MODE` chooses the user-visible operation. The two search profiles are internal steps of one `search_run`; they are not additional run modes. Search ranges come from the workbook `search_config` sheet. The manual `EXEC_POLICY` dictionary may replace fields of the three existing execution profiles, but it does not replace fixed config or search ranges.

178A `run_config.control.execution_profile` 是 workbook facade selector。
`excel_to_config_178A(..., run_mode=...)` 在建立 `COMConfig` 前選定一組
profile，並展開為 `cfg.alg/num/srch/exe`；model 不判斷 selector。
有效方法、profile 名稱及 raw/effective override 隨 config snapshot 輸出。
`COM.__init__()` 不解析 NUM-003，也不建立共享 impairment-record context。
NUM-003 只在 Pre-DTE 與 pre-MLSD PSD 即將加總時，由各自
owner 解析；channel／pulse 與完整 `eq_ch` 一律保留原本的 `COMConfig.link` 表示。

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
    │   │   └── validate scalar cfg.srch → COM._run_once()
    │   └── COMReport178A(cfg, status).export_single_run(report_path)
    │       └── COMReportBase.plot_single_run()
    │           ├── plot_overview()
    │           ├── plot_paths()
    │           ├── plot_equalizer()
    │           ├── plot_impairments()
    │           ├── plot_pmf()
    │           └── plot_mlsd()
    └── search_run
        ├── load sweep_cfg and final_cfg, each carrying cfg.srch
        └── run_full_search(sweep_cfg, final_cfg, report_path)
```

The model returns status. Reporting receives the completed config and status and remains a downstream consumer.

## One-candidate model pipeline

`COM.run()` requires scalar candidate axes in `cfg.srch` and delegates to
`_run_once()`. Outer search resolves every vector candidate into a copied
scalar config before calling the same public method.

```text
COM._run_once()
├── initialize COMStatus and target checks
├── Stage 1 — build_all_paths()
│   └── com_178a.path_stage
│       ├── _build_channel_under_test(cfg.src, cfg.channel)
│       │   ├── each source binding loads and validates its artifact
│       │   ├── S4P: physical R0 renormalization → binding port-order Sdd
│       │   ├── native S2P: differential-domain 2*R0 renormalization
│       │   └── physical measured-frequency limit → common measured grid
│       ├── _build_shared_path(config, frequency grid)
│       └── _build_paths(config, shared blocks, channels)
│           ├── resolve cfg.alg.missing_dc_policy once for every path
│           └── _build_path(...) for victim, NEXT, and FEXT paths
│               ├── directly inject concrete ALG-001 method
│               │   └── L5 SparamModel.completed_voltage_transfer_function()
│               │       └── one DC-complete terminated H21
│               ├── _realize_ctle_pulse(...) -> path.pulse
│               │   ├── continuous_tf: frequency-domain CTF + unit pulse
│               │   └── bilinear_iir: measured TF -> finite record -> IIR + unit pulse
│               └── victim only: _realize_ctle_pulse(include_txffe=False)
│                   └── path.pulse_no_txffe
├── Stage 2 — Pre-DTE model: phase-independent preparation
│   ├── calculate_pre_dte_imp_common(victim) -> sigma_X cache
│   └── prepare_pre_dte_phase_inputs(...)
│       ├── select each XT path phase from the full oversampled response
│       └── emit full one-sample/UI eq_ch_XT records
├── Stage 3 — Sampling search block in _run_once()       [SRCH-001 L1 owner]
│   ├── resolve method / stride once                     [sole selector read]
│   ├── initialize COMRunStatus
│   ├── _initial_pos_sweep_indices(...)
│   ├── while one initial/fine phase batch remains
│   │   └── for each requested phase
│   │       ├── Stage 2 — Pre-DTE model: calculate_pre_dte_imp_at_pos(...)
│   │       │   ├── build complete per-phase eq_ch responses
│   │       │   └── _build_pre_dte_psd(...)
│   │       │       ├── resolve NUM-003 record_cfg
│   │       │       ├── resolve ALG-008 clipping noise / CDF tail
│   │       │       ├── resolve NUM-004 ADC-input PMF grid
│   │       │       ├── build ADC-input FIR PMF with NUM-006 keep_mass
│   │       │       │   └── Pmf1D.fir_filter() [NUM-006 L5 owner]
│   │       │       └── build/sum PSDs → R_n
│   │       ├── Stage 4 — DTE solver: calculate_MMSE_DTE(...)
│   │       │   ├── COM_MMSE_DTE(...).run(...)
│   │       │   └── build H_rxffe from selected w_lim representation
│   │       └── record MSE/error and retain strict-minimum complete bundle
│   ├── coarse_fine only: _fine_pos_sweep_indices(...)
│   └── _assign_selected_phase(eq_ch, imp, dte) once
└── branch by cfg.exe.target
    ├── mse
    │   └── return selected pre-DTE/DTE status
    ├── dfe
    │   ├── Stage 5 — Post-FFE model: calculate_post_ffe_imp(...)
    │   │   ├── _apply_rxffe_response(...) on each victim, XT, and DDJ input grid
    │   │   ├── _resolve_adc_input_pmf_config() for NUM-004 selected-phase material
    │   │   ├── _build_adc_input_pmf_exact() with NUM-006 keep_mass
    │   │   │   └── Pmf1D.fir_filter() [same NUM-006 L5 owner]
    │   │   └── transform pre-DTE PSDs on their existing record (NUM-003 non-owner)
    │   ├── _assign_post_ffe(...) once, including resolved response/PSD grids
    │   ├── Stage 6 — calculate_COM_DFE(...)
    │   └── return DFE COM status
    ├── mlsd
    │   ├── Stage 5 — calculate_post_ffe_imp(...)
    │   ├── Stage 6 — calculate_COM_DFE(...)
    │   ├── Stage 7 — calculate_COM_MLSD()
    │   └── return DFE plus MLSD status
    └── all_enabled
        ├── Stage 5 — calculate_post_ffe_imp(...)
        ├── Stage 6 — calculate_COM_DFE(...)
        ├── Stage 7 — calculate_COM_MLSD() when cfg.mlsd.enable is true
        └── return requested completed status
```

MLSD 的 `build_mlsd_noise()` 是第二個 NUM-003 owner：它從完整 pre/post-FFE
`eq_ch` response 直接建立 MLSD 專用 component PSD；只在該函數內解析 record、
加總 `S_ni` 並形成 `R_ni`。Post-FFE reporting PSD 不作為 MLSD PSD source，
完整 `h_ISI` 也不會預先截短。MLSD 不擁有另一個 RX FFE realization selector。

A `COMMainCursorError` rejects only that phase in the root Sampling-search loop.
Other exceptions leave `_run_once()` and preserve any status already assigned,
as described in the status lifecycle. Stage 1–7 are retained as runtime and
navigation labels, not ownership coordinates; domain function sets own their
dataclasses while this call tree records runtime order and feedback loops.

## Stage 4 DTE solver call boundary

```text
calculate_MMSE_DTE(...)
├── inject cfg.alg.floating_mode                         [ALG-010 injector; non-owner]
└── COM_MMSE_DTE.run(...)                                [ALG-010 L3 concrete owner]
    ├── validate input
    ├── build full solver matrices
    ├── dispatch floating_mode
    │   ├── heuristic → _select_floating_tap_by_isi()    [executor; non-owner]
    │   ├── simplified → _select_floating_tap_onetime()  [executor; non-owner]
    │   └── spec-defined → _calculate_float_ffe_178A()   [executor; non-owner]
    ├── N_wg=0 → bypass floating selection
    ├── solve selected system
    ├── apply coefficient limits and refinement
    ├── calculate candidate MSE
    ├── build COMDTEStatus
    └── validate equalized main cursor
```

The detailed numerical meaning of these operations belongs in the reviewed DTE stage document. This tree fixes ALG-010 ownership: semantic owner `COM_MMSE_DTE`, concrete callable owner `COM_MMSE_DTE.run()`. `calculate_MMSE_DTE()` is the selector injector, strategy helpers are executors, and `_run_once()` owns phase comparison and selection; none of those three roles creates another ALG-010 owner.

## DFE COM and MLSD branches

ALG-002 and every other branch's classification and L0--L5 ownership position
are centralized in the
[178A Branch Behavior Registry](branch_behavior_registry.md#分支-ownership--function-position-tree).
This file records only the surrounding pipeline flow.

```text
Stage 6 — calculate_COM_DFE(imp_status, dte_status)
├── _resolve_final_com_pmf_config(...) [NUM-005 L4 owner / execution point 1]
│   └── COMPMFGridControl.resolve_dy() [shared L5 kernel]
├── build component PMFs from stored post-FFE results
├── combine PMFs
└── return COMPMFStatus

Stage 7 — calculate_COM_MLSD()
├── require completed impairment, DTE, and DFE PMF status
├── _resolve_final_com_pmf_config(...) [same NUM-005 owner / execution point 2]
├── gaussian_addition → solve_g_an(...)
│   └── evaluate_delta_com_an() rebuilds p_G_an on resolved final dy [direct]
├── scaled_total_pdf → reuse/scale DFE PMFs [NUM-005 indirect]
├── build_mlsd_noise(...) -> COMMLSDNoiseStatus
├── calculate_der_mlsd(p_an, R_ni, ...) -> DER_MLSD, der_by_j
├── assemble complete COMMLSDStatus using Eq. 178A-47
└── assign status.mlsd
```

`calculate_COM()` is a compatibility alias for `calculate_COM_DFE()`.
NUM-005 does not apply a final post-combination regrid. The DFE COM model
constructs its component PMFs on the resolved grid; MLSD either rebuilds the
Gaussian PMF on that grid or inherits the already gridded DFE PMFs.

## Local file-backed search

`run_configured(single_cfg, sweep_cfg, final_cfg, report_dir)` is the SRCH
dispatch boundary. A Cartesian product of one resolves its candidate into
`single_cfg` and calls `COM.run()` directly. A larger product delegates to
`run_full_search()`; vectors never reach `COM.run()`.

`run_full_search()` is the sequential multi-candidate entry used by the manual
search path.

```text
run_full_search(sweep_cfg, final_cfg, report_dir)
├── create_search_plan(...)
│   ├── sweep_cfg.srch.candidates(sweep_cfg.filter)
│   ├── write candidate_manifest.csv
│   └── write group_plan.csv
├── for every planned group
│   └── run_partial_group(...)
│       ├── reconstruct candidate
│       ├── apply candidate to copied filter + scalar cfg.srch
│       ├── COM(candidate_cfg).run()
│       └── write group_NNN.csv
└── finalize_search(...)
    ├── merge_partial_results(...)
    ├── rank successful rows by MSE
    ├── rank rows and seek cfg.srch.final_top_k valid final results
    ├── for each attempted row, backfilling after grid overflow
    │   ├── COM(candidate_cfg).run()
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
│       ├── load mode-resolved configs carrying cfg.srch
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
