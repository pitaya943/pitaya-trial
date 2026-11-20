<!-- pitaya template 0.1.1 · docs/agents/glossary.md -->
# Glossary

The project's own words, so people, agents and code use the same name for the same thing. Use these terms in tickets, code, tests and PRs. When a word under "Avoid" comes up, use the term instead.

`/plan` adds terms when planning settles a new one. Ticket PRs propose changes in their description instead of editing this file.

| Term | Meaning | Avoid |
| --- | --- | --- |
| ledger | One group's record of members and expenses, stored as a JSON file. | book, group file |
| member | A person in the ledger; names are trimmed and case-insensitive, shown as first added. | user, participant (when meaning everyone) |
| expense | An amount paid by one member and split among participants. | transaction, payment |
| payer | The member who paid an expense, or who paid a settlement (from M2). | owner, buyer |
| receiver | The member a settlement was paid to (from M2). | payee, creditor |
| participant | A member an expense is split among (default: every member). | debtor |
| share | One participant's part of an expense, in cents. | portion, cut |
| balance | What a member paid minus their shares of everything; positive means others owe them. All balances sum to zero. | debt, total |
| cents | The unit of every amount: an integer, never a float. | amount in dollars |
| settle up | A list of payments that would clear every balance; computed, not recorded. | settle (that's recording one payment) |
| settlement | A recorded payment from one member to another that pays back what they owe (from M2). | refund, transfer |
| entry | One recorded item in the ledger, an expense or a settlement, kept in the order recorded; its `kind` says which (from M2). | record, item, transaction |
| ledger version | The `version` number in the ledger file; absent means v0.1 (from M2). | schema number |
