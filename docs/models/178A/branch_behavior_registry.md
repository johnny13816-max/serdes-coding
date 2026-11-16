# 178A 分支行為登錄表

狀態：**authoritative**  
最後核對：2026-11-15

本文件是 178A model 分支行為的唯一權威紀錄，集中保存分類總表與
ownership/function-position tree。新增、修改、重新命名、合併、移除或二次審查
branch behavior 時，必須在同一變更中更新兩者。Stage 文件只保存 stage I/O 與
execution detail；`call_tree.md` 只保存 pipeline flow，不再各自維護 branch owner
結論。歷史 change contract 說明決策過程；本文件描述目前實作與 review state。

範圍包含 178A runtime 及其實際呼叫的 shared utility 分支；不把 178A 選項自動視為 93A 行為。若 93A 新增平行算法，應建立或更新對應的 `docs/models/93A/branch_behavior_registry.md`。

## Stage 1 adaptive grid

`alg.path_grid_mode`（`fixed`／`adaptive`）的 owner 為
`COM.build_all_paths()`；fixed 與 adaptive 已完成實作、適用驗證、受影響分支
審查及 production 遠端整合。
`num.fine_grid_df`、`num.relative_threshold`、
`num.absolute_threshold` 為 adaptive controls，不各自構成 branch；runtime
defaults 分別為 `1e6` Hz、`1e-3`、`None`。完整設計與待完成驗證見
[adaptive grid change contract](../../planning/178A_adaptive_grid_change_contract.md)。

## 判定規則

branch behavior、一般 config、execution strategy、input boundary、固定行為與
provenance 的正式定義，見 [Branch behavior contract](../../architecture/branch_behavior_contract.md)。
本表只授予通過 eligibility 的 selectable behavior branch identity。ID 的
`ALG`／`NUM`／`SRCH` 前綴記錄 selector 所在的 runtime domain，不是三種
branch classes，也不能單憑 config container 判定它是 branch。Physical fields、
`cfg.src` 與 `cfg.exe` 不建立 `PHY`／`SRC`／`EXE` branch ID；它們只在
「不是分支的項目」記錄必要 exclusion。

branch ID 是穩定識別碼：核准並登錄後，不因新增、移除、合併、Stage 調整或
owner／consumer 位置改變而重編或重用。新 branch 通過 eligibility 並核准後才核發
同一 ID prefix 的下一號；既有 unreviewed selector 暫沿用已登錄 ID 完成審查。若這類
項目後來判定為從未成立的 non-branch，移除該列但不回退序號。各類別序號只增不減，
退役 ID 永不重用。ID prefix 記錄 selector 所在 runtime domain，不編入 Stage 或排序資訊。

Next ID allocation cursor：`ALG-019`、`NUM-010`、`SRCH-002`。此 cursor 只記錄各類別
下一個可核發號碼，不建立舊 ID 對照或歷史映射。

本表依 Stage／function call tree 順序排列，不依 ID 數字排序。跨 Stage 或 shared
utility branch 列出唯一 owner 與全部 consumers，依 owner 在 call tree 的位置登錄；
不因 consumer 位於多個 Stage 而重複建立紀錄。完全位於 COM pipeline 外的 shared
utility 以 `Shared L5 utility` 表示，不虛構 Stage 0 owner。Stage 文件不另建平行分類表。

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
- `retired branch`：曾核准並取得 canonical ID，現已移除 runtime 選擇；只保留
  ID、退役原因與目前固定／替代行為，不提供可選 runtime values。

從未核准為 branch 的候選一旦判定為 non-branch，就不取得 ID，也不列入本表或
ownership tree；必要的分類理由可記於「不是分支的項目」。曾核准後退役的 branch
仍保留於本表，但移出 active ownership tree。Legacy ID mapping 不屬於本 registry；
依既定審查後清理時點，現行文件只保留 canonical ID，Git history 不改寫。

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

`sicopr_reference_v1` 只記錄 adapter 對 active branch 解析出的 concrete choice；它
不是另一套 branch 分類，也不建立新的 runtime owner。完整 profile 展開、override
與 provenance contract 由 `config_tree.md` 維護。Retired branch 的 selector 與 profile
choice 欄標示為 `none — retired`；不保留歷史 legal values 作為目前可選值。

| ID | Branch classification / lifecycle | Scope | Selector 與 project choices | `sicopr_reference_v1` | Semantic owner | Ownership review |
|---|---|---|---|---|---|---|
| `ALG-018` | active — algorithm_policy branch | Stage 1 path response grid | `alg.path_grid_mode`：`fixed`／`adaptive`；fine df 與 thresholds 為 numerical parameters | 不覆蓋；預設 `fixed` | **L1** `COM.build_all_paths()` | 已實作；分類與 project golden 已驗證；production 已整合 |
| `ALG-007` | active — approved branch | Stage 1 CTLE pulse realization | `alg.ctle_pulse_realization`：project default `continuous_tf`；另有 `bilinear_iir`／`bilinear_fine_grid` | `bilinear_iir` | **L4 owner set** `_prepare_ctle_pulse_realization()`／`_realize_ctle_pulse()` | shared setup 與 per-path realization 各自決策；focused 104 passed、project golden passed；production 已整合 |
| `ALG-001` | active — approved branch | Stage 1 path construction | `alg.missing_dc_policy`：project default `skrf`；另有 `error`／`hold`／`mag_phase_trend_to_dc` | `mag_phase_trend_to_dc` | **L5** `SparamModel.completed_voltage_transfer_function()` | **二次審查已確認** |
| `ALG-006` | active — approved branch | Stage 1 measured-grid scalar-transfer extension | `alg.out_of_measured`：project default `cosine_decay`；另有 `zero_padding` | `zero_padding` | **L5** `resample_tf()` | **Closed 2026-11-11** |
| `ALG-005` | retired — approved branch | Stage 1 channel renormalization | none — retired; S4P order fixed by D3.2 and S2P uses representation dispatch | none — fixed contract | — (retired; former owner `COM._build_channel_under_test()`) | Retired: fixed specification behavior and input representation dispatch; no runtime selector |
| `NUM-003` | active — approved branch | Stages 2／7 Pre-DTE 與 pre-MLSD PSD/correlation record | `num.eq_ch_imp_len`：`full`／`truncated`；`num.num_trunc_ui` 是 branch parameter | `truncated`；`num.num_trunc_ui=4096` | **兩個 L3 owner**：Pre-DTE `_build_pre_dte_psd()`；MLSD `build_mlsd_noise()` | XT window 已驗證並完成遠端整合 |
| `ALG-008` | active — approved branch | Stage 2 Pre-DTE PSD／per-phase ADC input | `alg.pre_dte_adc_clipping_convention`：`full_jitter_half_tail`／`rj_only_full_tail_reference` | `rj_only_full_tail_reference` | **L3** `COM._build_pre_dte_psd()` | **Closed 2026-11-12** |
| `NUM-006` | active — approved branch | Stages 2／5 ADC-input FIR-PMF convergence; direct consumers `_build_psd_adc_qn()` and `_build_adc_input_pmf_exact()` | `num.pmf_keep_mass`：`0 < value <= 1`；project `1-1e-5`；reference profile `1.0` | profile 值見 `config_tree.md` | **L5 owner** `Pmf1D.fir_filter()` | **Closed 2026-11-13** |
| `NUM-007` | active — review closed；reference evidence bounded | Stages 2／5／6／7 PMF convolution | `num.pmf_convolution_method`：`fft`／`linear`；project 預設 `fft` | `linear` | **L5 owner set** `Pmf1D.fir_filter()`／`Pmf1D.combine()` | 已討論選項與兩個 owner、核准並整合 `564aac4`；focused 78 passed、FFT golden 與 linear fixed case 通過。證據見 `docs/validation/178A_pmf_convolution_evidence.md`；未宣稱全面 reference 對齊 |
| `NUM-004` | active — approved branch | Stages 2／5 ADC-input PMF grid | `num.adc_input_pmf_grid.*`：`relative_As_with_cap`／`relative_As`＋grid parameters；`dy_override` 優先 | `relative_As_with_cap`；`dy_override=10e-6 V` | **L4** `_resolve_adc_input_pmf_config()`；L5 shared kernel `COMPMFGridControl.resolve_dy()` | **Closed 2026-11-12** |
| `ALG-009` | retired — approved branch | Stage 2 Pre-DTE PMF method | none — retired; exact PMF is fixed | none — fixed exact-PMF contract | — (retired; former execution point `_build_psd_adc_qn()`) | Retired: Gaussian approximation altered `V_qc`, MSE and selected phase for only 1.5–2% evaluation savings; exact PMF is fixed |
| `SRCH-001` | active — approved branch | Stage 3 Sampling search control | `srch.pos_sweep_method`：`each_phase`／`coarse_fine`；`pos_coarse_stride` 是 branch parameter | 不覆蓋 | **L1 owner** `COM._run_once()` 中完整且刻意展開的 Stage 3 control block | **Ownership corrected 2026-11-13** |
| `ALG-010` | active — approved branch | Stage 4 DTE solver | `alg.floating_mode`：`heuristic`／`simplified`／`spec-defined` | 不覆蓋 | **L3 semantic owner** `COM_MMSE_DTE`；**concrete owner** `COM_MMSE_DTE.run()` | **Closed 2026-11-12** |
| `ALG-011` | retired — approved branch | Stage 5 RX FFE record realization | none — retired; fixed circular convolution | none — fixed contract | — (retired; former Stage 5 owner `_apply_rxffe_response()`) | Retired: the Stage 5 contract now uses fixed circular convolution; former selectable realization methods were removed. |
| `NUM-005` | active — approved branch | Stages 6／7 final-domain PMF grid | `num.final_pmf_grid.*`：`relative_As_with_cap`／`relative_As`＋grid parameters；`dy_override` 優先 | `relative_As`；`dy_override=None` | **L4** `_resolve_final_com_pmf_config()`；L5 shared kernel `COMPMFGridControl.resolve_dy()` | **Closed 2026-11-12** |
| `ALG-012` | active — review closed；reference evidence bounded | Stage 6 DFE COM final clipping | `alg.final_com_vqc_convention`：`selected_phase_adc_input`／`sicopr_final_reconstruction` | `sicopr_final_reconstruction` | **L3** `COM._build_final_adc_quantization()` | fixed-input SiCoPR clipping 與 component 對照通過；reference tap 跳過非完整 FIR 模型；零係數 `S_in` 議題依使用者決定延後，不宣稱所有案例對齊 |
| `ALG-013` | active — review closed；reference evidence bounded | Stage 6 DFE COM final ADC PMF | `alg.final_adc_pmf_projection`：`annex_d3`／`reference_support` | `reference_support` | **L3** `COM._build_final_adc_quantization()` | Stage 6 owner、兩種選項與互斥驗證已確認；SiCoPR fixed-input PMF 與 fixed-case COM 已對照。NUM-007 控制卷積；不宣稱通用 reference equivalence |
| `ALG-014` | active — review closed | Stage 7 MLSD added noise | `alg.added_noise_pdf`：`gaussian_addition`／`scaled_total_pdf` | `scaled_total_pdf` | **L3** `COM._build_mlsd_added_noise()` | Our branch Gaussian 增量；reference 以 PMF 二階矩差對齊 SiCoPR；focused 56 passed，fixed case 符合 golden 容差 |
| `ALG-015` | active — review closed | Stage 7 MLSD noise PSD | `alg.mlsd_quantization_psd`：`pre_dte_filtered`／`main_tap_white` | `main_tap_white` | L3 `build_mlsd_noise()` | our 使用完整 RxFFE；reference 在 unit-main 尺度重算 clipping 與 white `S_qn`，轉回專案尺度；fixed case 與 SiCoPR 對照通過 |
| `NUM-008` | active — review closed | Stage 7 MLSD DER 加總停止 | `num.mlsd_stop_method`：`fixed_length`／`relative_tail`；後者門檻 `1e-4` | `relative_tail` | **L3** `calculate_der_mlsd()` | 早停回傳已計算項；SiCoPR 同輸入及固定 golden 驗證通過 |
| `NUM-009` | active — validated；integration pending | Signal／ISI／XT／DDJ PMF response-tap 篩選 | `num.response_tap_threshold`：`None` 使用各 PMF 的 `dy`；非負數為 V；`0` 保留所有非零 taps | `None` | **L5** `Pmf1D.fir_filter()` | 設定與 FFE 行為已驗證；reference golden 通過，fixed-case FFE 隔離對照不變；尚待獨立提交與遠端整合。 |
| `ALG-016` | active — review closed | Stage 7 MLSD DER recurrence | `alg.sequence_termination`：`fixed_length_sum`／`matlab_relative_tail` | `matlab_relative_tail` | **L3** `calculate_der_mlsd()` | 選擇 penalty 與沿用既有 CDF 取點；停止控制分至 NUM-008；SiCoPR 邊界對照通過 |
| `ALG-017` | retired — approved branch | Stage 7 MLSD reported DER | none — 兩種 DER 固定分別記錄 | none | — | 移除輸出選擇；計算用 DER 與 SiCoPR-style diagnostic 各自保存，不影響 COM |
| `ALG-002` | active — approved branch | Cross-stage PMF target-grid projection (Stages 3／5／6／7); consumers `_calculate_V_qc()`、`_build_psd_adc_qn()`、`_build_adc_input_pmf_exact()`、`_reconstruct_final_vqc_sicopr()`、`calculate_der_mlsd()` | `alg.pmf_projection_method`：`linear`／`nearest` | `nearest` | **L5 owner set** `Pmf1D.multi_dirac()`／`scale_x()`／`resample_dx()`／`fir_filter()` | **Closed 2026-11-11** |
| `ALG-003` | active — approved branch | Cross-stage PDF→PMF shared utility; consumers `_calculate_V_qc()`、`_build_psd_adc_qn()`、`_build_adc_input_pmf_exact()`、`_build_pmf_G()`、`_reconstruct_final_vqc_sicopr()`、`evaluate_delta_com_an()`、`solve_g_an()`、`calculate_der_mlsd()` | `alg.pdf_to_pmf_method`：`bin_integral`／`pmf_sample` | `pmf_sample` | **L5 owner set** `Pmf1D.gaussian()`／`uniform()` | **Closed 2026-11-11** |
| `ALG-004` | active — approved branch | Stage 7 MLSD fixed-grid scalar-PMF scaling; consumers `_build_scaled_total_pdf_added_noise()` and `calculate_der_mlsd()` | `alg.pmf_scaling_method`：`mass_deposit`／`interpolate_ordinates` | `interpolate_ordinates` | **L5** `Pmf1D.scale_x()` | **Closed 2026-11-11** |
## Numerical control 盤點與審查狀態

本盤點同時包含分支及數值參數，避免只看分支分類表而漏掉影響精度的控制。待核對表示目前尚未找到足夠的完整審查證據，不代表已證明從未討論；是否另成分支亦未預先決定。

| 控制 | 現況與已知證據 | 後續狀態 |
|---|---|---|
| `num.eq_ch_imp_len`／`num_trunc_ui` | NUM-003；PSD record 長度。 | owner、full／truncated 和後續 XT 先選 phase 再選最大能量 window 已討論、核准並驗證；不宣稱固定案例可證明所有數值設定的精度。 |
| `num.adc_input_pmf_grid.*` | NUM-004；ADC-input PMF 間距及 override。 | 選項、override 優先權、scope、owner 與 fixed golden 已於 `e003_pmf_grid_numerical_control.md` 核准及驗證；不因欠缺跨案例精度研究而重列未審。 |
| `num.final_pmf_grid.*` | NUM-005；final PMF 間距及 override。 | 選項、override 優先權、scope、owner 與 fixed golden 已於 `e003_pmf_grid_numerical_control.md` 核准及驗證；跨案例精度／成本不屬既有結案宣稱。 |
| `num.pmf_keep_mass` | NUM-006；ADC-input PMF 卷積保留機率質量。 | 完整初次審查與驗證已完成。 |
| `num.pmf_convolution_method` | NUM-007；FFT／linear。 | 已討論選項及 owner，核准實作並驗證；不因文件標籤不一致重列未審。 |
| `num.mlsd_stop_method` | NUM-008；MLSD DER 加總停止方式。 | 與 ALG-016 一併討論、核准及驗證。 |
| `num.response_tap_threshold` | NUM-009；response PMF tap 絕對門檻，`None` 跟隨 dy。 | 契約已實作並驗證；獨立提交與遠端整合待完成。 |
| `num.fine_grid_df`、`num.relative_threshold`、`num.absolute_threshold` | ALG-018 adaptive grid 的數值參數；曾於 adaptive grid 設計契約討論，預設依現行 config。 | 設計、初始 1 MHz／relative `1e-3` 選擇與功能驗證已完成；門檻的跨案例收斂屬後續實驗，不因此重列為未審分支。 |
| `num.pmf_grid_quality` | coarse／fine 的 legacy profile effective record。 | 178A 的 ADC resolver 隨即覆寫 dy，final resolver 固定 fine 後亦覆寫 dy；不改變這兩條 production resolver 的有效 dy。移除或相容性變更尚未核准。 |
| `pmf.tap_rel_As`／`pmf.tap_abs_th_override` | legacy-compatible PMF tap 門檻欄位。 | 178A response taps 現由 `num.response_tap_threshold` 控制；ADC FFE 不再依這兩欄篩選。欄位保留以免擴大相容性變更，不假設其他版本或外部 callers 可直接移除。 |
| `pmf.dy_override`／`dy_rel_As`／`dy_abs_max`／`keep_mass` | `COMPMFConfig` 的 legacy-compatible 欄位；canonical numerical families 和實際 override 邊界見 `config_tree.md`。 | 178A ADC／final resolvers 會覆寫 resolved dy 與 keep_mass；這不代表外部直接呼叫 `COMPMFConfig.resolve()` 或 adapter compatibility 可無條件移除。 |

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
| `ALG-018` | 決定 Stage 1 固定或 adaptive path grid 建立方式及輸出 paths；影響 response 表示和後續計算 | downstream stage 不讀取 selector；NUM-003 PSD record、CTLE realization 與 threshold 數值保持獨立 |
| `NUM-003` | 在 pre-DTE／pre-MLSD PSD owner 內建立 `full` 或固定 `num_trunc_ui` record；truncated 的 XT 先選完整 response phase，再選最大能量 window，其他 response 取前段；過短補零，再建 PSD 並加總 | Path response、完整 `eq_ch` status、Sampling search、DTE solve、Post-FFE reporting transform、response grid |
| `SRCH-001` | 要評估的 phase schedule、coarse/fine visit order、最低 MSE complete bundle 與 per-phase run status | Pre-DTE model、DTE solver／ALG-010、XT independent-phase preparation、post-selection domains |
| `ALG-008` | per-phase `V_qc → delta → S_qn → R_n` clipping convention | final ADC PMF；後續結果只可能經 selected phase/taps 間接受影響 |
| `NUM-004` | Pre-DTE 與 selected-phase Post-FFE ADC-input PMF 的 voltage spacing；override／relative／capped-relative resolution | NUM-005 final PMF grid、NUM-006 retained mass、PMF projection／PDF discretization、NUM-003 PSD record grid |
| `NUM-005` | DFE component／combined PMFs 與 MLSD added-noise PMF 的 voltage spacing；override／relative／capped-relative resolution。Gaussian-replacement flow 直接使用 resolved grid；`scaled_total_pdf` flow 間接沿用 DFE PMFs | NUM-004 ADC-input PMF grid、NUM-006 retained mass、PMF projection／PDF discretization／scalar scaling、MLSD PSD record grid |
| `NUM-006` | 每個 tap convolution 後對 intermediate PMF 做對稱尾端截斷並重新正規化；`1.0` 關閉截斷。Stage 2／5 是 direct consumers | NUM-004／005 grid spacing、tap threshold、ALG-002 projection、ALG-003 PDF discretization、ALG-008 clipping、NUM-003 PSD record；Stage 6 final PMF 固定 `keep_mass=1.0`，不是此 branch consumer |
| `NUM-007` | PMF FIR 及 PMF 加總使用 FFT 或直接線性卷積；Stages 2／5／6／7 | PMF grid、tap threshold、keep mass、projection 與 93A default 獨立 |
| `NUM-009` | Signal／ISI／XT／DDJ PMF response-tap 篩選；ADC-input 與 final domain 使用各自解析的門檻 | ADC FFE taps 不使用此門檻；PMF grid、retained mass、卷積方式與 93A 獨立 |
| `ALG-010` | floating tap/group selection strategy；owner 依 resolved selector dispatch，並控制該 placement 的完整 solve／limit／MSE／`COMDTEStatus` lifecycle | fixed-tap limiter definition、MMSE/KKT equations、coefficient limits、phase search、equal-score tie-break implementation |
| `ALG-012` | final-COM clipping voltage convention | final-quantization main-tap accumulation issue |
| `ALG-013` | final ADC quantization PMF projection/support | pre-DTE ADC PMF；reference option 對 ALG-012 有相依但不合併 owner |
| `ALG-014` | added-noise PDF construction | `S_isi`、`S_ni` definitions |
| `ALG-015` | Eq. 178A-54 的 MLSD quantization-noise PSD composition | MMSE noise、RxFFE taps、`S_an`、`S_isi`、DER solver |
| `ALG-016` | DER recurrence termination | Eq. 178A-49 的共同 sign definition |

## 分支 ownership / function-position tree

本樹是所有 active 178A branches、unreviewed selectors 與 pending candidates 在 semantic
function call tree 中的位置總表。Retired branches 保留於上方分類總表，不出現在本 active tree；
從未核准的 fixed/non-branch behavior 不取得 branch identity，也不列入本樹。
`[owner]` 表示目前登錄的最低 semantic owner；`[injector]` 只解析或注入 concrete
choice；`[consumer]` 使用結果但不擁有 branch；`[provisional]` 表示完整初次
review 尚未完成。

```text
COM model
├─ L1 Stage 1 / Domain — Path realization
│  ├─ COM.build_all_paths()                                  [ALG-018 L1 owner: fixed / adaptive]
│  └─ L2 path-realization function set
│     ├─ _build_shared_path()                                [ALG-007 config resolver / shared coordinator]
│     │  └─ _prepare_ctle_pulse_realization()                [ALG-007 L4 owner: shared setup]
│     │     ├─ continuous_tf → ctle_iir=None
│     │     └─ bilinear_iir / bilinear_fine_grid → COMBilinearCTLE
│     └─ _build_paths()                                      [ALG-001/006 config resolver / fanout]
│        └─ _build_path() × victim / NEXT / FEXT
│           ├─ SparamModel.completed_voltage_transfer_function() [ALG-001 L5 owner]
│           ├─ LinkSegment.from_tf()                         [ALG-006 analysis-grid direct injector]
│           │  └─ resample_tf()                              [ALG-006 L5 owner]
│           └─ _realize_ctle_pulse() × pulse / victim pulse_no_txffe [ALG-007 L4 owner: per-path]
│              ├─ continuous_tf                           [uses analysis-grid H21; ALG-006 upstream-folded]
│              ├─ bilinear_fine_grid                     [full-grid IFFT → shared pre-IIR shift → IIR → pulse]
│              └─ bilinear_iir → _reference_fd_to_td_record() [ALG-006 finite-record direct injector]
│                 └─ resample_tf()                        [same ALG-006 L5 owner]
├─ L1 Stage 2 / Domain — Pre-DTE model
│  ├─ calculate_pre_dte_imp_common()
│  ├─ prepare_pre_dte_phase_inputs()
│  │  └─ _select_xtalk_path_phase()                          [full-response preparation]
│  ├─ calculate_pre_dte_imp_at_pos()                         [per-phase domain operation]
│  │  ├─ _calculate_tx_noise_eq_ch()                         [ALG-006/007 upstream-folded consumer]
│  │  └─ ADC-input FIR-PMF construction                     [NUM-006 direct consumer]
│  └─ _build_pre_dte_psd()                                   [NUM-003 / ALG-008 L3 owner]
│     ├─ resolve one record_cfg                               [NUM-003 dispatch]
│     ├─ realize S_rn/S_xn/S_tn/S_jn on that record
│     ├─ resolve clipping noise + CDF tail                    [ALG-008 dispatch]
│     │  ├─ full jitter + P_qc/2
│     │  └─ RJ-only jitter + P_qc
│     ├─ _build_psd_adc_qn(...)                               [fixed executor / non-owner]
│     │  └─ _calculate_V_qc(...)                              [PMF helper / non-owner]
│     │     └─ _build_pmf_interference_178A(...)
│     │        └─ Pmf1D.fir_filter()                          [NUM-006 L5 owner]
│     ├─ _resolve_adc_input_pmf_config()                      [NUM-004 L4 owner; execution point 1]
│     │  └─ COMPMFGridControl.resolve_dy()                    [L5 shared grid kernel]
│     └─ sum S_total and form R_n                             [one atomic owner boundary]
├─ L1 Stage 3 / Control — Sampling search
│  └─ _run_once() exposed Stage 3 control block              [SRCH-001 L1 owner]
│     ├─ resolve pos_sweep_method / pos_coarse_stride        [sole selector read]
│     ├─ _initial_pos_sweep_indices(...)                     [concrete-choice helper]
│     ├─ one shared initial/fine phase-batch loop
│     ├─ _fine_pos_sweep_indices(...)                        [concrete-choice helper]
│     ├─ strict minimum-MSE complete-bundle retention
│     ├─ COMRunStatus coarse/fine/MSE/error records
│     └─ _assign_selected_phase()                             [commit validator; non-owner]
├─ L1 Stage 4 / Domain — DTE solver
│  ├─ calculate_MMSE_DTE()                                   [ALG-010 selector injector; non-owner]
│  │  └─ inject cfg.alg.floating_mode
│  ├─ COM_MMSE_DTE.run() floating tap/group solve            [ALG-010 L3 concrete owner]
│  │  ├─ _select_floating_tap_by_isi()                        [heuristic executor; non-owner]
│  │  ├─ _select_floating_tap_onetime()                       [simplified executor; non-owner]
│  │  ├─ _calculate_float_ffe_178A()                          [spec-defined executor; non-owner]
│  │  └─ solve／limit／MSE／COMDTEStatus lifecycle
│  └─ COMDTEStatus.H_rxffe                                   [bound to pre-DTE record after solve; non-owner]
├─ L1 Stage 5 / Domain — Post-FFE model
│  ├─ _apply_rxffe_response()                                [fixed circular operation]
│  │  └─ COMPostFFEEqChannelStatus                           [DFE／MLSD consumer record]
│  ├─ _resolve_adc_input_pmf_config()                        [same NUM-004 L4 owner; execution point 2]
│  │  └─ COMPMFGridControl.resolve_dy()                      [same L5 shared grid kernel]
│  ├─ _build_adc_input_pmf_exact()                           [NUM-006 direct consumer]
│  │  └─ _build_pmf_interference_178A(...) × signal/XT/DDJ
│  │     └─ Pmf1D.fir_filter()                               [same NUM-006 L5 owner]
│  └─ transform pre-DTE PSDs on their existing record        [NUM-003 non-owner]
├─ L1 Stage 6 / Domain — DFE COM model / final PMF
│  ├─ _resolve_final_com_pmf_config()                        [NUM-005 L4 owner; execution point 1]
│  │  └─ COMPMFGridControl.resolve_dy()                      [L5 shared grid kernel]
│  ├─ calculate_COM_DFE() component／combined PMFs           [NUM-005 direct consumer]
│  └─ COM._build_final_adc_quantization()                    [ALG-012、ALG-013 L3 owner]
├─ L1 Stage 7 / Domain — MLSD model
│  ├─ _resolve_final_com_pmf_config()                        [same NUM-005 L4 owner; execution point 2]
│  │  └─ gaussian_addition → solve_g_an()／evaluate_delta_com_an()
│  │     [direct consumer; rebuild p_G_an on final-domain dy]
│  ├─ scaled_total_pdf → reuse DFE COM PMFs                  [NUM-005 indirect consumer]
│  ├─ COM._build_mlsd_added_noise()                          [ALG-014 L3 owner]
│  │  ├─ solve_g_an()                                       [Gaussian executor]
│  │  └─ _build_scaled_total_pdf_added_noise()               [reference executor]
│  ├─ build_mlsd_noise()                                     [NUM-003 + ALG-015 L3 owner]
│  │  ├─ resolve MLSD record_cfg and rebuild component PSDs
│  │  └─ Eq. 178A-54 composition → S_ni／R_ni
│  ├─ calculate_der_mlsd()                                  [ALG-016 + NUM-008 L3 owner]
│  └─ calculate_COM_MLSD() 固定記錄計算用及 SiCoPR-style diagnostic DER
└─ Cross-domain L5 PMF operations
   ├─ `_calculate_V_qc()`／`_build_psd_adc_qn()`／`_build_adc_input_pmf_exact()`／`_reconstruct_final_vqc_sicopr()`／`calculate_der_mlsd()` [ALG-002 injectors]
   │  └─ Pmf1D.multi_dirac()/scale_x()/resample_dx()/fir_filter() [ALG-002 owner set]
   │     └─ Pmf1D._project_to_grid()                         [private kernel; non-owner]
   ├─ Pmf1D.fir_filter(..., keep_mass)                       [NUM-006 L5 owner]
   │  └─ _truncate_keep_mass()                               [private executor; non-owner]
   ├─ Pmf1D.fir_filter()/combine()                           [NUM-007 L5 owner set]
   │  └─ _convolve_probability_mass()                        [private executor; non-owner]
   ├─ Pmf1D.fir_filter(..., tap_abs_th)                       [NUM-009 L5 owner]
   ├─ `_calculate_V_qc()`／`_build_psd_adc_qn()`／`_build_adc_input_pmf_exact()`／`_build_pmf_G()`／`_reconstruct_final_vqc_sicopr()`／`evaluate_delta_com_an()`／`solve_g_an()`／`calculate_der_mlsd()` [ALG-003 consumers]
   │  └─ Pmf1D.gaussian()/uniform() PDF→PMF                     [ALG-003 L5 owner set]
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

The final-quantization reference tap selection follows the SiCoPR indexing rule
within ALG-012's existing reference path, without introducing a separate branch.
ALG-013 的 PMF projection/support 與 ALG-012 clipping convention 各自保留；
`reference_support` 必須搭配 `sicopr_final_reconstruction` 與 `pmf_sample`。
兩項 review 的結案範圍各自獨立，不因 ALG-013 結案推論 ALG-012 全面對齊。

## 不是分支的項目

| 項目 | 分類與原因 |
|---|---|
| `src.channel.victim/next/fext` binding | **Source/input configuration**。`path`、`representation`、`port_order` 選擇並解讀 artifact；`COMSourceConfig.ChannelBinding.load()` 負責載入與驗證，unsupported representation 不得 fallback。它不選擇同一 semantic operation 的平行方法，因此不建立 `SRC-001` branch。 |
| `exe.target` | **Execution control**。`mse/dfe/mlsd/all_enabled` 只決定 pipeline 執行範圍；`COM._run_once()` 不因 target 改變任何已執行 stage 的公式或 method，因此不建立 execution branch，也不參加 ownership review。 |
| `channel.sparam_frequency_limit_Hz` | **輸入邊界**。描述實際送入 reader 的有效量測上限；execution profile 不得把任意 100 GHz 檔案暗中裁成 67 GHz。`ALG-006` 只決定此邊界外如何處理。 |
| `alg.xtalk_pmf_accumulation` | **固定行為**。目前唯一合法值是 `pathwise_convolution`，沒有 A/B 分支能力；保留是待清理的 API 欄位。 |
| TX FFE discrete filter 與 `LinkSegment.cascade_ir()` | **等價實作**。對 oversampled pulse 做 shift-sum／convolution，不屬 CTLE branch。 |
| sinc／boxcar unit-pulse 表示 | **等價表示**。對齊 transfer function 與時間原點後不建立平行算法。 |
| RX package `reverse_ports()` | **共同正確流程**。die-to-channel network 建立後交換 two-port port orientation，不提供錯誤舊法作分支。 |
| Eq. 178A-49 `(-1)^(j+1)` | **共同公式修正**。不是 Annex/reference 平行方法。 |
| final quantization FIR 是否「包含 main tap」 | Spec path 傳入完整 FFE taps；reference path 為重現 SiCoPR，先移除零係數再按位置跳過一個 tap，不等同完整 FIR 模型。`Pmf1D.fir_filter()` 本身不執行此選擇。 |
| `interference_pmf_method` | **已移除的非必要分支**。`signal_fir` 與 `pam_atoms` 的差異源自過早 grid projection；固定採 exact PAM atoms → tap scaling → grid projection → convolution。Runtime config、preset 與 workbook 不再提供此 selector。 |
| `SampledPSD.filtered_by()` grid matching | **固定 utility contract**。輸入 grid 不一致即由 caller 先處理；沒有隱藏 auto-regrid branch。 |
| `cascade_ir(force_grid=False)` | **診斷／caller-owned utility behavior**。可回傳完整 linear-convolution record，或由 caller 明示 `output_cfg`；它不是獨立 Project Config branch，也不是 Stage 5 circular RX FFE。 |

### `ALG-002` 二次審查證據

| Item | Record |
|---|---|
| Status | **Closed 2026-11-11**。Helper ownership convergence 已由 isolated commit `b417b8c` 整合並推送；權威 owner tree 已由 `c804e3c` 整合。 |
| Code convergence | `_calculate_V_qc()`、`_build_psd_adc_qn()`、`_build_adc_input_pmf_exact()`、`_reconstruct_final_vqc_sicopr()` 不再接收 `COMAlgorithmPolicyConfig`，只接收 concrete `pmf_projection_method`；`pdf_to_pmf_method` 維持獨立 concrete argument。 |
| Preserved boundary | PAM source 保持 exact natural-grid atoms；已移除的 selector 不恢復；`tap_abs_th`、retained mass、ALG-003 與 ALG-004 都是獨立決策。 |
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
| RX FFE record | `_apply_rxffe_response()` 在每條輸入 response cfg 做 circular FFE；DFE/MLSD consume recorded grids | `tests/test_com_model_178A_post_ffe.py`、`test_com_model_178A_mlsd_noise.py`、CTLE pulse tests |
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
