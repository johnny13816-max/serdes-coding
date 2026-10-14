# Reporting architecture

This document defines ownership of plots, text summaries, numerical exports, and report artifacts. It does not define COM equations or recompute model results.

The shared 93A/178A plot inventory and renderer-reuse rules are defined in [Cross-version reporting](cross_version_reporting.md).

## Boundary

```text
validated config + completed status
                ↓
        reporting / export
                ↓
 text summaries + arrays + plots + manifests
```

The model owns computed quantities and status lifecycle. Reporting owns presentation, file organization, labels, and serialization. A report must use the status produced by the run and must not silently replace a missing status value with a fresh model calculation.

## Current implementations

| Version | Reporter | Model compatibility surface |
|---|---|---|
| 93A | `reporting/com_report_93A.py::COMReport` | `models/com_model_93A.py` re-exports `COMReport` for existing imports |
| 178A | `reporting/com_report_178A.py::COMReport178A` | reporting is imported explicitly by run/search orchestration |

`COMReport` and `COMReport178A` are presentation-only: they consume versioned
config/status objects, group figures by available pipeline stage, and do not
mutate either object. `plot_single_run()` emits only groups whose status data
exists. The model modules retain compatibility imports, but new reporting and
search code imports reporters directly from `serdes_coding.reporting`.

### Known 93A boundary gap

Most 93A report plots consume config and status. `_plot_noise_filter()` currently rebuilds the receiver noise-filter response from config for presentation instead of reading a stored response from status. Treat this as a known exception, not as permission for other report methods to recreate protected quantities. Resolving it requires a separately reviewed status/reporting change.

## Plot API behavior

Detailed report methods accept an output directory. A non-empty output path creates PNG files; an empty path uses the active interactive backend. Status objects expose data serialization only; run and search orchestration explicitly invoke the version-specific report object when plots are requested.

When saving report figures, `COMReport` and `COMReport178A` create a local `FigureCanvasAgg`. They do not change Matplotlib's global backend, so batch export does not require a GUI and does not overwrite an interactive IPython backend. Lower-level `LinkSegment` and `SparamModel` plot helpers use the caller's current pyplot backend.

A plot helper may accept an existing `Axes` for composition. The caller that creates the figure owns final save/show behavior unless the helper's API explicitly finishes the figure.

## Export ownership

Configuration objects export a human-readable `config_summary.txt` containing the resolved typed configuration.

### 93A single run

- `COMStatus.export()` writes compressed numerical arrays to `arrays.npz`.
- `COMStatus.export_report_summary()` writes `report_summary.txt`.
- `COMReport.plot_single_run()` writes detailed plots grouped by path, DFE, impairment, and PMF ownership.
- `COMReport.export_single_run()` and `export_search_run()` write the detailed plot tree and validated `plot_manifest.json`.

### 178A single run

- `COMStatus.export()` writes `status_summary.txt`.
- Run/search orchestration invokes `COMReport178A.export_single_run()` explicitly when plots are enabled. The reporter writes `plot_manifest.json` containing each returned PNG's relative path, byte count, and SHA-256 hash.
- Stage-specific numerical and presentation details must follow the 178A status tree once that document is reviewed.

### Search results

Search CSV, manifest, merge, finalization, and verification files are owned by the search workflow described in [`../operations/search_execution.md`](../operations/search_execution.md). Search reports may add metric traces and selected-candidate plots, but they must preserve the version's native ranking metric.

Search-status `export()` methods serialize search rows and the selected status only. The orchestration layer owns the `include_plots` workflow choice and calls `COMReport.export_search_run()` or `COMReport178A.export_search_run()` explicitly. Status objects never carry a hidden originating config such as `_config_for_report`.

These exports support reports, debugging, and run traceability. They are not a stable object-reconstruction or long-term binary checkpoint format.

## Plot organization

The first victim path uses `path_victim/`. Other path directories include the path index and kind. Stage folders reflect data ownership rather than arbitrary visual grouping.

Both version reporters follow the shared tree defined by
[`cross_version_reporting.md`](cross_version_reporting.md):

```text
overview/
path_victim/
path_<index>_<kind>/
equalization/
impairment/
  pre_dte/       # emitted by 178A when available
  final/
pmf/
mlsd/            # 178A only
```

A report must not create a figure whose required status stage is absent. Plot inventories that are specific to a model stage belong in that stage's model documentation.

The S-parameter detail, insertion-loss detail, transfer-function, impulse-response,
step-response, overview, equalizer, impairment-bar, PMF-component, and manifest
renderers live in `reporting/com_report_common.py`. Version reporters select
their fields and compose version-specific subtitles; they do not duplicate the
figure construction.

## Frequency-plot presentation

The shared report convention is:

- use a logarithmic frequency axis for frequency-domain detail plots;
- retain DC in the underlying data but start a logarithmic display at the first positive frequency bin;
- show up to `min(available_frequency_max, 1.1 * baud_rate)` by default;
- mark Nyquist at `f_nyq = baud_rate / 2` when it lies inside the available band;
- report S-parameter insertion loss as absolute `IL` and scalar transfer response as relative gain;
- do not extrapolate an annotation beyond the measured or available frequency band;
- derive automatic y-limits only from finite data visible in the selected x-range, ignoring values at or below the numerical display floor of `-300 dB` when higher values exist.

Titles describe the plotted quantity. A smaller subtitle carries figure-specific parameters or band limitations. Run-level configuration notes belong on overview plots rather than every detail figure.

## Artifact verification

A successful plot export is more than the presence of a directory. Verification should confirm that expected PNG files are non-empty, have a valid PNG signature, and match their recorded hashes when a plot manifest exists. Workflow verification also checks final status and selected-candidate coverage; see the search runbook for lifecycle details.

