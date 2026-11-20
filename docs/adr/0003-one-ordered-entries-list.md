# 0003: Expenses and settlements live in one ordered entries list

Status: accepted
Date: 2026-11-20
Decided by: pitaya943 (Owner)
Decision log row: D-10

## Context

M2 adds settlements and the ledger file's first version number (D-2). The milestone left open whether settlements live in their own list or as a kind of entry beside expenses. M4 (History) must list "entries in the order recorded" with their kind, then edit or delete them by id. Design: `docs/milestones/M2-design.md`.

## Options

### A: Separate lists

`Ledger.settlements` beside `Ledger.expenses`; the file keeps `"expenses"` and adds `"settlements"`. The v0.1 → v2 upgrade is minimal and expense code is untouched. But the order between an expense and a settlement is not stored, so M4 would need a second format change (version 3) to add one.

### B: One ordered entries list with a kind

`Ledger.entries` holds expenses and settlements in recorded order; `expenses` and `settlements` are read-only views. The file has `"entries": [{"kind": "expense", ...}, {"kind": "settlement", ...}]`. The upgrade renames `expenses` to `entries` and adds `kind`.

### C: A settlement as an expense among the receiver only (rejected early)

Balances would come out right with no new code, but a settlement is not an expense (glossary), and M4 couldn't tell them apart without a flag.

## Decision

B. Recorded order gets one owner now, and M4 can add ids without a second format change. The bigger upgrade is guarded by M2's exit criteria 3 (v0.1 fixture with hard-coded balances) and 5 (atomic save). Revisit if M4 needs a separate store per kind, for example different editing rules that a shared list makes awkward.

## Consequences

- `Ledger.expenses` changes from a dataclass field to a read-only property; code that appended to it directly must call `add_expense`.
- `from_dict` maps v0.1 `expenses` to `entries` forever (D-2); the v0.1 fixture test must stay.
- Every reader of entries handles each `kind`; an unknown kind in a version 2 file is a `TallyError`.
- Watch: if the M2 upgrade tests need many special cases, the mapping is too clever.
