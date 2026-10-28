# Planning documentation

This directory contains active change contracts and unresolved future work. Planning documents describe proposed changes; they do not override implemented code or authoritative architecture documentation.

## Active planning documents

- [v1.0 platform roadmap](v1_0_roadmap.md): the platform review sequence and current chapter-level completion state.
- [Toward v1.0 change tracker](open_issues.xlsx): concise status, dependency,
  boundary, dates, next step, and closure evidence for proposed and active work.
- [當前契約狀態](active_contracts.md): each named contract's current gate and next action.
- [HANDOFF](HANDOFF.md): at most 30–40 lines of current cross-session recovery state; verify it against Git and trackers.
- [Candidate reusable lessons](NOTES.md): reviewed candidates awaiting promotion into durable rules.
- [Reference 驗證待結案 Contracts](reference_alignment_contracts.md): E/G/T issue log and detailed TC history.
- [Future ideas](future_ideas.md): deferred improvements and unresolved design work.
- [TC-013 — Run-level fixed grid 與 search overflow 補位](utility_grid_contract_draft.md): approved scope, implementation record, and remaining acceptance gates.

When a plan is completed:

1. move its durable rules into the appropriate architecture, model, validation, or operations document;
2. record a lasting design decision as an ADR when the reasoning must remain available;
3. delete superseded planning drafts after their useful content has been incorporated;
   retain named TC decision/evidence history with a clear link to the current contract.

Do not keep completed plans as a second source of project behavior.

## State ownership

```text
v1_0_roadmap.md    long-lived platform direction and chapter progress
open_issues.xlsx   complete queue and historical tracker
active_contracts   one active/next execution boundary
HANDOFF.md         short-lived session recovery context
NOTES.md           candidate lessons, not permanent rules
```

Only `active_contracts.md` may identify an executable active boundary. A HANDOFF entry cannot authorize work.

