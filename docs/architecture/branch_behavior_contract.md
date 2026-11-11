# Branch behavior contract

## Purpose

本契約定義什麼行為有資格成為 branch，以及所有 branch 必須遵守的共同規則。
它回答的是「這個可設定行為是否構成 branch、由誰負責、需要留下哪些證據」，
而不是重複 Project Config 或 runtime config 的完整資料分類。

本契約只建立分類、ownership、紀錄與驗證義務；它不核准新方法、不修改模型
公式，也不因某個欄位可設定就使它自動成為 branch。

## Definition and eligibility

**Branch behavior** 是同一類有效 physical input、同一 semantic operation 下，
兩種以上具名且受支援的 computational realizations 之間的選擇。選項必須改變
計算方法、數值語義或搜尋方法，而不是只改變輸入值、執行範圍、候選集合、
精度預算或輸出保存方式。

一個候選只有同時滿足下列條件，才可列為 branch：

1. 有兩種以上語義清楚、可被選擇且受支援的 realization；
2. 選項代表不同方法或 numerical semantics，而不只是不同資料值；
3. selector 會進入 production execution path，且有明確 consumer；
4. 能指出最低的 semantic owner boundary，以及實際 decision/execution point；
5. 能定義 legal values、project default、profile override、impact boundary 與
   preserved invariants；
6. 能以 isolation test、focused regression 或等價證據驗證各選項。

規範可能只定義其中一個 baseline，另一個選項則是專案保留的 research 或
reference realization。這種 branch 是 project-owned；除非規範確實要求選擇，
不得把它描述成 specification-owned choice。

## Relationship to configuration domains

Configuration Architecture 負責 runtime configuration 的資料分類；本契約只對
其中真正符合 eligibility 的 selectable behavior 建立 branch identity。Physical
fields 是完整 model input/configuration 的一部分，branch 只是其中可選方法的子集合；
runtime container 與 branch category 不是同一套分類。

| Runtime domain | Runtime responsibility | Branch relationship |
|---|---|---|
| physical fields | system、topology、physical condition、case data | 不是 branch；描述被計算的對象。 |
| `cfg.src` / `block_source` | artifact identity、format、units、representation 與 binding | 不是 branch；source selection 與 input dispatch 由來源契約負責。 |
| `cfg.alg` / `algorithm_policy` | named mathematical or computational policy | branch 的主要候選；仍須逐項通過 eligibility。 |
| `cfg.num` / `numerical_control` | resolution、convergence、truncation、precision、cost | 只有不同值代表受支援的 numerical realization 時才是 branch；純 tolerance、resolution 或 resource limit 只是 control。 |
| `cfg.srch` / `search` | candidate axes、coverage、strategy、retention、orchestration | 只有選擇不同搜尋方法時才是 branch；候選值、coverage、top-K、error policy 與 scheduling 本身不是 branch。 |
| `cfg.exe` / `execution` | run extent、target、scheduling、stage gate | 不是 branch；只控制哪些 stage 執行，不改變已執行 stage 的方法。 |

因此 `SRC`、`ALG`、`NUM`、`SRCH`、`EXE` 是 runtime config domains，不是五種
branch classes。Branch Registry 的 prefix 只標示通過 eligibility 後的 semantic
choice 所屬領域；不得從 container 名稱反推它必然是 branch。

`intrinsic` 是 Project Config parameter class，不是 runtime wrapper；derived value
仍留在 physical dataclass、runtime owner 或 status。Provenance 只記錄 effective
setting 的來源，不得選擇 numerical flow。

## Explicit exclusions and boundary cases

| Item | Classification |
|---|---|
| Physical/case value | 輸入，不是方法選擇。 |
| Source/artifact binding or representation dispatch | Input/source contract；成功與失敗不得形成隱藏 fallback branch。 |
| Input presence, malformed-input handling, bounds check | Guard 或 input boundary；不是 branch。 |
| Branch parameter | 只服務某個已核准 branch，沒有獨立 branch identity。 |
| Search candidate value、coverage、retention、orchestration | Search configuration；除非它本身選擇不同 search algorithm。 |
| Execution target 或 stage gate | Execution control；不是 branch。 |
| Fixed implementation behavior | 只有一個受支援方法；不是 branch。 |
| Provenance、status、report/output control | 記錄或呈現資料；不得決定 model flow。 |
| Structural fan-out、guard、error handling、ordinary object construction | 即使形成 control flow，也不是 method branch。 |

Input fact 與處理方法必須分開分類。例如「輸入缺少 DC sample」是 input
condition；`error`、`hold`、`skrf`、`mag_phase_trend_to_dc` 則是對同一 condition
採取的不同 completion methods，因此 `missing_dc_policy` 可被核准為 ALG branch。

## Required structure and ownership

Branch owner 是不可避免必須知道「選中了哪個 behavior」的最低概念層，不是
selector 所在的 config dataclass，也不固定為 L3。Ownership 使用 COM semantic
coding-layer tree 判定，而不是 Python call depth：

```text
COM model
└─ L0 stage set
   └─ L1 stage
      └─ L2 function set
         └─ L3 functional block
            └─ L4 model auxiliary function
               └─ L5 generic utility / numerical kernel
```

每個核准 branch 必須符合以下 ownership 契約：

1. 一個 semantic operation 只有一個 semantic owner；
2. selector 在 owner boundary 解析；只有直接呼叫 owning operation 的 caller
   注入 resolved choice；
3. forwarding-only selector/config arguments 應移除；
4. helper 只接收需要的 concrete operation argument，不接收整個 policy/config；
5. generic utility 不依賴 model config、COM stage 或 mutable global policy；
6. 多個 consumers 必須收斂到同一 owner，而不是各自複製 ownership；
7. fixed behavior、input dispatch 與 retired non-branch 不參加 branch-owner review。

Owner 可以位於 L0--L5 任一層；execution point 也不預設固定比 owner 低一層。
Registry 必須同時記錄 semantic owner、concrete decision/execution function、直接
callers 與所有 in-scope production consumers。

## Required registry record

Branch Behavior Contract 只定義必填欄位；各版本現存 branch 的實際內容由該版本
Branch Registry 負責。每個核准 branch 至少記錄：

1. branch ID、名稱與 semantic operation；
2. options、legal values、project default 與 profile/preset behavior；
3. selector path，以及 conditional branch parameters；
4. owner layer、owner block/function 與 direct execution points；
5. direct callers、所有 consumers 與明確 non-owners；
6. intended impact boundary、quantities allowed to change 與 preserved invariants；
7. verified implementation coverage、exclusions 與 validation evidence；
8. review status、pending decision 或下一個 validation gate。

Declared impact 與 verified coverage 必須分開記錄。只有設定欄位或候選實作，
但尚未定位 production consumer，不構成已驗證 coverage。

## Review outcomes and lifecycle

既有候選必須得到下列其中一種結果：

| Outcome | Meaning |
|---|---|
| Approved branch behavior | 保留或新增 selector，完成 ownership 與 registry record。 |
| Branch parameter | 附屬於已核准 branch，不取得獨立 ID。 |
| Non-branch runtime control | 留在其 config domain，由該 workflow 記錄，不參加 branch-owner review。 |
| Case/input/source boundary | 由 case、source 或 input contract 記錄。 |
| Fixed behavior | 移除 selector 語言，記錄唯一受支援的 model/utility contract。 |
| Provenance | 只儲存或輸出來源，不得控制 numerical flow。 |
| Pending evidence | 明確記錄缺少的 evidence 與下一個 decision gate。 |

Review 依 stage 推進，但 owner 可以是跨 stage shared operation 或 L5 utility。
每個決定必須同步更新契約、registry、必要的 implementation 與適用驗證；純文件
reclassification 不要求重跑未改變的 production baseline。

```text
1. 盤點 selectable candidates 與 production consumers。
2. 依 eligibility 決定 branch、parameter、non-branch、fixed 或 pending。
3. 對 branch 定位最低 semantic owner 與 concrete decision point。
4. 必要時收斂 selector propagation，並更新 focused validation。
5. 同步 registry、stage/call-tree documentation 與 current state。
6. 完成後才進入下一個 branch ownership review。
```

## Document ownership

| Document | Authoritative responsibility |
|---|---|
| Configuration Architecture | Project/runtime config domains、資料結構與欄位放置。 |
| Branch Behavior Contract | branch definition、eligibility、exclusions、ownership 與 validation obligations。 |
| Version Branch Registry | **唯一**保存分支分類總表與 branch ownership/function-position tree；同時保存現存 branch、owner、consumer、impact、status、evidence 與 legacy mapping。 |
| Stage/call-tree documents | 保存 stage I/O、一般 execution flow 與 material functions；可標註 branch ID 並連回 Registry，但不得重複保存 branch 分類、owner 結論、review status 或 closure evidence。 |
| Active state/handoff | 目前 review 順序、stop point、blocker 與下一步；不重複 branch contract。 |

Config domain 回答「設定放在哪裡」；Branch Behavior Contract 回答「這個可設定
行為是否構成 branch，以及由誰負責」。任何新 method choice 都必須先通過本契約，
才可暴露於 public config、workbook 或 preset；普通 case parameter 不得只因會改變
結果就被提升為 branch。

## Review update and closure gate

Branch review 的文件更新不是結案後補做，而是 review 本身的一部分。每個項目
在狀態前進時都必須更新同一份 Version Branch Registry：

| Review state | Registry obligation | Commit obligation |
|---|---|---|
| `Review complete / decision pending` | 更新分類候選、proposed owner、未決 evidence 與下一 gate。 | 不要求 commit；不得標記 `Closed`。 |
| `Implemented / validation passed` | 更新正式分類表、ownership/function tree、consumer、impact、exclusion 與 validation evidence；同步真正受影響的 config/stage contract。 | 必須完成 scoped diff review，並明確決定 isolated commit 或使用者核准的 batch integration。 |
| `Closed` | Registry、必要技術文件、active state 與 handoff 均不得殘留舊結論。 | 必須已有可追溯 commit；若該工作要求 remote integration，還必須完成 push。 |

關閉前依序確認：

1. Registry 分類表是否已更新；
2. Registry ownership/function-position tree 是否已更新；
3. selector、owner、consumer、impact、exclusion 與 validation evidence 是否一致；
4. config tree、stage contract 或 pipeline call tree 是否真的因本次變更而需要更新；
5. active state 與 handoff 是否已移除舊 stop point；
6. `git diff` 是否只包含核准範圍，且既有使用者變更未被覆寫；
7. 是否已建立 isolated commit，或已有使用者明示核准的 batch commit 邊界。

即使是 documentation-only ownership relocation，只要 durable contract 有變更，
也需要 commit 才能標記 `Closed`。若使用者選擇稍後批次 commit，項目只能停在
`Implemented / validation passed — integration pending`。
