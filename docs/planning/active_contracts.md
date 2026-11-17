# 當前契約狀態

此文件只保留目前執行焦點、排隊項目與最近完成的責任邊界。完整歷史與
E/G/T 證據見 [`reference_alignment_contracts.md`](reference_alignment_contracts.md)，
v1.0 release 狀態見
[`../operations/v1_0_release_gate.md`](../operations/v1_0_release_gate.md)。

## Temporary rule contract — RC-20261117-003

**Boundary:** 建立逐檔 document lifecycle registry、固定 lifecycle/owner/update/closure 規則與機械性 checker；只整理規則 metadata，不收斂 branch-review 技術內容。
**Status:** Closed；registry/checker validation 與 local/remote integration 已完成，implementation commit `b147050` 已同步至 `origin/main`。
**Next gate:** 於獨立 project-maintenance 對話啟動 Boundary B，依已核准 disposition 執行刪除與 branch-review 文件收斂。
**Evidence:** [`rule_changes.md`](rule_changes.md#rc-20261117-003--document-lifecycle-registry-and-enforcement)、[`../document_registry.md`](../document_registry.md)、[`document_disposition_manifest.md`](document_disposition_manifest.md)。
**Authorization:** 使用者已確認改善計畫；本對話為規則維護 boundary。

## Temporary rule contract — RC-20261115-001

**Boundary:** 修改 branch ID lifecycle、registry ordering、retired records 與舊 ID cleanup 規則；不接管或修改 CP-BR project task。
**Next gate:** HANDOFF 的過寬 cleanup 摘要待 project dirty state 可安全同步時更新，之後關閉本 RC。push 暫緩，因 `origin/main` 落後的 16 個既有 project commits 超出本規則變更範圍。
**Authorization:** 使用者已核准 change contract；本規則專用對話有明確規則維護授權。

## Temporary rule contract — RC-20261116-001

**Boundary:** 在子項完成或切換下一項前，核對驗收證據、權威技術文件與狀態來源、commit/push 邊界及 pending 條件。
**Status:** Closed；Workflow rule implemented in commit `2a8f6dc`，本次 active-state reconciliation 與 closure 記錄已完成。
**Evidence:** 規則詳細決策與驗證見 [`rule_changes.md`](rule_changes.md)。HANDOFF 未變更，因本項未切換或改變 active project task。
**Authorization:** 使用者要求處理此規則的 active-state reconciliation；本規則維護對話具明確規則維護授權。

## Temporary rule contract — RC-20261117-001

**Boundary:** 定義單一文件 owner、項目結案時的有界跨文件一致性核對、歷史／過期內容處置與跨 session 恢復依據。
**狀態:** Closed；規則實作 commit `1b5df29`。
**Evidence:** 規則與驗證見 [`rule_changes.md`](rule_changes.md)。HANDOFF 未變更，因本項未切換或改變 CP-BR project task。
**Authorization:** 使用者要求以規則約束文件收斂、整理與知識傳遞；本規則維護對話具明確規則維護授權。

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
實作修正，確認 Pre-DTE／MLSD model 各有一個 PSD-sum owner。SRCH-001 已完成
ownership correction：`COM._run_once()` 中完整且刻意展開的 L1 Stage 3 control
block 是 owner；Stage 1–7 保留為 runtime/navigation labels，其他 stage 不因 caller
relationship 轉移 ownership；Pre-DTE 與 DTE
operations 在 root runtime flow 中保持可見。ALG-008 也已完成二次審查，確認
Pre-DTE model L3 `_build_pre_dte_psd()`
是 sole owner。NUM-004／005 已確認各自的 L4 domain resolver 是 sole owner；
L5 `COMPMFGridControl.resolve_dy()` 僅為 shared kernel。NUM-005 的 Stage 6
consumer 是直接完整使用；Stage 7 依 added-noise flow 直接使用 final grid 或
間接沿用 Stage 6 PMFs。ALG-010 已完成完整初次審查並關閉：保留三種 floating
strategies，L3 `COM_MMSE_DTE`／`COM_MMSE_DTE.run()` 是 semantic／concrete owner，
production 不需修改。NUM-006 也已完成完整初次審查：L5
`Pmf1D.fir_filter()` 是 owner，Stage 2／5 是 direct consumers，Stage 6 固定
`keep_mass=1.0` 而不是 consumer。ALG-011 已收斂為固定 circular FFE；ALG-012 已結案。
2026-11-17 completion audit 未發現新的未審 selectable behavior。RC-004
仍為 Proposed，僅由規則專用對話評估。

歷史評估與 178A P3 workbook/config interface review 已完成；P3 的完成範圍限於目前同步的
SiCoPR case。已完成／未完成事實、分離後的目標與恢復條件見
[v1_0_rebaseline.md](v1_0_rebaseline.md)。未經使用者選定新目標，不得自動恢復 P4、93A、
reporting、C2M migration 或 release 工作。

## Current queue

**2026-11-17 NUM-009：** 審查結案，實作 `15823b6` 已整合至 `origin/main`。核准的 response tap threshold 已實作；`None` 沿用 dy，`0` 保留所有非零 response taps，非負數為 V 門檻；our ADC FFE 保留所有非零 taps，reference 保留既有規則。Focused 89 passed、2 subtests passed；最終版本 fixed reference golden 1 passed；固定案例 ADC FFE 隔離對照 MSE、DFE COM、final COM 不變。外部 Hansel workbook 缺失的 3 項介面測試未能執行。

**2026-11-16 ALG-012：** 初次審查完成；保留兩個 clipping 選項，L3 `COM._build_final_adc_quantization()` 為 owner。Akinwale 固定 response／noise 輸入的 SiCoPR 4.17 對照中，完整 clipping reconstruction 的 `V_qc` 差 `6.94e-18 V`；ISI／XT／DDJ component 對照及 Gaussian 差異記於 Stage 6 文件。不宣稱一般案例皆對齊；`S_in` 零係數議題依使用者決定延後。此次僅更新文件，不重跑 golden。

**2026-11-16 ALG-016／NUM-008：** L3 `calculate_der_mlsd()` 分別處理 penalty／既有 CDF 與 DER 停止。Project `fixed_length`；reference `relative_tail`，門檻 `1e-4`。Focused 54 passed、profile/provenance 40 passed、FFT golden 1 passed；SiCoPR recurrence 共同輸入的提前停止及 penalty 邊界對照通過。Reference linear 固定 case：j=16、phase 5、MSE 0.006191300963670364、DFE COM 1.5247607834260184 dB、final COM 2.895898684873275 dB，符合 golden 容差；不宣稱所有 case 相同。

**2026-11-16 ALG-015：** owner `build_mlsd_noise()`；our branch 不變，reference 以 unit-main 尺度重算 clipping，再將 `S_qn` 轉回專案尺度。Focused 51 passed、原 FFT golden 1 passed。固定案例 reference linear profile：phase 5、MSE 0.006191300963670364、DFE COM 1.5247607834260184 dB、final COM 2.895898684873275 dB。專案 `S_qn_rms=22.7386657816 mV` 除以 main gain 58.9224659，等於 SiCoPR 4p17p0 實跑的 0.3859082514 mV；對照限於此固定案例。

**2026-11-16 ALG-014：** Our branch 維持 Gaussian 校準；reference 使用二階矩
差計算 `g_an`，兩者統一由 `COM._build_mlsd_added_noise()` 選擇。Focused 56 passed；
非零平均 PMF 的 SiCoPR 共同輸入與固定 reference case 已驗證；implementation
commit `2f0d252` 已推送。

**現行更新（2026-11-16）：** ALG-013 完成選項、Stage 6 owner、profile、
fixed-input SiCoPR PMF 和固定案例 COM 審查；新增 focused boundary tests
3 passed。NUM-007 提供 reference direct convolution（`564aac4`）。
不宣稱一般案例全面對齊；ALG-012 的獨立 reference 證據不因本項結案而關閉。

| ID／名稱 | 狀態 | 邊界 | 下一個關卡 |
| --- | --- | --- | --- |
| GOV-V1-002 — 178A review 與 v1.0 狀態收斂 | **Closed with corrected claim** | governance 文件已提交；全面 PASS claim 已撤回，P1/P2 evidence 保留 | 以 roadmap 逐章完成剩餘 review |
| CFG-178A — COMConfig domain/runtime migration | **Closed 2026-11-10** | `cfg.src/alg/num/srch/exe` 是唯一 runtime tree；temporary aliases 與 draft `group` vocabulary 已移除；profile provenance 位於 export-only adapter resolution；八個 populated cases、search smoke、focused integration、Python 3.7 validator 與 fixed golden 通過；已整合為單一 local commit | 無；後續 config 變更另立 boundary |
| CP-BR — 178A complete branch review | **Closed 2026-11-17** | Completion audit 未發現新的未審 selectable behavior；ALG-011 固定為 circular FFE，ALG-012 維持 bounded closure；tracker、roadmap、active state 與 HANDOFF 已收斂 | Boundary commit `ed316a8` 已推送並確認存在於 `origin/main`；後續工作由使用者另選目標 |
| 178A P4–P8 — Remaining design-review chapters | Paused / superseded where CP-BR overlaps | 不重複 CP-BR ownership work；非 branch 章節仍維持暫停 | 完成 CP-BR 後重新盤點 |
| P9 / release preparation | Paused | release candidate、claim boundary、regression/CI、package/tag | 使用者選擇 Goal C |
| ARC-CROSS-001 — Current-schema 93A golden case | Paused | 選定 source case、schema strategy、baseline 與 validation level；不改 93A equations | 使用者選擇 Goal B |
| ARC-REPORT-001 — Cross-version report plot refinement | Paused | 收集具體 plot defect；renderer 與 version composition 分開處理 | 使用者選擇 Goal D |

## Recently closed boundaries

| Boundary | Evidence |
| --- | --- |
| NUM-006 — ADC-input FIR-PMF retained mass | **完整初次審查 Closed 2026-11-13**。保留 project `1-1e-5`／reference `1.0`；L5 public `Pmf1D.fir_filter()` 是 owner，在每個 tap convolution 後對稱截尾並重新正規化，`1.0` 關閉截斷。Stage 2／5 是 direct consumers；`_resolve_adc_input_pmf_config()` 只注入數值，private `_truncate_keep_mass()` 只執行；Stage 6 final PMF 固定 `1.0`，不是 consumer。公開 owner 新增 `(0,1]` finite validation；合法設定的 numerical path 未變。Focused `53 passed`，未重跑 golden。 |
| ALG-010 — Floating FFE strategy | **完整初次審查 Closed 2026-11-12**。保留 `heuristic`／`simplified`／`spec-defined`；L3 `COM_MMSE_DTE` 是 semantic owner，`COM_MMSE_DTE.run()` 是 concrete callable owner。`COM.calculate_MMSE_DTE()` 只注入 `cfg.alg.floating_mode`；三個 strategy helpers 是 executors。Focused `7 passed` 覆蓋唯一 operational selector read、每個 selector 的唯一 dispatch 與三種 mode 的 `N_wg=0` bypass，並檢查 coherent `COMDTEStatus`；與既有 policy tests 合跑 `42 passed`。Production path 不變，未重跑 golden，也不宣稱 equation/spec equivalence。 |
| SRCH-001 — Sampling-phase schedule | **Ownership corrected 2026-11-13**。`COM._run_once()` 中完整且刻意展開的 L1 Stage 3 control block 是 owner：唯一讀取 method/stride、操作 initial/fine phase sweeping、處理 cursor rejection、保留 strict-minimum complete bundle、決定 locking point 並 commit。Stage 2 Pre-DTE 與 Stage 4 DTE 直接顯示於 loop 內但保有獨立 ownership。`COMRunStatus` 只保存 `mse_by_pos.png` 所需的四個 diagnostic trace 欄位；PMF controls 由 reporter 直接讀取 `cfg.num`。Current focused Stage 3/status/reporting/policy `63 passed`；既有 fixed SiCoPR golden `1 passed`；production numerical formulas 未修改。 |
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
