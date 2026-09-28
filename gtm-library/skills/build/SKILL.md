---
name: build
description: Build and maintain a GTM library: offerings, ICPs, personas (titles by company size and industry, a title regex, weighted research questions), use cases, references, proof points, objections, alternatives, triggers, competitors and angles, one markdown file each, linked by id and scoped by offering and motion. Type-aware (single-sided B2B, multi-sided, single decision-maker, mutual selection). Modes - status, init, add, refresh, render. Other skills and scripts read the library for fit, titles and research questions. Use when the user says "/gtm-library:build", "build our ICP", "add a persona", "refresh the ICP", "what titles should we target", "set up a GTM library", or asks who the company sells to. For gathering evidence from calls, mail and CRM, use /gtm-library:evidence.
---

# GTM library: build

A living set of files that says what the company sells, to which companies, to which people, for what jobs, with what proof. One file per item, linked by id. The spec is [`references/schema.md`](../../references/schema.md); read it before writing any item. The tool is:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/gtm_library.py" <command>
```

Commands: `lint [--stale]`, `show <id>`, `list [--type …] [--offering …] [--motion …] [--icp …] [--persona …]`, `match --title … [--employees …] [--industry …] [--revenue …] [--funding …] [--icp …] [--offering …]`, `questions [--offering …] [--icp …] [--persona …] [--json]`, `classify <csv> [--offering …]`, `export [--type …] [--offering …] [--motion …]`, `render`. Standard library only.

**Paths** come from `.gtmlibrary.json` at the repo root (see [`templates/gtmlibrary.json`](../../templates/gtmlibrary.json)). With no config, the library lives in `gtm-library/`.

## The model

- **Offerings** anchor everything: what you sell, or plan to.
- **ICPs** are kinds of company (or of individual buyer). Firmographics, signals, research questions.
- **Personas** are separate files that ICPs link to. One persona can sit in several ICPs, and its titles change with company size inside the persona rather than by copying it.
- **Some personas only exist for one offering.** Selling a placement service brings in recruiters; selling training seats to the same company doesn't. Scope those with `offerings` on the persona rather than inventing a second ICP for the same companies. Every other type scopes the same way.
- **Use cases, references, proof points** hang off all three.
- **Objections, alternatives and triggers** are what a buyer says, what they do instead, and what makes now the moment. **Competitors** are short current items that point at the long dated research. **Angles** are reusable pitches: one offering, aimed at chosen ICPs and personas, around a trigger or competitor, drawing on the rest. Campaigns name the angle they run.
- **Motion** (`new`, `renewal`, `expansion`, `win-back`) labels angles, objections and triggers by where the buyer already stands with you, so a renewal call gets renewal objections.
- **Scripts read frontmatter; people write bodies.** Links, scope, titles, weighted questions and tags go in frontmatter. Descriptive lists go under the headings the schema requires per type; `export` hands both to agents as one view.
- A generated summary (`render_to`, default `<library>/ICP.md`) gives any tool that wants one file a single document to read.

## Modes

With no clear request, run `status`.

| Mode | Does |
|---|---|
| `status` | `lint` and `lint --stale`; says what's broken, what's stale, and the one thing to do next. |
| `init` | Builds the library from scratch (below). |
| `add <type>` | Writes one new item and links it both ways. |
| `refresh <id>` | Re-checks one item against its sources, shows the diff, updates `last_confirmed`. |
| `render` | Regenerates the summary file and the HTML dashboard (`dashboard_to`). Point the owner at the dashboard when they want to see how things connect. |

Every mode that writes ends with `lint` clean, then `render`.

## How to work

1. **Read first:** any company overview in the repo (what the company is, business model, audiences, goals), competitor research, and the library as it stands (`export`).
2. **One question at a time** when you need something only the owner knows. Never a batch.
3. **Propose, then write.** Show each change as a short before → after with its source. Write after the owner approves.
4. **Tag every claim** with the confidence tags in the schema. A number with no source is `[UNAVAILABLE]`. Set `last_confirmed` only for what you actually checked.
5. **Link both ways.** An ICP lists its personas and offerings; they list it back.

## init

1. **Audience model.** From the company overview, or the website if there's no overview:
   - *Single-sided B2B:* ICPs are company segments; personas cover the buying committee (`champion`, `economic-buyer`, `technical-evaluator` where it matters).
   - *Multi-sided* (marketplace, platform, school, fund): at least one ICP per side, each with its own offering.
   - *Single decision-maker* (founder, consumer, member, LP): one persona, `role: decision-maker`. Don't invent a committee.
   - *Mutual selection* (fund ↔ founder, school ↔ employer): decision criteria both ways; your side's fit tests go in `research.qualify_good`.

   Don't invent audiences the company doesn't serve, and don't merge different ones.
2. **Offerings** from the pricing page and the owner.
3. **ICPs.** Define fit by what actually separates buyers: stage, motion, team, not an industry label unless the industry really is the segment. Enrichment industry labels misfile companies often, so "sells to businesses" is a qualify question, not a filter. Use `firmographics.any_of` for stage tests ("11+ employees, or $1M+ revenue, or Series A+").
4. **Personas per offering.** Walk the offerings one at a time and ask who buys, who champions and who signs *for that offering*. A person who only shows up for one offering gets `offerings: [that-one]`. A company with several offerings usually has a few of these; one that has none is worth a second look.
5. **Personas with titles from real people.** If there's a list of customers with title and company size, bucket the titles by size band and put what you see in `titles.by_size`. Write `title_regex` wide and `exclude_regex` narrow; lint warns when a listed title doesn't match. Some personas can't be found by title (a career switcher looks like any SDR); say so in the body.
6. **Research questions** on every offering, ICP and persona: `qualify_good` (yes means fit, answerable from public data or one enrichment call), `qualify_bad` (including known false positives), `deep` (what to learn before a personal message, specific enough for a cheaper model). Weight the qualify questions 0–10 by how decisive each is, and mark the few that rule a buyer out on their own as `must`. Give those an `id` so answers keep working when the wording changes. Propose the weights; the owner sets them.
7. **Proof and references** only from public or owner-confirmed sources. `permission: internal` on anything not cleared for outward use.
8. **Framing, per offering.** Objections from calls and replies, alternatives (the status quo and DIY, not only vendors), triggers with how to `detect` each in data, a competitor item for each competitor with research, and an angle for each pitch that has actually been used. Move any ICP `signals` that are events into triggers; leave fit and warmth as signals. Draft from what the repo and the calls say; tag what you inferred for the owner to confirm, and never invent an objection nobody raised.
9. **Check it.** Run `classify` on the buyer list. The headline is the share of buyers no ICP describes. Report it; don't widen the ICPs to hide it.

## Titles

- Test with `match --title "…" --employees … --industry …`.
- Split by industry only where titles really differ (agencies, public sector, healthcare).
- A scoring script can keep its own narrower rules under `person_score` on an ICP (see the schema) and read them with `load()`, so the rules and the library live in one place.

## How other skills use it

- **List building and campaigns:** `match` to place a person, `titles.by_size` and `title_regex` for searches, `questions --json` for per-person research, `export --type angle --offering …` for the pitch and what it draws on.
- **Who we're up against:** `list --type competitor --offering …`.
- **Objection handling:** `list --type objection --offering … --motion …`, then `export` for the reframes.
- **Call prep:** `brief --offering … --icp … --persona … --motion …`, or `/gtm-library:qualify` to score the account first.
- **Positioning and messaging:** the rendered summary or the files; pains are in priority order.
- **Outward notes:** references with `permission: public` only.

## Refresh

Items default to 90 days (`cadence_days` in the config, or per item). Run `/gtm-library:evidence` weekly or after each sales cycle to keep it current.
