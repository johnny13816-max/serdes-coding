# 當前契約狀態

此文件只保留目前執行焦點、排隊項目與最近完成的責任邊界。完整歷史與
E/G/T 證據見 [`reference_alignment_contracts.md`](reference_alignment_contracts.md)，
v1.0 release 狀態見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

## Workflow state

使用者已以「可帶入公司後持續擴充」為短期目標恢復 CP-BR stage-by-stage
branch review；93A、reporting、C2M migration 與 release 項目仍維持暫停。
規則維護 RC-20261106-002 已結案。CFG-178A A--F 已完成並整合；CP-BR 目前依
已關閉項目保留既有 closure evidence。由 ALG-010 起，使用者不再採信一次／二次
審查標籤；所有剩餘項目一律依 algorithm-review 完整初次流程，重新確認 eligibility、
選項、scope、owner、consumers 與 validation。ALG-003 已完成二次審查並關閉；TC-025 將
Gaussian `pmf_sample` 收斂至固定 ±8σ support。ALG-002 也已完成 owner
convergence、驗證與 isolated integration。ALG-004 signed-scale contract、實作、
驗證與 remote integration 已完成並關閉；ALG-006 也已完成二次 ownership
審查，確認 `resample_tf()` 為 L5 owner。ALG-007 也已完成二次審查，確認
L3 CTLE pulse-realization functional block ownership。NUM-003 也已完成二次審查與
實作修正，確認 Stage 2／Stage 7 各有一個 PSD-sum owner。SRCH-001 已完成
ownership 收斂，Stage 3 L2 `COM.calculate_sampling_phase()` 是唯一 selector
owner。ALG-008 也已完成二次審查，確認 Stage 2 L3 `_build_pre_dte_psd()`
是 sole owner。NUM-004／005 已確認各自的 L4 domain resolver 是 sole owner；
L5 `COMPMFGridControl.resolve_dy()` 僅為 shared kernel。NUM-005 的 Stage 6
consumer 是直接完整使用；Stage 7 依 added-noise flow 直接使用 final grid 或
間接沿用 Stage 6 PMFs。完整初次審查由 ALG-010 開始；NUM-006 與 ALG-011–017
同樣不得沿用舊有 approved／owner 結論。RC-004
仍為 Proposed，僅由規則專用對話評估。

歷史評估與 178A P3 workbook/config interface review 已完成；P3 的完成範圍限於目前同步的
SiCoPR case。已完成／未完成事實、分離後的目標與恢復條件見
[v1_0_rebaseline.md](v1_0_rebaseline.md)。未經使用者選定新目標，不得自動恢復 P4、93A、
reporting、C2M migration 或 release 工作。

## Current queue

| ID／名稱 | 狀態 | 邊界 | 下一個關卡 |
| --- | --- | --- | --- |
| GOV-V1-002 — 178A review 與 v1.0 狀態收斂 | **Closed with corrected claim** | governance 文件已提交；全面 PASS claim 已撤回，P1/P2 evidence 保留 | 以 roadmap 逐章完成剩餘 review |
| CFG-178A — COMConfig domain/runtime migration | **Closed 2026-11-10** | `cfg.src/alg/num/srch/exe` 是唯一 runtime tree；temporary aliases 與 draft `group` vocabulary 已移除；profile provenance 位於 export-only adapter resolution；八個 populated cases、search smoke、focused integration、Python 3.7 validator 與 fixed golden 通過；已整合為單一 local commit | 回到 CP-BR，從 production consumers 重新定義 NUM-006 boundary |
| CP-BR — 178A complete branch review | **Active — ALG-010 initial review** | 已關閉項目不重開；ALG-010、NUM-006、ALG-011–017 全部從 eligibility 開始，不採信歷史 approved／owner 標籤 | 完整審查 ALG-010 floating tap/group selector、選項、owner、consumers、tie behavior 與 validation |
| 178A P4–P8 — Remaining design-review chapters | Paused / superseded where CP-BR overlaps | 不重複 CP-BR ownership work；非 branch 章節仍維持暫停 | 完成 CP-BR 後重新盤點 |
| P9 / release preparation | Paused | release candidate、claim boundary、regression/CI、package/tag | 使用者選擇 Goal C |
| ARC-CROSS-001 — Current-schema 93A golden case | Paused | 選定 source case、schema strategy、baseline 與 validation level；不改 93A equations | 使用者選擇 Goal B |
| ARC-REPORT-001 — Cross-version report plot refinement | Paused | 收集具體 plot defect；renderer 與 version composition 分開處理 | 使用者選擇 Goal D |

## Recently closed boundaries

| Boundary | Evidence |
| --- | --- |
| SRCH-001 — Sampling-phase schedule | **二次 ownership review Closed 2026-11-12**。Stage 3 L2 `COM.calculate_sampling_phase()` 是 sole selector owner；解析 `each_phase`／`coarse_fine` 與 stride、維護 visit order／`COMRunStatus`、保留 strict-minimum-MSE complete bundle。`_run_once()` 只 orchestration/commit；index helpers 只接收 concrete choice；`calculate_pos_candidate()`／Stage 4 solver 是 non-owner。Focused `53 passed`；SiCoPR golden `1 passed`，selected phase 5、MSE `0.0061912610245255335`、COM_DFE `1.5247607834259893 dB`、final COM `2.895898684873246 dB` 與三個 digests 不變。 |
| ARC-178A-001 — standalone 178A COM roots | `cc5339e` |
| ARC-178A-002 — semantic dataclass text | `149bbd6` |
| ARC-178A-003 — shared reporting orchestration | `e5b0b2b` |
| ARC-178A-004 — remove 178A implementation dependency on 93A | `4e21aca`, `313cf6b`, `13d1018`, `40470e8` |
| UTIL-SNP-001 — explicit S2P/S4P representations | `d9a2c6e` |
| UTIL-EYE-001 — deterministic LinkSegment eye plotting | `e7e1612` |
| COMPAT-PY37-001 — Python 3.7 utility export | `f774487` |
| UTIL-SNP-002 — synthetic S4P target semantics | `94e5613` |
| 178A P3 — Workbook/config interface review | current SiCoPR scope complete；evidence in `docs/models/178A/design_review.md` |
| NUM-003（legacy B-005）— Eq-channel impairment length | **二次 ownership review Closed 2026-11-12**。Stage 2 `COM._build_pre_dte_psd()` 與 Stage 7 `COM.build_mlsd_noise()` 各自在 PSD 真正加總前解析 `full`／固定 `num_trunc_ui` record；完整 `eq_ch` 不受影響。Stage 3 只選 phase，Stage 5 只在既有 pre-DTE record 上轉換 reporting PSD。Static ownership test、focused `54 passed`、non-GUI `212 passed, 17 skipped, 2 subtests passed` 與 SiCoPR golden `1 passed`；golden 未修改。完整 collection 的 7 failures 限於缺少外部 Hansel workbook、sandbox system temp 與 repo-internal basetemp provenance，未進入 NUM-003 path。 |
| ALG-002 — Discrete-amplitude PMF projection | **Closed 2026-11-11**。L5 public `Pmf1D.multi_dirac()`／`scale_x()`／`resample_dx()`／`fir_filter()` owner set；private `_project_to_grid()` 是 kernel/non-owner。四個 model helpers 只接收 concrete methods。Focused `47 passed`、Python 3.7 export validation passed、固定 SiCoPR golden `1 passed`，DFE/final COM 與 intermediate digests 不變。Implementation `b417b8c`、權威文件 `c804e3c`。 |
| ALG-003 — PDF→PMF discretization | **Closed 2026-11-11**。L5 `Pmf1D.gaussian()`／`uniform()` owner set；model helpers 只注入 concrete method。TC-025 將 `pmf_sample` Gaussian support 收斂至固定 ±8σ。Focused `47 passed`、Python 3.7 export validation passed、固定 SiCoPR golden `1 passed`，既有 tolerances 與三個 digests 全數通過。Implementation `e65f644`、權威文件 `c804e3c`。 |
| ALG-004 — Scalar-PMF scaling | **Closed 2026-11-11**。L5 `Pmf1D.scale_x()` sole owner；Stage 7 `_build_scaled_total_pdf_added_noise()`／`calculate_der_mlsd()` 是 direct injectors。`interpolate_ordinates` 支援 signed scale 並保持同一 `abs(scale)` output grid；FIR 固定 `mass_deposit`，不屬 ALG-004。Focused `49 passed, 2 subtests passed`、Python 3.7 export passed、固定 golden `1 passed`。Implementation／docs `114e7bf`。 |
| NUM-004（legacy E-003）— ADC-input PMF grid | **二次 ownership review Closed 2026-11-12**。L4 `_resolve_adc_input_pmf_config()` 是 sole domain owner，明確選取 `cfg.num.adc_input_pmf_grid`；Stage 2 `_build_pre_dte_psd()` 與 Stage 5 `calculate_post_ffe_imp()` 是兩個 consumers。L5 `COMPMFGridControl.resolve_dy()` 是與 NUM-005 共用且不擁有 domain identity 的 numerical kernel。Static audit 確認唯一 family read 與兩個 call sites；current focused `9 passed`。Production path 未變，因此未重跑 golden。 |
| NUM-005（legacy B-013）— Final-domain PMF grid | **二次 ownership review Closed 2026-11-12**。L4 `_resolve_final_com_pmf_config()` 是 sole domain owner；Stage 6 `calculate_COM_DFE()` 直接以 resolved dy 建立所有 component／combined PMFs。Stage 7 `gaussian_addition` 直接以同一 dy 重建 `p_G_an`，`scaled_total_pdf` 則間接沿用 Stage 6 PMFs。L5 `COMPMFGridControl.resolve_dy()` 是 non-domain-owning shared kernel。Static audit 確認唯一 family read 與兩個 call sites；current focused `9 passed`。Production path 未變，因此未重跑 golden。 |
| ALG-001（legacy B-019）— Missing-DC completion | 四種 methods 收斂至單一 owner；`continuous_tf`／`bilinear_iir` 共用 completed H21，reference profile 選 `mag_phase_trend_to_dc`。Focused `59 passed`、Python 3.7 export passed、SiCoPR golden `1 passed`；`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 與 intermediate digests 不變。Commit `7c256b2` 已推送。 |
| ALG-011（legacy B-004）— RX FFE record realization | Stage 5 sole owner；`linear_fixed_grid`／`linear_expanded_grid`／`finite_record_circshift`；victim、all XT、DDJ、ISI 共用 response grid。NUM-003 不改變 ALG-011 response；Stage 7 只消費已解析 response 並獨立建立 MLSD PSD record。Python 3.7 validator passed；SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。Commit `565ccba` 已推送。 |
| NUM-002（legacy B-014）— Gaussian support | Retired as non-branch。178A 固定 internal 8σ；focused `48 passed`、workbook scans 0、SiCoPR golden `1 passed`；COM_DFE 與 final COM 不變。Evidence 見 `num002_gaussian_support.md`。 |
| legacy E-001 — Pipeline target（reclassified non-branch） | `full` 已改名為 `all_enabled` 且不保留 alias；`COM._run_once()` 只依 `cfg.exe.target` 決定執行範圍，不改變已執行 stage 的方法，因此不再使用 `EXE-001` branch identity。Focused `43 passed`；七份 workbook legal-value／stale-value／formula-error scans 通過；SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。Implementation `68ea755`、workbook/docs `3f2bc73` 已推送。 |
| ALG-005（legacy B-001）— Channel renormalization | Retired as non-branch。D3.2 measured S4P 固定 single-ended renormalization → mixed-mode；native S2P 僅依 port count dispatch，錯誤不 fallback。Focused `52 passed`、Python 3.7 validator passed、9 份 workbook selector scan 0、matrix formula errors 0；SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。 |
| ALG-006（legacy B-002）— Out-of-measured transfer | 保留 `cosine_decay`／`zero_padding` branch；`resample_tf()` 是共同數值 owner。Analysis-grid `H_21` 與 bilinear finite record 是兩個 direct execution paths；victim TX noise 只抽樣已建立的 `pulse_no_txffe`，不是第三個 execution point。Focused `41 passed`；SiCoPR fixed 67 GHz＋zero-padding golden `1 passed`，MSE `0.0061912610245255335`、`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 與 stage digests 不變。Full suite 的七項既有／環境 failure 已依 contract 記錄 deviation。Implementation `db0e836` 已推送至 `origin/main`。 |
| ALG-007（legacy B-003）— CTLE pulse realization | **Closed 2026-11-11**。L3 CTLE pulse-realization functional block 是 semantic owner；L4 `_prepare_ctle_pulse_realization()`／`_realize_ctle_pulse()` 分別執行 shared setup 與 per-path realization。Victim `COMPath` 同時保存 `pulse` 與 `pulse_no_txffe`，NEXT／FEXT 的後者為 `None`；Stage 3 只抽樣 no-TX-FFE pulse。Focused `38 passed`；SiCoPR production golden 的 MSE、COM_DFE、final COM 與三個 digests 不變。Implementation `e676a45`、二次 ownership 文件 `b79a964`。 |
| ALG-008（legacy B-006）— Pre-DTE ADC clipping convention | **二次 ownership review Closed 2026-11-12**。Stage 2 L3 `_build_pre_dte_psd()` 是 sole owner；它選擇 clipping noise composition／CDF tail，固定 `_build_psd_adc_qn()`／`_calculate_V_qc()` 只消費 concrete inputs。D3.2 確認 `full_jitter_half_tail`，MATLAB 4.17 對照為 `rj_only_full_tail_reference`。直接影響 `V_qc/delta/S_qn/R_n`；後續 COM 僅可能經 phase／taps 間接受影響，final ADC PMF 不讀此 selector。AST ownership evidence 只找到一個 owner；current focused `2 passed`。Production path 未變，因此未重跑 golden；既有 SiCoPR golden `1 passed` evidence 保留。 |
| RC-20261106-001 — Remove stale branch-review checklist | `9161e63823daaa1009deeccebd927ea72dc46ab0`；registry 與 stage progress 為現行分類／待辦來源。 |
| RC-20261106-002 — Repository workbook batch maintenance | `194ce220479c2c2825bf553b333a2e7c0d6f90c2`；inventory→batch authoring→single final verification，按 layout 與視覺影響 render。 |

## Status rules

- `Open` 只表示已記錄，不表示可開始修改。
- `Approved`／`Implemented` 同一時間最多一項。
- 新提案不會自動中斷 active contract；切換前必須完成或明確記錄 pause/cancel。
- `Closed` 必須具備 scoped implementation、validation、required documentation、
  tracker reconciliation 與 isolated commit；需要 GitHub synchronization 時也必須完成 push。
