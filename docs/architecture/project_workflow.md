# Project workflow

## 權責與目的

本文件是一般任務執行的權威 workflow。COM/reference gap 使用更專門的
[`reference_change_workflow.md`](reference_change_workflow.md)；protected kernel 仍受
`AGENTS.md` 的 approval gate 約束。

```text
User goal
└─ classify task / complexity / risk / collaboration mode
   └─ inspect and establish baseline
      └─ design or contract when needed
         └─ execute approved boundary
            └─ verify → document → commit → close
```

## 自動分類器

開始工作前，在內部判定以下欄位；只有模型切換、approval、active-item 衝突、protected model、
release 或使用者要求時才完整顯示，避免輸出浪費。

```text
Task type:
Read-only or modifying:
Complexity: low / medium / high
Risk: low / medium / high
Active-item impact:
Workflow:
Recommended model level:
Collaboration mode:
Approval gate:
Stop point:
```

風險與複雜度獨立。更強模型不能取代使用者核准、destructive-action approval 或 protected contract。

## 模型等級

| 等級 | 適用範圍 | 目前建議映射 |
|---|---|---|
| Fast | 狀態、文件、清楚的小型例行工作 | GPT-6 Luna low/medium |
| Standard | 一般 coding、code review、contract 執行 | GPT-6.1 Sol medium/high |
| Deep | 算法、架構、spec/reference、複雜 root cause | GPT-6.1 Sol xhigh 或 Astra high |
| Critical Review | release、重大架構與獨立複核 | Astra xhigh |

實際模型名稱可能改版；workflow 使用抽象等級，Agent runtime/skill 維護當期映射。優先使用能穩定達到
品質門檻的最輕模型。

下列情況至少升一級：protected equation/numerical flow、spec/reference 衝突、跨版本架構、
public API/workbook schema/serialization、兩個以上合理 root cause、證據互相矛盾、兩次差異化嘗試
仍失敗、release independent audit。檔案多、測試久或已核准的例行執行本身不構成升級理由。

## Task taxonomy

| 任務 | 固定 workflow | 等級 | 預設模式 | Stop point |
|---|---|---|---|---|
| 專案狀態 | Git → tracker → active item → evidence → 結論 | Fast | 全代理 | 狀態已判定或資料互相矛盾 |
| 程式結構 | 問題 → owner → call tree → dependency → finding | Standard | 全代理 | 回答問題；重構前停止 |
| Bug／數值 gap | baseline → reproduce → first mismatch → root cause → proposal | Deep | 追查全代理；核心修正半代理 | 第一個可操作原因；修改模型前停止 |
| 算法審查 | spec → equation → code → intermediate → reference → verdict | Deep | 審查全代理；新算法半代理 | 每式已判定；權威來源衝突時停止 |
| 架構／API | scenario → owner → responsibility → tree → alternatives → decision | Deep | 半代理 | 可 review 的設計完成；實作前停止 |
| Change Contract | evidence → boundary → files/functions → invariants → validation | Standard/Deep | Agent 起草；User 審核 | contract 完整，等待核准 |
| Contract 執行 | preflight → edit → focused test → regression → docs → commit | Standard/Deep | 已核准範圍全代理 | 完成或出現 scope expansion |
| 文件 | authority → owner doc → update → consistency check | Fast/Standard | 全代理 | 文件與實作一致；技術規則改變前停止 |
| 測試／驗證 | boundary → run → diagnose → evidence | Standard | 全代理 | acceptance 已判定或需要新修改 |
| Release | gate → clean candidate → regression → artifact → review → publish | Critical Review | 全代理至發布 gate | tag/publish/merge 前停止 |

## 一般執行流程

### 1. Preflight

1. 核對 canonical cwd、Git root、`AGENTS.md`、branch 與 `git status`。
2. 保護既有修改；辨認 active item、approved boundary、next gate。
3. 只讀取與任務相關的 authority、code 與 evidence。
4. 使用 task header；非平凡修改先給 scope tree／before-after tree。

### 2. Read-only work

Read-only 可以持續到明確結論，不因「可能需要修改」而只報 gap。找到問題時必須同時提出 owner、
修改層級、方案與驗證；若修改需要 approval，保存證據並停在 contract gate。

### 3. Non-trivial change brief

public API、architecture、config/status/workbook schema、超過兩個 ownership files、numerical behavior、
migration/compatibility 都屬 non-trivial。編輯前至少說明 scope、approach、risk、affected files 與 validation。
只有使用者明確要求 contract，或 protected/core 規則要求時，才啟用正式 contract approval protocol。

正式一般 contract 固定使用：

```text
Goal:
Allowed changes:
Forbidden changes:
Top-level flow to preserve:
Validation:
Open questions:
```

### 4. Core Model Change Contract

修改 protected behavior 前，契約必須逐項包含：

1. 修改原因；
2. governing specification equation、Ad Hoc reference 或其他已接受來源；
3. 現行 equation 與 data flow；
4. 提議 equation 與 data flow；
5. 精確 files/functions；
6. 預期改變的 intermediate quantities；
7. 必須保持不變的 intermediate quantities 與 behavior；
8. validation case、expected intermediates、numerical tolerances 與 final acceptance；
9. 93A、178A、single run 與 search run 影響；
10. rollback commit 或其他精確 rollback boundary。

核准只涵蓋列出的內容；新發現需修訂並重新核准。

### 5. Implementation

- 限定在批准範圍；dependency search/read 可批次並行，mutation、approval 與 dependent steps 依序執行。
- confirmed error 修正 baseline；合法 design diff 使用具核心概念的 named parallel method；experiment 不改 default。
- 不在高層直接修補低層結果。選擇策略的層、傳遞設定的層與執行數值操作的 owner 必須分清。
- 同一責任邊界同步 code、tests、authoritative docs 與 tracker。

### 6. Verification

依序做最小 invariant/focused test、fixed golden intermediate/final value、affected regression，必要時才做
small/full search。已通過的檢查不因形式而重跑；只有新變更、failure 或未解風險才擴大驗證。

### 7. Git and closure

- 每個可獨立 review/rollback 的責任邊界一個 commit；protected behavior 必須獨立 commit。
- 不提交無法安全歸屬的既有 dirty changes。需要 GitHub sync 的 workflow 在切換下一項前先 push。
- `Closed` 需要 implementation、focused/applicable regression、required docs、tracker reconciliation、
  isolated commit，以及工作流要求時的 push。討論、draft、counterfactual 或 passing test 都不是 closure。

## Active-item document lifecycle

每個 non-trivial modifying item 進入 active state 時，必須有一份暫存 contract；routine metadata/docs
maintenance 與純 read-only inquiry 可只在 `active_contracts.md` 記 boundary。暫存 contract 位於
`docs/planning/<ITEM_ID>_<short_name>.md`，並由 `active_contracts.md` 連結。它記錄問題、scope、
tree/call boundary、決策、驗證與尚未完成的 gate，不是正式技術權威。

```text
Open issue
→ Active item + temp contract
→ Implementation + validation
→ Durable knowledge promoted into authoritative technical documents
→ Boundary commit and evidence
→ Close open issue / reconcile active_contracts
→ Delete or archive the temp contract
→ Slim HANDOFF and NOTES
→ Closure commit when a separate status commit is needed
```

順序不可顛倒：authoritative technical documentation 必須在 issue 關閉前完成。若 closure evidence 需要
實際 commit SHA，先提交 code/tests/technical docs 的 boundary commit，再用小型 closure commit 更新 tracker、
temp-contract disposition、HANDOFF 與 NOTES。若不需要 post-commit SHA，一個 isolated commit 可同時完成兩階段。

Temp contract 的 durable 內容依 owner 分流：API/architecture 進 `docs/architecture/`；version/stage/equation
進 `docs/models/`；驗收方法與數值進 `docs/validation/`；執行方式進 `docs/operations/`。合併完成後：

- 一般 temporary plan 刪除，避免形成第二份權威來源；
- protected model contract、重要 ADR 或 reference decision 可保留為 historical evidence，但 header 必須標明
  `Historical / non-authoritative` 並連回目前 owner；
- open question 若仍有效，移到新 issue 或 `NOTES.md` candidate，不得靠保留整份 temp contract 逃避分類。

每次 closure 都執行 memory slimming：`HANDOFF.md` 移除已完成細節，只保留下一個 active context；
`NOTES.md` 依其 Maintenance 權限檢查候選，只直接執行符合條件的機械性清理；其他內容保留並提出
待決事項，不因 closure 要求繞過同意或規則修改 gate。兩者都不能累積歷史日誌。

## Workflow integrity and interruption

新想法依序處理：同 boundary 則併入；使 boundary 失效則修訂並重審；獨立想法則記入 tracker 並完成
active item。只有使用者明確 pause/cancel，或 blocker 使工作無法前進，才能切換；切換前記錄狀態、原因、
evidence、next owner 與 resumption gate。

## Failure handling

- 先診斷再 retry。相同原因／策略最多兩次 corrective attempt；第二次必須基於新證據改變方法。
- 新權限、destructive action、scope expansion 或新設計決策需要停止並取得核准。
- 停止時保留 recoverable state，說明已做、未做、失敗證據與最安全的下一步。

## Claim gates

`observed → isolated → classified → approved → implemented → golden-verified → regression-passed → committed → closed`

每個 claim 只涵蓋實際通過的 boundary。使用精確狀態，例如 `counterfactual matched`、
`implemented, awaiting golden validation`、`COM_DFE aligned`。alignment tolerance、release tolerance 與
causal-isolation tolerance 必須分開命名。

## Cross-session loop

```text
工作經驗
└─ candidate lesson → 使用者同意寫入 NOTES
   └─ 重複驗證 → 提議升格
      └─ 涉及專案規則時提出 rule_change → 已授權 session 評估與執行
         └─ 依 NOTES Maintenance 權限清理；需同意的內容先保留
```

[`../planning/HANDOFF.md`](../planning/HANDOFF.md) 只保存當前狀態，恢復工作時必須與 Git/tracker 重新核對；
[`../planning/NOTES.md`](../planning/NOTES.md) 只保存尚未升格的可重用經驗。Agent 不得自行演化永久規則。

## rule_change 流程

本節是規則提案流程的唯一權威；修改授權仍由 `AGENTS.md` 管理。
提案集中記在 [`../planning/rule_changes.md`](../planning/rule_changes.md)，不以 NOTES 或聊天取代。

```text
Proposed → Accepted → Implemented → Closed
         ├─ Deferred → Proposed（補齊證據或恢復條件後重審）
         └─ Rejected
```

- 任何 session 都可新增 `Proposed`，或為既有提案補充證據；這是提案記錄權，不是規則修改權。
  不需為登記提案另外取得規則修改授權，不自動中斷目前 project task。
- 每項使用唯一 `RC-YYYYMMDD-NNN` ID，記錄日期、問題、規則位置、情境／證據、建議、影響、
  狀態、評估者／授權依據、決策理由、修改範圍、驗證與 commit evidence；未知欄位明記待評估。
- 只有使用者明確指定且授權的規則專用 session，可寫入評估決策並將提案轉為 Accepted、Deferred
  或 Rejected，以及執行後續規則修改、驗證、提交與結案。專案更新 session 只交付提案／事實證據，
  不承接這些步驟，不以單次例外混合兩種對話角色。評估須檢查必要性、權威 owner、既有衝突及
  授權範圍；Accepted 不把授權轉給其他 session。
- Accepted 項目進入實作前，在 `active_contracts.md` 連結提案作為該規則維護項目的暫存 contract，
  記錄當前 boundary、next gate 與授權。仍遵守單一 active responsibility boundary；不得自動接管
  或修改另一 session 的 project task。既有 technical queue 保留。
- 僅在授權範圍修改唯一權威文件，並同步必要索引；完成修改標 Implemented。至少驗證 diff、
  Markdown 本地連結、規則交叉一致性及原問題情境，不以程式測試冒充規則驗證。
- Closed 須有決策理由、實際修改範圍、驗證結果、獨立 commit evidence 及 active state 收斂；
  尚未 commit 保持 Implemented。Deferred 記恢復條件，Rejected 記拒絕理由，兩者均不得執行修改。
- 提案不得成為新規則的權威來源。結案後只保留短版決策與 evidence，刪除重複草稿；不刪除 ID 或
  未解提案，不強制再登記至 `open_issues.xlsx` 或 NOTES，以免形成多份狀態來源。

## `/handoff` command

`/handoff` 是本專案定義的對話命令，不是用來取代 Git 或 tracker 的原生 Codex 指令。使用者輸入
`/handoff` 後，Agent 必須完成下列動作並停止本 session：

```text
/handoff
├─ verify cwd / Git root / branch / status
├─ reconcile roadmap / active_contracts / temp contract / current evidence
├─ write one compact HANDOFF snapshot
├─ record pre-existing or task-owned dirty state without modifying it
├─ run link/format check when governance docs changed
└─ report handoff complete; do not start another task
```

HANDOFF snapshot 固定包含：state、source branch/revision、active task、current phase、collaboration mode、
approved boundary、completed、in progress、blocked、next recommended action、next owner、stop point、evidence links
與 dirty-state summary。無內容的欄位寫 `none`，不得省略到讓新 session 猜測。

`/handoff` 不會自行授權 commit、push、stash、reset 或清除工作樹。若既有 workflow 已授權 closure commit，
HANDOFF 可包含在該 commit；否則保留為明確的 working-tree update，並在 snapshot 記錄。不得為了得到 clean
status 而混入、還原或移動其他人的修改。

### New-session auto-read

每個新對話第一次處理本 repository 時，在規劃或執行前自動：

1. 讀取 `AGENTS.md` 與 `HANDOFF.md`；
2. 核對 canonical cwd、Git root、branch、HEAD 與 dirty state；
3. 核對 `active_contracts.md`、相關 temp contract、`open_issues.xlsx` 與 roadmap；
4. 回報三項：可恢復的 active task、任何 stale/conflict、建議 next gate；
5. 只有在使用者的新要求與 handoff 一致且具備既有授權時才繼續執行，否則先依 workflow integrity 分類。

若 HANDOFF 與 Git/tracker 衝突，以 Git 和 authoritative tracker 為準，修正 HANDOFF 後再工作。讀取本身
不會將 snapshot 標為完成；task 切換或結案時以新的 snapshot 取代舊內容。
