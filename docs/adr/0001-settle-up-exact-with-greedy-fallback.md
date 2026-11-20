# 0001: Settle up uses the exact minimum up to 12 members, greedy above

Status: accepted
Date: 2026-11-20
Decided by: pitaya943 (Owner)
Decision log row: D-1

## Context

The spec asks settle up for "a list of payments that clears every balance, with as few payments as possible" (`docs/spec.md`, Wanted next 2). With n members of non-zero balance, n−1 payments always suffice, and the true minimum is n−k, where k is the largest number of disjoint groups whose balances each sum to zero. Finding k is NP-hard (it contains subset-sum). Milestone: `docs/milestones/M1.md`.

## Options

### A: Exact up to a cap, greedy above

Dynamic programming over subsets (about O(3^n)) finds the true minimum for groups up to a cap; above it, greedy (largest debtor pays largest creditor) gives at most n−1. Meets the spec for realistic groups and never hangs; costs two code paths and a message when the fallback is used.

### B: Greedy only

Always at most n−1 payments, O(n log n), one simple path. Not always the minimum, so the spec's wording would have to change.

### C: Exact always

Always the minimum, but exponential: a large group could hang the command.

## Decision

A, with a cap of 12 members with a non-zero balance. It keeps the spec's promise for the group sizes tally is for (trips, shared flats) and bounds the run time. Revisit if real ledgers regularly exceed 12 members or the exact path is slow near the cap.

## Consequences

- M1 needs a brute-force oracle test for small ledgers and a timing check near the cap.
- The output must say when the greedy fallback was used, so users know the count may not be minimal.
- Watch: complaints about slow settle up, or groups above 12.
