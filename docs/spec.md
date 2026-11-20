# tally: specification

tally keeps a ledger for one group of people who share expenses, such as a trip or a shared flat, and tells them who owes whom.

## Rules that always hold

1. **Money is an integer number of cents.** Never a float. Input like `12.50` is parsed to `1250`; anything with more than two decimals is rejected.
2. **Names are case-insensitive and trimmed.** `" Ana "` and `"ana"` are the same member. They are shown as first added.
3. **Balances always sum to zero.** For every ledger, the sum of all members' balances is exactly 0 cents.
4. **Errors are explicit.** Invalid input raises `TallyError` with a message that says what was wrong; nothing is half-recorded.

## Done (version 0.1)

- **Members:** add a member; adding the same name twice is an error.
- **Expenses:** record an expense paid by one member, split equally among a list of members (default: everyone). Amount must be positive. Payer and every participant must be members.
- **Equal split remainder:** when the amount doesn't divide evenly, the leftover cents go one each to participants in the order they were listed, so the shares differ by at most 1 cent.
- **Balances:** each member's balance is what they paid minus their share of everything. Positive means others owe them.
- **CLI:** `tally add-member`, `tally add-expense`, `tally balances`, working on a JSON ledger file (`--ledger`, default `tally.json`).

## Wanted next (not built)

These are for the roadmap; they are not specified in detail yet, and questions about them go to the Owner.

1. **Unequal splits:** split by exact amounts, by percentages, or by shares (2:1:1).
2. **Settle up:** a list of payments that clears every balance, with as few payments as possible.
3. **Settlements as entries:** record that a member paid another back, so balances update.
4. **History:** list expenses, edit or delete one, with balances recomputed.
5. **Export and import:** write the ledger to CSV and read it back.
6. **Currencies:** expenses in more than one currency, converted at a rate given per expense, balances in one base currency.
