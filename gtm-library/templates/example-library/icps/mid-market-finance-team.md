---
id: mid-market-finance-team
type: icp
name: Mid-market company with an in-house finance team
status: active
owner: Head of Marketing
last_confirmed: 2026-09-01
kind: company
offerings: [close-platform]
personas: [finance-ops-manager, controller]
use_cases: [close-books-faster]
references: []
proof_points: [customers-live]
triggers: [second-entity]
firmographics:
  business_model: [B2B]
  employees: ["100-2000"]
  # Big enough to have a finance team: either condition.
  any_of:
    headcount:
      employees: ["200+"]
    revenue:
      revenue_min: 20M
  exclude_industry_regex: '(?i)accounting|bookkeeping'
# Fit and warmth that aren't events; events that change the pitch are trigger elements.
signals:
  - Already on a cloud ERP
  - A customer of ours already works with their auditor
research:
  qualify_good:
    - Do they run more than one legal entity?
    - Is there a finance team of three or more?
  qualify_bad:
    - Is the close run by an outside firm?
  deep:
    - Which ERP do they run?
    - Who owns the close today, and how long does it take?
---

# Mid-market company with an in-house finance team

Example ICP. Size and revenue are the fit test; industry only excludes accounting firms, who are partners rather than buyers. `[INFERRED: example]`

## Anti-ICP

- Companies whose books are kept by an outside firm.
