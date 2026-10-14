# Ad Hoc mapping field table

This table follows `io/conversion/mapping_rules.py`. Read the [contract](adhoc_mapping_contract.md) for selection, requiredness, provenance, source exclusions, and export behavior. All listed targets belong to the mapping view. Case metadata, channels, policy defaults and fixed single-run baselines are intentionally separate.

Unless stated otherwise, values are required. Runtime adapters retain responsibility for typed validation; no COM calculation is performed by conversion.

178A 新模板使用唯一可見的 `fixed_config.align_to_ref` 開關；它與 optional `noise_grid_num_ui` 都是 project-owned policy，**不從 Ad Hoc 映射**。舊 workbook 的 `out_of_measured`、`channel_renormalization_order`、`pre_dte_adc_clipping_convention`、`final_adc_quantization_convention` 與各 `run_config.*.pmf_dy_override` 仍可讀取，以保持既有 case 的可重現性。`align_to_ref=True` 時由 `com_excel_io_178A` 在 project→runtime 邊界展開有效具名方法與 PMF 精度值；model 不接收或判斷此開關。reference 分支只供 SiCoPR／MATLAB 4.17 比對，均非 general method。

## 93A

| Project field | Source key(s) | Project unit | Method | Transformation / requirement |
|---|---|---|---|---|
| `fixed_config.fb` | f_b | Hz | converted | f_b × 1e+09; keyword units govern Required. |
| `fixed_config.target_df` | Delta_f | Hz | converted | Delta_f × 1e+09; keyword units govern Required. |
| `fixed_config.Tr` | T_r | s | converted | T_r × 1e-09; keyword units govern Required. |
| `fixed_config.eta_0` | eta_0 | V^2/Hz | converted | eta_0 × 1e-09; keyword units govern Required. |
| `fixed_config.per_ui` | M | samples/UI | direct | M Required. |
| `fixed_config.fr` | f_r, f_b | Hz | derived | f_r × f_b × 1e9 Hz Required. |
| `fixed_config.R_LM` | R_LM | dimensionless | direct | R_LM Required. |
| `fixed_config.SNR_TX` | SNR_TX | dB | direct | SNR_TX Required. |
| `fixed_config.sigma_RJ` | sigma_RJ | UI | direct | sigma_RJ Required. |
| `fixed_config.A_DD` | A_DD | UI | direct | A_DD Required. |
| `fixed_config.L` | L | levels | direct | L Required. |
| `fixed_config.DER_0` | DER_0 | dimensionless | direct | DER_0 Required. |
| `fixed_config.N_b` | N_b | UI/taps | direct | N_b Required. |
| `fixed_config.c_m3` | c(-3) | dimensionless | direct | c(-3) Required. |
| `fixed_config.num_pre` | TX tap layout | tap index | derived | Main index of [c(-3), c(-2), c(-1), c(0), c(1)] Required. |
| `fixed_config.f_z` | f_z | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_LF` | f_HP_PZ | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_p1` | f_p1 | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_p2` | f_p2 | Hz | converted | GHz to Hz Required. |
| `search_config.c_m2` | c(-2) | dimensionless | converted | Source search range; single-run baseline is separate Required. |
| `search_config.c_m1` | c(-1) | dimensionless | converted | Source search range; single-run baseline is separate Required. |
| `search_config.c_1` | c(1) | dimensionless | converted | Source search range; single-run baseline is separate Required. |
| `search_config.g_DC` | g_DC | dB | converted | Source search range; single-run baseline is separate Required. |
| `search_config.g_DC2` | g_DC_HP | dB | converted | Source search range; single-run baseline is separate Required. |
| `fixed_config.b_max` | N_b, b_max(1), b_max(2..N_b) | dimensionless | derived | First-tap limit followed by N_b-1 remaining-tap limits Required. |
| `fixed_config.b_min` | N_b, b_min(1), b_min(2..N_b) | dimensionless | derived | First-tap limit followed by N_b-1 remaining-tap limits Required. |
| `fixed_config.txpkg_victim.C_d` | C_d | F | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.txpkg_victim.L_s` | L_s | H | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.txpkg_victim.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.txpkg_victim.z_p` | z_p (TX) | mm | reduced | Approved maximum selected testcase segment; no second segment Required. |
| `fixed_config.txpkg_victim.z_p2` | z_p (TX) | mm | reduced | Maximum reduction uses one segment; second segment disabled Allowed blank. |
| `fixed_config.txpkg_victim.Z_c` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.txpkg_victim.Z_c2` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.txpkg_victim.enable` | PKG_NAME | boolean | derived | Construct source profile including PKG_Null zero elements; no whole-package bypass inferred Required. |
| `fixed_config.txpkg_victim.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.txpkg_victim.a1` | package_tl_gamma0_a1_a2 | 1/(mm sqrt(GHz)) | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.txpkg_victim.a2` | package_tl_gamma0_a1_a2 | 1/(mm GHz) | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.txpkg_victim.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.txpkg_victim.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.txpkg_victim.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.txpkg_fext.C_d` | C_d | F | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.txpkg_fext.L_s` | L_s | H | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.txpkg_fext.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.txpkg_fext.z_p` | z_p (FEXT) | mm | reduced | Approved maximum selected testcase segment; no second segment Required. |
| `fixed_config.txpkg_fext.z_p2` | z_p (FEXT) | mm | reduced | Maximum reduction uses one segment; second segment disabled Allowed blank. |
| `fixed_config.txpkg_fext.Z_c` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.txpkg_fext.Z_c2` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.txpkg_fext.enable` | PKG_NAME | boolean | derived | Construct source profile including PKG_Null zero elements; no whole-package bypass inferred Required. |
| `fixed_config.txpkg_fext.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.txpkg_fext.a1` | package_tl_gamma0_a1_a2 | 1/(mm sqrt(GHz)) | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.txpkg_fext.a2` | package_tl_gamma0_a1_a2 | 1/(mm GHz) | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.txpkg_fext.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.txpkg_fext.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.txpkg_fext.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.txpkg_next.C_d` | C_d | F | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.txpkg_next.L_s` | L_s | H | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.txpkg_next.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.txpkg_next.z_p` | z_p (NEXT) | mm | reduced | Approved maximum selected testcase segment; no second segment Required. |
| `fixed_config.txpkg_next.z_p2` | z_p (NEXT) | mm | reduced | Maximum reduction uses one segment; second segment disabled Allowed blank. |
| `fixed_config.txpkg_next.Z_c` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.txpkg_next.Z_c2` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.txpkg_next.enable` | PKG_NAME | boolean | derived | Construct source profile including PKG_Null zero elements; no whole-package bypass inferred Required. |
| `fixed_config.txpkg_next.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.txpkg_next.a1` | package_tl_gamma0_a1_a2 | 1/(mm sqrt(GHz)) | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.txpkg_next.a2` | package_tl_gamma0_a1_a2 | 1/(mm GHz) | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.txpkg_next.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.txpkg_next.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.txpkg_next.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.rxpkg.C_d` | C_d | F | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.rxpkg.L_s` | L_s | H | reduced | Approved 178A→93A fallback: maximum selected-side element; nF/nH to SI Required. |
| `fixed_config.rxpkg.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.rxpkg.z_p` | z_p (RX) | mm | reduced | Approved maximum selected testcase segment; no second segment Required. |
| `fixed_config.rxpkg.z_p2` | z_p (RX) | mm | reduced | Maximum reduction uses one segment; second segment disabled Allowed blank. |
| `fixed_config.rxpkg.Z_c` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.rxpkg.Z_c2` | package_Z_c | ohm | reduced | Maximum selected-side impedance; Z_c2 remains required but unused with z_p2 empty Required. |
| `fixed_config.rxpkg.enable` | PKG_NAME | boolean | derived | Construct source profile including PKG_Null zero elements; no whole-package bypass inferred Required. |
| `fixed_config.rxpkg.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.rxpkg.a1` | package_tl_gamma0_a1_a2 | 1/(mm sqrt(GHz)) | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.rxpkg.a2` | package_tl_gamma0_a1_a2 | 1/(mm GHz) | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.rxpkg.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.rxpkg.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.rxpkg.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.A_v` | A_v | V | direct | A_ne uses RX profile; A_v/A_fe use TX profile Required. |
| `fixed_config.A_fe` | A_fe | V | direct | A_ne uses RX profile; A_v/A_fe use TX profile Required. |
| `fixed_config.A_ne` | A_ne | V | direct | A_ne uses RX profile; A_v/A_fe use TX profile Required. |
| `fixed_config.R_0` | R_0 | ohm | direct | Global single-ended COM reference resistance. Required. |
| `fixed_config.R_d_tx` | R_d | ohm | converted | TX-side die termination from the selected TX package profile. Required. |
| `fixed_config.R_d_rx` | R_d | ohm | converted | RX-side die termination from the selected RX package profile. Required. |

## 178A

| Project field | Source key(s) | Project unit | Method | Transformation / requirement |
|---|---|---|---|---|
| `fixed_config.fb` | f_b | Hz | converted | f_b × 1e+09; keyword units govern Required. |
| `fixed_config.target_df` | Delta_f | Hz | converted | Delta_f × 1e+09; keyword units govern Required. |
| `fixed_config.sparam_frequency_limit_GHz` | flim | GHz | converted | Source values expressed in Hz are divided by 1e9; already-GHz values are preserved. Optional intrinsic channel-ingestion boundary; blank project value maps to `None` and keeps the complete measured record. |
| `fixed_config.Tr` | T_r | s | converted | T_r × 1e-09; keyword units govern Required. |
| `fixed_config.eta_0` | eta_0 | V^2/Hz | converted | eta_0 × 1e-09; keyword units govern Required. |
| `fixed_config.per_ui` | M | samples/UI | direct | M Required. |
| `fixed_config.fr` | f_r, f_b | Hz | derived | f_r × f_b × 1e9 Hz Required. |
| `fixed_config.R_LM` | R_LM | dimensionless | direct | R_LM Required. |
| `fixed_config.SNR_TX` | SNR_TX | dB | direct | SNR_TX Required. |
| `fixed_config.sigma_RJ` | sigma_RJ | UI | direct | sigma_RJ Required. |
| `fixed_config.A_DD` | A_DD | UI | direct | A_DD Required. |
| `fixed_config.L` | L | levels | direct | L Required. |
| `fixed_config.DER_0` | DER_0 | dimensionless | direct | DER_0 Required. |
| `fixed_config.N_b` | N_b | taps | direct | N_b Required. |
| `fixed_config.c_m3` | c(-3) | dimensionless | direct | c(-3) Required. |
| `fixed_config.num_pre` | TX tap layout | tap index | derived | Main index of [c(-3), c(-2), c(-1), c(0), c(1)] Required. |
| `fixed_config.f_z1` | f_z | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_z2` | f_HP_PZ | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_p3` | f_HP_PZ | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_p1` | f_p1 | Hz | converted | GHz to Hz Required. |
| `fixed_config.f_p2` | f_p2 | Hz | converted | GHz to Hz Required. |
| `search_config.c_m2` | c(-2) | dimensionless | converted | Source search range; single-run baseline is separate Required. |
| `search_config.c_m1` | c(-1) | dimensionless | converted | Source search range; single-run baseline is separate Required. |
| `search_config.c_1` | c(1) | dimensionless | converted | Source search range; single-run baseline is separate Required. |
| `search_config.g_1` | g_DC | dB | converted | Source search range; single-run baseline is separate Required. |
| `search_config.g_2` | g_DC_HP | dB | converted | Source search range; single-run baseline is separate Required. |
| `fixed_config.c_0_min` | c(0) | dimensionless | direct | c(0) Required. |
| `fixed_config.b_first_max` | b_max(1) | dimensionless | direct | b_max(1) Required. |
| `fixed_config.b_first_min` | b_min(1) | dimensionless | direct | b_min(1) Required. |
| `fixed_config.w_pre1_max` | ffe_pre_tap1_max | dimensionless | direct | ffe_pre_tap1_max Required. |
| `fixed_config.w_post1_max` | ffe_post_tap1_max | dimensionless | direct | ffe_post_tap1_max Required. |
| `fixed_config.N_wg` | N_bg | groups | direct | N_bg Required. |
| `fixed_config.N_wf` | N_bf | taps/group | direct | N_bf Required. |
| `fixed_config.w_fixed_rest_max` | ffe_tapn_max | dimensionless | direct | ffe_tapn_max Required. |
| `fixed_config.w_float_max` | bmaxg | dimensionless | direct | bmaxg Required. |
| `fixed_config.b_rest_max` | b_max(2..N_b) | dimensionless | direct | b_max(2..N_b) Required. |
| `fixed_config.b_rest_min` | b_min(2..N_b) | dimensionless | direct | b_min(2..N_b) Required. |
| `fixed_config.N_qb` | N_qb | bits | direct | N_qb Required. |
| `fixed_config.P_qc` | P_qc | probability | direct | P_qc Required. |
| `fixed_config.mlsd_enable` | MLSE | boolean | direct | MLSE Required. |
| `fixed_config.d_w` | ffe_pre_tap_len | taps | derived | `ffe_pre_tap_len`: precursor tap count. Required. |
| `fixed_config.N_fix` | ffe_pre_tap_len, ffe_post_tap_len | taps | derived | `ffe_pre_tap_len + 1 + ffe_post_tap_len`: precursors, main cursor, then fixed postcursors. Required. |
| `fixed_config.N_max` | ffe_pre_tap_len, ffe_post_tap_len, N_bg, N_f | taps | derived | `N_fix` when `N_bg=0`; otherwise `ffe_pre_tap_len + N_f + 1`. Required. |
| `fixed_config.w_float_min` | bmaxg | dimensionless | derived | -bmaxg Required. |
| `fixed_config.mlsd_trunc_len` | N_tc (preferred), trunc | events | direct | Required when MLSE is enabled; no 128 default Blank only when MLSE disabled. |
| `fixed_config.minimum_com_limit` | COM Pass threshold | dB | direct | COM Pass threshold Blank only when MLSE disabled. |
| `fixed_config.delta_com_an` | add_rx_noise | dB | direct | Optional; runtime owns fallback to minimum_com_limit Allowed blank. |
| `fixed_config.txpkg_victim.device_term.C_d_seq` | C_d | F | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.txpkg_victim.device_term.L_s_seq` | L_s | H | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.txpkg_victim.device_term.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.txpkg_victim.device_pkg.z_p_seq` | z_p (TX) | mm | converted | Selected testcase column; NEXT lengths use RX profile Required. |
| `fixed_config.txpkg_victim.device_pkg.Z_c_seq` | package_Z_c | ohm | converted | package_Z_c Required. |
| `fixed_config.txpkg_victim.device_pkg.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.txpkg_victim.device_pkg.a1` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.txpkg_victim.device_pkg.a2` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.txpkg_victim.device_pkg.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.txpkg_victim.device_pkg.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.txpkg_victim.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.txpkg_victim.partial_host.enable` | Include PCB | boolean | derived | Include PCB Required. |
| `fixed_config.txpkg_victim.partial_host.C_0` | C_0 | F | converted | C_0 Required. |
| `fixed_config.txpkg_victim.partial_host.C_1` | C_1 | F | converted | C_1 Required. |
| `fixed_config.txpkg_victim.partial_host.z_h` | z_bp (TX) | mm | direct | z_bp (TX) Required. |
| `fixed_config.txpkg_victim.partial_host.Z_h` | board_Z_c | ohm | direct | board_Z_c Required. |
| `fixed_config.txpkg_victim.partial_host.gamma_0` | board_tl_gamma0_a1_a2 | 1/mm | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_victim.partial_host.a1` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_victim.partial_host.a2` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_victim.partial_host.tau` | board_tl_tau | ns/mm | direct | board_tl_tau Required. |
| `fixed_config.txpkg_fext.device_term.C_d_seq` | C_d | F | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.txpkg_fext.device_term.L_s_seq` | L_s | H | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.txpkg_fext.device_term.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.txpkg_fext.device_pkg.z_p_seq` | z_p (FEXT) | mm | converted | Selected testcase column; NEXT lengths use RX profile Required. |
| `fixed_config.txpkg_fext.device_pkg.Z_c_seq` | package_Z_c | ohm | converted | package_Z_c Required. |
| `fixed_config.txpkg_fext.device_pkg.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.txpkg_fext.device_pkg.a1` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.txpkg_fext.device_pkg.a2` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.txpkg_fext.device_pkg.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.txpkg_fext.device_pkg.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.txpkg_fext.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.txpkg_fext.partial_host.enable` | Include PCB | boolean | derived | Include PCB Required. |
| `fixed_config.txpkg_fext.partial_host.C_0` | C_0 | F | converted | C_0 Required. |
| `fixed_config.txpkg_fext.partial_host.C_1` | C_1 | F | converted | C_1 Required. |
| `fixed_config.txpkg_fext.partial_host.z_h` | z_bp (FEXT) | mm | direct | z_bp (FEXT) Required. |
| `fixed_config.txpkg_fext.partial_host.Z_h` | board_Z_c | ohm | direct | board_Z_c Required. |
| `fixed_config.txpkg_fext.partial_host.gamma_0` | board_tl_gamma0_a1_a2 | 1/mm | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_fext.partial_host.a1` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_fext.partial_host.a2` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_fext.partial_host.tau` | board_tl_tau | ns/mm | direct | board_tl_tau Required. |
| `fixed_config.txpkg_next.device_term.C_d_seq` | C_d | F | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.txpkg_next.device_term.L_s_seq` | L_s | H | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.txpkg_next.device_term.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.txpkg_next.device_pkg.z_p_seq` | z_p (NEXT) | mm | converted | Selected testcase column; NEXT lengths use RX profile Required. |
| `fixed_config.txpkg_next.device_pkg.Z_c_seq` | package_Z_c | ohm | converted | package_Z_c Required. |
| `fixed_config.txpkg_next.device_pkg.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.txpkg_next.device_pkg.a1` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.txpkg_next.device_pkg.a2` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.txpkg_next.device_pkg.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.txpkg_next.device_pkg.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.txpkg_next.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.txpkg_next.partial_host.enable` | Include PCB | boolean | derived | Include PCB Required. |
| `fixed_config.txpkg_next.partial_host.C_0` | C_0 | F | converted | C_0 Required. |
| `fixed_config.txpkg_next.partial_host.C_1` | C_1 | F | converted | C_1 Required. |
| `fixed_config.txpkg_next.partial_host.z_h` | z_bp (NEXT) | mm | direct | z_bp (NEXT) Required. |
| `fixed_config.txpkg_next.partial_host.Z_h` | board_Z_c | ohm | direct | board_Z_c Required. |
| `fixed_config.txpkg_next.partial_host.gamma_0` | board_tl_gamma0_a1_a2 | 1/mm | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_next.partial_host.a1` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_next.partial_host.a2` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.txpkg_next.partial_host.tau` | board_tl_tau | ns/mm | direct | board_tl_tau Required. |
| `fixed_config.rxpkg.device_term.C_d_seq` | C_d | F | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.rxpkg.device_term.L_s_seq` | L_s | H | converted | Selected TX/RX device row; nF/nH to SI Required. |
| `fixed_config.rxpkg.device_term.C_b` | C_b | F | converted | C_b Required. |
| `fixed_config.rxpkg.device_pkg.z_p_seq` | z_p (RX) | mm | converted | Selected testcase column; NEXT lengths use RX profile Required. |
| `fixed_config.rxpkg.device_pkg.Z_c_seq` | package_Z_c | ohm | converted | package_Z_c Required. |
| `fixed_config.rxpkg.device_pkg.gamma_0` | package_tl_gamma0_a1_a2 | 1/mm | converted | Selected profile coefficient 1; no maximum across different coefficients Required. |
| `fixed_config.rxpkg.device_pkg.a1` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 2; no maximum across different coefficients Required. |
| `fixed_config.rxpkg.device_pkg.a2` | package_tl_gamma0_a1_a2 | per package TL formula | converted | Selected profile coefficient 3; no maximum across different coefficients Required. |
| `fixed_config.rxpkg.device_pkg.tau` | package_tl_tau | ns/mm | direct | package_tl_tau Required. |
| `fixed_config.rxpkg.device_pkg.C_p` | C_p | F | converted | C_p Required. |
| `fixed_config.rxpkg.R0` | R_0 | ohm | direct | R_0 Required. |
| `fixed_config.rxpkg.partial_host.enable` | Include PCB | boolean | derived | Include PCB Required. |
| `fixed_config.rxpkg.partial_host.C_0` | C_0 | F | converted | C_0 Required. |
| `fixed_config.rxpkg.partial_host.C_1` | C_1 | F | converted | C_1 Required. |
| `fixed_config.rxpkg.partial_host.z_h` | z_bp (RX) | mm | direct | z_bp (RX) Required. |
| `fixed_config.rxpkg.partial_host.Z_h` | board_Z_c | ohm | direct | board_Z_c Required. |
| `fixed_config.rxpkg.partial_host.gamma_0` | board_tl_gamma0_a1_a2 | 1/mm | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.rxpkg.partial_host.a1` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.rxpkg.partial_host.a2` | board_tl_gamma0_a1_a2 | per host TL formula | converted | board_tl_gamma0_a1_a2 Required. |
| `fixed_config.rxpkg.partial_host.tau` | board_tl_tau | ns/mm | direct | board_tl_tau Required. |
| `fixed_config.A_v` | A_v | V | direct | A_ne uses RX profile; A_v/A_fe use TX profile Required. |
| `fixed_config.A_fe` | A_fe | V | direct | A_ne uses RX profile; A_v/A_fe use TX profile Required. |
| `fixed_config.A_ne` | A_ne | V | direct | A_ne uses RX profile; A_v/A_fe use TX profile Required. |
| `fixed_config.R_0` | R_0 | ohm | direct | Global single-ended COM reference resistance. Required. |
| `fixed_config.R_d_tx` | R_d | ohm | converted | TX-side die termination from the selected TX package profile. Required. |
| `fixed_config.R_d_rx` | R_d | ohm | converted | RX-side die termination from the selected RX package profile. Required. |
