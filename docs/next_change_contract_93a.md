# 93A alignment and fallback discussion draft

Status: discussion preparation only, 2026-09-15. No runtime/workbook/workflow changes in this step. Today's 178A full search remains independent.

## Already decided

Mirror the 178A operation design: canonical case/model config.xlsx, channel references in its channels sheet, intrinsic versus policy, single_run/search_run, per-stage execution policies, manual %run entry, partial/merge/final/report boundaries and explicit final failures. Port the shared operating mechanisms; keep model-specific equations and parameter semantics. Do not ask again about these agreed boundaries.

## Reference-first rule (user correction, 2026-09-15)

The items below are an investigation checklist, NOT questions for the user. Resolve them first using the applicable COM ad hoc config, its keyword definitions and the matching reference implementation. Establish the source version and selected package/receiver case before treating values as authoritative. Settings-sheet values, missing-key defaults and keyword descriptions must be distinguished; keyword-table entries alone do not establish runtime fallback behavior.

For each item, record: source file/version and cell or reference-code location; supplied value; missing-value behavior; units; project mapping; runtime field; implementation support. Use source-defined behavior directly. If the reference defines behavior but this project lacks it, classify that as an implementation gap, not permission to invent a fallback. Only genuinely unresolved source behavior, conflicting definitions or a required departure from reference behavior should be brought to the user.

Do not assume DFE-only, omitted ADC qnoise, collapsed packages or a dropped CTLE pole are approved fallbacks. Earlier suggestions below are provisional and must be superseded by the reference findings.

## Current implementation evidence / reference investigation checklist

1. Package representation: 178A uses device_term vectors, device_pkg vectors and propagation parameters, and partial_host; 93A uses C_d/L_s/C_b/C_p, z_p/z_p2 and Z_c/Z_c2 under its own package equations. Decide what comparable 93A package is acceptable for this case. Prefer explicit reference-backed 93A parameters. Do not silently sum ladder components, remove partial_host, or call two different package models equivalent. Record any accepted approximation and its validity range.
2. CTLE representation: 178A uses g_1/g_2, f_z1/f_z2 and optional f_p3; 93A runtime uses g_DC/g_DC2, f_z/f_LF, f_p1/f_p2. Gain-name translation alone does not establish transfer-function equivalence. Compare the implemented formulas, propose the exact supported mapping, and identify any extra pole that cannot be represented. Decide whether the comparison uses a common representable response or native model settings with the difference reported.
3. Receiver equalization: 178A MMSE DTE includes fixed/floating RxFFE and DFE bounds; 93A implements DFE (including optional floating DFE). Floating DFE is not floating RxFFE. Propose native 93A DFE configuration and list what is omitted from the 178A receiver; do not claim an equivalent receiver or transfer coefficients without evidence.
4. ADC quantization: 93A COMImpairmentConfig declares N_qb/P_qc/quantization_vqc_method, but searches of the model show declarations/validation only; its project reader does not populate N_qb/P_qc. Thus field presence is not evidence of active ADC qnoise. Decide whether this comparison explicitly excludes ADC qnoise for 93A, or whether adding ADC qnoise is required before the comparison. No silent enabled-looking inert fields.
5. MLSD: 178A has a dedicated MLSD stage; 93A currently has no corresponding implementation. Native DFE-only 93A is the proposed fallback. Record whether the reported 178A comparison value is its DFE baseline or MLSD result; unsupported requests must be explicit.
6. Execution policy support: mirror the per-stage organization, but list which 178A options are meaningful for 93A. Prefer rejecting explicitly requested unsupported options instead of silently ignoring them. Preserve native 93A FOM ranking; 178A MSE ranking is not a replacement metric. Policy fallback and model/receiver fallback must be recorded separately.

## Mechanical defects to repair without reopening design decisions

- The 93A project reader passes f_z1/f_z2/f_p3 to COMFilterConfig, but the runtime dataclass defines f_z/f_LF and has no f_p3. Correct reader/schema mapping after the CTLE mapping is established; this is a code defect, not a valid fallback.
- The reader only constructs N_b/b_max for COMDFEConfig, omitting its supported optional floating DFE and per-tap bound fields. Wire intended project fields to their existing runtime fields; preserve documented COMConfig defaults and validate incomplete enabled configurations.
- missing_dc_policy is already read by the shared channel reader and passed to both model paths. Keep the same selected policy and source S4P inputs for paired cases; do not reintroduce implicit hold or disable packages to bypass input problems.
- Shared physical units and PMF semantics follow existing model/reference definitions. Do not invent defaults or rescale units based on labels alone.

## Subsequent contracts after fallback decisions

A. Reference -> project -> runtime mapping and fallback record: source field, target field, units, exact/approximate/unsupported status, trigger, chosen value, rationale and expected comparison impact. Unsupported required settings fail before a search.
B. 93A operation alignment: manual entry, workbook execution policies, file-backed partial/merge/final, native FOM selection, plots and artifact verification. Use the agreed 178A operating pattern.
C. Paired-case validation: same channel files and hash evidence, each model's resolved config and explicit fallback list; single run first, then small search. Do not launch a 93A full search until the preceding boundaries are accepted.


## Initial source inventory

Found local candidate source: reference_data/COM_channel_data/C2M/mellitz_3dj_02_2409/mellitz_3dj_COM_01a_240625.xlsx, with COM_Settings and keywords_20-Feb-2024 sheets. Inspected both: package selections/vectors, g_DC/g_DC_HP and pole/zero definitions, RxFFE and floating-tap controls are present. This is a 2024 development workbook; applicability to the intended 93A reference and the later 178A source still needs verification. It must not silently replace a newer agreed reference.

Next deliverable: a source-backed mapping/fallback table split into (1) resolved by reference, (2) project implementation gaps, and (3) unresolved source questions. No runtime changes in this preparation stage.
