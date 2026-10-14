# SerDes Coding Todo / Future Ideas

## 目的

這份文件記錄未來可能加入的 module、method、validation flow。它不是 issue tracker，而是避免已討論過的想法遺失。

## 近期優先項目

0. Public GitHub Actions split search
   - 以 `group_id` 為 GitHub Actions matrix/job unit，呼叫 178A `run_partial_group()`，產生可合併的 `group_XXX.csv`。
   - 僅允許已確認可公開的 project config、channel S4P、search result 進入 workflow；不得放入公司名稱、內部路徑、客戶資訊或任何公司文件。
   - final merge/top-K 可先維持本機或 Codespaces 手動執行；之後再決定是否也加入 Actions workflow。

1. COM v1.0 search flow
   - 完成 93A search candidate sweep。
   - search parameters: `c_m2`, `c_m1`, `c_1`, `g_DC`, `g_DC2`。
   - search 階段只保存 lightweight summary。
   - best candidate 再跑完整 PMF/COM。
   - 未來可加入 `keep_top_n_status`：只對 top N candidates 保留完整 `COMStatus`，用於 search debug，但避免保存所有 candidate 的大型 arrays。

2. Single-run full output
   - 定義 durable output 格式。
   - 目標是可以重建某次 `COMStatus`。
   - 需要包含 config snapshot、paths、DFE、imp、PMF、COM、debug plots。

3. Excel input contract
   - 完成 project-owned template 的 mapping validation。
   - 確認 PyChOpMarg/PyCOM reference config 是否正確 mapping 到目前 template。
   - 前處理 adapter 不放入 COM algorithm core。
   - 建立雙向離線 preprocessing adapter：
     - `adhoc_to_project_config()`：將 COM Ad Hoc Config 轉為 versioned Project Config，例如 `config_93A.xlsx` 或 `config_178A.xlsx`。
     - `project_to_adhoc_config()`：將 Project Config 匯出為 COM Ad Hoc 對外溝通格式。
   - 固定三層名稱與邊界：`Ad Hoc Config -> Project Config -> Runtime Config`；runtime `excel_to_config_*()` 只處理 Project Config，不直接解析或輸出 Ad Hoc Config。
   - `Include PCB` mapping：`0` 對應所有 `partial_host.enable=False`；`1` 對應 Tx/Rx 兩端 enable；`2` 對應 Rx-only enable。各 path 的 host length 必須依 COM Ad Hoc `add_brd.m` 的 path-specific `z_bp` selection 映射。

4. COM module cleanup
   - 先移出 Excel I/O。
   - 再移出 reference adapter。
   - 再移出 smoke test。
   - 最後才拆 config/status/formula。

5. Project template update
   - `templates/` 目前仍是舊版 config workbook 格式，暫標記為待更新。
   - 更新前不可視為現行 `config_93A.xlsx` / `config_178A.xlsx` 的正式模板。

## COM / 93A Core

28. Formal 93A validation case
   - 尋找或整理真正對應 93A 的 channel / config baseline。
   - 建立獨立 template，不與 `debug_case_93a_style` 混用。
   - 驗證 package/filter/noise/jitter/search parameters 是否逐項對應 93A。

6. FOM validation
   - 檢查 93A.1.6 imp statistics。
   - 檢查 FOM formula 與 sign convention。
   - 建立 small sanity case。

7. PMF validation
   - 檢查 93A.1.7 PMF source：ISI、Gaussian、dual-Dirac jitter、XT。
   - 檢查 PMF convolution order 與 amplitude grid。
   - 檢查 final COM。

8. COM 93A vs 178A comparison
   - 先不實作。
   - 保留未來架構：`model_93a.py` / `model_178a.py` 或 method suffix `_93a` / `_178a`。

## DFE / Sampling Phase Validation

8. DFE / sampling phase debug report
   - selected `ts`
   - selected `pos`
   - main cursor
   - fixed DFE coefficients
   - clipped taps
   - residual ISI vector

9. 93A sampling phase validation
   - 檢查 `_find_sampling_phase_93A()`。
   - 檢查 `h_J` boundary handling。
   - 檢查 `pos == 0` / `pos == per_ui - 1` edge cases。

10. 802.3ck floating DFE
   - 未來項目。
   - 需要釐清 floating bank、overlap removal、tail RSS constraint、tap indexing。

10.1 Versioned floating-tap limiter boundary
   - 93A：floating group 是 DFE feedback taps；limiter 屬於 `b` / DFE coefficient family。
   - 178A：floating group 是 FFE feed-forward taps；limiter 屬於 `w` / FFE coefficient family。
   - 不可共用 93A DFE floating limiter 與 178A FFE floating limiter；178A Project Config 需獨立描述 fixed-FFE 與 floating-FFE limiter。

## SparamPreProcess

11. 建立 `SparamPreProcess` module/class
   - 專門處理 `sparam_to_sbr.pdf` 中提到的前處理議題。
   - 包含 DC、causality、passivity、reciprocity、extrapolation。

12. Raw S4P / full mixed-mode debug domain
   - 保存原始 S4P。
   - 產生完整 mixed-mode matrix。
   - 提供 Sdd / Sdc / Scd / Scc debug。
   - 避免讓 `SparamModel` 失去 Sdd 2-port contract。

13. S4P port-order auto debug helper
   - 比較 candidate port order，例如 `0123`、`0213`。
   - 檢查 `Sdd21/Sdd11/Sdd22` magnitude。
   - 檢查 mode conversion。
   - 檢查 impulse response causality。
   - 檢查 polarity / Tx-Rx direction swap。

14. Passivity check / fix
   - 定義 passivity metric。
   - 研究 passivity enforcement/correction 是否需要。

15. Causality check / fix
   - 建立 S-parameter to impulse response causality report。
   - 檢查 non-causal energy、wrap-around、main cursor alignment。

16. S-parameter DC extrapolation
   - 比較 hold、linear、rational fit、low-frequency physical model。
   - 對應 `sparam_to_sbr.pdf` 的 missing DC 問題。

17. Channel high-frequency extrapolation
   - 定義 measured channel 未達 LinkConfig Nyquist 時的處理。
   - 避免 high-frequency 補值造成 impulse artifact。

18. Measured-domain cascade policy
   - S-parameter domain 優先維持 measured grid。
   - cascade 後再轉 voltage transfer function。
   - 最後才轉到 `LinkSegment` grid。

## LinkSegment Deferred Flow

19. `LinkSegment.from_ir()` flow 加強
   - 明確定義 measured discrete waveform / fitted IR / resample 到 LinkConfig grid 的流程。
   - 檢查 interpolation 後是否需要 amplitude scaling。
   - 檢查 raw/aligned IR contract 是否仍適用。

20. LinkSegment plot/report
   - 增加 standardized debug plot set。
   - 例如 TF / IR / SR / SBR / main-cursor aligned view。

## PSD / Noise

21. PSD arithmetic
   - 定義 PSD addition / filtering / integration。
   - 支援多個 imp PSD 合成。

22. PSD resample / align policy
   - arbitrary grid 與 LinkConfig grid 的轉換。
   - DC extrapolation 與 high-frequency extrapolation policy。
   - `ifftable` contract。

23. PSD to time-domain noise generation
   - one-sided PSD 轉 random time-domain noise。
   - 用於 Monte Carlo waveform debug。

24. ADC quantization noise helper
   - 不放在 `ContinuousPSD` constructor。
   - 建立 helper 將 ADC setup 轉成 `ContinuousPSD.from_sigma()` 或 `from_constant()` 輸入。

## PMF Handler

25. PMF cleanup
   - 移除或實作殘留 public API：`fir_filtered_pmf()`。
   - 確認 public methods 全部是 immutable style。

26. PMF debug / plot tools
   - plot PMF/PDF-like view。
   - plot CDF。
   - main cursor normalized view。
   - tail probability debug view。

27. PMF numerical validation
   - 檢查 `combine()` round-trip / mass conservation。
   - 檢查 `resample_dx()` mass conservation。
   - 檢查 `fir_filter()` tap pruning 與 93A threshold。


## Deferred: development validation entry (2026-09-15)

Keep the current production workflow (branch + case_id). Defer this design until after today's 178A full search; no workflow or runtime changes are authorized by this note.

- Add a separate development-validation entry, sharing the production runner.
- Allow selecting an existing Actions run/artifact to rerun finalize without recomputing partial results.
- Allow explicit EXEC_POLICY overrides for single_run/search_sweep/search_final; save original, overrides and resolved settings with code version and input hashes.
- Validate reuse against fixed config, channels, candidate grid, search_sweep policy and changes to the computation. Report-only changes can reuse partial results when compatible; equation changes may invalidate them.
- Execution-stage selection is orchestration, not another RUN_MODE. Search ranges remain workbook-owned; fixed_config.policy remains the consistent model-treatment boundary.
