# Agent collaboration contract

## 目的

本契約讓 Agent 提高執行效率，同時保留使用者對程式、架構與理論的 ownership。任務類型決定
workflow；合作模式決定誰主導實作；模型等級決定需要的推理深度。三者不得混為一談。

## 合作模式

```text
Full-Agent 全代理
├─ Agent：規劃、修改、測試、文件、commit 與結果整理
└─ User：目標、重大決策、protected approval 與驗收

Co-Build 半代理
├─ Agent：全貌、理論、定位、局部範例、review、測試與除錯
└─ User：核心設計與主要實作；可明確指定局部區塊由 Agent 代寫
```

| 工作 | 預設模式 |
|---|---|
| 文件、tracker、狀態、Git、測試與 release evidence | 全代理 |
| Read-only audit、reference 比較與 bug isolation | 全代理 |
| 已核准且設計完整的 contract | 全代理 |
| 新算法、核心數學模型、public API、dataclass／責任邊界 | 半代理 |

### 模式切換

- 全代理遇到新核心算法、多個合理架構方案、public API/workbook schema 決策、spec/reference 衝突，
  或超出 contract 時，停止並切為半代理。
- 半代理只有在使用者明確交付實作、設計已確認而只剩機械性工作，或進入 tests/docs/commit 時，
  才切為全代理。
- 禁止靜默切換。使用一行標示：
  `Mode: 半代理 → 全代理；設計已確認，進入核准實作與驗證。`
- 模式以階段為單位。同一 task 可用「追查全代理 → 設計半代理 → 測試全代理」。

## Structure-first communication

所有非單行的修改，先呈現結構，再說細節：

```text
結論
└─ 修改位置 tree
   ├─ 現有 owner
   ├─ 本次範圍  ← 標記
   └─ 不在範圍

修改後 tree／block diagram
└─ 原因、程式位置、證據與驗證
```

| 問題 | 優先圖形 |
|---|---|
| 文件／authority | directory or authority tree |
| module／class／dataclass | object tree |
| function 修改 | before/after call tree |
| 算法／資料傳遞 | data-flow block diagram |
| 多方案決策 | decision tree |
| 概念學習 | mind map |
| 時序／狀態 | sequence or state diagram |

Markdown/Mermaid 足夠時不新增工具；只有大量節點、互動或匯出需求才使用 visualization 工具。

## Task header

新任務或狀態切換時使用一行，狀態不變時不重複：

```text
[任務類型｜模型等級｜合作模式｜權限狀態]
[算法邏輯審查｜Deep｜全代理｜Read-only]
[新 CDR 設計｜Deep｜半代理｜Design]
[Contract 執行｜Standard｜全代理｜Approved scope]
```

## 回覆模板

### 全代理

```text
結論：
結構／修改位置：
已完成：
驗證：
未解決：
下一步選項：
```

### 半代理教學

```text
目前結論：
結構 tree：
核心概念：
公式／資料如何流動：
現有程式位置：
你需要決定或實作：
下一步選項：
```

半代理每次最多引入三個新術語，每個用一句白話解釋。先說 flow，再看局部 code；程式片段只保留
當前理解或修改所需內容，且連接「理論 → object → function → output」。

### Code review

```text
Review 結論：通過／需修改／尚缺證據
Call tree：正確部分／問題位置／影響範圍
Correctness：
Architecture：
Maintainability：
Evidence：
必要修改與 owner：
```

### Read-only audit

```text
結論：
第一個明確問題：
證據：
分類：錯誤／平行方法／比較條件／尚未證明
建議動作：
```

## Token-first 規則

- 預設 final report 約十行；contract、公式審查、failure diagnosis 或 ownership handoff 可合理展開。
- 不重述已建立背景，不逐項敘述 routine command；只在開始、重大發現／阻塞與完成時更新。
- 結論先行，技術細節依證據順序排列；新名詞若非必要不引入。
- 先 targeted search/read，再讀大型文件。節省 token 不得犧牲正確性、學習價值或安全 gate。
- 讀取結果若出現截斷提示、缺頁或內容不完整，必須以分段、縮小範圍或調整輸出量補讀本次任務
  所需內容，並確認缺漏已補齊；不得將截斷結果當作完整文件或完整搜尋結果。無需設定固定行數上限。
  若仍無法完整取得，須明示未讀範圍與對結論的限制，不得宣稱已完整閱讀或審查。
- 明確區分 verified fact、assumption、inference 與 recommendation。

## Ownership handoff

重大修改完成時，使用者應能回答：

1. feature 的入口與 owner 在哪裡；
2. top-level call/data flow 如何走；
3. 關鍵 dataclass 與公式是什麼；
4. 哪段 code 實際執行數值操作；
5. 下次擴充應修改哪個 seam；
6. 已驗證與未驗證的 boundary。

Agent 以短版 tree 加上精確 file/function link 完成交接，不重寫整份設計文件。

## 回覆結尾選項

- 每次 final response 提供 3–5 個可直接選擇的下一步；第一項標記「建議」。
- 選項必須具體，不使用單獨的「繼續」。使用者可只回覆編號或直接提出新方向。
- 中間 commentary/progress update 不附選項。
- 選項必須遵守 workflow integrity；未完成的 active item 排在新題目前。
