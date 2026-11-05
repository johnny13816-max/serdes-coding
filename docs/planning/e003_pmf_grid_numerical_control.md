# E-003 — PMF grid numerical-control separation

> Status: Historical / implemented and validated (2026-11-05)
>
> This is the closed implementation contract and is no longer authoritative.
> Durable behavior belongs in the
> 178A config, stage, branch-registry, and validation documents.

## Goal

Separate ADC-input and final-PMF grid controls without moving their established
resolver owners or changing PMF formulas. The existing `execution_profile`
remains the only preset selector.

## Approved config families

```text
numerical_control
├─ adc_input_pmf_grid
│  ├─ rule: relative_As | relative_As_with_cap
│  ├─ dy_rel_As
│  ├─ dy_abs_max
│  └─ dy_override
└─ final_pmf_grid
   ├─ rule: relative_As | relative_As_with_cap
   ├─ dy_rel_As
   ├─ dy_abs_max
   └─ dy_override
```

`dy_override` has highest priority. Otherwise `relative_As` resolves
`dy_rel_As*abs(As)`, and `relative_As_with_cap` resolves the minimum of that
value and `dy_abs_max`.

## Ownership and scope

```text
execution_profile
└─ effective numerical controls
   ├─ ADC-input family → _resolve_adc_input_pmf_config()
   │  ├─ pre-DTE phase/MMSE
   │  └─ selected-phase ADC-input PMF
   └─ final family → _resolve_final_com_pmf_config()
      ├─ final DFE COM
      └─ final MLSD
```

The SiCoPR reference profile resolves ADC-input `dy_override=10e-6 V` and final
`rule=relative_As` with no final override. E-004 mass retention, PMF projection,
scaling, Gaussian support, convolution, and 93A are excluded.

## Compatibility and validation

Legacy Python/workbook inputs remain readable during this family migration.
New templates and exports use canonical names and record raw/effective/profile
provenance. Focused tests cover validation, precedence, profile resolution,
workbook round-trip, and cross-domain non-leakage. The fixed SiCoPR case must
retain `COM_DFE=1.5247607834259893 dB` and final
`COM=2.895898684873246 dB` within the established tolerance.

## Closure evidence

- Focused policy/text tests: `37 passed`.
- Canonical workbook inspection: both template and SiCoPR case contain all eight
  family fields; old run-level shared grid rows and formula errors: 0.
- Fixed SiCoPR golden: `COM_DFE=1.5247607834259893 dB`, final
  `COM=2.895898684873246 dB` (unchanged).

