# ALG-011 — RX FFE record realization

狀態：**Closed 2026-11-06**

日期：2026-11-06

Legacy ID：B-004

Implementation commit：`565ccba`（已推送 `origin/main`）

## 白話定義

Stage 4 已經求出 RX FFE taps。ALG-011 決定 Stage 5 要如何把這組 taps 套到
有限長度的 victim、XT 與 DDJ response record：保留原 grid、擴張 grid 保存完整
linear convolution，或在原有限 record 上做 circular shift-sum。它不重新求 taps，
也不改 Stage 4 MSE。

## 正式契約

| 項目 | 契約 |
|---|---|
| Class | `algorithm_policy` |
| RG | `policy.rxffe_record_realization` |
| Project default | `linear_fixed_grid` |
| Alternate | `linear_expanded_grid` |
| SiCoPR reference | `finite_record_circshift` |
| Sole owner | Stage 5 `_apply_rxffe_response()` |
| Direct scope | victim、all XT、DDJ；residual ISI 由同一 resolved victim record 建立 |
| Downstream consumers | Stage 6 DFE、Stage 7 MLSD、reporting |
| Excluded | Stage 4 MMSE solve／taps、pre-FFE responses、ADC-input PMF grid、final PMF grid |

## Coding-layer tree

```text
Workbook / profile facade
└── policy.rxffe_record_realization
    └── COMPolicyConfig validation + provenance
        └── Stage 5 COM.calculate_post_ffe_imp()
            ├── _resolve_post_ffe_response_cfg()
            ├── _apply_rxffe_response()              <- sole branch owner
            │   ├── victim h_w
            │   ├── XT h_XTs_w[*]
            │   └── DDJ h_w_J
            ├── residual h_ISI on the same response_cfg
            ├── COMPostFFEEqChannelStatus
            │   ├── record_realization
            │   └── response_cfg
            └── NUM-003 _resolve_post_ffe_imp_record_cfg()
                ├── full -> response_cfg
                └── truncated -> configured truncated record_cfg
                    ├── Stage 5 PSD status
                    └── Stage 7 MLSD noise PSDs
```

`SampledResponse.cascade_ir(force_grid=False, output_cfg=...)` 是 owner 使用的
caller-owned utility contract，不是另一個 selectable branch。`_calculate_h_J()`
只建立 pre-FFE adjacent-phase derivative，不接收 ALG-011 selector。

## 方法定義

- `linear_fixed_grid`：算完整 linear convolution，檢查超出原 grid 的 tail；通過後
  回到 `cfg.link`。超過 guard 即報 `GridOverflowError`。
- `linear_expanded_grid`：Stage 5 先建立共同 output grid，長度可容納
  `cfg.link.sampled_nfft + N_max - 1`；所有 response 保存完整 linear result。
- `finite_record_circshift`：每個 tap 在原有限 record 上 circular shift 後加總；
  保留 `cfg.link`，對齊 SiCoPR finite-record behavior。

## 與 NUM-003 的關係

ALG-011 決定 time-domain response 的 boundary method；NUM-003 決定
PSD/correlation record 的 `full`／`truncated` numerical domain。兩者不可合併：

```text
ALG-011 response_cfg
├── NUM-003 full      -> same response_cfg
└── NUM-003 truncated -> configured num_trunc_ui grid
```

MLSD 沒有另一個 ALG-011 selector，只能消費 Stage 5 已解析並記錄的 `record_cfg`。

## Closure gate

1. 三個 method 的 owner unit tests 通過。
2. victim／all XT／DDJ／ISI 共用 `response_cfg`。
3. full／truncated NUM-003 與 expanded record 的交互測試通過。
4. MLSD 消費 Stage 5 `record_cfg`，沒有自行重選 realization。
5. template config、branch matrix、registry、stage/call-tree 與 Python 3.7 utility export 同步。
6. SiCoPR case：`COM_DFE=1.5247607834259893 dB`、final
   `COM=2.895898684873246 dB`，不得改變 baseline。

## Closure evidence

- ALG-011／NUM-003／MLSD focused：`59 passed`；唯一 failure 是 Stage 4
  MSE 舊 golden 的 `3.45e-14` 差異，發生在 Stage 5 之前且不由本契約修改。
- Full regression：`186 passed, 17 skipped`；其餘 failures 是既有
  architecture/B-008 mock、已排除 reference data、sandbox temp 及 fingerprint
  expectations，無 ALG-011 新路徑 failure。
- SiCoPR production golden：`1 passed`，上述 DFE/final COM 與 intermediate
  digests 不變。
- Python 3.7 export validator passed；workbook formula/error scan 為 0，兩份
  workbook 均完成 visual inspection。
