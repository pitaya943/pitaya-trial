"""Settle up: the payments that would clear every balance. Pure computation, no I/O.

A positive balance means others owe that member (a creditor); a negative one means they owe (a debtor).
A payment from debtor to creditor raises the debtor's balance and lowers the creditor's by its amount.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Payment:
    payer: str
    receiver: str
    amount: int  # cents, always > 0


def settle_up(balances: dict[str, int]) -> list[Payment]:
    """Greedy settle up: the largest debtor pays the largest creditor, until every balance is 0.

    `balances` is what `Ledger.balances()` returns: display name -> cents, in member order, summing to 0.
    Each payment zeroes at least one of the two members, so there are at most n-1 payments for n members
    with a non-zero balance. This is not always the minimum (see ADR 0001; T-002 adds the exact method).

    Determinism: ties on amount go to the member added first. Every pick is "largest amount, then
    earliest position", so the same balances always give the same payments.
    """
    order = {name: i for i, name in enumerate(balances)}
    owed = {name: v for name, v in balances.items() if v > 0}     # creditors: what they should receive
    owes = {name: -v for name, v in balances.items() if v < 0}    # debtors: what they should pay

    def largest(side: dict[str, int]) -> str:
        return min(side, key=lambda name: (-side[name], order[name]))

    payments: list[Payment] = []
    while owes and owed:
        debtor, creditor = largest(owes), largest(owed)
        amount = min(owes[debtor], owed[creditor])
        payments.append(Payment(debtor, creditor, amount))
        for side, name in ((owes, debtor), (owed, creditor)):
            side[name] -= amount
            if side[name] == 0:
                del side[name]
    return payments
