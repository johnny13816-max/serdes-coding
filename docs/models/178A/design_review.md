# 178A v1.0 平台設計審查

狀態：**PASS（2026-10-27）**。178A architecture foundation 已通過；v1.0 release
仍受 93A golden boundary、report presentation、release-candidate regression 與
package/tag gates 約束。

本審查不再逐式重做已完成的 178A COM 演算法校準。既有 fixed-case golden、
SiCoPR 對齊結果與 full-search artifact 是 regression anchor；除非 regression、
規格證據或新 study 推翻它們，演算法基線視為已敲定。

本審查的目標是確認 178A 已經是一個可長期演進的平台，而不只是一個目前能算對
COM 的模型。平台必須能同時支援：

1. 公開、可重現的 COM baseline；
2. 公司內部延伸的設計分析工具；
3. 可比較替代 CDR、S-parameter、PSD、PMF 等方法的研究平台。

## 審查原則

每一章都回答以下問題：

- 對使用者公開的介面是什麼，哪個 module/object 負責？
- function call tree、config tree、status tree 是否反映同一個責任邊界？
- 是否有過度分支、重複狀態、隱藏轉換或不應由使用者理解的內部選項？
- 未來新增 stage 方法或 utility 方法時，應插在哪個 extension seam？
- 新方法屬於 baseline 修正、named parallel method，還是暫時 experiment？
- 文件、測試、artifact 與相容性規則是否足以防止設計漂移？

演算法數值只用來驗證重構沒有改變既有結果，不作為本次審查的主要切分方式。

## Review map

| ID | 審查面 | 主要輸出 | 狀態 |
|---|---|---|---|
| P1 | 產品邊界與演進模型 | public baseline、internal fork、research extension 的依賴規則 | **pass** — `evolution_strategy.md` 定義三條產品路徑與回饋邊界 |
| P2 | software layers 與 function call tree | entry/adaptor/orchestrator/stage/utility/reporting 的 owner 與合法依賴 | **pass** — 178A 不再依賴 93A concrete implementation |
| P3 | Workbook 與設定映射門面 | Ad Hoc → project → runtime mapping、profile、validation、provenance、UX | **pass for 178A** — versioned execution profile 與 resolved provenance 已落地；93A 為獨立後續項目 |
| P4 | config/status dataclass trees | 分層、生命週期、可選欄位、重複欄位、過度分支與 serialization | **pass** — 178A-owned config/status tree、semantic text 與 lifecycle 文件一致 |
| P5 | stage extension framework | 新 CDR、equalizer、noise、MLSD 等 stage method 的加入流程 | **pass** — stage checklist、version ownership 與 call direction 已定義 |
| P6 | utility extension framework | S4P、grid、PSD、PMF 等底層方法的介面與不變量 | **pass** — utility checklist、explicit S2P/S4P representation 與 round-trip boundary 已建立 |
| P7 | execution/search/reporting | single run、search、resume、artifact、status-only reporting | **pass with queued presentation work** — full search/artifact 與 shared report orchestration 通過；`ARC-REPORT-001` 不改數值模型 |
| P8 | 文件與治理 | 文件 authority、同步規則、change classification、review/closure gate | **pass** — tracker、claim/run gates 與 workflow integrity gate 已建立 |
| P9 | public API、packaging 與 v1.0 release | 相容性、deprecation、範例、效能、公開 claim boundary | **architecture pass; release pending** — public claim boundary 已定義，G7/G9/G10/G11 尚未全數通過 |

## 既有演算法基線

下列證據用來阻擋架構調整造成數值回歸：

- Akinwale fixed case production golden；
- `sicopr_reference_v1` execution profile 的 resolved provenance；
- GitHub full search run 29 與其 final artifact verification；
- 178A branch behavior registry；
- stage-level tests 與 project regression suite。

如果審查發現演算法問題，應另行分類成 confirmed error 或 named parallel method，
依專案 change-contract 規則處理；不得在架構整理中順手改變數學模型。

## 初步文件盤點

目前已有 project structure、software layers、configuration architecture、call/config/
status trees、stage documents、branch registry、search runbook、validation evidence 與
v1.0 release gate。這些文件已覆蓋「現在如何運作」，但尚未完整覆蓋「未來如何安全
演進」。目前缺口是：

1. public baseline、internal product fork、research extension 之間的依賴與回饋規則；
2. experiment → named parallel method → optional default 的方法生命週期；
3. 新增 stage method 與 utility method 時必須遵循的 extension checklist；
4. public API 相容性、deprecation 與 config/status serialization versioning；
5. workbook mapping 的 error/warning/provenance UX 標準；
6. 架構變更必須同步 call/config/status tree 與 branch registry 的可檢查 gate。

上述共通規則由 `docs/architecture/evolution_strategy.md` 補上；本文件逐章記錄
178A 是否符合這些規則。

## 審查順序

依相依關係執行，而不是依 COM 數值資料流：

1. P1 確定三條產品路徑與共用核心邊界；
2. P2 確定 code ownership 和合法 call direction；
3. P3、P4 審查專案門面與資料結構；
4. P5、P6 驗證未來 study 是否能循框架加入；
5. P7、P8 確認執行證據與治理能封閉迴路；
6. P9 才判定 178A v1.0 是否可封版，之後才進入 93A。

P8 同時包含 Notion implementation notes review：依 stage 整理 spec 未描述的工程細節與
branch rationale，但 repository branch registry 與 code contract 仍是實作行為的權威來源。

## Review conclusion

178A 的 numerical production baseline、version ownership、extension seam、configuration
boundary、status lifecycle、search artifact 與 documentation authority 已具備可維護的
共同地基。後續可以開始 93A foundation 工作，不需要再以 93A concrete classes 作為
178A parent，也不得在 93A migration 中回復該依賴。

此 PASS 的範圍是 **178A architecture foundation**，不代表：

- v1.0 package/tag 已可發布；
- 93A current-schema production path 已有 golden；
- report presentation issue 已完成；
- 所有未來 research methods 已經實作。

剩餘事項均已移出本審查 boundary：`ARC-CROSS-001` 負責 93A golden，
`ARC-REPORT-001` 負責 plot presentation，release gate 負責 final regression、版本與 tag。

## P2 implementation record

`ARC-178A-001` removes root-class inheritance between 178A and 93A. The later
`ARC-178A-004A/B/C` commits move 178A config/status ownership and path construction
into `models/com_178a/`, then remove the remaining private-helper dependency on
`com_model_93A.py`. Both versions may use neutral utility/reporting contracts,
but neither version owns the other's concrete orchestration or semantic types.

The fixed-case before/after snapshot requires exact equality for all numerical
objects under `paths`, `run`, `dte`, `imp`, `pmf`, and `mlsd`. This architecture
change does not authorize an algorithm or result change.

Evidence commits: `cc5339e`, `4e21aca`, `313cf6b`, `13d1018`, `40470e8`.
