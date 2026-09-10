# 178A Full Search Phase Sweep Comparison

日期：2026-09-09

目的：比對 GitHub Actions 上已完成的兩組 `c2m_8023dj_4p13p0_50mm` full search artifact，確認 `each_phase` 與 `coarse_fine` phase sweeping 對 candidate ranking、best candidate、final COM 與中間 MSE/phase selection 的影響。

## Scope

本文件只比較既有 GitHub Actions artifact，不重新執行 full search，不修改 mapping/config，也不使用外部 IEEE/Matlab/Octave reference result。

## Compared Runs

| Item | each_phase run | coarse_fine run |
| --- | --- | --- |
| GitHub run ID | `34136328662` | `34040724340` |
| run number | `22` | `20` |
| trigger | `workflow_dispatch` | `workflow_dispatch` |
| branch | `full-search-dry-run` | `full-search-dry-run` |
| head SHA | `ee2a86e435e3b24ac355053ef6804655074a2af0` | `c0e0d75a37ab275b0b2f0c0d58ffabb6be2bc14d` |
| artifact ID | `10038376229` | `9999893504` |
| artifact digest | `sha256:053466b64da5fcca4f87ec34f62f458b6d0ff7ebfcf9f13f8467657eb84fcfd9` | `sha256:5454f7c3b2871a01b393de2f1481b0485c7eeaf9973325ab124d0c059bc632cf` |
| phase policy | `each_phase` from workflow input | default/current config path, interpreted as `coarse_fine` |
| prepared candidates | `232848` | `232848` |
| groups | `233` | `233` |
| Python | CPython `3.11.16` | CPython `3.11.16` |
| key deps | numpy `2.4.6`, scipy `1.17.1`, scikit-rf `2.1.0`, pandas `3.0.5` | same |

Important limitation: the two runs are not a perfectly clean same-commit A/B comparison. The commit diff between the two heads is limited to `.github/workflows/run_full_search_178A.yml` and `scripts/run_full_search_178A.py`, adding the `--phase-sweep` override plumbing and changing finalize to `include_plots=True`. Core search/evaluation code was not changed in that commit diff, but the provenance should still be recorded as different-SHA evidence.

## Artifact Identity Checks

| File | Result |
| --- | --- |
| `full_search_manifest.csv` | identical SHA256: `8FC4A08447F66BE8AFE8651E69CF9F0527CA51324F04CF5E9256447605B38CCB` |
| `group_plan.csv` | identical SHA256: `A2795B49E3FFF2450B808A46001747FF08360DAC6811F7F5329588C814BEB37B` |
| `merged_partial_results.csv` | different SHA256 |
| `full_search_results.csv` | different SHA256 |

Row counts:

| File | each_phase | coarse_fine |
| --- | ---: | ---: |
| `full_search_manifest.csv` | 232848 | 232848 |
| `group_plan.csv` | 233 | 233 |
| `merged_partial_results.csv` | 232848 | 232848 |
| `full_search_results.csv` | 100 | 100 |

Interpretation: both runs searched the same candidate set with the same group partitioning. Numerical differences start at the per-candidate phase/MSE evaluation stage, not at candidate generation.

## Partial Search Comparison

Status counts are identical:

| status | each_phase | coarse_fine |
| --- | ---: | ---: |
| `ok` | 185514 | 185514 |
| `infeasible` | 47334 | 47334 |

Pairwise comparison by `search_index`:

| Metric | Value |
| --- | ---: |
| candidates present in both | 232848 |
| missing in coarse_fine | 0 |
| status differences | 0 |
| candidate parameter differences | 0 |
| finite MSE pairs | 185514 |
| infinite MSE pairs | 47334 |
| rows with nonzero finite MSE difference | 67830 |
| max absolute finite MSE difference | `4.308605027301e-4` |
| mean absolute finite MSE difference among changed rows | `2.696691619473e-6` |
| rows where each_phase MSE is lower | 36229 |
| rows where coarse_fine MSE is lower | 31601 |
| phase `pos` differences | 5060 |
| `ts` differences | 5060 |

The apparent cases where `coarse_fine` is lower are numerical roundoff only. The largest observed `coarse_fine` improvement is about `6.17e-15`, while the largest `each_phase` improvement is about `4.31e-4`.

Largest observed `each_phase` improvements:

| search_index | each MSE | coarse MSE | each pos | coarse pos | delta `each - coarse` |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 187278 | `8.568279179442e-3` | `8.999139682172e-3` | 31 | 3 | `-4.308605027301e-4` |
| 129550 | `6.611395125572e-3` | `7.024416207066e-3` | 3 | 2 | `-4.130210814944e-4` |
| 158795 | `6.788852591664e-3` | `7.201667049671e-3` | 15 | 14 | `-4.128144580067e-4` |
| 128219 | `6.831276582755e-3` | `7.242978949366e-3` | 19 | 18 | `-4.117023666110e-4` |
| 126609 | `7.271254280134e-3` | `7.655127768113e-3` | 23 | 22 | `-3.838734879786e-4` |

## Final Top-K Comparison

Top-100 ranking is identical by `search_index`.

Best candidate in both runs:

| Field | Value |
| --- | --- |
| `search_index` | `203642` |
| `c_m2` | `0.020000000000000018` |
| `c_m1` | `0.0` |
| `c_1` | `0.0` |
| `g_1` | `-14.0` |
| `g_2` | `-1.0` |
| partial `mse` | `0.0029674411881983826` |
| partial `mse_dB` | `-25.276178795828127` |
| `ts` | `50676` |
| `pos` | `20` |
| final status | `ok` |
| final `COM_dB` | `4.2282976469690245` |

Top-100 final CSV differences:

| Metric | Value |
| --- | ---: |
| same rank positions | 100 / 100 |
| rows with field-string differences | 29 |
| rows with COM floating differences | 2 |
| max absolute COM difference | `8.88178419700125e-16` |

Interpretation: final candidate selection and reported COM are effectively identical for this case. The full-search outcome is not sensitive to replacing `coarse_fine` with `each_phase` for the selected top region, although some non-top candidates show meaningful phase/MSE differences.

## Top-K Artifact Difference

`each_phase` artifact has 420 files under `top_K`; `coarse_fine` has 10 files under `top_K`.

This difference is expected from the commit diff: the later workflow/script changed finalize to `include_plots=True`, so the `each_phase` run uploaded plot subdirectories for each top-K candidate, while the earlier `coarse_fine` run uploaded only `status_summary.txt`.

## Engineering Takeaways

1. Candidate source is aligned: same manifest hash, same group plan hash, same row counts.
2. Full-search final outcome is aligned: same best candidate, same top-100 ordering, same COM to floating precision.
3. Per-candidate phase/MSE can differ: `each_phase` found lower MSE for 36,229 candidates and different selected phase for 5,060 candidates.
4. The current `coarse_fine` policy did not lose the best candidate in this 50 mm C2M case.
5. This is internal regression evidence, not external COM validation. It cannot support claims of IEEE COM compliance, official Matlab equivalence, or real-IC correlation.

## Recommended Next Action

Create a small focused regression check that compares these two policies on a reduced candidate subset and asserts:

- same manifest construction for fixed config;
- same status counts for this case;
- `each_phase` MSE is never meaningfully worse than `coarse_fine` beyond a floating tolerance;
- top-N overlap/ranking for the known 50 mm C2M case;
- best candidate and final COM equality within tolerance.

This can be done before any broad refactor or mapping change.
