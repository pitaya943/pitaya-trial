<!-- Design for one milestone, written by /design, saved as docs/milestones/M<n>-design.md. Use the document language from docs/agents/harness.md. Tickets are cut from the scenarios; /report M<n> checks every one. -->

# M2 design: Settlements and a versioned file format

Status: agreed by the Owner on 2026-11-20 (D-10 to D-13, [ADR 0003](../adr/0003-one-ordered-entries-list.md)). Tickets: T-003, T-004, T-005, T-006 (added by D-14).

## Scenarios

Example group used below (`_group` in `tests/test_cli.py`): Ana pays 30.00 for Ana, Bo, Cy; Bo pays 6.00 for Ana and Bo. Balances: Ana 17.00, Bo −7.00, Cy −10.00.

| ID | Given | When | Then | Proved by |
| --- | --- | --- | --- | --- |
| S-1 | The example group | `tally settle Bo Ana 7.00`, then `tally balances` | Ana 10.00, Bo 0.00, Cy −10.00: the payer's balance rises and the receiver's falls by 7.00 (a sign-flipped implementation gives Bo −14.00 and fails) | `tests/test_cli.py::test_cli_settle_updates_balances` |
| S-2 | A `Ledger` with expenses | `add_settlement(payer, receiver, amount)` | `balances()` moves by exactly `+amount` for the payer and `−amount` for the receiver, and still sums to 0; names are matched case-insensitively and trimmed | `tests/test_ledger.py::test_settlement_moves_balances` |
| S-3 | A ledger with members Ana and Bo | Settle with an unknown payer, an unknown receiver, payer = receiver (also `ana` → `Ana`), amount `0`, `-1`, `1.234` | `TallyError` that says what was wrong; nothing recorded; the CLI exits 1 and the file's bytes are unchanged | `tests/test_ledger.py::test_invalid_settlements_record_nothing`, `tests/test_cli.py::test_cli_settle_errors_leave_the_file_unchanged` |
| S-4 | Seeded random ledgers (at least 300, D-5), including some with 13+ members with a non-zero balance so the greedy path is covered | Record every payment `settle_up(ledger.balances())` returns, as a settlement | Every balance is 0 | `tests/test_settle.py::test_recording_settle_up_clears_every_balance` |
| S-5 | The example group | `tally settle-up`, then `tally settle` with each printed line | `tally balances` prints 0.00 for everyone (end-to-end version of S-4, output format fed back as input) | `tests/test_cli.py::test_cli_settling_every_settle_up_payment_clears_balances` |
| S-6 | Any ledger | Any command that saves | The file has `"version": 2` at the top level, and expenses and settlements survive `to_dict` → `from_dict` in recorded order | `tests/test_cli.py::test_cli_writes_version_2`, `tests/test_ledger.py::test_round_trip_keeps_entries_in_order` |
| S-7 | `tests/fixtures/v0.1.json`, written by the v0.1 code (no `version`; remainder splits, a subset of participants, mixed-case names, notes) | `tally balances` | Prints exactly the balances recorded beside the fixture when it was made (hard-coded in the test, not recomputed) | `tests/test_cli.py::test_v01_fixture_loads_with_the_same_balances` |
| S-8 | A copy of the v0.1 fixture | `balances` and `settle-up` (read-only) | The file's bytes and mtime are unchanged: upgrade happens only on save | `tests/test_cli.py::test_read_only_commands_do_not_upgrade_a_v01_file` |
| S-9 | A copy of the v0.1 fixture | A command that saves (`add-member Dee`) | The file now has `"version": 2`; the old members' balances are identical; the expenses are kept in order | `tests/test_cli.py::test_v01_file_is_written_as_version_2_on_save` |
| S-10 | A file with `"version": 3` (and `99`) | Any command, read-only or saving | `TallyError` whose message names the version (e.g. "ledger version 3 is newer than this tally supports (2)"); exit 1; bytes and mtime unchanged | `tests/test_cli.py::test_unknown_future_version_is_rejected_and_not_written` |
| S-11 | A file whose `"version"` is neither absent nor the integer 2: `1`, `0`, `"2"`, `null`, `true` (D-11) | `Ledger.from_dict` | `TallyError` whose message names the value (`true` is not taken as 1); nothing is guessed | `tests/test_ledger.py::test_unsupported_version_values` |
| S-12 | A saved ledger file | Save fails part-way through the write (the test makes the temp-file write emit half the bytes, then raise `OSError`) | The original file's bytes are intact and no temp file is left in the directory. The current `path.write_text` would truncate the original, so this test goes red first | `tests/test_save.py::test_failed_save_leaves_the_old_file_intact` |
| S-13 | A saved ledger file; a fresh path with no file | A normal save | The file holds the full new content, its permission bits are preserved (existing file) and no temp file is left behind | `tests/test_save.py::test_save_replaces_the_file_and_leaves_no_temp_file` |
| S-14 | The whole repository | `.venv/bin/python -m pytest -q` | Passes locally and in CI | the test command |
| S-15 | Ana 17.00, Bo −7.00 (example group) | `add_settlement("Bo", "Ana", 1000)`: more than Bo owes (D-12) | Recorded: Bo +3.00, Ana 7.00; balances still sum to 0 | `tests/test_ledger.py::test_overpaying_settlement_is_recorded` |
| S-16 | A file `{"version": 2, "members": ["Ana", "Bo"], "expenses": [{"payer": "Ana", "amount": 1000, "participants": ["Ana", "Bo"], "note": ""}]}` (a v0.1 body with a version 2 line) | Any command | `TallyError` naming the missing `entries`; exit 1; bytes and mtime unchanged. With T-003's reader it loads as an empty ledger, and the next save writes `"entries": []` (the data loss the T-003 verifiers found) | `tests/test_cli.py::test_v2_file_without_entries_is_refused` |
| S-17 | A file with `members` and `entries` but no `version` | Any command | `TallyError` naming `version`, not read as v0.1 with zero expenses; file unchanged | `tests/test_cli.py::test_entries_without_version_is_refused` |
| S-18 | A file that isn't JSON (`{"members": [`), or whose top level is `[]`, `"x"` or `3` | Any command | `error: <one line>` on stderr, exit 1, no traceback; file unchanged | `tests/test_cli.py::test_unreadable_or_non_object_file_is_refused` |
| S-19 | A version 2 entry that is `"x"`, an expense without `payer`, `amount` or `participants`, a settlement without `receiver`; a v0.1 expense without `amount` | `Ledger.from_dict` | `TallyError` naming the entry's position (from 1) and the missing field; nothing recorded | `tests/test_ledger.py::test_malformed_entries_are_refused` |

Exit criteria coverage: 1 → S-1, S-2, S-3, S-15; 2 → S-4, S-5; 3 → S-6, S-7, S-8, S-9; 4 → S-10, S-11; 5 → S-12, S-13; 6 → S-14; 7 → S-16, S-17, S-18, S-19.

## Interfaces

`src/tally/ledger.py`:

```python
FORMAT_VERSION = 2

@dataclass
class Settlement:
    payer: str      # member key; same field names as settle.Payment so settle-up output maps 1:1
    receiver: str
    amount: int     # cents, > 0

class Ledger:
    entries: list[Expense | Settlement]          # the one owner of recorded order
    @property
    def expenses(self) -> list[Expense]: ...     # read-only view, filtered from entries
    @property
    def settlements(self) -> list[Settlement]: ...
    def add_settlement(self, payer: str, receiver: str, amount: int) -> Settlement: ...
    def to_dict(self) -> dict: ...               # always writes "version": FORMAT_VERSION
    @classmethod
    def from_dict(cls, data: dict) -> "Ledger": ...  # accepts no version (v0.1) or 2; else TallyError
```

`src/tally/cli.py`:

- New command `tally settle <payer> <receiver> <amount>`: parses with `parse_amount`, calls `add_settlement`, saves. Help text: "record that <payer> paid <receiver> back".
- `save(ledger, path)` becomes atomic: write to a temp file in the same directory (`tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")`), flush and `fsync`, copy the old file's permission bits if it exists, then `os.replace(temp, path)`. On any exception, remove the temp file and re-raise.
- `load(path)` is unchanged; version handling lives in `Ledger.from_dict`.

File format, version 2:

```json
{
  "version": 2,
  "members": ["Ana", "Bo", "Cy"],
  "entries": [
    {"kind": "expense", "payer": "Ana", "amount": 3000, "participants": ["Ana", "Bo", "Cy"], "note": ""},
    {"kind": "settlement", "payer": "Bo", "receiver": "Ana", "amount": 700}
  ]
}
```

v0.1 (read forever, D-2): `{"members": [...], "expenses": [...]}` with no `version`. Each expense becomes an `entries` item with `"kind": "expense"`, in the same order.

## Data flow

```
argv ──► cli.main ──► load(path) ──► json.loads ──► Ledger.from_dict
                                                     │  version absent → read "expenses" (v0.1)
                                                     │  version == 2   → read "entries"
                                                     │  otherwise      → TallyError (nothing written)
                       ledger.add_settlement / add_expense / add_member  (validation, TallyError)
                       save(ledger, path) ──► Ledger.to_dict (version 2)
                                          ──► temp file in same dir ──► fsync ──► os.replace
```

`balances()` walks `entries` once: an expense adds its amount to the payer and subtracts each share; a settlement adds its amount to the payer and subtracts it from the receiver.

## Workflow

1. Settle (S-1): parse args → `load` → `parse_amount` → `add_settlement` validates and appends → atomic `save` → exit 0. Any `TallyError` before `save` exits 1 with the file untouched.
2. Upgrade (S-7–S-9): `load` reads a v0.1 file into the in-memory model; read-only commands return before `save`; saving commands write version 2.
3. Reject (S-10): `from_dict` raises before any command runs, so no command can reach `save`.

## Notifications

None. Errors go to stderr as `error: <message>` as today.

## State owners

| State | Owner (one) | Who reads it |
| --- | --- | --- |
| Members, expenses, settlements and their recorded order (`Ledger.entries`) | `ledger` | `cli`, `settle` (via `balances()` only) |
| Format version (`FORMAT_VERSION`) and the v0.1 → v2 mapping | `ledger` (`to_dict` / `from_dict`) | `cli` only through those two methods |
| The file on disk and how it is written (atomic replace) | `cli` (`load` / `save`) | none |
| Settle-up payments | `settle` (computed, never stored) | `cli` |

## Shapes considered

1. **A — separate lists.** `Ledger.settlements: list[Settlement]` beside `expenses`; the file gets a `"settlements"` key and keeps `"expenses"` as it is. The upgrade is the smallest possible (add `version`, default `settlements` to `[]`), and existing expense code is untouched. But the order between an expense and a settlement is lost: M4 exit criterion 2 ("lists entries in the order recorded") would then need another format change (version 3) to add a sequence, so the format would change twice in two milestones.
2. **B — one ordered list of entries with a `kind`.** `Ledger.entries` holds expenses and settlements in recorded order; `expenses` and `settlements` are read-only views. The upgrade renames `expenses` to `entries` and adds `kind`, which is a bigger change to guard (S-7, S-9), but recorded order has one owner from now on, and M4 can add ids without changing the shape again.
3. (Rejected early) **Settlement as an expense** paid by the payer among `[receiver]`. `balances()` would be right with no new code, but it breaks the glossary (a settlement is not an expense), and M4's history and `kind` could not tell them apart without a flag, so it is A or B in disguise.

**Chosen:** B (D-10, ADR 0003), because recorded order gets one owner now and M4 needs no second format change; the extra upgrade risk is exactly what exit criteria 3 and 5 already guard.

## Open questions

None left. The Owner decided them on 2026-11-20:

1. Shape B, one ordered `entries` list (D-10, ADR 0003).
2. A `version` that is neither absent nor the integer 2 is rejected, naming the value (D-11).
3. A settlement may be larger than what the payer owes (D-12).
4. A save that fails with `OSError` still ends in a traceback in M2; only the old file's safety is promised (D-13).

Known limits, not addressed (say if you want them): saving through a symlink replaces the link with a regular file; two `tally` processes saving at once can lose one write (last rename wins); on some network filesystems `os.replace` is not atomic.

## Ticket cut

| Ticket | Scenarios | Depends on | Parallel with |
| --- | --- | --- | --- |
| T-003 Versioned ledger file format | S-6, S-7, S-8, S-9, S-10, S-11 | none | T-004 |
| T-004 Atomic save | S-12, S-13 | none | T-003 |
| T-005 Record settlements | S-1, S-2, S-3, S-4, S-5, S-15 | T-003, T-004 | none |
| T-006 Refuse malformed ledger files | S-16, S-17, S-18, S-19 | T-005 | none (same files as T-005) |

S-14 (the full test command) is a done-when condition of every ticket.
