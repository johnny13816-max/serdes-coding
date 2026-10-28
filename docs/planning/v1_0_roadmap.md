# v1.0 platform roadmap

## 目標

v1.0 是可重現、可理解、可擴充的 COM model platform。它不只要求數值正確，還要求清楚的 function
call tree、config/status ownership、workbook UX、study extension framework、文件與 release evidence。

```text
v1.0 foundation
├─ numerical COM baseline
├─ version-owned architecture
├─ workbook → project → runtime interface
├─ stage/utility extension framework
├─ reporting and human-readable status
├─ reproducible validation/search
└─ documentation, packaging and public boundary
```

## Review roadmap

| Phase | 審查範圍 | 目前狀態 | Exit evidence |
|---|---|---|---|
| P1 | 產品邊界：public baseline／internal fork／research | Complete | `evolution_strategy.md` |
| P2 | software layers、version ownership、93A/178A decoupling | Complete | ARC-178A-001/004 commits and anchors |
| P3 | workbook、Ad Hoc→project→runtime mapping、UX/provenance | **Next / not reviewed as a whole** | mapping tree、field ownership、user workflow review |
| P4 | config/status dataclass tree、serialization、過度分支 | Partial | reviewed trees、lifecycle and compatibility evidence |
| P5 | function call tree、stage responsibility、extension seams | Partial | stage-wise owner/call review and unresolved list |
| P6 | utility contracts：S-parameter/grid/PSD/PMF/response | Partial | invariant/round-trip/loss policy review |
| P7 | reporting、to_string、plots、single/search artifacts | Partial | shared renderer evidence and open presentation closure |
| P8 | documentation、study workflow、governance、learning notes | Partial | authority consistency and implementation-note coverage |
| P9 | 93A boundary、regression、package、release/tag | Not complete | G7/G9/G10/G11 in release gate |

`docs/models/178A/design_review.md` 是逐章 review 記錄；不得用已完成的 P2 架構 decoupling 推定 P3–P9
全部通過。只有每一列具備 exit evidence 後，才能將 178A platform review 宣告完成並進入 93A 修改。

## 下一個建議焦點

P3：以使用者門面為主，先畫出 Ad Hoc config → project workbook → runtime config/profile 的 tree，
再逐欄確認 source、default、requiredness、validation、provenance 與 workbook 暴露程度。這是 read-only
review；發現修改需求後再依責任邊界建立 contract。

## 與其他狀態文件的分工

- `open_issues.xlsx`：所有 proposal 與歷史 tracker。
- `active_contracts.md`：唯一 active／next execution boundary。
- `HANDOFF.md`：跨對話的短期狀態。
- `v1_0_release_gate.md`：是否能發布，不代表 roadmap 每章的設計品質。
- 本文件：v1.0 平台建設方向與逐章完成度。
