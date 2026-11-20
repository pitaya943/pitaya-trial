<!-- pitaya template 0.1.1 · docs/agents/architecture.md -->
# Architecture

A map of the codebase, for orientation before changing it: the main modules, where they live and what each is for. Keep it short; the code is the detail.

`/setup` drafts it from the repository and the Owner corrects it. `/plan` updates it when a plan adds, removes or moves a module.

| Module | Path | Purpose |
| --- | --- | --- |
| ledger | `src/tally/ledger.py` | The domain: `Ledger` (members, expenses, balances), `Expense`, `parse_amount` (text to integer cents), `TallyError`, JSON round-trip via `to_dict`/`from_dict`. |
| cli | `src/tally/cli.py` | `tally` command (`add-member`, `add-expense`, `balances`): loads the JSON ledger file, calls `Ledger`, saves it, formats cents for output. |
| settle | `src/tally/settle.py` | Settle up (from M1): `settle_up(balances)` returns the payments that clear every balance; pure computation, no I/O. |
| tests | `tests/` | `test_ledger.py` for the domain rules, `test_cli.py` for the commands end to end. |

## How the parts connect

`cli` parses arguments, `load`s the ledger file (`--ledger`, default `tally.json`) into a `Ledger`, calls one method, and `save`s it back. All money rules live in `ledger`; `cli` only converts text and formats output. Boundary: `cli` never does arithmetic on money, and the JSON shape written by `to_dict` is a file format users keep, so changing it is a sensitive change (see the harness file).
