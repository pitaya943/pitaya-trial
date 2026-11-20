import pytest

from tally.cli import main


def test_cli_records_and_prints_balances(tmp_path, capsys):
    ledger = ["--ledger", str(tmp_path / "t.json")]
    assert main(ledger + ["add-member", "Ana"]) == 0
    assert main(ledger + ["add-member", "Bo"]) == 0
    assert main(ledger + ["add-expense", "Ana", "10.01"]) == 0
    assert main(ledger + ["balances"]) == 0
    assert capsys.readouterr().out == "Ana\t5.00\nBo\t-5.00\n"


def test_cli_reports_errors_without_saving(tmp_path, capsys):
    path = tmp_path / "t.json"
    ledger = ["--ledger", str(path)]
    main(ledger + ["add-member", "Ana"])
    before = path.read_text()
    assert main(ledger + ["add-expense", "Ana", "1.234"]) == 1
    assert "not an amount" in capsys.readouterr().err
    assert path.read_text() == before


def _group(tmp_path):
    """Ana pays 30.00 for three; Bo pays 6.00 for Ana and Bo. Balances: Ana 17.00, Bo -7.00, Cy -10.00."""
    path = tmp_path / "t.json"
    ledger = ["--ledger", str(path)]
    for name in ("Ana", "Bo", "Cy"):
        main(ledger + ["add-member", name])
    main(ledger + ["add-expense", "Ana", "30.00"])
    main(ledger + ["add-expense", "Bo", "6.00", "--among", "Ana", "Bo"])
    return path, ledger


def test_cli_settle_up_prints_payments(tmp_path, capsys):
    _, ledger = _group(tmp_path)
    capsys.readouterr()
    assert main(ledger + ["settle-up"]) == 0
    out = capsys.readouterr()
    assert out.out == "Cy\tAna\t10.00\nBo\tAna\t7.00\n"
    assert out.err == ""  # 3 members: exact method, so no note (T-002 condition 4)


def test_cli_settle_up_does_not_write_the_ledger(tmp_path):
    path, ledger = _group(tmp_path)
    before = path.read_bytes()
    assert main(ledger + ["settle-up"]) == 0
    assert path.read_bytes() == before


def test_cli_settle_up_prints_nothing_when_settled(tmp_path, capsys):
    path = tmp_path / "t.json"
    ledger = ["--ledger", str(path)]
    main(ledger + ["add-member", "Ana"])
    main(ledger + ["add-member", "Bo"])
    capsys.readouterr()
    assert main(ledger + ["settle-up"]) == 0
    assert capsys.readouterr().out == ""


def test_cli_settle_up_notes_greedy_above_the_limit(tmp_path, capsys):
    path = tmp_path / "t.json"
    ledger = ["--ledger", str(path)]
    names = [f"M{i:02d}" for i in range(14)]
    for name in names:
        main(ledger + ["add-member", name])
    for i in range(0, 14, 2):  # 7 pairs, each a different amount: 14 members with a non-zero balance
        main(ledger + ["add-expense", names[i], f"{i + 1}.00", "--among", names[i], names[i + 1]])
    capsys.readouterr()
    assert main(ledger + ["settle-up"]) == 0
    out = capsys.readouterr()
    assert len(out.out.splitlines()) >= 7
    assert out.err == "note: greedy method; this may not be the minimum number of payments\n"


def test_cli_settle_up_keeps_a_hand_formatted_ledger_untouched(tmp_path):
    # A ledger not in save()'s format: a stray save() would rewrite it, so bytes and mtime catch any write.
    path = tmp_path / "t.json"
    path.write_text('{"members": ["Ana", "Bo"], "expenses": [{"payer": "Ana", "amount": 1000, "participants": ["Ana", "Bo"]}]}')
    before, mtime = path.read_bytes(), path.stat().st_mtime_ns
    assert main(["--ledger", str(path), "settle-up"]) == 0
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime


@pytest.mark.parametrize("members, note", [(12, False), (13, True)])
def test_cli_settle_up_note_at_the_limit(tmp_path, capsys, members, note):
    # Pins the 12/13 boundary at the CLI: one payer covers everyone else, so all members are non-zero.
    path = tmp_path / "t.json"
    ledger = ["--ledger", str(path)]
    names = [f"M{i:02d}" for i in range(members)]
    for name in names:
        main(ledger + ["add-member", name])
    main(ledger + ["add-expense", names[0], f"{members - 1}.00", "--among", *names[1:]])
    capsys.readouterr()
    assert main(ledger + ["settle-up"]) == 0
    expected = "note: greedy method; this may not be the minimum number of payments\n" if note else ""
    assert capsys.readouterr().err == expected
