import pytest

from tally import Ledger, TallyError, parse_amount


def group(*names):
    ledger = Ledger()
    for n in names:
        ledger.add_member(n)
    return ledger


@pytest.mark.parametrize("text,cents", [("12", 1200), ("12.5", 1250), ("12.50", 1250), ("0.01", 1), (" 3.07 ", 307)])
def test_parse_amount(text, cents):
    assert parse_amount(text) == cents


@pytest.mark.parametrize("text", ["", "-1", "1.234", "abc", "1,50", "1."])
def test_parse_amount_rejects(text):
    with pytest.raises(TallyError):
        parse_amount(text)


def test_names_are_case_insensitive_and_trimmed():
    ledger = group(" Ana ")
    with pytest.raises(TallyError, match="already a member"):
        ledger.add_member("ana")
    ledger.add_member("Bo")
    ledger.add_expense("ANA", 1000)
    assert ledger.balances() == {"Ana": 500, "Bo": -500}


def test_equal_split_gives_leftover_cents_in_listed_order():
    ledger = group("Ana", "Bo", "Cy")
    expense = ledger.add_expense("Ana", 1000, ["Cy", "Ana", "Bo"])
    assert Ledger.shares(expense) == {"cy": 334, "ana": 333, "bo": 333}


def test_balances_sum_to_zero():
    ledger = group("Ana", "Bo", "Cy")
    ledger.add_expense("Ana", 1001)
    ledger.add_expense("Bo", 2999, ["Bo", "Cy"])
    ledger.add_expense("Cy", 7, ["Ana"])
    assert sum(ledger.balances().values()) == 0


@pytest.mark.parametrize("payer,amount,among,message", [
    ("Ana", 0, None, "more than 0"),
    ("Dee", 100, None, "not a member"),
    ("Ana", 100, ["Bo", "Dee"], "not a member"),
    ("Ana", 100, ["Bo", "bo"], "listed twice"),
])
def test_invalid_expenses_record_nothing(payer, amount, among, message):
    ledger = group("Ana", "Bo")
    with pytest.raises(TallyError, match=message):
        ledger.add_expense(payer, amount, among)
    assert ledger.expenses == []


def test_round_trip_through_dict():
    ledger = group("Ana", "Bo")
    ledger.add_expense("Ana", 999, note="taxi")
    again = Ledger.from_dict(ledger.to_dict())
    assert again.balances() == ledger.balances()
