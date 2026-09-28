---
id: finance-ops-manager
type: persona
name: Finance operations manager
status: active
owner: Head of Marketing
last_confirmed: 2026-09-01
icps: [mid-market-finance-team]
role: champion
seniority: [manager, senior manager]
functions: [accounting, finance operations]
titles:
  default: [Accounting Manager, Finance Operations Manager, Senior Accountant]
  by_size:
    "100-499": [Accounting Manager, Senior Accountant]
    "500+": [Finance Operations Manager, Assistant Controller, Close Manager]
title_regex: '(?i)\b(accounting|finance\s+operations|accountant|close|assistant\s+controller)\b'
exclude_regex: '(?i)\b(cfo|chief|vp|vice\s+president|intern)\b'
research:
  qualify_good:
    - Do they own the month-end close?
  qualify_bad:
    - Are they in tax or audit only?
  deep:
    - What have they said publicly about the close?
---

# Finance operations manager

Example persona. The same job is "Accounting Manager" at a 150-person company and "Close Manager" at a 1,000-person one, which is what `titles.by_size` is for.
