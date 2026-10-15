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

| Gate | Acceptance condition | Current state (2026-10-15) |
|---|---|---|
| G1 Repository state | 所有納入 release 的 model/config changes 已分離提交；無未分類修改混入 | TC-024 已提交；execution-profile change 進行中 |
| G2 Configuration UX | 新 178A template 使用 versioned `execution_profile`；legacy input 有測試；resolved profile/provenance 可匯出 | 實作完成；待 regression／commit |
| G3 Fixed golden | Akinwale `sicopr_reference_v1`, `target=full` production path 在目前 commit 通過既有 intermediate/final tolerances | 通過：pos=5、MSE=`0.0061912610245255335`、COM_DFE=`1.5247607834259893 dB`、COM_MLSD=`2.895898684873246 dB` |
| G4 Local search | 縮小 candidate set 完成 prepare→partial→finalize→verify，final target 為 `full` | 通過：2 candidates、1 full final、53 PNG hashes；evidence `%TEMP%/serdes-v1-small-search/results` |
| G5 GitHub full search | 完整 232,848 candidates 在目前 release candidate commit 成功，artifact verify 通過 | 舊 commit/D FE-only run 成功；不計入本 gate |
| G6 178A reference result | Full-search best candidate 記錄 MSE、COM_DFE、ΔCOM、COM_MLSD，並說明與 reference 的比較邊界 | 待 G5 |
| G7 93A support boundary | 至少一個正式 93A case 通過 single/search smoke；文件明示 validation level 與未驗證範圍 | 待盤點 |
| G8 Output durability | Results 保存 resolved config、input hashes、revision、candidate coverage、status summary 與 plot manifest | local gate 通過；待 GitHub clean-revision artifact 複核 |
| G9 Documentation | README、architecture、178A stage/branch docs、operations 與 public claim boundary 對齊程式 | 進行中 |
| G10 Regression | 完整 test suite 在 release candidate commit 通過；GUI/Tcl exclusion 若存在須具名記錄 | working tree 通過：136 passed、2 subtests passed；待 commit 後確認 CI |
| G11 Package/release | `pyproject.toml` 版本、release notes、tag 與 GitHub main 指向同一 verified commit | 待所有 gate 通過 |

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
