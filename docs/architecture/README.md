# Architecture documentation

This directory owns stable, project-wide boundaries. Documents here explain where files belong, how configuration moves through the system, and which layer owns each responsibility.

- [Project structure](project_structure.md): canonical repository and case layout.
- [Documentation contract](documentation_contract.md): documentation hierarchy, ownership, and update rules.
- [Software layers](software_layers.md): source-code layer boundaries and dependency direction.
- [Utility grid](utility_grid.md): one run-level `LinkConfig`, fixed-grid convolution, and overflow handling.
- [Reference change workflow](reference_change_workflow.md): named contracts, file scope, approval, validation, commits, and closure.
- [Configuration architecture](configuration_architecture.md): workbook schema, adapters, typed configuration, runtime mapping, and validation boundaries.
- [Ad Hoc mapping contract](adhoc_mapping_contract.md) and [field table](adhoc_mapping_fields.md): source rules and shared GUI/converter validation.
- [Reporting architecture](reporting_architecture.md): plot, export, artifact, backend, and presentation ownership.
- [Repository cleanup audit](repository_cleanup_audit.md): current cleanup findings and retained exceptions.
- [Contract migration inventory](contract_migration_inventory.md): non-authoritative material awaiting source review and relocation.

Version-specific fields, call trees, status trees, equations, and stage contracts belong under `docs/models/<version>/`. Concrete case values and dataset-specific facts do not belong here.
- [Cross-version reporting](cross_version_reporting.md): shared 93A/178A plot slots, version extensions, artifact layout, and renderer reuse.
