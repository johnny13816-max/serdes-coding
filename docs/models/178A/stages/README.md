# 178A stage documentation

This directory owns the stable input/output and status-lifecycle contract for each 178A model stage. Functional blocks are documented inside their owning stage; small private helpers remain in source docstrings.

## Stage order and status

1. [Path construction](path_construction.md) — implemented structural contract; specification equations still require independent reference validation.
2. [Pre-DTE impairment](pre_dte.md) — implemented common-cache, per-phase impairment, ADC-input policy, and status contract; specification equations still require independent reference validation.
3. [Sampling phase and MMSE DTE](mmse_dte.md) — implemented phase scheduling, floating placement, limiter flow, MSE selection, and status contract; equations still require independent reference validation.
4. [Post-FFE impairment](post_ffe.md) — fixed run-level grid with checked linear-convolution tails, residual ISI, Gaussian/ADC inputs, and reporting PSDs; equations still require independent reference validation.
5. [DFE COM](com_dfe.md) — implemented final-PMF accuracy override, component ownership, quantization handoff, combined PMF, and scalar result contract; equations still require independent reference validation.
6. [MLSD COM](com_mlsd.md) — implemented added-noise calibration, convergence history, MLSD PSD/autocorrelation, truncated DER, final adjustment, and reporting contract; equations still require independent reference validation.

Reporting and search are downstream orchestration layers documented in [Reporting architecture](../../../architecture/reporting_architecture.md), [Search execution](../../../operations/search_execution.md), and the model [Call tree](../call_tree.md).

## Review state

A stage document distinguishes:

- **implemented structure**: confirmed from current source;
- **validated behavior**: backed by a named test or reproducible reference case;
- **unresolved**: requires specification or numerical review.

Source inspection alone does not validate a protected model equation. Mathematical assertions are added only through the Core Model Change Contract defined in `AGENTS.md`.
