<!-- pitaya template 0.1.1 · docs/agents/architecture.md -->
# Architecture

A map of the codebase, for orientation before changing it: the main modules, where they live and what each is for. Keep it short; the code is the detail.

`/setup` drafts it from the repository and the Owner corrects it. `/plan` updates it when a plan adds, removes or moves a module.

| Module | Path | Purpose |
| --- | --- | --- |
| ledger | `src/tally/ledger.py` | The domain: `Ledger` (members, and `entries`: expenses and settlements in recorded order; balances), `Expense`, `Settlement`, `parse_amount` (text to integer cents), `TallyError`, the file format version (`FORMAT_VERSION`) and JSON round-trip via `to_dict`/`from_dict`, including reading v0.1 files (from M2, ADR 0003). |
| cli | `src/tally/cli.py` | `tally` command (`add-member`, `add-expense`, `balances`, `settle-up`, `settle` from M2): loads the JSON ledger file, calls `Ledger`, saves it atomically (temp file and rename, from M2), formats cents for output. |
| settle | `src/tally/settle.py` | Settle up (from M1): `settle_up(balances)` returns the payments that clear every balance; pure computation, no I/O. |
| tests | `tests/` | `test_ledger.py` for the domain rules, `test_cli.py` for the commands end to end, `test_settle.py` for settle up, `test_save.py` for atomic save (from M2), `fixtures/v0.1.json` as a v0.1 file kept readable forever. |

## How the parts connect

`cli` parses arguments, `load`s the ledger file (`--ledger`, default `tally.json`) into a `Ledger`, calls one method, and `save`s it back. All money rules live in `ledger`; `cli` only converts text and formats output. Boundary: `cli` never does arithmetic on money, and the JSON shape written by `to_dict` is a file format users keep, so changing it is a sensitive change (see the harness file).
