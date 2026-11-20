"""Settle up (T-001). Property tests use seeded random ledgers (D-5), so a failure is reproducible by its seed."""

import random
import time

import pytest

from tally.settle import EXACT_LIMIT, Payment, _greedy, settle_up, uses_exact

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


@pytest.mark.parametrize("seed", range(50))
def test_same_balances_give_same_payments(seed):
    balances = random_balances(random.Random(seed))
    assert settle_up(balances) == settle_up(dict(balances))


def test_ties_go_to_the_member_added_first():
    # Ana and Bo owe the same; Cy and Di are owed the same. Member order decides who goes first.
    balances = {"Di": 500, "Ana": -500, "Cy": 500, "Bo": -500}
    assert settle_up(balances) == [Payment("Ana", "Di", 500), Payment("Bo", "Cy", 500)]


# --- T-002: exact minimum for up to 12 members ---------------------------------------------


def grouped_balances(rng: random.Random, max_members: int = 7) -> dict[str, int]:
    """Balances built from random zero-sum groups, then shuffled, so a smaller minimum often exists."""
    values: list[int] = []
    while len(values) < max_members - 1:
        size = rng.randint(2, min(3, max_members - len(values)))
        group = [rng.choice([-3, -2, -1, 1, 2, 3]) * 100 for _ in range(size - 1)]
        values += group + [-sum(group)]
    values = values[:max_members]
    values[-1] -= sum(values)  # keep the total at 0 if the last group was cut
    rng.shuffle(values)
    return {f"m{i}": v for i, v in enumerate(values)}


def set_partitions(items: list[int]):
    """Every partition of `items` into blocks (Bell(7) = 877 for 7 items)."""
    if not items:
        yield []
        return
    first, rest = items[0], items[1:]
    for partition in set_partitions(rest):
        for i in range(len(partition)):
            yield partition[:i] + [[first] + partition[i]] + partition[i + 1:]
        yield [[first]] + partition


def oracle_minimum(balances: dict[str, int]) -> int:
    """n minus the largest number of blocks that each sum to 0, over every partition: the true minimum."""
    values = [v for v in balances.values() if v != 0]
    if not values:
        return 0
    best = max(len(p) for p in set_partitions(values) if all(sum(block) == 0 for block in p))
    return len(values) - best


@pytest.mark.parametrize("seed", range(300))
def test_exact_matches_brute_force_minimum(seed):
    balances = grouped_balances(random.Random(seed))
    payments = settle_up(balances)
    assert all(v == 0 for v in apply(balances, payments).values()), f"seed {seed}"
    assert len(payments) == oracle_minimum(balances), f"seed {seed}"


def test_exact_beats_greedy_when_a_smaller_group_clears_itself():
    # {A, D, E} and {B, C} each sum to 0, so 2 + 1 = 3 payments suffice; greedy needs 4. Replaces the ticket's {+5, -5, +3, -3} example, where greedy is already minimal.
    balances = {"A": 500, "B": 400, "C": -400, "D": -300, "E": -200}
    exact = settle_up(balances)
    assert len(exact) == 3
    assert all(v == 0 for v in apply(balances, exact).values())
    assert len(_greedy(balances)) == 4


def test_exact_is_fast_at_the_limit():
    rng = random.Random(12)
    values = [rng.choice([-1, 1]) * rng.randint(1, 9) * 100 for _ in range(EXACT_LIMIT - 1)]
    values.append(-sum(values) or 100)  # never 0, so all 12 members have a non-zero balance
    if sum(values):
        values[0] -= sum(values)
    balances = {f"m{i}": v for i, v in enumerate(values)}
    assert sum(1 for v in balances.values() if v) == EXACT_LIMIT and uses_exact(balances)
    start = time.perf_counter()
    payments = settle_up(balances)
    assert time.perf_counter() - start < 1.0
    assert all(v == 0 for v in apply(balances, payments).values())


def test_greedy_above_the_limit():
    at_limit = {f"m{i}": (100 if i % 2 else -100) for i in range(EXACT_LIMIT)}
    above = {f"m{i}": (100 if i % 2 else -100) for i in range(EXACT_LIMIT + 2)}
    assert uses_exact(at_limit)
    assert not uses_exact(above)
    assert settle_up(above) == _greedy(above)


@pytest.mark.parametrize("nonzero, exact", [(EXACT_LIMIT, True), (EXACT_LIMIT + 1, False)])
def test_exact_limit_boundary(nonzero, exact):
    # Pins the cap itself: exactly 12 members with a non-zero balance use exact, exactly 13 use greedy.
    # Zero balances don't count toward the cap.
    values = [100 * (i + 1) for i in range(nonzero - 1)]
    values.append(-sum(values))
    balances = {f"m{i}": v for i, v in enumerate(values)} | {"z0": 0, "z1": 0}
    assert uses_exact(balances) is exact
    if not exact:
        assert settle_up(balances) == _greedy(balances)
