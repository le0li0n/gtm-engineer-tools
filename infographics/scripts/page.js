// In-page layout + QA. Inlined into every rendered graphic.
// window.__qa() lays out any positioned archetype, fits text, then reports problems.
(function () {
  const W = () => document.querySelector('.sheet').offsetWidth;

  // Cycle archetype: place stage cards around an ellipse inside <main>, then draw arc arrows.
  function layoutCycle() {
    const box = document.querySelector('.cycle');
    if (!box) return;
    const stages = [...box.querySelectorAll('.stage')];
    const cw = box.clientWidth, ch = box.clientHeight;
    const n = stages.length;
    const sw = stages[0] ? stages[0].offsetWidth : 0;
    const sh = Math.max(...stages.map(s => s.offsetHeight), 0);
    const rx = (cw - sw) / 2, ry = (ch - sh) / 2;
    const cx = cw / 2, cy = ch / 2;
    const pts = stages.map((s, i) => {
      const a = -Math.PI / 2 + (2 * Math.PI * i) / n;
      const x = cx + rx * Math.cos(a), y = cy + ry * Math.sin(a);
      s.style.left = (x - s.offsetWidth / 2) + 'px';
      s.style.top = (y - s.offsetHeight / 2) + 'px';
      return { a, x, y };
    });
    const svg = box.querySelector('svg.arcs');
    svg.setAttribute('viewBox', `0 0 ${cw} ${ch}`);
    svg.setAttribute('width', cw); svg.setAttribute('height', ch);
    // Ring through the card centres, then an arrow along it between each pair of stages,
    // clipped so it starts and ends in the visible gap between cards (never under one).
    const bx = box.getBoundingClientRect();
    const GAP = 16;
    const rects = stages.map(s => { const r = s.getBoundingClientRect(); return { l: r.left - bx.left - GAP, r: r.right - bx.left + GAP, t: r.top - bx.top - GAP, b: r.bottom - bx.top + GAP }; });
    const inside = (x, y) => rects.some(q => x > q.l && x < q.r && y > q.t && y < q.b);
    const p = t => [cx + rx * Math.cos(t), cy + ry * Math.sin(t)];
    let paths = `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" class="ring"/>`;
    for (let i = 0; i < n; i++) {
      const a0 = pts[i].a, a1 = i === n - 1 ? pts[0].a + 2 * Math.PI : pts[i + 1].a;
      const N = 160, samples = [];
      for (let k = 0; k <= N; k++) samples.push(p(a0 + ((a1 - a0) * k) / N));
      let s = 0; while (s <= N && inside(...samples[s])) s++;
      let e = N; while (e >= 0 && inside(...samples[e])) e--;
      if (e - s < 4) continue; // cards nearly touch; no room for an arrow
      const seg = samples.slice(s, e + 1);
      paths += `<path d="M ${seg.map(q => q[0].toFixed(1) + ' ' + q[1].toFixed(1)).join(' L ')}" class="arc" marker-end="url(#head)"/>`;
    }
    svg.innerHTML = `<defs><marker id="head" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="head"/></marker></defs>` + paths;
  }

  function cardsCollide() {
    const r = [...document.querySelectorAll('.stage')].map(e => e.getBoundingClientRect());
    for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++) if (rectsOverlap(r[i], r[j])) return true;
    return false;
  }

  // Tree archetype: elbow connectors from each question box to its branches' boxes.
  function layoutTree() {
    const tr = document.querySelector('.tree');
    if (!tr) return;
    const svg = tr.querySelector('svg.tlinks');
    const o = tr.getBoundingClientRect();
    let d = '';
    for (const br of tr.querySelectorAll('.tbranch[data-from]')) {
      const p = document.getElementById(br.dataset.from); if (!p) continue;
      const c = br.querySelector(':scope > .tsub > .tbox'); if (!c) continue;
      const a = p.getBoundingClientRect(), b = c.getBoundingClientRect();
      const x1 = a.left + a.width / 2 - o.left, y1 = a.bottom - o.top;
      const x2 = b.left + b.width / 2 - o.left, y2 = b.top - o.top;
      const ym = y1 + (y2 - y1) * 0.45;
      d += `M ${x1} ${y1} V ${ym} H ${x2} V ${y2} `;
    }
    svg.setAttribute('viewBox', `0 0 ${o.width} ${o.height}`);
    svg.innerHTML = `<path d="${d}"/>`;
  }
  function layoutAll() { layoutCycle(); layoutTree(); }

  // A single word wider than its cell (long uppercase labels) spills sideways.
  function boxSpills() {
    return [...document.querySelectorAll('[data-box]')].some(b => b.scrollWidth > b.clientWidth + 1);
  }

  function mainOverflows() {
    const m = document.querySelector('main');
    return m.scrollHeight > m.clientHeight + 1 || m.scrollWidth > m.clientWidth + 1 || cardsCollide() || boxSpills();
  }

  // Free vertical space left in <main> below its content (cycle fills main by design).
  function spare() {
    const m = document.querySelector('main');
    if (m.querySelector('.cycle')) return 999;
    const kids = [...m.children];
    if (!kids.length) return 0;
    const bottom = Math.max(...kids.map(k => k.getBoundingClientRect().bottom));
    return m.getBoundingClientRect().bottom - bottom;
  }

  function rectsOverlap(a, b) {
    return a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
  }

  window.__qa = async function () {
    await document.fonts.ready;
    const fixed = document.body.dataset.fixed === '1';
    const errors = [], warnings = [];
    let fit = 1;
    const root = document.documentElement;
    root.style.setProperty('--fit', fit);
    layoutAll();
    if (fixed) {
      while (mainOverflows() && fit > 0.8) {
        fit = Math.round((fit - 0.02) * 100) / 100;
        root.style.setProperty('--fit', fit);
        layoutAll();
      }
      if (mainOverflows()) errors.push('Content overflows the canvas even at 80% text size. Cut copy, drop an item, or use size "tall".');
      else if (fit < 1) warnings.push(`Text was shrunk to ${Math.round(fit * 100)}% to fit. Consider trimming copy.`);
      else {
        // Room to spare: grow the body text (up to 130%) so the canvas isn't half empty and
        // phone readers get bigger type. Stop one step before anything overflows.
        const maxFit = document.body.classList.contains("sheet-style") ? 1.6 : 1.3;
        while (fit < maxFit) {
          const next = Math.round((fit + 0.02) * 100) / 100;
          root.style.setProperty('--fit', next); layoutAll();
          if (mainOverflows() || spare() < 24) { root.style.setProperty('--fit', fit); layoutAll(); break; }
          fit = next;
        }
      }
    }

    const sheet = document.querySelector('.sheet');
    const width = W();
    const height = fixed ? sheet.offsetHeight : Math.ceil(sheet.getBoundingClientRect().height);

    // Every text run must sit inside the canvas, and inside its own card if it has one.
    let minFont = 999, minFontText = '', minMeta = 999;
    const walker = document.createTreeWalker(sheet, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    const offCanvas = [];
    while (walker.nextNode()) {
      const t = walker.currentNode; if (t.parentElement.closest("[data-qa-skip]")) continue;
      if (!t.textContent.trim()) continue;
      const el = t.parentElement;
      if (el.closest('svg')) continue;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      // Source lines and the footer are meant to be small (an on-image method note, like
      // Adam Schoenfeld's); they get a lower floor than content text.
      if (el.closest('[data-meta]')) { if (fs < minMeta) minMeta = fs; }
      else if (fs < minFont) { minFont = fs; minFontText = t.textContent.trim().slice(0, 40); }
      range.selectNodeContents(t);
      for (const r of range.getClientRects()) {
        if (r.left < 0 || r.right > width + 0.5 || r.top < 0 || r.bottom > height + 0.5) {
          offCanvas.push(t.textContent.trim().slice(0, 40)); break;
        }
        const card = el.closest('[data-box]');
        if (card) {
          const c = card.getBoundingClientRect();
          if (r.right > c.right + 1 || r.bottom > c.bottom + 1 || r.left < c.left - 1) {
            errors.push(`Text spills out of its box: "${t.textContent.trim().slice(0, 40)}"`); break;
          }
        }
      }
    }
    if (offCanvas.length) errors.push('Text runs off the canvas: ' + offCanvas.slice(0, 3).map(s => `"${s}"`).join(', '));

    // Positioned cards must not collide.
    const boxes = [...sheet.querySelectorAll('.stage')].map(e => ({ e, r: e.getBoundingClientRect() }));
    for (let i = 0; i < boxes.length; i++)
      for (let j = i + 1; j < boxes.length; j++)
        if (rectsOverlap(boxes[i].r, boxes[j].r))
          errors.push(`Cards overlap: "${boxes[i].e.innerText.split('\n')[0]}" and "${boxes[j].e.innerText.split('\n')[0]}"`);

    // Legibility at phone feed width (about 360px across).
    // Dense cheat sheets are built to be saved and zoomed: the headline must read at feed
    // size, body text only has to survive a tap-to-expand. Classic slides stay stricter.
    const dense = document.body.classList.contains('sheet-style');
    const [hardFloor, softFloor] = dense ? [4.8, 5.4] : [6, 7.5];
    const eff = minFont * 360 / width;
    if (eff < hardFloor) errors.push(`Smallest text ("${minFontText}") is ${minFont}px, about ${eff.toFixed(1)}px on a phone. Too small to read even after tapping.`);
    else if (eff < softFloor) warnings.push(`Smallest text ("${minFontText}") is ${minFont}px, about ${eff.toFixed(1)}px on a phone. Check it in the 360px preview.`);
    const t = document.querySelector('.title');
    if (t) { const tf = parseFloat(getComputedStyle(t).fontSize) * 360 / width; if (tf < 15) errors.push(`Headline is about ${tf.toFixed(1)}px on a phone; it has to read at feed size (aim for 18px+). Shorten it.`); }
    if (minMeta * 360 / width < (dense ? 4.2 : 5.5)) errors.push(`Source line or footer text is ${minMeta}px; below about 17px it vanishes on a phone.`);

    // Broken images (logos, wordmark).
    for (const img of sheet.querySelectorAll('img')) if (!img.complete || !img.naturalWidth) errors.push(`Image failed to load: ${img.getAttribute('alt') || img.src.slice(0, 60)}`);

    return { fit, width, height, minFont, errors, warnings };
  };
})();
