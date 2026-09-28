---
id: controller
type: persona
name: Controller or VP Finance
status: active
owner: Head of Marketing
last_confirmed: 2026-09-01
icps: [mid-market-finance-team]
role: economic-buyer
seniority: [director, vice president]
functions: [finance]
titles:
  default: [Controller, VP Finance, Director of Finance]
title_regex: '(?i)\b(controller|vp,?\s+finance|vice\s+president,?\s+finance|director,?\s+(of\s+)?finance)\b'
exclude_regex: '(?i)\bassistant\b'
research:
  qualify_good:
    - Do they sign software spend for finance?
  qualify_bad:
    - Did they start in the last 30 days?
  deep:
    - What did they buy at their last company?
---

# Controller or VP Finance

Example economic buyer.
