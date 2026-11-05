# CP-BR — 178A algorithm-branch coverage matrix

> 狀態：**初始盤點，尚未逐項對照 source**。權威技術文件仍為
> [`../models/178A/branch_behavior_registry.md`](../models/178A/branch_behavior_registry.md).
> 本工作矩陣依 model stage 歸納現有算法／數值選擇，供 CP-BR 審查；尚不宣稱
> coverage 完整。

`rg_name` 是實際 typed project-runtime configuration path。run control 的
`execution.<profile>` 代表 `single_run`、`search_sweep` 或 `search_final`，
由 project 的 `run_config` sheet 解析。`—` 表示 internal utility argument，
不是可由 project config 選擇的欄位。

| Stage | Branch | rg_name (project config) | Description |
|---|---|---|---|
| Path construction | B-001 Channel renormalization order | `policy.channel_renormalization_order` | 在 differential conversion 前選擇 SDD-first 或 four-port S4P-first renormalization。 |
| Path construction | B-002 Out-of-measured-band transfer | `policy.out_of_measured` | 在量測頻帶外選擇 cosine-decay extrapolation 或 zero padding。 |
| Path construction | B-003 CTLE pulse realization | `policy.ctle_pulse_realization` | 選擇 continuous transfer-function 或 bilinear-IIR finite-record pulse realization。 |
| Shared response utility | B-020 Time-domain cascade grid | — (`cascade_ir(force_grid=...)`) | 選擇保留原固定 grid 並檢查 tail，或使用完整 linear-convolution record；目前不由 project config 選擇。 |
| Multiple stages involved / Shared L3 (Stages 2, 3, 5, 7) | B-005 Eq-channel impairment length | `policy.eq_ch_imp_len`, `policy.num_trunc_ui` | 完整 one-sample/UI impairment eq-channel 先形成；PSD 前統一選 `full` 或依 `num_trunc_ui` 做 `truncated`。Stage 7 的 MLSD `S_isi` 也走同一入口；workbook 獨立控制。 |
| Pre-DTE impairment / ADC | B-006 Pre-DTE ADC clipping convention | `policy.pre_dte_adc_clipping_convention` | 選擇 Annex D3 clipping 或 reference-only RJ/tail convention。 |
| Pre-DTE impairment / ADC | E-002 ADC-input PMF method | `execution.<profile>.pre_dte_pmf_method` | 選擇 Gaussian approximation 或 exact PMF flow 的 pre-DTE clipping。 |
| Multiple PMF stages / shared L3 + PMF utility | B-008 Discrete-amplitude projection | `policy.pmf_projection_method` | `Pmf1D` 只保存 PMF data；各 stage 把同一 project policy 明示傳入 projection operation，exact PAM atoms 先乘 tap，再由唯一 utility decision point 選 linear mass deposition 或 nearest-bin projection。B-009 平行 FIR path 已移除。 |
| Multiple PMF stages / shared L3 + PMF utility | B-010/B-011 PDF→PMF discretization | `policy.pdf_to_pmf_method` | `bin_integral` 或 `pmf_sample`；Gaussian／uniform 各自執行 SiCoPR 對應的離散化 rule。 |
| Pre-DTE impairment / PMF | B-012 PMF amplitude scaling | `policy.pmf_scaling_method` | 在 PMF scaling 時選擇 mass deposition 或 ordinate interpolation。 |
| Pre-DTE impairment / PMF | E-003 PMF grid quality | `execution.<profile>.pmf_grid_quality` | 選擇 coarse 或 fine derived PMF grid。 |
| Pre-DTE impairment / PMF | E-004 PMF convergence controls | `execution.<profile>.pmf_keep_mass`, `execution.<profile>.pmf_dy_override` | 選擇 retained mass，並可用明示值取代 derived grid spacing。 |
| MMSE DTE | E-005 Floating FFE solve | `execution.<profile>.floating_mode` | 選擇 heuristic、simplified 或 spec-defined floating-tap placement flow。 |
| MMSE DTE | E-006 Sampling-phase search | `execution.<profile>.pos_sweep_method`, `execution.<profile>.pos_coarse_stride` | 選擇 exhaustive 或 coarse/fine sampling-phase evaluation。 |
| Post-FFE impairment | B-004 RX FFE record realization | `policy.rxffe_record_realization` | 選擇 fixed-grid linear convolution 或 finite-record circular shift-sum。 |
| DFE COM / final PMF | B-007 Final COM `V_qc` convention *(pending D3p2)* | `policy.final_com_vqc_convention` | 選擇沿用 Stage 5 selected-phase ADC-input `V_qc/delta`，或依 SiCoPR final composition 重建。main-tap accumulation 不屬此分支。 |
| DFE COM / final PMF | B-013 Final PMF grid | `policy.final_pmf_grid` | 選擇受 absolute/relative limit 約束的 fine grid，或直接 relative-to-`As` grid。 |
| DFE COM / final PMF | B-014 Gaussian support | `policy.gaussian_n_sigma_override` | 使用 config Gaussian support 或明示的 reference-profile override。 |
| DFE COM / final PMF | B-015 Final ADC PMF projection | `policy.final_adc_pmf_projection` | 選擇 Annex D3 或 reference-support/tap projection；後者要求 reference-only quantization convention。 |
| MLSD COM | B-016 Added-noise PDF | `policy.added_noise_pdf` | 選擇 Annex Gaussian addition 或 scaled-total-DFE-PDF calibration。 |
| MLSD COM | B-017 Sequence termination | `policy.sequence_termination` | 選擇 fixed-length sequence sum 或 reference relative-tail realization。 |
| MLSD COM | B-018 Reported DER | `policy.reported_der` | 選擇 raw sequence-sum DER 或以 baseline PDF re-evaluate 的 reported DER。 |
| MLSD COM | B-021 Quantization PSD | `policy.mlsd_quantization_psd` | 選擇完整 filtered pre-DTE noise 或 main-tap-white quantization treatment。 |

## 明確不納入本表

- `COMRunConfig.target`: pipeline termination gate, not a same-stage algorithm
  selection。
- Guard methods、input validation、error handling 與 data-presence paths。
- B-019 `channel.missing_dc_policy`：它由缺失 DC sample 觸發，屬 data-presence
  handling，不符合本次 algorithm-branch 定義。
- `policy.xtalk_pmf_accumulation`：fixed single-value behavior，不是選擇。

## CP-BR 下一輪審查欄位

每一列接著補 source location、accepted purpose、required stage interface、
status/provenance record、legal combinations 與 current test evidence。若某列實際
是 input boundary、fixed behavior 或 execution-only numerical control，會經使用者
確認後重新分類，不會默默當成 extension seam。
