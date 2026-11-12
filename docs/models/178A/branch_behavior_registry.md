# 178A 分支行為登錄表

狀態：**authoritative**  
最後核對：2026-11-12

本文件是 178A model 分支行為的唯一權威紀錄，集中保存分類總表與
ownership/function-position tree。新增、修改、重新命名、合併、移除或二次審查
branch behavior 時，必須在同一變更中更新兩者。Stage 文件只保存 stage I/O 與
execution detail；`call_tree.md` 只保存 pipeline flow，不再各自維護 branch owner
結論。歷史 change contract 說明決策過程；本文件描述目前實作與 review state。

範圍包含 178A runtime 及其實際呼叫的 shared utility 分支；不把 178A 選項自動視為 93A 行為。若 93A 新增平行算法，應建立或更新對應的 `docs/models/93A/branch_behavior_registry.md`。

## 判定規則

branch behavior、一般 config、execution strategy、input boundary、固定行為與
provenance 的正式定義，見 [Branch behavior contract](../../architecture/branch_behavior_contract.md)。
本表只授予通過 eligibility 的 selectable behavior branch identity。ID 的
`ALG`／`NUM`／`SRCH` 前綴記錄 selector 所在的 runtime domain，不是三種
branch classes，也不能單憑 config container 判定它是 branch。Physical fields、
`cfg.src` 與 `cfg.exe` 不建立 `PHY`／`SRC`／`EXE` branch ID；它們只在
「不是分支的項目」記錄必要 exclusion。

號碼在同一 ID prefix 內依最早 behavioral owner／consumer 的 stage 排序。
完全位於 COM pipeline 外的 shared utility 以 `Shared L5 utility` 表示，不虛構
Stage 0 owner；跨多 stage 的 branch 必須列出全部 consumers。若後續 evidence
改變 scope，ID 允許隨 stage order 重排，並須在同一變更同步本表與 legacy
mapping。Stage 文件不另建平行分類表。

一個 branch behavior 對應某個 coding layer 的一個 semantic choice，並可由
一個或多個 runtime fields 共同完整定義；field 數量本身不是分支數量。相反地，
即使兩組 fields 使用相同 dataclass 或 numerical primitive，只要它們由不同
function set 擁有、作用於不同 impact boundary，仍可能是不同 branch。

本表使用下列 `Review classification`，這才是 branch review 的正式分類：

- `approved branch`：已通過 eligibility，保留 selectable behavior；
- `unreviewed existing selector`：production 已有 selector，但沒有可追溯的完整
  branch review；選項、eligibility、scope、owner 與 validation 都必須從頭確認；
- `pending candidate`：尚缺 branch／non-branch 決定、scope、owner 或 evidence，
  暫留本表但不得宣稱已核准。

一旦決定為 non-branch，就從本表與 ownership tree 移除，只在 legacy mapping
或「不是分支的項目」保留必要的決策理由。

`Selector domain` 只記錄 selector 位於 `cfg.alg`、`cfg.num` 或 `cfg.srch`。
其中的欄位仍須逐項通過 eligibility：純 tolerance、resolution、candidate value、
coverage、retention 或 scheduling 不會只因位於這些 domain 就成為 branch。

- **輸入邊界**描述 case 實際提供的資料範圍，不是算法分支。
- **固定行為**目前只有一種合法 realization，不能宣稱為可切換分支。
- `execution_profile` 只在 workbook adapter 選取具名 preset；model 不讀取 selector。
- 所有 runtime 算法 policy 平放在 `COMConfig.alg: COMAlgorithmPolicyConfig`；
  不得為單一 stage 再加入 nested policy dataclass。數值控制平放在
  `COMConfig.num`，run extent 位於 `COMConfig.exe`。舊 `policy`／
  `numerical_control`／`execution` aliases 已移除。

## 分支分類總表

這是 178A branch review 的唯一分類表。它只回答 branch identity、selector、
選項、semantic owner 與 ownership review state；impact boundary 拆到下一節，
function position 則由後面的 tree 表示。`Semantic owner` 是最低且不可避免必須知道
所選行為的 conceptual layer，不是 config container、forwarding caller 或結果
consumer。尚未完成完整初次審查的 owner 只標為「provisional」，不得當成正式結論。

`sicopr_reference_v1` 只記錄 adapter 對該 branch 解析出的 concrete choice；它
不是另一套 branch 分類，也不建立新的 runtime owner。完整 profile 展開、override
與 provenance contract 由 `config_tree.md` 維護。Legacy ID 只在後面的 mapping
維護，不再占用分類總表欄位。

| ID | Branch classification | Scope | Selector 與 project choices | `sicopr_reference_v1` | Semantic owner | Ownership review |
|---|---|---|---|---|---|---|
| `ALG-001` | approved branch | Stage 1 path construction | `alg.missing_dc_policy`：project default `skrf`；另有 `error`／`hold`／`mag_phase_trend_to_dc` | `mag_phase_trend_to_dc` | **L5** `SparamModel.completed_voltage_transfer_function()` | **二次審查已確認** |
| `ALG-002` | approved branch | Stages 3／5／6／7 target-grid PMF projection | `alg.pmf_projection_method`：`linear`／`nearest` | `nearest` | **L5 owner set** `Pmf1D.multi_dirac()`／`scale_x()`／`resample_dx()`／`fir_filter()` | **Closed 2026-11-11** |
| `ALG-003` | approved branch | Shared PDF→PMF utility | `alg.pdf_to_pmf_method`：`bin_integral`／`pmf_sample` | `pmf_sample` | **L5 owner set** `Pmf1D.gaussian()`／`uniform()` | **Closed 2026-11-11** |
| `ALG-004` | approved branch | MLSD fixed-grid scalar-PMF scaling | `alg.pmf_scaling_method`：`mass_deposit`／`interpolate_ordinates` | `interpolate_ordinates` | **L5** `Pmf1D.scale_x()` | **Closed 2026-11-11** |
| `ALG-006` | approved branch | Stage 1 measured-grid scalar-transfer extension | `alg.out_of_measured`：project default `cosine_decay`；另有 `zero_padding` | `zero_padding` | **L5** `resample_tf()` | **Closed 2026-11-11** |
| `ALG-007` | approved branch | Stage 1 CTLE pulse realization | `alg.ctle_pulse_realization`：project default `continuous_tf`；另有 `bilinear_iir` | `bilinear_iir` | **L3** CTLE pulse-realization functional block；L4 `_prepare_ctle_pulse_realization()`／`_realize_ctle_pulse()` | **Closed 2026-11-11** |
| `NUM-003` | approved branch | Pre-DTE 與 pre-MLSD PSD/correlation record | `num.eq_ch_imp_len`：`full`／`truncated`；`num.num_trunc_ui` 是 branch parameter | `truncated`；`num_trunc_ui=4096` | **兩個 L3 owner**：Pre-DTE `_build_pre_dte_psd()`；MLSD `build_mlsd_noise()` | **Closed 2026-11-12** |
| `SRCH-001` | approved branch | Sampling search control | `srch.pos_sweep_method`：`each_phase`／`coarse_fine`；`pos_coarse_stride` 是 branch parameter | 不覆蓋 | **semantic owner** Sampling search function set；**concrete owner** `COM._run_once()` phase-search loop | **Ownership corrected 2026-11-13** |
| `ALG-008` | approved branch | Pre-DTE PSD／per-phase ADC input | `alg.pre_dte_adc_clipping_convention`：`full_jitter_half_tail`／`rj_only_full_tail_reference` | `rj_only_full_tail_reference` | **L3** `COM._build_pre_dte_psd()` | **Closed 2026-11-12** |
| `NUM-004` | approved branch | Stages 2／5 ADC-input PMF grid | `num.adc_input_pmf_grid.*`：`relative_As_with_cap`／`relative_As`＋grid parameters；`dy_override` 優先 | `relative_As_with_cap`；`dy_override=10e-6 V` | **L4** `_resolve_adc_input_pmf_config()`；L5 shared kernel `COMPMFGridControl.resolve_dy()` | **Closed 2026-11-12** |
| `NUM-005` | approved branch | Stages 6／7 final-domain PMF grid | `num.final_pmf_grid.*`：`relative_As_with_cap`／`relative_As`＋grid parameters；`dy_override` 優先 | `relative_As`；`dy_override=None` | **L4** `_resolve_final_com_pmf_config()`；L5 shared kernel `COMPMFGridControl.resolve_dy()` | **Closed 2026-11-12** |
| `NUM-006` | pending candidate | Pre-DTE ADC-input PMF convergence | `num.pmf_keep_mass`：project `1-1e-5`；reference profile `1.0` | profile 值見 `config_tree.md` | **未決定** | 待完整初次審查；不宣稱 branch owner |
| `ALG-010` | approved branch | DTE solver | `alg.floating_mode`：`heuristic`／`simplified`／`spec-defined` | 不覆蓋 | **L3 semantic owner** `COM_MMSE_DTE`；**concrete owner** `COM_MMSE_DTE.run()` | **Closed 2026-11-12** |
| `ALG-011` | unreviewed existing selector | Post-FFE model | `alg.rxffe_record_realization`：`linear_fixed_grid`／`linear_expanded_grid`／`finite_record_circshift` | `finite_record_circshift` | **provisional L3** `_apply_rxffe_response()` | 待完整初次審查 |
| `ALG-012` | unreviewed existing selector；evidence pending | DFE COM final clipping | `alg.final_com_vqc_convention`：`selected_phase_adc_input`／`sicopr_final_reconstruction` | `sicopr_final_reconstruction` | **provisional L3** `calculate_COM_DFE()` final-`V_qc` block | 待完整初次審查；D3p2 evidence pending |
| `ALG-013` | unreviewed existing selector | DFE COM final ADC PMF | `alg.final_adc_pmf_projection`：`annex_d3`／`reference_support` | `reference_support` | **provisional L3** `calculate_COM_DFE()` final-ADC-PMF block | 待完整初次審查 |
| `ALG-014` | unreviewed existing selector | MLSD added noise | `alg.added_noise_pdf`：`gaussian_addition`／`scaled_total_pdf` | `scaled_total_pdf` | **provisional L3** `solve_g_an()` | 待完整初次審查 |
| `ALG-015` | unreviewed existing selector | MLSD noise PSD | `alg.mlsd_quantization_psd`：`pre_dte_filtered`／`main_tap_white` | `main_tap_white` | **provisional L3** `build_mlsd_noise()` | 待完整初次審查 |
| `ALG-016` | unreviewed existing selector | MLSD DER recurrence | `alg.sequence_termination`：`fixed_length_sum`／`matlab_relative_tail` | `matlab_relative_tail` | **provisional L3** `calculate_der_mlsd()` | 待完整初次審查 |
| `ALG-017` | unreviewed existing selector | MLSD reported DER | `alg.reported_der`：`raw_sequence_sum`／`baseline_pdf_re_evaluation` | `baseline_pdf_re_evaluation` | **provisional L3** `calculate_COM_MLSD()` reported-DER block | 待完整初次審查 |

## Responsibility / impact boundaries

本表將原本塞在 `Responsibility boundary` 單一欄位的內容拆成「允許改變」與
「必須保持獨立」。Owner、injector 與 consumer 的 function position 不在此處
重複，統一查閱下一節 ownership tree。

| ID | Branch 允許改變 | 必須保持獨立／不屬此 branch |
|---|---|---|
| `ALG-001` | terminated H21 的 missing-DC completion | source binding、measured-frequency boundary、out-of-measured extension、CTLE realization |
| `ALG-002` | 已建立 PMF 投影至 target grid 的 placement method | source atoms、PDF discretization、scalar scaling semantics、retained mass |
| `ALG-003` | Gaussian／uniform PDF 離散成 PMF 的方法 | Gaussian initial support 固定 ±8σ；target-grid projection 與 scalar-PMF scaling 保持獨立 |
| `ALG-004` | fixed-grid scalar-PMF scaling；signed scale 保持同一 `abs(scale)` output grid，負值鏡射 ordinates | FIR tap construction；`mass_deposit` 使用 ALG-002 placement 但不擁有它；grid spacing、retained mass 與 PDF construction |
| `ALG-006` | effective measured grid 上的 scalar transfer function 重採樣至目標 frequency grid；目前涵蓋 analysis-grid H21，以及 bilinear CTLE path／victim no-TX-FFE finite record | `S_ch`、`S_all`、boundary-in interpolation、case frequency limit、missing-DC completion、CTLE realization／IIR／IFFT／截尾 |
| `ALG-007` | CTLE pulse method-specific shared state，以及 victim／NEXT／FEXT `pulse` 與 victim `pulse_no_txffe` 的完整 CTLE realization | TX FFE、continuous `H_all`、ALG-006 transfer extension、Pre-DTE TX-noise sampling policy |
| `NUM-003` | 在 pre-DTE／pre-MLSD PSD 真正加總的 owner 內，先把各完整 eq-channel response realization 成 `full` 或固定 `num_trunc_ui` record，再建 PSD、加總並形成 autocorrelation；固定長度模式對過長 response 截尾、對過短 response 補零 | Path response、完整 `eq_ch` status、Sampling search、DTE solve、Post-FFE reporting transform、ALG-011 response realization／grid |
| `SRCH-001` | 要評估的 phase schedule、coarse/fine visit order、最低 MSE complete bundle 與 per-phase run status | Pre-DTE model、DTE solver／ALG-010、XT independent-phase preparation、post-selection domains |
| `ALG-008` | per-phase `V_qc → delta → S_qn → R_n` clipping convention | final ADC PMF；後續結果只可能經 selected phase/taps 間接受影響 |
| `NUM-004` | Pre-DTE 與 selected-phase Post-FFE ADC-input PMF 的 voltage spacing；override／relative／capped-relative resolution | NUM-005 final PMF grid、NUM-006 retained mass、PMF projection／PDF discretization、NUM-003 PSD record grid |
| `NUM-005` | DFE component／combined PMFs 與 MLSD added-noise PMF 的 voltage spacing；override／relative／capped-relative resolution。Gaussian-replacement flow 直接使用 resolved grid；`scaled_total_pdf` flow 間接沿用 DFE PMFs | NUM-004 ADC-input PMF grid、NUM-006 retained mass、PMF projection／PDF discretization／scalar scaling、MLSD PSD record grid |
| `NUM-006` | pending：ADC-input PMF retained-mass／convergence effect | branch eligibility、consumer scope 與 owner 尚未核准 |
| `ALG-010` | floating tap/group selection strategy；owner 依 resolved selector dispatch，並控制該 placement 的完整 solve／limit／MSE／`COMDTEStatus` lifecycle | fixed-tap limiter definition、MMSE/KKT equations、coefficient limits、phase search、equal-score tie-break implementation |
| `ALG-011` | victim、all XT、DDJ 的 post-FFE response record/grid | RX FFE taps、MMSE solve、pre-FFE responses、NUM-003 record length |
| `ALG-012` | final-COM clipping voltage convention | final-quantization main-tap accumulation issue |
| `ALG-013` | final ADC quantization PMF projection/support | pre-DTE ADC PMF；reference option 對 ALG-012 有相依但不合併 owner |
| `ALG-014` | added-noise PDF construction | `S_isi`、`S_ni` definitions |
| `ALG-015` | Eq. 178A-54 的 MLSD quantization-noise PSD composition | MMSE noise、RxFFE taps、`S_an`、`S_isi`、DER solver |
| `ALG-016` | DER recurrence termination | Eq. 178A-49 的共同 sign definition |
| `ALG-017` | reported DER formation | raw sequence DER 必須獨立保留 |

## 分支 ownership / function-position tree

本樹是所有現存 178A closed branches、unreviewed selectors 與 pending candidates 在 semantic
function call tree 中的位置總表。
`[owner]` 表示目前登錄的最低 semantic owner；`[injector]` 只解析或注入 concrete
choice；`[consumer]` 使用結果但不擁有 branch；`[provisional]` 表示完整初次
review 尚未完成。Retired／fixed non-branches 不放入本樹，統一列在後面的
「不是分支的項目」。

```text
COM model
├─ L1 Domain — Path realization
│  └─ L2 path-realization function set
│     ├─ _build_shared_path()                                [ALG-007 config resolver / shared coordinator]
│     │  └─ CTLE pulse-realization block                     [ALG-007 L3 owner: shared setup]
│     │     └─ _prepare_ctle_pulse_realization()             [ALG-007 L4 setup decision]
│     │        ├─ continuous_tf → ctle_iir=None
│     │        └─ bilinear_iir → COMBilinearCTLE
│     └─ _build_paths()                                      [ALG-001/006 config resolver / fanout]
│        └─ _build_path() × victim / NEXT / FEXT
│           ├─ SparamModel.completed_voltage_transfer_function() [ALG-001 L5 owner]
│           ├─ LinkSegment.from_tf()                         [ALG-006 analysis-grid direct injector]
│           │  └─ resample_tf()                              [ALG-006 L5 owner]
│           └─ CTLE pulse-realization block                  [same ALG-007 L3 owner: per-path]
│              └─ _realize_ctle_pulse() × pulse / victim pulse_no_txffe [ALG-007 L4 execution decision]
│                 ├─ continuous_tf                           [uses analysis-grid H21; ALG-006 upstream-folded]
│                 └─ bilinear_iir → _reference_fd_to_td_record() [ALG-006 finite-record direct injector]
│                    └─ resample_tf()                        [same ALG-006 L5 owner]
├─ L1 Domain — Pre-DTE model
│  ├─ calculate_pre_dte_imp_common()
│  ├─ prepare_pre_dte_phase_inputs()
│  │  └─ _select_xtalk_path_phase()                          [full-response preparation]
│  ├─ calculate_pre_dte_imp_at_pos()                         [per-phase domain operation]
│  │  ├─ _calculate_tx_noise_eq_ch()                         [ALG-006/007 upstream-folded consumer]
│  │  └─ PMF retained-mass consumer                          [NUM-006 pending owner/scope]
│  └─ _build_pre_dte_psd()                                   [NUM-003 / ALG-008 L3 owner]
│     ├─ resolve one record_cfg                               [NUM-003 dispatch]
│     ├─ realize S_rn/S_xn/S_tn/S_jn on that record
│     ├─ resolve clipping noise + CDF tail                    [ALG-008 dispatch]
│     │  ├─ full jitter + P_qc/2
│     │  └─ RJ-only jitter + P_qc
│     ├─ _build_psd_adc_qn(...)                               [fixed executor / non-owner]
│     │  └─ _calculate_V_qc(...)                              [PMF helper / non-owner]
│     ├─ _resolve_adc_input_pmf_config()                      [NUM-004 L4 owner; execution point 1]
│     │  └─ COMPMFGridControl.resolve_dy()                    [L5 shared grid kernel]
│     └─ sum S_total and form R_n                             [one atomic owner boundary]
├─ L1 Control — Sampling search
│  └─ _run_once() phase-search loop                          [SRCH-001 concrete owner]
│     ├─ resolve pos_sweep_method / pos_coarse_stride        [sole selector read]
│     ├─ _initial_pos_sweep_indices(...)                     [concrete-choice helper]
│     ├─ one shared initial/fine phase-batch loop
│     ├─ _fine_pos_sweep_indices(...)                        [concrete-choice helper]
│     ├─ strict minimum-MSE complete-bundle retention
│     ├─ COMRunStatus coarse/fine/MSE/error records
│     └─ _assign_selected_phase()                             [commit validator; non-owner]
├─ L1 Domain — DTE solver
│  ├─ calculate_MMSE_DTE()                                   [ALG-010 selector injector; non-owner]
│  │  └─ inject cfg.alg.floating_mode
│  ├─ COM_MMSE_DTE.run() floating tap/group solve            [ALG-010 L3 concrete owner]
│  │  ├─ _select_floating_tap_by_isi()                        [heuristic executor; non-owner]
│  │  ├─ _select_floating_tap_onetime()                       [simplified executor; non-owner]
│  │  ├─ _calculate_float_ffe_178A()                          [spec-defined executor; non-owner]
│  │  └─ solve／limit／MSE／COMDTEStatus lifecycle
│  └─ COMDTEStatus.H_rxffe                                   [bound to pre-DTE record after solve; non-owner]
├─ L1 Domain — Post-FFE model
│  ├─ _apply_rxffe_response()                                [ALG-011 provisional owner]
│  │  └─ COMPostFFEEqChannelStatus                           [DFE／MLSD consumer record]
│  ├─ _resolve_adc_input_pmf_config()                        [same NUM-004 L4 owner; execution point 2]
│  │  └─ COMPMFGridControl.resolve_dy()                      [same L5 shared grid kernel]
│  └─ transform pre-DTE PSDs on their existing record        [NUM-003 non-owner]
├─ L1 Domain — DFE COM model / final PMF
│  ├─ _resolve_final_com_pmf_config()                        [NUM-005 L4 owner; execution point 1]
│  │  └─ COMPMFGridControl.resolve_dy()                      [L5 shared grid kernel]
│  ├─ calculate_COM_DFE() component／combined PMFs           [NUM-005 direct consumer]
│  ├─ calculate_COM_DFE() final V_qc selection               [ALG-012 provisional; evidence pending]
│  └─ calculate_COM_DFE() final ADC PMF projection           [ALG-013 provisional]
├─ L1 Domain — MLSD model
│  ├─ _resolve_final_com_pmf_config()                        [same NUM-005 L4 owner; execution point 2]
│  │  └─ gaussian_addition → solve_g_an()／evaluate_delta_com_an()
│  │     [direct consumer; rebuild p_G_an on final-domain dy]
│  ├─ scaled_total_pdf → reuse DFE COM PMFs                  [NUM-005 indirect consumer]
│  ├─ solve_g_an() added-noise PDF                           [ALG-014 provisional]
│  ├─ build_mlsd_noise()                                     [NUM-003 L3 owner + ALG-015 provisional]
│  │  ├─ resolve MLSD record_cfg and rebuild component PSDs
│  │  └─ Eq. 178A-54 composition → S_ni／R_ni
│  ├─ calculate_der_mlsd() recurrence termination            [ALG-016 provisional]
│  └─ calculate_COM_MLSD() reported DER formation            [ALG-017 provisional]
└─ Cross-domain L5 PMF operations
   ├─ model helpers(..., pmf_projection_method)              [ALG-002 injectors]
   │  └─ Pmf1D.multi_dirac()/scale_x()/resample_dx()/fir_filter() [ALG-002 owner set]
   │     └─ Pmf1D._project_to_grid()                         [private kernel; non-owner]
   ├─ Pmf1D.gaussian()/uniform() PDF→PMF                     [ALG-003 L5 owner set]
   └─ MLSD scalar-PMF scaling
      ├─ _build_scaled_total_pdf_added_noise()               [ALG-004 direct injector]
      ├─ calculate_der_mlsd()                                [ALG-004 direct injector]
      └─ Pmf1D.scale_x()                                     [ALG-004 L5 owner]
```

當完整審查改變 owner 時，只修改本樹與上方分類表的正式結論；domain 文件只在
實際 I/O、function ordering、dataclass ownership 或 data handoff 改變時更新。

`COMRunConfig` 只存在於 workbook adapter 的 profile compatibility boundary。
Adapter 選定 run mode 後，canonical runtime fields 為 `cfg.alg`、`cfg.num`、
`cfg.exe`；runtime domain function sets 不讀取或傳遞 `COMRunConfig`。
`cfg.num.pmf_grid_quality` 是 legacy profile resolution 的 effective record；
canonical voltage-grid semantics 仍由 `adc_input_pmf_grid` 與
`final_pmf_grid` 決定，不把它另列為 selectable branch。

### Canonical SRCH domain

`COMConfig.srch: COMSearchConfig` 是唯一 178A SRCH runtime group：

- candidate axes：`c_m2_values`、`c_m1_values`、`c_1_values`、
  `g_DC_values`、`g_DC2_values`；scalar 與 length-one vector 等價，任一
  multi-value axis 由 outer runner 形成 Cartesian product；
- phase coverage：`pos_sweep_method`、`pos_coarse_stride`，只由 `_run_once()`
  Sampling-search control block 讀取；
- retention/error policy：`keep_top_n`、`keep_all_rows`、
  `continue_on_error`；
- orchestration：`group_size`、`final_top_k`。

Outer runner 解析 candidate 後，同時把 scalar 值寫入 physical filter 與
scalar-only `cfg.srch`。`COM.run()` 拒絕未解析的 multi-candidate SRCH state；
candidate ranking、Stage formulas 與 execution target 不屬於此 config migration。

The former E-007 final-quantization tap-accumulation item has no selectable
runtime control, so it receives no selectable-control ID. It remains a deferred
technical issue: production ordering is frozen until PMF seed, main-tap
contribution, projection/support, and `ALG-013` interaction are resolved.

### Legacy ID mapping

| Legacy ID | Current ID | Note |
|---|---|---|
| B-001 / B-002 / B-003 | — / `ALG-006` / `ALG-007` | B-001 retired：178A S4P 固定依 D3.2 先做 single-ended renormalization；native S2P 僅為 input dispatch。B-002/B-003 仍是 Stage 1 branches。 |
| B-004 / B-005 / B-006 / B-007 | `ALG-011` / `NUM-003` / `ALG-008` / `ALG-012` | Reordered by earliest stage and class |
| B-008 | `ALG-002` | L5 public `Pmf1D` target-grid projection function set |
| B-009 | — | Retired selector; historical ID only |
| B-010/B-011 | `ALG-003` | Merged shared PDF→PMF control |
| B-012 / B-013 / B-014 / B-015 | `ALG-004` / `NUM-005` / — / `ALG-013` | B-014 retired：178A Gaussian support 固定 8σ，不再是 Project Config；B-013 remains the independent final-domain grid resolver consumed in Stages 6／7 |
| B-016 / B-017 / B-018 | `ALG-014` / `ALG-016` / `ALG-017` | Stage 7 ordering follows production flow |
| B-019 / B-020 / B-021 | `ALG-001` / — / `ALG-015` | B-020 retired as a selectable control：`force_grid=False` is diagnostic utility behavior, not Project Config；B-021 remains Stage 7 PSD |
| E-001 / E-002 / E-003 / E-004 | — / — / `NUM-004` / `NUM-006` | E-001 是 `cfg.exe.target` non-branch execution control；E-002 retired with ALG-009 after exact PMF became fixed behavior；E-003/E-004 依實際 function-set effect 歸入 NUM。 |
| E-005 / E-006 / E-007 | — / `SRCH-001` / — | E-005 曾同時指 RX FFE tap-layout mapping defect 與 floating-mode inventory，存在 ID collision；不得作為 ALG-010 已審查證據。E-007 is a deferred non-selectable issue。 |

## 不是分支的項目

| 項目 | 分類與原因 |
|---|---|
| `src.channel.victim/next/fext` binding | **Source/input configuration**。`path`、`representation`、`port_order` 選擇並解讀 artifact；`COMSourceConfig.ChannelBinding.load()` 負責載入與驗證，unsupported representation 不得 fallback。它不選擇同一 semantic operation 的平行方法，因此不建立 `SRC-001` branch。 |
| `exe.target`（legacy E-001） | **Execution control**。`mse/dfe/mlsd/all_enabled` 只決定 pipeline 執行範圍；`COM._run_once()` 不因 target 改變任何已執行 stage 的公式或 method，因此不建立 `EXE-001` branch，也不參加 ownership review。 |
| `channel.sparam_frequency_limit_Hz` | **輸入邊界**。描述實際送入 reader 的有效量測上限；execution profile 不得把任意 100 GHz 檔案暗中裁成 67 GHz。`ALG-006` 只決定此邊界外如何處理。 |
| B-001／retired `ALG-005` channel renormalization selector | **固定規範行為＋input representation dispatch**。有 measured S4P 時，178A 依 D3.2 先將 single-ended S-parameters renormalize 至 `R0`，再轉 mixed-mode Sdd；只有 native differential S2P 才在 Sdd domain renormalize 至 `2*R0`。`_build_channel_under_test()` 是唯一語意 owner；失敗不得 fallback，`_build_path()` 不再 renormalize。 |
| legacy E-002／retired `ALG-009` pre-DTE PMF method | **固定 exact-PMF 行為**。Cost/accuracy review 顯示 Gaussian approximation 僅節省約 1.5–2% candidate evaluation，卻實質改變 `V_qc`、MSE 與 selected phase，因此 selector 已移除；`_build_psd_adc_qn()` 固定執行 exact PMF。Legacy workbook `pmf_exact` row 僅維持 read compatibility。 |
| `alg.xtalk_pmf_accumulation` | **固定行為**。目前唯一合法值是 `pathwise_convolution`，沒有 A/B 分支能力；保留是待清理的 API 欄位。 |
| TX FFE discrete filter 與 `LinkSegment.cascade_ir()` | **等價實作**。對 oversampled pulse 做 shift-sum／convolution，不屬 CTLE branch。 |
| sinc／boxcar unit-pulse 表示 | **等價表示**。對齊 transfer function 與時間原點後不建立平行算法。 |
| RX package `reverse_ports()` | **共同正確流程**。die-to-channel network 建立後交換 two-port port orientation，不提供錯誤舊法作分支。 |
| Eq. 178A-49 `(-1)^(j+1)` | **共同公式修正**。不是 Annex/reference 平行方法。 |
| final quantization FIR 是否「包含 main tap」 | **不是 `ALG-012` 分支**。它是 PMF seed／FIR accumulation 的等價實作問題；目前 production ordering 依 deferred final-quantization accumulation issue 凍結。 |
| B-009 `interference_pmf_method` | **已移除的非必要分支**。`signal_fir` 與 `pam_atoms` 的差異源自過早 grid projection；固定採 exact PAM atoms → tap scaling → grid projection → convolution。Runtime config、preset 與 workbook 不再提供 B-009 selector。 |
| `SampledPSD.filtered_by()` grid matching | **固定 utility contract**。輸入 grid 不一致即由 caller 先處理；沒有隱藏 auto-regrid branch。 |
| `cascade_ir(force_grid=False)` | **診斷／caller-owned utility behavior**。可回傳完整 linear-convolution record，或由 caller 明示 `output_cfg`；它不是獨立 Project Config branch。ALG-011 only uses it behind the Stage 5 owner after the record grid is resolved. |

### `ALG-002` 二次審查證據

| Item | Record |
|---|---|
| Status | **Closed 2026-11-11**。Helper ownership convergence 已由 isolated commit `b417b8c` 整合並推送；權威 owner tree 已由 `c804e3c` 整合。 |
| Code convergence | `_calculate_V_qc()`、`_build_psd_adc_qn()`、`_build_adc_input_pmf_exact()`、`_reconstruct_final_vqc_sicopr()` 不再接收 `COMAlgorithmPolicyConfig`，只接收 concrete `pmf_projection_method`；`pdf_to_pmf_method` 維持獨立 concrete argument。 |
| Preserved boundary | PAM source 保持 exact natural-grid atoms；B-009 不恢復；`tap_abs_th`、retained mass、ALG-003 與 ALG-004 都是獨立決策。 |
| Validation | Focused `47 passed`；Python 3.7 export validation passed；固定 SiCoPR golden `1 passed`，DFE COM `1.5247607834259893 dB`、final COM `2.895898684873246 dB` 與 intermediate digests 不變。 |

### `ALG-003` 二次審查證據

| Item | Record |
|---|---|
| Status | **Closed 2026-11-11**。Protected implementation `e65f644` 已整合並推送；權威文件 commit `c804e3c` 已建立；本 closure-state commit 同步 Registry、active state、handoff 與 TC-025 record。 |
| Owner | L5 public `Pmf1D.gaussian()`／`uniform()` constructor set；model helpers 只注入 concrete `pdf_to_pmf_method`，不保存 policy。 |
| Code convergence | Gaussian `pmf_sample` extent 從 `2 * n_sigma` 收斂為 `n_sigma`；178A 的 `bin_integral`／`pmf_sample` 都使用固定 ±8σ initial support。Uniform distribution-specific rule 不變。 |
| Preserved boundary | ALG-002 projection、ALG-004 scaling、NUM-006 retained mass、93A default `bin_integral`、config/workbook schema 均不變。 |
| Validation | Focused `47 passed`；Python 3.7 export validation passed；固定 SiCoPR golden `1 passed`，既有 MSE／COM_DFE／final-COM tolerance 與三個 intermediate digests 全數通過。 |

### `ALG-004` 二次審查證據

| Item | Record |
|---|---|
| Status | **Closed 2026-11-11**。使用者核准 signed-scale contract；implementation／test／export／technical docs 已由 isolated commit `114e7bf` 整合並推送。 |
| Owner / consumers | L5 public `Pmf1D.scale_x()` 是 sole semantic owner；Stage 7 `_build_scaled_total_pdf_added_noise()` 與 `calculate_der_mlsd()` 只注入 concrete `pmf_scaling_method`／`pmf_projection_method`。 |
| Code convergence | `interpolate_ordinates` 對 `+a`／`-a` 使用相同 `abs(a)` output grid；負值只反轉 ordinates。Public signature、positive-scale result 與 zero-scale behavior 不變。 |
| Preserved boundary | `mass_deposit` 才委派 ALG-002 placement；`interpolate_ordinates` 不讀 projection choice。`fir_filter()` 固定使用 `mass_deposit`，不是 ALG-004 consumer。ALG-003、grid、retained mass、config/profile 與 93A 不變。 |
| Validation | Focused PMF／MLSD／profile tests `49 passed, 2 subtests passed`；Python 3.7 export validation passed；fixed SiCoPR golden `1 passed`，既有 MSE／COM_DFE／final-COM tolerance 與三個 intermediate digests 全數通過。 |

### `ALG-010` 完整初次審查證據

| Item | Record |
|---|---|
| Status | **Closed 2026-11-12**。保留 `heuristic`／`simplified`／`spec-defined` 三種 floating tap/group strategies；production code 不需修改。 |
| Owner / injector | L3 `COM_MMSE_DTE` 是 semantic owner，`COM_MMSE_DTE.run()` 是 concrete callable owner；`COM.calculate_MMSE_DTE()` 只注入 resolved `cfg.alg.floating_mode`，不是 owner。三個 strategy helpers 是 executor，不能各自宣稱 ownership。 |
| Complete operation | Owner 內完成 selector dispatch、placement 所需 solve、limiter/refinement、MSE 與 coherent `COMDTEStatus` publication；`N_wg=0` 固定繞過三個 floating strategies。 |
| Preserved boundary | 不改 strategy 算法、equal-score tie-break、MMSE/KKT equations、coefficient limits、phase search、profile/default 或 golden tolerance。 |
| Validation | `tests/test_com_model_178A_floating_mode.py` focused `7 passed`：static audit 確認 operational selector read 只在 `run()`；三種 selector 各命中唯一 executor，且三種 mode 在 `N_wg=0` 均不進入 floating selector；每次都驗證完整 status shape、finite MSE 與 solver-level `H_rxffe=None`。與既有 policy tests 合跑 `42 passed`（workspace basetemp；792 個既有 skrf deprecation warnings）。Production numerical path 未變，因此不重跑 golden，也不建立 reference-equivalence claim。 |

## 實作入口與驗證證據

| 範圍 | 主要實作入口 | 主要驗證 |
|---|---|---|
| Channel representation normalization（fixed/input dispatch） | `models/com_178a/path_stage.py::_build_channel_under_test()` + `utilities/sparam.py` 的具名 representation methods | `tests/test_channel_renormalization.py`、`tests/test_sparam_synthetic_s4p.py` |
| High-frequency handling | `LinkSegment.from_tf()`、`_reference_fd_to_td_record()`、`utilities/link.py::resample_tf()` | `tests/test_sparam_out_of_measured.py`、`tests/test_com_model_178A_ctle_pulse.py` |
| CTLE pulse realization | `_build_shared_path()`、`_prepare_ctle_pulse_realization()`、`_realize_ctle_pulse()`；`COMPath.pulse_no_txffe` | `tests/test_com_model_178A_ctle_pulse.py` |
| RX FFE record | `COM._resolve_post_ffe_response_cfg()`、`_apply_rxffe_response()`；DFE/MLSD consume recorded grids | `tests/test_com_model_178A_post_ffe.py`、`test_com_model_178A_mlsd_noise.py`、CTLE pulse tests |
| Eq-channel impairment record／MMSE inputs | Pre-DTE `COM._build_pre_dte_psd()`；MLSD `COM.build_mlsd_noise()`；`_select_xtalk_path_phase()` 明確是 non-owner | policy ownership test、`tests/test_com_model_178A_mlsd_noise.py`、SiCoPR golden |
| Floating FFE strategy | L3 `COM_MMSE_DTE.run()`；`COM.calculate_MMSE_DTE()` 只注入 `cfg.alg.floating_mode` | `tests/test_com_model_178A_floating_mode.py` |
| PMF branches | `_build_pmf_interference_178A()`、`_build_pmf_G()`、ADC/final PMF builders | `tests/test_pmf_reference_methods.py`、policy tests |
| MLSD branches | `solve_g_an()`、`build_mlsd_noise()`、`calculate_der_mlsd()`、`calculate_COM_MLSD()` | `tests/test_com_model_178A_mlsd_flow.py`、`test_com_model_178A_mlsd_noise.py`、`test_com_model_178A_mlsd_eq47.py` |
| Fixed-grid cascade | `utilities/link.py::LinkSegment.cascade_ir()`、`SampledResponse.cascade_ir()` | `tests/test_fixed_grid_contract.py` |

## 維護檢查表

任何 branch change 必須在同一變更中完成：

1. 更新本文件的分類 row（含 project default 與 reference selection）、ownership/function-position tree、責任邊界與驗證證據。
2. 只有 runtime field 實際改變時才更新 `config_tree.md`；只有 pipeline／stage I/O 或 function ordering 實際改變時才更新 `call_tree.md` 與相應 stage 文件。不得為了保存 branch owner 結論而複製另一份表。
3. 依 Branch Behavior Contract 明確分類為 branch、branch parameter、non-branch runtime control、input/source boundary 或 fixed behavior；runtime domain 本身不等於 branch 類別。
4. 寫出 project default、所有合法 alternate、哪些 versioned execution profiles 會覆蓋，以及互相依賴的欄位。
5. 列出會改變與不得改變的中間量，並提供 branch isolation test。
6. 新增 reference-only 分支時保留 general method，不得用 reference 接近度取代公式正確性判定。
7. 若發現 general method 錯誤，依 Core Model Change Contract 直接修正共同流程，不保留已知錯誤作平行分支。
8. 關閉前同步 `active_contracts.md` 與 `HANDOFF.md`，完成 scoped diff review，並建立 isolated commit；若使用者核准 batch integration，則在 commit 完成前維持 `Implemented / validation passed — integration pending`。
