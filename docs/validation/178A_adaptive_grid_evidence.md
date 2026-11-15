# 178A adaptive grid 驗證紀錄

狀態：**已實作並完成主要驗證；remote 整合待完成**｜更新至 2026-11-15

本紀錄只描述目前工作樹在指定 case 的結果；不得推廣為其他 case、IEEE
compliance 或全面 SiCoPR 等價。契約見
[adaptive grid change contract](../planning/178A_adaptive_grid_change_contract.md)。

## XT 最大能量 PSD window 修改（未結案）

NUM-003 truncated 對完整 XT response 先選 phase，再於 pre-DTE／MLSD PSD
owner 截取最大能量 window；其餘 noise 與 full 不變。針對性測試
`tests/test_adaptive_grid_downstream.py`、`tests/test_com_model_178A_mlsd_noise.py`
共 `13 passed`。固定 SiCoPR case `tests/test_com_model_178A_golden.py` 以原
容差執行，MSE 與 golden `0.0061912610245255335` 的絕對差為
`3.99391448e-8`，超過 `1e-14`：`1 failed`。未更動 golden 或容差；
固定 reference 對齊尚未通過。

使用者確認最大能量 window 為刻意採用的行為，此處不要求與 SiCoPR
一致；原 SiCoPR 對照數值保留為歷史證據，另以本專案新行為建立 golden，
不放寬既有容差，也不聲稱 reference 對齊。
固定案例單一因素 counterfactual：僅在記憶體中將 pre-DTE 與 MLSD 的 XT
window 從最大能量改回前段，其他工作樹與輸入不變。MSE 由
`0.006191300963670364` 回復至 `0.0061912610245255335`；DTE w、
`R_n` digest 皆回復原 golden，final COM 均為 `2.895898684873246 dB`。
此為指定 case 的差異歸因，不代表其他 case 都只有相同差異。
使用者同意以新行為建立 project golden；以原容差重跑
`tests/test_com_model_178A_golden.py` 為 `1 passed`。此測試使用 SiCoPR
case／profile 作輸入，但不宣稱 XT window 數值與 SiCoPR 一致。
同一 SiCoPR case、adaptive + `bilinear_fine_grid`、phase 28、4096 UI
的 production pre-DTE 路徑：五條 XT 選中 window 的能量占各自完整
selected-phase response 能量分別為 `0.9999209176`、`0.9999833225`、
`0.9970622029`、`0.9999899189`、`0.9999961835`；截取前仍使用完整
response 選 XT phase。這只證明此案例能量保留，不構成 COM 精確度保證。
相同 case 完整 `all_enabled` production run：phase `29`、MSE
`0.006189886671790953`、COM_DFE `1.5247607834259893 dB`、final COM
`2.895898684873246 dB`；與修改前 fine-grid 結果不同，非全面對齊聲明。
後續 adaptive-grid、CTLE、PSD、post-FFE 與 stage-status focused regression
合計 `73 passed`；policy suite 為 `36 passed`。後者首次在 sandbox 因
pytest 無法建立系統暫存目錄而有 7 個 setup errors，於可使用系統暫存
目錄的環境重跑後通過。

## `bilinear_fine_grid` 新路徑：時間原點與驗證

初版 focused tests `36 passed`，但實際 SiCoPR case
以 adaptive + `bilinear_fine_grid` 建立 NEXT path 時，effective range 為
`[10, 3400000)` samples，最後 sample 的 amplitude 為 peak 的 `0.01044`，
現有邊界檢查報 `next effective response cannot fit the fine record`。
這是由 measured pre-CTLE TF 在 fine grid 上 IFFT 後，未先調整時間原點、
以零 state 等長濾波的結果。僅為診斷，將 IIR 輸入以既有 `causalize_ir()`
選出的 `1698231` samples 作 circular shift，再執行相同 IIR／boxcar，
range 變為 `[1431016, 1792325)`，尾端 amplitude 為 peak 的 `2.65e-5`。
此 counterfactual 本身不代表已完成修正。後經使用者確認，在 IIR 前由
actual pre-CTLE IR 決定 shift，preset 套用同一 shift，XT 各自決定 shift；
已對齊 pulse 不再於 adaptive 裁切時重複套用。原 `bilinear_iir` reference
路徑未改動。新路徑 focused tests `37 passed`；同一 case、adaptive、
`all_enabled` 的 production run 完成：victim `4096 UI`、5 條 XT `32768 UI`、
phase `28`、MSE `0.005351752979756553`、COM_DFE `1.4014087983082355 dB`、
final COM `2.705531359394457 dB`。這些數值不宣稱與 reference 一致；
當時的 reference fixed golden 於新路徑與 normalization 完成後以原容差重跑：
`tests/test_com_model_178A_golden.py`，`1 passed`。
該結果早於 XT 最大能量 window 修改；目前 project golden 和 SiCoPR
差異以本文件上方的最新記錄為準。
同一 case 的 fixed + `bilinear_fine_grid`、`target=mse` run 完成：
六條 path 均 `10626 UI`，phase `3`，MSE `0.005353060408701168`；
該 run 不包含 DFE／MLSD，也不視為 reference-alignment 結果。

## 固定案例

Case：`cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx`；profile：
`sicopr_reference_v1`；`fb=106.25 GBd`、`per_ui=32`、bilinear CTLE。
執行時工作樹未提交；`relative_threshold=1e-3` 為暫定設定。

| 執行 | 結果 | 邊界 |
| --- | --- | --- |
| fixed-grid production golden | 現行工作樹、更新 workbook 與 XT window 修正後 `1 passed` | 既有 golden 及 tolerance 未變；執行 `tests/test_com_model_178A_golden.py`。 |
| adaptive，fine target 1 MHz，NUM-003 truncated 4096 UI | victim 4096 UI；5 條 XT 共同 16384 UI；selected phase 5；MSE `0.006191233030475246`；COM_DFE `1.5247607834259893 dB`；final COM `2.895898684873246 dB` | 固定 golden MSE 為 `0.0061912610245255335`；兩個 COM 數值在本次輸出與 golden 相同。不視為 intermediate 全數相同，也不宣稱其他 case 對齊。 |
| adaptive，continuous CTLE，fine target 1 MHz，NUM-003 truncated 4096 UI | victim 4096 UI；5 條 XT 共同 32768 UI；selected phase 27；MSE `0.005352330545243842`；COM_DFE `1.350524706456924 dB`；final COM `2.6844957149167974 dB` | XT 整數 UI 修正後 `all_enabled` production path 成功執行；為非 reference CTLE 的結果，不視為 SiCoPR 數值比較。 |

2026-11-14 修正 XT window 起點／終點必須落在整數 UI 後，以同一 case、
profile、`all_enabled` 與上述 adaptive controls 重跑完整 production path：
victim／XT grid、phase、MSE、COM_DFE、final COM 的上述數值均相同。
修正後 adaptive/config/window/link/Stage 5/MLSD focused suite 為 `46 passed`；
增加 production XT group 整數 UI 覆蓋後，window suite 為 `12 passed`。
這些結果不代表所有通道、threshold 或記憶體成本均已驗證。
2026-11-15 依核准流程改為先將有效邊界取整 UI、再加 FFE margin、
選 cfg 長度並延伸理想窗後，adaptive focused tests `35 passed`；以相同
bilinear case 重跑 `all_enabled`，grid、phase、MSE 與 COM 均與上表相同。
此結果只適用此 case，不保證其他 response 的 window 起點不變。
Continuous 執行期間在 Windows 觀察到 process peak working set 至少
`955.9 MiB`；這是執行中抽樣的下限，不是完整 peak-memory benchmark。
擴充回歸首次執行為 `92 passed, 7 errors`；7 errors 均在 sandbox 無法建立
system `tmp_path` 的 fixture setup，並未進入測試。於允許 system temp 的
環境重跑完整 policy suite 為 `36 passed`，包含先前 7 項。

2026-11-15 補充非零 victim shift／共同 window 與 adaptive 無 XT 測試；
`test_adaptive_path_windows.py`、`test_adaptive_grid_downstream.py`、
`test_link_effective_range.py` 合計 `28 passed`。前者使用合成資料確認
preset 沿用 pulse 的非零 shift，非所有真實通道的時間對齊證明。
另以 mock stage 計算驗證 `mse`、`dfe`、`mlsd`、`all_enabled` 四種
target 的 stage 執行邊界；加入 MLSD noise 與 stage status tests 合計
`46 passed`。此項驗證 root dispatch，不代表四個 target 各有完整 case。
同日於可使用 system temp 的環境重跑 adaptive、CTLE、MLSD、policy、
post-FFE 與 stage status 合併測試：`105 passed`。

同日對上述 bilinear case 在 production path 加入量測：fine IR 窗外能量／
完整 fine IR 能量，victim actual 和 preset 各為 `1.0037879237241686e-8`，
5 條 XT 為 `0.0`；FFT record 分別是 3400000 samples，victim window 為
`[8448, 139520)`，XT window 為 `[0, 524288)`。Stage 5 用 `np.convolve`
計算的 record 長度之外的線性 convolution 尾端能量／完整卷積能量，在
7 條實際輸入上均為 `0.0`；這是此案例的繞回量，不是普遍精度保證。
帶量測的整個 Python process peak working set 為 `758.63 MiB`（Windows
process `peak_wset`），包含量測額外的陣列／計算，不代表一般執行的精確峰值。

同一 case 切換 continuous-TF 後，victim actual／preset 窗外能量比例各為
`2.5037198660799235e-7`；5 條 XT 分別為 `7.72084298465933e-6`、
`1.4799208261495398e-6`、`2.1096591587373933e-5`、
`6.809116137077002e-7`、`2.6130852677345834e-7`。同樣量測 Stage 5
7 條輸入的繞回能量比例依序為 `1.0405654294674735e-10`、
`9.668034311498272e-10`、`2.1666157635777633e-10`、
`4.301576505158534e-9`、`7.984156063238964e-11`、
`8.335567995414912e-11`、`2.372983749909589e-10`。帶量測 process
peak working set 為 `959.21 MiB`；phase `27`、MSE `0.005352330545424438`、
final COM `2.6844957149167974 dB`。數值為觀測而非已核准的誤差門檻。

兩種 CTLE 案例的 production 裁切均經現有 `LinkSegment.from_ir()`
檢查並成功建立；該方法仍要求最大峰值位於 record 前 75%，且末 1 UI
能量比例不超過 `1e-6`。這只能證明本案例可通過，不能排除其他分散型
XT 合理 response 會被拒絕；目前未改動該工具或宣稱已涵蓋所有 XT。

## Bilinear IIR 早期截尾比較

同一 case、fine target 1 MHz、原 measured-domain 頻率取樣；逐 path 在
`_reference_fd_to_td_record()` 比較既有 `1e-3` 相對門檻與 `0.0`，接著各自
通過相同 CTLE IIR。下表的誤差是 IIR 輸出差值能量／未提前截尾 IIR 輸出
能量；不是 pulse energy、MSE 或 COM 差異，也不是接受標準。

| Path | 原門檻保留 samples | 0 門檻保留 samples | IIR 輸出差值能量比例 |
| --- | ---: | ---: | ---: |
| NEXT 0 | 340000 | 340000 | 0 |
| NEXT 1 | 340000 | 340000 | 0 |
| FEXT 2 | 340000 | 340000 | 0 |
| FEXT 3 | 114205 | 340000 | `2.6178021924435424e-5` |
| FEXT 4 | 117283 | 340000 | `1.0500041520057748e-5` |

上表僅為 IIR 中間輸出；完整 pulse 比較見下節，尚無隔離單一截尾因素的
完整 COM 比較。Reference 方法保留既有截尾；不將上表解讀為 COM 誤差。

### Fine-grid XT pulse tail 後續量測

同一 case 在 Stage 1 第一輪逐條對比既有 `1e-3` 與將 bilinear 預先截尾門檻
設為 `0.0` 的 counterfactual；其餘流程與 fine grid 相同。量測以未提前
截尾 pulse 的完整能量為分母，tail 為從 record 起點 4096 UI 之後的能量。
兩個 response 使用同一 raw-record 時間參考，並非對 production grid 重建。

| Path | 既有 pulse tail／長 pulse 總能量 | 未提前截尾 pulse tail／長 pulse 總能量 | pulse 差值能量／長 pulse 總能量 |
| --- | ---: | ---: | ---: |
| NEXT 0 | `9.341329945062072e-4` | `9.341329945062072e-4` | 0 |
| NEXT 1 | `2.0097211299255702e-4` | `2.0097211299255702e-4` | 0 |
| FEXT 2 | `5.012027310834718e-3` | `5.012027310834718e-3` | 0 |
| FEXT 3 | 0 | `1.3601477709452073e-5` | `1.699438167385343e-5` |
| FEXT 4 | 0 | `4.452755840808587e-6` | `6.735978807215432e-6` |

這是單一 case、單一尾端區間及 counterfactual pulse 的量測，不是 COM
差異或接受標準。FEXT 3／4 的既有提前截尾確實移除部分 XT tail；使用者
已決定保留 reference `bilinear_iir`，另以 `bilinear_fine_grid` 不提前截尾。
此 counterfactual 並非最終 fine-grid 方法的完整對照，後者另改 IFFT grid
及 pre-IIR 時間對齊，不可將上表視為兩個最終方法的唯一差異。

## Fixed 與 adaptive 的 pre-DTE 差異（phase 5）

同一 case、SiCoPR profile、NUM-003 `truncated=4096 UI`；以下 PSD 的數值
為 `||adaptive - fixed||₂ / ||fixed||₂`，不是相對 COM 誤差：

| PSD | 相對 L2 差異 |
| --- | ---: |
| `S_rn` | 0 |
| `S_xn` | `7.17558262656691e-5` |
| `S_tn` | `4.2100450753261566e-5` |
| `S_jn` | `1.8330217452039262e-4` |
| `S_qn` | 0 |
| `S_total` | `5.3520548247365904e-5` |

Fixed 的 h_tn／h_J peak index 為 1192／1193，adaptive 為 928／929；兩條
NEXT 與第一條 FEXT 的 sampled peak 各移動 6 UI。這證明兩種模式送往
4096-UI 截取的 finite record 時間位置不同；此結果與 adaptive window／
XT 整數 UI 平移有關，但尚未逐項隔離每個變更的貢獻。MSE 差異超過 fixed
golden 的 `1e-14` absolute tolerance；COM 數值在此 case 相同。使用者已
確認 adaptive 不要求與 SiCoPR intermediate 完全對齊；fixed golden tolerance
仍只適用 fixed，不能據此宣稱 adaptive 全面等價。
