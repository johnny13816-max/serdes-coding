# Candidate reusable lessons

本文件只記錄尚未升格為正式規則、但可能跨任務重用的經驗。新增、改寫或升格候選內容前須先取得使用者同意；
不得用 NOTES 覆蓋 `AGENTS.md`、architecture、model、validation 或 operations 文件。

## Entry format

```text
ID:
Observation:
Evidence / repeated cases:
Candidate rule:
Scope:
Status: proposed / accepted-for-trial / promoted / rejected
Review date:
```

## Active candidates

目前無 active candidate。已確認的 workflow integrity、token-first、structure-first、全代理／半代理與
cross-session 規則已直接納入權威文件，不在此重複。

## Maintenance

- 每個 milestone 或至少每月檢查一次。
- 每個 active item 結案後立即檢查一次，不等待月度檢查；只有下列機械性清理可由一般 session
  直接執行，不需另取得規則修改授權或再次詢問：
  - 已升格：有明確的目前權威文件位置與已完成升格證據，且候選沒有剩餘未解內容。
  - 完全重複：刪除副本並保留一份內容完全相同的 canonical entry；不得合併改寫或丟失獨有證據。
- 執行機械性清理時，在該任務結案紀錄或 HANDOFF 記下被移除的 ID、理由與保留的權威位置／entry。
  證據不明或內容僅部分重複時，保留原文並提出待決事項。
- 因失效、無證據、技術判斷改變而移除，以及任何新增、實質改寫或升格，須先取得使用者同意；
  涉及正式專案規則變更時，另依 AGENTS.md 與 rule_change 流程，由已授權 session 評估及執行。
- 上述清理權只適用於本文件的候選內容，不授權修改本節維護規則或其他正式規則。
- 只有在多個任務中重複成立，且使用者 review 後，才升格為永久規則。
