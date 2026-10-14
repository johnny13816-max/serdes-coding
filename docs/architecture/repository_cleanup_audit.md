# Repository cleanup audit

Date: 2026-09-25

This audit records cleanup boundaries before files are moved or deleted. It is
not authorization to discard unresolved work.

## Canonical root

`C:/Users/johnn/Documents/Serdes-learn/serdes-coding`

The active branch is `main`. At audit time it is two commits ahead of
`origin/main` with the completed 178A MLSD diagnostic work.

## Preserve

- `src/`, `tests/`, `scripts/`, `.github/`, and package metadata.
- Validated reusable project-config templates belong under `cases/_templates/<model>/`; none are currently maintained.
- Canonical `.venv/` at the project root.
- External datasets and provenance under `reference_data/` until their license,
  source, and active case references have been checked.
- Case inputs and result archives until each case has a manifest and an agreed
  canonical layout.
- Existing historical contracts and validation records until the new document
  index marks them current, historical, or superseded.

## Retired recovery worktree

The registered `tmp/.codex-merge-main` worktree was removed on 2026-09-25.
Before removal, its branch history remained in Git and the following material
was preserved outside the repository at
`C:/Users/johnn/Documents/Serdes-learn/serdes-coding-recovery-20260925`:

- a binary patch of all modified tracked files;
- worktree status, branch log, and complete untracked-file inventory;
- unique config workbooks, manifests, preparation scripts, and documents;
- small PDF, workbook-repair, and debug scratch files.

The nested worktree and its nested virtual environment released about 899 MiB.
The remaining top-level `tmp/` and generated per-case `.run/` directories were
also removed after preserving the small non-generated scratch files, releasing
about another 2.95 GiB. Do not recreate a nested checkout under this project.

## Case-layout resolution

The canonical layout is now:

```text
cases/<case_id>/<model>/config.xlsx
cases/<case_id>/<model>/results/<run_name>/
```

`docs/architecture/project_structure.md` owns this rule. Older `config/config_<model>.xlsx` and `report/<model>/` paths may remain in legacy cases or compatibility tools, but they are not templates for new work. Migrate such tools deliberately and verify workbook channel resolution before deleting existing user data.
## Clear generated material

The following classes are removable after their owning result has been retained
or proven reproducible:

- `__pycache__`, `.pytest_cache`, inspection sidecars, and notebook checkpoints;
- per-case `.run/` scratch;
- duplicated downloaded Actions artifacts;
- nested virtual environments;
- temporary workbooks whose canonical replacement is identified.

Generated output must remain ignored by Git. A cleanup must never mix deletion
of generated data with protected model changes.
