# 178A Project-Config Template

`config.xlsx` is the fixed schema and reviewed project-default workbook used by the Ad Hoc-to-project-config GUI. The GUI resolves it from this folder automatically; users do not select a base workbook.

The template is not a runnable case. It intentionally has blank case identity, source-specific intrinsic values, and channel S4P paths. The conversion GUI fills values supported by the selected registered Ad Hoc parser; users review fallback/manual fields, enter a case ID, and select the victim, aggregated NEXT, and aggregated FEXT S4P files in the `channels` sheet before using the exported workbook. Output is fixed at `cases/<case_id>/178A/config.xlsx`.

Execution profiles and project-owned numerical policies are retained as defaults. Review them for the intended workflow before running a case.

The shared PMF grid defaults are initialized to `dy_rel_As=0.001`,
`dy_abs_max=1e-5`, `tap_rel_As=0.001`, and `gaussian_n_sigma=8`, matching the
shared `COMPMFConfig` defaults. They are project policy, not source Ad Hoc
values.
