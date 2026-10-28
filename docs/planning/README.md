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
2. complete validation and create the boundary commit/evidence;
3. close the tracker row and reconcile `active_contracts.md`;
4. delete the superseded temp contract, or mark retained protected/ADR evidence as historical and link its current owner;
5. remove completed detail from HANDOFF and promote/delete/deduplicate NOTES candidates;
6. create a small closure commit when the actual boundary SHA must be recorded after the implementation commit.

Do not keep completed plans as a second source of project behavior.

## Temporary contract rule

Every non-trivial modifying item selected as active owns
`docs/planning/<ITEM_ID>_<short_name>.md`. `active_contracts.md` must link it and show one current lifecycle state,
evidence link, next gate, and owner. Routine metadata/docs upkeep and pure read-only questions may omit a separate file
when their full boundary fits in `active_contracts.md`.

The temp contract may evolve during approved work, but it cannot silently expand scope. Durable content is rewritten
into its technical owner; the temp file is not renamed into an architecture/model document and is not cited as current
behavior after closure.

## State ownership

```text
v1_0_roadmap.md    long-lived platform direction and chapter progress
open_issues.xlsx   complete queue and historical tracker
active_contracts   one active/next execution boundary
HANDOFF.md         short-lived session recovery context
NOTES.md           candidate lessons, not permanent rules
```

Only `active_contracts.md` may identify an executable active boundary. A HANDOFF entry cannot authorize work.
The write trigger is the project-level `/handoff` command defined in `project_workflow.md`; the read trigger is the
first repository-related turn of every new conversation, enforced by `AGENTS.md`.

