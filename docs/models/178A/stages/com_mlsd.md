# 178A MLSD COM stage

> **Review state:** TC-023 已完成 Eq. 178A-49 索引修正及 reference realization。
> Akinwale reference profile 的最終 COM 差 `-0.0148476782 dB`，通過 0.05 dB
> reference gate；兩個 amplitude-grid bin 的殘差仍保留為可追查數值差異。

## Purpose and ownership

This optional stage evaluates the Annex 178A MLSD adjustment after a complete DFE COM baseline exists.

It owns:

- added receiver-noise calibration and its convergence trace;
- the MLSD noise/interference PSD and autocorrelation;
- detector-error contributions by sequence length;
- raw and selected MLSD COM values;
- `COMMLSDStatus` assignment to `status.mlsd`.

It does not modify the stored DFE PMF baseline. `status.pmf` remains the DFE result, and MLSD results are stored separately.

## Governing references

Current source identifies:

- Annex 178A.1.10.1 and Eq. 178A-50 for added-noise calibration;
- Eq. 178A-47 through Eq. 178A-53 for truncated MLSD detector-error calculation;
- Eq. 178A-54 for MLSD input PSD/autocorrelation construction.

The implementation annotations and data flow are recorded here. Focused equation checks are listed below; they do not certify the remaining normalization, recurrence, or end-to-end reference agreement.

## 逐式 spec review 索引

下表是下一輪逐式核對的入口；「已驗」只代表所列不變量，並非整個 MLSD stage 與 reference 等價。

| 178A 公式 | 目前程式責任 | 已驗證／待核對 |
|---|---|---|
| (47) | `calculate_COM_MLSD()`：`A_MLSD=-P_an^{-1}(DER_MLSD)`；`COM_DFE+20log10(A_MLSD/A_s)`，再套 DFE floor | TC-011 已驗分母與 floor；待跨 case |
| (48) | `calculate_der_mlsd()`：逐 `j` 的 CDF 門檻、`((L-1)/L)^(j-1)` 權重與截斷加總 | 固定候選 65–128 項尾和 `2.05e-18`；門檻／無窮和一般情況待核對 |
| (49) | `_build_mlsd_sequence_vector()`：建立 `u_j` 的首項、中間項、末項 | TC-023 已驗 `j=1,2,3`；末項為 `(-1)^(j+1)b_1` |
| (50) | `evaluate_delta_com_an()`／`solve_g_an()`：`S_an=g_an S_rn |H_rxffe|²` 的校準 | post-FFE `S_rn` 已含 FFE；校準數值及 reference 邊界待核對 |
| (51) | `evaluate_delta_com_an()`：`sigma_an²=sigma_G²+power(S_an)` 並重建 `p_an` | Gaussian／PMF 卷積與 quantile 細節待核對 |
| (52) | `calculate_der_mlsd()`：`p_1=conv(p_an,scale(p_an,+b_1))` | TC-012 非對稱 PMF 符號測試已驗；一般 PMF 網格誤差待核對 |
| (53) | `calculate_der_mlsd()`：後續迭代卷積 `scale(p_an,1-b_1)` | 遞迴次數與 PMF 網格誤差待核對 |
| (54) | `build_mlsd_noise()`：`S_ni=S_n|H_rxffe|²+S_an+S_isi`；`R_ni` 由同一 PSD 反轉換 | TC-009 已驗 pre-FFE 選源、one-sided `S_isi`、Parseval 與 PSD 和；跨 case 待核對 |
| (54) 後文 | `calculate_der_mlsd()`：由 `R_ni[n]/R_ni[0]` 建 Toeplitz `V_j` | 矩陣維度、lag 與數值正定性待核對 |

## 公式到程式的逐條對照（review 用）

本節只描述**目前工作樹實作**，以便逐項與 178A 原文核對；程式註解或本節
都不是「已符合 spec」的宣告。每一條的 review 結論應記回上表與對應 TC。

### Eq. 178A-50：added receiver-noise PSD

`evaluate_delta_com_an()` 收到的是 post-FFE `S_rn`，因此程式的 `S_an` 已在
RX FFE output；此處不能再次乘 `|H_rxffe|²`：

```python
# com_model_178A.py::evaluate_delta_com_an()
# Eq. (178A-50). post_ffe.S_rn already contains |H_rxffe|^2.
S_an = SampledPSD(
    theta=post_psd.S_rn.theta,
    psd=g_an * post_psd.S_rn.psd,
    fb=post_psd.S_rn.fb,
    cfg=post_psd.S_rn.cfg,
)
```

`solve_g_an()` 不改變公式；它以 `g_an=0` 起始、倍增建立 bracket，然後二分
求使 Eq. 178A-51 所得 penalty 接近 `delta_com_an` 的非負尺度。數值終止條件
目前為絕對殘差 `<= 1e-2 dB`、最多 64 次，尚待確認是否應成為明示 policy。

### Eq. 178A-51：added-noise PMF 與校準量測

目前將原 Gaussian sigma 與 `S_an` 積分出的 sigma 作 RSS，並只替換 Gaussian
PMF；DFE 的 ISI／XT／DD／ADC quantization PMF 維持不變：

```python
# com_model_178A.py::evaluate_delta_com_an()
sigma_added = float(S_an.to_sigma())
sigma_an = float(np.hypot(sigma_G, sigma_added))
p_G_an = Pmf1D.gaussian(mu=0.0, sigma=sigma_an, dx=pmf_cfg.dy,
                         n_sigma=pmf_cfg.gaussian_n_sigma, unit="volt")
p_an = (pmf_dfe.p_ISI.combine(pmf_dfe.p_XT).combine(pmf_dfe.p_DD)
        .combine(pmf_dfe.p_qn).combine(p_G_an, name="MLSD added-noise total"))
a_ref = abs(float(pmf_dfe.p_combined.quantile(der_0)))
a_an = abs(float(p_an.quantile(der_0)))
delta_com_an_temp = 20.0 * np.log10(a_an / a_ref)
```

`Pmf1D.quantile()` 是離散右連續 CDF 的第一個 `CDF >= der_0` grid point；因此
此處另有 PMF `dx` 量化誤差。Eq. 50/51 的 PMF 組成、ADC range 是否應重算、
以及 quantile convention 仍是獨立 review 項目。

### Eq. 178A-54：MLSD input PSD 與 autocorrelation

此 block 必須區分 Eq. 178A-15 的 pre-FFE `S_n` 與 Eq. 178A-50 的 post-FFE
`S_an`。前者經 `H_rxffe` 一次，後者不得再濾波；ISI 項由 two-sided spec
density 轉成 `SampledPSD` 的 one-sided rFFT 表示：

```python
# com_model_178A.py::COM.build_mlsd_noise()
S_n_filtered = S_n.filtered_by(H_rxffe)             # S_n |H_rxffe|²
S_isi = SampledPSD.from_constant(
    H_rxffe.theta, imp_status.sigma_X**2 / H_rxffe.fb,
    H_rxffe.fb, cfg=H_rxffe.cfg,
).filtered_by(h_ISI)                                # one-sided S_isi
S_ni = S_n_filtered.add(added_noise.S_an).add(S_isi)
R_ni = S_ni.to_autocorrelation()
```

`SampledPSD.from_constant()` 對內部 rFFT bins 做 two-sided→one-sided folding；
DC/Nyquist 不加倍。focused test 驗 `R_isi[0] = sigma_X² sum(h_ISI²)`、
`S_ni` 的逐 bin 加總、pre-FFE source 與共同 grid。

### Eq. 178A-52／53：`p_j` recurrence

`Pmf1D.scale_x(a, keep_dx=True)` 表示隨機變數 `Y=aX` 並將 probability mass
投影回共用 PMF grid；PDF 的 `1/|a|` 正規化由該 utility 的 mass projection
承擔。程式中 Eq. 52 的尺度是正的 `+b_1`；第 2 項起依 Eq. 53 加上
`(1-b_1)` 倍的同一 `p_an`：

```python
# com_model_178A.py::calculate_der_mlsd()
p_1_term = p_an.scale_x(b_lim_1, keep_dx=True, dx_ref=p_an.dx)
p_later_term = p_an.scale_x(1.0 - b_lim_1, keep_dx=True, dx_ref=p_an.dx)
if j == 1:
    p_j = p_an.combine(p_1_term, name="MLSD p_1")
else:
    p_j = p_j.combine(p_later_term, name=f"MLSD p_{j}")
```

Eq. 52 的正負號已有非對稱 PMF test；Eq. 53 的 recurrence、每次 projection
造成的 grid 誤差與 truncation policy 尚未完成數學 review。

### Eq. 178A-49 與 Eq. 178A-54 後文：`u_j`、`V_j`

程式使用 0-based array 表示 spec 的 1-based vector：第 0 格為 `1`，中間
spec index `2..j`，最後一格是 spec index `j+1`。`V_j` 是以 `R_ni[0]`
正規化的 Toeplitz covariance matrix：

```python
# com_model_178A.py::calculate_der_mlsd()
u_j = _build_mlsd_sequence_vector(j, b_lim_1)
# helper 內：spec 最後一項 i=j+1；Python 儲存位置才是 j
u_j[j] = ((-1.0) ** (j + 1)) * b_lim_1
V_j = toeplitz(R_ni[:j + 1] / R_ni[0])
```

`j=1,2,3` 的完整向量已有 equation-level test；`V_j` 的 lag ordering 由固定
reference case 驗證，但跨 case 正定性仍由 runtime guard 保護。

### Eq. 178A-48：每個 sequence-length 的 detector error

每個 `j` 以 `u_j`／`V_j` 建 threshold，查 `p_j` 的 CDF，再乘 PAM sequence
機率；目前將無窮和以 `trunc_len` 截斷：

```python
# com_model_178A.py::calculate_der_mlsd()
quadratic = float(u_j @ V_j @ u_j)
norm_sq = float(u_j @ u_j)
threshold = -As * norm_sq ** 1.5 / np.sqrt(quadratic)
der_event = float(p_j.cdf_at(threshold))
der_by_j[j - 1] = ((L - 1.0) / L) ** (j - 1) * der_event
DER_MLSD = float(np.sum(der_by_j))
```

此 block 已檢查 `R_ni` 長度／實數性／`R_ni[0] > 0`，但 threshold 的
`||u_j||³ / sqrt(u_jᵀV_ju_j)`、CDF tail convention、PAM 權重、截斷誤差仍待
直接對照 spec。不能用最終 COM 接近 reference 取代這些檢查。

### Eq. 178A-47：MLSD COM

`DER_MLSD` 回代至 added-noise `p_an` 的 inverse CDF，並以 signal amplitude
`A_s`（不是 `A_ni`）計算增量；最後執行規範文字所述的 DFE floor：

```python
# com_model_178A.py::COM.calculate_COM_MLSD()
A_MLSD = -float(added_noise.p_an.quantile(DER_MLSD))
delta_COM = float(20.0 * np.log10(A_MLSD / imp_status.As))
COM_MLSD_raw = COM_DFE + delta_COM
COM_MLSD = max(COM_DFE, COM_MLSD_raw)
```

已用人工 PMF 驗過 `A_s` 分母和 floor；inverse-CDF 的 grid 誤差與跨 case
reference 數值仍待 review。

## Enablement and prerequisites

MLSD runs when:

- `cfg.mlsd.enable` is true; and
- the active target is `mlsd`, or the target is `full` with MLSD enabled.

A direct `target="mlsd"` with MLSD disabled is rejected. The current implementation also requires exactly one DFE feedback tap: `cfg.dte.N_b == 1` and selected `b_lim.shape == (1,)`.

Required completed inputs are:

| Input | Required data | Use |
|---|---|---|
| DFE PMF status | component PMFs, `p_combined`, `A_ni`, and DFE `COM` | immutable baseline and added-noise calibration |
| selected pre-DTE and post-FFE status | pre-FFE `S_total` (Eq. 178A-15 `S_n`), run-level-grid `S_rn`, `sigma_G`, `H_rxffe`, `h_ISI`, `sigma_X` | added-noise calibration and Eq. 178A-54 noise model |
| selected DTE | one limited feedback coefficient | DER recurrence |
| PMF config | final-COM resolved grid | added-noise PMFs |
| MLSD config | `trunc_len`, added-noise target | convergence target and sequence length |
| fixed config | `L`, `DER_0`, `As` | detector-error and amplitude evaluation |

## MLSD configuration

| Field | Current role |
|---|---|
| `enable` | enables the optional stage |
| `trunc_len` | number of sequence-length contributions; must be positive when enabled |
| `delta_com_an` | explicit added-noise calibration target in dB |
| `minimum_com_limit` | fallback target when `delta_com_an` is absent |

`resolved_delta_com_an()` chooses explicit `delta_com_an`, otherwise `minimum_com_limit`, and raises if neither is available. This follows 178A.1.10.1: the specified `delta_COM_an` target defaults to the minimum COM limit defined by the owning clause or annex. For the supported D3p2 Ad Hoc workbook, `add_rx_noise` maps to `delta_com_an` and `COM Pass threshold` maps to `minimum_com_limit`.

The added-noise numerical solver currently uses function defaults `cvg_th=1e-2 dB` and `max_iter=64`; these are internal solver settings rather than workbook fields.

`COMPolicyConfig` 將可平行的 realization 保留為具名方法：

| Method field | Annex/general | Reference profile |
|---|---|---|
| `added_noise_pdf` | `gaussian_addition` | `scaled_total_pdf` |
| `mlsd_quantization_psd` | `pre_dte_filtered`：`S_qn` 隨完整 RxFFE filtering | `main_tap_white`：`S_qn` 保持 white，只乘 RxFFE main-tap gain squared |
| `sequence_termination` | `fixed_length_sum` | `matlab_relative_tail` |
| `reported_der` | `raw_sequence_sum` | `baseline_pdf_re_evaluation` |

`align_to_ref` 不進入 model；project Excel adapter 一次展開右欄設定。Eq. 178A-49
sign 不在此表，因為它是共同公式修正。

## Top-level flow

```text
calculate_COM_MLSD(run_cfg=None)
├── validate enablement, N_b, and completed prerequisite status
├── resolve final-COM PMF config with optional run_cfg.pmf_dy_override
├── Annex: solve_g_an(target, ...)
│   └── reference: scale complete DFE PDF and derive g_an from variance delta
├── build_mlsd_noise(...)
│   └── return COMMLSDNoiseStatus with S_isi, S_ni, and R_ni
├── calculate_der_mlsd(p_an, R_ni, ...)
│   └── return DER_MLSD and der_by_j without mutating input
├── obtain A_MLSD from added-noise PMF at DER_MLSD
├── calculate delta_COM and COM_MLSD_raw
├── select COM_MLSD using the DFE floor; assemble complete COMMLSDStatus
└── assign status.mlsd
```

`_run_once()` passes the active execution profile. A direct call without
`run_cfg` uses `cfg.execution.single_run`; a set `pmf_dy_override` directly
selects the PMF voltage step for added-noise calibration, while final-PMF
`keep_mass` remains 1.0.

## Added-noise evaluation

For one non-negative `g_an`, `evaluate_delta_com_an()` currently:

1. scales the stored post-FFE receiver-noise PSD to create `S_an`;
2. combines the existing Gaussian sigma with the added-noise sigma;
3. builds a replacement Gaussian PMF;
4. recombines the stored DFE `p_ISI`, `p_XT`, `p_DD`, and `p_qn` with that Gaussian PMF;
5. compares the configured-error-ratio quantile with the DFE baseline;
6. returns the temporary added-noise penalty and diagnostic scalars.

The existing quantization PMF is retained. Its ADC range is not recomputed during added-noise calibration.

## Added-noise solver and convergence history

```text
solve_g_an(...)
├── evaluate baseline at g_an=0
├── return if residual is within tolerance
├── bracket target
│   ├── start at g_an=1
│   └── double until target is crossed
├── bisect bracket
└── return when absolute dB residual <= cvg_th
```

Each observation is appended to `iteration_history` with phase `baseline`, `bracket`, or `bisection`.

The solver enforces non-negative `g_an`, non-decreasing added-noise penalty during bracketing/bisection, a finite positive quantile amplitude, convergence within the iteration budget, and a finite residual.

## MLSD PSD and autocorrelation

`build_mlsd_noise()` constructs the MLSD-specific PSD objects on the one run-level grid, following Eq. 178A-54:

```text
selected pre-DTE S_total (= Eq. 178A-15 S_n)
  -> filter directly by |H_rxffe|² on cfg.link.theta
h_ISI and sigma_X²/fb -> S_isi (two-sided spec density converted to one-sided)
S_n_filtered + S_an + S_isi -> S_ni
S_ni -> R_ni
```

The block returns transient `COMMLSDNoiseStatus`; the top-level stage later copies its `S_isi`, `S_ni`, and `R_ni` into the complete `COMMLSDStatus`. These detector quantities do not belong to the physical impairment status.

The method requires pre-DTE `S_n`, `S_an`, `h_ISI`, and `H_rxffe` to share the complete theta grid and `fb` (`rtol=1e-12`, `atol=1e-15` for theta); COM-produced objects retain the same `LinkConfig` reference. The post-FFE reporting `S_total` is not substituted for Eq. 178A-15 `S_n`, because its ADC quantization term is calculated independently. For `S_isi`, interior rFFT bins are doubled while DC and Nyquist are not; `R_isi[0] = sigma_X² sum(h_ISI[n]²)` is the Parseval check.

## Truncated DER calculation

`calculate_der_mlsd(p_an, R_ni, *, L, As, b_lim_1, trunc_len)`:

- validates PAM order, signal amplitude, first feedback coefficient, truncation length, added-noise PMF, and autocorrelation length;
- builds `p_1 = conv(p_an, scale(p_an, +b_lim_1))` for Eq. 178A-52, then repeatedly convolves `scale(p_an, 1-b_lim_1)` for Eq. 178A-53; `scale_x()` preserves probability mass while representing the PDF's `1/|scale|` factor;
- evaluates one weighted detector-error contribution for each `j=1..trunc_len`;
- returns the contribution vector `der_by_j` and its sum `DER_MLSD` without modifying either input.

The intermediate PMF recurrence remains local to the function. The top-level flow stores only the contribution vector and total DER in the completed status. The Eq. 178A-52 positive scaling is covered by an asymmetric synthetic PMF; a symmetric fixed reference PMF alone cannot detect its sign.

This is the current implementation of the source-cited Eq. 178A-48 through Eq. 178A-53 DER flow. Eq. 178A-52's scaling sign has a focused check; the other DER details still require independent mathematical review.

## Final MLSD result

After obtaining `DER_MLSD`, the stage evaluates the added-noise PMF at that error ratio to produce `A_MLSD = -P_an^{-1}(DER_MLSD)`. Eq. 178A-47 uses the signal amplitude `A_s` in the increment:

```text
delta_COM = 20 log10(A_MLSD / A_s)
COM_MLSD_raw = COM_DFE + delta_COM
COM_MLSD = max(COM_DFE, COM_MLSD_raw)
```

The denominator is `A_s`, not the DFE noise/interference quantile `A_ni`; the latter already appears in `COM_DFE = 20 log10(A_s / A_ni)`. The stage stores:

- `delta_COM`;
- `COM_MLSD_raw` relative to the DFE baseline;
- `COM_MLSD`, selected as the greater of DFE COM and the raw MLSD result in the current implementation.

`COMStatus.final_COM` prefers `COM_MLSD` when available and otherwise returns DFE COM.

For the fixed phase=23, FFE 6/15/87 validation candidate after the Eq. 178A-54 correction, `A_s=0.31666666666666665 V`, `A_ni=0.27518 V`, `A_MLSD=0.3448300000000002 V`, `COM_DFE=1.219709685032426 dB`, and `DER_MLSD=0.0008488189507241757`. Eq. 178A-47 gives `delta_COM=0.7400538316518406 dB` and `COM_MLSD=1.9597635166842666 dB`. This is an equation-level fixed-candidate check, not a claim of final SiCoPR equivalence.

## Produced status

```text
COMMLSDStatus
├── added_noise: COMAddedNoiseStatus
│   ├── g_an
│   ├── S_an
│   ├── sigma_an
│   ├── p_an
│   ├── delta_com_an_temp
│   ├── target_delta_com_an
│   ├── residual_dB
│   ├── iterations
│   ├── sigma_added
│   ├── A_ref
│   ├── A_an
│   └── iteration_history[]
│       └── COMAddedNoiseIterationStatus
│           ├── iteration
│           ├── phase
│           ├── g_an
│           ├── sigma_added
│           ├── sigma_an
│           ├── A_an
│           ├── delta_com_an_temp
│           └── residual_dB
├── S_isi / sigma_isi
├── S_qn / sigma_qn              # 本次 MLSD 實際使用的 quantization PSD
├── S_ni / sigma_ni
├── R_ni
├── der_by_j
├── DER_MLSD_raw_sequence
├── DER_MLSD
├── DER_MLSD_reported
├── A_MLSD
├── delta_COM
├── COM_MLSD_raw
└── COM_MLSD
```

The complete dataclass lifecycle is defined in [Status tree](../status_tree.md).

## Failure conditions

The stage rejects or propagates errors for these conditions:

- MLSD is disabled or its target is unresolved;
- selected DTE does not have exactly one feedback coefficient;
- DFE PMF, post-FFE impairment, `A_ni`, or DFE COM is incomplete/invalid;
- PMF grid spacing differs between the DFE result and resolved final config;
- added-noise target, convergence tolerance, or iteration budget is invalid;
- added-noise penalty is non-monotonic or cannot be bracketed/converged;
- pre-DTE `S_n`, `S_an`, or `h_ISI` does not share the run-level post-FFE grid;
- `R_ni` is missing, too short, complex beyond tolerance, non-finite, or non-positive at lag zero;
- PAM order, `As`, `b_lim[0]`, or `trunc_len` is invalid;
- a DER contribution, total DER, or inverse-CDF amplitude is invalid.

## Reporting consumers

The MLSD report currently produces up to five core views:

1. DFE COM, raw MLSD COM, and selected MLSD COM comparison;
2. per-sequence-length DER contributions and cumulative convergence;
3. receiver, added, ISI, and combined MLSD noise PSDs;
4. DFE baseline versus added-noise PMF/CDF with amplitude markers;
5. added-noise solver trace from `iteration_history`.

Reporting reads `status.pmf` and `status.mlsd`; it does not rerun the added-noise or DER solvers.

Final-search CSV stores DFE and selected final COM scalars but intentionally does not expand iteration history or every MLSD diagnostic field.

## Validation evidence and tolerance

已有 focused automated tests：`test_com_model_178A_mlsd_noise.py` 驗 Eq. 178A-54
的 pre-FFE source、one-sided ISI folding、PSD sum 與 Parseval；
`test_com_model_178A_mlsd_eq47.py` 驗 Eq. 178A-47 的 `A_s` 分母與 DFE floor；
`test_com_model_178A_mlsd_flow.py` 驗 Eq. 178A-52 的正號及 DER block 不修改
輸入。這些是局部不變量，不能取代下列 end-to-end／逐式驗收。

Required validation remains:

1. `evaluate_delta_com_an()` against independent fixed-PMF calculations;
2. bracket and bisection convergence, including zero-target and failure cases;
3. iteration-history values and phase labels;
4. `S_isi`, `S_ni`, and `R_ni` against an accepted reference;
5. each `der_by_j` contribution and truncated sum;
6. `A_MLSD`, raw delta, DFE floor, and final COM;
7. multiple `trunc_len`, PAM order, and valid feedback-coefficient cases;
8. explicit numerical tolerances and a fixed golden MLSD case.

TC-024 已完成固定 Akinwale reference case：`main_tap_white` 正式 run 的
`COM_MLSD=2.895898684873246 dB`，對 SiCoPR 差 `-1.29e-14 dB`。跨 PAM
order／跨 case 驗證仍待擴充。

## Known limitations and unresolved questions

- The project currently supports MLSD only with `N_b=1`.
- Added-noise solver tolerance and iteration budget are internal defaults, not explicit config/policy fields.
- `minimum_com_limit` is used as a fallback added-noise target; the reference justification for that fallback must remain traceable in config documentation and future validation.
- The implemented final floor at DFE COM and all source-cited equations require independent comparison with the accepted 178A reference.
- MLSD can be significantly more expensive because each added-noise iteration rebuilds/convolves PMFs and the DER stage grows the sequence-length PMF recurrence through `trunc_len`.
