#!/usr/bin/env python3
# pitaya template 0.1.1 · docs/guardrails/files/no-weakened-tests/compare_junit.py
"""Guardrail "no-weakened-tests": every test that passes on the base still exists and passes on the PR.

Usage (in CI, after running the test command on both commits)::

    python3 compare_junit.py --base base-junit.xml --head head-junit.xml [--ticket ticket.md]

It judges by results, not by reading test code: a test removed, renamed,
skipped or now failing shows up as a passing base test that isn't passing on
the head. New tests are welcome; tests already failing on the base are not
required. A rename the Owner approved goes in the ticket's "## Test renames"
section as "old_id -> new_id"; the new test must then pass.

Test IDs are "classname::name" from JUnit XML, which pytest, Jest, Go, JUnit
and cargo-nextest can all write.

When to remove: when the suite runs under mutation testing or coverage gates
that would catch the same weakening, and transcripts show agents no longer
try it.

Exit 0 when nothing was weakened, 1 otherwise. Standard library only.
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def ticket_section(text: str, title: str) -> list[str] | None:
    """Bullet items under "## <title>", backticks stripped; None if the section is missing."""
    items, inside = None, False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].strip().lower().replace("-", " ") == title.lower().replace("-", " ")
            if inside:
                items = []
            continue
        match = re.match(r"\s*(?:[-*]|\d+\.)\s+(.*)", line) if inside else None
        if match:
            items.append(match.group(1).strip().strip("`").strip())
    return items


def load_results(path: Path) -> dict[str, str]:
    """Map "classname::name" to "passed", "failed" or "skipped". Raises ValueError if unreadable."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError) as exc:
        raise ValueError(f"can't read {path}: {exc}") from exc
    results = {}
    for case in root.iter("testcase"):
        test_id = f"{case.get('classname', '')}::{case.get('name', '')}"
        if case.find("failure") is not None or case.find("error") is not None:
            results[test_id] = "failed"
        elif case.find("skipped") is not None:
            results[test_id] = "skipped"
        else:
            results[test_id] = "passed"
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that no passing test was removed or broken.")
    parser.add_argument("--base", required=True, type=Path, help="JUnit XML from the base commit")
    parser.add_argument("--head", required=True, type=Path, help="JUnit XML from the PR head")
    parser.add_argument("--ticket", type=Path, help="ticket with an optional \"## Test renames\" section")
    args = parser.parse_args(argv)

    try:
        base, head = load_results(args.base), load_results(args.head)
    except ValueError as exc:
        print(f"FAIL no-weakened-tests: {exc}")
        print("To fix: make the test command write JUnit XML to the path the workflow expects, "
              "and make sure it runs on both the base and the head.")
        return 1
    if not base:
        print("FAIL no-weakened-tests: the base run reported no tests, so there is nothing to compare against.")
        print("To fix: check that the base job's test command writes JUnit XML with its test cases; "
              "an empty base report would let any test disappear.")
        return 1
    renames = {}
    if args.ticket:
        for item in ticket_section(args.ticket.read_text(), "Test renames") or []:
            old, sep, new = item.partition("->")
            if sep:
                renames[old.strip().strip("`")] = new.strip().strip("`")

    problems = []
    for test_id, status in sorted(base.items()):
        if status != "passed":
            continue
        now_id = renames.get(test_id, test_id)
        now = head.get(now_id)
        if now is None:
            problems.append(f"{test_id}: passed on the base, missing on the PR")
        elif now != "passed":
            problems.append(f"{now_id}: passed on the base, {now} on the PR")
    if problems:
        print("FAIL no-weakened-tests: tests that passed before don't pass now:")
        for line in problems:
            print(f"  {line}")
        print("To fix: restore or fix these tests; don't delete, skip or loosen them. If a rename is "
              "really needed, ask the Owner to add \"old_id -> new_id\" to the ticket's \"## Test renames\" section.")
        return 1
    print(f"PASS no-weakened-tests: all {sum(s == 'passed' for s in base.values())} tests passing on the base still pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
