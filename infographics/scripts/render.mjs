#!/usr/bin/env node
// infographic-render — spec.json → branded PNGs, checked before anyone looks.
//
//   node render.mjs <spec.json> [--out DIR] [--ref IMAGE] [--only NAME]   render + check + review sheet
//   node render.mjs check <spec.json>                                    text checks only, no Chrome
//   node render.mjs templates                                            re-render every template in ../templates
//
// Chrome is driven over the DevTools protocol (Node's built-in WebSocket), so there is
// nothing to install. Set CHROME=/path/to/chrome if it is not in the default macOS spot.
import { readFileSync, writeFileSync, mkdirSync, existsSync, mkdtempSync, rmSync, readdirSync } from 'node:fs';
import { resolve, dirname, join, basename, relative } from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { buildHtml, sizeOf, plain, ARCHETYPES } from './build.mjs';
import { loadConfig } from './config.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const SKILL = dirname(HERE);
const sleep = ms => new Promise(r => setTimeout(r, ms));
const T0 = Date.now();
const log = (...a) => { if (process.env.IGR_DEBUG) console.error(`[${((Date.now() - T0) / 1000).toFixed(1)}s]`, ...a); };
// Every CDP call gets a deadline, so a wedged Chrome fails loudly instead of hanging the run.
const deadline = (p, ms, what) => Promise.race([p, new Promise((_, rej) => setTimeout(() => rej(new Error(`Timed out after ${ms / 1000}s: ${what}`)), ms).unref())]);

// ---------------- Chrome over CDP ----------------
function chromePath() {
  const cands = [process.env.CHROME, '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    '/Applications/Chromium.app/Contents/MacOS/Chromium', '/usr/bin/google-chrome', '/usr/bin/chromium'].filter(Boolean);
  const hit = cands.find(p => existsSync(p));
  if (!hit) throw new Error('Chrome not found. Set CHROME=/path/to/chrome.');
  return hit;
}

class Chrome {
  async start() {
    this.prof = mkdtempSync(join(tmpdir(), 'igr-'));
    this.proc = spawn(chromePath(), ['--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run',
      '--no-default-browser-check', '--allow-file-access-from-files', `--user-data-dir=${this.prof}`,
      '--remote-debugging-port=0', 'about:blank'], { stdio: 'ignore' });
    const portFile = join(this.prof, 'DevToolsActivePort');
    for (let i = 0; i < 200 && !existsSync(portFile); i++) await sleep(100);
    if (!existsSync(portFile)) throw new Error('Chrome did not start (no DevToolsActivePort).');
    let txt = '';
    for (let i = 0; i < 20 && !txt.includes('\n'); i++) { txt = readFileSync(portFile, 'utf8'); if (!txt.includes('\n')) await sleep(50); }
    const [port, path] = txt.trim().split('\n');
    this.ws = new WebSocket(`ws://127.0.0.1:${port}${path}`);
    this.id = 0; this.pending = new Map(); this.waiters = [];
    this.ws.onmessage = ev => {
      const m = JSON.parse(ev.data);
      if (m.id && this.pending.has(m.id)) {
        const { res, rej } = this.pending.get(m.id); this.pending.delete(m.id);
        m.error ? rej(new Error(m.error.message)) : res(m.result);
      } else if (m.method) {
        this.waiters = this.waiters.filter(w => {
          if (w.method === m.method && w.sid === m.sessionId) { w.res(m.params); return false; }
          return true;
        });
      }
    };
    await new Promise((res, rej) => { this.ws.onopen = res; this.ws.onerror = rej; });
    const { targetId } = await this.send('Target.createTarget', { url: 'about:blank' }, null);
    const { sessionId } = await this.send('Target.attachToTarget', { targetId, flatten: true }, null);
    this.sid = sessionId;
    await this.send('Page.enable');
    await this.send('Runtime.enable');
  }
  send(method, params = {}, sid = this.sid, ms = 45000) {
    const id = ++this.id;
    const msg = { id, method, params }; if (sid) msg.sessionId = sid;
    log('→', method);
    return deadline(new Promise((res, rej) => { this.pending.set(id, { res, rej }); this.ws.send(JSON.stringify(msg)); }), ms, method);
  }
  event(method) { return new Promise(res => this.waiters.push({ method, sid: this.sid, res })); }
  async viewport(w, h, dsf) { await this.send('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: dsf, mobile: false }); }
  async load(url, w, h, dsf = 2) {
    await this.viewport(w, h, dsf);
    const done = this.event('Page.loadEventFired');
    await this.send('Page.navigate', { url });
    await Promise.race([done, sleep(15000)]);
  }
  async eval(expression) {
    const r = await this.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (r.exceptionDetails) throw new Error('Page script failed: ' + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
    return r.result.value;
  }
  async shot(file, w, h) {
    const r = await this.send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: w, height: h, scale: 1 } });
    writeFileSync(file, Buffer.from(r.data, 'base64'));
  }
  async close() {
    try { await this.send('Browser.close', {}, null, 2000); } catch { }
    try { this.ws.close(); } catch { }
    try { this.proc.kill('SIGKILL'); } catch { }
    try { rmSync(this.prof, { recursive: true, force: true }); } catch { }
    log('chrome closed');
  }
}

// ---------------- text checks ----------------
const SKIP_KEYS = new Set(['logo', 'url', 'slug', 'archetype', 'preset', 'size', 'allow', 'variants', 'name', 'pick', 'layout',
  'label_width', 'columns_count', 'height', 'chart_height', 'y_max', 'prefix', 'unit', 'title_scale', 'accent', 'human', 'center', 'wordmark']);

function strings(obj, out = [], key = '') {
  if (typeof obj === 'string') { if (!SKIP_KEYS.has(key)) out.push(obj); }
  else if (Array.isArray(obj)) obj.forEach(v => strings(v, out, key));
  else if (obj && typeof obj === 'object') for (const [k, v] of Object.entries(obj)) if (!SKIP_KEYS.has(k)) strings(v, out, k);
  return out;
}

const BUDGET = {
  title: 12, subtitle: 26,
  matrix: { cell: 18, rows: 12, cols: 4 },
  steps: { min: 3, max: 7, body: 24 },
  cycle: { min: 3, max: 8, body: 14 },
  split: { points: 5, point: 14 },
  stats: { min: 2, max: 6 },
};
const words = s => plain(s).split(/\s+/).filter(Boolean).length;

function allowList(spec) {
  const f = join(SKILL, 'wordlist.txt');
  const base = existsSync(f) ? readFileSync(f, 'utf8').split('\n').map(s => s.trim()).filter(s => s && !s.startsWith('#')) : [];
  return new Set([...base, ...(spec.allow || [])].map(s => s.toLowerCase()));
}

export function textChecks(spec) {
  const errors = [], warnings = [];
  if (!spec.title) errors.push('Spec has no title.');
  if (!ARCHETYPES.includes(spec.archetype)) errors.push(`Unknown archetype "${spec.archetype}".`);
  if (spec.title && words(spec.title) > BUDGET.title) warnings.push(`Title is ${words(spec.title)} words; the studies' best headlines run under ${BUDGET.title}.`);
  if (spec.subtitle && words(spec.subtitle) > BUDGET.subtitle) warnings.push(`Subtitle is ${words(spec.subtitle)} words; keep it under ${BUDGET.subtitle}.`);
  if (spec.title && !/\[\[.+?\]\]/.test(spec.title)) warnings.push('Title has no [[highlighted]] key word. The highlight is the signature device; use it unless there is a reason not to.');
  const d = spec.data || {};
  const a = spec.archetype;
  if (a === 'matrix') {
    const n = (d.columns || []).length;
    if (n > BUDGET.matrix.cols) warnings.push(`${n} columns; more than ${BUDGET.matrix.cols} gets hard to read on a phone.`);
    if ((d.rows || []).length > BUDGET.matrix.rows) warnings.push(`${d.rows.length} rows; consider size "tall" or cutting rows.`);
    for (const r of d.rows || []) {
      if ((r.cells || []).length !== n) errors.push(`Row "${r.label}" has ${(r.cells || []).length} cells for ${n} columns.`);
      for (const c of r.cells || []) if (words(c) > BUDGET.matrix.cell) warnings.push(`Cell in "${r.label}" is ${words(c)} words: "${plain(c).slice(0, 40)}…"`);
    }
  }
  if (a === 'steps') {
    const n = (d.steps || []).length;
    if (n < BUDGET.steps.min || n > BUDGET.steps.max) warnings.push(`${n} steps; ${BUDGET.steps.min}–${BUDGET.steps.max} reads best.`);
    for (const s of d.steps || []) if (s.body && words(s.body) > BUDGET.steps.body) warnings.push(`Step "${plain(s.title)}" body is ${words(s.body)} words.`);
  }
  if (a === 'cycle') {
    const n = (d.stages || []).length;
    if (n < BUDGET.cycle.min || n > BUDGET.cycle.max) warnings.push(`${n} stages; ${BUDGET.cycle.min}–${BUDGET.cycle.max} fit a ring.`);
    for (const s of d.stages || []) if (s.body && words(s.body) > BUDGET.cycle.body) warnings.push(`Stage "${plain(s.title)}" body is ${words(s.body)} words; ring cards hold about ${BUDGET.cycle.body}.`);
  }
  if (a === 'split') for (const k of ['left', 'right']) {
    const pts = d[k]?.points || [];
    if (pts.length > BUDGET.split.points) warnings.push(`${k} side has ${pts.length} points; keep to ${BUDGET.split.points}.`);
    for (const p of pts) if (words(p) > BUDGET.split.point) warnings.push(`${k} point is ${words(p)} words: "${plain(p).slice(0, 40)}…"`);
  }
  if (a === 'stats') {
    const n = (d.stats || []).length;
    if (n < BUDGET.stats.min || n > BUDGET.stats.max) warnings.push(`${n} stats; ${BUDGET.stats.min}–${BUDGET.stats.max} reads best.`);
  }
  if (a === 'trend') {
    for (const s of d.series || []) for (const p of s.points || []) if (typeof p[1] !== 'number') errors.push(`Series "${s.name}" has a non-number value at ${p[0]}.`);
  }

  // Cardinal rule: numbers on a graphic need a stated source.
  const all = strings(spec);
  const hasNumbers = all.some(s => /\d/.test(plain(s))) || a === 'trend' || a === 'stats';
  if (hasNumbers && !spec.note && !spec.sources && !spec.placeholder) warnings.push('The graphic shows numbers but the spec has no "note" (on-image source line) or "sources" list. Every number must trace to a source.');

  // Repeated words ("the the").
  for (const s of all) { const m = plain(s).match(/\b(\w+)\s+\1\b/i); if (m) warnings.push(`Repeated word "${m[1]}" in "${plain(s).slice(0, 50)}"`); }

  // Spelling, with the macOS system dictionary.
  const allow = allowList(spec);
  const toks = new Set();
  for (const s of all) for (const t of plain(s).match(/[A-Za-z][A-Za-z'’]*[A-Za-z]|[A-Za-z]/g) || []) {
    const w = t.replace(/[’']s$/, '');
    if (w.length < 3 || /^[A-Z0-9]+$/.test(w) || allow.has(w.toLowerCase())) continue;
    toks.add(w);
  }
  let misspelled = [];
  if (toks.size && !spec.placeholder) {
    try {
      misspelled = JSON.parse(execFileSync('osascript', ['-l', 'JavaScript', join(HERE, 'spell.js'), JSON.stringify([...toks])], { encoding: 'utf8', timeout: 30000 }).trim());
    } catch (e) { warnings.push('Spellcheck unavailable (needs macOS osascript). Proofread by eye.'); }
  }
  if (misspelled.length) errors.push(`Possible misspellings: ${misspelled.join(', ')}. Fix them, or add real names/terms to the spec's "allow" list or wordlist.txt.`);
  return { errors, warnings, misspelled };
}

// ---------------- rendering ----------------
function variantsOf(spec) {
  const base = { ...spec }; delete base.variants;
  const list = [{ name: spec.name || 'main', ...base }];
  for (const v of spec.variants || []) list.push({ ...base, ...v, data: v.data || base.data, name: v.name || `v${list.length + 1}` });
  return list;
}

function mmyy(d = new Date()) { return String(d.getMonth() + 1).padStart(2, '0') + String(d.getFullYear()).slice(2); }

function reviewHtml(items, ref, caption, spec) {
  const css = readFileSync(join(HERE, 'styles.css'), 'utf8');
  const fig = (src, cap, sub, w) => `<figure><figcaption>${cap}${sub ? `<small>${sub}</small>` : ''}</figcaption><img src="${src}" style="width:${w}px"></figure>`;
  let h = '';
  if (ref) h += fig(pathToFileURL(resolve(ref)).href, 'Reference', basename(ref), 540);
  for (const it of items) h += fig(pathToFileURL(it.png).href, it.name, `${it.preset} · ${it.w}×${it.h}${it.errors.length ? ` · ${it.errors.length} error(s)` : ''}`, 540);
  for (const it of items) h += fig(pathToFileURL(it.preview).href, `${it.name} at phone width`, '360px, how most people first see it', 360);
  if (caption) {
    const lines = caption.split('\n');
    const fold = lines.slice(0, 3).join('\n');
    h += `<figure><figcaption>In the feed<small>first three lines, then the graphic</small></figcaption><div class="feed"><div class="who"><div class="av"></div><div><div class="nm">${(spec.footer?.author || 'Author').replace(/</g, '')}</div><div class="hd">1h</div></div></div><div class="cap">${fold.replace(/</g, '&lt;')}${lines.length > 3 ? ' <span class="more">…more</span>' : ''}</div><img src="${pathToFileURL(items[0].png).href}"></div></figure>`;
  }
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body style="margin:0;background:#F2F0EC"><div class="review">${h}</div></body></html>`;
}

// ---------------- style rotation ----------------
function readLog(f) { try { return JSON.parse(readFileSync(f, 'utf8')); } catch { return []; } }
function pickStyle(cfg, logFile, slug) {
  const prior = readLog(logFile).find(e => e.slug === slug);
  if (prior) return prior.preset; // a re-render keeps the look it was given
  const log = readLog(logFile);
  const last = Object.fromEntries(cfg.rotation.map(n => [n, -1]));
  log.forEach((e, i) => { if (e.preset in last) last[e.preset] = i; });
  return cfg.rotation.filter(n => cfg.kits[n] || ['paper', 'exhibit', 'navy'].includes(n))
    .sort((a, b) => last[a] - last[b])[0] || cfg.rotation[0];
}
function logStyle(logFile, slug, preset) {
  const log = readLog(logFile).filter(e => e.slug !== slug);
  log.push({ slug, preset, date: new Date().toISOString().slice(0, 10) });
  mkdirSync(dirname(logFile), { recursive: true });
  writeFileSync(logFile, JSON.stringify(log, null, 2) + '\n');
}

export async function render(specPath, opts = {}) {
  const spec = JSON.parse(readFileSync(specPath, 'utf8'));
  const base = dirname(resolve(specPath));
  const cfg = loadConfig(base);
  const root = cfg.root;
  const out = resolve(opts.out || join(cfg.output_dir, `${mmyy()}-${spec.slug || basename(specPath, '.json')}`));
  // Style rotation: "auto" (or no preset) picks the kit used longest ago, so a feed posting
  // three times a week doesn't repeat the same look. Real graphics are logged; templates aren't.
  const logFile = join(cfg.output_dir, '_rotation.json');
  const logging = !opts.out && !spec.placeholder;
  if (!spec.preset || spec.preset === 'auto') spec.preset = pickStyle(cfg, logFile, spec.slug);
  mkdirSync(out, { recursive: true });
  if (resolve(specPath) !== join(out, 'spec.json')) writeFileSync(join(out, 'spec.json'), JSON.stringify(spec, null, 2) + '\n');

  const text = textChecks(spec);
  const variants = variantsOf(spec).filter(v => !opts.only || v.name === opts.only);
  const chrome = new Chrome();
  await chrome.start();
  const results = [];
  try {
    for (const v of variants) {
      for (const t of textChecks(v).misspelled) if (!text.misspelled.includes(t)) text.misspelled.push(t);
      const sz = sizeOf(v);
      const htmlFile = join(out, `${v.name}.html`);
      writeFileSync(htmlFile, buildHtml(v, { base }));
      const url = pathToFileURL(htmlFile).href;
      log('variant', v.name, 'load'); await chrome.load(url, sz.w, sz.h, 2);
      log('qa'); let qa = await chrome.eval('window.__qa()');
      let h = sz.h;
      if (!sz.fixed) {
        h = Math.max(sz.h, qa.height);
        if (h > sz.max) { qa.errors.push(`Tall graphic is ${h}px; LinkedIn crops past about ${sz.max}px. Cut content.`); h = sz.max; }
        await chrome.viewport(sz.w, h, 2);
        const again = await chrome.eval('window.__qa()');
        qa = { ...again, errors: [...new Set([...qa.errors.filter(e => e.startsWith('Tall')), ...again.errors])] };
      }
      const png = join(out, `${v.name}.png`);
      log('shot'); await chrome.shot(png, sz.w, h);
      await chrome.viewport(sz.w, h, 360 / sz.w);
      const preview = join(out, `${v.name}-360.png`);
      await chrome.shot(preview, sz.w, h);
      results.push({ name: v.name, preset: v.preset || 'paper', archetype: v.archetype, w: sz.w, h, png, preview, html: htmlFile,
        fit: qa.fit, min_font_px: qa.minFont, errors: qa.errors, warnings: qa.warnings });
    }
    const caption = spec.caption ? (existsSync(resolve(base, spec.caption)) ? readFileSync(resolve(base, spec.caption), 'utf8') : spec.caption) : null;
    if (results.length > 1 || opts.ref || caption) {
      const sheetHtml = join(out, 'sheet.html');
      writeFileSync(sheetHtml, reviewHtml(results, opts.ref, caption, spec));
      await chrome.load(pathToFileURL(sheetHtml).href, 1800, 1200, 1);
      const dims = await chrome.eval('(async()=>{await Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>i.onload=i.onerror=r)));const r=document.querySelector(".review").getBoundingClientRect();return {w:Math.ceil(r.width),h:Math.ceil(r.height)}})()');
      await chrome.viewport(dims.w, dims.h, 1);
      await chrome.shot(join(out, 'sheet.png'), dims.w, dims.h);
    }
  } finally {
    await chrome.close();
  }

  const rel = p => relative(root, p);
  const report = {
    spec: rel(join(out, 'spec.json')), rendered: new Date().toISOString(),
    text: { errors: text.errors, warnings: text.warnings, misspelled: text.misspelled },
    variants: results.map(r => ({ ...r, png: rel(r.png), preview: rel(r.preview), html: rel(r.html) })),
    sheet: existsSync(join(out, 'sheet.png')) ? rel(join(out, 'sheet.png')) : null,
  };
  report.ok = !report.text.errors.length && results.every(r => !r.errors.length);
  if (logging) logStyle(logFile, spec.slug || basename(specPath, '.json'), spec.preset);
  writeFileSync(join(out, 'qa.json'), JSON.stringify(report, null, 2) + '\n');
  return report;
}

function printReport(r) {
  const line = s => console.log(s);
  line(`${r.ok ? 'PASS' : 'FAIL'}  ${r.spec}`);
  for (const e of r.text.errors) line(`  error   ${e}`);
  for (const w of r.text.warnings) line(`  warn    ${w}`);
  for (const v of r.variants) {
    line(`  ${v.name}: ${v.png}  (${v.w}×${v.h}, text ${Math.round(v.fit * 100)}%, smallest ${v.min_font_px}px)`);
    for (const e of v.errors) line(`    error ${e}`);
    for (const w of v.warnings) line(`    warn  ${w}`);
  }
  if (r.sheet) line(`  sheet: ${r.sheet}`);
}

// ---------------- CLI ----------------
const args = process.argv.slice(2);
const flag = n => { const i = args.indexOf(n); return i >= 0 ? args.splice(i, 2)[1] : undefined; };
const outDir = flag('--out'), ref = flag('--ref'), only = flag('--only');
const cmd = args[0];
if (!cmd) {
  console.log('usage: node render.mjs <spec.json> [--out DIR] [--ref IMAGE] [--only NAME]\n       node render.mjs check <spec.json>\n       node render.mjs templates');
  process.exit(2);
}
if (cmd === 'compare' || cmd === 'shot') {
  // compare OUT.png "Label=path.png" ...   side-by-side grid at feed width, for judging against references
  // shot FILE.html OUT.png W H             screenshot any HTML (prototypes) at 2x
  const chrome = new Chrome(); await chrome.start();
  try {
    if (cmd === 'shot') {
      const [html, out, w, h] = args.slice(1);
      await chrome.load(pathToFileURL(resolve(html)).href, +w, +h, 2);
      await chrome.eval('document.fonts.ready.then(()=>1)');
      await chrome.shot(resolve(out), +w, +h);
      console.log(out);
    } else {
      const out = resolve(args[1]);
      const items = args.slice(2).map(a => { const i = a.indexOf('='); return { label: a.slice(0, i), src: pathToFileURL(resolve(a.slice(i + 1))).href }; });
      const css = readFileSync(join(HERE, 'styles.css'), 'utf8');
      const html = `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body style="margin:0;background:#F2F0EC"><div class="review" style="width:${4 * 440 + 80}px">${items.map(it => `<figure style="width:420px"><figcaption>${it.label.replace(/</g, '&lt;')}</figcaption><img src="${it.src}" style="width:420px"></figure>`).join('')}</div></body></html>`;
      const tmp = join(tmpdir(), `igr-compare-${Date.now()}.html`);
      writeFileSync(tmp, html);
      await chrome.load(pathToFileURL(tmp).href, 4 * 440 + 80, 1000, 1);
      const d = await chrome.eval('(async()=>{await Promise.all([...document.images].map(i=>i.complete?1:new Promise(r=>i.onload=i.onerror=r)));const r=document.querySelector(".review").getBoundingClientRect();return {w:Math.ceil(r.width),h:Math.ceil(r.height)}})()');
      await chrome.viewport(d.w, d.h, 1);
      await chrome.shot(out, d.w, d.h);
      console.log(out);
    }
  } finally { await chrome.close(); }
  process.exit(0);
} else if (cmd === 'check') {
  const spec = JSON.parse(readFileSync(args[1], 'utf8'));
  const t = textChecks(spec);
  t.errors.forEach(e => console.log('error  ' + e)); t.warnings.forEach(w => console.log('warn   ' + w));
  console.log(t.errors.length ? 'FAIL' : 'PASS');
  process.exit(t.errors.length ? 1 : 0);
} else if (cmd === 'templates') {
  // Re-render every template in ../templates/<type>/spec.json into its own folder.
  const dir = join(SKILL, 'templates');
  let ok = true;
  for (const t of readdirSync(dir).filter(d => existsSync(join(dir, d, 'spec.json'))).sort()) {
    const r = await render(join(dir, t, 'spec.json'), { out: join(dir, t) });
    printReport(r); ok &&= r.ok;
  }
  process.exit(ok ? 0 : 1);
} else {
  const r = await render(cmd, { out: outDir, ref, only });
  printReport(r);
  process.exit(r.ok ? 0 : 1);
}
