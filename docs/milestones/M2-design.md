<!-- Design for one milestone, written by /design, saved as docs/milestones/M<n>-design.md. Use the document language from docs/agents/harness.md. Tickets are cut from the scenarios; /report M<n> checks every one. -->

# M2 design: Settlements and a versioned file format

Status: draft, waiting for the Owner. The chosen shape and the open questions below are recommendations, not decisions.

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
| S-11 | A file with `"version"` set to something that is neither absent nor a known integer (see open question 2) | Any command | As in open question 2 | `tests/test_ledger.py::test_unsupported_version_values` |
| S-12 | A saved ledger file | Save fails part-way through the write (the test makes the temp-file write emit half the bytes, then raise `OSError`) | The original file's bytes are intact and no temp file is left in the directory. The current `path.write_text` would truncate the original, so this test goes red first | `tests/test_cli.py::test_failed_save_leaves_the_old_file_intact` |
| S-13 | A saved ledger file; a fresh path with no file | A normal save | The file holds the full new content, its permission bits are preserved (existing file) and no temp file is left behind | `tests/test_cli.py::test_save_replaces_the_file_and_leaves_no_temp_file` |
| S-14 | The whole repository | `.venv/bin/python -m pytest -q` | Passes locally and in CI | the test command |

Exit criteria coverage: 1 → S-1, S-2, S-3; 2 → S-4, S-5; 3 → S-6, S-7, S-8, S-9; 4 → S-10, S-11; 5 → S-12, S-13; 6 → S-14.

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

**Recommended:** B, because recorded order gets one owner now and M4 needs no second format change; the extra upgrade risk is exactly what exit criteria 3 and 5 already guard. If chosen, it gets an ADR (it changes the data model and two real options were weighed) and a decision row.

## Open questions

1. **Shape A or B** (the milestone's own open question). Recommendation: B. A is safer for M2 alone but costs a second format change in M4.
2. **Version values that are not "future"** (`1`, `0`, `"2"`, `null`, `true`). Options: (a) reject everything except "absent" and the integer `2`, naming the value; (b) treat only integers greater than 2 as errors and the rest as v0.1. Recommendation: (a). Version 1 never existed, and guessing risks misreading a file, which is what D-2 is meant to prevent.
3. **Overpaying.** Can a settlement be larger than what the payer owes (their balance flips sign)? Options: (a) allow it, since it records something that happened in real life; (b) reject it. Recommendation: (a). The milestone doesn't ask for a limit, and (b) would make the order in which you record things matter.
4. **A save that fails with `OSError`.** Today it ends in a traceback. Options: (a) leave it as is (M2 only promises the old file stays intact); (b) catch it in `cli` and print `error: could not save <path>: ...`, exit 1. Recommendation: (a) for M2, to stay in scope.

Known limits, not addressed (say if you want them): saving through a symlink replaces the link with a regular file; two `tally` processes saving at once can lose one write (last rename wins); on some network filesystems `os.replace` is not atomic.

## Proposed ticket cut (for the plan PR, after the Owner agrees)

- **T-003 Versioned format** (S-6–S-11): first commit the v0.1 fixture, generated by the current code, together with its expected balances; then add `version`, the v0.1 → v2 mapping, and rejection. Scope: `src/tally/ledger.py`, `tests/test_ledger.py`, `tests/test_cli.py`, `tests/fixtures/v0.1.json`. Risk: high (sensitive area: file format).
- **T-004 Atomic save** (S-12, S-13): scope `src/tally/cli.py`, `tests/test_cli.py`. Can run in parallel with T-003.
- **T-005 Settlements** (S-1–S-5): blocked by T-003. Scope: `src/tally/ledger.py`, `src/tally/cli.py`, `tests/test_ledger.py`, `tests/test_cli.py`, `tests/test_settle.py`. Risk: high (sensitive area: money and balances).
