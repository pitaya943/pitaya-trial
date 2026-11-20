"""The ledger: members, expenses and balances. Money is always integer cents (spec rule 1)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

AMOUNT = re.compile(r"^\d+(\.\d{1,2})?$")


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
class Ledger:
    members: dict[str, str] = field(default_factory=dict)  # key -> name as first added
    expenses: list[Expense] = field(default_factory=list)

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
        self.expenses.append(expense)
        return expense

    @staticmethod
    def shares(expense: Expense) -> dict[str, int]:
        """Equal split; leftover cents go one each to participants in listed order."""
        base, extra = divmod(expense.amount, len(expense.participants))
        return {p: base + (1 if i < extra else 0) for i, p in enumerate(expense.participants)}

    def balances(self) -> dict[str, int]:
        """Paid minus owed, per member, by display name. Always sums to 0 (spec rule 3)."""
        totals = {k: 0 for k in self.members}
        for expense in self.expenses:
            totals[expense.payer] += expense.amount
            for member, share in self.shares(expense).items():
                totals[member] -= share
        return {self.members[k]: v for k, v in totals.items()}

    # --- storage -----------------------------------------------------------------

    def to_dict(self) -> dict:
        return {"members": list(self.members.values()),
                "expenses": [{"payer": self.members[e.payer], "amount": e.amount,
                              "participants": [self.members[p] for p in e.participants], "note": e.note}
                             for e in self.expenses]}

    @classmethod
    def from_dict(cls, data: dict) -> "Ledger":
        ledger = cls()
        for name in data.get("members", []):
            ledger.add_member(name)
        for e in data.get("expenses", []):
            ledger.add_expense(e["payer"], e["amount"], e["participants"], e.get("note", ""))
        return ledger
