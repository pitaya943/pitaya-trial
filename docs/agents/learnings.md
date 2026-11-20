<!-- pitaya template 0.1.1 · docs/agents/learnings.md -->
# Learnings

What the next agent should know before starting: things that cost time, surprised someone, or went wrong more than once. Read it before planning or building.

Append only: add a row, never edit or delete one; mark an outdated row as superseded in a new row. `/retro` adds the rows the Owner accepts. Verdicts and hand-off notes propose them.

| # | Date | Learning | Source | Supersedes |
| --- | --- | --- | --- | --- |
| 1 | 2026-11-20 | A test pins a behaviour only if a plausible wrong implementation fails it. Choose inputs where right and wrong differ: test a threshold at exactly N and N−1, not N+1; compare two code paths on an input where their results differ; check "never writes" with a file the writer would reformat (or its mtime), since a canonical file round-trips to identical bytes. Prove it with a mutation when there is no natural red. | M1 retro: T-001 verdict on #7; T-002 verdicts rounds 1 and 2 on #8; D-6 | |
