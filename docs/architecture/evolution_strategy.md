# 專案演進與擴充框架

## 目的

本文件定義 COM baseline 完成後，專案如何在不破壞可重現性的前提下，發展成
公司內部分析工具與研究平台。它約束新 stage、新 utility、新算法分支與設定介面
應放在哪一層，以及它們何時可成為正式方法。

## 三條產品路徑

### Public baseline

公開 repository 是唯一共用地基，提供 typed COM model、公開資料可重現案例、
穩定 API、validation evidence 與版本化 execution profile。

### Internal product fork

公司內部工具可以加入專有 channel/device data、circuit-specific adapter、設計空間、
報告與流程整合，但應透過 public baseline 的 typed interface 延伸。公開核心不得反向
依賴公司資料、私有命名或內部 workflow。

### Research extensions

研究路徑可以比較不同 CDR、equalizer、S4P、grid、PSD、PMF 或 noise 方法。每項研究
都保留 baseline 和 candidate，固定輸入、比較 boundary、metric、revision 與 artifact，
避免研究程式直接污染 production default。

```text
                       ┌─ internal product fork
public COM baseline ───┤
                       └─ research extensions
                                  │
                     generic, verified improvements
                                  └────→ public baseline
```

## 責任配置

| 問題 | 應負責的層 | 不應發生的事 |
|---|---|---|
| Excel 名稱、legacy alias、欄位錯誤訊息 | workbook adapter | core model 讀取 worksheet 細節 |
| Ad Hoc → project mapping | versioned adapter/converter | solver 猜測來源語意 |
| project → effective runtime/profile expansion | adapter profile resolver | 各 stage 判斷 `align_to_ref` |
| stage 算法選擇 | stage-owned named strategy/policy | workbook 暴露每個 helper 開關 |
| utility 數值行為 | utility-owned method 與 invariants | workflow 複製 utility 內部公式 |
| stage 順序與 status 傳遞 | model orchestrator | reporting 重算模型量 |
| 呈現與輸出 | reporting/status exporter | report 改變模型狀態 |

工作簿只呈現使用者需要理解的意圖與 study 維度。底層 helper 即使有多種實作，
也不因此自動成為 workbook 欄位；reference 組合由 named execution profile 一次展開，
resolved config 則完整記錄真正使用的分支。

## 方法生命週期

```text
experiment
  → isolated comparison
  → named parallel method
  → registered typed config/profile
  → regression + method-specific validation
  → documented evidence and responsibility boundary
  → optional default change
```

- `experiment` 可以存在於暫存 script/notebook，不得改變 production default。
- `named parallel method` 必須有清楚的核心概念名稱，不能只叫 reference workaround。
- 進入正式 config 前，必須確認 owner、輸入輸出、不變量、failure behavior 與 evidence。
- default 變更是獨立決策；方法存在不代表應成為預設值。
- confirmed error 直接修正 baseline，並保留 regression evidence，不建立永久分支掩蓋錯誤。

## Stage extension checklist

新增或替換 stage 方法時，必須：

1. 指定 stage owner 與 top-level orchestrator call；
2. 使用既有 typed config/status interface，或先明確修改其 contract；
3. 說明 baseline 與 candidate 在哪個 boundary 分岔、在哪裡重新匯合；
4. 定義共同輸入、比較量、允許差異與 failure condition；
5. 更新 call tree、config tree、status tree、stage document 與 branch registry；
6. 提供 baseline non-regression 和 candidate-specific validation；
7. 若 workbook 需要控制，說明它是使用者意圖、profile，或 study dimension。

## Utility extension checklist

新增 S-parameter、grid、response、PSD、PMF 等 utility 方法時，必須：

1. 定義 object invariant、單位、domain、grid/reference impedance 與 ownership；
2. 說明操作是 constructor、轉換、filter/cascade，還是 representation change；
3. 對可逆操作提供 round-trip/closure test；
4. 對不可逆操作記錄資訊損失、overflow/truncation 與 warning/error policy；
5. 不把 COM-specific profile 名稱寫進 general utility；
6. 由 stage/policy 選擇方法，utility 只執行明確方法；
7. 更新 utility contract 與所有受影響的 stage 文件。

## Internal fork contract

- 公司資料、私有 adapter 與內部報告留在 private repository/package。
- 透過公開 typed interface、named strategy 與 plugin/adaptor seam 接入。
- 可泛化的修正先去除私有依賴，以公開測試與證據回饋 public baseline。
- private fork 應能定期 rebase/merge public baseline，不複製並改寫核心 solver。
- 公開 repository 不保存私有資料、內部效能 claim 或無法公開驗證的 golden。

## Research study contract

每個 study 至少記錄：

- baseline method 與 candidate method；
- 分岔與重新匯合 boundary；
- 固定的 input/config/revision；
- primary metric 與 supporting diagnostics；
- 必須保持的不變量和允許改變的量；
- artifact 路徑與重現命令；
- 結果分類：error fix、parallel method、rejected experiment 或 default candidate。

如此可讓高層 CDR study 與底層 S4P/PMF study 共用同一個驗證框架，同時維持
production COM baseline 的穩定性。

## 文件同步 gate

架構變更若影響 stage boundary、semantic call、config/status dataclass、workbook mapping、
算法分支或 reporting dependency，必須在同一變更更新對應的 authoritative documents。
若文件未更新，該變更不得標記完成。後續應以自動檢查補強這項規則；在自動檢查
建立前，由 review checklist 強制執行。

## Workflow integrity gate

同一時間只執行一個 approved/implemented responsibility boundary。討論中新提出的
想法必須被分類為：併入現有 boundary、修訂並重新核准，或排入下一項；它不會因為
對話移轉而自動取代目前工作。切換前必須列出 active item、剩餘 closure steps、
新想法的排程位置與恢復條件。

實作項目只有在 scoped implementation、validation、required documentation、tracker
reconciliation 與 isolated commit 完成後才能關閉；當 workflow 包含 GitHub 同步時，
也必須先 push。若使用者明確暫停／取消，或實際 blocker 阻止工作，則先記錄原因、
現有 evidence 與恢復 gate，再切換題目。

## Repository 文件與實作筆記的分工

- IEEE/OIF specification notes 保存 normative 定義、版本與公式來源。
- Repository 文件保存目前 code contract、branch registry、責任邊界、測試與 release evidence，
  是判定程式行為的權威來源。
- Notion 實作筆記解釋 spec 未規定的工程選擇、reference behavior、數值後果、設計理由與
  心智模型，方便日後 study；它不得取代 repository contract。
- 每個 Notion 分支說明必須連回 owning stage、runtime policy 名稱、project default、reference
  profile 與驗證證據，並明確標示 Spec-defined、Implementation evidence、Engineering inference
  或 Open question。
- 收尾審查發現 Notion 與 code 不一致時，先以已驗證的 repository contract 為準，修正筆記並
  記錄適用版本；若 repository 本身缺乏證據，則保留為 open question，不以現有 code 反推 spec。
