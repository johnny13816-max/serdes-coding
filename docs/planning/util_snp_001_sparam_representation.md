# UTIL-SNP-001 — S2P/S4P representation boundary

## Status

Approved, implemented, validated, and isolated in the dedicated commit that contains this record.

## Goal

保留 raw S4P，讓 S4P→Sdd、renormalization、frequency limit 與 port mapping 成為顯式、
可追蹤的 copy-returning operations，同時維持 93A／178A 的既有 COM 數值。

## Boundary

- Utility owner: `src/serdes_coding/utilities/sparam.py`
- 178A ingestion owner: `src/serdes_coding/models/com_178a/path_stage.py`
- 93A ingestion owner: `src/serdes_coding/models/com_model_93A.py`
- Config summaries只讀 raw grid，不執行 mixed-mode conversion。
- 不新增 N-port cascade、termination 或 COM algorithm。

## Validation

- Explicit representation and channel-equation tests: pass.
- Synthetic S4P Touchstone round trip for multiple port orders: pass.
- 93A/178A golden and branch regressions: pass, bit-exact golden assertions unchanged.

Rollback boundary: commit `40470e87510e760f17adb3179a9d91930dcf127f`.
