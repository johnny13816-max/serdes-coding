# NUM-002 — Gaussian support retirement

**狀態：Closed 2026-11-06；isolated commit 與 `origin/main` 同步為最後 integration gate。**

## 決策

178A Gaussian PMF support 固定為 internal 8σ，不再由 workbook、Python
Project Config 或 `sicopr_reference_v1` profile 選擇。`Pmf1D` 保留通用
`n_sigma` 參數；`COMPMFRuntimeConfig.gaussian_n_sigma` 只保存 resolver 產生的
internal derived value。NUM-002（legacy B-014）因此退休，不再列為 branch。

`keep_mass` 維持獨立 NUM-006 execution control：8σ 決定初始 Gaussian
support，`keep_mass` 只裁切後續 convolution 的 retained mass。

## Evidence

固定 SiCoPR case、production path、`dy=10 µV`、`keep_mass=1` 比較：

| Metric | 3.540083799206174σ | 8σ | Delta |
|---|---:|---:|---:|
| Gaussian PMF points | 1,889 | 4,267 | +2,378 |
| Combined PMF points | 42,045 | 52,735 | +10,690 |
| Single-run time | 91.545 s | 94.259 s | +2.714 s |
| `V_qc` (V) | 0.043139428270345365 | 0.04313942827034537 | 6.9e-18 |
| `A_ni` (V) | 0.2656833333333335 | 0.2656833333333335 | 0 |
| COM_DFE (dB) | 1.5247607834259893 | 1.5247607834259893 | 0 |
| final COM (dB) | 2.895898684873287 | 2.895898684873287 | 0 |

Runtime 是單次量測，只用於確認成本量級，不作 benchmark claim。正式 closure
evidence：focused tests `48 passed`；九份實際修改 workbook 的目標文字與
formula-error scan 均為 0；SiCoPR production golden `1 passed`，
`COM_DFE=1.5247607834259893 dB`、final `COM=2.895898684873246 dB`，intermediate
digests 不變。依賴缺少 private/reference workbook 的 conversion tests 未宣稱通過，
亦不屬本契約 acceptance boundary。

## Coding layer

```text
L1 Workbook / Python Project Config
└─ no Gaussian-support RG or reference override
   └─ L2 178A PMF resolver
      └─ fixed internal 8σ
         └─ L3 COMPMFRuntimeConfig derived value
            ├─ pre-DTE / ADC-input Gaussian
            ├─ final COM Gaussian
            └─ MLSD added-noise Gaussian
```

93A 與 generic `Pmf1D` API 不在本契約修改範圍。
