# TC-016 — 178A channel S4P/Sdd renormalization 順序正式分支

**狀態：2026-10-11 使用者明確核准；工作樹已實作、分層測試與完整回歸通過，待隔離提交。** 關聯 G-001；分類為平行算法 policy。下列邊界和驗收適用於本次實作。

## 結論與依據

現行 178A／93A 共用 reader 先將 S4P 轉成 differential Sdd，再把二埠從 measured differential impedance renormalize 至 `2R_0`。這對應目前採用的 178A D3.0 Annex 178A.1.3、Eq. (178A-4) 二埠敘述。SiCoPR 先在原四埠上把 single-ended reference renormalize 至 `R_0`，再依相同 port order 取 Sdd；此順序在存在 differential/common-mode 耦合時能保留四埠中的耦合對轉換結果的影響。兩者是不同的模型選擇，不以數值較接近 reference 代替 spec 判斷。

本案六路徑用暫存 S4P-first reader 對 SiCoPR S_ch 四元素的最大複數差 `2.78e-15`；既有 32-phase MSE A/B 為 Sdd-first `0.006170581278`、S4P-first `0.006169233304`，均選專案 phase 23。S4P-first 並未單獨消除 phase／tap 差。證據在 [channel renormalization audit](../validation/channel_renormalization.md)。

## 目前 → 提議資料流與責任層級

```text
178A fixed_config.channel_renormalization_order
  -> COMConfig（只選 policy）
  -> 178A _build_channel_under_test（傳入同一 policy 給六條路徑）
  -> SparamModel.from_touchstone/from_network（執行 renormalization）
  -> measured-grid align -> S_tx/S_ch/S_rx cascade -> H21 -> pulse
```

新增 `channel_renormalization_order: Literal["sdd_first", "s4p_first"]`，預設 `sdd_first` 以維持既有 case；SiCoPR Akinwale case 設 `s4p_first`。`s4p_first` 僅適用 `mode="s4p"` 且明確提供目標 differential `z0=2R_0`、四個 single-ended port 的實數 reference impedance 相同的情況：copy 原 Network → 把四埠 renormalize 至 `R_0` → 按 `port_order` 取得 Sdd → 建立 z0=`2R_0` 的二埠 SparamModel。對不滿足前提的輸入明確報錯，不默默退回 `sdd_first`。`sdd_first` 保留既有公式、預設和結果。

COM 的 `_build_path()`、package、filter、MMSE solver 都不得對已建立的 S_ch 再做補救式 renormalization。`from_sdd_array()`／`from_s4p_array()` 的現有語意不變；93A 不暴露此新 project policy，仍用原本 `sdd_first`。

## 預計修改檔案與函式

| 層級 | 檔案／函式 | 修改 |
| --- | --- | --- |
| utility 數值 owner | `src/serdes_coding/utilities/sparam.py::SparamModel.from_network()`／`from_touchstone()` | 增加明確的順序參數與 S4P-first 四埠複本轉換；預設保留 Sdd-first；檢查 z0、mode、port impedance 前提 |
| 178A config／orchestration | `src/serdes_coding/models/com_model_178A.py::COMConfig`、`_build_channel_under_test()`、`COM.build_all_paths()` | 配置並傳遞 policy，所有 victim/NEXT/FEXT 一致；不修改 `_build_path()` 數值 |
| workbook／conversion | `src/serdes_coding/io/com_excel_io_178A.py`、`src/serdes_coding/io/conversion/mapping_rules.py`、`cases/_templates/178A/config.xlsx`、`cases/sicopr_akinwale_vendorx_22db/178A/config.xlsx` | 178A fixed-config policy row；模板 `sdd_first`，SiCoPR case `s4p_first`；不從 Ad Hoc intrinsic 映射 |
| tests | `tests/test_channel_renormalization.py`、178A fixed-case integration test | 四埠 oracle、source 不變、port permutation、相同阻抗、invalid inputs、六路徑 S_ch 與下游固定候選 |
| docs | `docs/models/178A/config_tree.md`、`docs/models/178A/stages/path_construction.md`、`docs/validation/channel_renormalization.md`、`docs/architecture/adhoc_mapping_fields.md`、本契約／active status | 區分兩順序、預設、適用前提與責任層級 |

GUI 僅由既有 fixed-config policy row 呈現；不新增 GUI 專屬公式或 requiredness。若實際實作需要超出本表的檔案或改變 93A，先修訂契約。

## 中間量、驗證、影響與回退

`s4p_first` 預期改變 S_ch 四元素及其下游 S_all、H21、pulse、h_dsamp、S_xn/S_tn/S_jn、V_qc/S_qn、R_n、phase、FFE/DFE/MSE/COM；不應改 raw S4P、S_tx/S_rx package、LinkConfig、filter、MMSE 求解式。相同 S_ch 若注入兩路，所有下游量應一致。93A 及現有 178A 預設／search 結果必須不變；178A single、search sweep/final 應讀同一 fixed policy。

驗收先用合成、含 mode coupling 的四埠矩陣與獨立 scikit-rf 四埠 oracle 比較，Sdd 四元素 `atol=1e-12`；六條 Akinwale S_ch 對已擷取 SiCoPR dump 最大複數差不超過 `1e-11`，並核對 S_all 四元素、terminated H21、固定 candidate 的 h_dsamp/R_n／MSE。sdd_first 舊 golden 不變至既有容差；93A、178A 全回歸及一次固定 single-run 通過後才進 search。這個 contract 不要求最終 COM 追零，因 67 GHz input、ADC PMF 與相位選擇仍是獨立邊界。

開始實作前在 `%TEMP%` 專用子目錄保存本次涉及檔案的精確修改前 patch／副本。核心數值修改須獨立 commit；現有工作樹混有其他變更，無法安全隔離時不得把整檔或既有 staged 內容混入提交，狀態保留「待隔離提交」。回退只逆轉本契約 patch／專用 commit，不還原既有使用者修改。

## 2026-10-11 實作與固定驗證

`SparamModel.from_network()`／`from_touchstone()` 已加入 keyword-only `renormalization_order`。`s4p_first` 對來源 Network 的副本做四埠 renormalization，明確檢查 scalar real target z0 和共同 real measured port impedance；`sdd_first` 保留原入口。178A `COMConfig` 選 policy，`_build_channel_under_test()` 傳至六條 channel。模板選 `sdd_first`、SiCoPR case 選 `s4p_first`；93A 與 `_build_path()` 沒有修改。

六條 SiCoPR case 的正式 `S_ch` 與原 reference-only S4P-first reader **逐元素差 0**；原 reference-only reader 已對 SiCoPR dump 驗證最大複數差 `2.78e-15`。另把正式輸出的六條 Sdd channel 在暫存記憶體取 `f<=67 GHz`，以現行 `out_of_measured=zero_padding` 轉 grid，固定 pos=22、ts=163990 並只在比較副本補已知 `16.5588 ps` 時間原點：`h_dsamp` 與舊受控 oracle 最大差 `0 V`，`R_n[0:86]` 各來源最大差 `0 V²`，MSE 差 `0`；主游標 `14.31679220487629 mV`、`S_xn` RMS `0.333390253611 mV`、`S_qn` RMS `0.384350322061 mV`、MSE `0.006206638173753184`。這是新正式 branch 對歷史 SiCoPR 比較邊界的重現，**不是**原始 100 GHz case 的 final COM 對齊宣告。

在同一受控邊界與 SiCoPR locked solver input 直接比：reference 主游標 `14.317724231 mV`，專案差 `−0.000932026 mV`；主游標前 100 到後 256 UI 的最大／RMS 差 `0.001848009/0.000158875 mV`。receiver `R_n[0]` 差 0；XT、TX、jitter、quantization 分量分別差 `−9.1664e-11`、`−3.0056e-11`、`−4.9821e-11`、`+2.2457e-9 V²`，總差 `+2.0741e-9 V²`。SiCoPR MSE `0.006191261024525`、專案 `0.006206638173753`，差 `+1.5377e-5`。完整來源逐項值在 `%TEMP%/serdes-tc016-20261011/mmse_input_compare.json`；量化項仍主導殘差，不是本 renormalization 分支的失敗。

驗證命令：專案 `.venv` 執行 `pytest -q -p no:cacheprovider`（`--basetemp` 指向 `%TEMP%/serdes-tc016-20261011/pytest-full`），結果 `108 passed, 2 subtests passed`。本次快照及 fixed-case 腳本／JSON 全在 `%TEMP%/serdes-tc016-20261011/`。完整 search 尚未執行；現有工作樹混有其他 protected model 未提交修改，因此不得將整檔混入 TC-016 專用 commit。

正式 SiCoPR case（原始 100 GHz S4P、`s4p_first`、`zero_padding`）的 `COM.run()` 以 `single_run.target="mse"` 完成 32-phase sweep：選 pos=23、ts=163991，87 個 FFE tap，MSE `0.0062106134601428815`。紀錄在 `%TEMP%/serdes-tc016-20261011/single_run_result.json`。這與前述暫存 67 GHz／固定 pos=22 的 MMSE 輸入比較是兩個不同邊界，不應直接比較 MSE。核心本次專用 diff 在同一 TEMP 目錄的 `tc016-kernel-only.patch`，只含 `sparam.py` 與 `com_model_178A.py` 本次修改。
