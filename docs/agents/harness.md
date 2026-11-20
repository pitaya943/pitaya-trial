# Harness

Read by every pitaya skill before it plans, builds, verifies or reports. Written by `/setup`; edit it by hand or re-run `/setup`.

## Level

- Level: 2. What it includes: `docs/levels.md` in the pitaya plugin; what each part achieves: `docs/suggestion.md`. Raise it by adding guardrail recipes; record each under "Guardrails" below.
- Templates: pitaya 0.1.1. The version `/setup` installed; re-run `/setup` to find stale copies.

## People and accounts

- Owner: pitaya943.
- Machine account: bullet-bots. Agents push, open PRs and comment as this account.
- Autonomy: Only the Owner merges `main`.

## Work

- Issue tracker: GitHub Issues in this repo.
- Tickets: `docs/tickets/T-<nnn>.md` files, each mirrored by a GitHub issue labelled `ticket` that links to the file. The file is the source of truth; checks read it from the base branch.
- Milestones: `docs/milestones/M<n>.md`, written by `/plan --roadmap`; one is active at a time.
- Test command: `.venv/bin/python -m pytest -q`. Recorded exactly as it runs here; create the venv first with `python3 -m venv .venv && .venv/bin/pip install pytest`.
- Document language: en. Used for PRs, issues, comments and reports. Code, identifiers and commit messages stay in English.

## Review

- Verification: a fresh subagent, started by `/verify`.
- Fix rounds: 2. Round 1 in the builder's session, the rest in fresh sessions; still failing after the last round means escalating to the Owner.
- Autopilot: off.
- Learning: off. When on, `/report` ends by offering the `learning` review.

## Records

- Decisions: `docs/decisions.md`. Append only: add new entries, never rewrite old ones.
- Glossary: `docs/agents/glossary.md`. The project's words; `/plan` keeps it current.
- Learnings: `docs/agents/learnings.md`. Append only; `/retro` adds what the Owner accepts.
- Architecture: `docs/agents/architecture.md`. The module map; `/plan` keeps it current.

## Sensitive areas

Areas where a change needs a covering test before it starts, otherwise escalate to the Owner.

- Money calculations: `src/tally/ledger.py` (parsing amounts to cents, equal-split remainder, balances summing to zero).
- Ledger file format: the JSON written by `Ledger.to_dict` and read by `Ledger.from_dict`; a change must keep existing `tally.json` files readable.

## Guardrails

Guardrails in place. Skills rely on these being enforced by hooks or CI rather than re-checking them by hand.

- Session guards (`.claude/settings.json` and `.claude/hooks/`): Read denied on secrets; hooks block pushes to `main` and destructive commands, and ask before edits to rule files and before merges.
- Tests workflow (`.github/workflows/tests.yml`): runs the test command on every PR and push to `main`.
- Ticket checks (`.github/workflows/` with scripts in `.github/guardrails/`), Level 2, run on every pull request. They need the repository variable `MACHINE_ACCOUNT` (the agents' login); until it is set they fail. Make each a required check after its first run.
  - `scope` (`scope.yml`, `check_scope.py`): a ticket PR changes only the paths in its ticket's "## Scope". "Scope" is a required ticket field.
  - `read-only-paths` (`read-only-paths.yml`, `check_read_only.py`): a ticket PR can't change rule, CI, decision, ticket or milestone files unless its scope names the exact file. Extra paths in `--also`: `docs/spec.md`.
  - `no-weakened-tests` (`no-weakened-tests.yml`, `compare_junit.py`): every test that passes on the base still exists and passes on the PR. CI runs the test command with `--junitxml` to write JUnit XML.
  - `done-when` (`done-when.yml`, `check_done_when.py`): every test listed under the ticket's "## Test IDs" exists and passes. "Test IDs" is a required ticket field.
- Protect main: pending. The Owner creates the ruleset (see "Repo settings" in the setup report); until then nothing on GitHub stops a direct push to `main` except the session hook.
