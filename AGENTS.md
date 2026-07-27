# SerDes Coding Subproject Instructions

## Scope

This subproject contains Python code for SerDes and COM modeling experiments.

Code, tests, examples, notebooks, and package metadata belong here. IEEE PDFs,
raw reading notes, and theory summaries belong in `../serdes-theory-note/`.

This subproject is the main home for the user's personal after-work coding
artifact and public GitHub repository. It owns implementation decisions,
package structure, tests, examples, and repository hygiene for public-facing
SerDes/COM modeling code.

Theory or spec-reading discussions from `../serdes-theory-note/` may feed this
project with implementation guidance, API boundary recommendations, numerical
conventions, and validation ideas. Those discussions should become code here
only when the user explicitly asks to implement or port them into this
subproject.

## Conventions

- Keep importable source under `src/serdes_coding/`.
- Keep validation tests under `tests/`.
- Keep exploratory notebooks under `notebooks/`.
- Prefer small modules with clear numerical conventions.
- Document FFT, S-parameter, impedance, and COM equation conventions at the API boundary.
- Keep private PDFs, work documents, raw spec excerpts, and long-form theory notes out of this public coding repository.
