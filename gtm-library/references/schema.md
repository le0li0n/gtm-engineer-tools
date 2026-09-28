# GTM library schema

The contract for the library folder named in `.gtmlibrary.json` (`library`, default `gtm-library/`). `scripts/gtm_library.py lint` enforces the parts marked **checked**.

## Layout

```
<library>/
  offerings/<id>.md      type: offering
  icps/<id>.md           type: icp
  personas/<id>.md       type: persona
  use-cases/<id>.md      type: use-case
  references/<id>.md     type: reference
  proof-points/<id>.md   type: proof-point
  objections/<id>.md     type: objection
  alternatives/<id>.md   type: alternative
  triggers/<id>.md       type: trigger
  competitors/<id>.md    type: competitor
  angles/<id>.md         type: angle
```

One item per file. The filename is the id, kebab-case (**checked**). The body may open with an H1, which `render` drops.

**Where a field goes.** Anything a script filters, matches, links or scores on goes in frontmatter: links, offering scope, titles, regexes, weighted questions, tags. Descriptive lists (pains, reframes, hidden costs) go in the body under headings. Some types have required headings (warned when missing); headings match case-insensitively at any level, and `export` returns each one's content by name, so an agent gets structured fields without anyone writing prose in YAML. An item that serves several offerings can say something different per offering with a suffixed heading, `## Why we win (talent-placement)`: `brief` uses it for that offering and falls back to the plain heading otherwise, and the suffixed heading also meets the requirement for the plain one.

It is a relational model stored as files: a folder per type, a file per row, id lists in frontmatter as the join rows, `lint` as the foreign-key check, and the script as the query layer.

## Frontmatter syntax

A restricted YAML subset, so the checker needs nothing but `python3`:

- `key: value`: plain scalar. Integers and `true`/`false` are typed; everything else is a string.
- `key: [a, b, "c, d"]`: a flow list on one line.
- `key:` then indented `- item` lines: a block list.
- `key:` then indented `sub: value` lines: a nested map, any depth, consistent indentation.
- `key:` then `- sub: value` with the item's other keys indented to line up under `sub`: a list of maps. The first key must be a bare lowercase word, so a prose item such as `- Hiring: who owns it?` stays a string.
- Full-line `# comments`.
- Quote a value that contains `: `, ` #`, a leading `[`, or a comma inside a flow list. Regexes go in single quotes; a literal `'` is written `''`.

Anything else is a parse error, not a guess (**checked**).

## Fields every item has

| Field | Required | Notes |
|---|---|---|
| `id` | yes | Equals the filename. |
| `type` | yes | Matches the folder. |
| `name` | yes | Human label. |
| `status` | yes | `active`, `planned` or `retired`. |
| `owner` | no | Who re-confirms it. |
| `last_confirmed` | yes | ISO date someone last checked it against reality. Not the last edit. |
| `cadence_days` | no | Default 90. `lint --stale` lists items past it. |
| `sources` | no | Paths or URLs the item was built from. Warned on an offering, whose price and package drift in public. |
| `offerings` | no | Scope. Left out, the item applies whatever is being sold. Listed, it applies only when selling one of them; every read command takes `--offering` and drops items scoped elsewhere. An item with `icps` scoped to an offering none of them sells never applies (warned). On an ICP, `offerings` is instead the list of what is sold to it. |
| `primary_offering` | no | For an item serving several offerings: the one to lead with when writing. Must be among its `offerings` (warned). |
| `internal_name` | no | What the team calls it, when that differs from `name`. |
| `tags` | no | A map of group to values: `tags:` then `region: [NA]`, `tier: [1]`. Groups must be listed in `tag_groups` in the config (warned). |
| `motion` | no | On angles, objections and triggers only: one or more of the config's `motions` (default `new`, `renewal`, `expansion`, `win-back`) (**checked**). Left out, it applies to every motion. A motion is the kind of sale by where the buyer already stands with you; who you sell to is the offering and ICP. |

Every non-obvious claim in the body carries exactly one confidence tag. Never invent a number: write `[UNAVAILABLE]`.

| Tag | Means |
|---|---|
| `[VERIFIED: source, date]` | Read directly from a primary source: a page, a transcript you re-read, a record. |
| `[INFERRED: from X + Y]` | A defensible deduction from signals. |
| `[ESTIMATED: reasoning]` | A reasoned figure or range, with the reasoning shown. |
| `[UNAVAILABLE]` | The data exists somewhere but you can't reach it. |
| `[call summary, date, not re-read]` | Taken from a call summary rather than the transcript. Upgrade to `VERIFIED` once someone re-reads it. |
| `[Owner, date]` | The owner said so. Their call, not a sourced fact. |

A skill reading the library inherits the weakest tag in what it reads.

## Links

Link fields hold ids and must resolve to an item of the right type (**checked**):

| Field | Points to |
|---|---|
| `offerings` | offering |
| `icps` | icp |
| `personas` | persona |
| `use_cases` | use-case |
| `references` | reference |
| `proof_points` | proof-point |
| `objections` | objection |
| `alternatives` | alternative |
| `triggers` | trigger |
| `competitors` | competitor. A link to a research file in `competitors_dir` is warned rather than refused, so older libraries keep linting. |
| `angles` | angle |
| `primary_offering` | offering |

ICP ↔ persona, ICP ↔ offering and ICP ↔ trigger links should run both ways (warned).

## Research questions

On offerings, ICPs and personas, under `research`: `qualify_good` (yes means fit), `qualify_bad` (yes means not a fit) and `deep` (what to find out before outreach, never scored). Each item is either a plain question or a map:

```
research:
  qualify_good:
    - Is the role a real build role?
    - id: open-req
      q: Is there an open GTM engineering req right now?
      weight: 9
      must: true
      why: No req, no placement.
```

| Key | Notes |
|---|---|
| `q` | The question. |
| `id` | Stable id for answers to refer to. Defaults to a slug of `q`, which changes when the wording does; set one on anything a scorer or a saved answer set relies on. Duplicate ids warn. |
| `weight` | Whole number 0–10 (**checked**). Plain questions count 5. `deep` questions are 0: asked, never scored. |
| `must` | A deal-breaker. Failing it rules the company or person out whatever the total. |
| `why` | One line on why the question separates fit from not. |

`questions` prints them with their weights; `questions --json` and `export` return them normalised as `{id, q, fit, weight, must, why}`. In prose, `[[id]]` is fine and renders as a link in Obsidian.

## offering

What the company sells, or plans to.

| Field | Notes |
|---|---|
| `kind` | `product`, `service`, `solution` or `sponsorship`, or the config's `offering_kinds` (warned). Each kind has required body headings: service `Deliverables`, `Challenges addressed`, `Why us`; sponsorship `Package`, `Challenges addressed`, `Why us`; product `Challenges addressed`, `Distinct capabilities`, `Why us`; solution `Challenges addressed`, `Key components`, `Why us`. |
| `price` | Free text, e.g. `"$1,850 per seat"`, or `[UNAVAILABLE]`. |
| `icps`, `use_cases`, `proof_points`, `references`, `competitors` | Links. |
| `research` | Fit questions specific to this offering (see Research questions). |

## icp

A kind of company, or of individual buyer, the company sells to. Some tools call this a segment.

| Field | Notes |
|---|---|
| `kind` | `company` or `individual`. For an individual, firmographics describe their employer or situation. |
| `offerings`, `personas`, `use_cases`, `references`, `proof_points`, `competitors` | Links. Personas are separate files; list them here. |
| `firmographics.employees` | Size ranges: `"51-200"`, `"5001+"`, `"1-50"`. An enrichment band is a range of possible sizes, and a company fits if its band overlaps: "11-50 employees" fits `"20-500"`, because it may have 20 or more. Only a band wholly outside the range rules it out. An exact number is tested as itself. Titles `by_size` use the same rule (**checked** syntax). |
| `firmographics.industries` | Display list, using the enrichment provider's labels. |
| `firmographics.any_of` | Map of named conditions; the company fits if any one holds. Each condition may set `employees` (ranges), `revenue_min` (`1M`, `500K`) and `funding_stages` (list), and holds when all its known fields pass. Unknown values don't disqualify. Use it for stage tests like "11+ employees, or $1M+ revenue, or Series A+" (**checked** syntax). |
| `firmographics.industry_regex` | What `match` tests. Must compile (**checked**). Enrichment industry labels are unreliable for B2B vs B2C; prefer a qualify question unless the industry really defines the ICP (agencies, vendors). |
| `firmographics.exclude_industry_regex` | A hit disqualifies. |
| `firmographics.geographies`, `funding_stages`, `business_model`, `revenue`, `categories` | Free lists. Not matched yet. |
| `signals` | One-liners for fit and warmth that aren't events ("an alum already works there"). Events that change the pitch are trigger items, linked with `triggers`. |
| `triggers` | Links to trigger items. |
| `research.qualify_good` | Yes means fit. What a qualify agent asks about the company (warned if empty). |
| `research.qualify_bad` | Yes means not a fit. |
| `research.deep` | What to find out before outreach. Other skills pull these with `questions --icp <id>`. |

| `person_score` | Optional. Scoring rules a list-building script applies to people at companies in this ICP: groups of named rules, each with `points`, `label`, `regex`, first match wins per group. Every `regex` must compile (**checked**). A script reads it with `gtm_library.load()`; the library itself only validates it. |

Body sections, in this order where they apply: who and why · pains in order · decision criteria · anti-ICP · where they are · mutual selection · voice · open questions.

## persona

A kind of person inside one or more ICPs.

| Field | Notes |
|---|---|
| `icps` | Links back. |
| `offerings` | Optional. Leave it out and the persona applies whatever is being sold to its ICPs. List offerings and it applies only when selling one of them: a recruiter matters for a placement service and not for a training seat, even at the same company. Each listed offering must be sold to at least one of the persona's ICPs, or the persona never applies (warned). `match`, `questions` and `classify` take `--offering` and drop personas scoped elsewhere. |
| `role` | `champion`, `economic-buyer`, `user`, `decision-maker`, `influencer`, `technical-evaluator`. |
| `seniority`, `functions` | Free lists. |
| `titles.default` | Comma list of titles that hold at any size. |
| `titles.by_size` | Map of size range → titles. The same job has different titles at a 20-person startup and a 5,000-person company; put that here. |
| `titles.by_industry` | Map of industry regex → titles, for industries where titles differ. |
| `title_regex` | Catches titles nobody listed. Every listed title must match it (warned). Must compile (**checked**). |
| `exclude_regex` | A hit rules the title out, e.g. founders out of an IC persona. No listed title may hit it (warned). |
| `research.qualify_good`, `qualify_bad`, `deep` | As for icp, about the person (warned if `qualify_good` is empty). |

`match` scores a title: 3 if it's listed for the company's size band or industry, 2 if in `default`, 1 if only the regex catches it, 0 if excluded.

Body sections: who · their week · JTBD · triggers · pains in order · decision criteria · voice.

## use-case

| Field | Notes |
|---|---|
| `offerings`, `icps`, `personas`, `references`, `proof_points` | Links. |
| `problem` | One line, in the buyer's terms. |
| `outcome` | One line, what changes. |

## reference

A named customer, student, sponsor or employer.

| Field | Notes |
|---|---|
| `kind` | `customer`, `learner`, `sponsor`, `employer`, … |
| `permission` | `public` (may be cited outward) or `internal`. Never cite an `internal` reference outward. |
| `company`, `domain` | For joins with the CRM. |
| `icps`, `personas`, `offerings`, `use_cases` | Links. |
| `quote`, `quote_source` | Verbatim only. |

A person's private admissions never go in a reference.

## proof-point

A result across many customers, or a structural fact.

| Field | Notes |
|---|---|
| `claim` | The sentence as it may be used. |
| `value`, `as_of` | The number and its date. |
| `confidence` | `VERIFIED`, `INFERRED`, `ESTIMATED`, `UNAVAILABLE`. |
| `source` | Path or URL. |
| `offerings`, `icps` | Links. |

## objection

What a buyer says to not buy, and what to do about it. `offerings`, `personas`, `motion` scope it.

Required headings: `Underlying concern` · `Misconceptions` · `What to probe` · `Reframe`.

## alternative

What a buyer does instead: the status quo, an incumbent approach, or doing it themselves. Scoped by `offerings`.

Required headings: `Where it works` · `Where it breaks` · `Who champions it` · `Hidden costs` · `Why ours is better`.

## trigger

An event that makes now the moment and changes what you say. Fit and warmth that aren't events stay ICP `signals`.

| Field | Notes |
|---|---|
| `detect` | How to spot it in data: filings, job posts, funding news, enrichment fields (warned if empty). |
| `icps`, `offerings`, `motion` | Where it applies. |

Required headings: `Why now` · `Who feels it` · `Cost of waiting` · `How we help`.

## competitor

The short, current view of one competitor. The long dated research stays in `competitors_dir`.

| Field | Notes |
|---|---|
| `offerings` | Which of your offerings it competes with, so "who are we up against selling X" is `list --type competitor --offering X`. |
| `url` | Their site. |
| `dossiers` | Research files in `competitors_dir`, newest first, by filename without `.md` (**checked** when `competitors_dir` is set). |

Required headings: `How they position` · `Why we win` · `Why we lose`.

## angle

A reusable pitch: one offering, aimed at chosen ICPs and personas, around a trigger or competitor. Campaigns name the angle they run; many campaigns reuse one.

| Field | Notes |
|---|---|
| `offerings` | Exactly one (warned otherwise). |
| `icps`, `personas`, `triggers`, `competitors`, `objections`, `alternatives`, `proof_points`, `references` | What it draws on. |
| `motion` | Which kind of sale it is for. |

Required headings: `Approach` · `Key messages` · `Value props`.

## The quote log and the suggestions ledger

Two logs sit beside the element folders as markdown tables, so they read in any editor and diff line by line in a review PR. Escape a pipe in a cell as `\|`. Lint checks both (**checked**).

**`voice/YYYY-MM.md`**, one file per month, one row per verbatim quote:

| Column | Notes |
|---|---|
| `id` | `q-<date>-<company-slug>-<n>`, unique across months. Items point at it with `quotes: [id]` (**checked**). |
| `date` | When it was said; the file is the month it was said in (warned otherwise). |
| `quote` | The words, verbatim. |
| `speaker`, `company` | A role and a company, never a name. |
| `category` | `objection`, `resonates`, `pain`, `pricing`, `competitor`, `request`, `commitment`, `trigger`, `alternative` (config `voice_categories`). |
| `offering`, `persona` | Ids, comma-separated if several (**checked**). |
| `motion` | As for items. |
| `outcome` | The deal's outcome if known: `open`, `won`, `lost`. |
| `permission` | `internal` or `public`. Only `public` quotes go outward (`voice --public`). |
| `source` | The call or thread it came from; the evidence run skips sources already here. |

**`suggestions.md`**, one row per proposed change: `id`, `date`, `element` (an id, or `new:<type>/<id>`), `change`, `status` (`proposed`, `accepted`, `rejected`, `deferred`), `reason` (warned if empty on a rejection), `evidence`. The evidence run adds rows as `proposed` in its review PR; rows still `proposed` on the default branch came by a merged PR and are flipped to `accepted` with `suggestions --accept-proposed`; a closed PR's rows are recorded `rejected`. The run reads the rejections before proposing.

**Standing questions.** `extractors` prints the questions the evidence run asks of every call and thread. Override them in the config as `extractors: [{id, q, category}]`.

## Config

`.gtmlibrary.json` at the repo root. Every key is optional.

| Key | Default | Notes |
|---|---|---|
| `library` | `gtm-library` | The library folder. |
| `render_to` | `<library>/ICP.md` | Where `render` writes the one-file summary. |
| `dashboard_to` | `<library>/dashboard.html` | Where `render` and `dashboard` write the one-page HTML dashboard. |
| `company` | the repo folder's name | The name on the dashboard. |
| `competitors_dir` | none | Where dated competitor research lives. |
| `cadence_days` | 90 | Default review cadence. |
| `offering_kinds` | product, service, solution, sponsorship | Allowed `kind` values. |
| `motions` | new, renewal, expansion, win-back | Allowed `motion` values. |
| `tag_groups` | none | Allowed tag groups. |
| `headings` | built in | Override required headings per type, or per offering kind: `{"objection": ["Concern", "Reframe"]}`. |
| `classifier` | none | `{"backend": "jev", "min_confidence": 0.7, "key_env": "JEV_API_KEY", "batch": 40}`. Which backend makes closed-answer judgements: placing a title in a persona, answering a qualifying question from evidence. With `jev`, the key is read from the environment, then a `.env` at the repo root, then the main checkout's `.env` when running in a git worktree; a configured backend with no key falls back to the rules with a note. Below `min_confidence` a judgement counts as unknown. |

## Reading it

| Command | Returns |
|---|---|
| `list [--type T] [--offering O] [--motion M] [--icp I] [--persona P]` | The items that apply. An item with no scope on a field applies to every value of it. |
| `export [--type T] [--offering O] [--motion M]` | JSON, one agent view per item: frontmatter, questions normalised, and `sections`, every body heading by name. |
| `questions [--offering O] [--icp I] [--persona P] [--json]` | Research questions with weights and deal-breakers. |
| `place --title T [--headline H] [--offering O] [--employees N] [--industry I] [--backend jev]` | The persona for one person: the rules when a title is listed; otherwise the classifier, or `unsure` below the confidence bar. |
| `qualify --offering O [--icp I] [--persona P] --template` | A blank answers file: every scored question, `unknown`. |
| `qualify … --answers FILE [--state FILE --backend jev] [--json]` | Scores: per element, the share of answered weight pointing to fit out of 100, answered of total, deal-breakers failed (ruled out) and unknown (unconfirmed). Unknowns are left out of the score, never counted as fails. With `--state`, the classifier answers the still-unknown questions from an evidence file first. |
| `brief --offering O [--icp I] [--persona P] [--motion M]` | One page for a call: weighted questions, what to find out, triggers, objections and reframes, alternatives, competitors, angles, proof, and references cleared to name. |
| `dashboard [--out FILE]` | One self-contained HTML page: an offering and motion switcher, a map from offerings through ICPs and personas to triggers, objections, competitors and angles (click anything to light up what it connects to), a detail panel per item, and tabs for every item, the quote log, the ledger and lint's findings. No server; `render` rebuilds it too. |
| `voice [--category C] [--offering O] [--motion M] [--persona P] [--since DATE] [--public] [--json]` | Search the quote log. |
| `suggestions [--status S] [--element E] [--accept-proposed]` | Read the ledger, or flip merged proposals to accepted. |
| `drift` | Repo sources changed since their element's `last_confirmed` (from git, merges left out), and the web pages offerings cite, to re-read. |
| `extractors` | The standing questions for every call. |
| `counts --since DATE` | Per offering: quotes logged and suggestions made since the date. |
| `label CSV --offering O [--backend jev] [--extra-col C] [--out FILE]` | Labels a lead list for one offering and writes it back with its own columns plus `gtm_persona`, `gtm_persona_source` (listed title, title regex, classifier, unsure, none), `gtm_persona_confidence`, `gtm_icp` and `gtm_offering` — ready to import into a campaign tool. The rules decide a listed title; the classifier is asked once per distinct title about the rest; anything under the confidence bar stays `unsure` for a person. |
| `classify CSV --backend jev [--out FILE]` | As `classify`, and every distinct title also goes to the classifier: agreement where the rules were sure, what it adds where they weren't, one row per person to `--out`. |

## Not built yet

- **Matrix cells** (`matrix/<icp>--<persona>.md`): the narrative for one ICP × persona pair, where it differs from the two files alone. Add a cell only when copy for that pair actually differs.

