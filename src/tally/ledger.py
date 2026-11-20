"""The ledger: members, expenses, settlements and balances. Money is always integer cents (spec rule 1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

AMOUNT = re.compile(r"^\d+(\.\d{1,2})?$")

# The ledger file format written by to_dict. A file without "version" is v0.1 and is read forever (D-2);
# any other value is refused rather than guessed (D-11).
FORMAT_VERSION = 2


class TallyError(ValueError):
    """Invalid input; nothing was recorded (spec rule 4)."""


def parse_amount(text: str) -> int:
    """'12.5' -> 1250 cents. Rejects negatives, more than two decimals and non-numbers."""
    text = text.strip()
    if not AMOUNT.match(text):
        raise TallyError(f"not an amount: {text!r} (use digits with at most two decimals, like 12.50)")
    whole, _, frac = text.partition(".")
    return int(whole) * 100 + int(frac.ljust(2, "0") or 0)


def key(name: str) -> str:
    return name.strip().casefold()


@dataclass
class Expense:
    payer: str
    amount: int
    participants: list[str]
    note: str = ""


@dataclass
class Settlement:
    """A recorded payment that pays back what the payer owes. Field names match settle.Payment."""
    payer: str  # member key
    receiver: str  # member key
    amount: int  # cents, > 0


@dataclass
class Ledger:
    members: dict[str, str] = field(default_factory=dict)  # key -> name as first added
    entries: list[Expense | Settlement] = field(default_factory=list)  # the one owner of recorded order (ADR 0003)

    @property
    def expenses(self) -> list[Expense]:
        """Read-only view: the expenses among the entries, in recorded order. Record with add_expense."""
        return [e for e in self.entries if isinstance(e, Expense)]

    @property
    def settlements(self) -> list[Settlement]:
        """Read-only view: the settlements among the entries, in recorded order. Record with add_settlement."""
        return [e for e in self.entries if isinstance(e, Settlement)]

    def add_member(self, name: str) -> None:
        if not name.strip():
            raise TallyError("a member needs a name")
        if key(name) in self.members:
            raise TallyError(f"{name.strip()!r} is already a member")
        self.members[key(name)] = name.strip()

    def _member(self, name: str) -> str:
        if key(name) not in self.members:
            raise TallyError(f"{name.strip()!r} is not a member")
        return key(name)

    def add_expense(self, payer: str, amount: int, participants: list[str] | None = None, note: str = "") -> Expense:
        if amount <= 0:
            raise TallyError("an expense must be more than 0")
        who = self._member(payer)
        among = [self._member(p) for p in participants] if participants else list(self.members)
        if len(set(among)) != len(among):
            raise TallyError("a participant is listed twice")
        expense = Expense(who, amount, among, note)
        self.entries.append(expense)
        return expense

    def add_settlement(self, payer: str, receiver: str, amount: int) -> Settlement:
        """Record that `payer` paid `receiver` back `amount` cents. More than the payer owes is allowed (D-12)."""
        # `type(...) is int`: a float like 1.234 is not cents, and a bool is not an amount.
        if type(amount) is not int:
            raise TallyError(f"a settlement is a whole number of cents, not {amount!r}")
        if amount <= 0:
            raise TallyError("a settlement must be more than 0")
        who, to = self._member(payer), self._member(receiver)
        if who == to:
            raise TallyError(f"{self.members[who]!r} can't settle with themselves")
        settlement = Settlement(who, to, amount)
        self.entries.append(settlement)
        return settlement

    @staticmethod
    def shares(expense: Expense) -> dict[str, int]:
        """Equal split; leftover cents go one each to participants in listed order."""
        base, extra = divmod(expense.amount, len(expense.participants))
        return {p: base + (1 if i < extra else 0) for i, p in enumerate(expense.participants)}

    def balances(self) -> dict[str, int]:
        """Paid minus owed, per member, by display name. Always sums to 0 (spec rule 3)."""
        totals = {k: 0 for k in self.members}
        for entry in self.entries:
            # Paying raises the payer's balance either way; an expense's shares, or a settlement's
            # receiver, take the same amount back off, which keeps the sum at 0.
            totals[entry.payer] += entry.amount
            if isinstance(entry, Settlement):
                totals[entry.receiver] -= entry.amount
            else:
                for member, share in self.shares(entry).items():
                    totals[member] -= share
        return {self.members[k]: v for k, v in totals.items()}

    # --- storage -----------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"version": FORMAT_VERSION,
                "members": list(self.members.values()),
                "entries": [self._entry_to_dict(e) for e in self.entries]}

    def _entry_to_dict(self, e: Expense | Settlement) -> dict:
        if isinstance(e, Settlement):
            return {"kind": "settlement", "payer": self.members[e.payer],
                    "receiver": self.members[e.receiver], "amount": e.amount}
        return {"kind": "expense", "payer": self.members[e.payer], "amount": e.amount,
                "participants": [self.members[p] for p in e.participants], "note": e.note}

    @classmethod
    def from_dict(cls, data: dict) -> "Ledger":
        """Read a v0.1 file (no "version", an "expenses" list) or a version 2 file; refuse anything else.

        Every entry goes through add_member / add_expense, so a file gets the same validation as the CLI.
        """
        if "version" not in data:  # v0.1: each expense becomes an entry of kind "expense", same order
            entries = [{"kind": "expense", **e} for e in data.get("expenses", [])]
        else:
            version = data["version"]
            # `type(...) is int` because True == 1 and isinstance(True, int): a bool is not a version.
            if type(version) is int and version > FORMAT_VERSION:
                raise TallyError(f"ledger version {version} is newer than this tally supports ({FORMAT_VERSION})")
            if type(version) is not int or version != FORMAT_VERSION:
                raise TallyError(f"unsupported ledger version {version!r} (this tally reads {FORMAT_VERSION}, "
                                 "or a file with no version)")
            entries = data.get("entries", [])
        ledger = cls()
        for name in data.get("members", []):
            ledger.add_member(name)
        for e in entries:
            if e.get("kind") == "expense":
                ledger.add_expense(e["payer"], e["amount"], e["participants"], e.get("note", ""))
            elif e.get("kind") == "settlement":
                ledger.add_settlement(e["payer"], e["receiver"], e["amount"])
            else:
                raise TallyError(f"unknown entry kind {e.get('kind')!r} in the ledger file")
        return ledger
