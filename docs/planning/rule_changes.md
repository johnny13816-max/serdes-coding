# rule_change 提案與決策

本文件只保存規則提案與處理結果，不授權修改規則，也不取代現行規則。
流程與狀態定義見 [project_workflow.md](../architecture/project_workflow.md#rule_change-流程)。

## RC-20261029-001 — 技術文件同步結案檢查

- 日期／狀態：2026-10-29／Closed。
- 問題／位置：documentation_contract.md 的 Update rule 與 project_workflow.md 的 Git and closure；
  既有同步規則缺少一般技術文件用途、結案前明確核對及無需更新的理由紀錄。
- 情境／證據：使用者要求每次修改 close 前確認相關專案技術文件已同步，並核准本對話提出的文字。
- 建議／影響：以唯一技術文件 owner 同步為 closure gate，不強迫新增文件，不授權修改治理規則。
- 評估者／授權依據：本規則專用對話；使用者已授權規則維護並選擇依建議文字加入。
- 決策理由：接受；讓文件同步是否完成有明確結案證據。
- 修改範圍：documentation_contract.md、project_workflow.md、本紀錄及 active_contracts.md 的獨立規則狀態。
- 驗證：diff whitespace、本地連結及新增 heading anchor 核對通過；人工確認需同步者未同步不得
  Closed、無需更新者須記理由、無須每次新增文件且不改變治理授權。不執行 project code 或數值測試。
- Commit evidence：`4f5f5156d95e7f847c52799dcc3f39297dd69af1`；後續 closure commit 記錄結案。
  本項暫存 active 段落已移除；active_contracts.md 的其餘既有專案修改與 HANDOFF 保持原狀且不納入提交。

## RC-20261028-006 — 規則與專案對話分工

- 日期／狀態：2026-10-28／Closed。
- 問題／位置：AGENTS.md 原允許單次規則修改授權，未要求規則與專案更新分屬不同對話。
- 情境／證據：使用者明確要求只有規則專用對話參與規則更新，專案對話不參與。
- 建議／影響：規則專用對話處理評估至結案；專案對話僅提案與交付事實證據，繼續依現行規則工作。
- 評估者／授權依據：本對話；使用者已明確指定規則維護角色、授權修改規則，並要求此次分工。
- 決策理由：接受；避免專案實作自行更動其約束或把規則修改混入專案 commit。
- 修改範圍：AGENTS.md、project_workflow.md、active_contracts.md、HANDOFF.md 與本紀錄。
- 驗證：diff 與本地連結檢查通過；heading anchor 已核對。人工情境檢查確認專案對話可提案、
  不能評估或提交規則；新對話不能繼承授權；技術文件更新不等於規範修改；本對話只維護規則。
- Commit evidence：`b6dee0fc9de13e6544476dcd0a4780e67a062cbb`；後續 closure commit 收斂交接狀態。
  RC-004 維持 Proposed，不阻擋專案對話，也不由專案對話接手。

## RC-20261028-005 — 讀取截斷補讀要求

- 日期／狀態：2026-10-28／Closed。
- 問題／規則位置：collaboration_contract.md 的 Token-first 只要求 targeted read，未定義截斷後的完整性責任。
- 情境／證據：工具輸出可能因 token budget 截斷；讀取命令成功不等於已取得所有必要內容。
- 建議／影響：截斷時分段補讀並核對任務所需範圍；保留彈性讀取量，無法補齊時揭露限制。
- 評估者／授權依據：本規則維護 session；使用者已授權規則維護，並選擇補充截斷補讀要求。
- 決策理由：接受；避免以不完整輸入作完整審查 claim，不設定固定行數上限。
- 修改範圍：collaboration_contract.md、active_contracts.md、HANDOFF.md 與本紀錄。
- 驗證：diff 與本地連結檢查通過，新增 heading anchor 與標題核對；人工情境檢查確認截斷須補讀、
  非相關內容不強制全讀、無法補齊須揭露限制，且不設固定行數上限。
- Commit evidence：`a1f592c1527cb1c39c700fe26cfd3708a7f112fc`；active state 與 HANDOFF 於後續 closure commit 收斂。
- 下一個關卡：無；其餘提案等待評估，不自動啟動。

## RC-20261028-001 — 建立規則提案流程

- 日期：2026-10-28
- 狀態：Closed。
- 問題：未授權 session 能提出 rule_change，但缺少集中保存、評估與結案流程。
- 規則位置：AGENTS.md 的 Change authorization；project_workflow.md 的 Cross-session loop。
- 情境／證據：本對話 rule integrity review 發現提案跨 session 可能遺失、評估權限不明。
- 建議／影響：建立集中清單與權限分工；project task 可登記提案，規則維護由已授權 session 處理。
- 評估者／授權依據：本規則維護 session；使用者明確授權本對話修改規則，並選擇建立此流程。
- 決策理由：接受；使提案有可追蹤紀錄，並保留規則修改 gate。
- 修改範圍：AGENTS.md、project_workflow.md、planning/README.md、active_contracts.md 與本文件。
- 驗證：diff whitespace、本地檔案連結檢查通過；人工情境檢查確認未授權者僅能提案、Accepted
  不轉移 session 授權、未 commit 不得 Closed；新增 heading anchors 已與標題核對。
- Commit evidence：`d02cee394df010ea253d0b7f7979a3e22a44555b`；active state 與 HANDOFF 於後續 closure commit 收斂。
- 下一個關卡：無；其他提案各自等待評估，不自動啟動。

## RC-20261028-002 — NOTES 維護權限

- 日期／狀態：2026-10-28／Closed。
- 問題／位置：NOTES.md 要求修改前取得同意；project_workflow.md 的 closure slimming 要求結案時移除內容。
- 情境／證據：一般 project session 結案可能同時遇到兩項不同要求。
- 建議／影響：區分候選內容變更與已升格、重複內容清理，明確指定權限。
- 評估者／授權依據：本規則維護 session；使用者已授權規則維護，並同意定義可自行清理的精確範圍。
- 決策理由：接受；允許有可核對證據的機械性清理，保留內容判斷與正式規則變更的 gate。
- 修改範圍：NOTES.md Maintenance、project_workflow.md closure slimming、active_contracts.md 與本紀錄。
- 驗證：人工情境檢查通過：有升格證據且無剩餘問題可清理；完全重複可刪副本；部分重複、
  失效判斷或證據不足須保留並取得同意；正式規則仍受授權 gate 約束。diff 與本地連結檢查通過。
- Commit evidence：`2a841b8f9a6806ab97230b79cf915cf8b4922d58`；active state 與 HANDOFF 於後續 closure commit 收斂。

## RC-20261028-003 — Artifact 輸出位置

- 日期／狀態：2026-10-28／Closed。
- 問題／位置：project_structure.md 的 case output、下載 artifact 的 results/ 與頂層 allowlist 定義不一致。
- 情境／證據：下載 artifact 解壓指令可能被解讀為新增未允許的頂層 results/。
- 建議／影響：明確指定 artifact 保存位置與 lifecycle，避免各 session 自行選擇。
- 評估者／授權依據：本規則維護 session；使用者授權規則維護並選擇評估 RC-003。
- 決策理由：接受；沿用 case/model results 的既有 ownership，區分本機保存與 CI 暫存。
- 修改範圍：project_structure.md、search_execution.md、active_contracts.md、HANDOFF.md 與本紀錄；
  不改 code、workflow、ignore pattern 或既有資料位置。
- 驗證：diff、本地連結與示例 case output 的 git check-ignore 檢查通過；已核對 heading anchors。
  既有 93A/178A workflows 使用 case results，partial validation workflow 使用 CI 暫存
  artifacts/partial_search，規則明列兩者；人工確認不同 attempt 隔離、未知 case 暫存與驗證失敗保留 ZIP。
- Commit evidence：`e7a7c4a0a02badf051b6c6dbc1a2036399a84213`；active state 與 HANDOFF 於後續 closure commit 收斂。

## RC-20261028-004 — Release evidence 時效

- 日期／狀態：2026-10-28／Proposed。
- 問題／位置：v1_0_release_gate.md 的 G3/G5 要求目前 candidate 通過，但狀態引用歷史驗證。
- 情境／證據：歷史 pass 容易被讀成目前 release candidate 已通過。
- 建議／影響：區分 historical evidence 與 current candidate acceptance；不改數值或重跑結果。
- 評估者／授權依據、決策理由、修改範圍、驗證、commit evidence：待評估；尚未核准或修改。
