---
name: render
description: >-
  Render a LinkedIn infographic from a JSON spec: pick one of 19 template types (stack,
  layers, workflow, tree, cycle, levels, cheatsheet, resources, events, versus, belief,
  case, bento, comparison, stats, trend, steps, split), fill it with exact copy, render it
  in a rotating style kit, then look at every PNG before calling it done. Use when the
  user says "/infographics:render", "make a graphic", "infographic", "graphic for this
  post", "tech stack graphic", "workflow graphic", "who to follow graphic", "mistakes vs
  fixes", "comparison table", "cheat sheet", or "visual for the post".
---

# render

One idea per graphic, a headline that states the finding, one highlighted keyword, concrete names and logos, real numbers with a source printed on the image, and a footer that carries the author and a URL. That is what the graphics that perform on LinkedIn have in common, and every template here is built around it.

**The renderer never writes copy.** If a word or number isn't in the spec, it isn't on the graphic. You write the copy; the renderer lays it out, fits it, and checks it.

If `.infographic.json` doesn't exist at the repo root yet, run `/infographics:setup` first, or proceed and the footer shows placeholders.

## When not to use it

- **The post is stronger without an image.** Sharp contrarian text posts often win alone. Decide first: no image, a real screenshot, or a rendered graphic.
- **The proof is a real artifact.** A screenshot of the actual dashboard, doc or message beats a redrawn one.
- **You need logos fetched.** Get them first (the `deck-graphics` plugin has a logo chain, or save favicons), then point the spec at the files.

## Steps

1. **Read** `${CLAUDE_PLUGIN_ROOT}/RULES.md` (learned rules) and `${CLAUDE_PLUGIN_ROOT}/templates/CATALOG.md` (every type: when to use it, layout, type sizes, content budget).

2. **Pick the type from what the reader is hunting for:**

| The reader wants | Types |
|---|---|
| A better process: an SOP, a workflow, a decision | `layers`, `workflow`, `tree`, `cycle`, `steps`, `cheatsheet`, `levels` |
| Hot tools and tech | `layers`, `stack`, `comparison` (archetype `matrix`) |
| Sharp people to learn from | `resources` |
| Events to go to | `events` |
| A real thing to learn from | `case`, `belief` (archetype `versus`), `versus`, `bento`, `stats`, `trend`, `split` |

   The strongest angle is often a known idea applied to a niche: not "the GTM stack" but "the GTM stack for MCP companies". Put the niche words in the headline.

3. **Copy the template** from `${CLAUDE_PLUGIN_ROOT}/templates/{type}/spec.json` into the output folder (or anywhere in the repo). Delete `"placeholder": true`. Delete `"preset"` so the style rotates.

4. **Replace every placeholder with real, concrete copy.** Real tool names with logo files, real people (public information only), real numbers with their source in `note`. Headline under about 10 words with one `[[keyword]]`. Stay inside the catalog's budgets.

5. **Check the text:** `node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" check path/to/spec.json`

6. **Render:** `node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" path/to/spec.json`
   Add `--ref path/to/reference.png` to put a graphic you admire beside yours on the review sheet. Add `variants` to the spec for a second style or size.

7. **Look at every PNG and the 360px phone preview with the Read tool.** The checks catch overflow and typos, not taste. They passed graphics with hidden arrows and half-empty canvases. Ask: does the headline read at phone size in two seconds? Is it as dense and specific as the reference? Any orphan words, collisions or dead space?

8. **Fix and re-render** until clean. If it overflows, cut copy or drop an item before accepting shrunk text. Show the user `sheet.png`.

9. **Learn.** A problem you fix twice becomes a numbered rule in `RULES.md`.

## Styles and rotation

Five built-in kits: `pop` (warm light), `midnight` (navy), `electric` (white and blue with a yellow marker), `citrus` (loud yellow, hard shadows), `ocean` (deep teal). With no `preset`, the renderer picks the kit in `rotation` used longest ago and logs it in `{output_dir}/_rotation.json`, so three posts a week don't repeat a look. A re-render keeps its first style. Custom kits: see `${CLAUDE_PLUGIN_ROOT}/styles/README.md`. The classic `paper`, `exhibit` and `navy` styles use the brand token file from the config.

## Spec reference

```json
{
  "slug": "short-name",
  "archetype": "one of the types below",
  "preset": "omit to rotate, or a kit name",
  "size": "portrait | square | landscape | tall",
  "eyebrow": "SHORT LABEL",
  "title": "Headline that states the [[finding]]",
  "subtitle": "One line of context",
  "note": "Source: where every number came from (printed on the image)",
  "footer": { "author": "override", "url": "override", "wordmark": false, "actions": ["Save", "Repost"] },
  "byline": false,
  "byline_avatar": false,
  "allow": ["NamesTheSpellcheckerDoesntKnow"],
  "caption": "post text or a path to it; adds a feed mock to the review sheet",
  "variants": [{ "name": "square", "size": "square" }],
  "data": {}
}
```

Inline markup anywhere: `**bold**`, `[[highlight]]`, `` `code` ``, and `\n` for a forced line break. A logo or avatar is a path relative to the spec; without one, a monogram is drawn. Each template's `spec.json` is a complete worked example of its `data`:

- **stack**: `groups` [{`name`, `note`?, `price`?, `tools` [name or {`name`, `logo`}], `featured`?, `wide`?}]
- **layers**: `layers` top to bottom [{`icon`, `name`, `tag`?, `body`, `tools`}], `labels` (logos with names), `top_width`, `strip` ({`title`} or `false`)
- **workflow**: `steps` [{`title`, `body`, `tools`?, `flow` [input, tool, output]}]
- **tree**: `root` {`q`, `icon`?, `branches` [{`label`, `node`}]}; a leaf is {`outcome`, `note`?, `tone` good/bad/neutral, `icon`?}
- **cycle**: `stages` [{`title`, `body`, `tag`?, `human`?}], `center` {`title`, `body`}
- **levels**: `levels` [{`name`, `tag`?, `summary`?, `rows` [{`label`, `text`}], `flow` []}]
- **steps**: `steps` [{`title`, `body`}], `layout` list or grid
- **cheatsheet**: `items` [{`title`, `body`}], `columns`
- **resources**: `groups` [{`kind`, `name`, `items` [{`name`, `handle`?, `why`?, `avatar`?}]}]
- **events**: `events` [{`name`, `month`, `days`, `city`, `host`?, `why`, `tag`?, `price`?, `logo`?}]
- **versus** (and belief): `left_title`, `right_title`, `pairs` [[left, right], …]
- **case**: `results` [{`value`, `label`}], `setup` [{`icon`, `label`, `value`}], `steps` [{`title`, `body`}], `lesson`
- **bento**: `cards` [{`tag`, `title`, `big`?, `points`, `wide`?}]
- **matrix** (comparison): `columns` [{`name`, `logo`?}], `rows` [{`label`, `cells`, `center`?}], `pick`, `label_width`?
- **stats**: `stats` [{`value`, `label`, `sub`?}], `pick`, `columns`?
- **trend**: `series` [{`name`, `points` [[label, number]], `accent`?}], `time`, `unit`, `prefix`, `y_label`, `annotations`, `context` [{`date`, `text`}]
- **split**: `left` / `right` {`label`, `title`, `points`}, `divider`, `pick`

Icon names are listed in `${CLAUDE_PLUGIN_ROOT}/scripts/icons.mjs`.

## What the checks catch

Errors block: content overflowing the canvas after fitting, text off the canvas or spilling out of its box, overlapping cards, text too small to read on a phone, a headline that won't read at feed size, broken images, misspellings (macOS dictionary), and row or column count mismatches. Warnings: copy over budget, no highlighted keyword, numbers with no source line, repeated words. Text is fitted automatically between 80% and 160% of its base size.

## Output

In `output_dir` from the config (default `graphics/`), a folder per graphic, `MMYY-{slug}/`: `spec.json` (the exact copy), `{variant}.png` at 2x, `{variant}-360.png` phone preview, `{variant}.html` source, `qa.json` with every check result, and `sheet.png` when there are variants, a reference or a caption.

## Commands

```
node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" <spec.json> [--out DIR] [--ref IMAGE] [--only NAME]
node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" check <spec.json>
node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" compare OUT.png "Label=a.png" "Label=b.png"
node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" templates
```

`IGR_DEBUG=1` prints step timing if a render seems stuck.
