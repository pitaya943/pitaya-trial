#!/usr/bin/env python3
# pitaya template 0.1.1 · docs/guardrails/files/scope/check_scope.py
"""Guardrail "scope": a pull request changes only the paths its ticket lists.

Usage (from the repository root, in CI)::

    python3 check_scope.py --base <base sha> --head <head sha> --ticket ticket.md [--ticket-path docs/tickets/<id>.md]

The ticket's "## Scope" section lists paths or globs, one bullet each, in
backticks or not. `*` matches within one directory, `**` across directories.
Every file the PR adds, changes, deletes or renames must match one of them.
One exception: with --ticket-path, the PR may change its own ticket file's
"Status:" line (marking it done), and nothing else in that file.

When to remove: when agents no longer work in parallel, or when transcripts
show out-of-scope edits have stopped for a long stretch and review catches
the rare one.

Exit 0 when every change is in scope, 1 otherwise. Standard library and git only.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
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


def glob_to_regex(pattern: str) -> re.Pattern:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def changed_files(base: str, head: str) -> list[str]:
    out = subprocess.run(["git", "diff", "--name-only", "--no-renames", f"{base}...{head}"],
                         capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if line]


STATUS_LINE = re.compile(r"\s*Status:\s*\S")


def status_only_change(base: str, head: str, path: str) -> bool:
    """True when `path` differs between base and head only in its "Status:" lines.

    A file ticket's own PR marks it done this way (D35); any other edit still counts.
    """
    merge_base = subprocess.run(["git", "merge-base", base, head], capture_output=True,
                                text=True, check=True).stdout.strip()

    def lines(rev: str) -> list[str] | None:
        out = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
        return out.stdout.splitlines() if out.returncode == 0 else None

    old, new = lines(merge_base), lines(head)
    if old is None or new is None or len(old) != len(new):
        return False
    pairs = [(a, b) for a, b in zip(old, new) if a != b]
    return bool(pairs) and all(STATUS_LINE.match(a) and STATUS_LINE.match(b) for a, b in pairs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that a PR stays inside its ticket's scope.")
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--ticket", required=True, type=Path)
    parser.add_argument("--ticket-path", default="",
                        help="the ticket's own file in the repository, such as docs/tickets/T-001.md; "
                             "its Status line may change")
    args = parser.parse_args(argv)

    scope = ticket_section(args.ticket.read_text(), "Scope")
    if not scope:
        print("FAIL scope: the ticket has no \"## Scope\" section, or it's empty.")
        print("To fix: ask the Owner to add a \"## Scope\" section to the ticket listing the paths "
              "this work may change, one bullet per path or glob.")
        return 1
    patterns = [glob_to_regex(p) for p in scope]
    outside = [f for f in changed_files(args.base, args.head)
               if not any(p.match(f) for p in patterns)
               and not (f == args.ticket_path and status_only_change(args.base, args.head, f))]
    if outside:
        print("FAIL scope: these files are outside the ticket's scope:")
        for path in outside:
            print(f"  {path}")
        print("To fix: revert the changes to these files, or, if the ticket really needs them, "
              "ask the Owner to add them to the ticket's \"## Scope\" section.")
        return 1
    print("PASS scope: every changed file is inside the ticket's scope.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
