#!/usr/bin/env python3
"""The GTM library: offerings, ICPs, personas, use cases, references, proof points.

One markdown file per item under <library>/<kind>/, structured fields in the
frontmatter, prose in the body. Items link to each other by id (the filename slug).
The spec is references/schema.md in this plugin.

The repo is the git toplevel of the working directory (or $GTM_LIBRARY_ROOT). Paths come
from .gtmlibrary.json at its root; see templates/gtmlibrary.json. Defaults:
library "gtm-library", render_to "gtm-library/ICP.md", competitors_dir none.

Usage:
  python3 gtm_library.py lint [--stale]
  python3 lib/gtm_library.py show <id>                       # one item, resolved links
  python3 lib/gtm_library.py match --title T [--employees N|"51-200 employees"] [--industry I] [--revenue 10M] [--funding "Series A"] [--icp ID] [--offering ID]
  python3 lib/gtm_library.py questions [--offering ID] [--icp ID] [--persona ID] [--json]
  python3 lib/gtm_library.py classify CSV [--offering ID] [--title-col Title] [--size-col "Employee Size"] [--industry-col Industry] [--revenue-col "Annual Revenues"]
  python3 lib/gtm_library.py export                          # whole library as JSON
  python3 gtm_library.py render [--out PATH]

Standard library only. The frontmatter is a restricted YAML subset (see parse_frontmatter);
anything outside it is an error, not a guess.
"""
import argparse, collections, csv, json, os, re, sys
from datetime import date

def _find_root():
    if os.environ.get("GTM_LIBRARY_ROOT"):
        return os.path.abspath(os.environ["GTM_LIBRARY_ROOT"])
    d = os.getcwd()
    while True:
        if os.path.exists(os.path.join(d, ".gtmlibrary.json")) or os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.getcwd()
        d = parent


def _config(root):
    path = os.path.join(root, ".gtmlibrary.json")
    cfg = {"library": "gtm-library", "render_to": None, "competitors_dir": None, "cadence_days": 90}
    if os.path.exists(path):
        try:
            cfg.update(json.load(open(path, encoding="utf-8")))
        except ValueError as e:
            raise SystemExit(f".gtmlibrary.json: {e}")
    cfg["render_to"] = cfg["render_to"] or os.path.join(cfg["library"], "ICP.md")
    cfg["dashboard_to"] = cfg.get("dashboard_to") or os.path.join(cfg["library"], "dashboard.html")
    return cfg


ROOT = _find_root()
CONFIG = _config(ROOT)
LIB = os.path.join(ROOT, CONFIG["library"])
KINDS = {  # folder -> type
    "offerings": "offering", "icps": "icp", "personas": "persona",
    "use-cases": "use-case", "references": "reference", "proof-points": "proof-point",
    "objections": "objection", "alternatives": "alternative", "triggers": "trigger",
    "competitors": "competitor", "angles": "angle",
}
REQUIRED = ["id", "type", "name", "status", "last_confirmed"]
STATUSES = {"active", "planned", "retired"}
# Fields that hold ids of other items, and the type each must resolve to.
LINKS = {"offerings": "offering", "icps": "icp", "personas": "persona",
         "use_cases": "use-case", "references": "reference", "proof_points": "proof-point",
         "objections": "objection", "alternatives": "alternative", "triggers": "trigger",
         "competitors": "competitor", "angles": "angle", "primary_offering": "offering"}
# Pairs that should point at each other.
RECIPROCAL = [("icp", "personas", "persona", "icps"), ("icp", "offerings", "offering", "icps"),
              ("icp", "triggers", "trigger", "icps")]
DEFAULT_CADENCE_DAYS = int(CONFIG["cadence_days"])
OFFERING_KINDS = CONFIG.get("offering_kinds") or ["product", "service", "solution", "sponsorship"]
MOTIONS = CONFIG.get("motions") or ["new", "renewal", "expansion", "win-back"]
MOTION_TYPES = {"angle", "objection", "trigger"}
# Body headings each type must carry (lint warns), and for offerings, per kind. Matched
# case-insensitively at any heading level; `export` returns every heading's content by name.
HEADINGS = {
    "objection": ["Underlying concern", "Misconceptions", "What to probe", "Reframe"],
    "alternative": ["Where it works", "Where it breaks", "Who champions it", "Hidden costs", "Why ours is better"],
    "trigger": ["Why now", "Who feels it", "Cost of waiting", "How we help"],
    "competitor": ["How they position", "Why we win", "Why we lose"],
    "angle": ["Approach", "Key messages", "Value props"],
}
OFFERING_HEADINGS = {
    "service": ["Deliverables", "Challenges addressed", "Why us"],
    "sponsorship": ["Package", "Challenges addressed", "Why us"],
    "product": ["Challenges addressed", "Distinct capabilities", "Why us"],
    "solution": ["Challenges addressed", "Key components", "Why us"],
}
for _t, _hs in (CONFIG.get("headings") or {}).items():
    (OFFERING_HEADINGS if _t in OFFERING_HEADINGS else HEADINGS)[_t] = _hs


# ---------------------------------------------------------------- frontmatter

def _scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] == "'":
        return s[1:-1].replace("''", "'")
    if len(s) >= 2 and s[0] == s[-1] == '"':
        return json.loads(s)
    if s in ("null", "~", ""):
        return None
    if s in ("true", "false"):
        return s == "true"
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    return s


def _flow_list(s, where):
    inner = s.strip()[1:-1]
    out, buf, q = [], "", None
    for ch in inner:
        if q:
            buf += ch
            if ch == q:
                q = None
        elif ch in "'\"":
            q = ch; buf += ch
        elif ch == ",":
            out.append(buf); buf = ""
        else:
            buf += ch
    if q:
        raise ValueError(f"{where}: unterminated quote in list")
    if buf.strip():
        out.append(buf)
    return [_scalar(x) for x in out]


_KEY = re.compile(r"^('[^']*'|\"[^\"]*\"|[^:'\"\s][^:'\"]*?):(?:\s+(.*))?$")
# A list item opens a map only with a bare lowercase key (`- q: …`), so prose like
# `- Hiring: who owns it?` stays a string.
_ITEM_KEY = re.compile(r"^[a-z_][a-z0-9_]*:(\s|$)")


def parse_frontmatter(text, where="?"):
    """Restricted YAML: `key: scalar`, `key: [a, b]`, block lists (`- x`), lists of maps
    (`- q: …` with the map's other keys indented under it) and nested maps by indentation.
    Full-line `#` comments. Quote anything containing `: `, ` #` or a leading `[`."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        raise ValueError(f"{where}: frontmatter never closes")
    body = text[end + 4:].lstrip("\n")
    lines = []
    for n, raw in enumerate(text[4:end].split("\n"), 2):
        if raw.strip() and not raw.lstrip().startswith("#"):
            if "\t" in raw[:len(raw) - len(raw.lstrip())]:
                raise ValueError(f"{where}:{n}: tab indentation")
            lines.append((n, len(raw) - len(raw.lstrip(" ")), raw.strip()))
    pos = 0

    def block(ind):
        nonlocal pos
        is_list = lines[pos][2].startswith("-")
        out = [] if is_list else {}
        while pos < len(lines):
            n, i, line = lines[pos]
            if i < ind:
                break
            if i > ind:
                raise ValueError(f"{where}:{n}: unexpected indentation")
            if is_list:
                if not line.startswith("- "):
                    raise ValueError(f"{where}:{n}: expected a `- ` list item")
                if _ITEM_KEY.match(line[2:]):
                    # A map as a list item: `- q: …` then its other keys indented two past the dash.
                    lines[pos] = (n, ind + 2, line[2:])
                    out.append(block(ind + 2))
                    continue
                out.append(_scalar(line[2:])); pos += 1
                continue
            m = _KEY.match(line)
            if not m:
                raise ValueError(f"{where}:{n}: can't parse {line!r}")
            key, val = str(_scalar(m.group(1))), (m.group(2) or "").strip()
            pos += 1
            if not val:
                nxt = lines[pos] if pos < len(lines) else None
                out[key] = block(nxt[1]) if nxt and nxt[1] > ind else None
            elif val.startswith("["):
                if not val.endswith("]"):
                    raise ValueError(f"{where}:{n}: a flow list must close on its own line")
                out[key] = _flow_list(val, f"{where}:{n}")
            else:
                out[key] = _scalar(val)
        return out

    root = block(0) if lines else {}
    if not isinstance(root, dict):
        raise ValueError(f"{where}: frontmatter must be a map")
    return root, body


# ---------------------------------------------------------------- load

def load(lib=LIB):
    items, errors = {}, []
    for folder, typ in KINDS.items():
        d = os.path.join(lib, folder)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".md") or f.startswith(("_", "CLAUDE", "README")):
                continue
            path = os.path.join(d, f)
            try:
                fm, body = parse_frontmatter(open(path, encoding="utf-8").read(), os.path.relpath(path, ROOT))
            except ValueError as e:
                errors.append(str(e)); continue
            fm["_path"] = os.path.relpath(path, ROOT)
            fm["_body"] = body
            fm["_folder_type"] = typ
            fm["_file_id"] = f[:-3]
            items[fm.get("id") or f[:-3]] = fm
    return items, errors


def as_list(v):
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def serves(item, offering):
    """An element with no `offerings` applies whatever is being sold; one that lists offerings
    applies only when selling one of them. No offering given means no filter."""
    scoped = as_list(item.get("offerings"))
    return not offering or not scoped or offering in scoped


def in_motion(item, motion):
    """Same rule for motions: no `motion` field means every motion."""
    m = as_list(item.get("motion"))
    return not motion or not m or motion in m


def sections(body):
    """The body's headings and what sits under each, keyed by heading text. The H1 title is
    skipped; a deeper heading ends the one above it."""
    out, cur = {}, None
    for line in body.splitlines():
        m = re.match(r"^(#{2,6})\s+(.+?)\s*#*\s*$", line)
        if m:
            cur = m.group(2).strip()
            out[cur] = []
        elif cur is not None:
            out[cur].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def section_for(sec, name, offering=None):
    """A section's text for an offering: `## Name (offering)` when the item has one for it,
    else the plain `## Name`. `sec` is sections() with lowercased keys."""
    if offering and sec.get(f"{name} ({offering})".lower()):
        return sec[f"{name} ({offering})".lower()]
    return sec.get(name.lower())


def required_headings(it):
    if it.get("type") == "offering":
        return OFFERING_HEADINGS.get(it.get("kind"), [])
    return HEADINGS.get(it.get("type"), [])


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")[:48]


def norm_questions(it):
    """Every research question on an item as {id, q, fit, weight, must, why}. Strings are
    questions weighted 5; `deep` questions are research-only, weight 0; a map sets its own
    `weight` (0-10), `must` (a deal-breaker) and `why`. fit is `good`, `bad` or None for deep."""
    r = it.get("research") or {}
    out = []
    for group, fit, default in (("qualify_good", "good", 5), ("qualify_bad", "bad", 5), ("deep", None, 0)):
        for x in as_list(r.get(group)):
            d = dict(x) if isinstance(x, dict) else {"q": x}
            d.setdefault("weight", default)
            out.append({"id": d.get("id") or slug(d.get("q", "")), "q": d.get("q"), "fit": fit,
                        "weight": d["weight"], "must": bool(d.get("must")), "why": d.get("why")})
    return out


def offering_personas(items, offering):
    """Personas that apply when selling this offering: those of its ICPs, less any scoped elsewhere."""
    return [p for i in as_list(items[offering].get("icps")) for p in as_list(items.get(i, {}).get("personas"))
            if p in items and serves(items[p], offering)]


# ---------------------------------------------------------------- sizes

def parse_range(key):
    """'51-200' -> (51, 200); '5001+' -> (5001, inf); '1' -> (1, 1)."""
    k = str(key).replace(",", "").strip()
    if m := re.fullmatch(r"(\d+)\s*\+", k):
        return int(m.group(1)), float("inf")
    if m := re.fullmatch(r"(\d+)\s*-\s*(\d+)", k):
        return int(m.group(1)), int(m.group(2))
    if re.fullmatch(r"\d+", k):
        return int(k), int(k)
    raise ValueError(f"not a size range: {key!r}")


def headcount(v):
    """A number, or an enrichment band like '51-200 employees' / 'Self-employed'. Returns the
    band's lower bound, which is what the ranges are matched against."""
    if v is None or str(v).strip() == "":
        return None
    s = str(v).lower().replace(",", "")
    if "self" in s:
        return 1
    m = re.search(r"\d+", s)
    return int(m.group()) if m else None


def size_band(v):
    """What a company's size could be: (lo, hi). '51-200 employees' -> (51, 200), '10,001+' ->
    (10001, inf), 'Self-employed' -> (1, 1), 120 -> (120, 120). None if unreadable."""
    if v is None or str(v).strip() == "":
        return None
    s = str(v).lower().replace(",", "")
    if "self" in s:
        return 1, 1
    if m := re.search(r"(\d+)\s*-\s*(\d+)", s):
        return int(m.group(1)), int(m.group(2))
    if m := re.search(r"(\d+)\s*\+", s):
        return int(m.group(1)), float("inf")
    m = re.search(r"\d+", s)
    return (int(m.group()),) * 2 if m else None


def in_ranges(n, ranges):
    """True if the size could fall in any range. n is a number or a (lo, hi) band; a band
    passes if it overlaps, so '11-50 employees' fits '20-500'. Only a band wholly outside fails."""
    lo, hi = n if isinstance(n, tuple) else (n, n)
    return any(lo <= r_hi and hi >= r_lo for r_lo, r_hi in map(parse_range, ranges))


def band_lists(mapping, n):
    """All lists in a {range: [..]} map whose range the size (number or band) could fall in."""
    out = []
    for k, v in (mapping or {}).items():
        if n is not None and in_ranges(n, [k]):
            out += as_list(v)
    return out


# ---------------------------------------------------------------- lint

def lint(items, errors, stale_only=False, today=None):
    today = today or date.today()
    problems, warnings, stale = list(errors), [], []
    for iid, it in items.items():
        p = it["_path"]
        for k in REQUIRED:
            if not it.get(k):
                problems.append(f"{p}: missing `{k}`")
        if it.get("id") and it["id"] != it["_file_id"]:
            problems.append(f"{p}: id `{it['id']}` doesn't match the filename")
        if it.get("type") and it["type"] != it["_folder_type"]:
            problems.append(f"{p}: type `{it['type']}` is in the {it['_folder_type']} folder")
        if it.get("status") and it["status"] not in STATUSES:
            problems.append(f"{p}: status `{it['status']}` is not one of {sorted(STATUSES)}")
        comp_dir = CONFIG.get("competitors_dir")
        for field, want in LINKS.items():
            for ref in as_list(it.get(field)):
                tgt = items.get(ref)
                if not tgt and field == "competitors" and comp_dir and os.path.exists(os.path.join(ROOT, comp_dir, f"{ref}.md")):
                    warnings.append(f"{p}: competitors -> `{ref}` is a research file; link a competitor element that lists it in `dossiers`")
                elif not tgt:
                    problems.append(f"{p}: {field} -> `{ref}` doesn't exist")
                elif tgt.get("type") != want:
                    problems.append(f"{p}: {field} -> `{ref}` is a {tgt.get('type')}, not a {want}")
        _lint_model(it, items, problems, warnings)
        for where, rx in _nested_regexes(it.get("person_score")):
            try:
                re.compile(rx)
            except re.error as e:
                problems.append(f"{p}: person_score.{where} regex doesn't compile: {e}")
        for rx_field in ("title_regex", "exclude_regex", "industry_regex", "exclude_industry_regex"):
            for rx in _regexes(it, rx_field):
                try:
                    re.compile(rx)
                except re.error as e:
                    problems.append(f"{p}: {rx_field} doesn't compile: {e}")
        fg = it.get("firmographics") or {}
        size_keys = list((it.get("titles") or {}).get("by_size") or {}) + as_list(fg.get("employees"))
        any_of = fg.get("any_of") or {}
        if not isinstance(any_of, dict) or not all(isinstance(c, dict) for c in any_of.values()):
            problems.append(f"{p}: firmographics.any_of must map a name to a condition"); any_of = {}
        for c in any_of.values():
            size_keys += as_list(c.get("employees"))
            if c.get("revenue_min") and money(c["revenue_min"]) is None:
                problems.append(f"{p}: revenue_min `{c['revenue_min']}` isn't an amount")
        for rk in size_keys:
            try:
                parse_range(rk)
            except ValueError as e:
                problems.append(f"{p}: {e}")
        if it.get("type") == "persona":
            _lint_titles(it, warnings)
            if not (it.get("research") or {}).get("qualify_good"):
                warnings.append(f"{p}: no research.qualify_good questions")
        if it.get("type") == "icp" and not (it.get("research") or {}).get("qualify_good"):
            warnings.append(f"{p}: no research.qualify_good questions")
        lc = it.get("last_confirmed")
        try:
            age = (today - date.fromisoformat(str(lc))).days
            if age > int(it.get("cadence_days") or DEFAULT_CADENCE_DAYS):
                stale.append(f"{p}: last confirmed {lc} ({age} days)")
        except ValueError:
            problems.append(f"{p}: last_confirmed `{lc}` isn't a date")
    for a_type, a_field, b_type, b_field in RECIPROCAL:
        for iid, it in items.items():
            if it.get("type") != a_type:
                continue
            for ref in as_list(it.get(a_field)):
                tgt = items.get(ref)
                if tgt and iid not in as_list(tgt.get(b_field)):
                    warnings.append(f"{it['_path']}: lists {b_type} `{ref}`, which doesn't list this {a_type} back")
    if stale_only:
        return [], [], stale
    return problems, warnings, stale


def _lint_model(it, items, problems, warnings):
    """Offering scope, kinds, motions, tags, weighted questions, required headings, and the
    rules particular to competitors, angles and triggers."""
    p, typ = it["_path"], it.get("type")
    scoped = as_list(it.get("offerings")) if typ != "icp" else []
    if typ != "offering" and scoped and it.get("icps"):
        sold = {o for i in as_list(it.get("icps")) for o in as_list(items.get(i, {}).get("offerings"))}
        for o in scoped:
            if o in items and o not in sold:
                warnings.append(f"{p}: scoped to offering `{o}`, which none of its ICPs lists, so it never applies" if typ == "persona"
                                else f"{p}: lists offering `{o}` but none of its ICPs buys it; add the ICP or drop the offering")
    po = it.get("primary_offering")
    if po and it.get("offerings") and po not in as_list(it.get("offerings")):
        warnings.append(f"{p}: primary_offering `{po}` isn't one of its offerings")
    if typ == "offering" and it.get("kind") not in OFFERING_KINDS:
        warnings.append(f"{p}: kind `{it.get('kind')}` is not one of {OFFERING_KINDS}")
    if typ == "offering" and not it.get("sources"):
        warnings.append(f"{p}: an offering should cite `sources`, so drift can be checked")
    for m in as_list(it.get("motion")):
        if m not in MOTIONS:
            problems.append(f"{p}: motion `{m}` is not one of {MOTIONS}")
    if it.get("motion") and typ not in MOTION_TYPES:
        warnings.append(f"{p}: `motion` only means something on {sorted(MOTION_TYPES)}")
    tags = it.get("tags")
    if tags is not None:
        if not isinstance(tags, dict):
            problems.append(f"{p}: tags must map a group to values, e.g. `tags: {{region: [NA]}}` as a nested map")
        else:
            allowed = set(CONFIG.get("tag_groups") or [])
            for grp in tags:
                if grp not in allowed:
                    warnings.append(f"{p}: tag group `{grp}` isn't in `tag_groups` in .gtmlibrary.json")
    seen = set()
    for q in norm_questions(it):
        w = q["weight"]
        if not q["q"]:
            problems.append(f"{p}: a research question has no `q`")
        if not isinstance(w, int) or isinstance(w, bool) or not 0 <= w <= 10:
            problems.append(f"{p}: question `{q['id']}` weight `{w}` isn't a whole number 0-10")
        elif q["must"] and (w == 0 or q["fit"] is None):
            warnings.append(f"{p}: question `{q['id']}` is a deal-breaker but isn't scored")
        if q["id"] in seen:
            warnings.append(f"{p}: two research questions share the id `{q['id']}`; give one an `id`")
        seen.add(q["id"])
    # A required heading is met by the plain heading or by any per-offering variant of it,
    # `## Why we win (talent-placement)`.
    have = {re.sub(r"\s*\([^)]*\)\s*$", "", h).lower() for h in sections(it["_body"])}
    for h in required_headings(it):
        if h.lower() not in have:
            warnings.append(f"{p}: no `## {h}` section")
    for h in sections(it["_body"]):
        m = re.search(r"\(([^)]*)\)\s*$", h)
        if m and m.group(1) in items and items[m.group(1)].get("type") == "offering" \
                and as_list(it.get("offerings")) and m.group(1) not in as_list(it.get("offerings")):
            warnings.append(f"{p}: section `{h}` is for an offering this item isn't scoped to")
    comp_dir = CONFIG.get("competitors_dir")
    if typ == "competitor":
        for d in as_list(it.get("dossiers")):
            if not comp_dir or not os.path.exists(os.path.join(ROOT, comp_dir, f"{d}.md")):
                problems.append(f"{p}: dossiers -> `{d}` has no file in {comp_dir or '(no competitors_dir set)'}/")
    if typ == "angle" and len(as_list(it.get("offerings"))) != 1:
        warnings.append(f"{p}: an angle sells exactly one offering; it lists {len(as_list(it.get('offerings')))}")
    if typ == "trigger" and not it.get("detect"):
        warnings.append(f"{p}: no `detect` list saying how to spot this trigger in data")


def _nested_regexes(node, path=""):
    """Every `regex` value inside a nested map, with its dotted path."""
    if not isinstance(node, dict):
        return []
    out = []
    for k, v in node.items():
        if k == "regex" and isinstance(v, str):
            out.append((path.strip("."), v))
        elif isinstance(v, dict):
            out += _nested_regexes(v, f"{path}.{k}")
    return out


def _regexes(it, field):
    v = it.get(field)
    if v is None:
        v = (it.get("firmographics") or {}).get(field)
    return as_list(v) if not isinstance(v, dict) else [x for vs in v.values() for x in as_list(vs)]


def _lint_titles(it, warnings):
    """Every title the persona lists should be one its own regex would catch."""
    t = it.get("titles") or {}
    listed = as_list(t.get("default"))
    for group in ("by_size", "by_industry"):
        for v in (t.get(group) or {}).values():
            listed += as_list(v)
    inc = [re.compile(r) for r in _regexes(it, "title_regex")]
    exc = [re.compile(r) for r in _regexes(it, "exclude_regex")]
    for title in sorted(set(listed)):
        if inc and not any(r.search(title) for r in inc):
            warnings.append(f"{it['_path']}: listed title {title!r} isn't matched by title_regex")
        elif any(r.search(title) for r in exc):
            warnings.append(f"{it['_path']}: listed title {title!r} is caught by exclude_regex")


# ---------------------------------------------------------------- match

def money(v):
    """'$1M', '10M-25M', '500K' -> lower bound in dollars; None if unreadable."""
    if v is None or str(v).strip() == "":
        return None
    m = re.search(r"([\d.]+)\s*([KMBT]?)", str(v).replace(",", "").replace("$", ""), re.I)
    if not m:
        return None
    return float(m.group(1)) * {"": 1, "K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[m.group(2).upper()]


def _any_of(conds, n, rev, funding):
    """True/False when any condition can be decided, None when every tested field is unknown.
    A condition holds if all of its known fields pass: employees (ranges), revenue_min, funding_stages."""
    decided = False
    for c in conds:
        results = []
        if c.get("employees") and n is not None:
            results.append(in_ranges(n, as_list(c["employees"])))
        if c.get("revenue_min") and rev is not None:
            results.append(rev >= money(c["revenue_min"]))
        if c.get("funding_stages") and funding:
            results.append(funding.strip().lower() in {s.lower() for s in as_list(c["funding_stages"])})
        if results:
            decided = True
            if all(results):
                return True
    return False if decided else None


def match_icps(items, employees=None, industry=None, revenue=None, funding=None):
    """ICPs whose firmographics fit. An ICP with no constraint on a field doesn't test it; an
    unknown value doesn't disqualify. Returns [(icp, score, reasons)] best first."""
    n = size_band(employees)
    rev = money(revenue)
    out = []
    for it in items.values():
        if it.get("type") != "icp" or it.get("status") == "retired":
            continue
        f = it.get("firmographics") or {}
        score, why = 0, []
        if f.get("employees") and n is not None:
            if not in_ranges(n, as_list(f["employees"])):
                continue
            score += 1; why.append("size")
        if f.get("any_of"):
            ok = _any_of(list(f["any_of"].values()), n, rev, funding)
            if ok is False:
                continue
            if ok:
                score += 1; why.append("stage")
        if industry:
            if any(re.search(r, industry) for r in as_list(f.get("exclude_industry_regex"))):
                continue
            if f.get("industry_regex"):
                if not any(re.search(r, industry) for r in as_list(f["industry_regex"])):
                    continue
                score += 2; why.append("industry")
        out.append((it, score, why))
    return sorted(out, key=lambda x: -x[1])


def match_personas(items, title, employees=None, industry=None, icp=None, offering=None):
    """Personas whose titles fit, scored: exact title in the list for this size band 3, in the
    industry list 3, in the default list 2, regex only 1. Excludes win. With an offering, only the
    personas it reaches: those of its ICPs, less any scoped to other offerings."""
    n = size_band(employees)
    t = (title or "").strip()
    tl = t.lower()
    allowed = set(as_list(items[icp].get("personas"))) if icp else None
    reach = set(offering_personas(items, offering)) if offering else None
    out = []
    for it in items.values():
        if it.get("type") != "persona" or it.get("status") == "retired":
            continue
        if allowed is not None and it["id"] not in allowed:
            continue
        if reach is not None and it["id"] not in reach:
            continue
        if any(re.search(r, t) for r in _regexes(it, "exclude_regex")):
            continue
        titles = it.get("titles") or {}
        score, why = 0, []
        if tl in (x.lower() for x in band_lists(titles.get("by_size"), n)):
            score, why = 3, ["title listed for this size"]
        elif industry and any(tl in (x.lower() for x in as_list(v))
                              for k, v in (titles.get("by_industry") or {}).items() if re.search(k, industry, re.I)):
            score, why = 3, ["title listed for this industry"]
        elif tl in (x.lower() for x in as_list(titles.get("default"))):
            score, why = 2, ["title in default list"]
        elif any(re.search(r, t) for r in _regexes(it, "title_regex")):
            score, why = 1, ["title_regex"]
        if score:
            out.append((it, score, why))
    return sorted(out, key=lambda x: -x[1])


def questions(items, icp=None, persona=None, offering=None):
    """Research questions for an offering (the deal), an ICP (the company) and a persona (the person)."""
    out = {}
    for iid, label in ((offering, "offering"), (icp, "company"), (persona, "person")):
        if not iid:
            continue
        it = items[iid]
        qs = norm_questions(it)
        out[label] = {"id": iid, "name": it.get("name"),
                      "qualify_good": [q["q"] for q in qs if q["fit"] == "good"],
                      "qualify_bad": [q["q"] for q in qs if q["fit"] == "bad"],
                      "deep": [q["q"] for q in qs if q["fit"] is None],
                      "questions": qs}
    return out


def select(items, typ=None, offering=None, motion=None, icp=None, persona=None):
    """Elements of a type that apply to an offering, motion, ICP or persona. An element with
    no `offerings` (or `motion`, `icps`, `personas`) applies to all of them."""
    out = []
    # With an offering, the structural types narrow to what it actually reaches: the offering
    # itself, the ICPs it is sold to, and those ICPs' personas that aren't scoped elsewhere.
    sold_to = set(as_list(items[offering].get("icps"))) if offering else None
    reach = set(offering_personas(items, offering)) if offering else None
    out = []
    for it in items.values():
        if typ and it.get("type") != typ or it.get("status") == "retired":
            continue
        if not serves(it, offering) or not in_motion(it, motion):
            continue
        if offering and ((it.get("type") == "offering" and it["id"] != offering)
                         or (it.get("type") == "icp" and it["id"] not in sold_to)
                         or (it.get("type") == "persona" and it["id"] not in reach)):
            continue
        if icp and it.get("type") != "icp" and as_list(it.get("icps")) and icp not in as_list(it.get("icps")):
            continue
        if persona and as_list(it.get("personas")) and persona not in as_list(it.get("personas")):
            continue
        out.append(it)
    return sorted(out, key=lambda x: (x.get("type"), x["id"]))


def agent_view(it):
    """One element as an agent reads it: frontmatter fields, questions normalised, and every
    body section by heading."""
    d = {k: v for k, v in it.items() if not k.startswith("_")}
    if it.get("research"):
        d["research"] = norm_questions(it)
    d["sections"] = sections(it["_body"])
    d["path"] = it["_path"]
    return d


# ---------------------------------------------------------------- classify

def classify(items, path, title_col, size_col, industry_col, offering=None, revenue_col="Annual Revenues",
             backend=None, out_csv=None):
    """Run a list of real buyers through the library. The point is the misses: titles no
    persona catches and companies no ICP describes are where the library is wrong.
    With an offering, only the ICPs it links (and their personas) are candidates. With the
    jev backend, titles the rules only catch by regex (or not at all) also go to Jev, and the
    report compares the two."""
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if backend == "jev":
        try:
            return _classify_with_jev(items, rows, path, title_col, size_col, industry_col, offering, revenue_col, out_csv)
        except JevUnavailable as e:
            print(f"note: {e}; classifying with the rules only\n", file=sys.stderr)
    scope = None
    if offering:
        icp_ids = as_list(items[offering].get("icps"))
        scope = {"icps": set(icp_ids), "personas": set(offering_personas(items, offering))}
    icp_hits, persona_hits = collections.Counter(), collections.Counter()
    no_icp, no_persona, pairs = collections.Counter(), collections.Counter(), collections.Counter()
    for r in rows:
        title, size, ind = r.get(title_col, ""), r.get(size_col, ""), r.get(industry_col, "")
        rev = r.get(revenue_col, "")
        icps = match_icps(items, size, ind, rev) if (size or ind or rev) else []
        if scope:
            icps = [x for x in icps if x[0]["id"] in scope["icps"]]
        top_icp = icps[0][0]["id"] if icps and icps[0][1] > 0 else None
        pers = match_personas(items, title, size, ind, icp=top_icp, offering=offering) if title else []
        if not pers and title and top_icp:
            pers = match_personas(items, title, size, ind, offering=offering)
        if scope:
            pers = [x for x in pers if x[0]["id"] in scope["personas"]]
        top_p = pers[0][0]["id"] if pers else None
        icp_hits[top_icp or "-"] += 1
        persona_hits[top_p or "-"] += 1
        pairs[(top_icp or "-", top_p or "-")] += 1
        if not top_icp:
            no_icp[f"{size or '?'} / {ind or '?'}"] += 1
        if not top_p:
            no_persona[title or "(blank)"] += 1
    total = len(rows)
    print(f"{total} rows from {os.path.relpath(path, ROOT)}" + (f", scoped to {offering}" if offering else "") + "\n")
    for label, c in (("ICP", icp_hits), ("Persona", persona_hits)):
        print(f"## {label}")
        for k, v in c.most_common():
            print(f"  {v:>4}  {v / total:>4.0%}  {k}")
        print()
    print("## ICP x persona")
    for (a, b), v in pairs.most_common():
        print(f"  {v:>4}  {a} x {b}")
    print("\n## No ICP matched (size / industry)")
    for k, v in no_icp.most_common(25):
        print(f"  {v:>4}  {k}")
    print("\n## No persona matched (title)")
    for k, v in no_persona.most_common(60):
        print(f"  {v:>4}  {k}")


def label(items, path, offering, title_col, size_col, industry_col, revenue_col, out_csv, backend=None, extra_col=None):
    """Label a lead list for one offering, so it can go into a campaign tool as it is. Every row
    keeps its own columns and gains: the persona, where that came from (a listed title, the
    title regex, the classifier, or nothing), the classifier's confidence, and the ICP its
    firmographics fit. The rules decide a listed title; the classifier is asked only about the
    rest, once per distinct title. Anything under the confidence bar is left `unsure` for a
    person, never guessed."""
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    if not rows:
        sys.exit(f"{path} has no rows")
    cands = list(dict.fromkeys(offering_personas(items, offering)))
    icp_ids = set(as_list(items[offering].get("icps")))
    ruled, ask = [], {}
    for r in rows:
        t = (r.get(title_col) or "").strip()
        size, ind, rev = r.get(size_col, ""), r.get(industry_col, ""), r.get(revenue_col, "")
        hits = [h for h in match_personas(items, t, size, ind, offering=offering) if h[0]["id"] in cands] if t else []
        icps = [x for x in match_icps(items, size, ind, rev) if x[0]["id"] in icp_ids] if (size or ind or rev) else []
        top = hits[0] if hits else None
        if t and (not top or top[1] < 2):
            ask[t + "\u0000" + (r.get(extra_col) or "" if extra_col else "")] = (t, r.get(extra_col) or "" if extra_col else "")
        ruled.append((r, t, top, icps[0][0]["id"] if icps and icps[0][1] > 0 else ""))
    placed = {}
    if ask and backend == "jev":
        try:
            placed = place_with_jev(items, [(k, v[0], v[1]) for k, v in ask.items()], cands)
        except JevUnavailable as e:
            print(f"note: {e}; labelling with the rules only\n", file=sys.stderr)
    out, counts = [], collections.Counter()
    for r, t, top, icp in ruled:
        persona, source, conf = "", "none", ""
        if top and top[1] >= 2:
            persona, source = top[0]["id"], "listed title"
        elif t:
            key = t + "\u0000" + ((r.get(extra_col) or "") if extra_col else "")
            jp, jc = placed.get(key, (None, 0.0))
            if jc >= CLASSIFIER["min_confidence"]:
                persona, source, conf = (jp or ""), ("classifier" if jp else "classifier: none of them"), round(jc, 2)
            elif top:
                persona, source = top[0]["id"], "title regex"
            elif backend == "jev" and placed:
                source, conf = "unsure", round(jc, 2)
        counts[source] += 1
        d = dict(r)
        d["gtm_persona"], d["gtm_persona_source"], d["gtm_persona_confidence"], d["gtm_icp"], d["gtm_offering"] = persona, source, conf, icp, offering
        out.append(d)
    fields = list(rows[0].keys()) + [c for c in ("gtm_persona", "gtm_persona_source", "gtm_persona_confidence", "gtm_icp", "gtm_offering") if c not in rows[0]]
    dest = out_csv or os.path.splitext(path)[0] + "-labelled.csv"
    w = csv.DictWriter(open(dest, "w", newline="", encoding="utf-8"), fieldnames=fields)
    w.writeheader(); w.writerows(out)
    n = len(out)
    print(f"{n} leads labelled for {offering} → {os.path.relpath(dest, ROOT)}\n")
    print("## Where the persona came from")
    for k, v in counts.most_common():
        print(f"  {v:>5}  {v / n:>4.0%}  {k}")
    print("\n## Persona")
    for k, v in collections.Counter(d["gtm_persona"] or "-" for d in out).most_common():
        print(f"  {v:>5}  {v / n:>4.0%}  {k}")
    print("\n## ICP")
    for k, v in collections.Counter(d["gtm_icp"] or "-" for d in out).most_common():
        print(f"  {v:>5}  {v / n:>4.0%}  {k}")
    unsure = [d for d in out if d["gtm_persona_source"] in ("unsure", "none")]
    if unsure:
        print(f"\n## For a person to look at: {len(unsure)}")
        for t, v in collections.Counter((d.get(title_col) or "(blank title)") for d in unsure).most_common(20):
            print(f"  {v:>5}  {t}")
    return out


def _classify_with_jev(items, rows, path, title_col, size_col, industry_col, offering, revenue_col, out_csv):
    """Rules first; every distinct title Jev then places too. Reports agreement where the
    rules were sure, what Jev adds where they weren't, and writes one row per person."""
    cands = offering_personas(items, offering) if offering else [i for i, x in items.items() if x.get("type") == "persona" and x.get("status") != "retired"]
    cands = list(dict.fromkeys(cands))
    ruled = []
    for r in rows:
        t, size, ind = r.get(title_col, "").strip(), r.get(size_col, ""), r.get(industry_col, "")
        hits = [h for h in match_personas(items, t, size, ind, offering=offering) if h[0]["id"] in cands] if t else []
        ruled.append((t, hits[0][0]["id"] if hits else None, hits[0][1] if hits else 0))
    titles = sorted({t for t, _, _ in ruled if t})
    placed = place_with_jev(items, [(t, t, "") for t in titles], cands) if titles else {}
    minc = CLASSIFIER["min_confidence"]
    c = collections.Counter()
    disagree = collections.Counter()
    out = []
    for t, rp, rs in ruled:
        jp, jc = placed.get(t, (None, 0.0)) if t else (None, 0.0)
        sure = jc >= minc
        kind = ("blank" if not t else "rules-sure" if rs >= 2 else "rules-regex" if rs == 1 else "rules-miss")
        c[kind] += 1
        if kind == "rules-sure":
            c["sure-agree" if jp == rp else "sure-disagree"] += 1
            if jp != rp:
                disagree[f"{t} — rules {rp}, jev {jp or 'none'} ({jc:.2f})"] += 1
        elif kind == "rules-regex":
            c["regex-agree" if jp == rp else ("regex-jev-other" if sure else "regex-jev-unsure")] += 1
        elif kind == "rules-miss":
            c[("miss-placed" if jp else "miss-jev-none") if sure else "miss-jev-unsure"] += 1
        final = rp if rs >= 2 else (jp if sure else rp)
        out.append({"title": t, "rules": rp or "", "rules_score": rs, "jev": jp or "", "jev_confidence": round(jc, 2), "final": final or ""})
    n = len(rows)
    print(f"{n} rows from {os.path.relpath(path, ROOT)}, {len(titles)} distinct titles sent to Jev" + (f", scoped to {offering}" if offering else ""))
    print(f"min confidence {minc}\n")
    for label, keys in (("Rules sure (listed title)", ["rules-sure", "sure-agree", "sure-disagree"]),
                        ("Rules by regex only", ["rules-regex", "regex-agree", "regex-jev-other", "regex-jev-unsure"]),
                        ("Rules miss", ["rules-miss", "miss-placed", "miss-jev-none", "miss-jev-unsure"]),
                        ("Blank title", ["blank"])):
        print(f"## {label}: {c[keys[0]]}")
        for k in keys[1:]:
            print(f"  {c[k]:>4}  {k}")
        print()
    fin = collections.Counter(r["final"] or "-" for r in out)
    rules_only = collections.Counter(r["rules"] or "-" for r in out)
    print("## Persona, rules only → rules + Jev")
    for k in sorted(set(fin) | set(rules_only), key=lambda k: -fin[k]):
        print(f"  {rules_only[k]:>4} → {fin[k]:>4}  {k}")
    if disagree:
        print("\n## Where Jev disagrees with a listed title (the rules win; check the library)")
        for k, v in disagree.most_common(25):
            print(f"  {v:>4}  {k}")
    if out_csv:
        w = csv.DictWriter(open(out_csv, "w", newline="", encoding="utf-8"), fieldnames=list(out[0]))
        w.writeheader(); w.writerows(out)
        print(f"\nwrote {out_csv}")


# ---------------------------------------------------------------- judge (the classifier)
#
# Closed-answer judgements (which persona is this title, is this answer a yes) go through one
# step with a configured backend. `jev` calls TypeSafe's System One API over plain HTTP. With no
# backend, the script only prints the questions and the calling skill answers them with a model.
# Every judgement carries a confidence; below `min_confidence` it counts as unknown.

JEV_URL = "https://api.typesafe.ai/v1/systemone"
CLASSIFIER = {"backend": None, "min_confidence": 0.7, "key_env": "JEV_API_KEY", "batch": 40,
              **(CONFIG.get("classifier") or {})}


def _env_key(name):
    """An API key from the environment, else from a `.env` at the repo root, else from the
    `.env` of the main checkout when running in a git worktree. Never printed."""
    if os.environ.get(name):
        return os.environ[name]
    roots = [ROOT]
    try:
        import subprocess
        common = subprocess.run(["git", "-C", ROOT, "rev-parse", "--git-common-dir"], capture_output=True, text=True).stdout.strip()
        if common:
            roots.append(os.path.dirname(os.path.abspath(os.path.join(ROOT, common))))
    except OSError:
        pass
    for r in roots:
        p = os.path.join(r, ".env")
        if os.path.exists(p):
            for line in open(p, encoding="utf-8"):
                k, _, v = line.strip().partition("=")
                if k == name and v:
                    return v.strip().strip("'\"")
    return None


def pick_backend(requested=None, need=False):
    """The backend to use: the flag, else the config. A configured jev with no key falls back
    to rules only with a note, so a scheduled run without the key still works; asked for
    explicitly (or needed), a missing key is an error."""
    b = requested or CLASSIFIER["backend"]
    if b == "jev" and not _env_key(CLASSIFIER["key_env"]):
        if requested or need:
            raise SystemExit(f"--backend jev needs {CLASSIFIER['key_env']} in the environment or a .env file")
        print(f"note: classifier is jev but {CLASSIFIER['key_env']} isn't set; using the rules only", file=sys.stderr)
        return None
    return b


class JevUnavailable(Exception):
    """Jev couldn't answer: no network, a blocked domain, or an error status."""


def jev(state, questions, key=None, timeout=60):
    """One System One call. `questions` is {id: {type, instructions, criteria?}}; returns
    {id: answer}. Retries twice on 429/529."""
    import time, urllib.error, urllib.request
    key = key or _env_key(CLASSIFIER["key_env"])
    if not key:
        raise SystemExit(f"no {CLASSIFIER['key_env']} in the environment or a .env file")
    body = json.dumps({"state": state, "model": "jev-latest", "questions": questions}).encode()
    for attempt in range(3):
        req = urllib.request.Request(JEV_URL, body, {"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            return json.load(urllib.request.urlopen(req, timeout=timeout))["answers"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < 2:
                time.sleep(2 ** attempt * 2)
                continue
            raise JevUnavailable(f"Jev returned {e.code}: {e.read().decode(errors='replace')[:300]}")
        except (urllib.error.URLError, OSError) as e:
            # A blocked or absent network, e.g. a cloud environment whose network access
            # doesn't allow api.typesafe.ai. Callers fall back to the rules.
            raise JevUnavailable(f"couldn't reach Jev ({getattr(e, 'reason', e)}); check network access to api.typesafe.ai")


def persona_criteria(items, ids):
    """Choice options for placing a person: one line per persona, plus `none`."""
    out = {}
    for pid in ids:
        p = items[pid]
        t = p.get("titles") or {}
        out[pid] = (f"{p.get('name')}: {', '.join(as_list(p.get('functions')))}; "
                    f"{', '.join(as_list(p.get('seniority')))}; e.g. {', '.join(as_list(t.get('default'))[:5])}")
    out["none"] = "None of these: outside go-to-market, a student with no GTM role, or no role given"
    return out


def place_with_jev(items, people, persona_ids, key=None):
    """people: [(key, title, extra)] -> {key: (persona id or None, confidence)}. Batched."""
    crit = persona_criteria(items, persona_ids)
    out, n = {}, CLASSIFIER["batch"]
    for i in range(0, len(people), n):
        chunk = people[i:i + n]
        qs = {f"p{j}": {"type": "choice", "criteria": crit,
                        "instructions": f"Which buyer persona best describes a person titled {t!r}" + (f" ({x})" if x else "") + "?"}
              for j, (_, t, x) in enumerate(chunk)}
        ans = jev("Place people into the buyer personas of a GTM engineering school.", qs, key)
        for j, (k, _, _) in enumerate(chunk):
            a = ans.get(f"p{j}") or {}
            out[k] = (None if a.get("choice") == "none" else a.get("choice"), float(a.get("confidence") or 0))
    return out


def answer_with_jev(qs, state, key=None):
    """Answer normalised questions ({id, q, …}) from evidence text. Returns {id: {answer,
    confidence, p_yes}}; below min_confidence the answer is `unknown`."""
    # A choice with an explicit "not stated" option, not a yes/no: a yes/no probability can't
    # tell "no" from "the evidence doesn't say", and it reported a supplier list nobody had
    # mentioned as a confident no. A choice also carries its own confidence.
    crit = {"yes": "The evidence says yes.", "no": "The evidence says no.",
            "not_stated": "The evidence doesn't say either way."}
    ans = jev(state, {q["id"]: {"type": "choice", "criteria": crit,
                                "instructions": f"From the evidence only: {q['q']}"} for q in qs}, key)
    out = {}
    for q in qs:
        a = ans.get(q["id"]) or {}
        choice, c = a.get("choice"), float(a.get("confidence") or 0)
        sure = choice in ("yes", "no") and c >= CLASSIFIER["min_confidence"]
        out[q["id"]] = {"answer": choice if sure else "unknown", "confidence": round(c, 2),
                        "jev": choice, "evidence": "jev"}
    return out


# ---------------------------------------------------------------- qualify (scoring)

def score(items, answers):
    """answers: {element id: {question id: {answer: yes|no|unknown, evidence?}}}. For each
    element, the share of answered weight that points to fit, out of 100; deal-breakers
    failed (ruled out) and unanswered (unconfirmed); coverage. Unknowns are left out of the
    score, never counted as fails; weight-0 questions are never scored."""
    report = {}
    for eid, given in answers.items():
        if eid not in items:
            raise SystemExit(f"answers name `{eid}`, which isn't in the library")
        got = pas = 0
        failed, unconfirmed, answered, scored, unknown_ids = [], [], 0, 0, []
        known = {q["id"]: q for q in norm_questions(items[eid])}
        for qid in given:
            if qid not in known:
                raise SystemExit(f"`{eid}` has no question `{qid}`")
        for q in known.values():
            if q["fit"] is None or q["weight"] == 0:
                continue
            scored += 1
            a = str((given.get(q["id"]) or {}).get("answer", "unknown")).lower()
            if a not in ("yes", "no"):
                unknown_ids.append(q["id"])
                if q["must"]:
                    unconfirmed.append(q["id"])
                continue
            answered += 1
            fits = (a == "yes") == (q["fit"] == "good")
            got += q["weight"]
            pas += q["weight"] if fits else 0
            if q["must"] and not fits:
                failed.append(q["id"])
        report[eid] = {"type": items[eid]["type"], "score": round(100 * pas / got) if got else None,
                       "answered": answered, "of": scored, "ruled_out_by": failed,
                       "unconfirmed": unconfirmed, "unknown": unknown_ids}
    return report


def answer_template(items, ids):
    """A blank answers file for these elements: every scored question, answer `unknown`."""
    return {eid: {q["id"]: {"q": q["q"], "answer": "unknown", "evidence": ""}
                  for q in norm_questions(items[eid]) if q["fit"] and q["weight"]} for eid in ids}


# ---------------------------------------------------------------- brief (call prep)

def brief(items, offering, icp=None, persona=None, motion=None):
    """One page for a call: fit questions, then what they'll say and what to say back, why now,
    what they do instead, who we're up against, and what to cite. Internal-only references and
    anything scoped to other offerings or motions are left out."""
    o = items[offering]
    pick = lambda typ: [x for x in select(items, typ, offering, motion, icp, persona)
                        if not (typ == "objection" and persona and as_list(x.get("personas")) and persona not in as_list(x.get("personas")))]
    head = f"# Call brief: {o['name']}" + (f" · {items[icp]['name']}" if icp else "") + (f" · {items[persona]['name']}" if persona else "")
    L = [head, "", f"Motion: {motion or 'any'} · generated from the GTM library {date.today().isoformat()}", ""]
    q = questions(items, icp, persona, offering)
    # The same question can sit on the offering, the ICP and the persona; show it once, where
    # it first appears. Same id or the same wording counts as the same question.
    seen = set()

    def first(x):
        keys = {x["id"], " ".join(str(x["q"]).lower().split())}
        if keys & seen:
            return False
        seen.update(keys)
        return True

    L += ["## Qualify", ""]
    for label, block in q.items():
        rows = [x for x in block["questions"] if x["fit"] and first(x)]
        if not rows:
            continue
        L.append(f"**{block['name']}**")
        for x in rows:
            L.append(f"- [{x['weight']}{', deal-breaker' if x['must'] else ''}] {'' if x['fit'] == 'good' else '(yes = not a fit) '}{x['q']}")
        L.append("")
    L += ["## Find out first", ""] + [f"- {x['q']}" for b in q.values() for x in b["questions"] if not x["fit"] and first(x)] + [""]

    def block(title, typ, parts):
        xs = pick(typ)
        if not xs:
            return []
        out = [f"## {title}", ""]
        for x in xs:
            sec = {k.lower(): v for k, v in sections(x["_body"]).items()}
            out.append(f"**{x['name']}** (`{x['id']}`)")
            for p in parts:
                text = section_for(sec, p, offering)
                if not text:
                    continue
                bullets = [l.strip()[2:] for l in text.splitlines() if l.strip().startswith("- ")]
                if bullets and len(bullets) == len([l for l in text.splitlines() if l.strip()]):
                    out.append(f"- *{p}:*")
                    out += [f"  - {b}" for b in bullets]
                else:
                    out.append(f"- *{p}:* " + " ".join(text.split()))
            out.append("")
        return out

    L += block("Why now", "trigger", ["Why now", "How we help"])
    L += block("What they'll say", "objection", ["Underlying concern", "What to probe", "Reframe"])
    L += block("What they do instead", "alternative", ["Where it breaks", "Why ours is better"])
    L += block("Who we're up against", "competitor", ["Why we win", "Why we lose"])
    L += block("Angles that have run", "angle", ["Approach", "Key messages"])
    pps = [items[p] for p in as_list(o.get("proof_points")) if p in items]
    if pps:
        L += ["## Proof", ""] + [f"- {p.get('claim') or p['name']} `[{p.get('confidence', '?')}: {p.get('source', '?')}]`" for p in pps] + [""]
    refs = [items[r] for r in as_list(o.get("references")) if r in items and items[r].get("permission") == "public"]
    if refs:
        L += ["## References you may name", ""] + [f"- {r['name']}" + (f": \"{r['quote']}\"" if r.get("quote") else "") for r in refs] + [""]
    return "\n".join(L)


# ---------------------------------------------------------------- the loop: quotes, suggestions, drift
#
# Two logs live beside the element folders, as markdown tables so they read in any editor and
# diff line by line in a review PR:
#   <library>/voice/YYYY-MM.md   one row per verbatim quote
#   <library>/suggestions.md     one row per proposed library change, and what became of it

VOICE_COLS = ["id", "date", "quote", "speaker", "company", "category", "offering", "motion", "persona",
              "outcome", "permission", "source"]
VOICE_CATEGORIES = CONFIG.get("voice_categories") or [
    "objection", "resonates", "pain", "pricing", "competitor", "request", "commitment", "trigger", "alternative"]
SUGGESTION_COLS = ["id", "date", "element", "change", "status", "reason", "evidence"]
SUGGESTION_STATUSES = ["proposed", "accepted", "rejected", "deferred"]
EXTRACTORS = CONFIG.get("extractors") or [
    {"id": "objection", "q": "What reason not to buy, or worry about buying, did they raise, in their words?", "category": "objection"},
    {"id": "resonates", "q": "What did they react to well, or repeat back?", "category": "resonates"},
    {"id": "pain", "q": "What problem or goal did they describe, in their words?", "category": "pain"},
    {"id": "pricing", "q": "What did they say about price, budget or who pays?", "category": "pricing"},
    {"id": "alternative", "q": "What do they use or do today instead, including doing nothing?", "category": "alternative"},
    {"id": "competitor", "q": "Which competitor or other provider did they name, and what did they say?", "category": "competitor"},
    {"id": "trigger", "q": "What made now the moment: an event, a hire, a deadline, a round?", "category": "trigger"},
    {"id": "signer", "q": "Who decides or signs, and who else has to agree?", "category": None},
    {"id": "titles", "q": "What titles did the people on the call have?", "category": None},
    {"id": "commitment", "q": "What did they commit to, with a date?", "category": "commitment"},
]


def _cells(line):
    """Split a markdown table row on unescaped pipes; `\\|` stays a literal pipe."""
    s = line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    return [p.strip().replace("\\|", "|") for p in re.split(r"(?<!\\)\|", s)]


def read_table(path, cols):
    """Rows of the first table in a markdown file whose header matches `cols`. Returns
    ([dict], [problem]); each dict carries `_line`."""
    rows, problems, header = [], [], None
    rel = os.path.relpath(path, ROOT)
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.lstrip().startswith("|"):
            if header and rows:
                break
            continue
        cells = _cells(line)
        if header is None:
            if [c.lower() for c in cells] == cols:
                header = cells
            continue
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if len(cells) != len(cols):
            problems.append(f"{rel}:{n}: {len(cells)} cells, expected {len(cols)} ({' | '.join(cols)}); escape a pipe in text as \\|")
            continue
        d = dict(zip(cols, cells))
        d["_line"], d["_path"] = n, rel
        rows.append(d)
    if header is None and os.path.getsize(path):
        problems.append(f"{rel}: no table with columns {' | '.join(cols)}")
    return rows, problems


def load_voice(lib=LIB):
    d = os.path.join(lib, "voice")
    rows, problems = [], []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if re.fullmatch(r"\d{4}-\d{2}\.md", f):
                r, p = read_table(os.path.join(d, f), VOICE_COLS)
                rows += r; problems += p
    return rows, problems


def load_suggestions(lib=LIB):
    p = os.path.join(lib, "suggestions.md")
    return read_table(p, SUGGESTION_COLS) if os.path.exists(p) else ([], [])


def _ids(cell):
    return [x.strip().strip("`") for x in cell.split(",") if x.strip().strip("`") and x.strip() not in ("-", "—")]


def lint_loop(items, lib=LIB):
    """The quote log and the suggestions ledger: columns, vocabularies, links, unique ids."""
    problems, warnings = [], []
    voice, p = load_voice(lib); problems += p
    seen = {}
    for r in voice:
        where = f"{r['_path']}:{r['_line']}"
        if r["id"] in seen:
            problems.append(f"{where}: quote id `{r['id']}` also on line {seen[r['id']]}")
        seen[r["id"]] = r["_line"]
        try:
            date.fromisoformat(r["date"])
        except ValueError:
            problems.append(f"{where}: date `{r['date']}` isn't a date")
        if not r["date"].startswith(os.path.basename(r["_path"])[:7]):
            warnings.append(f"{where}: dated {r['date']} but filed in {os.path.basename(r['_path'])}")
        if r["category"] not in VOICE_CATEGORIES:
            problems.append(f"{where}: category `{r['category']}` is not one of {VOICE_CATEGORIES}")
        if r["permission"] not in ("internal", "public"):
            problems.append(f"{where}: permission must be `internal` or `public`")
        for m in _ids(r["motion"]):
            if m not in MOTIONS:
                problems.append(f"{where}: motion `{m}` is not one of {MOTIONS}")
        for col, want in (("offering", "offering"), ("persona", "persona")):
            for x in _ids(r[col]):
                if items.get(x, {}).get("type") != want:
                    problems.append(f"{where}: {col} `{x}` isn't a {want} in the library")
        if not r["quote"] or not r["source"]:
            problems.append(f"{where}: a quote needs the words and a source")
    for it in items.values():
        for qid in as_list(it.get("quotes")):
            if qid not in seen:
                problems.append(f"{it['_path']}: quotes -> `{qid}` isn't in the quote log")
    sugg, p = load_suggestions(lib); problems += p
    sids = {}
    for r in sugg:
        where = f"{r['_path']}:{r['_line']}"
        if r["id"] in sids:
            problems.append(f"{where}: suggestion id `{r['id']}` also on line {sids[r['id']]}")
        sids[r["id"]] = r["_line"]
        if r["status"] not in SUGGESTION_STATUSES:
            problems.append(f"{where}: status `{r['status']}` is not one of {SUGGESTION_STATUSES}")
        if r["status"] in ("rejected", "deferred") and not r["reason"].strip("—- "):
            warnings.append(f"{where}: a {r['status']} suggestion should say why, so it isn't proposed again")
        for x in _ids(r["element"]):
            if x not in items and not x.startswith("new:"):
                warnings.append(f"{where}: element `{x}` isn't in the library (write `new:<type>/<id>` for a proposed item)")
    return problems, warnings


def accept_proposed(lib=LIB, today=None):
    """Rows still `proposed` on the default branch arrived there by a merged review PR, so they
    were accepted. Flips them and returns how many. Run at the start of an evidence run."""
    p = os.path.join(lib, "suggestions.md")
    if not os.path.exists(p):
        return 0
    rows, _ = read_table(p, SUGGESTION_COLS)
    lines = open(p, encoding="utf-8").read().split("\n")
    n = 0
    for r in rows:
        if r["status"] == "proposed":
            i = r["_line"] - 1
            cells = _cells(lines[i])
            cells[SUGGESTION_COLS.index("status")] = "accepted"
            lines[i] = "| " + " | ".join(c.replace("|", "\\|") for c in cells) + " |"
            n += 1
    if n:
        open(p, "w", encoding="utf-8").write("\n".join(lines))
    return n


def drift(items, today=None):
    """Elements whose repo-path sources changed after the element was last confirmed (from
    git), and the web pages offerings cite, which need a re-read. The judgement, whether the
    change matters, belongs to the evidence run."""
    import subprocess
    changed, pages = [], []
    for it in items.values():
        lc = str(it.get("last_confirmed"))
        for src in as_list(it.get("sources")):
            s = str(src)
            if re.match(r"^(https?://|[\w.-]+\.[a-z]{2,}/)", s) and not os.path.exists(os.path.join(ROOT, s)):
                if it.get("type") == "offering":
                    pages.append((it["id"], s if s.startswith("http") else "https://" + s))
                continue
            path = os.path.join(ROOT, s)
            if not os.path.exists(path):
                changed.append((it["id"], s, "missing", []))
                continue
            log = subprocess.run(["git", "-C", ROOT, "log", "--no-merges", f"--since={lc}T23:59:59", "--format=%h %as %s", "--", s],
                                 capture_output=True, text=True).stdout.strip().splitlines()
            if log:
                changed.append((it["id"], s, "changed", log))
    return changed, pages


def voice_select(rows, category=None, offering=None, motion=None, persona=None, since=None, public=False):
    out = []
    for r in rows:
        if category and r["category"] != category:
            continue
        if offering and offering not in _ids(r["offering"]):
            continue
        if motion and _ids(r["motion"]) and motion not in _ids(r["motion"]):
            continue
        if persona and persona not in _ids(r["persona"]):
            continue
        if since and r["date"] < since:
            continue
        if public and r["permission"] != "public":
            continue
        out.append(r)
    return out


def counts(items, since, lib=LIB):
    """The weekly line per offering: quotes logged and suggestions made since a date."""
    voice, _ = load_voice(lib)
    sugg, _ = load_suggestions(lib)
    out = {}
    for o in sorted(i for i, x in items.items() if x.get("type") == "offering"):
        q = [r for r in voice if r["date"] >= since and o in _ids(r["offering"])]
        related = {o} | set(as_list(items[o].get("icps"))) | {x["id"] for x in select(items, offering=o) if x.get("offerings")}
        s = [r for r in sugg if r["date"] >= since and set(_ids(r["element"])) & related]
        out[o] = {"quotes": len(q), "by_category": dict(collections.Counter(r["category"] for r in q)),
                  "suggestions": len(s)}
    return out


# ---------------------------------------------------------------- dashboard

DASHBOARD_TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "templates", "dashboard.html")


def dashboard_data(items, errors=(), today=None):
    """Everything the dashboard page shows, as plain JSON: every item with its links, scope,
    questions and body sections, plus the quote log, the ledger and lint's findings."""
    problems, warnings, stale = lint(items, list(errors), today=today)
    lp, lw = lint_loop(items)
    stale_ids = {s.split(":")[0] for s in stale}
    out = []
    for it in sorted(items.values(), key=lambda x: (x.get("type"), x["id"])):
        typ = it.get("type")
        body = it["_body"]
        intro = re.sub(r"\A#\s[^\n]*\n+", "", body.strip() + "\n").split("\n## ")[0].strip()
        intro = "" if intro.startswith("#") else intro
        t = it.get("titles") or {}
        titles = ([["any size", as_list(t.get("default"))]] if t.get("default") else []) + \
                 [[f"{k} people", as_list(v)] for k, v in (t.get("by_size") or {}).items()] + \
                 [[f"industry /{k}/", as_list(v)] for k, v in (t.get("by_industry") or {}).items()]
        f = it.get("firmographics") or {}
        firmo = "; ".join(f"{k.replace('_', ' ')} {', '.join(map(str, as_list(v)))}" for k, v in f.items()
                          if k in ("employees", "business_model", "geographies", "funding_stages", "industries") and v)
        name = str(it.get("name", it["id"]))
        out.append({
            "id": it["id"], "type": typ, "name": name, "status": it.get("status"),
            "short": it.get("internal_name") or re.sub(r"\s*\([^)]*\)", "", name.split(" — ")[-1]),
            "owner": it.get("owner"), "last_confirmed": str(it.get("last_confirmed")), "path": it["_path"],
            "stale": it["_path"] in stale_ids,
            "scope": [] if typ in ("icp", "offering") else as_list(it.get("offerings")),
            "motion": as_list(it.get("motion")),
            "links": {fld: [str(x) for x in as_list(it.get(fld))] for fld in LINKS if it.get(fld)},
            "quotes": as_list(it.get("quotes")),
            "questions": norm_questions(it),
            "sections": sections(body), "intro": intro,
            "inferred": body.count("[INFERRED"),
            "kind": it.get("kind"), "price": it.get("price"), "role": it.get("role"),
            "titles": titles, "titles_flat": " ".join(x for _, xs in titles for x in xs),
            "title_regex": it.get("title_regex"), "detect": as_list(it.get("detect")), "firmo": firmo,
        })
    voice, _ = load_voice()
    sugg, _ = load_suggestions()
    q = [{"id": r["id"], "date": r["date"], "quote": r["quote"], "speaker": r["speaker"], "company": r["company"],
          "category": r["category"], "offering": _ids(r["offering"]), "motion": _ids(r["motion"]),
          "persona": _ids(r["persona"]), "outcome": r["outcome"], "permission": r["permission"], "source": r["source"]}
         for r in voice]
    s = [{"id": r["id"], "date": r["date"], "element": _ids(r["element"]), "change": r["change"],
          "status": r["status"], "reason": r["reason"].strip("—- "), "evidence": r["evidence"]} for r in sugg]
    return {"company": CONFIG.get("company") or os.path.basename(ROOT), "library": CONFIG["library"],
            "generated": (today or date.today()).isoformat(), "motions": MOTIONS, "quote_categories": VOICE_CATEGORIES,
            "items": out, "quotes": q, "suggestions": s,
            "health": {"problems": problems + lp, "warnings": warnings + lw, "stale": stale}}


def write_dashboard(items, out, errors=()):
    """One self-contained HTML page: the template with the library's data inlined. No
    server, no build step; open it in a browser or publish it anywhere static."""
    data = dashboard_data(items, errors)
    blob = json.dumps(data, ensure_ascii=False, default=str).replace("</", "<\\/")
    html = open(DASHBOARD_TEMPLATE, encoding="utf-8").read()
    html = html.replace("__GTM_LIBRARY_TITLE__", f"{data['company']} GTM library").replace("__GTM_LIBRARY_DATA__", blob)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    return data


# ---------------------------------------------------------------- render

def _body(it, depth):
    """An item's prose without its own H1, headings pushed down to sit under `depth`."""
    b = re.sub(r"\A#\s[^\n]*\n+", "", it["_body"].strip() + "\n")
    return re.sub(r"(?m)^(#+) ", lambda m: "#" * (len(m.group(1)) + depth - 2) + " ", b).rstrip()


def render(items):
    """ICP.md, generated. Downstream skills that read the old single file keep working."""
    by = collections.defaultdict(list)
    for it in items.values():
        by[it.get("type")].append(it)
    get = lambda i: items.get(i, {})
    tl = lambda xs: "; ".join(map(str, as_list(xs)))
    active_first = lambda x: (x.get("status") != "active", x["id"])
    lib_rel = CONFIG["library"].rstrip("/") + "/"
    L = ["---", f"title: ICP — generated from {lib_rel}", "type: icp-profile",
         "status: generated", f"generated: {date.today().isoformat()}", "---", "",
         "# ICP (generated)", "",
         f"**Don't edit this file.** It is rebuilt from `{lib_rel}` by `gtm_library.py render`. "
         "Edit the library item named under each heading, then re-render. Titles are separated by semicolons.", "",
         "## Offerings", "", "| Offering | Status | ICPs | Personas |", "|---|---|---|---|"]
    for o in sorted(by["offering"], key=active_first):
        ps = ", ".join(dict.fromkeys(offering_personas(items, o["id"]))) or "—"
        L.append(f"| {o['name']} (`{o['id']}`) | {o['status']} | {', '.join(as_list(o.get('icps')))} | {ps} |")
    L += ["", "# ICPs", ""]
    for icp in sorted(by["icp"], key=active_first):
        f = icp.get("firmographics") or {}
        L += [f"## {icp['name']} (`{icp['id']}`, {icp['status']})", "",
              f"Source: `{icp['_path']}` · last confirmed {icp['last_confirmed']}", ""]
        for k in ("employees", "industries", "geographies", "funding_stages", "business_model", "categories"):
            if f.get(k):
                L.append(f"- **{k.replace('_', ' ')}:** {tl(f[k])}")
        if f.get("any_of"):
            conds = ["; ".join(f"{k.replace('_', ' ')} {tl(v)}" for k, v in c.items()) for c in f["any_of"].values()]
            L.append(f"- **any of:** {' · or · '.join(conds)}")
        L.append(f"- **offerings:** {', '.join(as_list(icp.get('offerings'))) or '—'}")
        only = lambda p: f", {' / '.join(as_list(get(p).get('offerings')))} only" if get(p).get("offerings") else ""
        L.append("- **personas:** " + ", ".join(f"{get(p).get('name', p)} (`{p}`, {get(p).get('role', '?')}{only(p)})"
                                               for p in as_list(icp.get("personas"))))
        L += ["", _body(icp, 3), ""]
        pps = [x for x in map(get, as_list(icp.get("proof_points"))) if x]
        if pps:
            L += ["### Proof points", ""] + [f"- {x.get('claim')} `[{x.get('confidence', '?')}: {x.get('source', '?')}]`" for x in pps] + [""]
        quotes = [x for x in map(get, as_list(icp.get("references"))) if x.get("quote")]
        if quotes:
            L += ["### Voice (verbatim)", ""] + [f"- *\"{x['quote']}\"* — {x['name']}" for x in quotes] + [""]
    L += ["# Personas", ""]
    for p in sorted(by["persona"], key=active_first):
        t = p.get("titles") or {}
        L += [f"## {p['name']} (`{p['id']}`, {p.get('role', '?')})", "",
              f"Source: `{p['_path']}` · last confirmed {p['last_confirmed']} · in ICPs: {', '.join(as_list(p.get('icps')))}"
              + (f" · only when selling: {', '.join(as_list(p.get('offerings')))}" if p.get("offerings") else ""), ""]
        if t.get("default"):
            L.append(f"- **Titles:** {tl(t['default'])}")
        for band, ts in (t.get("by_size") or {}).items():
            L.append(f"  - **{band} employees:** {tl(ts)}")
        for ind, ts in (t.get("by_industry") or {}).items():
            L.append(f"  - **industry /{ind}/:** {tl(ts)}")
        L += ["", _body(p, 3), ""]
    for typ, head in (("angle", "Angles"), ("competitor", "Competitors"), ("trigger", "Triggers"),
                      ("objection", "Objections"), ("alternative", "Alternatives")):
        if not by[typ]:
            continue
        L += [f"# {head}", ""]
        for x in sorted(by[typ], key=active_first):
            meta = [f"Source: `{x['_path']}`", f"last confirmed {x['last_confirmed']}",
                    f"offerings: {', '.join(as_list(x.get('offerings'))) or 'all'}"]
            if x.get("motion"):
                meta.append(f"motion: {', '.join(as_list(x['motion']))}")
            L += [f"## {x['name']} (`{x['id']}`, {x['status']})", "", " · ".join(meta), ""]
            if x.get("detect"):
                L += ["- **Spot it by:** " + tl(x["detect"]), ""]
            L += [_body(x, 3), ""]
    return "\n".join(L)


# ---------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("lint"); s.add_argument("--stale", action="store_true")
    s = sub.add_parser("show"); s.add_argument("id")
    s = sub.add_parser("match")
    s.add_argument("--title", default=""); s.add_argument("--employees"); s.add_argument("--industry"); s.add_argument("--icp")
    s.add_argument("--revenue"); s.add_argument("--funding"); s.add_argument("--offering")
    s = sub.add_parser("questions"); s.add_argument("--icp"); s.add_argument("--persona"); s.add_argument("--offering"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("classify"); s.add_argument("csv")
    s.add_argument("--title-col", default="Title"); s.add_argument("--size-col", default="Employee Size"); s.add_argument("--industry-col", default="Industry"); s.add_argument("--offering")
    s.add_argument("--revenue-col", default="Annual Revenues")
    s.add_argument("--backend", choices=["jev"]); s.add_argument("--out")
    s = sub.add_parser("label", help="label a lead list with personas and ICPs for one offering")
    s.add_argument("csv"); s.add_argument("--offering", required=True)
    s.add_argument("--title-col", default="Title"); s.add_argument("--size-col", default="Employee Size")
    s.add_argument("--industry-col", default="Industry"); s.add_argument("--revenue-col", default="Annual Revenues")
    s.add_argument("--extra-col", help="another column to give the classifier, e.g. a headline or company")
    s.add_argument("--backend", choices=["jev"]); s.add_argument("--out")
    s = sub.add_parser("qualify")
    for f in ("--offering", "--icp", "--persona"):
        s.add_argument(f)
    s.add_argument("--template", action="store_true", help="print a blank answers file for these elements")
    s.add_argument("--answers", help="answers JSON: {element: {question id: {answer, evidence}}}")
    s.add_argument("--state", help="evidence text file; with --backend jev, Jev answers every question from it")
    s.add_argument("--backend", choices=["jev"]); s.add_argument("--json", action="store_true")
    s = sub.add_parser("place")
    for f in ("--title", "--headline", "--offering", "--employees", "--industry", "--icp"):
        s.add_argument(f)
    s.add_argument("--backend", choices=["jev"])
    s = sub.add_parser("brief")
    for f in ("--offering", "--icp", "--persona", "--motion"):
        s.add_argument(f)
    s = sub.add_parser("voice", help="search the quote log")
    for f in ("--category", "--offering", "--motion", "--persona", "--since"):
        s.add_argument(f)
    s.add_argument("--public", action="store_true", help="only quotes cleared for outward use")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("suggestions", help="the suggestions ledger")
    s.add_argument("--status"); s.add_argument("--element")
    s.add_argument("--accept-proposed", action="store_true", help="flip rows still `proposed` to `accepted` (they reached this branch by a merged PR)")
    sub.add_parser("drift", help="sources changed since their element was last confirmed")
    sub.add_parser("extractors", help="the standing questions asked of every call")
    s = sub.add_parser("counts", help="per-offering quotes and suggestions since a date"); s.add_argument("--since", required=True)
    s = sub.add_parser("list")
    for f in ("--type", "--offering", "--motion", "--icp", "--persona"):
        s.add_argument(f)
    s = sub.add_parser("export")
    for f in ("--type", "--offering", "--motion"):
        s.add_argument(f)
    s = sub.add_parser("render"); s.add_argument("--out", default=os.path.join(ROOT, CONFIG["render_to"]))
    s = sub.add_parser("dashboard", help="write the one-page HTML dashboard"); s.add_argument("--out", default=os.path.join(ROOT, CONFIG["dashboard_to"]))
    a = ap.parse_args()

    items, errors = load()
    if a.cmd == "lint":
        problems, warnings, stale = lint(items, errors, a.stale)
        if not a.stale:
            lp, lw = lint_loop(items)
            problems += lp; warnings += lw
        for lbl, xs in (("ERROR", problems), ("warn", warnings), ("stale", stale)):
            for x in xs:
                print(f"{lbl}: {x}")
        print(f"{len(items)} items · {len(problems)} errors · {len(warnings)} warnings · {len(stale)} stale")
        sys.exit(1 if problems else 0)
    if errors:
        sys.exit("\n".join(errors) + "\nrun `lint` first")
    if getattr(a, "offering", None) and items.get(a.offering, {}).get("type") != "offering":
        sys.exit(f"no offering `{a.offering}`")
    if getattr(a, "motion", None) and a.motion not in MOTIONS:
        sys.exit(f"motion `{a.motion}` is not one of {MOTIONS}")
    if getattr(a, "type", None) and a.type not in KINDS.values():
        sys.exit(f"type `{a.type}` is not one of {sorted(KINDS.values())}")
    if a.cmd == "show":
        it = items.get(a.id) or sys.exit(f"no item `{a.id}`")
        print(json.dumps({k: v for k, v in it.items() if not k.startswith("_")}, indent=2, default=str))
        for field in LINKS:
            for ref in as_list(it.get(field)):
                print(f"  {field} -> {ref}: {items.get(ref, {}).get('name', '??')}")
        print(f"\nlinked from: {', '.join(i for i, x in items.items() if any(a.id in as_list(x.get(f)) for f in LINKS)) or '—'}")
    elif a.cmd == "match":
        if a.icp and a.icp not in items:
            sys.exit(f"no ICP `{a.icp}`")
        icps = [(items[a.icp], 9, ["given"])] if a.icp else (
            match_icps(items, a.employees, a.industry, a.revenue, a.funding)
            if (a.employees or a.industry or a.revenue or a.funding) else [])
        if a.offering:
            icps = [x for x in icps if x[0]["id"] in as_list(items[a.offering].get("icps"))]
        if not a.title:
            for it, sc, why in icps:
                print(f"  {sc}  {it['id']:<28} {', '.join(why) or 'no constraint tested'}")
        elif not icps:
            given = a.employees or a.industry or a.revenue or a.funding
            print("No ICP fits these firmographics. Title matches from every ICP:" if given
                  else "No firmographics given, so personas from every ICP:")
            for it, sc, why in match_personas(items, a.title, a.employees, a.industry, offering=a.offering):
                print(f"  {sc}  {it['id']:<28} {', '.join(why)}")
        else:
            rows = [(icp, isc, iwhy, p, psc, pwhy) for icp, isc, iwhy in icps
                    for p, psc, pwhy in match_personas(items, a.title, a.employees, a.industry, icp["id"], a.offering)]
            if not rows:
                print(f"No persona in {', '.join(x[0]['id'] for x in icps)} catches {a.title!r}"
                      + (f" when selling {a.offering}." if a.offering else "."))
                sys.exit(0)
            print("icp score · persona score · icp x persona")
            for icp, isc, iwhy, p, psc, pwhy in rows:
                print(f"  {isc}  {psc}  {icp['id']} x {p['id']:<22} {', '.join(iwhy)}; {', '.join(pwhy)}")
            print("Firmographics can't tell a vendor from a customer. Run `questions` for the pair and check.")
    elif a.cmd == "questions":
        if a.persona and a.persona in items and not serves(items[a.persona], a.offering):
            sys.exit(f"`{a.persona}` is scoped to {', '.join(as_list(items[a.persona].get('offerings')))}, not {a.offering}")
        q = questions(items, a.icp, a.persona, a.offering)
        if a.json:
            print(json.dumps(q, indent=2))
        else:
            for lbl, block in q.items():
                print(f"# {lbl}: {block['name']} ({block['id']})")
                for fit, head in (("good", "qualify_good (yes = fit)"), ("bad", "qualify_bad (yes = not a fit)"), (None, "deep (research only)")):
                    print(f"## {head}")
                    for x in block["questions"]:
                        if x["fit"] == fit:
                            tag = f"[{x['weight']}{', deal-breaker' if x['must'] else ''}] " if fit else ""
                            print(f"- {tag}{x['q']}" + (f"  ({x['why']})" if x.get("why") else ""))
                print()
    elif a.cmd == "classify":
        classify(items, a.csv, a.title_col, a.size_col, a.industry_col, a.offering, a.revenue_col,
                 pick_backend(a.backend), a.out)
    elif a.cmd == "label":
        label(items, a.csv, a.offering, a.title_col, a.size_col, a.industry_col, a.revenue_col, a.out,
              pick_backend(a.backend), a.extra_col)
    elif a.cmd == "qualify":
        ids = [x for x in (a.offering, a.icp, a.persona) if x]
        for x, want in ((a.icp, "icp"), (a.persona, "persona")):
            if x and items.get(x, {}).get("type") != want:
                sys.exit(f"no {want} `{x}`")
        if not ids:
            sys.exit("name at least one of --offering, --icp, --persona")
        if a.template:
            print(json.dumps(answer_template(items, ids), indent=2))
            return
        answers = json.load(open(a.answers)) if a.answers else {}
        if a.state:
            if pick_backend(a.backend, need=bool(a.backend)) != "jev":
                sys.exit("--state needs a backend to read it: pass --backend jev, or have the skill answer and use --answers")
            state = open(a.state, encoding="utf-8").read()
            for eid in ids:
                qs = [q for q in norm_questions(items[eid]) if q["fit"] and q["weight"]]
                have = answers.setdefault(eid, {})
                todo = [q for q in qs if str((have.get(q["id"]) or {}).get("answer", "unknown")) not in ("yes", "no")]
                if todo:
                    try:
                        have.update(answer_with_jev(todo, state))
                    except JevUnavailable as e:
                        print(f"note: {e}; those questions stay unknown", file=sys.stderr)
                        break
        rep = score(items, {eid: answers.get(eid, {}) for eid in ids})
        if a.json:
            print(json.dumps({"report": rep, "answers": answers}, indent=2))
            return
        for eid, r in rep.items():
            verdict = ("RULED OUT by " + ", ".join(r["ruled_out_by"])) if r["ruled_out_by"] else (
                "unconfirmed deal-breakers: " + ", ".join(r["unconfirmed"]) if r["unconfirmed"] else "no deal-breaker failed")
            sc = "no answers" if r["score"] is None else f"{r['score']}/100"
            print(f"{r['type']:<9} {eid:<28} {sc:<11} on {r['answered']} of {r['of']} answered · {verdict}")
    elif a.cmd == "place":
        if not a.title:
            sys.exit("--title is required")
        cands = offering_personas(items, a.offering) if a.offering else [i for i, x in items.items() if x.get("type") == "persona" and x.get("status") != "retired"]
        hits = [h for h in match_personas(items, a.title, a.employees, a.industry, a.icp, a.offering) if h[0]["id"] in cands]
        if hits and hits[0][1] >= 2:
            print(f"{hits[0][0]['id']}  (rules: {', '.join(hits[0][2])})")
        elif pick_backend(a.backend) == "jev":
            try:
                pid, conf = place_with_jev(items, [("x", a.title, a.headline or "")], list(dict.fromkeys(cands)))["x"]
            except JevUnavailable as e:
                print(f"note: {e}", file=sys.stderr)
                print(f"{hits[0][0]['id']}  (rules: regex only; Jev unreachable)" if hits else "none  (rules found nothing; Jev unreachable)")
                return
            sure = conf >= CLASSIFIER["min_confidence"]
            rule = f"; rules said {hits[0][0]['id']} by regex" if hits else "; rules found nothing"
            print(f"{(pid or 'none') if sure else 'unsure'}  (jev {pid or 'none'} at {conf:.2f}{rule})")
        else:
            print(f"{hits[0][0]['id']}  (rules: regex only; pass --backend jev to check)" if hits else "none  (rules found nothing; pass --backend jev to ask)")
    elif a.cmd == "voice":
        if a.category and a.category not in VOICE_CATEGORIES:
            sys.exit(f"category `{a.category}` is not one of {VOICE_CATEGORIES}")
        rows, _ = load_voice()
        sel = voice_select(rows, a.category, a.offering, a.motion, a.persona, a.since, a.public)
        if a.json:
            print(json.dumps([{k: v for k, v in r.items() if not k.startswith("_")} for r in sel], indent=2))
        else:
            for r in sel:
                print(f"{r['date']}  [{r['category']}, {r['permission']}] \"{r['quote']}\" — {r['speaker']}, {r['company']}  ({r['id']})")
            print(f"{len(sel)} of {len(rows)} quotes")
    elif a.cmd == "suggestions":
        if a.accept_proposed:
            print(f"{accept_proposed()} proposed → accepted")
            return
        rows, _ = load_suggestions()
        for r in rows:
            if (a.status and r["status"] != a.status) or (a.element and a.element not in _ids(r["element"])):
                continue
            print(f"{r['date']}  {r['status']:<9} {r['element']:<28} {r['change']}" + (f"  — {r['reason']}" if r["reason"].strip("—- ") else ""))
    elif a.cmd == "drift":
        changed, pages = drift(items)
        print("## Repo sources changed since the element was last confirmed")
        for eid, src, what, log in changed:
            print(f"- {eid}: `{src}` {what}" + "".join(f"\n    {l}" for l in log[:5]))
        print("\n## Offering pages to re-read")
        for eid, url in pages:
            print(f"- {eid}: {url}")
        if not changed and not pages:
            print("nothing")
    elif a.cmd == "extractors":
        for x in EXTRACTORS:
            print(f"- {x['id']}: {x['q']}" + (f"  → quote category `{x['category']}`" if x.get("category") else ""))
    elif a.cmd == "counts":
        for o, c in counts(items, a.since).items():
            cats = ", ".join(f"{k} {v}" for k, v in sorted(c["by_category"].items()))
            print(f"- **{o}**: {c['quotes']} quotes" + (f" ({cats})" if cats else "") + f", {c['suggestions']} suggestions")
    elif a.cmd == "brief":
        if not a.offering:
            sys.exit("--offering is required")
        for x, want in ((a.icp, "icp"), (a.persona, "persona")):
            if x and items.get(x, {}).get("type") != want:
                sys.exit(f"no {want} `{x}`")
        if a.persona and not serves(items[a.persona], a.offering):
            sys.exit(f"`{a.persona}` is scoped to {', '.join(as_list(items[a.persona].get('offerings')))}, not {a.offering}")
        print(brief(items, a.offering, a.icp, a.persona, a.motion))
    elif a.cmd == "list":
        for it in select(items, a.type, a.offering, a.motion, a.icp, a.persona):
            extra = [f"motion {', '.join(as_list(it['motion']))}" if it.get("motion") else "",
                     f"only {', '.join(as_list(it['offerings']))}" if it.get("offerings") and it["type"] not in ("icp",) else ""]
            print(f"  {it['type']:<12} {it['id']:<34} {it.get('name', '')}" + "".join(f" · {e}" for e in extra if e))
    elif a.cmd == "export":
        sel = select(items, a.type, a.offering, a.motion) if (a.type or a.offering or a.motion) else items.values()
        print(json.dumps({x["id"]: agent_view(x) for x in sel}, indent=2, default=str))
    elif a.cmd == "render":
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(render(items))
        print(f"wrote {os.path.relpath(a.out, ROOT)}")
        dash = os.path.join(ROOT, CONFIG["dashboard_to"])
        write_dashboard(items, dash, errors)
        print(f"wrote {os.path.relpath(dash, ROOT)}")
    elif a.cmd == "dashboard":
        d = write_dashboard(items, a.out, errors)
        print(f"wrote {os.path.relpath(a.out, ROOT)}: {len(d['items'])} items, {len(d['quotes'])} quotes, {len(d['suggestions'])} suggestions")


if __name__ == "__main__":
    main()
