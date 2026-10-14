# SerDes Coding

Python implementation project for SerDes and IEEE COM modeling experiments.
The repository owns source code, typed workbook configuration, reproducible
cases, search workflows, reports, validation records, and project documentation.
Theory notes, private PDFs, and raw specification-reading notes belong outside
this public coding repository.

## Start here

- [Project documentation](docs/README.md)
- [Project structure](docs/architecture/project_structure.md)
- [Software layers](docs/architecture/software_layers.md)
- [178A model documentation](docs/models/178A/README.md)

## Repository layout

```text
serdes-coding/
  src/serdes_coding/   importable Python package
  .github/             CI and search workflows
  cases/               project-owned run inputs and generated reports
    _templates/        validated model-specific config templates, when present
  compatibility/       standalone Python 3.6/3.7 direct-import exports
  docs/                architecture, models, validation, operations and plans
  reference_data/      external channels, configurations and provenance
  scripts/             orchestration and validation commands
  src/serdes_coding/   importable Python package
  tests/               automated validation
```

Read `AGENTS.md` and the project-structure contract before changing model code,
case layouts, workbook mappings, or execution paths.
