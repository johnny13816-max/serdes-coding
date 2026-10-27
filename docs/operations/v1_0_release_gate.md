# v1.0 release gate

狀態：**authoritative release acceptance contract**
目標：建立第一版可重現、可研究、可擴充的 COM model platform。v1.0 是
平台範圍宣告，不是 IEEE compliance、官方 SiCoPR equivalence 或實體 IC
correlation 宣告。

## Release scope

v1.0 必須同時涵蓋：

- 93A 與 178A 的 typed configuration、single run、search orchestration 及 reporting；
- 178A 從 measured channel、package、equalization、impairments、MMSE、DFE 到
  MLSD 的完整 production path；
- versioned workbook execution profiles，可重現 project-standard 與指定
  reference calibration；
- file-backed local／GitHub Actions search lifecycle；
- 可追溯的 config snapshot、input fingerprints、code revision、result status 與 plots；
- stage-first model 文件、branch registry、configuration/status/call trees；
- protected-kernel change、evidence、claim 與 release rules。

## Required gates

| Gate | Acceptance condition | Current state (2026-10-27) |
|---|---|---|
| G1 Repository state | 所有納入 release 的 model/config changes 已分離提交；無未分類修改混入 | release-scope code 已分離提交至 `94e5613`；本次收斂 governance/design-review 文件。canonical worktree 仍有不屬於本項的 reference-data/results 修改，因此尚未切 release candidate |
| G2 Configuration UX | 新 178A template 使用 versioned `execution_profile`；legacy input 有測試；resolved profile/provenance 可匯出 | 通過：`945dd2b` |
| G3 Fixed golden | Akinwale `sicopr_reference_v1`, `target=full` production path 在目前 commit 通過既有 intermediate/final tolerances | 通過：pos=5、MSE=`0.0061912610245255335`、COM_DFE=`1.5247607834259893 dB`、COM_MLSD=`2.895898684873246 dB` |
| G4 Local search | 縮小 candidate set 完成 prepare→partial→finalize→verify，final target 為 `full` | 通過：2 candidates、1 full final、53 PNG hashes；evidence `%TEMP%/serdes-v1-small-search/results` |
| G5 GitHub full search | 完整 232,848 candidates 在目前 release candidate commit 成功，artifact verify 通過 | 通過：run `38745800222`，commit `95f7f067`，236/236 jobs；232,848 rows、top 10、530 PNG hashes 全部驗證通過 |
| G6 178A reference result | Full-search best candidate 記錄 MSE、COM_DFE、ΔCOM、COM_MLSD，並說明與 reference 的比較邊界 | 通過：best index 28969；sweep/final MSE=`0.006361523694460796`/`0.006204188571809303`，COM_DFE=`1.514414278762367 dB`，ΔCOM=`1.3488568555276164 dB`，COM_MLSD=`2.8632711342899833 dB`；固定 reference candidate 仍另行精確對齊 |
| G7 93A support boundary | 至少一個正式 93A case 通過 single/search smoke；文件明示 validation level 與未驗證範圍 | **未通過**：`ARC-CROSS-001` 尚需建立 current-schema 93A golden case；這是下一個 proposed contract |
| G8 Output durability | Results 保存 resolved config、input hashes、revision、candidate coverage、status summary 與 plot manifest | 通過：clean revision、7 input hashes、resolved-config hash、coverage、status、top-K 與 plot manifests 均由下載 artifact 複核 |
| G9 Documentation | README、architecture、178A stage/branch docs、operations 與 public claim boundary 對齊程式 | 178A architecture review 已通過；`ARC-REPORT-001` presentation review 與 93A validation boundary 尚未結案 |
| G10 Regression | 完整 test suite 在 release candidate commit 通過；GUI/Tcl exclusion 若存在須具名記錄 | governance working tree：184 passed、2 subtests passed，使用 `%TEMP%/serdes-gov-v1-002/pytest`；release-candidate commit/CI 仍待 G7/G9 完成後執行 |
| G11 Package/release | `pyproject.toml` 版本、release notes、tag 與 GitHub main 指向同一 verified commit | **未通過**：package 目前仍為 `0.1.0`，尚無 v1.0 release notes、verified tag 或對應 release commit |

## Search acceptance

完整 reference search 的固定邊界為：

```text
case: sicopr_akinwale_vendorx_22db/178A
execution_profile: sicopr_reference_v1
search_sweep.target: mse
search_final.target: full
candidate count: 232848
final ranking input: completed MSE sweep
final output: DFE and MLSD results for retained candidates
```

先以 `%TEMP%` 的專用目錄完成縮小 search。縮小 search 只證明 lifecycle 與
full-target integration；完整 candidate coverage 只能由 GitHub full search 證明。

## Release claim boundary

允許的公開描述：

- Python COM modeling platform with 93A/178A-oriented workflows；
- 178A Akinwale case calibrated against the named SiCoPR reference result；
- reproducible single-run and distributed search artifacts。

在取得更廣泛 case/spec 證據前，不宣稱：

- IEEE official compliance；
- 所有 channel／configuration 的 SiCoPR 等價；
- silicon correlation 或產品 sign-off 能力。

## 178A architecture review gate

`docs/models/178A/design_review.md` 在 2026-10-27 判定 178A architecture
foundation 為 PASS。判定包含 standalone version ownership、function/config/status
boundaries、workbook/profile mapping、stage/utility extension framework、search artifact、
reporting orchestration 與 governance rules。這項判定解除「先完成 178A review，再進入
93A foundation」的程序 blocker，但不會自動通過 G7、G9、G10 或 G11。
