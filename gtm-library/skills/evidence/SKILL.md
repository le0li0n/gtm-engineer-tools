---
name: evidence
description: Keep a GTM library current from real evidence (call transcripts, email and campaign replies, CRM deal moves and buyer lists) and check it against who actually bought. Proposes library edits with sources and confidence tags; never overwrites on one data point. Also sets up a weekly scheduled run that opens a review PR. Use when the user says "/gtm-library:evidence", "what did customers say", "does our ICP match who bought", "update the ICP from calls", "check the ICP against our customers", or wants the ICP kept current automatically.
---

# GTM library: evidence

The library ([`references/schema.md`](../../references/schema.md)) is only as good as its last check against reality. This skill gathers evidence, turns it into proposed edits, and checks the library against real buyers. Tool:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gtm_library.py" <command>
```

## Modes

| Mode | Does |
|---|---|
| `evidence` | Reads recent sources and proposes edits. |
| `check <csv>` | Runs a buyer list through the library and turns the misses into proposals. |
| `schedule` | Sets up the weekly version as a cloud routine that opens a review PR. |

## evidence

**0. Open the run.** Before gathering anything:
- `suggestions --accept-proposed`: rows still `proposed` on the default branch reached it through a merged review PR, so they were accepted.
- Look for the previous run's review PR. If it was closed without merging, add its proposals to `suggestions.md` as `rejected`, reason "PR closed unmerged".
- Read `suggestions --status rejected`. Don't propose any of those again unless the evidence is materially new, and then say what changed.
- Run `drift`. Each repo source that changed after its element was last confirmed gets read: propose an edit where the two now disagree, or re-confirm the element if they don't. Re-read each offering page it lists and compare price, package and dates.

**1. Scope.** Ask once which business is in scope if the CRM or inbox is shared with others, and keep to it. When unsure whether something is in scope, skip it and say so.

**2. Gather.** Use what's connected; this skill only reads.

| Source | Look for |
|---|---|
| Call transcripts (Otter, Gong, Granola, Fireflies) | Pains, objections, decision criteria in the speaker's words; titles of people on the call. |
| Email and campaign replies | Who answered which campaign and what they said. |
| CRM | Deals that moved stage, won and lost; new customers and their titles. |
| Buyer lists (CSV) | Titles, sizes, industries of people who paid. Count with `csv.DictReader`, never `wc -l`. |
| The company site | New testimonials, published numbers, package changes. |
| Enrichment (Sumble, Clay) | Firmographics for a shortlist only; mind the credits. |

**Ask every call the same questions.** `extractors` prints the standing list: objections, what resonated, pains, pricing, alternatives, competitors, triggers, who signs, titles, commitments. Run each transcript and thread in the window through it with a cheaper model, one call per subagent, so every call is read the same way rather than skimmed. **Skip a source already in the quote log**: search `voice/` for its link first.

**Log every quote.** Each verbatim line worth keeping becomes one row in `voice/YYYY-MM.md` for the month it was said: id, date, the words, the speaker by role and company (never a name), category, offering, motion, persona, deal outcome if known, `permission` (`internal` unless they cleared it), source link. Library items then point at the row with `quotes: [id]` instead of copying the words.

**3. Keep only what bears on the library.** Titles no persona catches (`match`); buyers no ICP fits; who approved or signed; new public proof; offering changes; pains. Objections go to an objection item (new or existing), with the motion the deal was in. What a buyer uses instead goes to an alternative; what made them move now goes to a trigger, with how it could have been spotted in data; a competitor named on a call goes to its competitor item, and a new dated research file gets added to that item's `dossiers`. An answer to a qualifying question that surprised you is evidence about its weight: propose the change, never make it.

**4. Propose.** Every proposed change is also a row in `suggestions.md`, status `proposed`, with its evidence, so it is remembered whether it's accepted or not.
- A quote you re-read in the source is `[VERIFIED: source, date]`. A line from a summary is `[call summary, date, not re-read]` until someone checks it. If a research subagent gathered the quotes, re-read at least a sample before tagging any `VERIFIED`.
- Describe prospects by role and company size, not by name. Named people go in only as references already public, with `permission: public`. Private admissions never go in.
- Numbers said on a call aren't proof points. Mark them `said on call, unconfirmed`, or leave them out.
- Don't rewrite an item because one call disagreed. Add the evidence and flag the contradiction for the owner.
- Update `last_confirmed` only on what you checked.
- Show the owner each change with its source. Write after approval. Finish with `lint` clean and `render`.

## check

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gtm_library.py" classify <csv> --offering <id> [--title-col Title] [--size-col "Employee Size"] [--industry-col Industry] [--revenue-col "Annual Revenues"]
```

Each miss is one of three things: the library is wrong (propose a title, a range, an ICP), the buyer is an outlier (leave it), or the data is missing (say so). Lead with the share of buyers outside every ICP. Then check each matched ICP's `business_model` and qualify questions against the list's columns: anything the list can't show (whether a company sells to businesses, say) means the match rate is an upper bound, and the report must say so in the same sentence as the number. Count the unmatched titles by cause (blank, one-off, a real gap) rather than characterizing them.

## schedule

Offer a weekly cloud routine rather than a daily one; evidence arrives slowly and definitions that move daily are hard to build on. Use [`templates/routine-prompt.md`](../../templates/routine-prompt.md), filling the placeholders from the repo, and create it with the `/schedule` skill.

- **Connectors:** the call recorder, mail, the campaign tool and the CRM, read-only; plus Slack or mail to notify the owner.
- **Delivery:** a **draft** pull request on its own branch, touching only the library and the rendered summary. The PR body opens with the count per offering: calls read, quotes logged, deals that moved (`counts --since <last run>` gives the quotes and suggestions; the run adds calls and deals). If the repo auto-merges PRs, add whatever label blocks it as well. The owner merges or closes; merged rows become `accepted` at the next run, and a closed PR's rows are recorded as `rejected`.
- **Fallback:** if the session can't push or open a PR, the whole proposal goes to the owner's DM instead.
- Keep a readable copy of the prompt in the repo, since the live one isn't version-controlled.
