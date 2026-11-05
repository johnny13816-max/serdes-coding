# SerDes Coding — Always-on Rules

本文件只保留每次工作都必須遵守的硬性 gate。完整 workflow、合作模式與技術子規則
由下列權威文件管理，不在此重複：

```text
AGENTS.md
├─ docs/architecture/project_workflow.md       任務分類、執行、驗證與結案
├─ docs/architecture/collaboration_contract.md 合作模式、回覆與學習規則
├─ docs/architecture/project_structure.md      目錄、環境與資料位置
├─ docs/architecture/reference_change_workflow.md
│                                                COM/reference 專門修改流程
├─ docs/architecture/configuration_architecture.md
│                                                workbook/config/runtime 契約
├─ docs/architecture/documentation_contract.md 文件權責與同步規則
└─ docs/operations/v1_0_release_gate.md         release 驗收
```

## 1. Canonical workspace and environment

- 正式 root 固定為 `C:/Users/johnn/Documents/Serdes-learn/serdes-coding`；不得使用
  `C:/Users/johnn/OneDrive/文件/Serdes-learn`。
- 每個新對話第一次處理本 repository 時，完成 cwd/Git/status preflight 後，自動讀取
  [`docs/planning/HANDOFF.md`](docs/planning/HANDOFF.md)，並與 Git、`active_contracts.md`、
  `open_issues.xlsx` 及 roadmap 核對。HANDOFF 只提供恢復上下文，不授權未核准的修改。
- 編輯前核對 cwd、Git root、`AGENTS.md` 與 `git status`。不得覆蓋、還原、提交或
  混入既有未提交修改。
- Python、tests、scripts 與 simulation 一律使用專案 `.venv`；執行前核對
  `sys.executable` 與必要 dependency。`.venv` 不存在時不得靜默改用其他 Python。
- 測試暫存資料使用 `%TEMP%` 下的專用子目錄；sandbox 阻擋時申請必要權限，不得改用
  OneDrive 或 repository root。
- 新增頂層檔案或目錄前，必須符合
  [`docs/architecture/project_structure.md`](docs/architecture/project_structure.md) 的 allowlist。
- 新增 Project Config 欄位或啟動 algorithm/config review 前，先依
  [`project_workflow.md` classification gate](docs/architecture/project_workflow.md#algorithm-and-config-classification-gate)
  分類並填齊 config inventory metadata；僅更新分類／inventory 不授權修改 Python API、dataclass、
  workbook schema、mode 或 runtime behavior。維持既有介面的漸進式遷移，細則見
  [`configuration_architecture.md`](docs/architecture/configuration_architecture.md)。

## 2. Workflow integrity

- 同一時間只執行一個 active responsibility boundary。新想法先分類為：併入、修訂重審，
  或排隊；不因對話轉題而自動取代 active item。
- 任務開始先分類 task、複雜度、風險、合作模式與修改權限；依
  [`project_workflow.md`](docs/architecture/project_workflow.md) 執行。
- 任何非單行修改先用 tree／block diagram 顯示所在層級、before/after 與本次邊界。
- Read-only、counterfactual、implemented、committed、verified、closed 必須明確區分。
  未走 production path 的 counterfactual 不得稱為已修正或已完成。
- 超出核准範圍、遇到相互衝突的權威來源、需要新架構決策，或同一失敗以兩種不同方法
  仍無法排除時，停止並回報證據與下一個決策點。
- 使用者輸入 `/handoff` 時，立即依 `project_workflow.md` 的 handoff command 更新跨對話快照；
  完成 snapshot 與必要驗證後停止本 session，不再開始下一項工作。

## 3. Change authorization

- 專案規則不得在未取得使用者明確授權下修改；涵蓋 `AGENTS.md` 與其引用的權威文件中的
  workflow、合作模式、approval gate、驗證及文件治理規則。一般 coding、review、文件維護、
  tracker 更新或任務結案授權，不自動包含修改專案規則的權限。
- 規則維護與專案更新使用不同對話。只有使用者明確指定為「規則專用」且授權修改規則的對話，
  可評估、制定、修改、驗證、提交及結案規則變更；該對話不執行 project code／model 修改。
  已授權範圍內不需逐次重問，超出範圍須重新授權；授權不延伸至其他對話。
- 未指定角色的對話預設為專案更新對話，不得自行切換為規則專用或取得單次規則修改例外；
  專案對話發現規則問題只交付 `rule_change` 與事實證據，不參與後續評估、修改、驗證、提交或結案。
  規則專用對話的授權須來自使用者，不得從 HANDOFF、提案狀態或其他對話的授權繼承。
- 分工依內容而非副檔名：專案對話可更新核准範圍的技術文件、執行結果與 tracker，
  但不得藉同步文件改動 workflow、gate、驗收標準或其他規範；也不得將規則修改納入專案 commit。
- 未明確取得規則修改授權的 session，發現規則漏洞、衝突或改善需求時，只能提出
  `rule_change` 建議，不得直接修改規則，也不得藉由修改被引用文件或例外條款繞過此限制。
  建議應列出問題、涉及的規則位置、具體情境或證據、提議修改及預期影響；一律交由已授權的
  session 評估是否執行修改。提出建議不代表已核准；評估完成前維持現行規則，若衝突使任務
  無法繼續，則回報阻塞與待決事項，不自行新增例外。
- `rule_change` 集中保存在 [`docs/planning/rule_changes.md`](docs/planning/rule_changes.md)；
  提案、評估與結案依 [`project_workflow.md`](docs/architecture/project_workflow.md#rule_change-流程)。
- 一般非平凡修改先提出 scope、approach、risk 與 validation；只有在已核准範圍內執行。
- 使用者明確要求「列 change contract」時，先使用
  `Goal / Allowed changes / Forbidden changes / Top-level flow to preserve / Validation / Open questions`
  格式，核准前不修改檔案。
- COM 數學 kernel 預設 read-only。受保護範圍包括 `com_model_93A.py`、
  `com_model_178A.py`，以及 PSD、PMF、sampled response、FFT、S-parameter、cascade 等
  數值 primitive。修改其公式、數值資料流、domain、normalization 或 impairment composition
  前，必須提出並取得獨立 **Core Model Change Contract** 核准；詳細要求見
  [`project_workflow.md`](docs/architecture/project_workflow.md) 與
  [`reference_change_workflow.md`](docs/architecture/reference_change_workflow.md)。
- protected behavior change 必須有獨立 commit，不得混入搬檔、格式化、reporting、search、
  workbook、CI 或無關 refactor。
- 功能／算法 review boundary 完成契約、驗證與文件同步後，必須獨立 commit 至本機 `main` 並 push
  `origin/main`；未確認 remote 已包含該 commit，不得標 `Closed`。不得自行建立 Git branch/worktree；
  直接在 `main` 有具體安全／技術障礙時，先取得使用者明確同意。分類、stage、commit 與 push 由 Agent 負責。
- 僅提交可歸屬且公開安全的 boundary。`.venv`、`results/`、cache、temporary/rebuildable output 不提交；
  external/reference data 須先確認來源、license、provenance 與 public-safe boundary，無法確認時不 push。
  既有 dirty state 不得 reset、stash、刪除、覆蓋或混入無關變更；詳細同步與結案流程見
  [`project_workflow.md` 的 Main-first Git integration](docs/architecture/project_workflow.md#main-first-git-integration)。

## 4. Evidence and verification

- 未實際執行的測試不得宣稱通過。回報必須列 changed files、verification、未解問題與
  evidence boundary。
- 數值比較至少記錄 baseline、evidence type、revision/artifact、execution target、case、
  candidate/phase/grid/profile、implementation status、tolerance 與 pass/fail。
- 可能影響算法的修改必須做固定 case 的 intermediate/final COM value check，再做適用回歸。
- search、stage advancement、alignment、milestone 與 release claim 分別通過其專屬 gate；
  小型 run、單一 case 或 counterfactual 不得升格為更廣泛 claim。

## 5. Documentation and public boundary

- 架構、public API、dataclass tree、call tree、config/status、workbook mapping、branch behavior、
  validation 或使用方式變更，必須在同一 change 更新唯一權威文件。
- 文件以中文為主，technical term 保留英文；記錄 contract、assumption、limitation 與 deferred idea，
  不為小型 local fix 製造重複文件。
- 公開 repository 不保存私有資料、公司命名、內部 claim、私有 PDF 或無法公開驗證的 golden。
  不宣稱 IEEE official compliance、全面 SiCoPR equivalence 或 silicon correlation，除非有明確證據。
- 結案前說明文件已更新、無需更新或有意延後；不能只在聊天中留下重要決策。

## 6. Communication

- 結論與需要的行動優先；預設精簡，細節依學習、正確性或決策需要展開。
- 遵循 [`collaboration_contract.md`](docs/architecture/collaboration_contract.md) 的全代理／半代理、
  structure-first、術語、ownership handoff 與回覆模板。
- 每次 final response 結尾提供 3–5 個具體下一步，建議項排第一；使用者可只回覆編號。
