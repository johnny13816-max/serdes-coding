# 178A 分支盤點：`align_to_ref` 的適用邊界

> 本文件保留 TC-019R 時期的盤點與決策歷史。現行分支定義、project default、stage 與責任邊界，以 authoritative [178A 分支行為登錄表](../models/178A/branch_behavior_registry.md) 為準。

狀態：2026-10-12 已依 TC-019R 完成責任邊界遷移。下表記錄 workbook preset 所展開的算法；boolean 只存在於 project adapter，runtime/model 使用各自具名方法。

## 目前 `align_to_ref` 實際控制的項目

| 項目 | `False` 現況 | `True` 現況 | 建議歸屬／理由 |
| --- | --- | --- | --- |
| `channel_renormalization_order` | 取獨立欄位；預設 `sdd_first` | 強制 `s4p_first` | **獨立 channel ingestion policy**。四埠含 common-mode 的處理方法有物理意義，不應因「非 SiCoPR mode」自動退回 Sdd-first；由輸入／方法選擇明示。 |
| `out_of_measured` | 取獨立欄位；預設 `cosine_decay` | 強制 `zero_padding` | **獨立量測邊界 policy**。測到 100 GHz 或 67 GHz 是輸入事實，超出量測的處理是 utility 方法；reference mode 不可暗中改變量測截止。 |
| `ctle_pulse_realization` | `continuous_tf` | `bilinear_iir` | **獨立 pulse-realization method**。後者固定包含 measured composite TF、reference grid、raw IFFT、`1e-3` 截尾、bilinear IIR 與 boxcar；不再拆細項控制。 |
| `rxffe_record_realization` | `linear_convolution` | `finite_record_circshift` | **獨立 post-FFE record policy**。前者保留 overflow guard；後者重現 reference 的有限記錄 shift-sum。 |
| MMSE noise grid | `analysis_grid`，由 `LinkConfig.sampled_nfft` 決定 | `fixed_ui`；Akinwale `noise_grid_num_ui=4096` | **獨立 noise PSD/correlation policy**。只控制 noise DFT record，不修改 channel／pulse analysis grid。來源 `num_ui_RXFF_noise` 由 converter 保留。 |
| pre-DTE clipping | 取獨立欄位；預設 D3 `P_qc/2`＋完整 jitter | 強制 MATLAB 4.17 `P_qc`＋RJ-only clipping；MMSE 保留完整 jitter | **可留在 reference algorithm preset**。這是已確認、僅為對照的公式差異；須保持與 final-stage 選擇在邏輯上可區分。 |
| final ADC quantization | 取獨立欄位；預設 D3 selected-phase delta＋全部 FFE taps | 強制 MATLAB 4.17 final-PMF clipping＋略過主 tap | **可留在 reference algorithm preset**。這是另一 stage 的公式差異，不能假定與 pre-DTE 是同一條公式。 |
| 離散 tap PMF 格點 | 線性質量分配 | 最近格點 | **可留在 reference numerical preset**；只適用離散幅度建構，不應改成 `Pmf1D` 全部操作共用的量化規則。 |
| Gaussian PMF | bin integral；固定 `gaussian_n_sigma` | grid sample；依 `DER_0` 決定支撐範圍 | **可留在 reference numerical preset**，但截尾誤差／支撐範圍應另做數值收斂驗證。 |
| uniform PMF／PMF scaling | bin integral／mass deposit | nearest centers／ordinate interpolation | **可留在 reference numerical preset**；方法由 PMF 建立者按來源選擇，generic utility 僅提供可重用操作。 |
| final PMF grid | `fine` | `dy_rel_As × As`，再依主 tap gain 換算 | **建議拆成明確的 final PMF grid/domain policy**。這是數值座標與精度，不是物理公式；reference preset 可選它，但不能讓 boolean 取代單位／domain 契約。 |
| `COMRunConfig` PMF 執行設定 | 保留 `pre_dte_pmf_method`、`pmf_grid_quality`、`pmf_keep_mass`、`pmf_dy_override` | 強制 `pmf_exact`、`fine`、`keep_mass=1`、`pmf_dy_override=None` | **保留為具名 run-level 控制**。這些是精度／速度／收斂設定；reference preset 為了可重現 golden comparison 明確覆蓋，且 export 記錄 raw／effective／profile，不能成為 model 內的隱藏分支。 |

`align_to_ref=False` **不是單一「spec 模式」**：它仍允許舊 workbook 個別 `out_of_measured`、renormalization 和 ADC convention 欄位，且 run policy 各自獨立。`True` 由 adapter 覆蓋成 reference 具名值；`COMConfig.to_export_dict()` 匯出 effective policy／execution、profile 名稱及 raw/effective override。

## 已存在但不應由 `align_to_ref` 控制

| 項目 | 歸屬 |
| --- | --- |
| S4P 檔案、port order、reference impedance、`sparam_frequency_limit_GHz` | **case 輸入與 provenance**。TC-021 已將 SiCoPR `flim` 建模為獨立輸入；Akinwale 原檔 100 GHz、case limit 67 GHz。`zero_padding` 從有效 67 GHz 邊界後生效。 |
| `missing_dc_policy` | channel/utility 的量測缺口 policy。 |
| `pmf_dy_override`、`pmf_keep_mass`、`pmf_grid_quality`、`pre_dte_pmf_method` | run-level 精度、近似／成本 policy；不同 single/search profile 可不同，應記錄有效值並做收斂。 |
| `floating_mode`、`pos_sweep_method`／stride | MMSE／sampling-phase 搜尋演算法或加速 policy；不是 reference 物理公式。 |
| `force_grid`、grid overflow guard | utility 的卷積輸出契約與 search 候選處置；TC-013 尚未結案。 |
| `SampledPSD.filtered_by()` 的 grid 檢查 | utility 一致性契約，無隱藏 regrid 分支。 |
| TX 時間原點、sinc／boxcar unit-pulse 表示 | 已驗證為比較座標與等價表示；**不建立算法分支**。 |
| MLSD reference realization | `COMPolicyConfig` 保留 `added_noise_pdf`、`sequence_termination`、`reported_der` 三個具名方法；`align_to_ref=True` 由 adapter 展開成 TC-023 reference 組合。Eq. 178A-49 sign 是直接修正，不是分支。 |

## TC-020R2 完成狀態

[TC-020](tc020_ctle_pulse_realization.md) 已依 TC-020R2 完成上述兩個具名
runtime methods；Excel adapter 的 reference preset 分別選 `bilinear_iir`
與 `finite_record_circshift`。`H_all` 仍保留 Eq. 178A-14 continuous VTF；model
不讀取 `align_to_ref` boolean。

## 2026-10-12 已實作邊界

`align_to_ref` 是 **project workbook → typed/runtime config 的具名 preset 展開開關**；各平行算法仍各有描述核心方法的名稱。`src/serdes_coding/io/com_excel_io_178A.py::_resolve_project_profile_178A()` 讀取開關、覆蓋 reference 對齊所需的具名選項與 execution profiles，然後建構已解析的 `COMConfig`。模型、PMF helper 和 S-parameter utility 只收到具名選項，不依 `align_to_ref` boolean 決定數值行為。

建議資料流：

```text
project config workbook: align_to_ref + 物理輸入 + 明示的獨立 policy
  → com_excel_io_178A: 解析 workbook、選 reference preset、產生 override 紀錄
  → COMConfig: 全部有效算法／數值選項都有具名值；不再於 model runtime 重選
  → search: 複製 resolved COMConfig，只更換候選 TXFFE／CTLE 值
  → model/utility: 依具名方法執行，不知道 preset boolean
```

Workbook 可只露出總開關和真正需要使用者控制的物理／量測設定；reference 專用 PMF 細節保存在 versioned adapter 的一張可審核 preset 對照表，而不是散在 `_build_path()`、PMF helper 和 solver 中。原有 workbook 細項若繼續作 legacy input，當開關為 True 時須明確記錄原值與被覆蓋的有效值；不可默默讓 workbook 和執行值矛盾。`to_export_dict()`／結果 manifest 需要列 effective named methods、effective run settings、preset 來源與輸入 S4P 的頻率邊界，便於重現。

**目前 preset 覆蓋範圍**：`s4p_first`、`zero_padding`、`bilinear_iir`、
`finite_record_circshift`、fixed-UI noise grid、pre-DTE clipping、final ADC quantization、各來源 PMF
建構方法由開關一次選到 SiCoPR 對應的**具名值**；這些方法仍可在 Python
runtime config 各自指定、測試及 A/B。為 golden 比對所需的
`pmf_exact/fine/keep_mass=1/derived dy` 列為 reference execution preset 的明示
覆蓋。67 GHz 截止是輸入資料邊界，boolean 不會把 100 GHz 原檔裁成 67 GHz。

直接由 Python 建立 `COMConfig` 時，可逐一指定同一組具名 runtime 方法；不依賴 Excel adapter 也應能取得完全相同的結果。這種直接使用不需要 workbook preset boolean。workbook 欄位名稱維持 `align_to_ref`，不改名。

preset 邊界由已核准的 [TC-019R](tc019r_reference_preset_resolution.md) 實作；
CTLE 與 post-FFE record methods 由 TC-020R2 接入同一 adapter 展開流程。

## 控制項精簡結論

- `ctle_pulse_realization` 與 `rxffe_record_realization` 均須保留。前者決定
  pre-CTLE measured response 到 CTLE output pulse 的完整 realization；後者
  決定已取得有限 impulse record 後，RX FFE 如何作用於該 record，責任不同。
- `channel_renormalization_order`、`out_of_measured`、兩個 ADC convention 與
  各來源 PMF method 均代表已驗證的獨立算法選擇；`align_to_ref` 只負責一次
  選定 reference 組合。
- `xtalk_pmf_accumulation` 目前型別只有唯一值 `pathwise_convolution`，沒有
  實際分支能力，是多餘的公開控制候選。它的移除屬 PMF config API 清理，
  不混入 TC-020R2；在另案遷移前仍保留既有欄位以免擴大本次變更。
- 不新增 `ctle_fd_to_td`、`ctle_impulse_source`、
  `ctle_input_truncation`、threshold、causality、unit-pulse 或 hidden
  stop-frequency flags；這些都是 `bilinear_iir` 的固定定義。
  TC-021 的 `sparam_frequency_limit_GHz` 是明示 case input，不是 CTLE 細節開關。
