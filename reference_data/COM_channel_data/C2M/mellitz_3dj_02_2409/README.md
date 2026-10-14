# Mellitz 802.3dj C2M channel dataset

> **Status: external reference data.** These files are inputs and provenance;
> this directory does not define the project case layout or runtime policy.

## Local source package

The extracted files are retained with the original local archive:

```text
reference_data/COM_channel_data/C2M/mellitz_3dj_02_2409.zip
```

Companion source material in this directory:

```text
mellitz_3dj_01_2409.pdf
mellitz_3dj_COM_01a_240625.xlsx
```

Keep the original archive and companion material together until their upstream
URL, publication revision, and redistribution terms are recorded explicitly.

## Dataset contents

The extracted set contains C2M channel families for nominal 50 mm, 150 mm,
250 mm, and 500 mm host lengths. Each family currently contains:

- one through path;
- six NEXT paths;
- five FEXT paths.

The filenames retain the source naming convention, including the host length
and `max_skew_cable_module_pin_pad` description.

## Configuration ownership

The S4P files are external channel data. They do not own COM parameters,
selection, or execution behavior. For a run, the corresponding project
workbook `channels` sheet is authoritative for:

- which through, NEXT, and FEXT files are enabled;
- the resolved file paths;
- port order;
- reference impedance and termination fields.

The current C2M case workbooks translate the companion COM workbook port order
from MATLAB one-based `[1, 3, 2, 4]` to Python zero-based
`[0, 2, 1, 3]`. Verify the workbook `channels` sheet rather than inferring port
order from this README.
