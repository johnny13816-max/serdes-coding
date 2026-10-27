# UTIL-EYE-001 — LinkSegment deterministic eye plot

## Status

Approved, implemented, validated, and isolated in the dedicated commit that contains this record.

## Boundary

- `LinkSegment.eye_traces()` owns SBR superposition and eye folding.
- `LinkSegment.plot_eye()` owns Matplotlib presentation only.
- Caller supplies actual symbol amplitudes and explicit transient discard.
- No COM stage, noise, jitter, CDR, BER, PRBS, report, or workbook behavior is added.

## Validation gate

- Direct per-symbol SBR summation and `np.convolve` representation must agree.
- Main-cursor and record-start alignments must be tested.
- Plot lines must equal the `eye_traces()` matrix.
- 93A／178A production golden values and the full regression suite must remain unchanged.

## Result

- `tests/test_link_eye.py`: 12 passed.
- 93A／178A production golden: 2 passed; fixed values unchanged.
- Full suite: 182 passed, 2 subtests passed; the unrelated GUI test could not
  start because the local Python installation lacks a usable Tk/Tcl runtime.

Rollback boundary: commit `d9a2c6e`.
