# SiCoPR Akinwale VendorX 178A conversion

This case uses the public SiCoPR Akinwale VendorX example workbook and the exact IEEE 802.3dj channel files verified by SHA-256. Its channels sheet enables the victim plus 3 FEXT and 2 NEXT aggressors, matching the published with-crosstalk condition.

Reference files and provenance are indexed in `reference_data/COM_channel_data/CR/akinwale_3dj_02_2311/REFERENCE_SET.md`. Published target COM is 2.8958986848732575 dB (SiCoPR) and 2.8958986848732593 dB (COM Octave); these are reference values, not a result from this project model.

The source specifies port order `[1,3,2,4]`, `R_0=46.25 Ohm`, and selected-profile TX/RX `R_d=46.25 Ohm`; the project workbook uses zero-based `0,2,1,3`. Runtime `COMChannelConfig` derives both endpoint reflection coefficients as zero from these resistances. Gamma is not a project input.

This folder contains a project-config draft for the with-crosstalk case only. The no-crosstalk expected results are preserved in the reference data; a separate channel selection/config would be needed to reproduce that condition. No project COM run has been made.
