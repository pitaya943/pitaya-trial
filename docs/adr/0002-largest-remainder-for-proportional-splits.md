# 0002: Proportional splits give leftover cents by largest remainder

Status: accepted
Date: 2026-11-20
Decided by: pitaya943 (Owner)
Decision log row: D-3

## Context

Percentage and share splits produce fractional cents, but money is integer cents (spec rule 1). The leftover cents must go to someone, and the shares must still add up to the amount. Equal splits already give leftovers one each in listed order (spec, "Equal split remainder"). Milestone: `docs/milestones/M3.md`.

## Options

### A: Largest remainder (Hamilton), ties in listed order

Floor every exact share, then give the leftover cents one each to the largest fractional parts, ties going in listed order. For an equal split every fraction ties, so it reproduces today's rule exactly.

### B: Listed order everywhere

One rule for every split kind, simplest to explain. But with a 1:2 split of 1.00, the first participant gets 34 although their exact share (33.33) is the smaller fraction.

## Decision

A. It never gives a cent to someone whose exact share was further from the next cent than another participant's, and it agrees with the existing equal-split rule. Revisit if users find the order of leftover cents surprising.

## Consequences

- M3 needs property tests: shares add up to the amount and each share is within 1 cent of its exact value.
- The equal-split code can later be expressed as the all-ties case of the same function.
- Exact-amount splits need no rounding: amounts that don't add up are an error.
