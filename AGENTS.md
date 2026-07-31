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

## Helper Placement

Use this rule when deciding where to place validation helpers, conversion
helpers, and small internal functions:

- Use a module-level private helper when the function may be shared by multiple
  classes or module-level functions, or when the operation is a pure conversion
  that does not belong to one class instance.
- Use a class-level private helper when the helper is used by multiple methods
  in the same class and its meaning belongs to that class contract,
  representation, or validation boundary.
- Use a nested helper when the helper only supports one method and does not need
  independent reuse or testing.

Prefer choosing helper placement by semantic ownership, not only by the current
number of call sites. For example, an S4P-to-Sdd array conversion can be a
module-level helper even if it is initially called only by one constructor,
because the operation itself is not tied to one object instance.
