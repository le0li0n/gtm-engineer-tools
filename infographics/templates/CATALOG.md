# Template catalog

Every graphic starts from one of these types. Pick the type from **what the reader is hunting for**, open its `spec.json`, replace the placeholder copy with real copy, and render. `gallery.png` shows the library side by side.

## Start from what the reader wants

Business readers stop for five things. Each maps to a few templates.

| The reader is hunting for | Templates |
|---|---|
| **A better process**: an SOP, a linear workflow, a branching decision | `layers`, `workflow`, `tree`, `cycle`, `cheatsheet`, `levels` |
| **Hot tools and tech** | `layers` (tools slot into each layer), `stack`, `comparison` |
| **Sharp people to learn from** | `resources` |
| **Events to go to** | `events` |
| **A real thing to learn from**: a campaign that worked with little effort, or a belief the data overturned | `case`, `belief`, `bento`, `stats` |

## The angle: a known idea, applied to a niche

The strongest topics take something readers already know and apply it to a narrower market or use. The familiar half makes it instantly legible; the niche half makes it new and makes the target reader feel it was made for them.

| Known idea | Niche twist |
|---|---|
| The GTM stack | The GTM stack **for founder-led marketing** · **for MCP companies** · **for a solo founder at pre-seed** |
| The five-layer GTM engine | The five-layer engine **for a dev-tool launch** |
| 10 hiring mistakes | 10 mistakes **hiring your first AE** |
| Who to follow in AI | Who to follow **for AI pricing** |
| The PLG playbook | The PLG playbook **for a product with no free tier** |

Pick the niche from the author's audience and earned expertise (your author profile, if you keep one), and put the niche words in the headline.

**Three rules for every type** (from a study of creators whose graphics consistently perform on LinkedIn):

1. **Concrete subjects.** Real tool names with real logos, real people with real faces, real numbers with a source. Placeholder names in the templates exist only to show the layout; a graphic with "Loremly" or a monogram where a logo belongs is not finished.
2. **The headline reads at thumbnail size.** 5–10 words, bold, one keyword in the accent color (`[[like this]]`). Everything else can be dense; density is what earns the save.
3. **Rotate the look.** Leave `preset` out (or set `"auto"`) and the renderer picks the style kit used longest ago, so three posts a week never look the same twice in a row.

Sizes are for a 1080px-wide canvas at 100% text; the renderer fits text between 80% and 160% to fill the canvas. Word budgets are what the check warns on.

---

## layers — "The N-layer X"

**Use when** the idea is an architecture or a stack of responsibilities: what sits on top of what, from the thin visible layer to the wide foundation. Also the best way to redraw a "who does what" table.
**Looks like** centered slabs that widen toward the bottom, each with a colored lid, an icon, a name, one sentence, and a row of logos; a strip at the bottom collects every tool with a count badge.
**Layout** 3–5 layers, top to bottom; the last one is the widest.
**Type** title 70 · layer name 24 · sentence 17.5 · tool labels 13.
**Text vs image** about 50 / 50. Shape and logos do the work.
**Budget** one sentence per layer, under about 16 words; up to 8 logos per layer.
**Template** `layers/spec.json` → `layers/preview.png`

## tree — "Should you X?"

**Use when** the answer depends: a decision the reader has to make, with two or three questions in a row.
**Looks like** a dark root question, branch labels (Yes / No) on the connectors, second-level questions, and colored outcome cards (green go, red stop, neutral try).
**Layout** a root plus 2 levels; 3–4 outcomes.
**Type** title 70 · root 23 · questions 19 · outcomes 19.
**Budget** questions under about 10 words; each outcome a verb plus a short note.
**Template** `tree/spec.json` → `tree/preview.png`

## events — "Where to be this season"

**Use when** listing conferences, dinners, meetups or side events.
**Looks like** rows with a colored date block, the event name, a pin with the city and host, one line on why to go, a tag and a price.
**Layout** 4–7 events, in date order.
**Type** title 70 · name 24 · city 16 · why 16.5 · date 30.
**Budget** check every date and price; events move.
**Template** `events/spec.json` → `events/preview.png`

## case — "One X did Y"

**Use when** the author ran something specific that worked with little effort.
**Looks like** hero result cards on top, a setup strip (goal, time, team, budget) with icons, a numbered step timeline, and a dark "what we learned" bar.
**Layout** 2–3 results, 4 setup items, 3–5 steps, one lesson.
**Type** title 70 · result number 64 · step title 19 · lesson 21.
**Budget** every result is the author's own number, stated plainly.
**Template** `case/spec.json` → `case/preview.png`

## belief — "N things we believed"

**Use when** the lesson is a belief the data overturned. It's the versus template with "We believed" and "The data said" as the column heads.
**Template** `belief/spec.json` → `belief/preview.png`

## stack — "The tools for X, grouped by job"

**Use when** the post is a tool list, a tech stack, a "what I use" or a market map.
**Looks like** a grid of category cards; each card has a colored dot, a category name, an optional price, one line of what the category does, and a wrap of logo chips. One featured card (dark, full width) holds the category the post is really about.
**Layout** 2 columns; 5–8 groups; 3–6 tools per group; one `featured` + `wide` group in the middle.
**Type** title 70 · group name 23 · group note 16 · chip label 17 · price 15.5 mono.
**Text vs image** about 40 / 60. The logos are the content.
**Needs** a logo file per tool (fetch with the `deck-graphics` logo chain); missing logos render as monograms.
**Template** `stack/spec.json` → `stack/preview.png`

## workflow — "From A to B in N steps"

**Use when** the post explains a process someone can copy: a pipeline, a routine, a build.
**Looks like** a numbered rail down the left (one color per step) and a card per step: bold step title, one line of body, and a one-row flow `input → tool → output` with the output filled in the step's color.
**Layout** 1 column of 4–6 steps.
**Type** title 70 · step title 25 · body 18 · flow chips 17 · badge 22.
**Text vs image** about 70 / 30 (tool logos in the flow row).
**Budget** step body under about 18 words; flow of exactly three items reads best.
**Template** `workflow/spec.json` → `workflow/preview.png`

## resources — "Who to follow, read and listen to"

**Use when** the post curates people, newsletters, podcasts, books or communities.
**Looks like** sections with a colored kind pill (Follow / Read / Listen), each a 2-column grid of cards: a ringed avatar, the name in bold, a handle or count in mono, and one line on why.
**Layout** 2–3 sections; 2–4 cards each; 6–10 cards total.
**Type** title 70 · section 24 · name 20 · handle 14 mono · why 16.
**Text vs image** about 60 / 40 (faces carry it).
**Needs** a real headshot or logo per item. Name people only with public information; for a VC, don't rank founders or portfolio companies.
**Template** `resources/spec.json` → `resources/preview.png`

## versus — "N mistakes, and the fix" / good vs bad

**Use when** the reader should find themselves in one column. One of the most reliable formats in the feed.
**Looks like** two colored banners (red ✕, green ✓) with a VS badge between them, then numbered rows: the mistake on a red tint, the fix on a green tint.
**Layout** 8–12 pairs (10–11 is the sweet spot; under 8 looks thin, over 12 is unreadable on a phone).
**Type** title 70 · banner 28 · row text 18 · row number 22.
**Text vs image** about 95 / 5. The two colors are the visual.
**Budget** each side under about 10 words; mistakes must be ones the audience actually makes.
**Template** `versus/spec.json` → `versus/preview.png`

## levels — "Three levels of X"

**Use when** the idea is a progression or a choice between modes: beginner to advanced, manual to automated, three ways to do it.
**Looks like** stacked bands, each with a colored left edge; a big level number, tag pill and name on the left; labeled rows in the middle (How / Who controls / When it wins); a small `input ↓ tool ↓ output` flow on the right.
**Layout** 3 bands (2–4 works).
**Type** title 70 · big number 54 · level name 25 · row label 13.5 mono · row text 17.
**Text vs image** about 75 / 25.
**Template** `levels/spec.json` → `levels/preview.png`

## cheatsheet — "N prompts / tips / rules to save"

**Use when** the value is a dense list worth saving: prompts, rules, shortcuts, questions.
**Looks like** a 2-column grid of numbered cards, each badge in a rotating color, a bold lead-in and one line of detail.
**Layout** 8–16 items in 2 columns (3 columns for very short items).
**Type** title 70 · item title 19 · item body 16 · badge 19.
**Text vs image** about 95 / 5. Density is the point; make the eyebrow "SAVE THIS".
**Template** `cheatsheet/spec.json` → `cheatsheet/preview.png`

## bento — "Everything that changed"

**Use when** the post is a retrospective or a roundup of unlike things: what changed, what we learned, quarter in review.
**Looks like** mixed cards in a 2-column grid, each with a colored tag pill, an optional big number, a bold heading and arrow bullets; one wide card closes it.
**Layout** 4–7 cards; one `wide`.
**Type** title 70 · big number 46 · heading 22 · bullets 17.
**Text vs image** about 85 / 15. Add a real photo or logo row for more pull.
**Template** `bento/spec.json` → `bento/preview.png`

## comparison (`matrix`) — "X vs Y vs Z"

**Use when** the reader is choosing between named things across the same criteria. Often the best-performing format for tool choices.
**Looks like** a header row of column cards (logos optional), a solid colored label column, and cells; the recommended column outlined; bold verdict words.
**Layout** 3–4 columns; 5–7 rows; last row "Pick when".
**Type** title 70 · column name 26 · label 21 · cell 22 (fitted).
**Text vs image** about 90 / 10.
**Budget** cells under about 12 words; facts must be current (stale versions get called out in the comments).
**Template** `comparison/spec.json` → `comparison/preview.png`

## stats — "N numbers that say X"

**Use when** the post rests on 2–6 hard numbers from real sources.
**Looks like** a grid of cards with a huge number, a one-line label and a small source under each; one card emphasized.
**Layout** 4 stats in 2×2 (3 in a row, 6 in 3×2).
**Type** title 70 · number 112 · label 27 · source 20.
**Text vs image** about 80 / 20 (the numbers are the image).
**Budget** every number needs its source on the card or in the note.
**Template** `stats/spec.json` → `stats/preview.png`

## cycle — "The loop"

**Use when** the idea repeats: a flywheel, a feedback loop, a weekly routine.
**Looks like** stage cards around a ring with arrows in the gaps; stages a person owns are outlined; a short line in the center.
**Layout** 4–6 stages.
**Type** title 70 · stage title 29 · stage body 21 · center 40.
**Text vs image** about 70 / 30 (the ring and arrows).
**Budget** stage body under about 10 words.
**Template** `cycle/spec.json` → `cycle/preview.png`

---

## Also in the library

- **steps** (`steps/`): a numbered process, 3–7 steps, big numerals and one line each.
- **split** (`split/`): two approaches side by side with a ≠ between them, the better one outlined.
- **trend** (`trend/`): a number moving over time, endpoints labeled, an optional context strip. Set `"time": true` for uneven dates.
- **classic-paper** (`classic-paper/`): not a type, a test. It renders the brand's own paper, exhibit and navy styles so a brand-token change shows up.

## Not built yet

Next up, seen in layouts that perform in the feed:

- **wheel**: a ring split into colored wedges by role or category, tools as spokes or tiles.
- **quadrant**: a 2×2 with company bubbles, movement arrows and one empty quadrant as the thesis.
- **ranked**: a leaderboard of bars with logos, category colors, tags and a totals panel.
- **snake**: a long numbered workflow that winds across rows from START to FINISH.
- **Variants**: a winner column for `comparison`, a leaderboard panel beside `trend`, card and category-grid versions of `resources`.

Also worth adding: **anatomy** (an annotated thing: a prompt, a profile, a post), **tier list**, **folder tree**, **timeline / roadmap** **UI mock** of the tool being discussed and **carousel** cover + pages.
