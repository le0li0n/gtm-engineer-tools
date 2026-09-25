// Brand + style-kit configuration. Nothing brand-specific is hard-coded in the renderer:
// each repo that installs it supplies `.infographic.json` at its root (see config.example.json),
// and color kits are JSON files (built-ins in ../styles, plus any folders the config lists).
import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { resolve, dirname, join, basename } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
export const SKILL = dirname(HERE);

const DEFAULTS = {
  brand: {
    name: '',              // company or personal brand name, used as wordmark alt text
    author: '',            // default byline / footer name
    url: '',               // default footer URL
    avatar: null,          // path to a square headshot; a monogram is generated if missing
    wordmark_light: null,  // wordmark image for light backgrounds
    wordmark_dark: null,   // wordmark image for dark backgrounds
    tokens_css: null,      // optional brand token CSS (defines --uv-* for the classic presets)
    italic_word: null,     // optional brand rule: a word always set in italic in titles
  },
  output_dir: 'graphics',
  kits_dirs: [],           // extra folders of style-kit JSON files
  rotation: ['pop', 'midnight', 'electric', 'citrus', 'ocean'],
  footer_actions: ['Save', 'Repost'],
};

function findConfig(start) {
  let d = resolve(start);
  for (let i = 0; i < 12; i++) {
    const f = join(d, '.infographic.json');
    if (existsSync(f)) return f;
    const up = dirname(d); if (up === d) break; d = up;
  }
  return null;
}

let cache = new Map();
export function loadConfig(start = process.cwd()) {
  const file = findConfig(start) || findConfig(process.cwd()) || findConfig(HERE);
  const key = file || '(defaults)';
  if (cache.has(key)) return cache.get(key);
  const user = file ? JSON.parse(readFileSync(file, 'utf8')) : {};
  const root = file ? dirname(file) : process.cwd();
  const cfg = { ...DEFAULTS, ...user, brand: { ...DEFAULTS.brand, ...(user.brand || {}) }, root, file };
  const abs = p => (p ? resolve(root, p) : null);
  for (const k of ['avatar', 'wordmark_light', 'wordmark_dark', 'tokens_css']) cfg.brand[k] = abs(cfg.brand[k]);
  cfg.output_dir = resolve(root, cfg.output_dir);
  cfg.kits = loadKits([join(SKILL, 'styles'), ...cfg.kits_dirs.map(abs)]);
  cache.set(key, cfg);
  return cfg;
}

// A kit: { "name", "label", "mode": "light"|"dark", "colors": {...}, "fonts"?: {...}, "card_shadow"?: "...", "card_border"?: "..." }
export function loadKits(dirs) {
  const kits = {};
  for (const d of dirs) {
    if (!d || !existsSync(d)) continue;
    for (const f of readdirSync(d).filter(f => f.endsWith('.json')).sort()) {
      const k = JSON.parse(readFileSync(join(d, f), 'utf8'));
      k.name = k.name || basename(f, '.json');
      kits[k.name] = k; // later folders override built-ins with the same name
    }
  }
  return kits;
}

const VARMAP = { bg: 'bg', grid: 'grid', text: 'fg', text_soft: 'fg-soft', muted: 'muted', line: 'line', card: 'card', card_line: 'card-line',
  chip: 'chip', code_bg: 'code-bg', code_text: 'code-fg', accent1: 'c1', accent2: 'c2', accent3: 'c3', accent4: 'c4', accent5: 'c5',
  highlight: 'hl-bg', keyword: 'kw', good: 'good', good_soft: 'good-soft', bad: 'bad', bad_soft: 'bad-soft', badge_text: 'badge-fg',
  label_bg: 'label-bg', label_text: 'label-fg' };

export function kitCss(kit) {
  const c = kit.colors || {};
  const v = Object.entries(VARMAP).filter(([k]) => c[k]).map(([k, css]) => `--${css}: ${c[k]};`);
  // Classic-archetype variables, derived so matrix/steps/cycle/split/trend/stats also work in every kit.
  v.push(`--accent: ${c.accent1 || c.keyword}; --strong-card: ${c.card}; --series-2: ${c.text};`,
    `--footer-bg: transparent; --footer-fg: ${c.text_soft || c.text}; --footer-accent: ${c.keyword || c.accent1};`);
  if (!c.label_bg) v.push(`--label-bg: ${c.accent1}; --label-fg: ${c.badge_text || '#FFFFFF'};`);
  if (!c.highlight) v.push('--hl-bg: transparent;');
  if (kit.fonts?.sans) v.push(`--sans: ${kit.fonts.sans};`);
  if (kit.fonts?.mono) v.push(`--mono: ${kit.fonts.mono};`);
  let css = `.preset-${kit.name} { ${v.join(' ')} }\n`;
  if (kit.card_shadow) css += `.preset-${kit.name} .scard { box-shadow: ${kit.card_shadow}; }\n`;
  if (kit.card_border) css += `.preset-${kit.name} .scard { border-width: ${kit.card_border}; }\n`;
  if (kit.marker) css += `.preset-${kit.name} .title .hl { background: linear-gradient(transparent 58%, var(--hl-bg) 58%, var(--hl-bg) 92%, transparent 92%) !important; color: inherit !important; }\n`;
  return css;
}
