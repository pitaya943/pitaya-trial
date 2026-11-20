"""Command-line front end: tally add-member | add-expense | balances | settle-up, on a JSON ledger file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .ledger import Ledger, TallyError, parse_amount
from .settle import settle_up, uses_exact


def load(path: Path) -> Ledger:
    return Ledger.from_dict(json.loads(path.read_text())) if path.exists() else Ledger()


def save(ledger: Ledger, path: Path) -> None:
    path.write_text(json.dumps(ledger.to_dict(), indent=2) + "\n")


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
    sub.add_parser("balances")
    sub.add_parser("settle-up", help="list payments that would clear every balance (writes nothing)")
    args = parser.parse_args(argv)

    try:
        ledger = load(args.ledger)
        if args.command == "add-member":
            ledger.add_member(args.name)
        elif args.command == "add-expense":
            ledger.add_expense(args.payer, parse_amount(args.amount), args.among, args.note)
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
