# 93A Project-Config Template

`config.xlsx` is the fixed 93A project-config schema and default-policy workbook. It is selected automatically when 93A is chosen in the conversion GUI.

The template is not a runnable case. It has blank case identity, source-derived model values, search ranges, and channel S4P paths. The conversion GUI can map supported fields from the registered IEEE 802.3dj D3p2 200G CAKR 178 Ad Hoc workbook into this 93A schema. Values that cannot be represented faithfully remain marked unsupported and block export until reviewed.

The fixed single-run baseline for `c_m2`, `c_m1`, `c_1`, `g_DC`, and `g_DC2`
is zero. Ad Hoc search ranges are mapped independently into `search_config`.

Project PMF and missing-DC policy settings are retained as template defaults. Set the case ID and select the required channel files before exporting to `cases/<case_id>/93A/config.xlsx`.
