import json
import os
import shutil
from pathlib import Path

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


# --- ledger file format (T-003) ---------------------------------------------------

FIXTURE = Path(__file__).parent / "fixtures" / "v0.1.json"
# Printed by the v0.1 `tally balances` on the fixture when it was generated. Hard-coded on purpose:
# recomputing them with the current code could not catch a change in how old files are read (learning 1).
V01_BALANCES = "Ana\t80.82\nbo\t-29.12\nCy\t-15.02\nDeeDee\t-36.68\n"


def test_v01_fixture_loads_with_the_same_balances(capsys):
    assert main(["--ledger", str(FIXTURE), "balances"]) == 0
    assert capsys.readouterr().out == V01_BALANCES


def _copy_of_fixture(tmp_path):
    """A copy of the fixture with an old mtime, so a rewrite shows up even on a coarse clock."""
    path = tmp_path / "v01.json"
    shutil.copyfile(FIXTURE, path)
    os.utime(path, ns=(1_000_000_000, 1_000_000_000))
    return path


def test_cli_writes_version_2(tmp_path):
    path, ledger = _group(tmp_path)
    data = json.loads(path.read_text())
    assert data["version"] == 2
    assert "expenses" not in data
    assert [e["kind"] for e in data["entries"]] == ["expense", "expense"]
    assert [(e["payer"], e["amount"]) for e in data["entries"]] == [("Ana", 3000), ("Bo", 600)]


def test_read_only_commands_do_not_upgrade_a_v01_file(tmp_path, capsys):
    # Any write would change the bytes: the v2 writer adds "version" and renames "expenses".
    path = _copy_of_fixture(tmp_path)
    before, mtime = path.read_bytes(), path.stat().st_mtime_ns
    for command in ("balances", "settle-up"):
        assert main(["--ledger", str(path), command]) == 0
        assert path.read_bytes() == before
        assert path.stat().st_mtime_ns == mtime
    assert capsys.readouterr().out.startswith(V01_BALANCES)


def test_v01_file_is_written_as_version_2_on_save(tmp_path, capsys):
    path = _copy_of_fixture(tmp_path)
    assert main(["--ledger", str(path), "add-member", "Dee"]) == 0
    data = json.loads(path.read_text())
    assert data["version"] == 2
    assert "expenses" not in data
    old = json.loads(FIXTURE.read_text())["expenses"]
    assert data["entries"] == [{"kind": "expense", **e} for e in old]  # same expenses, same order
    capsys.readouterr()
    assert main(["--ledger", str(path), "balances"]) == 0
    assert capsys.readouterr().out == V01_BALANCES + "Dee\t0.00\n"


COMMANDS = [["add-member", "Dee"], ["add-expense", "Ana", "1.00"], ["balances"], ["settle-up"]]


def test_unknown_future_version_is_rejected_and_not_written(tmp_path, capsys):
    # One test, not parametrized: the done-when check matches this exact JUnit name.
    for version in (3, 99):
        for command in COMMANDS:
            case = f"version {version}, {command[0]}"
            # Hand-formatted (one line), so a stray save() would reformat it even if the content matched.
            path = tmp_path / f"v{version}-{command[0]}.json"
            path.write_text(f'{{"version": {version}, "members": ["Ana", "Bo"], "entries": []}}')
            os.utime(path, ns=(1_000_000_000, 1_000_000_000))
            before, mtime = path.read_bytes(), path.stat().st_mtime_ns
            assert main(["--ledger", str(path), *command]) == 1, case
            # The whole stderr, not a fragment: "version 3" alone would also match the
            # "unsupported ledger version 3" branch, so deleting the "newer" branch would go unnoticed.
            expected = f"error: ledger version {version} is newer than this tally supports (2)\n"
            assert capsys.readouterr().err == expected, case
            assert path.read_bytes() == before, case
            assert path.stat().st_mtime_ns == mtime, case


# --- settle (T-005) ----------------------------------------------------------------


def test_cli_settle_updates_balances(tmp_path, capsys):
    # S-1. A sign-flipped settle gives Bo -14.00 and Ana 24.00.
    _, ledger = _group(tmp_path)
    assert main(ledger + ["settle", "Bo", "Ana", "7.00"]) == 0
    capsys.readouterr()
    assert main(ledger + ["balances"]) == 0
    assert capsys.readouterr().out == "Ana\t10.00\nBo\t0.00\nCy\t-10.00\n"


def test_cli_settle_errors_leave_the_file_unchanged(tmp_path, capsys):
    # S-3. One test, not parametrized: the done-when check matches this exact JUnit name.
    path, ledger = _group(tmp_path)
    os.utime(path, ns=(1_000_000_000, 1_000_000_000))  # an old mtime, so any rewrite shows
    before, mtime = path.read_bytes(), path.stat().st_mtime_ns
    cases = [
        (["Dee", "Ana", "1.00"], "'Dee' is not a member"),
        (["Ana", "Dee", "1.00"], "'Dee' is not a member"),
        (["Ana", "Ana", "1.00"], "can't settle with themselves"),
        (["ana", "Ana", "1.00"], "can't settle with themselves"),
        (["Bo", "Ana", "0"], "a settlement must be more than 0"),
        (["Bo", "Ana", "-1"], "not an amount: '-1'"),
        (["Bo", "Ana", "1.234"], "not an amount: '1.234'"),
    ]
    for args, message in cases:
        capsys.readouterr()
        assert main(ledger + ["settle"] + args) == 1, args
        err = capsys.readouterr().err
        assert err.startswith("error: ") and message in err, (args, err)
        assert path.read_bytes() == before, args
        assert path.stat().st_mtime_ns == mtime, args


def test_cli_settling_every_settle_up_payment_clears_balances(tmp_path, capsys):
    # S-5: settle-up's output format fed back as settle's input, line by line.
    _, ledger = _group(tmp_path)
    capsys.readouterr()
    assert main(ledger + ["settle-up"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines  # the example group is not settled yet
    for line in lines:
        assert main(ledger + ["settle"] + line.split("\t")) == 0, line
    capsys.readouterr()
    assert main(ledger + ["balances"]) == 0
    assert capsys.readouterr().out == "Ana\t0.00\nBo\t0.00\nCy\t0.00\n"
    assert main(ledger + ["settle-up"]) == 0
    assert capsys.readouterr().out == ""


# --- malformed ledger files (T-006) --------------------------------------------------

EVERY_COMMAND = [["balances"], ["settle-up"], ["add-member", "Dee"], ["add-expense", "Ana", "1.00"],
                 ["settle", "Bo", "Ana", "1.00"]]


def _refused_untouched(path, text, capsys, expected_err):
    """Run every command on a file holding `text`; each must exit 1 with exactly `expected_err`
    on stderr (one line, so no traceback) and leave the file's bytes and mtime as they were."""
    for command in EVERY_COMMAND:
        case = (text, command[0])
        # Hand-formatted (one line, no trailing newline) and an old mtime, so a stray save()
        # would show in the bytes even if it wrote the same content.
        path.write_text(text)
        os.utime(path, ns=(1_000_000_000, 1_000_000_000))
        before, mtime = path.read_bytes(), path.stat().st_mtime_ns
        assert main(["--ledger", str(path), *command]) == 1, case
        out = capsys.readouterr()
        assert out.err == expected_err, case
        assert out.out == "", case
        assert path.read_bytes() == before, case
        assert path.stat().st_mtime_ns == mtime, case


def test_v2_file_without_entries_is_refused(tmp_path, capsys):
    # S-16. One test, not parametrized: the done-when check matches this exact JUnit name.
    # With T-003's reader each of these loaded as an empty ledger and the next save erased the expense.
    expense = '{"payer": "Ana", "amount": 1000, "participants": ["Ana", "Bo"], "note": ""}'
    texts = [f'{{"version": 2, "members": ["Ana", "Bo"], "expenses": [{expense}]}}',  # leftover v0.1 key
             '{"version": 2, "members": ["Ana", "Bo"]}',                              # no list at all
             '{"version": 2, "members": ["Ana", "Bo"], "entries": null}',             # not a list either
             f'{{"version": 2, "members": ["Ana", "Bo"], "entries": {expense}}}']
    for text in texts:
        _refused_untouched(tmp_path / "t.json", text, capsys,
                           'error: ledger version 2 needs an "entries" list\n')


def test_entries_without_version_is_refused(tmp_path, capsys):
    # S-17. A version 2 body without its version line: read as v0.1 it would have zero expenses,
    # and the next save would write it out empty.
    entry = '{"kind": "expense", "payer": "Ana", "amount": 1000, "participants": ["Ana", "Bo"], "note": ""}'
    for text in (f'{{"members": ["Ana", "Bo"], "entries": [{entry}]}}',
                 '{"members": ["Ana", "Bo"], "entries": []}'):
        _refused_untouched(tmp_path / "t.json", text, capsys,
                           'error: ledger file has "entries" but no "version"\n')


def test_unreadable_or_non_object_file_is_refused(tmp_path, capsys):
    # S-18. Whole stderr: one "error: " line and nothing else, so a traceback can't hide in it.
    cases = [('{"members": [', "ledger file is not valid JSON: Expecting value at line 1, column 14"),
             ("", "ledger file is not valid JSON: Expecting value at line 1, column 1"),
             ('{"members": ["Ana"]} x', "ledger file is not valid JSON: Extra data at line 1, column 22"),
             ("[]", "ledger file must be a JSON object, not a list"),
             ('"x"', "ledger file must be a JSON object, not a string"),
             ("3", "ledger file must be a JSON object, not a number"),
             ("null", "ledger file must be a JSON object, not null")]
    for text, message in cases:
        _refused_untouched(tmp_path / "t.json", text, capsys, f"error: {message}\n")
    # Bytes that aren't UTF-8 text at all are refused the same way, not with a UnicodeDecodeError.
    path = tmp_path / "bin.json"
    path.write_bytes(b'{"members": ["\xff"]}')
    before = path.read_bytes()
    assert main(["--ledger", str(path), "add-member", "Dee"]) == 1
    assert capsys.readouterr().err == "error: ledger file is not UTF-8 text\n"
    assert path.read_bytes() == before
