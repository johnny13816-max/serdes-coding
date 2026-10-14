# SiCoPR Akinwale VendorX reference set

This folder holds one reproducible public COM example associated with SiCoPR. It is a Todd Bermensolo/IEEE public example recommended by Hansel; it is not a case result supplied by Hansel.

## Source identity

- SiCoPR repository: https://github.com/tbermen/SiCoPR
- Repository commit: `f58a1e913c6b74b1b069d6c3759acd8992b7aede`
- Example directory: `examples/akinwale_CR_22dB_VendorX/`
- Example documentation: https://github.com/tbermen/SiCoPR/blob/f58a1e913c6b74b1b069d6c3759acd8992b7aede/examples/akinwale_CR_22dB_VendorX/EXPECTED.md and https://github.com/tbermen/SiCoPR/blob/f58a1e913c6b74b1b069d6c3759acd8992b7aede/examples/akinwale_CR_22dB_VendorX/CHANNEL.md

## Local reference inputs

- Config workbook: `reference_data/COM_adhoc_config/sicopr/config_com_dj_200G_CAKR_178_PKGA_06_2_2025__Case1.xlsx`
- Original IEEE contribution ZIP: `akinwale_3dj_02_2311.zip`
- IEEE source: https://www.ieee802.org/3/dj/public/tools/CR/akinwale_3dj_02_2311.zip
- ZIP SHA-256 in this local copy: `8a3da48ac684293946f5690493e02584dbe3223ec92cc5033417727512621e95`
- Six extracted S4P files are in this directory. Their roles and expected SHA-256 values are in [CHANNEL.md](CHANNEL.md); all six were verified against that list.

## Published expected results

`reference_results/sicopr/` preserves SiCoPR's full-precision expected CSVs for both SiCoPR and COM Octave, plus `EXPECTED.md`:

- no crosstalk: SiCoPR COM `3.507002840250303 dB`; COM Octave `3.507002840250293 dB`.
- with 3 FEXT and 2 NEXT aggressors: SiCoPR COM `2.8958986848732575 dB`; COM Octave `2.8958986848732593 dB`.

The expected results are the published SiCoPR/COM-Octave results, not MATLAB per-case output. The project config integration should select all five aggressors for the crosstalk-on case; a no-crosstalk run is a separate channel selection.

## Repeatability boundary

The workbook and result files are from the pinned SiCoPR commit above. The channel S4P data is from the IEEE contribution and must match the published SHA-256 list. SiCoPR's 4p16p0/Octave provenance and run details are recorded in `reference_results/sicopr/EXPECTED.md`. No external engine was installed or run as part of this data import.
