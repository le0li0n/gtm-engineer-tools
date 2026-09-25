---
name: setup
description: >-
  Set up infographics in the repo you are in: interview for brand name, author, URL,
  headshot, wordmarks and where graphics should go, write .infographic.json at the repo
  root, optionally create a custom color kit, then render one template to prove it works.
  Use when the user says "/infographics:setup", "set up infographics", "add my brand to
  the graphics", "use my headshot", "make a color kit", or has just installed the plugin.
---

# setup

Writes `.infographic.json` at the root of the repo you are in. Every graphic reads it for the byline, the Follow footer, the wordmark, the output folder and the style rotation. Nothing brand-specific lives in the plugin.

## Steps

1. **Check for an existing config.** If `.infographic.json` exists at the repo root, read it and ask only about what the user wants to change.

2. **Ask, one question at a time, with defaults.** Skip anything the user doesn't have yet; the renderer fills gaps with sensible placeholders.
   - Brand or company name (wordmark alt text)
   - Author name and URL for the footer ("Follow {author} · {url}")
   - A square headshot. If they give a photo that isn't square, crop it around the face to 600×600 (Pillow or `sips`) and save it next to the config, for example `brand/headshot.jpg`. Look at the crop before using it. Without one, a monogram is drawn.
   - Wordmark images for light and dark backgrounds (optional)
   - Where rendered graphics should go (default `graphics/`)
   - Optional brand token CSS for the classic `paper` / `exhibit` / `navy` styles. It must define the `--uv-*` variables listed in `${CLAUDE_PLUGIN_ROOT}/scripts/default-tokens.css`. Most people skip this; the five rotating kits don't need it.

3. **Write the config** from `${CLAUDE_PLUGIN_ROOT}/config.example.json`, with paths relative to the repo root.

4. **Offer a custom color kit.** If the user wants their brand colors in the rotation, write a kit JSON in a folder of their choice (for example `brand/kits/{name}.json`) following `${CLAUDE_PLUGIN_ROOT}/styles/README.md`: five distinct accents readable on the card color, a keyword color, good and bad colors for the versus template, and `badge_text` dark for pastel accents or white for saturated ones. Add the folder to `kits_dirs` and the kit name to `rotation`.

5. **Prove it.** Copy one template into the output folder and render it:

```
cp "${CLAUDE_PLUGIN_ROOT}/templates/stats/spec.json" graphics/setup-test.json
node "${CLAUDE_PLUGIN_ROOT}/scripts/render.mjs" graphics/setup-test.json
```

   Look at the PNG with the Read tool: name, URL, headshot and wordmark in the footer, colors from the kit if one was made. Then delete the test spec and its output folder, since both only exist to prove the setup.

## Requirements

Google Chrome (set `CHROME=/path/to/chrome` if it isn't in the default place), Node 22 or later, and macOS for the spellcheck (elsewhere the check warns and you proofread by eye). No npm packages.
