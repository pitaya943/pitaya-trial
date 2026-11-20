<!-- pitaya template 0.1.1 · docs/decisions.md -->
# Decisions

The Owner's decisions. Append only: add a new row, never edit or delete an old one. To change a decision, add a row that supersedes it and name the old number.

A decision that weighed two or more real options and changes the architecture, a public interface or the data model also gets a record in `docs/adr/<nnnn>-<slug>.md` (context, options, decision, consequences); link it from the row's Why. Everything else stays one row.

| # | Date | Decision | Why | Supersedes |
| --- | --- | --- | --- | --- |
| D-1 | 2026-11-20 | Settle up returns the exact minimum number of payments for up to 12 members with a non-zero balance, and greedy (at most n−1) above that, saying so. | The exact minimum is NP-hard; a cap keeps the spec's promise for realistic groups without hanging. [ADR 0001](adr/0001-settle-up-exact-with-greedy-fallback.md) | |
| D-2 | 2026-11-20 | The ledger file gets a `version` field on its first format change (M2). Every later version reads v0.1 files forever; files upgrade on save; an unknown version is rejected. | Users keep ledger files; a version makes later format changes safe and lets an old tally refuse a newer file instead of misreading it. | |
| D-3 | 2026-11-20 | Percentage and share splits give leftover cents by largest remainder, ties in listed order. | Fairer than listed order alone, and identical to the equal-split rule when all fractions tie. [ADR 0002](adr/0002-largest-remainder-for-proportional-splits.md) | |
| D-4 | 2026-11-20 | Roadmap: M1 Settle up, M2 Settlements and versioned format, M3 Unequal splits, M4 History, M5 Export and import, M6 Currencies. | Highest value and lowest risk first (M1 changes no format); the format is versioned before the milestones that change it; currencies last because they touch every amount. | |
| D-5 | 2026-11-20 | Property tests use seeded `random.Random` loops in plain pytest; no Hypothesis dependency for now. | Keeps CI, the harness and the README unchanged; failures stay reproducible by seed. Supersedes the roadmap's Hypothesis assumption (M1 risks), which was not a decision row. | |
