<!-- pitaya template 0.1.1 · docs/decisions.md -->
# Decisions

The Owner's decisions. Append only: add a new row, never edit or delete an old one. To change a decision, add a row that supersedes it and name the old number.

A decision that weighed two or more real options and changes the architecture, a public interface or the data model also gets a record in `docs/adr/<nnnn>-<slug>.md` (context, options, decision, consequences); link it from the row's Why. Everything else stays one row.

| # | Date | Decision | Why | Supersedes |
| --- | --- | --- | --- | --- |
