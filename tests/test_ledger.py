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


# --- ledger file format (T-003) ---------------------------------------------------


def test_round_trip_keeps_entries_in_order():
    # Recorded order differs from any sort by payer, amount or note, so a sorting writer or reader fails.
    ledger = group("Ana", "Bo", "Cy")
    ledger.add_expense("Cy", 500, ["Ana", "Cy"], "b")
    ledger.add_expense("Ana", 9000, note="c")
    ledger.add_expense("Bo", 1, ["Bo"], "a")
    data = ledger.to_dict()
    assert data["version"] == 2
    assert [(e["kind"], e["payer"], e["amount"]) for e in data["entries"]] == [
        ("expense", "Cy", 500), ("expense", "Ana", 9000), ("expense", "Bo", 1)]
    again = Ledger.from_dict(data)
    assert again.entries == ledger.entries
    assert again.expenses == ledger.expenses
    assert again.to_dict() == data


def test_unsupported_version_values():
    # Otherwise a valid v2 file, so the version alone decides. 1 and True must not be read as v0.1 or v2.
    # One test, not parametrized: the done-when check matches this exact JUnit name.
    # Whole messages, hard-coded: each must come from the "unsupported" branch, never the "newer" one,
    # and "'2'" (a string) must stay distinguishable from 2.
    tail = " (this tally reads 2, or a file with no version)"
    cases = [(1, "unsupported ledger version 1" + tail),
             (0, "unsupported ledger version 0" + tail),
             ("2", "unsupported ledger version '2'" + tail),
             (None, "unsupported ledger version None" + tail),
             (True, "unsupported ledger version True" + tail)]
    for version, message in cases:
        data = {"version": version, "members": ["Ana"], "entries": []}
        with pytest.raises(TallyError) as caught:
            Ledger.from_dict(data)
        assert str(caught.value) == message, version


def test_unknown_entry_kind_is_rejected():
    data = {"version": 2, "members": ["Ana"], "entries": [{"kind": "gift", "payer": "Ana", "amount": 1}]}
    with pytest.raises(TallyError, match="'gift'"):
        Ledger.from_dict(data)


def test_version_must_be_the_integer_2():
    # 2.0 == 2 in Python, so only a type check refuses it; D-11 accepts the integer 2 alone.
    with pytest.raises(TallyError) as caught:
        Ledger.from_dict({"version": 2.0, "members": [], "entries": []})
    assert str(caught.value) == "unsupported ledger version 2.0 (this tally reads 2, or a file with no version)"


# --- settlements (T-005) -----------------------------------------------------------


def example_group():
    """Ana pays 30.00 for three; Bo pays 6.00 for Ana and Bo. Balances: Ana 17.00, Bo -7.00, Cy -10.00."""
    ledger = group("Ana", "Bo", "Cy")
    ledger.add_expense("Ana", 3000)
    ledger.add_expense("Bo", 600, ["Ana", "Bo"])
    assert ledger.balances() == {"Ana": 1700, "Bo": -700, "Cy": -1000}
    return ledger


def test_settlement_moves_balances():
    # S-2. An amount that is not either balance (and not 7.00, which would clear Bo and hide a wrong
    # receiver): a sign flip, a wrong receiver or a settlement counted as an expense all give other numbers.
    ledger = example_group()
    before = ledger.balances()
    ledger.add_settlement(" bo ", "ANA", 250)  # names trimmed and case-insensitive, like members
    after = ledger.balances()
    assert after == {"Ana": before["Ana"] - 250, "Bo": before["Bo"] + 250, "Cy": before["Cy"]}
    assert after == {"Ana": 1450, "Bo": -450, "Cy": -1000}
    assert sum(after.values()) == 0
    # Stored by member key, with the same field names as settle.Payment.
    from tally.ledger import Settlement
    assert ledger.entries[-1] == Settlement("bo", "ana", 250)
    assert ledger.settlements == [Settlement("bo", "ana", 250)]
    # A second settlement in the other direction moves them again, by exactly its amount.
    ledger.add_settlement("Cy", "Bo", 1)
    assert ledger.balances() == {"Ana": 1450, "Bo": -451, "Cy": -999}
    assert sum(ledger.balances().values()) == 0


def test_invalid_settlements_record_nothing():
    # S-3. One test, not parametrized: the done-when check matches this exact JUnit name.
    cases = [
        ("Dee", "Ana", 100, "'Dee' is not a member"),
        ("Ana", "Dee", 100, "'Dee' is not a member"),
        ("Ana", "Ana", 100, "can't settle with themselves"),
        ("ana", "Ana", 100, "can't settle with themselves"),
        ("Bo", "Ana", 0, "a settlement must be more than 0"),
        ("Bo", "Ana", -1, "a settlement must be more than 0"),
        ("Bo", "Ana", 1.234, "a settlement is a whole number of cents"),
    ]
    for payer, receiver, amount, message in cases:
        ledger = group("Ana", "Bo")
        ledger.add_expense("Ana", 1000)
        entries, balances = list(ledger.entries), ledger.balances()
        with pytest.raises(TallyError) as caught:
            ledger.add_settlement(payer, receiver, amount)
        assert message in str(caught.value), (payer, receiver, amount)
        assert ledger.entries == entries, (payer, receiver, amount)
        assert ledger.settlements == [], (payer, receiver, amount)
        assert ledger.balances() == balances, (payer, receiver, amount)


def test_overpaying_settlement_is_recorded():
    # S-15, D-12: paying back more than owed is recorded as given, not capped at what Bo owed (7.00).
    ledger = example_group()
    ledger.add_settlement("Bo", "Ana", 1000)
    assert ledger.balances() == {"Ana": 700, "Bo": 300, "Cy": -1000}
    assert sum(ledger.balances().values()) == 0
    assert len(ledger.settlements) == 1


def test_round_trip_keeps_settlements_among_expenses():
    # The file format (a sensitive area): a settlement is an entry of kind "settlement" between expenses,
    # written with display names, and read back to the same entries in the same order.
    ledger = example_group()
    ledger.add_settlement("bo", "ana", 700)
    ledger.add_expense("Cy", 300, ["Ana", "Cy"])
    data = ledger.to_dict()
    assert data["entries"][2] == {"kind": "settlement", "payer": "Bo", "receiver": "Ana", "amount": 700}
    assert [e["kind"] for e in data["entries"]] == ["expense", "expense", "settlement", "expense"]
    again = Ledger.from_dict(data)
    assert again.entries == ledger.entries
    assert again.balances() == ledger.balances() == {"Ana": 850, "Bo": 0, "Cy": -850}
    assert again.to_dict() == data
