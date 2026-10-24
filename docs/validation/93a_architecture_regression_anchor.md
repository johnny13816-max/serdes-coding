# 93A architecture regression anchor

此 anchor 只保護 v1.0 架構整理前後的 93A production path；它不是 93A
spec correlation、SiCoPR alignment 或標準相容性證明。

## Baseline

- Evidence type: current working-tree production path
- Workbook: `cases/case_260915_report/93A/config.xlsx`
- Execution target: single run / final 93A PMF COM
- Implementation status: workbook schema implemented；golden test implemented
- Search space: workbook 可解析為 232,848 candidates，但本項不執行 full search

舊 case 的 package topology 與既有數值維持不變。新增的四組
`gamma_0/a1/a2/tau` 來自原 Ad Hoc workbook 選定的 TX
`PKG_HiR_CLASSB` 與 RX `PKG_Module` profiles；`b_min=0` 來自同一來源。
這些值是明確輸入，不使用 `COMPkgConfig` constructor defaults。

## Golden result

| Quantity | Value |
| --- | ---: |
| paths | 3 |
| DFE `ts` | 79,356 |
| DFE `pos` | 28 |
| DFE coefficient | 0.85 |
| FOM | 0.4603512834103074 |
| PMF `dy` | 4.658291240062964e-06 V |
| `A_ni` | 0.013807175235546622 V |
| COM | -9.43756398614581 dB |

自動化邊界由 `tests/test_com_model_93A_golden.py` 管理。ARC-178A-004
若改變 93A import ownership、shared primitives 或 status/config ownership，必須先後執行
此 test；任何數值變化都視為架構重構越界，除非另有核准的 93A model contract。

## Deferred mapping work

此 anchor 不把舊 package reduction 宣稱為目前 Ad Hoc→93A mapping。
現行 mapping 會改變 package reduction 與 COM，應以獨立 config/converter
contract 處理，不得混入 ARC-178A-004。

