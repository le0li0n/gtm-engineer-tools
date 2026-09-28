# gtm-library

What you sell, to which companies, to which people, for what jobs, and with what proof. One markdown file per item, linked by id, kept current from real evidence.

Most ICP documents get written once and go stale by next quarter. This plugin keeps the ICP as a set of small files that people can edit and scripts can read, with a weekly routine that proposes updates from your calls, mail and CRM.

## What's in a library

```
gtm-library/
  offerings/      what you sell, or plan to
  icps/           kinds of company: firmographics, signals, research questions
  personas/       kinds of people: titles by company size and industry, a title regex, research questions
  use-cases/      the jobs an offering does
  references/     named customers, with whether they can be cited publicly
  proof-points/   results across customers, with their source
  objections/     what buyers say to not buy, and the reframe
  alternatives/   what they do instead: the status quo, an incumbent, DIY
  triggers/       events that make now the moment, and how to spot them in data
  competitors/    the short current view of each competitor, linked to your dated research
  angles/         reusable pitches: one offering, aimed at chosen ICPs and personas
  voice/          the quote log, one file per month, verbatim and categorised
  suggestions.md  every proposed change and what became of it, so rejections stick
  ICP.md          generated summary, for anything that wants one file
  dashboard.html  generated one-page map of the whole library, to open in a browser
```

Personas are separate files that ICPs link to. A "Head of RevOps" can sit in three ICPs without being copied, and the persona's titles change with company size: the same job is "GTM Engineer" at a 20-person startup and "Revenue Systems Analyst" at a 5,000-person one.

Any item can be scoped to some of your offerings: a recruiter persona only matters when you sell placement, not training, even at the same company. Angles, objections and triggers also carry a motion (new, renewal, expansion, win-back), so a renewal call gets renewal objections. Research questions carry weights from 0 to 10 and can be marked deal-breakers.

Every claim carries a confidence tag (`VERIFIED`, `INFERRED`, `ESTIMATED`, `UNAVAILABLE`). A number with no source stays `[UNAVAILABLE]`. The full format is in [`references/schema.md`](references/schema.md).

## Skills

| Skill | Use it to |
|---|---|
| `/gtm-library:build` | Create the library, add or refresh an item, regenerate the summary. Adapts to single-sided B2B, marketplaces, single decision-makers and mutual selection. |
| `/gtm-library:qualify` | Score a company (and a person) against one offering's weighted questions, with evidence behind every answer, then brief for the call. |
| `/gtm-library:evidence` | Pull pains, objections and real titles from calls, mail, campaign replies and the CRM; check the library against a list of real buyers; set up the weekly routine. |

## The script

`scripts/gtm_library.py` needs nothing but Python 3.

```
python3 scripts/gtm_library.py lint [--stale]
python3 scripts/gtm_library.py match --title "Head of Revenue Operations" --employees "201-500 employees"
python3 scripts/gtm_library.py questions --icp mid-market-finance-team --persona controller --json
python3 scripts/gtm_library.py classify customers.csv --offering close-platform
python3 scripts/gtm_library.py list --type objection --offering close-platform --motion new
python3 scripts/gtm_library.py export --type angle
python3 scripts/gtm_library.py qualify --offering close-platform --icp mid-market-finance-team --answers answers.json
python3 scripts/gtm_library.py brief --offering close-platform --persona controller --motion new
python3 scripts/gtm_library.py place --title "Head of Accounting Systems" --backend jev
python3 scripts/gtm_library.py voice --category objection --offering close-platform
python3 scripts/gtm_library.py drift
python3 scripts/gtm_library.py render        # ICP.md and dashboard.html
```

- `lint` checks required fields, that every link resolves to the right kind of item, that regexes compile, that every listed title matches its persona's regex, question weights, motions, tags, required body headings per type, and which items are past their review date.
- `list` and `export` filter by type, offering and motion; `export` gives each item as an agent reads it, with body sections by heading.
- `match` places a person: 3 points if the title is listed for that company size or industry, 2 if in the default list, 1 if only the regex catches it. An exclude pattern wins.
- `classify` runs a CSV of real buyers through the library and prints the misses. The share of buyers no ICP describes is the number to watch.
- `qualify` scores answered questions: out of 100 on what's answered, with deal-breakers and coverage. The arithmetic is in the script so the same answers always give the same score; the answers come from the `qualify` skill, or from the classifier.
- **The classifier** (`"classifier": {"backend": "jev"}` in the config) makes closed-answer judgements with TypeSafe's Jev: which persona a title belongs to when the rules aren't sure, and yes / no / not stated for a qualifying question given evidence. Every answer carries a confidence, and below the bar it stays unknown. On 198 real buyer titles it agreed with the listed titles 82 times in 85, against 66 for a small Claude model given the same persona descriptions.
- Other scripts can `import gtm_library` and call `load()`, `match_icps()`, `match_personas()`, `questions()`, `select()` and `agent_view()`.

## Setup

1. Install the plugin.
2. Optional: copy [`templates/gtmlibrary.json`](templates/gtmlibrary.json) to `.gtmlibrary.json` at your repo root to choose where the library lives. Without it, the library is `gtm-library/`.
3. Run `/gtm-library:build` and pick `init`. [`templates/example-library/`](templates/example-library/) shows a finished small library for a made-up company.
4. When you have a customer list, run `/gtm-library:evidence check` on it.
5. For the weekly routine, run `/gtm-library:evidence schedule`. It uses [`templates/routine-prompt.md`](templates/routine-prompt.md) and opens a draft pull request each week for you to merge or close.

## Lessons from the first real library

- **Industry labels are a weak filter.** Enrichment tools file a health-tech company under "Mental Health Care" and restaurant software under "Restaurants". Test "sells to businesses" by reading the website, and define fit by stage, motion and team.
- **Get titles from people who bought.** Bucketing real buyers' titles by company size showed the size split more clearly than any guess would.
- **Keep scoring rules narrower than personas when they mean something narrower.** "Likely owns the hiring req" is not the same as "a GTM leader". A scoring script can keep its own rules in the library under `person_score`.
- **Tag call evidence by whether someone re-read the transcript.** Summaries paraphrase, and a quote that reads as verbatim needs to be verbatim.

## Tests

```
python3 scripts/test_gtm_library.py
```
