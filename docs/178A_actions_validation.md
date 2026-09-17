# 178A Actions validation, 2026-09-15

Canonical local root: C:/Users/johnn/Documents/Serdes-learn/serdes-coding.

- Local workbook-driven prepare -> two partial workers -> merge -> finalize completed for case_260915_ci_small (4 candidates).
- All four selected final candidates completed and exported 164 PNGs; manifest hashes verified.
- Injected one report write failure: final CSV retained one final_status=error, remaining candidates attempted, finalize raised RuntimeError.
- Deliberately damaged a PNG in a test copy: artifact verification rejected its hash; restoring it passed.
- Full case has 232848 candidates, 2329 internal groups, 233 workers (maximum 20 concurrent).
- CI uses Python 3.11 on Linux; local validation used Python 3.14. Cloud validation is required before dispatching the full case.
- Fixed, channel and execution workbook sheets are identical between report, small and full cases. Only search_config ranges differ.
- All selected finals must succeed. Finalize always draws the existing 178A full report (victim path, phase/DTE, pre/post impairment, PMF as available); each output PNG is hashed. A separate job downloads the artifact and verifies hashes and selected-candidate coverage.
