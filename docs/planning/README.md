# Planning documentation

This directory contains active change contracts and unresolved future work. Planning documents describe proposed changes; they do not override implemented code or authoritative architecture documentation.

## Active planning documents

- [當前契約狀態](active_contracts.md): each named contract's current gate and next action.
- [Reference 驗證待結案 Contracts](reference_alignment_contracts.md): E/G/T issue log and detailed TC history.
- [Future ideas](future_ideas.md): deferred improvements and unresolved design work.
- [TC-013 — Run-level fixed grid 與 search overflow 補位](utility_grid_contract_draft.md): approved scope, implementation record, and remaining acceptance gates.

When a plan is completed:

1. move its durable rules into the appropriate architecture, model, validation, or operations document;
2. record a lasting design decision as an ADR when the reasoning must remain available;
3. delete superseded planning drafts after their useful content has been incorporated;
   retain named TC decision/evidence history with a clear link to the current contract.

Do not keep completed plans as a second source of project behavior.

