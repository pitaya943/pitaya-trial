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
    assert out.err == "note: greedy method; this may not be the minimum number of payments\n"


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
