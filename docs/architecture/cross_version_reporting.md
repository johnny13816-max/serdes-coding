# Cross-version reporting contract

## Purpose

93A and 178A reports use one shared presentation contract wherever they expose
the same physical quantity or diagnostic. Version-specific stages extend that
baseline; they do not fork the formatting, filename, annotation, or directory
rules for a shared plot.

Reporting remains a read-only consumer of completed status. A renderer must not
rebuild a missing model quantity from configuration. The existing 93A receiver
noise-filter plot is a recorded legacy exception and is not a template for new
plots.

## Ownership and implementation rule

```text
completed versioned status
          ↓
version adapter → direct canonical report fields
          ↓
shared COMReportBase stage flow     version-specific stage composition
          ↓                                  ↓
common plot slot                    version-only plot slot
          └──────────────┬───────────────────┘
                         ↓
                  artifact manifest
```

A plot is implemented once in `serdes_coding.reporting` when both versions can
supply the required data with the same meaning. Version reporters adapt their
status field names into that renderer. Copying the same plotting body into both
version reporters is not an accepted alignment mechanism.

The version entry points are `reporting/com_report_93A.py::COMReport` and
`reporting/com_report_178A.py::COMReport178A`; both inherit
`reporting/com_report_base.py::COMReportBase`.  The base class owns the
`plot_<stage>()`, single-run, search-run, export, and optional-stage behavior.
The adapters map versioned status fields directly and do not create a parallel
report dataclass tree. `models/com_model_93A.py` re-exports `COMReport` only for
backward compatibility.

Versioned status objects own completed data and serialization. They do not own
plot methods or accept an `include_plots` export option. Manual entry points and
search finalizers retain that workflow choice and call the appropriate reporter
with both the resolved config and completed status.

Version-specific code is retained when the underlying definition, available
status, axes, or selection metric differs. Shared low-level behavior includes:

- local Agg figure creation and interactive fallback;
- output-path construction and directory creation;
- title and subtitle layout;
- run/config and impairment annotations;
- default frequency limits and visible-range y limits;
- common path labels and directory names;
- PMF moment and keep-mass annotations;
- plot-path collection and manifest serialization.

Both version reporters expose a manifest-producing export boundary. The
manifest format is identical and records each PNG relative to the run artifact
root with its byte count and SHA-256 hash.

## Canonical single-run plot tree

```text
plots/
├── overview/
├── path_victim/
├── path_<index>_<kind>/
├── equalization/
├── impairment/
│   ├── pre_dte/       # only when the model exposes this stage
│   └── final/
├── pmf/
└── mlsd/              # 178A only
```

A stage directory is omitted when its required status is absent. Reports do not
create empty placeholder figures.  When a stage object exists but a required
stored input is missing, its renderer is skipped with `COMReportDataWarning`.

## Shared plot matrix

| Slot | Canonical filename | 93A source | 178A source | Rule |
|---|---|---|---|---|
| path pulse overview | `overview/path_pulses.png` | every `COMPath.pulse` | every `COMPath.pulse` | shared renderer |
| path SBR overview | `overview/path_sbr.png` | every `COMPath.pulse.sbr` | every `COMPath.pulse.sbr` | shared renderer |
| path insertion loss | `overview/path_S_all_IL.png` | every `COMPath.S_all` | every `COMPath.S_all` | shared renderer |
| path voltage transfer | `overview/path_H21_tf.png` | every `COMPath.H_21` | every `COMPath.H_21` | shared renderer |
| path detail | same filenames under path directory | `COMPath` | `COMPath` | shared presentation and inventory |
| selected response | `equalization/h_dsamp.png` | selected 93A phase | selected 178A DTE | shared axes/layout; version subtitle |
| residual ISI | `equalization/h_ISI.png` | 93A DFE | 178A post-FFE equivalent channel | shared sequence renderer |
| equalizer coefficients | `equalization/equalizer_coefficients.png` | DFE coefficients | FFE and DFE coefficients | shared shell with version-specific series |
| final RMS breakdown | `impairment/final/imp_summary.png` | stored scalar sigmas | stored post-FFE scalar sigmas | shared bar renderer |
| final variance proportion | `impairment/final/imp_proportion.png` | stored scalar sigmas | stored post-FFE scalar sigmas | shared bar renderer |
| PMF components | filenames under `pmf/` | stored final PMFs | stored final DFE PMFs | shared PMF renderer; emit available components |
| combined PMF/CDF | `pmf/combined_cdf.png` | stored combined PMF | stored combined PMF | shared renderer |

The common inventory is additive. A version keeps extra figures whose data and
meaning are version-specific.

### Shared path-detail inventory

Every emitted path directory uses the same filenames and shared renderer:

| Quantity | Filename |
|---|---|
| TX package Sdd | `S_tx_sdd.png` |
| measured channel Sdd | `S_ch_sdd.png` |
| RX package Sdd | `S_rx_sdd.png` |
| cascaded path Sdd | `S_all_sdd.png` |
| measured channel IL | `S_ch_IL.png` |
| cascaded path IL | `S_all_IL.png` |
| TX FFE transfer function | `H_ffe_tf.png` |
| TX transition filter | `H_t_tf.png` |
| terminated voltage transfer | `H_21_tf.png` |
| receiver filter | `H_r_tf.png` |
| receiver equalizer/CTF | `H_ctf_tf.png` |
| complete continuous path | `H_all_tf.png` |
| TX transition step response | `H_t_sr.png` |
| terminated-path impulse response | `H_21_ir.png` |
| final pulse response | `pulse_ir.png` |

Versions may supply different parameter subtitles, but axes, frequency range,
Nyquist behavior, configuration-note placement, step-transition annotation,
and artifact filenames come from the common reporting module.

## Version extensions

93A retains FOM, DFE, and FOM-ranked search diagnostics. 178A retains phase-MSE,
MMSE matrix, pre-DTE/post-FFE PSD, ADC-input, quantization, and MLSD diagnostics.
A 93A report does not create quantization or MLSD placeholders. A 178A report
does not relabel MSE as FOM.

## Presentation rules

- Shared plots use identical figure size, title hierarchy, axis labels, legend
  placement, frequency range, and annotation placement.
- Frequency plots follow `reporting_architecture.md`: log display, first
  positive bin through `min(f_max, 1.1 * baud_rate)`, and Nyquist annotation
  only inside the available band.
- Run/config notes use the lower-left corner. Impairment definitions and scalar
  summaries use the upper-left corner so they do not cover bars.
- PMF plots emit only stored components. Component names and colors remain
  stable across versions.
- The combined PMF/CDF renderer consumes stored `y0`, `A_ni`, and `COM`; it
  does not derive a replacement threshold inside reporting.
- The output manifest records every emitted PNG by relative path, byte count,
  and SHA-256 hash.

## Status gaps

Missing presentation is fixed in reporting when the required status already
exists. If a requested plot needs a quantity that is not stored, document the
gap and prepare a separate status/core change contract. Do not calculate the
quantity inside the reporter. In particular, 93A currently stores scalar
impairment results rather than the full PSD set available in 178A.

## Validation

A reporting alignment change must verify:

1. both version reporters use the shared renderer for every shared slot;
2. the expected artifact inventory matches the status completion point;
3. every PNG is non-empty and has a valid PNG signature;
4. manifests contain the complete relative-path set;
5. reporting does not mutate config/status or change FOM, MSE, PMF, or COM;
6. version-only figures remain present.
