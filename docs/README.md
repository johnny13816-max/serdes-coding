# Documentation index

This directory contains the maintained project documentation. Start with the architecture documents, then use the version-specific model pages and operational guides for implementation or execution work.

## Reading order

1. [Project structure](architecture/project_structure.md)
2. [Project evolution and extension framework](architecture/evolution_strategy.md)
3. [Documentation contract](architecture/documentation_contract.md)
4. [Software layers](architecture/software_layers.md)
   and [Utility grid](architecture/utility_grid.md)
   and [COM dataclass text contract](architecture/dataclass_text_contract.md)
   and [Reference change workflow](architecture/reference_change_workflow.md)
5. [Configuration architecture](architecture/configuration_architecture.md)
6. [Reporting architecture](architecture/reporting_architecture.md)
7. [Model documentation](models/README.md)
   including the authoritative [178A branch behavior registry](models/178A/branch_behavior_registry.md)
8. [Validation](validation/README.md) and [operations](operations/README.md)
   including the authoritative [v1.0 release gate](operations/v1_0_release_gate.md)
9. [Active contracts](planning/active_contracts.md) and [planning](planning/README.md)

## Directory ownership

```text
docs/
├── architecture/   Project-wide boundaries, structure, and durable contracts
├── models/         Version-specific call trees, config trees, status trees, and algorithms
├── validation/     Reproducible verification methods and acceptance criteria
├── operations/     Runbooks for local execution, GitHub Actions, and artifact handling
└── planning/       Active change contracts and unresolved future work
```

## Authority

- `AGENTS.md` defines mandatory repository-working rules.
- `docs/architecture/` defines durable project boundaries.
- `docs/models/` explains reviewed, version-specific behavior.
- `docs/validation/` and `docs/operations/` describe repeatable procedures.
- `docs/planning/` contains active proposals and is not authoritative until its decisions are incorporated into the maintained documents.
- Files explicitly marked as migration inventories are not authoritative and are excluded from the reading order.

Concrete case values belong in workbooks and case-local README files. Reference-data provenance belongs beside the dataset. Do not duplicate either into project-wide rules.
