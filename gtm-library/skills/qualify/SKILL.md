---
name: qualify
description: Score a company, and optionally a person there, against one offering's weighted qualifying questions from the GTM library, with evidence behind every answer; then produce the call brief. Gathers the evidence (site, job posts, enrichment, CRM, LinkedIn) on a cheaper model, answers each question yes, no or unknown with a link, and lets the script do the arithmetic, so the same company scores the same way twice. Optional Jev backend answers from the gathered evidence in a second. Use when the user says "/gtm-library:qualify", "qualify this account", "is X a fit for Y", "score this lead", "should we pursue X", "prep me for a call with X", or hands over a list of companies to rank.
---

# GTM library: qualify

The judgement calls go to a model; the arithmetic stays in the script. The script is:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gtm_library.py" <command>
```

The questions, weights and deal-breakers come from the library (see [`references/schema.md`](../../references/schema.md), "Research questions"). If a question is wrong, fix it in the library with `/gtm-library:build`, not here.

## 1. Pick the frame

Which **offering** is this about? A company can fit one offering and not another, so never score "in general". Then the ICP and, if there is a person, the persona:

- `match --employees … --industry … --offering …` suggests ICPs.
- `place --title "…" --offering …` places the person. A listed title is certain; a regex-only or missing match is where the classifier helps (`--backend jev`), and anything under the confidence bar comes back `unsure`. Say so rather than guessing.

## 2. Get the questions

```
qualify --offering O --icp I [--persona P] --template > answers.json
```

Every scored question, answer `unknown`. Weight-0 (`deep`) questions aren't in it; run `questions` for those, they're for the call, not the score.

## 3. Gather evidence, per question

Use a cheaper model for the gathering (a subagent on a small model, one per company in a list). For each question, find what answers it and keep the link:

| Question is about | Look at |
|---|---|
| What they sell, to whom | Their site and pricing page, not the industry label |
| Stage and size | Enrichment (Sumble, Clay), funding news, LinkedIn headcount |
| Open roles | Job posts: what the posting asks the hire to build, not the title |
| Stack | Enrichment tech stack, job posts |
| Relationship | The CRM: deals, tags, past contact |
| The person | Their LinkedIn and posts |

**Answer only from evidence.** A company's reputation, or what "a company like this" usually does, is not evidence. No evidence means `unknown`, and unknowns are left out of the score rather than counted as fails. Never turn an unknown into a yes to make a lead look better, or into a no to close a question.

## 4. Answer

Either:

- **Answer each question yourself** in `answers.json`: `"answer": "yes" | "no" | "unknown"` and `"evidence": "<url or record>"`. Or
- **Let Jev answer** from the gathered evidence: write it to a text file, one fact per line with its source, and run `qualify … --state evidence.txt --backend jev`. Jev picks yes, no or not stated for every question at once, with a confidence; anything below `min_confidence` (config, default 0.7) stays unknown. Read what it answered before you trust the score.

Evidence sent to Jev leaves the machine. Send public facts and your own CRM's facts about the company, never a contact's private remarks from a call.

## 5. Score and report

```
qualify --offering O --icp I [--persona P] --answers answers.json
```

For each of offering, ICP and persona: a score out of 100 (the share of answered weight that points to fit), how many questions were answered, any deal-breaker that failed (**ruled out**, whatever the total), and any deal-breaker still unknown (**unconfirmed**).

Report in that order: ruled out first, then unconfirmed deal-breakers and what would settle each, then the score with its coverage ("72/100 on 6 of 9 answered"). A high score on two answers is not a fit; say how much is unknown. For a list, rank by ruled-out last, then score, and show coverage beside each.

## 6. Brief for the call

```
brief --offering O --icp I --persona P --motion new|renewal|…
```

One page: the qualify questions with weights, what to find out, the triggers, the objections with their reframes, the alternatives, the competitors with why we win and lose, the angles that have run, the proof, and the references that may be named. Add what you found in step 3 on top; the brief is the library's view, the evidence is this company's.

## What goes back to the library

An answer that surprised you, a question that couldn't be answered from public data, a title no persona caught, an objection you expect that isn't in the library: note it for `/gtm-library:evidence`. Don't edit weights from one company.
