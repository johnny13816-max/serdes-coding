# C01 Intake Evidence Check

Date: 2026-09-09

## Purpose

本文件用來判斷目前 C2M 50 mm candidate 是否可以作為第一個 Annex
178A external comparison case，暫定代號 `C01`。

目前目標不是調整 mapping，也不是跑新的 full search。目標是先確認：

- source workbook 是否可追溯；
- channel files 是否和來源資料同源；
- project workbook 的 config mapping 是否和外部結果使用的設定一致；
- 外部 8-9 dB COM result 是否有足夠 evidence 可以作為 comparison target。

在 exact C01 pairing 尚未成立前，本 case 只能稱為 candidate，不可稱為
validated reference case。

## Current Decision

目前結論：`C01` 尚未成立。

原因不是 channel 檔案本身明顯錯誤，而是缺少外部 comparison evidence：

- 原始 COM Ad Hoc config workbook 本體尚未在目前 worktree 中找到。
- 外部 8-9 dB COM result 尚未有 report、log、screenshot、CSV 或 tool metadata。
- 尚未確認外部結果使用的 package profile、search setting、noise/jitter setting
  與目前 `config_178A.xlsx` 完全相同。

## Candidate Case

Project case:

```text
cases/c2m_8023dj_4p13p0_50mm
```

Active project workbook:

```text
cases/c2m_8023dj_4p13p0_50mm/config/config_178A.xlsx
```

Do not use as authoritative 178A input:

```text
cases/c2m_8023dj_4p13p0_50mm/config.xlsx
```

Observed reason: the workbook exists, but the inspected `fixed_config`,
`search_config`, and `channels` worksheets currently contain no cell content.

## Source Identity

Declared source config workbook:

```text
IEEE802_3dj_COM_Adhoc/config_templates/C2M/200G/config_com-4p13p0_802p3dj_d2p3_200G_C2M_TP0_TP2_Egress_26_01_27.xlsx
```

Status:

- The source workbook name is recorded in the project workbook and README.
- The source workbook file itself was not found in the current worktree.
- No SHA256 hash, original download URL, or external result package is currently
  available for this workbook.

Local channel archive:

```text
reference_data/COM_channel_data/C2M/mellitz_3dj_02_2409.zip
```

Archive SHA256:

```text
19D8526E303A9BDD4F841840BA17CA847215E66771567B68E7966659764CFF4B
```

Public-source note:

- The IEEE public tools/channel-data page contains C2M channel contribution
  entries, including C2M cabled host channel data associated with Brandon Gore
  and Rich Mellitz.
- The exact local archive filename `mellitz_3dj_02_2409.zip` has not yet been
  tied to a specific public download URL or page entry by direct evidence.

## Channel Mapping

The local case uses renamed S4P files:

```text
channels/victim_thru.s4p
channels/next_1.s4p ... channels/next_6.s4p
channels/fext_1.s4p ... channels/fext_5.s4p
```

These map to the 50 mm entries in `mellitz_3dj_02_2409.zip`:

| Local file | Archive entry |
| --- | --- |
| `victim_thru.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_thru.s4p` |
| `next_1.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_next1.s4p` |
| `next_2.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_next2.s4p` |
| `next_3.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_next3.s4p` |
| `next_4.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_next4.s4p` |
| `next_5.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_next5.s4p` |
| `next_6.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_next6.s4p` |
| `fext_1.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_fext1.s4p` |
| `fext_2.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_fext2.s4p` |
| `fext_3.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_fext3.s4p` |
| `fext_4.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_fext4.s4p` |
| `fext_5.s4p` | `host_pkg_top_50mm_max_skew_cable_module_pin_pad_fext5.s4p` |

Important distinction:

- Raw SHA256 hashes differ between local files and archive entries.
- Each local file is larger than the corresponding archive entry by `40005`
  bytes.
- Newline-normalized text comparison is `True` for all 12 files.

Interpretation:

- Current evidence supports "same numerical S4P content after newline
  normalization."
- Current evidence does not support "bit-for-bit identical copy."
- Future comparison notes should preserve this distinction.

## Local Channel Hashes

Raw local SHA256:

| Local file | SHA256 |
| --- | --- |
| `victim_thru.s4p` | `54786563A9EE5CFB85629CF154BD50CF4F4A1277B34BD812167A24A0B95CEB68` |
| `next_1.s4p` | `742FF4DBF5AC5D4D93C89E398E5CFE1A873C51A253C2CD839C7FC55C8F856AB8` |
| `next_2.s4p` | `ABFBF209A78CB4F4186C0B74149961C4EC9E0B9915EF1FBFBBF6128B380DC901` |
| `next_3.s4p` | `979A62635BF63E5B9484EFBD38BAEFDAE7621A02F2666AF2666230817B9FF96A` |
| `next_4.s4p` | `782BCC3D413FE33E97D1C478A98262B4767E4FFBDFFAA8633BCC8B1D8D3CF771` |
| `next_5.s4p` | `F149F88BBF592D7AF29A7F3F3534E84E32D17A6BA66922FC96149ED1A345C5CA` |
| `next_6.s4p` | `6C8D1569582DE53967BCC433B63DD8F162EED35E0DF882706284C6287F95749E` |
| `fext_1.s4p` | `FDC19B020E766368D16E82F867D034EC4798B8EC5F7756A2597331FB0BD601D3` |
| `fext_2.s4p` | `BD2783F1939101F3C99F088A28698D134FAAC5EA65E09D0C3A1F887D9DEE5435` |
| `fext_3.s4p` | `E0C1A6B4BA7FF861A31BADB9E9941BA306BCA2FC143147AB6FA86F0E954AA09D` |
| `fext_4.s4p` | `3DDC7DA776470E01B30CB16A474B2CFEFB59A4FB0FA020DE61BB853CB282C07B` |
| `fext_5.s4p` | `0617E00CF2E0C5BA307729C7D8FA6E3AF81AAE5089487EDC2F05459D9ECE1882` |

## Project Workbook Mapping Snapshot

Current `config_178A.xlsx` declares:

| Area | Project value | Note |
| --- | --- | --- |
| case id | `c2m_8023dj_4p13p0_50mm` | Candidate C2M 50 mm case |
| `fb` | `106.25e9 Hz` | Source description: COM Ad Hoc `f_b = 106.25 GBd` |
| `per_ui` | `32` | Source description: COM Ad Hoc `M` |
| `target_df` | `10e6 Hz` | Source description: COM Ad Hoc `Delta_f = 0.01 GHz` |
| port order | `0,2,1,3` | Project 0-based form of MATLAB 1-based `[1 3 2 4]` |
| `R0` | `46.25 ohm` | Used for all listed paths |
| gamma source/load | `0 / 0` | Used for all listed paths |
| TX victim package | `PKG_HiR_CLASSB` implied by description | Needs source workbook confirmation |
| TX FEXT package | same as TX victim | Needs source workbook confirmation |
| TX NEXT package | package length starts with `44 mm` | Needs source workbook confirmation |
| RX package | `PKG_Module` implied by description | Needs source workbook confirmation |
| partial host | disabled | Source description: Include PCB = 0 |
| `SNR_TX` | `33.5 dB` | Needs source workbook confirmation |
| `sigma_RJ` | `0.01 UI` | Needs source workbook confirmation |
| `A_DD` | `0.02 UI` | Needs source workbook confirmation |
| `eta_0` | `7.9e-18 V^2/Hz` | Description says converted from `7.9e-9 V^2/GHz` |
| `N_qb` | `6 bits` | ADC quantization bits |
| `P_qc` | `1e-7` | ADC clipping probability |
| `L` | `4` | PAM4 |
| `DER_0` | `2e-5` | Target detector error ratio |
| MLSD | disabled | First C01 comparison should remain DFE-only unless source profile enables MLSD |

Search config currently enables:

| Parameter | Enabled | Values |
| --- | --- | --- |
| `c_m2` | yes | `0.14:-0.02:0` |
| `c_m1` | yes | `-0.34:0.02:0` |
| `c_1` | yes | `-0.2:0.02:0` |
| `g_1` | yes | `-20:1:0` |
| `g_2` | yes | `-6:1:0` |
| `keep_top_n` | yes | `10` |
| `keep_all_rows` | yes | `False` |
| `continue_on_error` | yes | `True` |

Run profiles currently declare:

| Profile | Key behavior |
| --- | --- |
| `single_run` | target `dfe`, `gaussian_approx`, coarse PMF grid, simplified floating mode, each phase |
| `search_sweep` | target `mse`, `gaussian_approx`, coarse PMF grid, heuristic floating mode, coarse-fine phase |
| `search_final` | target `dfe`, `gaussian_approx`, fine PMF grid, heuristic floating mode, each phase |

## Config / Channel Differences To Resolve

The following are not necessarily bugs. They are unresolved pairing questions.

| Topic | Current project value | Needed external evidence |
| --- | --- | --- |
| Source workbook | only filename is known | actual workbook file, SHA256, source URL |
| External COM | only "8-9 dB" is known from discussion | exact value, report/log/screenshot, tool version |
| Package profile | workbook text says TX `PKG_HiR_CLASSB`, RX `PKG_Module` | source workbook table values and selected profile evidence |
| Channel files | newline-normalized match to local archive entries | proof that external result used the same 50 mm archive entries |
| Search strategy | project-owned search and final rerun profiles | external search candidate selection and final candidate |
| CTF fields | project maps `g_1/g_2/f_z1/f_z2/f_p1/f_p2/f_p3` | source workbook fields and exact 178A interpretation |
| Quantization `V_qc` | project uses `gaussian_approx` for current run profiles | external tool method or intermediate value |
| PMF grid controls | project-owned numerical controls | external tolerance or intermediate output |
| MLSD | disabled | external profile must confirm DFE-only or explicitly enable MLSD |

## Required External Evidence For C01

Minimum evidence before starting comparison:

- [ ] Original source workbook file.
- [ ] Source workbook SHA256.
- [ ] Source workbook download URL or public provenance note.
- [ ] External tool name and version.
- [ ] External report/log/screenshot/CSV containing final COM.
- [ ] Exact final COM value, not only "8-9 dB".
- [ ] Whether the external result is single-run or search result.
- [ ] If search result, selected TX FFE / CTF / DTE settings.
- [ ] Confirmation that the external result used 50 mm channel files, not 150,
      250, or 500 mm.
- [ ] Confirmation that the external result used the same package profiles.
- [ ] Confirmation that MLSD was disabled or intentionally enabled.

Strong evidence before claiming validated external comparison:

- [ ] `H_21` or SDD/path transfer intermediate value.
- [ ] `H_ctf` or selected CTLE/CTF transfer.
- [ ] Pulse response / sampled pulse / selected `ts` and `pos`.
- [ ] DTE coefficients and MSE.
- [ ] `A_s`.
- [ ] Noise, jitter, crosstalk, quantization, residual ISI impairment values.
- [ ] PMF quantile / `A_ni`.
- [ ] DER and final COM.

## Claim Boundary

Allowed wording before C01 is complete:

```text
C2M 50 mm candidate case prepared for Annex 178A source-pairing audit.
Channel files are newline-normalized equivalent to the local 50 mm channel
archive entries. External COM pairing is not yet established.
```

Forbidden wording before C01 is complete:

```text
Validated against IEEE COM.
Matches official COM.
IEEE COM compliant.
Correlated to silicon.
Validated C2M 50 mm external result.
```

Allowed wording after exact pairing and stage comparison:

```text
Annex 178A spec-defined execution path, validated against named external
reference case C01 within documented evidence and limitations.
```

## Next Minimum Verifiable Action

Do this next:

1. Locate the original source workbook:

   ```text
   config_com-4p13p0_802p3dj_d2p3_200G_C2M_TP0_TP2_Egress_26_01_27.xlsx
   ```

2. Record:

   ```text
   file path
   SHA256
   source URL or provenance
   download/acquisition date
   ```

3. Extract only the source workbook fields needed to confirm pairing:

   ```text
   fb, M, Delta_f
   channel filenames
   port order
   R0
   package profile names and selected values
   TX FFE/search values
   CTF/search values
   DTE limits
   SNR_TX, sigma_RJ, A_DD, eta_0, N_qb, P_qc
   DER_0
   MLSD enable/disable state
   ```

4. Compare those fields to `config_178A.xlsx`.

Only after this passes should the project run a limited single-run or
candidate-level comparison. Do not start a broad refactor or new full search as
part of this intake task.
