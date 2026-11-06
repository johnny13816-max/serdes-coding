# 178A Project-Config Template

`config.xlsx` is the fixed schema and reviewed project-default workbook used by the Ad Hoc-to-project-config GUI. The GUI resolves it from this folder automatically; users do not select a base workbook.

The template is not a runnable case. It intentionally has blank case identity, source-specific intrinsic values, and channel S4P paths. The conversion GUI fills values supported by the selected registered Ad Hoc parser; users review fallback/manual fields, enter a case ID, and select the victim, aggregated NEXT, and aggregated FEXT S4P files in the `channels` sheet before using the exported workbook. Output is fixed at `cases/<case_id>/178A/config.xlsx`.

Execution profiles and project-owned numerical policies are retained as defaults. Review them for the intended workflow before running a case.

ADC-input and final PMF grids are independent `numerical_control` families.
Each defaults to `rule=relative_As_with_cap`, `dy_rel_As=0.001`,
`dy_abs_max=1e-5`, and blank `dy_override`. The SiCoPR reference profile
resolves ADC-input `dy_override=10e-6 V` while final PMF uses `relative_As`
without an override. `tap_rel_As=0.001` remains a PMF algorithm default.
Gaussian support is an internal fixed 8σ invariant and is not a workbook control.
