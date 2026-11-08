# ALG-006 — Out-of-measured transfer

狀態：TC-006R2 與 Amendment A 已於 2026-11-07 獲使用者核准；實作與
契約驗證通過，待獨立 commit／remote sync。

## 決策與邊界

`COMConfig.policy.out_of_measured` 保留 `cosine_decay`／`zero_padding` 兩個
具名算法。D3.2 要求 filtered voltage transfer function 必要時由 bounded
measurement range 外插至 half sampling frequency，但沒有指定唯一算法；因此
本項保留 project policy，而不是將其中一個方法宣告為通用規範答案。

ALG-006 一致控制 terminated scalar `H_21` 從 effective measured boundary 到
analysis Nyquist 的延伸，包括 continuous transfer path 與 `bilinear_iir` pulse
所需的 finite-record preparation。`sparam_frequency_limit_Hz` 仍是獨立的 case
input boundary；ALG-007 只選 CTLE realization，不擁有 out-of-measured 方法。

## Owner 與資料流

```text
COMConfig.policy.out_of_measured
└─ _build_paths() / _build_path()                 forwarding only
   ├─ LinkSegment.from_tf() -> resample_tf()      H_21 / H_all consumer
   └─ _realize_ctle_pulse()
      └─ _reference_fd_to_td_record()
         └─ resample_tf()                         bilinear path/TX-noise consumer
```

`resample_tf()` 是數值 owner。`_build_path()` 不得在結果形成後使用固定 cutoff
補零；victim、NEXT、FEXT 與 victim TX-noise equivalent channel 共用同一
resolved policy。

## 不變量與驗收

- `S_ch`、`S_all`、case frequency limit 與 boundary 內的 completed `H_21`
  不因 ALG-006 選項改變。
- `zero_padding` 保留 endpoint，並將 `f > f_stop` 的 complex response 設為零。
- `cosine_decay` 使用既有 phase/group-delay extension 與 magnitude cosine taper。
- SiCoPR fixed case 的 67 GHz＋zero-padding baseline、stage digests、COM_DFE 與
  final COM 必須不變。
- 93A、ALG-001 missing-DC、ALG-005 channel ingestion 及 ALG-007 CTLE equations
  不在本次修改範圍。

## 驗證結果

- Focused ALG-006／CTLE／policy regression：`41 passed`。
- SiCoPR fixed 67 GHz＋`zero_padding` production golden：`1 passed`；MSE
  `0.0061912610245255335`、COM_DFE `1.5247607834259893 dB`、final COM
  `2.895898684873246 dB` 與既有 stage digests 全部不變。
- 完整 suite：`197 passed, 17 skipped, 7 failed`。七項 failure 均不在本次
  diff／production call path：一項 dataclass migration stale expectation、兩個
  MLSD mock subtests 少列既有 `pmf_projection_method`、一項既有 continuous-CTLE
  post-FFE MSE stale golden，以及三項缺少 local-only Ad Hoc workbook。尤其
  post-FFE case 是 `cosine_decay + continuous_tf`；本次 bilinear helper 在
  continuous branch return 後不會執行，故不以修改該 golden 作為本契約修正。

```text
Deviation: full suite 無法達成全綠
Reason: 七項既有 failure 與 ALG-006 修改無資料流或檔案歸屬關係
Substitute evidence: focused 41 passed；fixed production golden 1 passed 且
                     MSE／COM／stage digests 不變
User decision needed: no
```

Durable owner 說明已同步至 Stage 1、config tree、branch registry 與 validation
boundary 文件。Commit 與 remote sync evidence 於結案狀態文件記錄。
