# Style kits

A kit is one JSON file: a name, a light or dark mode, and a set of colors. The renderer turns it into CSS variables, so every template works in every kit. Built-in kits live here; add your own in any folder listed under `kits_dirs` in `.infographic.json`. A kit with the same name as a built-in replaces it.

```json
{
  "name": "my-kit",
  "label": "One line describing the look",
  "mode": "light",
  "marker": false,
  "card_shadow": null,
  "card_border": null,
  "colors": {
    "bg": "#FBF7F1", "grid": "rgba(20,20,40,0.055)",
    "text": "#14141F", "text_soft": "#3A3A4A", "muted": "#7A7885",
    "line": "#E4DDD2", "card": "#FFFFFF", "card_line": "#E7E0D6", "chip": "#FFFFFF",
    "code_bg": "#F2EDE5", "code_text": "#2B2B3A",
    "accent1": "#F25C2A", "accent2": "#1E1EF6", "accent3": "#12A37F", "accent4": "#8B5CF6", "accent5": "#E8A300",
    "keyword": "#F25C2A", "highlight": "#FFE14D", "badge_text": "#FFFFFF",
    "good": "#12A37F", "good_soft": "#E3F6EF", "bad": "#E23D2E", "bad_soft": "#FDE8E5",
    "label_bg": null, "label_text": null
  }
}
```

- **accent1–5** rotate through sections, steps and badges. Pick five that are distinct from each other and readable against `card`.
- **keyword** colors the highlighted word in the title. **marker: true** draws `highlight` behind it instead, like a highlighter pen.
- **badge_text** is the text color on accent fills: white for saturated accents, dark for pastel or neon ones.
- **good / bad** drive the versus template.
- **card_shadow** and **card_border** give a kit its own feel (citrus uses a hard offset shadow).

Add the kit's name to `rotation` in `.infographic.json` to include it in the automatic rotation.

| Kit | Mode | Feel |
|---|---|---|
| `pop` | light | warm off-white, orange keyword, five bright accents |
| `midnight` | dark | navy card that stands out in a light feed |
| `electric` | light | white, electric blue, yellow marker highlight |
| `citrus` | light | loud yellow, black ink, hard offset shadows |
| `ocean` | dark | deep teal, mint keyword, warm accents |
