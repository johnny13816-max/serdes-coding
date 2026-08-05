# SerDes Coding Todo / Future Ideas

本文件記錄已討論但尚未完整落地的功能。目的不是取代 issue tracker，而是保留專案設計方向，避免之後忘記已經討論過的 module 或 method。

## COM / 93A Core

1. `COM.run()` 加入完整 FOM search
   - 掃描 `c(-2)`, `c(-1)`, `c(1)`, `gDC`, `gDC2`。
   - 每組設定需重新建立 equivalent channel、DFE、impairment，最後選擇最大 COM/FOM。

2. `COMResult / COMStatus` 最終輸出格式
   - 區分單一設定下的結果與掃描完成後的最佳結果。
   - 保留 path-level 中間量，方便 debug `status.paths[0].H_21`、`status.paths[0].pulse` 等資料。

3. 93A.1.7 PMF pipeline 完整串接
   - 將 signal PDF、ISI、noise、jitter、crosstalk PMF 合成。
   - 接到 final COM/FOM calculation。

4. `calculate_COM()` 主流程
   - 接在 `_find_pos_and_dfe()` 與 `_calculate_impairments()` 後面。
   - 實作從 impairment statistics / PMF 到 final COM value 的流程。

5. COM 93A vs 802.3ck / 178A 版本分流
   - 先完成 93A。
   - 後續用 config version 或 method naming 區分 `_93a`, `_178a`, `_8023ck` 行為。

## DFE / Sampling Phase Validation

6. DFE / sampling phase validation
   - 檢查 `_calculate_h_J()` 的 boundary case，特別是 `pos == 0`。
   - 驗證 fixed DFE tap clipping、sample phase search、main cursor 選擇是否符合 spec。
   - 驗證 802.3ck floating DFE 的 floating bank、overlap removal、tail RSS constraint、tap indexing。
   - 增加 debug report，例如 selected `ts`, `pos`, main cursor, clipped taps。

## SparamPreProcess

7. `SparamPreProcess` module / class
   - 專門處理 S-parameter quality 與 preprocessing。
   - 來源參考包含 `sparam_to_sbr.pdf` 內的 DC、causality、passivity、reciprocity、extrapolation 等議題。

8. Passivity check / fix
   - 檢查 S matrix 是否 passive。
   - 後續評估是否提供 passivity enforcement / correction。

9. Causality check / fix
   - 檢查 S-parameter 轉到時域後是否有 non-causal response。
   - 提供 debug/report，而不是直接靜默修正。

10. S-parameter DC extrapolation 多模型比較
    - 比較 hold、linear、rational fit、low-frequency physical model 等方法。
    - 用於缺少 DC 點的 measured S-parameter。

11. Channel high-frequency extrapolation policy
    - measured channel 不到 LinkConfig Nyquist 時，明確定義補高頻策略。
    - 需要避免不合理高頻外推造成 impulse response artifact。

12. SparamModel measured-domain cascade policy
    - S-domain 盡量維持 measured grid。
    - 轉成 voltage transfer function domain 後，再進 LinkSegment grid。

## LinkSegment Deferred Flow

13. `LinkSegment.from_ir()` 後續處理 flow
    - 目前先不文件化完整 contract，等 from-ir / resample / causality policy 穩定後再整理。
    - 之後需要補強 measured discrete waveform、fitted IR、resample 到 LinkConfig grid 的處理方式。

## PSD / Noise

14. PSD arithmetic
    - 增加 PSD 相加、縮放、合成等操作。
    - 支援多個 impairment PSD 組合。

15. PSD resample / align policy 完整化
    - 保留 arbitrary grid 與 LinkConfig grid 兩種入口。
    - 明確定義 `ifftable`、DC 外推、高頻外推、filter grid mismatch 的行為。

16. PSD to time-domain noise generation
    - 從 one-sided PSD 產生 random time-domain noise。
    - 用於 Monte Carlo waveform 或 debug noise injection。

## PMF Handler

17. PMF 93A.1.7 完整功能檢查
    - 確認 `PMF1D` 涵蓋 multi-dirac、Gaussian、scale_x、shift_x、resample_to_grid、fir_filter、cascade、CDF。

18. PMF lazy CDF policy
    - 決定 CDF 是否採 lazy evaluation。
    - 明確定義何時重算、何時不保存。

19. PMF debug / plot tools
    - 畫 PDF/CDF。
    - 加入 main cursor normalization、tail probability 等 debug view。
