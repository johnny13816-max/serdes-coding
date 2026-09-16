# COM Case Directory Contract

`cases/` stores project-owned COM simulation cases. Each case is intended to be self-contained enough to reproduce one COM study setup.

## Case Layout

```text
cases/<case_id>/
  config/
    config_93A.xlsx
    config_178A.xlsx
  channels/
    victim_thru.s4p
    next_*.s4p
    fext_*.s4p
  report/
    93A/
      single_run/
      search_run/
    178A/
      single_run/
      search_run/
```

## Workbook Contract

Both `config_93A.xlsx` and `config_178A.xlsx` use the project workbook shape:

- `fixed_config`: fixed COM parameters, grouped by the COMConfig dataclass fields.
- `search_config`: optional search-space parameters for COMSearchConfig.
- `channels`: victim/NEXT/FEXT S4P paths and port-order settings.

The channel paths may point to files inside this case's `channels/` folder or to a stable path under `reference_data/`.

## Report Contract

Run outputs belong to the same case folder:

- `report/93A/single_run`: one full 93A debug/study run.
- `report/93A/search_run`: 93A search run and best candidate result.
- `report/178A/single_run`: one 178A debug/study run.
- `report/178A/search_run`: 178A search run and best candidate result.

Do not use the top-level `reports/` folder for new case-owned studies.
