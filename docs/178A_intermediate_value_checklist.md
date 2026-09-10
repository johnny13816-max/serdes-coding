# Annex 178A Intermediate-Value Checklist

日期：2026-09-10

目的：在外部 Python COM / Matlab / Octave reference result 到手前，先定義要比對的 intermediate values、單位、normalization、alignment reference 與目前可接受的 evidence 型態。這份文件不是 compliance claim，只是後續 validation intake checklist。

## Claim Boundary

- 這份 checklist 只支援 internal validation planning。
- 未取得外部 reference output 前，不宣稱 IEEE COM compliance。
- 即使取得 Hansel / Rich 提供的 public-shareable Python COM output，也要先記錄其 collateral status、commit/version、config source 與使用方式，再決定可支援的 claim。
- 若 reference script 不是 IEEE 802.3 collateral，只能稱為 public/shared reference implementation evidence，不能稱為 official IEEE golden result。

## Reference Result Intake Metadata

拿到任何外部 result 時，先填這一段；沒有 metadata 的數值不應直接拿來對 final COM。

| Item | Required? | What to Record |
| --- | --- | --- |
| reference source | must | Matlab COM, Octave branch, Python COM script, or public report |
| maintainer / author | must | person or organization named by source |
| repository / release URL | must | public URL if available |
| commit / version / date | must | exact commit hash, tag, file date, or release date |
| collateral status | must | IEEE collateral, non-IEEE public script, meeting material, personal fork, etc. |
| command / run mode | must | headless command, config path, display disabled/enabled |
| config source | must | workbook/mat/csv/template name and version |
| channel source | must | exact S-parameter file set and path mapping |
| package/profile source | must | package/profile/config identity |
| expected output type | must | final COM only, intermediate log, CSV, report, plots |
| known limitations | must | missing display, config in flux, private assumptions, unsupported blocks |

## Comparison Levels

| Level | Purpose | Minimum Evidence |
| --- | --- | --- |
| L0 source identity | confirm same problem is being solved | same config, channel files, package/profile, search space |
| L1 path construction | confirm signal path setup | S-parameter count, victim/NEXT/FEXT mapping, package cascade, frequency grid |
| L2 sampling / DTE | confirm phase and equalizer solution | selected `ts`, `pos`, MSE, DTE coefficients |
| L3 impairment | confirm noise/jitter/XT decomposition | sigmas, PSD integration, post-FFE components |
| L4 PMF / COM | confirm final metric construction | `A_s`, `A_ni`, PMF/CDF tail, DER/COM |
| L5 search outcome | confirm optimization behavior | candidate manifest, top-K, best candidate, final rerun result |

## L0 Source Identity

| Field | Unit / Convention | Current Project Value / Evidence | Needed Reference Evidence |
| --- | --- | --- | --- |
| case id | text | `c2m_8023dj_4p13p0_50mm` | exact same case or documented equivalent |
| spec/profile | text | 802.3dj Annex 178A-inspired C2M flow | reference profile identity |
| config file | file path/version | project workbook/config under case root | exact external config file |
| victim channel | file/path mapping | C2M 50 mm victim S-parameter mapping in case config | same S-parameter filename and port mapping |
| NEXT/FEXT channels | file/path mapping | enabled aggressor mapping in case config | same aggressor set and ordering |
| TX/RX package | profile/parameters | project package profile in config | same package/profile source |
| signaling level | V or normalized | voltage-equivalent project convention | external amplitude convention |
| search variables | value grid | `c_m2`, `c_m1`, `c_1`, `g_1`, `g_2` manifest | external search grid |
| phase sweep policy | text | `each_phase` or `coarse_fine` | external phase policy |

## L1 Path Construction

| Value | Unit / Shape | Why It Matters | Needed Evidence |
| --- | --- | --- | --- |
| frequency grid | Hz, length, df | catches interpolation/extrapolation mismatch | `f_min`, `f_max`, `df`, number of points |
| victim `S_ch` | Sdd 2-port | confirms channel identity and port convention | insertion loss / Sdd matrix summary |
| package `S_tx`, `S_rx` | Sdd 2-port | catches package/profile mismatch | package transfer or S-parameter summary |
| cascaded `S_all` | Sdd 2-port | validates TX package + channel + RX package cascade | Sdd21 / IL curve or sample values |
| `H_21` impulse | V/V discrete IR | catches IFFT/grid/causality differences | impulse length, peak location, cursor sample |
| pulse response | V or normalized | first major RX-side observable | pulse/SBR sample values and alignment rule |
| crosstalk paths | V/V discrete IR | validates NEXT/FEXT inclusion and ordering | count, type, selected path summaries |

## L2 Sampling / MMSE-DTE

| Value | Unit / Convention | Current Project Field | Needed Reference Evidence |
| --- | --- | --- | --- |
| samples per UI | samples/UI | `LinkConfig` / run config | same OSR/per-UI convention |
| phase candidates | integer `pos` | `run.mse_by_pos` index | phase grid or selected phase log |
| selected time index | sample index | `dte.ts` / search CSV `ts` | selected `ts` |
| selected phase | sample phase index | `dte.pos` / search CSV `pos` | selected `pos` |
| MSE by phase | V^2 or normalized project MSE | `run.mse_by_pos` | per-phase MSE vector if available |
| final DTE MSE | V^2 or normalized project MSE | `dte.mse`, search CSV `mse` | MSE and definition |
| MSE dB | dB | search CSV `mse_dB` | reference MSE dB or formula |
| feed-forward weights | dimensionless filter taps | `dte.w` / `w_lim` | FFE/MMSE weights |
| DFE coefficients | dimensionless taps | `dte.b`, `dte.b_lim` | DFE taps before/after limiting |
| clipped tap status | boolean/list | compare `b` vs `b_lim` | tap limit report |
| residual ISI vector | V or normalized | post-DTE/post-FFE impairment stage | residual cursor/tail vector |

Minimum useful external data for this level: selected `ts`, selected `pos`, MSE, and DFE coefficients. Without these, a final COM mismatch is hard to debug.

## L3 Impairment / PSD / Noise

| Value | Unit / Convention | Current Project Field | Needed Reference Evidence |
| --- | --- | --- | --- |
| `sigma_X` | V or normalized symbol sigma | `COMPSDStatus.sigma_X` | amplitude normalization source |
| receiver noise sigma | V rms | `sigma_rn` | receiver noise model output |
| crosstalk sigma | V rms | `sigma_xn` | XT PSD integration result |
| TX noise sigma | V rms | `sigma_tn` | TX noise model output |
| jitter noise sigma | V rms | `sigma_jn` | jitter PSD / derivative convention |
| ADC quantization sigma | V rms | `sigma_qn` | quantization noise model output |
| total Gaussian sigma | V rms | `sigma_total` / `sigma_gn_adc` | Gaussian composition rule |
| ISI sigma | V rms | `sigma_ISI` | residual ISI contribution |
| PSD theta grid | rad/sample | `SampledPSD.theta` | one-sided/two-sided and theta convention |
| PSD integration rule | V^2 | `SampledPSD` integration | integration normalization |

Critical checks:

- Distinguish input-referred voltage from normalized symbol-domain quantities.
- Record whether jitter is modeled as time shift, equivalent voltage noise, or post-filter PSD.
- Record whether `sigma_total` includes or excludes residual ISI and quantization.

## L4 PMF / Final COM

| Value | Unit / Convention | Current Project Field | Needed Reference Evidence |
| --- | --- | --- | --- |
| signal amplitude `A_s` | V | search helper / final status | exact `A_s` formula and value |
| non-ISI noise amplitude `A_ni` | V | `pmf.A_ni` | PMF/CDF threshold result |
| PMF grid `dy` | V/bin | `pmf.dy` | PMF resolution |
| ISI PMF | probability mass | `pmf.p_ISI` | distribution or key moments |
| Gaussian PMF | probability mass | `pmf.p_G` | distribution or sigma |
| DD jitter PMF | probability mass | `pmf.p_DD` | DD amplitude/convolution rule |
| XT PMF | probability mass | `pmf.p_XT` | XT distribution |
| quantization PMF | probability mass | `pmf.p_qn` | ADC quantization convention |
| combined CDF | probability | `pmf.p_combined` | tail probability curve or quantile |
| target DER | probability | config/report | target used by COM |
| final COM | dB | `pmf.COM` / `COMStatus.final_COM` / `COM_dB` | final reported COM |

Formula boundary to verify when reference data arrives:

```text
COM = 20 * log10(A_s / A_ni)
```

Only use this formula after confirming the reference uses the same `A_s`, `A_ni`, and voltage convention.

## L5 Search Outcome

| Value | Current Evidence | Needed Reference Evidence |
| --- | --- | --- |
| candidate manifest | project artifact `full_search_manifest.csv` | external candidate grid or selected candidate parameters |
| group plan | project artifact `group_plan.csv` | not required unless external tool has same batch flow |
| partial result rows | project artifact `merged_partial_results.csv` | top candidates or full candidate CSV |
| top-K final rows | project artifact `full_search_results.csv` | top-K report if available |
| best candidate | `search_index=203642`, `c_m2=0.02`, `c_m1=0`, `c_1=0`, `g_1=-14`, `g_2=-1` for current internal baseline | external best candidate and settings |
| final COM | `4.2282976469690245 dB` for current internal baseline | external final COM |

Current internal baseline evidence:

- `each_phase` and `coarse_fine` full-search artifacts use identical manifest and group plan.
- Both produce the same top-100 ranking and same best candidate for the 50 mm C2M case.
- This is internal regression evidence only, not external reference validation.

## Tolerance Policy Draft

These tolerances are placeholders until an external reference format is known.

| Quantity | Draft Tolerance | Notes |
| --- | ---: | --- |
| exact identity fields | exact match | filenames, candidate settings, enabled path counts |
| selected `pos` / `ts` | exact or explained offset | allow only documented alignment offset |
| DFE coefficients | TBD | depends on printed precision and normalization |
| MSE | TBD | compare absolute and relative error |
| sigmas | TBD | compare absolute and relative error |
| `A_s`, `A_ni` | TBD | must know voltage convention first |
| COM | TBD | do not set until reference precision is known |

Do not hide mismatches with loose tolerances. If `pos`, `ts`, gain, or normalization differ, resolve the convention before comparing final COM.

## First Comparison Procedure

1. Record reference source metadata.
2. Confirm L0 source identity before checking numeric values.
3. Compare victim path construction before crosstalk-heavy quantities.
4. Compare selected phase and DTE MSE before impairment/PMF.
5. Compare impairment sigmas before final COM.
6. Compare `A_s`, `A_ni`, and final COM last.
7. For every mismatch, classify as one of:
   - source/config mismatch;
   - unit or normalization mismatch;
   - sampling/alignment mismatch;
   - implementation difference;
   - suspected bug;
   - insufficient reference evidence.

## Open Questions For Future Reference Intake

1. Will the public Python COM script expose intermediate logs, or only final COM?
2. Will the shared script use `.mat`, workbook, CSV, or script-level configuration?
3. Does the reference phase selection report `pos`, absolute sample index, or UI offset?
4. Are signal/noise quantities printed as physical voltage, normalized voltage, or dB quantities?
5. Does the reference include search candidate results, or only one selected configuration?
