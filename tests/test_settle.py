"""Settle up (T-001). Property tests use seeded random ledgers (D-5), so a failure is reproducible by its seed."""

import random

import pytest

from tally.settle import Payment, settle_up

CASES = 500


def random_balances(rng: random.Random) -> dict[str, int]:
    """Balances as Ledger.balances() returns them: member order, integers that sum to 0."""
    n = rng.randint(1, 10)
    values = [rng.randint(-50_000, 50_000) for _ in range(n - 1)]
    values.append(-sum(values))
    if rng.random() < 0.3:  # make zeros and duplicates common: they exercise ties
        values = [rng.choice([0, 500, -500]) for _ in range(n - 1)]
        values.append(-sum(values))
    return {f"m{i}": v for i, v in enumerate(values)}


def apply(balances: dict[str, int], payments: list[Payment]) -> dict[str, int]:
    """A payment from a debtor to a creditor raises the payer's balance and lowers the receiver's."""
    after = dict(balances)
    for p in payments:
        after[p.payer] += p.amount
        after[p.receiver] -= p.amount
    return after


@pytest.mark.parametrize("seed", range(CASES))
def test_payments_clear_every_balance(seed):
    balances = random_balances(random.Random(seed))
    payments = settle_up(balances)
    assert all(v == 0 for v in apply(balances, payments).values()), f"seed {seed}"
    assert all(isinstance(p.amount, int) and p.amount > 0 for p in payments)
    nonzero = sum(1 for v in balances.values() if v != 0)
    assert len(payments) <= max(nonzero - 1, 0)
