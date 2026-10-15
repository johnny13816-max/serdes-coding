# Search execution

This runbook defines the file-backed search lifecycle shared by local orchestration and GitHub Actions. Candidate definitions remain in each case workbook.

## Lifecycle

```text
prepare → partial → finalize → verify
```

1. **prepare** loads the case workbook, creates the complete candidate manifest, partitions it into groups, and records input fingerprints, the resolved config snapshot, and the Git revision. A case may live under the repository or in a dedicated `%TEMP%` validation directory; artifact keys remain stable in either location.
2. **partial** evaluates assigned groups and writes file-backed candidate rows. Workers do not depend on shared in-memory model state.
3. **finalize** checks complete candidate coverage, merges partial rows, applies the version-specific ranking rule, reruns selected candidate data needed for final output, and exports plots.
4. **verify** checks final status, selected-candidate coverage, required artifacts, and recorded hashes after download.

Missing groups, duplicate candidate indices, incomplete manifest coverage, or an invalid final result fail the corresponding stage after available diagnostic files have been written.

## Version ownership

| Version | Orchestrator | Ranking |
|---|---|---|
| 93A | `src/serdes_coding/search/com_search_93A.py` | highest native 93A FOM |
| 178A | `src/serdes_coding/search/com_search_178A.py` | lowest 178A MSE for sweep/final selection |

The two ranking definitions must remain separate. Search orchestration may share lifecycle concepts without translating one model's metric into the other.

Command-line runners are:

- `scripts/run_search_93A.py`
- `scripts/run_full_search_178A.py`

Both expose `prepare`, `partial`, `finalize`, and `verify` commands.

## GitHub Actions interface

The workflows are:

- `.github/workflows/run_search_93A.yml`
- `.github/workflows/run_full_search_178A.yml`

Their manual user input is `case_id`. The workflow resolves `cases/<case_id>/<version>/config.xlsx`; fixed parameters, channel references, search ranges, and execution policies remain workbook-owned. Worker count, grouping, concurrency, and top-K processing are internal orchestration details rather than top-level model controls.

For 178A, `run_config.control.execution_profile` selects the versioned
project→runtime preset. `search_sweep.target` must remain `mse`.
`search_final.target="full"` is required when the requested result includes
MLSD/COM_MLSD; a successful `target="dfe"` workflow proves only the DFE search
scope. The search prepare artifact must preserve the resolved profile and input
fingerprints before distributed execution begins.

Workflow outputs are written below:

```text
cases/<case_id>/<version>/results/actions/
```

Final artifacts include `resolved_config.json`, the Git revision and dirty-state marker, input fingerprints, manifests and group results needed for audit, merged/final search data, plots, and verification metadata.

## Local use

For a simple interactive search, the versioned model's manual `search_run` entry may be used. For reproducible split execution, use the command-line lifecycle above so partial results can be merged and verified using the same boundaries as GitHub Actions.

The legacy 178A split-search GUI still resolves the older case layout. Until it is migrated, it is a compatibility tool and is not the canonical entry for new cases.
