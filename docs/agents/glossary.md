<!-- pitaya template 0.1.1 · docs/agents/glossary.md -->
# Glossary

The project's own words, so people, agents and code use the same name for the same thing. Use these terms in tickets, code, tests and PRs. When a word under "Avoid" comes up, use the term instead.

`/plan` adds terms when planning settles a new one. Ticket PRs propose changes in their description instead of editing this file.

| Term | Meaning | Avoid |
| --- | --- | --- |
| ledger | One group's record of members and expenses, stored as a JSON file. | book, group file |
| member | A person in the ledger; names are trimmed and case-insensitive, shown as first added. | user, participant (when meaning everyone) |
| expense | An amount paid by one member and split among participants. | transaction, payment |
| payer | The member who paid an expense. | owner, buyer |
| participant | A member an expense is split among (default: every member). | debtor |
| share | One participant's part of an expense, in cents. | portion, cut |
| balance | What a member paid minus their shares of everything; positive means others owe them. All balances sum to zero. | debt, total |
| cents | The unit of every amount: an integer, never a float. | amount in dollars |
