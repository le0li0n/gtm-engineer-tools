# Suggestions ledger

Every change the evidence run proposes, and what became of it. The run adds rows as `proposed` in its review PR; rows still `proposed` on the default branch arrived by a merged PR, so the next run flips them to `accepted` (`suggestions --accept-proposed`). To reject one, change its status to `rejected` in the PR and say why: the run reads this file before proposing and won't propose a rejected change again without new evidence.

| id | date | element | change | status | reason | evidence |
|---|---|---|---|---|---|---|
| s-2026-09-10-1 | 2026-09-10 | erp-does-this | Add the objection, from two calls | accepted | — | calls 2026-09-03, 2026-09-08 |
| s-2026-09-10-2 | 2026-09-10 | mid-market-finance-team | Lower the size floor to 50 employees | rejected | One 60-person buyer isn't a pattern; revisit at three. | call 2026-09-09 |
