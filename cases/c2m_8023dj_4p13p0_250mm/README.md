# c2m_8023dj_4p13p0_250mm

IEEE 802.3dj 4p13p0 C2M reference case for a 250 mm host trace. The case compares the same channel set with the 93A and 178A models.

## Layout

`	ext
c2m_8023dj_4p13p0_250mm/
|-- case_manifest.yaml
|-- README.md
|-- 93A/
|   |-- config.xlsx
|   -- results/          # generated; created when a run is exported
-- 178A/
    |-- config.xlsx
    -- results/          # generated; created when a run is exported
`

The channels sheet in each workbook is the authority for channel selection. S-parameter files are stored once under eference_data/COM_channel_data/C2M/mellitz_3dj_02_2409/; they are not copied into this case folder.

Run either model through its manual entry point and select this case's matching workbook.

## Validation status

The 93A workbook loads successfully. The preserved 178A workbook has an incomplete fixed-config table and must be repaired before execution; it is retained because missing scientific parameters must not be guessed during folder cleanup.
