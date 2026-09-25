// Spec → self-contained HTML. One builder per archetype. No text is generated here:
// every word and number comes from the spec.
import { readFileSync, existsSync } from 'node:fs';
import { resolve, dirname, extname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadConfig, kitCss } from './config.mjs';
import { SHEET_BUILDERS, monoAvatar } from './templates.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));

export const SIZES = {
  portrait: { w: 1080, h: 1350, fixed: true },
  square: { w: 1080, h: 1080, fixed: true },
  landscape: { w: 1200, h: 627, fixed: true },
  tall: { w: 1080, h: 1350, fixed: false, max: 2700 },
};
export const CLASSIC = ['matrix', 'steps', 'cycle', 'split', 'trend', 'stats'];
export const ARCHETYPES = [...CLASSIC, ...Object.keys(SHEET_BUILDERS)];
export const CLASSIC_PRESETS = ['paper', 'exhibit', 'navy'];

export function repoRoot(start) { return loadConfig(start).root; }

// ---------- text ----------
const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
export function inline(s) {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[\[(.+?)\]\]/g, '<span class="hl">$1</span>')
    .replace(/`(.+?)`/g, '<span class="code">$1</span>')
    .replace(/\n/g, '<br>');
}
// Optional brand rule from config: one word always set in italic in titles.
const display = (s, word) => word ? inline(s).replace(new RegExp(`\\b(${word})\\b`, 'gi'), '<em>$1</em>') : inline(s);
export const plain = s => String(s ?? '').replace(/\*\*|\[\[|\]\]|`/g, '');

function dataUri(path) {
  const ext = extname(path).toLowerCase();
  const mime = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp' }[ext];
  if (!mime) throw new Error(`Unsupported image type: ${path}`);
  return `data:${mime};base64,${readFileSync(path).toString('base64')}`;
}
const logo = (p, base, alt) => p ? `<img src="${dataUri(resolve(base, p))}" alt="${esc(alt)}">` : '';

// ---------- archetypes ----------
function matrix(d, ctx) {
  const cols = d.columns || [];
  const pick = d.pick ?? -1;
  let h = `<div class="matrix" style="grid-template-columns: ${d.label_width || 210}px repeat(${cols.length}, 1fr)">`;
  h += `<div class="corner"></div>`;
  cols.forEach((c, i) => {
    h += `<div class="colhead${i === pick ? ' pick' : ''}" data-box>${logo(c.logo, ctx.base, c.name)}<span>${inline(c.name)}</span></div>`;
  });
  for (const r of d.rows || []) {
    h += `<div class="rowlabel" data-box>${inline(r.label)}</div>`;
    (r.cells || []).forEach((c, i) => {
      h += `<div class="cell${i === pick ? ' pick' : ''}${r.center ? ' center' : ''}" data-box><span>${inline(c)}</span></div>`;
    });
  }
  return h + '</div>';
}

function steps(d) {
  const list = d.steps || [];
  const grid = d.layout === 'grid';
  return `<div class="steps${grid ? ' grid' : ''}">` + list.map((s, i) =>
    `<div class="step" data-box><div class="n">${String(i + 1).padStart(2, '0')}</div><div><h3>${inline(s.title)}</h3>${s.body ? `<p>${inline(s.body)}</p>` : ''}</div></div>`
  ).join('') + '</div>';
}

function cycle(d, ctx) {
  const st = d.stages || [];
  const h = ctx.fixed ? '' : ` style="position:relative;height:${d.height || 1000}px"`;
  return `<div class="cycle"${h}><svg class="arcs"></svg>` +
    (d.center ? `<div class="center"><h3>${inline(d.center.title)}</h3>${d.center.body ? `<p>${inline(d.center.body)}</p>` : ''}</div>` : '') +
    st.map((s, i) => `<div class="stage${s.human ? ' human' : ''}" data-box><div class="k">${String(i + 1).padStart(2, '0')}${s.tag ? ' · ' + esc(s.tag) : ''}</div><h3>${inline(s.title)}</h3>${s.body ? `<p>${inline(s.body)}</p>` : ''}</div>`).join('') +
    `</div>`;
}

function split(d) {
  const side = (s, k) => `<div class="side${d.pick === k ? ' pick' : ''}" data-box>${s.label ? `<div class="lab">${inline(s.label)}</div>` : ''}<h3>${inline(s.title)}</h3><ul>${(s.points || []).map(p => `<li>${inline(p)}</li>`).join('')}</ul></div>`;
  return `<div class="split">${side(d.left || {}, 'left')}<div class="div">${esc(d.divider || '≠')}</div>${side(d.right || {}, 'right')}</div>`;
}

function niceMax(v) {
  if (v <= 0) return 1;
  const p = Math.pow(10, Math.floor(Math.log10(v)));
  for (const m of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) if (m * p >= v * 1.08) return m * p;
  return 10 * p;
}

function trend(d) {
  const series = d.series || [];
  const labels = d.x || series[0]?.points.map(p => p[0]) || [];
  const fmt = v => `${d.prefix || ''}${Number(v).toLocaleString('en-US')}${d.unit || ''}`;
  const W = 900, H = d.chart_height || ((d.context || []).length ? 380 : 470), L = 64, R = 96, T = 34, B = 52;
  const max = d.y_max ?? niceMax(Math.max(...series.flatMap(s => s.points.map(p => p[1]))));
  // "time": true spaces points by real date ("Dec 2024"), so uneven gaps don't distort the slope.
  const ts = d.time ? labels.map(l => Date.parse('1 ' + l)) : null;
  if (ts && ts.some(isNaN)) throw new Error('trend "time": true needs labels like "Dec 2024"');
  const xi = i => labels.length === 1 ? L
    : ts ? L + ((ts[i] - ts[0]) / (ts[ts.length - 1] - ts[0])) * (W - L - R)
    : L + (i * (W - L - R)) / (labels.length - 1);
  const yv = v => T + (1 - v / max) * (H - T - B);
  let svg = `<svg viewBox="0 0 ${W} ${H}" xmlns="http://www.w3.org/2000/svg">`;
  for (let k = 0; k <= 4; k++) {
    const v = (max * k) / 4, y = yv(v);
    svg += `<line class="grid" x1="${L}" x2="${W - R + 20}" y1="${y}" y2="${y}"/><text class="tick" x="${L - 12}" y="${y + 6}" text-anchor="end">${fmt(Math.round(v * 100) / 100)}</text>`;
  }
  labels.forEach((lab, i) => { svg += `<text class="tick" x="${xi(i)}" y="${H - 14}" text-anchor="middle">${esc(lab)}</text>`; });
  for (const a of d.annotations || []) {
    const i = labels.indexOf(a.x); if (i < 0) continue;
    svg += `<line class="annline" x1="${xi(i)}" x2="${xi(i)}" y1="${T - 8}" y2="${H - B}"/><text class="ann" x="${xi(i) + 8}" y="${T + 4}">${esc(a.text)}</text>`;
  }
  const ends = [];
  series.forEach((s, si) => {
    const color = s.accent || (si === 0 && !series.some(x => x.accent)) ? 'var(--accent)' : 'var(--series-2)';
    const pts = s.points.map(p => [xi(labels.indexOf(p[0])), yv(p[1]), p[1]]);
    svg += `<polyline fill="none" style="stroke:${color}" stroke-width="5" stroke-linejoin="round" stroke-linecap="round" points="${pts.map(p => p[0] + ',' + p[1]).join(' ')}"/>`;
    pts.forEach(p => { svg += `<circle cx="${p[0]}" cy="${p[1]}" r="8" style="fill:var(--card);stroke:${color}" stroke-width="4"/>`; });
    const first = pts[0], last = pts[pts.length - 1];
    // First-value label sits right of the point, on the side the line is not heading
    // (below a rising line, above a falling one), so it never meets the axis ticks or the line.
    const rising = pts.length > 1 && pts[1][1] < first[1];
    ends.push({ x: first[0] + 16, y: rising ? first[1] + 34 : first[1] - 18, v: first[2], color, anchor: 'start' });
    ends.push({ x: last[0] + 18, y: last[1] + 8, v: last[2], color, anchor: 'start', last: true });
  });
  // keep end labels on the right from colliding
  const lasts = ends.filter(e => e.last).sort((a, b) => a.y - b.y);
  for (let i = 1; i < lasts.length; i++) if (lasts[i].y - lasts[i - 1].y < 28) lasts[i].y = lasts[i - 1].y + 28;
  for (const e of ends) svg += `<text class="endlab" x="${e.x}" y="${e.y}" text-anchor="${e.anchor}" style="fill:${e.color}">${fmt(e.v)}</text>`;
  svg += '</svg>';

  const legend = series.length > 1 || d.legend ? `<div class="legend">${series.map((s, si) => {
    const color = s.accent || (si === 0 && !series.some(x => x.accent)) ? 'var(--accent)' : 'var(--series-2)';
    return `<span><i style="background:${color}"></i>${inline(s.name)}</span>`;
  }).join('')}</div>` : '';
  const ctxs = d.context || [];
  const context = ctxs.length ? `<div class="ctx-head">${esc(d.context_title || "What's behind it")}</div><div class="context" style="grid-template-columns: repeat(${ctxs.length}, 1fr)">${ctxs.map(c => `<div class="c" data-box><div class="d">${esc(c.date)}</div><div class="t">${inline(c.text)}</div></div>`).join('')}</div>` : '';
  return `${legend}<div class="chart">${d.y_label ? `<div class="cap">${esc(d.y_label)}</div>` : ''}${svg}</div>${context}`;
}

function stats(d) {
  const list = d.stats || [];
  const cols = d.columns || (list.length <= 3 ? list.length : list.length === 4 ? 2 : 3);
  return `<div class="stats" style="grid-template-columns: repeat(${cols}, 1fr)">` + list.map((s, i) =>
    `<div class="stat${i === d.pick ? ' pick' : ''}" data-box><div class="v">${esc(s.value)}</div><div class="l">${inline(s.label)}</div>${s.sub ? `<div class="s">${inline(s.sub)}</div>` : ''}</div>`
  ).join('') + '</div>';
}

const BUILDERS = { matrix, steps, cycle, split, trend, stats, ...SHEET_BUILDERS };

function titleScale(t) {
  const n = plain(t).length;
  return n <= 26 ? 1.12 : n <= 42 ? 1 : n <= 60 ? 0.86 : 0.74;
}

export function buildHtml(spec, { base }) {
  const cfg = loadConfig(base);
  const size = sizeOf(spec);
  if (!size) throw new Error(`Unknown size "${spec.size}". Use one of ${Object.keys(SIZES).join(', ')} or [w, h].`);
  const preset = spec.preset || cfg.rotation[0];
  const kit = cfg.kits[preset];
  if (!kit && !CLASSIC_PRESETS.includes(preset)) throw new Error(`Unknown style "${preset}". Kits: ${Object.keys(cfg.kits).join(', ')}; classic: ${CLASSIC_PRESETS.join(', ')}.`);
  const b = BUILDERS[spec.archetype];
  if (!b) throw new Error(`Unknown template type "${spec.archetype}". Use one of ${ARCHETYPES.join(', ')}.`);
  if (!kit && SHEET_BUILDERS[spec.archetype]) throw new Error(`Template type "${spec.archetype}" needs a style kit (${Object.keys(cfg.kits).join(', ')}), not the classic "${preset}".`);

  const tokens = readFileSync(cfg.brand.tokens_css && existsSync(cfg.brand.tokens_css) ? cfg.brand.tokens_css : join(HERE, 'default-tokens.css'), 'utf8');
  let css = readFileSync(join(HERE, 'styles.css'), 'utf8');
  if (kit) css += '\n' + readFileSync(join(HERE, 'sheet.css'), 'utf8') + '\n' + kitCss(kit);
  const js = readFileSync(join(HERE, 'page.js'), 'utf8');
  const f = { author: cfg.brand.author, url: cfg.brand.url, ...(spec.footer || {}) };
  const dark = kit ? kit.mode === 'dark' : preset !== 'paper';
  const wmPath = dark ? (cfg.brand.wordmark_dark || cfg.brand.wordmark_light) : (cfg.brand.wordmark_light || cfg.brand.wordmark_dark);
  const wm = f.wordmark === false || !wmPath ? '' : `<img class="wm" alt="${esc(cfg.brand.name)}" src="${dataUri(wmPath)}">`;
  const avPath = f.avatar ? resolve(base, f.avatar) : cfg.brand.avatar;
  const av = `<img class="av" alt="" src="${avPath && existsSync(avPath) ? dataUri(avPath) : monoAvatar(f.author || cfg.brand.name || '?')}">`;
  const body = b(spec.data || {}, { base, fixed: size.fixed });
  const title = display(spec.title, cfg.brand.italic_word);
  const sample = spec.placeholder ? '<div class="sample" data-qa-skip>TEMPLATE · PLACEHOLDER COPY</div>' : '';

  let head, foot;
  if (kit) {
    const byline = spec.byline === false || !f.author ? '' : `<div class="byline" data-meta>${spec.byline_avatar ? av : ""}<span><b>${esc(f.author)}</b>${f.url ? ` · ${esc(f.url)}` : ''}</span></div>`;
    head = `<header>${spec.eyebrow ? `<div class="eyebrow" data-meta>${esc(spec.eyebrow)}</div>` : ''}<h1 class="title" style="--tscale:${spec.title_scale || titleScale(spec.title)}">${title}</h1>${spec.subtitle ? `<p class="subtitle">${inline(spec.subtitle)}</p>` : ''}${byline}</header>`;
    const acts = (f.actions || cfg.footer_actions || []).map(a => `<span class="act">${esc(a)}</span>`).join('');
    foot = `<footer data-meta><div class="follow">${av}<span>Follow <b>${esc(f.author || cfg.brand.name)}</b>${f.url ? ` · <span class="url">${esc(f.url)}</span>` : ''}</span></div><div class="acts">${acts}${wm}</div></footer>`;
  } else {
    const who = [f.author && `<span>${esc(f.author)}</span>`, f.url && `<span class="url">${esc(f.url)}</span>`].filter(Boolean).join('<span class="sep">·</span>');
    head = `<header>${spec.eyebrow ? `<div class="eyebrow" data-meta>${esc(spec.eyebrow)}</div>` : ''}<h1 class="title" style="--tscale:${spec.title_scale || titleScale(spec.title)}">${title}</h1>${spec.subtitle ? `<p class="subtitle">${inline(spec.subtitle)}</p>` : ''}</header>`;
    foot = `<footer data-meta>${wm || '<span></span>'}<div class="who">${who}</div></footer>`;
  }
  return `<!doctype html><html><head><meta charset="utf-8"><title>${esc(plain(spec.title))}</title>
<style>${tokens}\n${css}</style></head>
<body class="preset-${preset}${kit ? ' sheet-style' : ''}" data-fixed="${size.fixed ? 1 : 0}" style="--w:${size.w}px;--h:${size.h}px">
<div class="sheet">${sample}<div class="canvas">
${head}
<main>${body}</main>
${spec.note ? `<div class="note" data-meta>${inline(spec.note)}</div>` : ''}
</div>
${foot}</div>
<script>${js}</script></body></html>`;
}

export function sizeOf(spec) {
  return typeof spec.size === 'object' ? { w: spec.size[0], h: spec.size[1], fixed: true } : SIZES[spec.size || 'portrait'];
}
