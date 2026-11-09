# CP-BR — 178A algorithm-branch coverage matrix

> 狀態：**2026-11-07 ALG-005 已退休為 fixed/input-dispatch behavior；未完成項仍待逐項 review**。權威技術文件仍為
> [`../models/178A/branch_behavior_registry.md`](../models/178A/branch_behavior_registry.md).
> 本工作矩陣依 model stage 歸納現有算法／數值選擇，供 CP-BR 審查；尚不宣稱
> coverage 完整。

`rg_name` 是實際 typed project-runtime configuration path。run control 的
`execution.<profile>` 代表 `single_run`、`search_sweep` 或 `search_final`，
由 project 的 `run_config` sheet 解析。`—` 表示 internal utility argument，
不是可由 project config 選擇的欄位。

| Stage order | ID / control class | rg_name (project config) | Description |
|---|---|---|---|
| Stage 0 / S-parameter ingestion | `ALG-001` algorithm policy | `channel.missing_dc_policy` | Missing-DC completion method；實際量測頻率邊界仍是 physical input fact，不由 execution profile 控制。 |
| Stage 0 / shared PMF utility | `ALG-002` algorithm policy | `policy.pmf_projection_method` | Target-grid projection：`linear` 或 `nearest`。 |
| Stage 0 / shared PMF utility | `ALG-003` algorithm policy | `policy.pdf_to_pmf_method` | PDF→PMF：`bin_integral` 或 `pmf_sample`。 |
| Stage 0 / shared PMF utility | `ALG-004` algorithm policy | `policy.pmf_scaling_method` | Scalar PMF scaling：`mass_deposit` 或 `interpolate_ordinates`。 |
| Stage 0 / pipeline gate | `EXE-001` execution | `execution.<profile>.target` | 選擇執行至 MSE、DFE、MLSD，或以 `all_enabled` 執行所有已啟用 stage；不改已執行 stage 公式。 |
| Stage 1 / path construction | `ALG-006` algorithm policy | `policy.out_of_measured` | 有效量測頻帶外 cosine decay 或 zero padding。 |
| Stage 1 / path construction | `ALG-007` algorithm policy | `policy.ctle_pulse_realization` | Continuous TF 或 bilinear-IIR finite-record pulse realization。 |
| Stage 2 / shared L3 (Stages 2, 3, 5, 7) | `NUM-003` numerical control | `policy.eq_ch_imp_len`, `policy.num_trunc_ui` | PSD 前使用 full 或 truncated equivalent-channel record。 |
| Stage 3 / phase scheduling | `SRCH-001` search | `execution.<profile>.pos_sweep_method`, `pos_coarse_stride` | Exhaustive 或 coarse/fine phase evaluation。 |
| Stage 3 / per-phase ADC | `ALG-008` algorithm policy | `policy.pre_dte_adc_clipping_convention` | Annex D3 或 reference-only RJ/tail clipping。 |
| Stage 3 / per-phase ADC | former `ALG-009` — retired non-branch | none；legacy `pmf_exact` row is read-compatible | `_build_psd_adc_qn()` fixed exact PMF flow；Gaussian approximation removed after cost/accuracy review。 |
| Stage 3 / ADC-input PMF grid | `NUM-004` numerical control | `numerical_control.adc_input_pmf_grid.*` | `_resolve_adc_input_pmf_config()` function set；只影響 ADC-input domain。 |
| Stage 3 / ADC-input PMF | `NUM-006` numerical control | `execution.<profile>.pmf_keep_mass` | Retained-mass convergence；不擁有 grid spacing。 |
| Stage 4 / MMSE DTE | `ALG-010` algorithm policy | `execution.<profile>.floating_mode` | Heuristic、simplified 或 spec-defined floating-tap solve。 |
| Stage 5 / post-FFE；Stages 6–7 consume | `ALG-011` algorithm policy | `policy.rxffe_record_realization` | `linear_fixed_grid`、`linear_expanded_grid` 或 `finite_record_circshift`；Stage 5 resolves one common victim/XT/DDJ record and downstream stages consume it。 |
| Stage 6 / final PMF grid | `NUM-005` numerical control | `numerical_control.final_pmf_grid.*` | `_resolve_final_com_pmf_config()` function set；只影響 final DFE／MLSD domain。 |
| Stage 6 / DFE COM | `ALG-012` algorithm policy | `policy.final_com_vqc_convention` | 沿用 selected-phase `V_qc/delta` 或重建 final clipping PMF。 |
| Stage 6 / final ADC PMF | `ALG-013` algorithm policy | `policy.final_adc_pmf_projection` | Annex D3 或 reference-support/tap projection。 |
| Stage 7 / MLSD added noise | `ALG-014` algorithm policy | `policy.added_noise_pdf` | Gaussian addition 或 scaled-total-PDF calibration。 |
| Stage 7 / MLSD noise PSD | `ALG-015` algorithm policy | `policy.mlsd_quantization_psd` | Full pre-DTE filtered quantization noise 或 main-tap-white treatment。 |
| Stage 7 / DER recurrence | `ALG-016` algorithm policy | `policy.sequence_termination` | Fixed-length sum 或 reference relative-tail termination。 |
| Stage 7 / reported DER | `ALG-017` algorithm policy | `policy.reported_der` | Raw sequence DER 或 baseline-PDF re-evaluation。 |

## 明確不納入本表

- Guard methods、input validation、error handling 與 data-presence paths。
- `cascade_ir(force_grid=False)`：caller-owned diagnostic/complete-record utility；沒有獨立 Project Config selector，因此原 `NUM-001` 已退休。
- `policy.xtalk_pmf_accumulation`：fixed single-value behavior，不是選擇。
- Retired B-009 `interference_pmf_method`：已無 selector。
- Former E-007 final-quantization accumulation：無 selectable control，保留為 deferred technical issue。
- Retired B-001／ALG-005：178A measured S4P 固定依 D3.2 先做 single-ended
  renormalization；native S2P 是 input representation dispatch，不是算法分支。

## CP-BR 下一輪審查欄位

每一列接著補 source location、accepted purpose、required stage interface、
status/provenance record、legal combinations 與 current test evidence。若某列實際
是 input boundary、fixed behavior 或 execution-only numerical control，會經使用者
確認後重新分類，不會默默當成 extension seam。
