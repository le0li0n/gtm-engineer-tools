// Template-type builders for the dense "sheet" styles: stack, workflow, resources, versus,
// levels, cheatsheet, bento. Every word comes from the spec. Missing logos and avatars get
// generated monogram placeholders so templates render complete before real assets exist.
import { readFileSync } from 'node:fs';
import { resolve, extname } from 'node:path';
import { icon } from './icons.mjs';

const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
export function inl(s) {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[\[(.+?)\]\]/g, '<span class="hl">$1</span>')
    .replace(/`(.+?)`/g, '<span class="code">$1</span>')
    .replace(/\n/g, '<br>');
}

const MONO = ['#F25C2A', '#1E1EF6', '#12A37F', '#8B5CF6', '#E8A300', '#FF4D8D', '#0E7C86', '#111111', '#E5322D', '#5AA9FF'];
function hash(s) { let h = 0; for (const c of String(s)) h = (h * 31 + c.charCodeAt(0)) >>> 0; return h; }
function initials(name) {
  const w = String(name).replace(/[^A-Za-z0-9 ]/g, ' ').trim().split(/\s+/).filter(Boolean);
  return ((w[0]?.[0] || '?') + (w.length > 1 ? w[w.length - 1][0] : (w[0]?.[1] || ''))).toUpperCase();
}
function svgUri(svg) { return 'data:image/svg+xml;base64,' + Buffer.from(svg).toString('base64'); }
export function monoLogo(name) {
  const c = MONO[hash(name) % MONO.length];
  return svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" rx="14" fill="${c}"/><text x="32" y="41" font-family="Helvetica Neue,Arial" font-weight="800" font-size="26" fill="#fff" text-anchor="middle">${esc(initials(name))}</text></svg>`);
}
export function monoAvatar(name) {
  const c = MONO[(hash(name) + 3) % MONO.length];
  return svgUri(`<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"><circle cx="48" cy="48" r="48" fill="${c}"/><circle cx="48" cy="38" r="17" fill="rgba(255,255,255,.28)"/><path d="M16 88c6-18 18-26 32-26s26 8 32 26" fill="rgba(255,255,255,.28)"/><text x="48" y="58" font-family="Helvetica Neue,Arial" font-weight="800" font-size="30" fill="#fff" text-anchor="middle">${esc(initials(name))}</text></svg>`);
}
function fileUri(p, base) {
  const f = resolve(base, p);
  const mime = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.webp': 'image/webp' }[extname(f).toLowerCase()];
  return `data:${mime};base64,${readFileSync(f).toString('base64')}`;
}
const logoSrc = (t, base) => t.logo ? fileUri(t.logo, base) : monoLogo(t.name);
export const avatarSrc = (p, base) => p.avatar ? fileUri(p.avatar, base) : monoAvatar(p.name);
const K = i => `style="--k: var(--c${(i % 5) + 1})"`;
const chip = (t, base, cls = '') => `<span class="chip ${cls}"><img src="${logoSrc(typeof t === 'string' ? { name: t } : t, base)}" alt="">${inl(typeof t === 'string' ? t : t.name)}</span>`;
const plainChip = (s, cls = '') => `<span class="chip ${cls}" style="padding:7px 12px">${inl(s)}</span>`;
const flowChips = (items, base) => items.map((s, i) => (i ? '<div class="arrow">↓</div>' : '') +
  (i === items.length - 1 ? plainChip(s, 'out') : (typeof s === 'object' || /^[A-Z]/.test(s) && !/\s/.test(s) ? chip(s, base) : plainChip(s)))).join('');

// One-row flow: input → tool → output, with the output filled in the section color.
const isTool = s => typeof s === 'object' || (/^[A-Z]/.test(s) && !/\s/.test(s));
const hflow = (items, base) => items.map((s, i) => (i ? '<span class="arrow">→</span>' : '') +
  (i === items.length - 1 ? plainChip(s, 'out') : isTool(s) ? chip(s, base) : plainChip(s, 'in'))).join('');

// ---------- stack: tools grouped by job ----------
function stack(d, { base }) {
  return `<div class="stack">` + (d.groups || []).map((g, i) =>
    `<div class="grp scard${g.featured ? ' featured' : ''}${g.wide ? ' wide' : ''}" ${K(i)} data-box>
      <div class="gh"><span class="dot"></span><h3>${inl(g.name)}</h3>${g.price ? `<span class="n">${esc(g.price)}</span>` : ''}</div>
      ${g.note ? `<p class="gd">${inl(g.note)}</p>` : ''}
      <div class="chips">${(g.tools || []).map(t => chip(t, base)).join('')}</div></div>`).join('') + `</div>`;
}

// ---------- workflow: numbered steps, each with tools and a mini in→out flow ----------
function workflow(d, { base }) {
  return `<div class="flow">` + (d.steps || []).map((s, i) =>
    `<div class="st" ${K(i)}>
      <div class="rail"><span class="badge">${i + 1}</span><i></i></div>
      <div class="body scard" data-box><div class="top"><div><h3>${inl(s.title)}</h3>${s.body ? `<p>${inl(s.body)}</p>` : ''}</div>${s.tools ? `<div class="chips">${s.tools.map(t => chip(t, base)).join('')}</div>` : ''}</div>
      ${s.flow ? `<div class="hflow">${hflow(s.flow, base)}</div>` : ''}</div></div>`).join('') + `</div>`;
}

// ---------- resources: people / newsletters / podcasts to follow ----------
function resources(d, { base }) {
  return `<div class="res">` + (d.groups || []).map((g, i) =>
    `<div class="rg" ${K(i)}><h3><span class="pill">${esc(g.kind || g.name)}</span>${g.kind ? inl(g.name) : ''}</h3>
      <div class="items">${(g.items || []).map(p =>
        `<div class="it scard" data-box><img class="av" src="${avatarSrc(p, base)}" alt=""><div><div class="nm">${inl(p.name)}</div>${p.handle ? `<div class="hd">${esc(p.handle)}</div>` : ''}${p.why ? `<div class="wy">${inl(p.why)}</div>` : ''}</div></div>`).join('')}</div></div>`).join('') + `</div>`;
}

// ---------- versus: mistakes vs fixes, good vs bad ----------
function versus(d) {
  const [lt, rt] = [d.left_title || 'Mistake', d.right_title || 'Do this instead'];
  return `<div class="vs"><div class="vh"><span></span><div class="b bad">✕ ${inl(lt)}</div><div class="b good">✓ ${inl(rt)}</div><div class="x">VS</div></div>` +
    (d.pairs || []).map((p, i) => `<div class="row"><div class="i">${i + 1}</div><div class="l" data-box><span>${inl(p[0])}</span></div><div class="r" data-box><span>${inl(p[1])}</span></div></div>`).join('') + `</div>`;
}

// ---------- levels: 1-2-3 progression, each with labeled rows and a mini flow ----------
function levels(d, { base }) {
  return `<div class="lv">` + (d.levels || []).map((l, i) =>
    `<div class="band scard" ${K(i)} data-box>
      <div class="head"><div class="big">${String(i + 1).padStart(2, '0')}</div>${l.tag ? `<span class="pill">${esc(l.tag)}</span>` : ''}<h3>${inl(l.name)}</h3>${l.summary ? `<p>${inl(l.summary)}</p>` : ''}</div>
      <div class="rows">${(l.rows || []).map(r => `<div class="rw"><span class="lab">${esc(r.label)}</span>${inl(r.text)}</div>`).join('')}</div>
      <div class="side">${flowChips(l.flow || [], base)}</div></div>`).join('') + `</div>`;
}

// ---------- cheatsheet: 8-20 numbered tips in columns ----------
function cheatsheet(d) {
  const cols = d.columns || 2;
  return `<div class="cs" style="grid-template-columns: repeat(${cols}, 1fr)">` + (d.items || []).map((it, i) =>
    `<div class="ci scard" ${K(i)} data-box><span class="badge">${i + 1}</span><div><h4>${inl(it.title)}</h4>${it.body ? `<p>${inl(it.body)}</p>` : ''}</div></div>`).join('') + `</div>`;
}

// ---------- bento: mixed-size cards, "everything that changed" ----------
function bento(d) {
  return `<div class="bento">` + (d.cards || []).map((c, i) =>
    `<div class="bc scard${c.wide ? ' wide' : ''}" ${K(i)} data-box><span class="pill">${esc(c.tag || '')}</span>${c.big ? `<div class="big">${esc(c.big)}</div>` : ''}<h3>${inl(c.title)}</h3>${c.points ? `<ul>${c.points.map(p => `<li>${inl(p)}</li>`).join('')}</ul>` : ''}</div>`).join('') + `</div>`;
}

// ---------- layers: a stacked architecture that widens toward its foundation ----------
// Top-to-bottom order; the last layer is the widest base. Each layer: icon, name, one sentence, logos.
function layers(d, { base }) {
  const L = d.layers || [];
  const n = L.length;
  const minW = d.top_width ?? 58, step = n > 1 ? (100 - minW) / (n - 1) : 0;
  const logos = ts => !(ts || []).length ? '' : d.labels ? `<div class="lgs chips">${ts.map(t => chip(t, base)).join('')}</div>` : `<div class="lgs">${ts.map(t => `<span class="lg"><img src="${logoSrc(typeof t === 'string' ? { name: t } : t, base)}" alt=""></span>`).join('')}</div>`;
  let h = `<div class="layers">` + L.map((l, i) =>
    `<div class="slab" style="--sw:${minW + step * i}%; --k: var(--c${((d.reverse_colors ? n - 1 - i : i) % 5) + 1})">
      <div class="lid"></div>
      <div class="face scard" data-box>
        <div class="lh">${l.icon ? `<span class="icb">${icon(l.icon)}</span>` : ''}<h3>${inl(l.name)}</h3>${l.tag ? `<span class="pill">${esc(l.tag)}</span>` : ''}</div>
        ${l.body ? `<p>${inl(l.body)}</p>` : ''}${logos(l.tools)}
      </div></div>`).join('') + `</div>`;
  const all = d.strip === false ? [] : (d.strip?.tools || [...new Map(L.flatMap(l => l.tools || []).map(t => [typeof t === 'string' ? t : t.name, t])).values()]);
  if (all.length) h += `<div class="strip scard" data-box><div class="sh">${inl(d.strip?.title || 'The stack behind it')}<span class="pill">${all.length} tools</span></div>
    <div class="st-tools">${all.map(t => { const o = typeof t === 'string' ? { name: t } : t; return `<div class="stt"><span class="lg big"><img src="${logoSrc(o, base)}" alt=""></span><span data-meta>${esc(o.name)}</span></div>`; }).join('')}</div></div>`;
  return h;
}

// ---------- tree: a branching decision diagram ----------
// node = { q: "question" , branches: [{ label: "Yes", node }, ...] }  or  { outcome: "...", tone: "good|bad|neutral", note? }
function tree(d) {
  let id = 0;
  const node = (n, depth) => {
    const me = `t${id++}`;
    if (n.outcome) {
      return `<div class="tsub"><div class="tbox out ${n.tone || 'neutral'}" id="${me}" data-box>${n.icon ? icon(n.icon) : ''}<div><b>${inl(n.outcome)}</b>${n.note ? `<span>${inl(n.note)}</span>` : ''}</div></div></div>`;
    }
    const kids = (n.branches || []).map(b => {
      const sub = node(b.node, depth + 1);
      return `<div class="tbranch" data-from="${me}"><span class="tlab">${esc(b.label)}</span>${sub}</div>`;
    }).join('');
    return `<div class="tsub"><div class="tbox q d${depth}" id="${me}" data-box>${n.icon ? icon(n.icon) : ''}<b>${inl(n.q)}</b></div><div class="tkids">${kids}</div></div>`;
  };
  return `<div class="tree"><svg class="tlinks"></svg>${node(d.root || {}, 0)}</div>`;
}

// ---------- events: where to be this season ----------
function events(d, { base }) {
  return `<div class="evs">` + (d.events || []).map((e, i) =>
    `<div class="ev scard" ${K(i)} data-box>
      <div class="edate"><span class="m">${esc(e.month || '')}</span><span class="dd">${esc(e.days || '')}</span></div>
      <div class="emid"><div class="en">${e.logo ? `<img class="elg" src="${logoSrc({ name: e.name, logo: e.logo }, base)}" alt="">` : ''}<h3>${inl(e.name)}</h3></div>
        <div class="ewhere">${icon('pin')}<span>${inl(e.city || '')}</span>${e.host ? `<span class="dot2">·</span><span>${inl(e.host)}</span>` : ''}</div>
        ${e.why ? `<p>${inl(e.why)}</p>` : ''}</div>
      <div class="eside">${e.tag ? `<span class="pill">${esc(e.tag)}</span>` : ''}${e.price ? `<span class="price">${esc(e.price)}</span>` : ''}</div></div>`).join('') + `</div>`;
}

// ---------- case: a real campaign, broken down ----------
function caseStudy(d) {
  const hero = (d.results || []).map((r, i) => `<div class="hr scard" ${K(i)} data-box><div class="hv">${esc(r.value)}</div><div class="hl2">${inl(r.label)}</div></div>`).join('');
  const setup = (d.setup || []).map((s, i) => `<div class="su" ${K(i + 1)}>${icon(s.icon || 'target')}<div><span class="lab">${esc(s.label)}</span><b>${inl(s.value)}</b></div></div>`).join('');
  const steps = (d.steps || []).map((s, i) => `<div class="cst" ${K(i)} data-box><span class="badge">${i + 1}</span><h4>${inl(s.title)}</h4>${s.body ? `<p>${inl(s.body)}</p>` : ''}</div>`).join('');
  return `<div class="case">
    <div class="heros" style="grid-template-columns: repeat(${(d.results || []).length || 1}, 1fr)">${hero}</div>
    ${setup ? `<div class="setup scard" data-box>${setup}</div>` : ''}
    <div class="csteps" style="grid-template-columns: repeat(${(d.steps || []).length || 1}, 1fr)"><i class="cline"></i>${steps}</div>
    ${d.lesson ? `<div class="lesson" data-box>${icon('bulb')}<div><span class="lab">${esc(d.lesson_label || 'What we learned')}</span><p>${inl(d.lesson)}</p></div></div>` : ''}
  </div>`;
}

export const SHEET_BUILDERS = { stack, workflow, resources, versus, levels, cheatsheet, bento, layers, tree, events, case: caseStudy };
export const SHEET_PRESETS = ['pop', 'midnight', 'electric', 'citrus', 'ocean'];
