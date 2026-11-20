"""Command-line front end: tally add-member | add-expense | settle | balances | settle-up, on a JSON ledger file."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from .ledger import Ledger, TallyError, parse_amount
from .settle import settle_up, uses_exact


def load(path: Path) -> Ledger:
    """Read the ledger file, or start an empty ledger when there is none.

    A file that can't be decoded raises TallyError (one line, no traceback) before any command runs,
    so nothing reaches save() and the file stays as it was (D-14). Shape checks live in from_dict.
    """
    if not path.exists():
        return Ledger()
    try:
        data = json.loads(path.read_bytes().decode("utf-8"))
    except UnicodeDecodeError:
        raise TallyError("ledger file is not UTF-8 text") from None
    except json.JSONDecodeError as exc:
        # exc.msg without its "(char n)" tail; line and column are what an editor shows.
        raise TallyError(f"ledger file is not valid JSON: {exc.msg} at line {exc.lineno}, "
                         f"column {exc.colno}") from None
    except RecursionError:  # deeper nesting than the decoder's stack allows
        raise TallyError("ledger file is not valid JSON: nested too deeply") from None
    except ValueError:
        # After JSONDecodeError (a subclass), the one plain ValueError json.loads raises on text is an
        # integer over Python's digit limit (3.11+). A fixed message: Python's own wording varies by version.
        raise TallyError("ledger file is not valid JSON: a number has too many digits") from None
    return Ledger.from_dict(data)


def save(ledger: Ledger, path: Path) -> None:
    """Write the ledger atomically: a temp file in the same directory, renamed over `path`.

    Readers see either the old file or the new one, never a partial write. The temp file sits
    next to the ledger because `os.replace` is only atomic within one filesystem. On any error
    the temp file is removed and the error re-raised, so the old ledger stays as it was.
    """
    text = json.dumps(ledger.to_dict(), indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())  # the data is on disk before the rename makes it the ledger
        if path.exists():
            # mkstemp creates the file 0o600; keep the permission bits the ledger already had.
            os.chmod(tmp, stat.S_IMODE(path.stat().st_mode))
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def cents(value: int) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{abs(value) // 100}.{abs(value) % 100:02d}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tally", description="Split shared expenses in a group.")
    parser.add_argument("--ledger", type=Path, default=Path("tally.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("add-member").add_argument("name")
    exp = sub.add_parser("add-expense")
    exp.add_argument("payer")
    exp.add_argument("amount", help="for example 12.50")
    exp.add_argument("--among", nargs="+", help="participants (default: everyone)")
    exp.add_argument("--note", default="")
    st = sub.add_parser("settle", help="record that <payer> paid <receiver> back")
    st.add_argument("payer")
    st.add_argument("receiver")
    st.add_argument("amount", help="for example 7.00")
    sub.add_parser("balances")
    sub.add_parser("settle-up", help="list payments that would clear every balance (writes nothing)")
    args = parser.parse_args(argv)

    try:
        ledger = load(args.ledger)
        if args.command == "add-member":
            ledger.add_member(args.name)
        elif args.command == "add-expense":
            ledger.add_expense(args.payer, parse_amount(args.amount), args.among, args.note)
        elif args.command == "settle":
            ledger.add_settlement(args.payer, args.receiver, parse_amount(args.amount))
        elif args.command == "balances":
            for name, value in ledger.balances().items():
                print(f"{name}\t{cents(value)}")
            return 0
        else:  # settle-up: read only, so it returns before save()
            balances = ledger.balances()
            payments = settle_up(balances)
            for p in payments:
                print(f"{p.payer}\t{p.receiver}\t{cents(p.amount)}")
            if payments and not uses_exact(balances):
                print("note: greedy method; this may not be the minimum number of payments", file=sys.stderr)
            return 0
        save(ledger, args.ledger)
    except TallyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
