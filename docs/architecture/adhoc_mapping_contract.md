# Ad Hoc mapping and GUI contract

This document owns external-source interpretation and conversion review. The
executable field registry is `src/serdes_coding/io/conversion/mapping_rules.py`.
The [field table](adhoc_mapping_fields.md) lists every mapping target. Runtime
owners remain documented in each version's config tree and Excel adapter.

## Boundaries

- Source-format ID identifies a parser layout/revision, not the supplier or storage path.
- Original workbooks stay in `reference_data/COM_adhoc_config/<source_id>/`.
- Templates are `cases/_templates/<version>/config.xlsx`. They supply the fixed schema and explicit project-policy defaults.
- Output is `cases/<case_id>/<version>/config.xlsx`. Case ID equals folder name.
- Channel files remain in `reference_data/COM_channel_data/` and are referenced, never copied.
- Case metadata, channel selection, project policy, and single-run baselines are separate from source mapping.
- Source search ranges populate search_config. Fixed single-run values c_m2/c_m1/c_1 and the two CTLE gains start at the approved zero baseline and remain editable separately.

## Outcomes and provenance

The mapping view has exactly three outcomes: `success`, `fail`, `empty`.
`empty` means a documented optional input whose adopted value is None. Missing
required source values, ambiguous values, invalid data, or missing formula caches
produce per-field failure without aborting the rest of the mapping table.

Acquisition method is a separate attribute: direct, converted, derived, reduced.
A manual edit is another attribute, not a fourth outcome. Preserve the original
source value/location/unit, calculated value, original failure, and adopted value.
Conditional activation is separate provenance: for example, `MLSE` may determine
whether `N_tc` is required, but it must never be displayed as the source of
`N_tc`. Audit records store the condition key/cell/value independently from the
target parameter's source key/cell/value.
Numeric/type validation occurs during review; both versioned runtime and search
config adapters must accept the staged workbook before it replaces the destination.
This validates configuration only, not numerical equivalence to external COM.

Opening a project workbook without mapping audit does not establish successful
source mapping. Display “source not recorded” as provenance information. Validate
its adopted values against the same requiredness rules before saving.

Case provenance is explicit. `case_id` is a user-entered case identity;
`source_config` records the original Ad Hoc workbook path; and `source_note`
records the parser format ID and source SHA-256. These fields must not claim to
have been retained from the project template.

## Source interpretation decisions

Evidence checked: local IEEE COM MATLAB release `com_ieee8023_4p14p0.m`, SHA-256
`ee5fd5ec1323f5779a818ef234d9fd32222348da43281a3e6ec4758c567c2f21`.

| Item | Rule | Evidence / authority |
|---|---|---|
| N_tc / trunc | Prefer explicit N_tc, otherwise explicit trunc. Required with MLSE enabled; never synthesize 128. | MATLAB lines 9827–9828 establish alias precedence; project user rejects MATLAB's default. |
| add_rx_noise | Map to delta_com_an; absent stays None. Runtime owns the minimum_com_limit fallback. | MATLAB line 9819 and delta_COM_an assignment in the MLSE calculation. |
| minimum_com_limit | COM Pass threshold, required when MLSE enabled. | Approved project conditional rule. |
| Tr, fr, 178A f_p3, N_qb, P_qc | Required. f_p3 comes from f_HP_PZ; frequency conversion uses GHz to Hz. | Approved mapping decision; ADC pair must both be supplied. |
| PKG_NAME | TX and RX profile selection, independently visible in GUI. | Source profile mechanism. |
| z_p select | A single index auto-selects; multiple indices require a user choice. Source rows are TL segments, columns are testcases. | Source package testcase processing. |
| NEXT | NEXT lengths and A_ne use RX profile. NEXT TX TL coefficients use TX profile. | MATLAB rx_fields at line 10225; make_full_pkg swaps gamma/tau by TX/RX type at lines 8192–8208. |
| include_die | A make_full_pkg function argument, defaulting to 1. False zeroes die C/L/bump C. It is not a discovered workbook parameter. | MATLAB lines 8181–8185 and 8218–8223. |
| PKG_Null | Read the selected zero-valued profile. Do not infer whole-package bypass. | Profile values; device termination is a separate model part. |
| 93A reduction | Maximum selected-side C_d/L_s and impedance; maximum selected testcase TL length, one segment, z_p2=None. Record reduction, never claim mathematical equivalence. | Explicit user-approved provisional 178A→93A fallback. |
| TL coefficients | gamma_0/a1/a2 are distinct entries, tau is separate. Do not max these together. | Native TL model and completed 93A coefficient contract. |
| 93A DFE | Build b_max and b_min as first-tap value plus N_b-1 remaining-tap limits; adapter passes lower limits to existing COMDFEConfig.bb_min. | Existing runtime supports vector bounds; no kernel change. |

With MLSE disabled, its three dependent fields may remain empty. With MLSE on,
only delta_com_an is optional. Package/partial-host inputs currently required by
the runtime schema remain required even when a part is inactive: the converter
does not invent zero/default values for absent data to bypass that boundary.

## Unsupported and excluded source behavior

Nonzero unsupported TX taps block export. Active Include PCB or MLSE in a 93A
conversion blocks export because that project schema has no corresponding feature.
Unknown source keys block export until a mapping or explicit exclusion is reviewed.
The source format's recognized reporting/TDR/ERL/ICN and execution controls are
listed explicitly in `SOURCE_EXTERNAL_CONTROLS`; they do not override project
execution policy. ADC/floating-FFE fields are version-native to 178A. Choosing 93A
does not promise the same receiver capability as 178A.

Port Order remains a channel-file interpretation input. `R_0`, TX-profile
`R_d_tx`, and RX-profile `R_d_rx` are required intrinsic mappings. The
project-to-runtime adapter constructs `COMChannelConfig` from them, and its
`__post_init__()` derives source/load reflection coefficients. Gamma is not a
project or GUI input. Every package `R0` remains mapped from the same Ad Hoc
`R_0`; the adapter rejects package/channel reference-impedance mismatches.

## Deferred core contract

No new device-termination/device-package enable switch is introduced by this GUI
change. A future core contract must define separate bypass behavior, exact builder
functions, reference equations and intermediate S-parameter tests before changing
protected model behavior. Partial-host enable continues using the existing model.

## Validation and export

Source mapping errors block conversion export; supplying a valid manual adopted
value can resolve a target missing-value error while preserving source failure in
the audit. Unsupported source behavior is a source-level error, not silently
resolved by overriding an unrelated target field.

Exactly one enabled `victim[0]` is required. NEXT/FEXT rows use one-based indices
(`NEXT[1..N]`, `FEXT[1..N]`) and their counts are editable, including zero. All enabled channel files must exist. Current runtime requires common
port order/R0/reflection settings across enabled rows; the runtime adapter enforces
this. Removed rows and explicitly cleared values must be removed in the workbook.

Validation stages a temporary workbook and constructs config objects, then uses
atomic replacement for config.xlsx. Failed validation leaves an existing workbook
untouched. Audit sidecars retain original source and edit information. Existing
project save does not require the Ad Hoc source file to be available.

Tests: `tests/test_mapping_contract.py`, `tests/test_93a_package_tl_config.py`,
`tests/test_conversion_status_view.py`, and `tests/test_adhoc_format_detection.py`.
