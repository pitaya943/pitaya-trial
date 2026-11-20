"""Settle up: the payments that would clear every balance. Pure computation, no I/O.

A positive balance means others owe that member (a creditor); a negative one means they owe (a debtor).
A payment from debtor to creditor raises the debtor's balance and lowers the creditor's by its amount.

Two methods (ADR 0001):
- exact, for at most EXACT_LIMIT members with a non-zero balance: the true minimum number of payments;
- greedy, above that: at most n-1 payments, not always the minimum.
"""

from __future__ import annotations

from dataclasses import dataclass

EXACT_LIMIT = 12  # members with a non-zero balance; ADR 0001


@dataclass(frozen=True)
class Payment:
    payer: str
    receiver: str
    amount: int  # cents, always > 0


def uses_exact(balances: dict[str, int]) -> bool:
    """True when settle_up returns the exact minimum for these balances."""
    return sum(1 for v in balances.values() if v != 0) <= EXACT_LIMIT


def settle_up(balances: dict[str, int]) -> list[Payment]:
    """The payments that clear every balance: the exact minimum when uses_exact(), else greedy.

    `balances` is what `Ledger.balances()` returns: display name -> cents, in member order, summing to 0.
    The result is deterministic; ties go to the member added first.
    """
    if not uses_exact(balances):
        return _greedy(balances)
    payments: list[Payment] = []
    for group in _zero_sum_groups(balances):
        payments += _greedy({name: balances[name] for name in group})
    return payments


def _zero_sum_groups(balances: dict[str, int]) -> list[list[str]]:
    """Split the members with a non-zero balance into as many zero-sum groups as possible.

    Why this gives the minimum: a group of m members whose balances sum to 0 can be settled with m-1
    payments, and no fewer if it has no smaller zero-sum subgroup. So with k groups, n members need
    n-k payments, and the minimum is n minus the largest k.

    How: order the members; every prefix whose sum is 0 closes a group. dp[mask] is the largest number of
    zero-sum prefixes over all orderings of the members in `mask`:
        dp[mask] = max over i in mask of dp[mask without i] + (1 if sum(mask) == 0 else 0)
    That is O(n * 2^n): about 49k steps for n = 12. (ADR 0001 estimated O(3^n) for the classic
    submask enumeration; this prefix formulation is cheaper and gives the same answer.)
    """
    names = [name for name, v in balances.items() if v != 0]  # member order
    n = len(names)
    if n == 0:
        return []
    full = (1 << n) - 1
    total = [0] * (1 << n)
    for mask in range(1, 1 << n):
        low = mask & -mask
        total[mask] = total[mask ^ low] + balances[names[low.bit_length() - 1]]
    dp = [0] * (1 << n)
    for mask in range(1, 1 << n):
        best = max(dp[mask ^ (1 << i)] for i in range(n) if mask >> i & 1)
        dp[mask] = best + (total[mask] == 0)

    # Recover one optimal ordering, back to front. Taking the lowest index that keeps the optimum makes
    # the result deterministic.
    order: list[int] = []
    mask = full
    while mask:
        bonus = total[mask] == 0
        i = next(i for i in range(n) if mask >> i & 1 and dp[mask ^ (1 << i)] + bonus == dp[mask])
        order.append(i)
        mask ^= 1 << i
    order.reverse()

    # Cut the ordering wherever the running sum returns to 0.
    groups: list[list[str]] = []
    current: list[int] = []
    running = 0
    for i in order:
        current.append(i)
        running += balances[names[i]]
        if running == 0:
            groups.append([names[j] for j in sorted(current)])  # keep member order inside the group
            current = []
    groups.sort(key=lambda group: names.index(group[0]))  # groups in order of their first member
    return groups


def _greedy(balances: dict[str, int]) -> list[Payment]:
    """Greedy settle up: the largest debtor pays the largest creditor, until every balance is 0.

    Each payment zeroes at least one of the two members, so there are at most n-1 payments for n members
    with a non-zero balance. Ties on amount go to the member added first.
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
