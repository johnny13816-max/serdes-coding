# 當前契約狀態

此文件只保留目前執行焦點、排隊項目與最近完成的責任邊界。完整歷史與
E/G/T 證據見 [`reference_alignment_contracts.md`](reference_alignment_contracts.md)，
v1.0 release 狀態見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

## Workflow state

使用者已以「可帶入公司後持續擴充」為短期目標恢復 CP-BR stage-by-stage
branch review；93A、reporting、C2M migration 與 release 項目仍維持暫停。
規則維護 RC-20261106-002 已結案。CFG-178A A--F 已完成並整合；CP-BR 目前依
使用者指定順序執行 ownership 二次審查：先重新確認曾完成一次審查的 branches，
再繼續尚未完成一次審查的項目。ALG-003 已完成二次審查並關閉；TC-025 將
Gaussian `pmf_sample` 收斂至固定 ±8σ support。ALG-002 也已完成 owner
convergence、驗證與 isolated integration。ALG-004 signed-scale contract、實作、
驗證與 remote integration 已完成並關閉；ALG-006 也已完成二次 ownership
審查，確認 `resample_tf()` 為 L5 owner。ALG-007 也已完成二次審查，確認
L3 CTLE pulse-realization functional block ownership。NUM-003 也已完成二次審查，
確認 shared L3 impairment-record realization block ownership；二次審查移至
SRCH-001。NUM-006
保持暫停。RC-004
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
| CP-BR — 178A branch ownership second review | **Active — SRCH-001** | NUM-003 已關閉；semantic owner 是跨 Stage 2／3／5／7 共用的 L3 impairment-record realization block，四個 L4 functions 分別負責 pre/post-FFE grid resolution、record realization 與 PSD facade | 重新確認 SRCH-001 sampling-phase schedule 的 owner、consumers 與 branch parameters |
| 178A P4–P8 — Remaining design-review chapters | Paused / superseded where CP-BR overlaps | 不重複 CP-BR ownership work；非 branch 章節仍維持暫停 | 完成 CP-BR 後重新盤點 |
| P9 / release preparation | Paused | release candidate、claim boundary、regression/CI、package/tag | 使用者選擇 Goal C |
| ARC-CROSS-001 — Current-schema 93A golden case | Paused | 選定 source case、schema strategy、baseline 與 validation level；不改 93A equations | 使用者選擇 Goal B |
| ARC-REPORT-001 — Cross-version report plot refinement | Paused | 收集具體 plot defect；renderer 與 version composition 分開處理 | 使用者選擇 Goal D |

## Recently closed boundaries

| Boundary | Evidence |
| --- | --- |
| ARC-178A-001 — standalone 178A COM roots | `cc5339e` |
| ARC-178A-002 — semantic dataclass text | `149bbd6` |
| ARC-178A-003 — shared reporting orchestration | `e5b0b2b` |
| ARC-178A-004 — remove 178A implementation dependency on 93A | `4e21aca`, `313cf6b`, `13d1018`, `40470e8` |
| UTIL-SNP-001 — explicit S2P/S4P representations | `d9a2c6e` |
| UTIL-EYE-001 — deterministic LinkSegment eye plotting | `e7e1612` |
| COMPAT-PY37-001 — Python 3.7 utility export | `f774487` |
| UTIL-SNP-002 — synthetic S4P target semantics | `94e5613` |
| 178A P3 — Workbook/config interface review | current SiCoPR scope complete；evidence in `docs/models/178A/design_review.md` |
| NUM-003（legacy B-005）— Eq-channel impairment length | **二次 ownership review Closed 2026-11-12**。L3 impairment-record realization block 是 semantic owner；L4 `_resolve_eq_ch_imp_record_cfg()`／`_resolve_post_ffe_imp_record_cfg()`／`_realize_eq_ch_imp_record()`／`_build_eq_ch_imp_psd()` 實作 `full` 或固定 `num_trunc_ui` record。Stage 4 `H_rxffe` 只綁定 concrete PSD grid，solver 不屬此 branch。本次 production code 未變；沿用既有 SiCoPR golden DFE COM `1.5247607834259893 dB`、final COM `2.895898684873246 dB` 與 `187 passed`, `1 deselected`, `2 subtests passed` evidence。 |
| ALG-002 — Discrete-amplitude PMF projection | **Closed 2026-11-11**。L5 public `Pmf1D.multi_dirac()`／`scale_x()`／`resample_dx()`／`fir_filter()` owner set；private `_project_to_grid()` 是 kernel/non-owner。四個 model helpers 只接收 concrete methods。Focused `47 passed`、Python 3.7 export validation passed、固定 SiCoPR golden `1 passed`，DFE/final COM 與 intermediate digests 不變。Implementation `b417b8c`、權威文件 `c804e3c`。 |
| ALG-003 — PDF→PMF discretization | **Closed 2026-11-11**。L5 `Pmf1D.gaussian()`／`uniform()` owner set；model helpers 只注入 concrete method。TC-025 將 `pmf_sample` Gaussian support 收斂至固定 ±8σ。Focused `47 passed`、Python 3.7 export validation passed、固定 SiCoPR golden `1 passed`，既有 tolerances 與三個 digests 全數通過。Implementation `e65f644`、權威文件 `c804e3c`。 |
| ALG-004 — Scalar-PMF scaling | **Closed 2026-11-11**。L5 `Pmf1D.scale_x()` sole owner；Stage 7 `_build_scaled_total_pdf_added_noise()`／`calculate_der_mlsd()` 是 direct injectors。`interpolate_ordinates` 支援 signed scale 並保持同一 `abs(scale)` output grid；FIR 固定 `mass_deposit`，不屬 ALG-004。Focused `49 passed, 2 subtests passed`、Python 3.7 export passed、固定 golden `1 passed`。Implementation／docs `114e7bf`。 |
| NUM-004／NUM-005（legacy E-003／B-013）— ADC-input／final PMF grid numerical controls | 兩個 RG groups、owners 與 impact boundaries 已分離；workbook 與 provenance 已 canonicalized。focused tests `37 passed`；workbook formula-error scan 0；SiCoPR golden `COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。 |
| ALG-001（legacy B-019）— Missing-DC completion | 四種 methods 收斂至單一 owner；`continuous_tf`／`bilinear_iir` 共用 completed H21，reference profile 選 `mag_phase_trend_to_dc`。Focused `59 passed`、Python 3.7 export passed、SiCoPR golden `1 passed`；`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 與 intermediate digests 不變。Commit `7c256b2` 已推送。 |
| ALG-011（legacy B-004）— RX FFE record realization | Stage 5 sole owner；`linear_fixed_grid`／`linear_expanded_grid`／`finite_record_circshift`；victim、all XT、DDJ、ISI 共用 response grid，NUM-003 獨立決定 PSD record，MLSD 只消費 resolved status。Python 3.7 validator passed；SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。Commit `565ccba` 已推送。 |
| NUM-002（legacy B-014）— Gaussian support | Retired as non-branch。178A 固定 internal 8σ；focused `48 passed`、workbook scans 0、SiCoPR golden `1 passed`；COM_DFE 與 final COM 不變。Evidence 見 `num002_gaussian_support.md`。 |
| legacy E-001 — Pipeline target（reclassified non-branch） | `full` 已改名為 `all_enabled` 且不保留 alias；`COM._run_once()` 只依 `cfg.exe.target` 決定執行範圍，不改變已執行 stage 的方法，因此不再使用 `EXE-001` branch identity。Focused `43 passed`；七份 workbook legal-value／stale-value／formula-error scans 通過；SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。Implementation `68ea755`、workbook/docs `3f2bc73` 已推送。 |
| ALG-005（legacy B-001）— Channel renormalization | Retired as non-branch。D3.2 measured S4P 固定 single-ended renormalization → mixed-mode；native S2P 僅依 port count dispatch，錯誤不 fallback。Focused `52 passed`、Python 3.7 validator passed、9 份 workbook selector scan 0、matrix formula errors 0；SiCoPR golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。 |
| ALG-006（legacy B-002）— Out-of-measured transfer | 保留 `cosine_decay`／`zero_padding` branch；`resample_tf()` 是共同數值 owner。Analysis-grid `H_21` 與 bilinear finite record 是兩個 direct execution paths；victim TX noise 只抽樣已建立的 `pulse_no_txffe`，不是第三個 execution point。Focused `41 passed`；SiCoPR fixed 67 GHz＋zero-padding golden `1 passed`，MSE `0.0061912610245255335`、`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 與 stage digests 不變。Full suite 的七項既有／環境 failure 已依 contract 記錄 deviation。Implementation `db0e836` 已推送至 `origin/main`。 |
| ALG-007（legacy B-003）— CTLE pulse realization | **Closed 2026-11-11**。L3 CTLE pulse-realization functional block 是 semantic owner；L4 `_prepare_ctle_pulse_realization()`／`_realize_ctle_pulse()` 分別執行 shared setup 與 per-path realization。Victim `COMPath` 同時保存 `pulse` 與 `pulse_no_txffe`，NEXT／FEXT 的後者為 `None`；Stage 3 只抽樣 no-TX-FFE pulse。Focused `38 passed`；SiCoPR production golden 的 MSE、COM_DFE、final COM 與三個 digests 不變。Implementation `e676a45`、二次 ownership 文件 `b79a964`。 |
| ALG-008（legacy B-006）— Pre-DTE ADC clipping convention | Stage 3 `calculate_pre_dte_imp_at_pos()` 是 sole execution owner；D3.2 確認 `full_jitter_half_tail`，MATLAB 4.17 對照為 `rj_only_full_tail_reference`。直接影響 `V_qc/delta/S_qn/R_n`；後續 COM 僅可能經 phase／taps 間接受影響，final ADC PMF 不讀此 selector。Focused `29 passed`；SiCoPR production golden `1 passed`，`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB` 不變。 |
| RC-20261106-001 — Remove stale branch-review checklist | `9161e63823daaa1009deeccebd927ea72dc46ab0`；registry 與 stage progress 為現行分類／待辦來源。 |
| RC-20261106-002 — Repository workbook batch maintenance | `194ce220479c2c2825bf553b333a2e7c0d6f90c2`；inventory→batch authoring→single final verification，按 layout 與視覺影響 render。 |

## Status rules

- `Open` 只表示已記錄，不表示可開始修改。
- `Approved`／`Implemented` 同一時間最多一項。
- 新提案不會自動中斷 active contract；切換前必須完成或明確記錄 pause/cancel。
- `Closed` 必須具備 scoped implementation、validation、required documentation、
  tracker reconciliation 與 isolated commit；需要 GitHub synchronization 時也必須完成 push。
