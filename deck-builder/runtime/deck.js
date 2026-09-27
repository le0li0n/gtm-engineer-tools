/*
 * deck.js — a tiny runtime for HTML slide decks. No dependencies, no build step.
 *
 *   <script src="deck.js"></script>
 *   <slide-deck width="1920" height="1080">
 *     <section data-label="Title">…</section>
 *     <section data-label="The point">…</section>
 *   </slide-deck>
 *   <script type="application/json" id="speaker-notes">["notes for slide 1", "…"]</script>
 *
 * - Each <section> is one slide, laid out as a width×height box (default 1920×1080).
 *   Slides stay direct light-DOM children, so page CSS like `slide-deck > section { … }` applies.
 * - The deck scales to fit the window, letterboxed. Add `noscale` to render at authored
 *   size with no transform (exporters that read geometry from the DOM set this).
 * - Keys: ←/→ and ↑/↓, PageUp/PageDown, Space (next), Home/End. Mouse: click to advance, click the
 *   left fifth to go back. Touch: tap left/right half. Links and selected text keep their click.
 *   N toggles the speaker-notes overlay. R toggles the thumbnail rail.
 * - Thumbnail rail: a column of numbered thumbnails down the left, one per slide, built as
 *   static clones inside `<slide-deck thumb>` wrappers so the page's own slide CSS styles them.
 *   Click a thumbnail to jump. The chevron tab at the top left shows or hides the rail, and the
 *   choice persists in localStorage. The rail stays out of print, out of `noscale` renders and
 *   out of the deck-builder stage server's captures (which strip this script anyway), and it
 *   starts hidden on windows narrower than 900px. `no-rail` on the element disables it.
 * - #N in the URL (1-based) picks the slide on load and on hashchange; moving updates it.
 * - Posts {slideIndexChanged: n} (0-based) to window.parent on every change.
 * - Print: every slide is its own page at the design size, so Chrome's
 *   --print-to-pdf gives one page per slide.
 * - window.slideDeck = { count, current, go(n), rail: { open, toggle(), show(), hide() } }   (n is 1-based)
 */
(function () {
  "use strict";

  var STYLE_ID = "slide-deck-runtime-style";
  var RAIL_W = 232;          // the column, in CSS px
  var THUMB_W = 184;         // the thumbnail frame inside it
  var RAIL_KEY = "slide-deck-rail";
  var RAIL_MIN_WINDOW = 900; // narrower than this, the rail starts hidden

  function injectStyle(w, h) {
    var old = document.getElementById(STYLE_ID);
    if (old) old.remove();
    var css =
      /* :where() keeps specificity at zero, so any page rule wins. */
      ":where(html, body) { margin: 0; height: 100%; }" +
      ":where(body) { overflow: hidden; background: #000; }" +
      ":where(slide-deck) { display: block; position: fixed; left: 50%; top: 50%;" +
      "  width: " + w + "px; height: " + h + "px; transform-origin: 0 0; overflow: hidden; }" +
      ":where(slide-deck[noscale]) { position: relative; left: 0; top: 0; }" +
      ":where(slide-deck > section) { position: absolute; inset: 0; width: 100%; height: 100%; box-sizing: border-box; }" +
      ":where(slide-deck > section:not([data-active])) { visibility: hidden; }" +
      /* A thumbnail is a second slide-deck element holding one cloned slide, scaled down in place. */
      ":where(slide-deck[thumb]) { position: relative; left: 0; top: 0; pointer-events: none; }" +
      ".slide-deck-notes { position: fixed; left: 0; right: 0; bottom: 0; max-height: 40vh; overflow: auto;" +
      "  margin: 0; padding: 16px 24px; background: rgba(0,0,0,.85); color: #fff; font: 15px/1.5 system-ui, sans-serif;" +
      "  white-space: pre-wrap; z-index: 2147483647; display: none; }" +
      ".slide-deck-notes[data-open] { display: block; }" +
      /* The rail. */
      ".slide-deck-rail { position: fixed; left: 0; top: 0; bottom: 0; width: " + RAIL_W + "px; box-sizing: border-box;" +
      "  padding: 12px 10px 12px 8px; overflow-y: auto; overflow-x: hidden; background: #0a0c14;" +
      "  border-right: 1px solid rgba(255,255,255,.08); z-index: 2147483000; display: none;" +
      "  scrollbar-width: thin; scrollbar-color: rgba(255,255,255,.18) transparent; }" +
      ".slide-deck-rail[data-open] { display: block; }" +
      ".slide-deck-thumb { display: flex; align-items: flex-start; gap: 6px; margin: 0 0 12px; cursor: pointer; user-select: none; }" +
      ".slide-deck-thumb .num { width: 16px; flex: none; padding-top: 2px; text-align: right; font: 500 11px/1.4 system-ui, sans-serif;" +
      "  color: rgba(255,255,255,.5); font-variant-numeric: tabular-nums; }" +
      ".slide-deck-thumb .frame { position: relative; flex: none; width: " + THUMB_W + "px; overflow: hidden; border-radius: 4px;" +
      "  outline: 2px solid transparent; outline-offset: 0; background: #000; transition: outline-color 120ms ease; }" +
      ".slide-deck-thumb:hover .frame { outline-color: rgba(255,255,255,.3); }" +
      ".slide-deck-thumb[data-current] .num { color: #fff; }" +
      ".slide-deck-thumb[data-current] .frame { outline-color: #EC4899; box-shadow: 0 0 14px rgba(236,72,153,.45); }" +
      /* The tab that shows or hides the rail. */
      ".slide-deck-rail-toggle { position: fixed; top: 10px; left: 8px; width: 30px; height: 30px; padding: 0; border: 1px solid rgba(255,255,255,.14);" +
      "  border-radius: 6px; background: rgba(10,12,20,.85); color: rgba(255,255,255,.75); font: 18px/28px system-ui, sans-serif;" +
      "  text-align: center; cursor: pointer; z-index: 2147483001; opacity: .55; transition: opacity 150ms ease, left 200ms cubic-bezier(.3,.7,.4,1); }" +
      ".slide-deck-rail-toggle:hover { opacity: 1; }" +
      ".slide-deck-rail-toggle[data-open] { left: " + (RAIL_W + 8) + "px; }" +
      ".slide-deck-rail-toggle[hidden] { display: none; }" +
      "@page { size: " + w + "px " + h + "px; margin: 0; }" +
      "@media print {" +
      "  html, body { height: auto !important; overflow: visible !important; }" +
      "  slide-deck { position: static !important; transform: none !important; width: " + w + "px !important;" +
      "    height: auto !important; overflow: visible !important; }" +
      "  slide-deck > section { position: relative !important; inset: auto !important; visibility: visible !important;" +
      "    width: " + w + "px !important; height: " + h + "px !important; overflow: hidden !important;" +
      "    break-after: page; page-break-after: always; }" +
      "  slide-deck > section:last-of-type { break-after: auto; page-break-after: auto; }" +
      "  .slide-deck-notes, .slide-deck-rail, .slide-deck-rail-toggle { display: none !important; }" +
      "}";
    var s = document.createElement("style");
    s.id = STYLE_ID;
    s.textContent = css;
    document.head.insertBefore(s, document.head.firstChild);
  }

  function readNotes() {
    var el = document.getElementById("speaker-notes");
    if (!el) return [];
    try {
      var v = JSON.parse(el.textContent);
      return Array.isArray(v) ? v : [];
    } catch (e) {
      return [];
    }
  }

  function hashSlide() {
    var m = /^#(\d+)$/.exec(location.hash || "");
    return m ? parseInt(m[1], 10) : null;
  }

  function readRailPref() {
    try { return localStorage.getItem(RAIL_KEY); } catch (e) { return null; }
  }

  function writeRailPref(v) {
    try { localStorage.setItem(RAIL_KEY, v); } catch (e) { /* private window: the choice lasts the session */ }
  }

  /* A static copy of one slide for the rail: no ids (they'd collide), no scripts, no live media. */
  function cloneForThumb(slide) {
    var c = slide.cloneNode(true);
    c.removeAttribute("id");
    c.setAttribute("data-active", "");
    var all = c.querySelectorAll("[id]");
    for (var i = 0; i < all.length; i++) all[i].removeAttribute("id");
    var dead = c.querySelectorAll("script, iframe, audio, video, object, embed");
    for (var j = 0; j < dead.length; j++) dead[j].remove();
    var imgs = c.querySelectorAll("img");
    for (var k = 0; k < imgs.length; k++) { imgs[k].loading = "lazy"; imgs[k].decoding = "async"; }
    return c;
  }

  class SlideDeck extends HTMLElement {
    connectedCallback() {
      if (this._connected) return;
      this._connected = true;
      // Thumbnail wrappers are inert: they exist so the page's slide CSS applies to the clone.
      if (this.hasAttribute("thumb")) return;
      // The element upgrades as soon as the parser meets the tag, before its children exist.
      // Set up once the document has been parsed, so every <section> is there.
      var self = this;
      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", function () { self.setup(); }, { once: true });
      } else {
        this.setup();
      }
    }

    setup() {
      this.designW = parseInt(this.getAttribute("width"), 10) || 1920;
      this.designH = parseInt(this.getAttribute("height"), 10) || 1080;
      injectStyle(this.designW, this.designH);

      this.slides = Array.prototype.filter.call(this.children, function (c) {
        return c.tagName === "SECTION";
      });
      this.notes = readNotes();
      this.notesEl = document.createElement("pre");
      this.notesEl.className = "slide-deck-notes";
      document.body.appendChild(this.notesEl);

      this.index = -1;
      var self = this;
      window.slideDeck = {
        get count() { return self.slides.length; },
        get current() { return self.index + 1; },
        go: function (n) { self.go(n); },
        rail: {
          get open() { return self.railOpen; },
          toggle: function () { self.setRail(!self.railOpen); },
          show: function () { self.setRail(true); },
          hide: function () { self.setRail(false); },
        },
      };

      this._onResize = function () { self.fit(); };
      this._onKey = function (e) { self.key(e); };
      this._onHash = function () { var n = hashSlide(); if (n) self.show(n - 1, false); };
      this._onTap = function (e) { self.tap(e); };
      window.addEventListener("resize", this._onResize);
      document.addEventListener("keydown", this._onKey);
      window.addEventListener("hashchange", this._onHash);
      this.addEventListener("click", this._onTap);

      this.buildRail();
      this.fit();
      var start = hashSlide();
      this.show(start ? start - 1 : 0, false);
    }

    disconnectedCallback() {
      window.removeEventListener("resize", this._onResize);
      document.removeEventListener("keydown", this._onKey);
      window.removeEventListener("hashchange", this._onHash);
    }

    /* The rail is skipped where it would land in a capture: noscale renders, automated browsers, `no-rail`. */
    railAllowed() {
      if (this.hasAttribute("noscale") || this.hasAttribute("no-rail")) return false;
      if (/[?&]rail\b/.test(location.search)) return true;   // ?rail forces it, for testing the rail itself headlessly
      if (document.getElementById("__stage_pin")) return false; // the deck-builder stage server pins one slide for capture
      if (navigator.webdriver) return false;
      return true;
    }

    buildRail() {
      this.railOpen = false;
      if (!this.railAllowed()) return;
      var self = this;
      var rail = document.createElement("nav");
      rail.className = "slide-deck-rail";
      rail.setAttribute("aria-label", "Slides");
      var k = THUMB_W / this.designW;
      this.thumbs = this.slides.map(function (slide, i) {
        var t = document.createElement("div");
        t.className = "slide-deck-thumb";
        t.title = slide.getAttribute("data-label") || ("Slide " + (i + 1));
        var num = document.createElement("span");
        num.className = "num";
        num.textContent = String(i + 1);
        var frame = document.createElement("div");
        frame.className = "frame";
        frame.style.height = Math.round(self.designH * k) + "px";
        var wrap = document.createElement("slide-deck");
        wrap.setAttribute("thumb", "");
        wrap.style.width = self.designW + "px";
        wrap.style.height = self.designH + "px";
        wrap.style.transformOrigin = "0 0";
        wrap.style.transform = "scale(" + k + ")";
        wrap.appendChild(cloneForThumb(slide));
        frame.appendChild(wrap);
        t.appendChild(num);
        t.appendChild(frame);
        t.addEventListener("click", function () { self.show(i, true); });
        rail.appendChild(t);
        return t;
      });
      var toggle = document.createElement("button");
      toggle.className = "slide-deck-rail-toggle";
      toggle.type = "button";
      toggle.setAttribute("aria-label", "Show or hide the slide list");
      toggle.addEventListener("click", function () { self.setRail(!self.railOpen); });
      document.body.appendChild(rail);
      document.body.appendChild(toggle);
      this.railEl = rail;
      this.railToggle = toggle;
      var pref = readRailPref();
      var open = pref ? pref === "open" : window.innerWidth >= RAIL_MIN_WINDOW;
      this.setRail(open, true);
    }

    setRail(open, silent) {
      if (!this.railEl) return;
      this.railOpen = !!open;
      if (this.railOpen) { this.railEl.setAttribute("data-open", ""); this.railToggle.setAttribute("data-open", ""); }
      else { this.railEl.removeAttribute("data-open"); this.railToggle.removeAttribute("data-open"); }
      this.railToggle.textContent = this.railOpen ? "‹" : "›";
      this.railToggle.title = this.railOpen ? "Hide the slide list (R)" : "Show the slide list (R)";
      if (!silent) writeRailPref(this.railOpen ? "open" : "closed");
      this.fit();
      if (this.railOpen && this.index >= 0) this.scrollRailTo(this.index);
    }

    scrollRailTo(i) {
      var t = this.thumbs && this.thumbs[i];
      if (t && t.scrollIntoView) t.scrollIntoView({ block: "nearest" });
    }

    fit() {
      if (this.hasAttribute("noscale")) {
        this.style.transform = "none";
        return;
      }
      var left = this.railOpen ? RAIL_W : 0;
      var avail = window.innerWidth - left;
      var k = Math.min(avail / this.designW, window.innerHeight / this.designH);
      this.style.left = this.railOpen ? (left + avail / 2) + "px" : "";
      this.style.transform =
        "scale(" + k + ") translate(" + (-this.designW / 2) + "px, " + (-this.designH / 2) + "px)";
    }

    show(i, updateHash) {
      if (!this.slides.length) return;
      i = Math.max(0, Math.min(this.slides.length - 1, i));
      if (i === this.index) return;
      if (this.index >= 0) {
        this.slides[this.index].removeAttribute("data-active");
        if (this.thumbs) this.thumbs[this.index].removeAttribute("data-current");
      }
      this.index = i;
      this.slides[i].setAttribute("data-active", "");
      if (this.thumbs) {
        this.thumbs[i].setAttribute("data-current", "");
        if (this.railOpen) this.scrollRailTo(i);
      }
      this.notesEl.textContent = this.notes[i] || "";
      if (updateHash !== false && location.hash !== "#" + (i + 1)) {
        history.replaceState(null, "", "#" + (i + 1));
      }
      try {
        if (window.parent && window.parent !== window) window.parent.postMessage({ slideIndexChanged: i }, "*");
      } catch (e) { /* cross-origin parent: nothing to tell */ }
      this.dispatchEvent(new CustomEvent("slidechange", { detail: { index: i, slide: i + 1 } }));
    }

    go(n) { this.show(n - 1, true); }
    next() { this.show(this.index + 1, true); }
    prev() { this.show(this.index - 1, true); }

    key(e) {
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      var t = e.target;
      if (t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName))) return;
      switch (e.key) {
        case "ArrowRight": case "ArrowDown": case "PageDown": case " ": case "Spacebar":
          this.next(); break;
        case "ArrowLeft": case "ArrowUp": case "PageUp":
          this.prev(); break;
        case "Home":
          this.show(0, true); break;
        case "End":
          this.show(this.slides.length - 1, true); break;
        case "n": case "N":
          if (this.notesEl.hasAttribute("data-open")) this.notesEl.removeAttribute("data-open");
          else this.notesEl.setAttribute("data-open", "");
          break;
        case "r": case "R":
          this.setRail(!this.railOpen); break;
        default:
          return;
      }
      e.preventDefault();
    }

    tap(e) {
      // Links, buttons and form controls inside a slide keep their click.
      if (e.target.closest && e.target.closest("a, button, input, textarea, select, label, [data-no-nav]")) return;
      // A click that ends a text selection is a copy, not a navigation.
      var sel = window.getSelection ? window.getSelection() : null;
      if (sel && sel.type === "Range" && String(sel).length) return;
      // Touch: left half back, right half forward. Mouse: the left fifth of the stage goes back,
      // everything else goes forward, so a presenter can click anywhere to advance.
      var coarse = matchMedia("(pointer: coarse)").matches;
      var left = this.railOpen ? RAIL_W : 0;
      var back = (e.clientX - left) < (window.innerWidth - left) / (coarse ? 2 : 5);
      if (back) this.prev();
      else this.next();
    }
  }

  if (!customElements.get("slide-deck")) customElements.define("slide-deck", SlideDeck);
})();
