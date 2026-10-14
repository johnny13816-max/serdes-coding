# Project config GUI

Start `scripts/run_config_conversion_gui.bat` at the canonical project. The BAT
uses the project's .venv and does not execute a COM model.

1. Choose New config, enter Case ID and Version, and optionally a source note.
   The corresponding version template is selected automatically. Output preview
   is `cases/<case_id>/<version>/config.xlsx`.
2. Browse an original Ad Hoc workbook under reference_data/COM_adhoc_config.
   Exact format detection loads automatically; compatible-only formats require
   explicitly selecting the parser after review. Format identity and source hash
   appear above the mapping view.
3. Confirm TX/RX profiles and choose a testcase if the source offers several.
   Changing a choice reloads all affected mappings. Unsaved edits require a
   discard confirmation before reloading.
4. Add one victim and any needed FEXT/NEXT rows using the channel editor. Select
   a row to update/remove it. The edit boxes follow the column heading order:
   kind, S4P path, port order, and Use. Confirm the port order for the selected
   dataset. `R_0`, `R_d_tx`, and `R_d_rx` are intrinsic fixed-config mappings;
   runtime derives source/load Gamma from them. No S4P files are copied.
5. Review mapping outcomes: fail needs action, empty is a permitted omission,
   success has an adopted value. Inspect source location and conversion/reduction
   details in the lower panel. A conditional controller such as MLSE is shown on
   its own Condition line and is not presented as the target field's source.
   “Edited” preserves a separate manual-edit marker.
6. Use Project policy and Single-run baseline tabs for project-owned settings.
   These are not presented as successful Ad Hoc mappings.
7. Export validates the workbook through the versioned runtime and search adapters.
   Confirm replacement if config.xlsx already exists. Correct validation errors
   in the GUI before retrying. This does not start single run or search.

For an existing config, choose Open existing config and Browse. Fields load
immediately, with policy/baseline separation and editable channels. Source audit
may be absent; “source not recorded” is not a successful source mapping claim.
Changing Case ID requires Save As. Save As may create a new canonical case folder.

Source-level unsupported-feature errors appear below the mapping table and at
export. A missing target input can be manually supplied; an unsupported source
feature cannot be silently hidden by editing a different target value.

Channel audit identity is stable across create/open/save: victim is `victim[0]`;
FEXT and NEXT rows begin at index 1.

Older 93A workbooks need the four TL coefficients per package path and b_min
added from their source before the strict adapter can accept them. This change
does not migrate or overwrite existing cases automatically.

See [mapping contract](../architecture/adhoc_mapping_contract.md) and the
[complete mapping table](../architecture/adhoc_mapping_fields.md).
