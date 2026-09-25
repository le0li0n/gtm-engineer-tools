# infographics

LinkedIn infographics from a JSON spec. Nineteen template types built from what performs in the feed, five color kits that rotate so a feed doesn't repeat itself, and checks that run before anyone looks.

## The problem

The graphics that do well on LinkedIn look like reference sheets someone spent hours on: a bold headline that states the finding, one keyword in color, real logos and faces, real numbers with a source, a dense body that earns the save. Making one by hand takes an afternoon in a design tool. Asking an image model for one gets you misspelled words and invented numbers.

The first version of this renderer made tasteful deck slides: thin headlines, lots of space, one color. Side by side with the graphics it was meant to match, the gap was obvious, and the templates here are the result of closing it.

## Install

```
/plugin marketplace add le0li0n/gtm-engineer-tools
/plugin install infographics
```

Then, in your repo:

```
/infographics:setup
```

It asks for your name, URL, headshot and wordmarks, writes `.infographic.json`, optionally makes a color kit from your brand, and renders one template to prove it works.

## Use

```
/infographics:render
```

Describe the idea, or point at a post. The skill picks a template type from what the reader is hunting for (a better process, hot tools, people to learn from, events, or a real thing someone learned), fills it with your exact copy, renders it, and looks at every PNG before showing you the review sheet.

## The templates

| Type | For |
|---|---|
| `layers` | an architecture or stack of responsibilities that widens toward its foundation |
| `stack` | tools grouped by job, a market map |
| `workflow` | a process someone can copy, each step with input → tool → output |
| `tree` | a decision: two or three questions, colored outcomes |
| `cycle` | a loop that repeats |
| `levels` | a progression or three modes |
| `steps` | a numbered how-to |
| `cheatsheet` | a dense list worth saving |
| `resources` | people, newsletters and podcasts to follow |
| `events` | where to be this season |
| `versus` / `belief` | mistakes and fixes; what we believed and what the data said |
| `case` | one campaign broken down: results, setup, steps, lesson |
| `bento` | a roundup of unlike things |
| `comparison` | X vs Y vs Z across the same criteria |
| `stats` | two to six hard numbers |
| `trend` | a number over time, endpoints labeled |
| `split` | two approaches, one better |

Each has a placeholder `spec.json` and a rendered `preview.png` in `templates/`, and `templates/gallery.png` shows them together. `templates/CATALOG.md` describes each one's layout, type sizes, text-to-image balance and content budget.

## Your brand

Nothing brand-specific lives in the plugin. `.infographic.json` at your repo root sets the author, URL, headshot, wordmarks, output folder and style rotation. Color kits are small JSON files (`styles/README.md`); add your own folder of them and they join the rotation. `config.example.json` shows every field.

The five built-in kits are a starting point, and everyone who installs the plugin gets the same five. Planned for v2: generate a unique set of kits for each user from their brand, so no two feeds share a look.

## Rules that came out of things going wrong

`RULES.md` is the list, and it grows. A few of them:

- **Passing checks is not done.** The checks passed graphics with arrows hidden under cards and a canvas 40% empty. The skill looks at every PNG.
- **Pull numbers from the source, not a summary.** A summary said "5.6x"; the source said "561% more", which is 6.6x.
- **Don't squeeze a variant that overflows.** Drop it; shrunk text is the failure.
- **A re-render keeps its style.** Rotation assigns a kit once.

## Requirements

Google Chrome (set `CHROME=/path/to/chrome` if it's elsewhere), Node 22 or later (it uses the built-in WebSocket to drive Chrome), and macOS for the spellcheck; elsewhere the check warns and you proofread by eye. No npm packages.
