# 178A full search — GitHub Actions run 29

Status: verified search artifact evidence for the Akinwale SiCoPR-alignment case.

## Execution identity

| Item | Value |
|---|---|
| GitHub run | `38745800222` |
| Workflow result | 236/236 jobs successful |
| Commit | `95f7f067c300a2616886092ce8098fb685f7821e` |
| Git dirty state | `false` |
| Case | `sicopr_akinwale_vendorx_22db/178A` |
| Execution profile | `sicopr_reference_v1` |
| Sweep target | `mse` |
| Final target | `full` |
| Candidates | 232,848 |
| Successful sweep rows | 188,601 |
| Infeasible TX FFE rows | 44,247 |
| Runtime errors | 0 |
| Final candidates | 10 |
| Grid overflows | 0 |
| Final artifact | `full-search-final-sicopr_akinwale_vendorx_22db`, artifact `12018068244` |
| Resolved config SHA-256 | `227cae152dffa6d975bcd8cd9016501251386e05dd025658329e69a51f402102` |

The downloaded artifact passed `scripts/run_full_search_178A.py verify`: all
232,848 partial rows were present, the final set contained exactly the selected
top 10 MSE-ranked candidates, and 530 PNG files matched their manifests.

## Best MSE-ranked candidate

```text
search_index = 28969
c_m2 = 0
c_m1 = 0
c_1  = 0
g_1  = -19 dB
g_2  = -3 dB
search_sweep MSE = 0.006361523694460796 V^2
search_final exact-phase MSE = 0.006204188571809303 V^2
COM_DFE = 1.514414278762367 dB
delta_COM = 1.3488568555276164 dB
COM_MLSD = 2.8632711342899833 dB
```

The sweep MSE and final MSE differ because candidate ranking uses the configured
`simplified` floating mode and `coarse_fine` phase sweep, while the full final
rerun uses `spec-defined` floating mode and `each_phase`. The artifact records
both execution boundaries.

## Reference comparison boundary

The published SiCoPR value `2.8958986848732575 dB` belongs to the fixed reference
settings (`g_1=-20 dB`, `g_2=-2 dB`, zero TX precursor/postcursor taps). The
project production path reproduces that fixed candidate separately to numerical
roundoff. Run 29 instead reports the minimum-MSE candidate over the workbook
search space; its COM_MLSD is `0.0326275505832742 dB` below the published fixed
candidate. This is a search-result comparison, not a regression of the fixed
golden.
