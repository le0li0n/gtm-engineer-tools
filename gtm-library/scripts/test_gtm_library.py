#!/usr/bin/env python3
"""Tests for gtm_library.py. Standard library only: python3 test_gtm_library.py"""
import json, os, shutil, subprocess, sys, tempfile, unittest
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
EXAMPLE = os.path.join(PLUGIN, "templates", "example-library")
SCRIPT = os.path.join(HERE, "gtm_library.py")

_TMP = tempfile.mkdtemp()
os.environ["GTM_LIBRARY_ROOT"] = _TMP
sys.path.insert(0, HERE)
import gtm_library as g  # noqa: E402

TODAY = date(2026, 9, 16)


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)


def edit(path, old, new):
    text = open(path, encoding="utf-8").read()
    assert old in text, (path, old)
    open(path, "w", encoding="utf-8").write(text.replace(old, new, 1))


class Repo:
    """A temp repo holding a copy of the example library."""

    def __init__(self, config=None):
        self.root = tempfile.mkdtemp()
        self.lib = os.path.join(self.root, "lib-dir")
        shutil.copytree(EXAMPLE, self.lib)
        json.dump(config or {"library": "lib-dir"}, open(os.path.join(self.root, ".gtmlibrary.json"), "w"))

    def items(self):
        return g.load(self.lib)

    def cli(self, *args):
        env = dict(os.environ, GTM_LIBRARY_ROOT=self.root)
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, env=env)


class Frontmatter(unittest.TestCase):
    def parse(self, fm):
        return g.parse_frontmatter(f"---\n{fm}\n---\nbody")[0]

    def test_scalars_and_types(self):
        d = self.parse("a: hello\nb: 3\nc: true\nd: null\ne: 'it''s'\nf: \"x: y\"")
        self.assertEqual(d, {"a": "hello", "b": 3, "c": True, "d": None, "e": "it's", "f": "x: y"})

    def test_flow_list_with_quoted_comma(self):
        self.assertEqual(self.parse('t: [A, "B, C", \'D\']')["t"], ["A", "B, C", "D"])

    def test_nested_maps_and_block_lists(self):
        d = self.parse("x:\n  y:\n    '1-50':\n      - Founder\n    51-200: [RevOps]\n  z: 2")
        self.assertEqual(d, {"x": {"y": {"1-50": ["Founder"], "51-200": ["RevOps"]}, "z": 2}})

    def test_empty_key_then_sibling(self):
        self.assertEqual(self.parse("a:\nb: 1"), {"a": None, "b": 1})

    def test_comments_ignored(self):
        self.assertEqual(self.parse("# note\na: 1\n  # indented note\nb: 2"), {"a": 1, "b": 2})

    def test_regex_backslashes_survive(self):
        self.assertEqual(self.parse(r"r: '(?i)\b(vp|head)\b'")["r"], r"(?i)\b(vp|head)\b")

    def test_errors(self):
        for bad in ("a: [1, 2", "a:\n  - x\n  y: 1", "- x", "a: 1\n   b: 2", "a:\n\t- x"):
            with self.assertRaises(ValueError, msg=bad):
                self.parse(bad)
        with self.assertRaises(ValueError):
            g.parse_frontmatter("---\na: 1\n")

    def test_no_frontmatter(self):
        self.assertEqual(g.parse_frontmatter("just text"), ({}, "just text"))


class Sizes(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(g.parse_range("51-200"), (51, 200))
        self.assertEqual(g.parse_range("5,001+"), (5001, float("inf")))
        with self.assertRaises(ValueError):
            g.parse_range("big")

    def test_headcount(self):
        self.assertEqual(g.headcount("51-200 employees"), 51)
        self.assertEqual(g.headcount("Self-employed"), 1)
        self.assertEqual(g.headcount("10,001+ employees"), 10001)
        self.assertIsNone(g.headcount(""))

    def test_size_band(self):
        self.assertEqual(g.size_band("11-50 employees"), (11, 50))
        self.assertEqual(g.size_band("10,001+ employees"), (10001, float("inf")))
        self.assertEqual(g.size_band("Self-employed"), (1, 1))
        self.assertEqual(g.size_band(120), (120, 120))
        self.assertIsNone(g.size_band(""))

    def test_a_band_fits_if_it_could_be_in_range(self):
        # 11-50 might be 20 or more, so a 20-500 ICP keeps it; only a band wholly below is out.
        self.assertTrue(g.in_ranges((11, 50), ["20-500"]))
        self.assertFalse(g.in_ranges((2, 10), ["20-500"]))
        self.assertFalse(g.in_ranges((501, 1000), ["20-500"]))
        self.assertTrue(g.in_ranges(20, ["20-500"]))
        self.assertFalse(g.in_ranges(19, ["20-500"]))

    def test_money(self):
        self.assertEqual(g.money("10M-25M"), 10e6)
        self.assertEqual(g.money("$500K"), 500e3)
        self.assertEqual(g.money("1B-10B"), 1e9)
        self.assertIsNone(g.money(""))


class Lint(unittest.TestCase):
    def test_example_is_clean(self):
        items, errors = Repo().items()
        problems, warnings, stale = g.lint(items, errors, today=TODAY)
        self.assertEqual((problems, warnings, stale), ([], [], []))

    def test_stale(self):
        items, errors = Repo().items()
        _, _, stale = g.lint(items, errors, today=date(2027, 1, 1))
        self.assertEqual(len(stale), len(items))

    def test_broken_link_wrong_type_and_bad_id(self):
        r = Repo()
        p = os.path.join(r.lib, "personas", "controller.md")
        s = open(p).read().replace("icps: [mid-market-finance-team]", "icps: [nope, close-platform]").replace("id: controller", "id: cfo")
        open(p, "w").write(s)
        problems, _, _ = g.lint(*r.items(), today=TODAY)
        text = "\n".join(problems)
        self.assertIn("`nope` doesn't exist", text)
        self.assertIn("is a offering, not a icp", text)
        self.assertIn("doesn't match the filename", text)

    def test_listed_title_must_match_regex(self):
        r = Repo()
        p = os.path.join(r.lib, "personas", "controller.md")
        edit(p, "[Controller, VP Finance", "[Controller, Treasurer, VP Finance")
        _, warnings, _ = g.lint(*r.items(), today=TODAY)
        self.assertTrue(any("'Treasurer' isn't matched" in w for w in warnings), warnings)

    def test_bad_regexes(self):
        r = Repo()
        p = os.path.join(r.lib, "icps", "mid-market-finance-team.md")
        s = open(p).read().replace("exclude_industry_regex: '(?i)accounting|bookkeeping'", "exclude_industry_regex: '(unclosed'")
        s = s.replace("research:", "person_score:\n  function:\n    ops:\n      points: 5\n      regex: '[bad'\nresearch:", 1)
        open(p, "w").write(s)
        problems, _, _ = g.lint(*r.items(), today=TODAY)
        self.assertTrue(any("exclude_industry_regex doesn't compile" in x for x in problems), problems)
        self.assertTrue(any("person_score.function.ops regex" in x for x in problems), problems)

    def test_reciprocal_warning(self):
        r = Repo()
        p = os.path.join(r.lib, "personas", "controller.md")
        edit(p, "icps: [mid-market-finance-team]", "icps: []")
        _, warnings, _ = g.lint(*r.items(), today=TODAY)
        self.assertTrue(any("doesn't list this icp back" in w for w in warnings), warnings)

    def test_parse_error_reported_not_raised(self):
        r = Repo()
        write(r.lib, "personas/broken.md", "---\nid: broken\n  bad: indent\n---\n")
        items, errors = r.items()
        self.assertTrue(errors and "broken.md" in errors[0])


class Match(unittest.TestCase):
    def setUp(self):
        self.items, _ = Repo().items()

    def ids(self, hits):
        return [h[0]["id"] for h in hits]

    def test_any_of_passes_on_either_condition(self):
        self.assertEqual(self.ids(g.match_icps(self.items, "201-500 employees")), ["mid-market-finance-team"])
        self.assertEqual(self.ids(g.match_icps(self.items, "101-200 employees", revenue="25M-75M")), ["mid-market-finance-team"])

    def test_any_of_fails_when_every_known_condition_fails(self):
        self.assertEqual(g.match_icps(self.items, "150", revenue="1M-5M"), [])
        # A band that could reach 200 might be 200+, so it stays in.
        self.assertTrue(g.match_icps(self.items, "101-200 employees", revenue="1M-5M"))

    def test_unknown_values_dont_disqualify(self):
        hits = g.match_icps(self.items, industry="Software Development")
        self.assertEqual(self.ids(hits), ["mid-market-finance-team"])
        self.assertEqual(hits[0][1], 0)

    def test_size_and_exclusion(self):
        self.assertEqual(g.match_icps(self.items, "11-50 employees"), [])
        self.assertEqual(g.match_icps(self.items, "201-500 employees", "Accounting"), [])

    def test_persona_scores(self):
        by_size = g.match_personas(self.items, "Close Manager", "501-1,000 employees")
        self.assertEqual((by_size[0][0]["id"], by_size[0][1]), ("finance-ops-manager", 3))
        default = g.match_personas(self.items, "Senior Accountant", "5,001+")
        self.assertEqual(default[0][1], 2)
        regex_only = g.match_personas(self.items, "Head of Accounting Systems", "150")
        self.assertEqual(regex_only[0][1], 1)

    def test_exclude_wins(self):
        self.assertEqual(self.ids(g.match_personas(self.items, "Assistant Controller", "150")), ["finance-ops-manager"])
        self.assertEqual(g.match_personas(self.items, "CFO"), [])

    def test_icp_scope(self):
        self.assertEqual(self.ids(g.match_personas(self.items, "Controller", icp="mid-market-finance-team")), ["controller"])

    def test_questions(self):
        q = g.questions(self.items, "mid-market-finance-team", "controller")
        self.assertEqual(set(q), {"company", "person"})
        self.assertTrue(q["company"]["qualify_good"] and q["person"]["deep"])


class OfferingScope(unittest.TestCase):
    """A persona can be limited to some offerings: a recruiter matters when selling placement,
    not when selling seats, even at the same company."""

    def setUp(self):
        self.r = Repo()
        write(self.r.lib, "offerings/hiring-service.md",
              "---\nid: hiring-service\ntype: offering\nname: Hiring\nstatus: planned\nlast_confirmed: 2026-09-16\n"
              "kind: service\nsources: [hiring.md]\nicps: [mid-market-finance-team]\n---\n"
              "## Deliverables\n\nx\n\n## Challenges addressed\n\nx\n\n## Why us\n\nx\n")
        write(self.r.lib, "personas/recruiter.md",
              "---\nid: recruiter\ntype: persona\nname: Recruiter\nstatus: planned\nlast_confirmed: 2026-09-16\n"
              "icps: [mid-market-finance-team]\nofferings: [hiring-service]\nrole: champion\n"
              "titles:\n  default: [Finance Recruiter]\ntitle_regex: '(?i)recruit|talent'\n"
              "research:\n  qualify_good:\n    - Do they own the finance req?\n---\n")
        icp = os.path.join(self.r.lib, "icps", "mid-market-finance-team.md")
        edit(icp, "offerings: [close-platform", "offerings: [hiring-service, close-platform")
        edit(icp, "personas: [", "personas: [recruiter, ")
        self.items, _ = self.r.items()

    def ids(self, hits):
        return [h[0]["id"] for h in hits]

    def test_lint_clean(self):
        problems, warnings, _ = g.lint(self.items, [], today=TODAY)
        self.assertEqual((problems, warnings), ([], []))

    def test_scoped_persona_only_for_its_offering(self):
        self.assertEqual(self.ids(g.match_personas(self.items, "Finance Recruiter", offering="hiring-service")), ["recruiter"])
        self.assertEqual(g.match_personas(self.items, "Finance Recruiter", offering="close-platform"), [])
        self.assertEqual(self.ids(g.match_personas(self.items, "Finance Recruiter")), ["recruiter"])

    def test_unscoped_persona_serves_every_offering(self):
        self.assertEqual(self.ids(g.match_personas(self.items, "Controller", offering="hiring-service")), ["controller"])

    def test_offering_never_reaches_personas_outside_its_icps(self):
        write(self.r.lib, "personas/auditor.md",
              "---\nid: auditor\ntype: persona\nname: Auditor\nstatus: active\nlast_confirmed: 2026-09-16\n"
              "icps: []\ntitle_regex: '(?i)recruit'\n---\n")
        items, _ = self.r.items()
        self.assertIn("auditor", self.ids(g.match_personas(items, "Finance Recruiter")))
        self.assertEqual(self.ids(g.match_personas(items, "Finance Recruiter", offering="hiring-service")), ["recruiter"])

    def test_offering_personas(self):
        self.assertIn("recruiter", g.offering_personas(self.items, "hiring-service"))
        self.assertNotIn("recruiter", g.offering_personas(self.items, "close-platform"))

    def test_scope_to_an_offering_no_icp_sells_warns(self):
        write(self.r.lib, "offerings/unsold.md",
              "---\nid: unsold\ntype: offering\nname: Unsold\nstatus: planned\nlast_confirmed: 2026-09-16\n---\n")
        edit(os.path.join(self.r.lib, "personas", "recruiter.md"), "offerings: [hiring-service]", "offerings: [unsold]")
        _, warnings, _ = g.lint(*self.r.items(), today=TODAY)
        self.assertTrue(any("never applies" in w for w in warnings), warnings)

    def test_questions_include_the_offering(self):
        q = g.questions(self.items, "mid-market-finance-team", "recruiter", "close-platform")
        self.assertEqual(list(q), ["offering", "company", "person"])

    def test_cli(self):
        out = self.r.cli("match", "--title", "Finance Recruiter", "--employees", "300", "--offering", "close-platform").stdout
        self.assertIn("No persona in mid-market-finance-team catches 'Finance Recruiter' when selling close-platform", out)
        out = self.r.cli("match", "--title", "Finance Recruiter", "--employees", "300", "--offering", "hiring-service").stdout
        self.assertIn("x recruiter", out)
        res = self.r.cli("questions", "--persona", "recruiter", "--offering", "close-platform")
        self.assertIn("scoped to hiring-service", res.stderr)
        self.assertIn("no offering `nope`", self.r.cli("match", "--title", "x", "--offering", "nope").stderr)

    def test_render_shows_scope(self):
        text = g.render(self.items)
        self.assertIn("recruiter", [l for l in text.splitlines() if l.startswith("| Hiring")][0])
        self.assertNotIn("recruiter", [l for l in text.splitlines() if "`close-platform`" in l and l.startswith("|")][0])
        self.assertIn("champion, hiring-service only", text)
        self.assertIn("only when selling: hiring-service", text)


class Model(unittest.TestCase):
    """Phase 1: weighted questions, new element types, motions, tags, headings, select, export."""

    def setUp(self):
        self.r = Repo({"library": "lib-dir", "tag_groups": ["region"]})
        self.items, _ = self.r.items()

    def test_list_item_maps_and_prose_with_colons(self):
        d = g.parse_frontmatter("---\nq:\n  - Hiring: who owns it?\n  - id: x\n    q: Is it real?\n    weight: 9\n  - plain\n---\n")[0]
        self.assertEqual(d["q"], ["Hiring: who owns it?", {"id": "x", "q": "Is it real?", "weight": 9}, "plain"])

    def test_questions_normalised(self):
        qs = {q["id"]: q for q in g.norm_questions(self.items["close-platform"])}
        self.assertEqual((qs["multi-entity"]["weight"], qs["multi-entity"]["must"], qs["multi-entity"]["fit"]), (9, True, "good"))
        bad = [q for q in qs.values() if q["fit"] == "bad"][0]
        self.assertEqual((bad["weight"], bad["must"]), (5, False))
        deep = [q for q in g.norm_questions(self.items["mid-market-finance-team"]) if q["fit"] is None]
        self.assertTrue(deep and all(q["weight"] == 0 for q in deep))

    def test_question_weight_checked(self):
        edit(os.path.join(self.r.lib, "offerings", "close-platform.md"), "weight: 9", "weight: 12")
        problems, _, _ = g.lint(*self.r.items(), today=TODAY)
        self.assertTrue(any("weight `12` isn't a whole number 0-10" in x for x in problems), problems)

    def test_missing_heading_and_bad_motion(self):
        p = os.path.join(self.r.lib, "objections", "erp-does-this.md")
        edit(p, "## Reframe", "## Answer")
        edit(p, "motion: [new]", "motion: [upsell]")
        problems, warnings, _ = g.lint(*self.r.items(), today=TODAY)
        self.assertTrue(any("no `## Reframe` section" in w for w in warnings), warnings)
        self.assertTrue(any("motion `upsell`" in x for x in problems), problems)

    def test_tags_checked_against_config(self):
        edit(os.path.join(self.r.lib, "competitors", "ledgerly.md"), "dossiers: []", "dossiers: []\ntags:\n  region: [NA]\n  tier: [1]")
        out = self.r.cli("lint").stdout  # the config is read at import, so go through the CLI
        self.assertIn("tag group `tier`", out)
        self.assertNotIn("tag group `region`", out)

    def test_angle_sells_one_offering_and_trigger_needs_detect(self):
        edit(os.path.join(self.r.lib, "angles", "second-entity-close.md"), "offerings: [close-platform]", "offerings: []")
        edit(os.path.join(self.r.lib, "triggers", "second-entity.md"), "detect:\n", "detect_old:\n")
        _, warnings, _ = g.lint(*self.r.items(), today=TODAY)
        self.assertTrue(any("an angle sells exactly one offering" in w for w in warnings), warnings)
        self.assertTrue(any("no `detect` list" in w for w in warnings), warnings)

    def test_offering_kind_and_sources(self):
        p = os.path.join(self.r.lib, "offerings", "close-platform.md")
        edit(p, "kind: product", "kind: media")
        edit(p, "sources: [https://example.com/pricing]\n", "")
        _, warnings, _ = g.lint(*self.r.items(), today=TODAY)
        self.assertTrue(any("kind `media`" in w for w in warnings), warnings)
        self.assertTrue(any("should cite `sources`" in w for w in warnings), warnings)

    def test_sections(self):
        s = g.sections("# Title\n\nintro\n\n## Why now\n\nBecause.\n\n### Who feels it\n\n- CFO\n")
        self.assertEqual(s, {"Why now": "Because.", "Who feels it": "- CFO"})

    def test_select_by_type_offering_and_motion(self):
        ids = lambda xs: [x["id"] for x in xs]
        self.assertEqual(ids(g.select(self.items, "objection", "close-platform", "new")), ["erp-does-this"])
        self.assertEqual(g.select(self.items, "objection", motion="renewal"), [])
        # A trigger with no offerings scope applies to every offering.
        self.assertEqual(ids(g.select(self.items, "trigger", "close-platform")), ["second-entity"])

    def test_select_by_offering_narrows_structural_types(self):
        write(self.r.lib, "offerings/other.md", "---\nid: other\ntype: offering\nname: Other\nstatus: active\nlast_confirmed: 2026-09-16\n---\n")
        items, _ = self.r.items()
        got = {x["id"] for x in g.select(items, offering="close-platform") if x["type"] in ("offering", "icp", "persona")}
        self.assertEqual(got, {"close-platform", "mid-market-finance-team", "controller", "finance-ops-manager"})
        self.assertEqual([x["id"] for x in g.select(items, "persona", "other")], [])

    def test_export_is_the_agent_view(self):
        data = json.loads(self.r.cli("export", "--type", "angle").stdout)
        self.assertEqual(list(data), ["second-entity-close"])
        self.assertIn("Key messages", data["second-entity-close"]["sections"])
        full = json.loads(self.r.cli("export").stdout)
        self.assertEqual(full["close-platform"]["research"][0]["id"], "multi-entity")

    def test_list_and_questions_cli(self):
        out = self.r.cli("list", "--offering", "close-platform", "--motion", "new").stdout
        self.assertIn("erp-does-this", out)
        self.assertIn("second-entity-close", out)
        q = self.r.cli("questions", "--offering", "close-platform").stdout
        self.assertIn("[9, deal-breaker] Do they close books", q)
        self.assertIn("motion `later`", self.r.cli("list", "--motion", "later").stderr)

    def test_render_includes_new_types(self):
        text = g.render(self.items)
        for part in ("# Angles", "# Competitors", "# Triggers", "# Objections", "# Alternatives", "**Spot it by:**"):
            self.assertIn(part, text)


class Use(unittest.TestCase):
    """Phase 2: scoring, templates, briefs, and the classifier with Jev stubbed out."""

    def setUp(self):
        self.r = Repo()
        self.items, _ = self.r.items()

    def test_score_leaves_unknowns_out_and_rules_out_on_a_deal_breaker(self):
        good = g.score(self.items, {"close-platform": {"multi-entity": {"answer": "yes"}}})["close-platform"]
        self.assertEqual((good["score"], good["answered"], good["ruled_out_by"]), (100, 1, []))
        bad = g.score(self.items, {"close-platform": {"multi-entity": {"answer": "no"}}})["close-platform"]
        self.assertEqual((bad["score"], bad["ruled_out_by"]), (0, ["multi-entity"]))
        none = g.score(self.items, {"close-platform": {}})["close-platform"]
        self.assertEqual((none["score"], none["unconfirmed"]), (None, ["multi-entity"]))

    def test_bad_fit_questions_score_on_no(self):
        qid = [q["id"] for q in g.norm_questions(self.items["close-platform"]) if q["fit"] == "bad"][0]
        r = g.score(self.items, {"close-platform": {"multi-entity": {"answer": "yes"}, qid: {"answer": "no"}}})["close-platform"]
        self.assertEqual((r["score"], r["answered"]), (100, 2))
        r = g.score(self.items, {"close-platform": {"multi-entity": {"answer": "yes"}, qid: {"answer": "yes"}}})["close-platform"]
        self.assertEqual(r["score"], round(100 * 9 / 14))

    def test_score_rejects_unknown_ids(self):
        with self.assertRaises(SystemExit):
            g.score(self.items, {"close-platform": {"nope": {"answer": "yes"}}})

    def test_template_lists_only_scored_questions(self):
        t = g.answer_template(self.items, ["mid-market-finance-team"])["mid-market-finance-team"]
        self.assertTrue(t and all(v["answer"] == "unknown" for v in t.values()))
        deep = {q["id"] for q in g.norm_questions(self.items["mid-market-finance-team"]) if q["fit"] is None}
        self.assertFalse(deep & set(t))

    def test_brief(self):
        b = g.brief(self.items, "close-platform", "mid-market-finance-team", "controller", "new")
        for part in ("# Call brief", "[9, deal-breaker]", "## Why now", "## What they'll say", "*Reframe:*",
                     "## What they do instead", "## Who we're up against", "## Angles that have run", "## Find out first"):
            self.assertIn(part, b)
        self.assertNotIn("## What they'll say", g.brief(self.items, "close-platform", motion="renewal"))

    def test_brief_prefers_the_offering_section_and_keeps_bullets(self):
        p = os.path.join(self.r.lib, "competitors", "ledgerly.md")
        edit(p, "## Why we win\n", "## Why we win (close-platform)\n\n- Live in weeks.\n- Built for mid-market.\n\n## Why we win\n")
        items, _ = self.r.items()
        b = g.brief(items, "close-platform")
        self.assertIn("- *Why we win:*\n  - Live in weeks.\n  - Built for mid-market.", b)
        self.assertNotIn("Mid-market teams live in weeks, not a six-month", b.split("## Why we lose")[0].split("Why we win")[1])

    def test_per_offering_heading_meets_the_requirement_and_is_checked(self):
        p = os.path.join(self.r.lib, "competitors", "ledgerly.md")
        edit(p, "## Why we lose\n", "## Why we lose (close-platform)\n")
        write(self.r.lib, "offerings/other.md", "---\nid: other\ntype: offering\nname: Other\nstatus: active\nlast_confirmed: 2026-09-16\nkind: service\nsources: [x]\n---\n## Deliverables\nx\n## Challenges addressed\nx\n## Why us\nx\n")
        edit(p, "## How they position\n", "## How they position (other)\n\nx\n\n## How they position\n")
        _, warnings, _ = g.lint(*self.r.items(), today=TODAY)
        self.assertFalse(any("no `## Why we lose`" in w for w in warnings), warnings)
        self.assertTrue(any("`How they position (other)` is for an offering this item isn't scoped to" in w for w in warnings), warnings)

    def test_brief_shows_a_repeated_question_once(self):
        icp = os.path.join(self.r.lib, "icps", "mid-market-finance-team.md")
        edit(icp, "    - Do they run more than one legal entity?", "    - id: multi-entity\n      q: Do they close books monthly across more than one entity?")
        items, _ = self.r.items()
        b = g.brief(items, "close-platform", "mid-market-finance-team")
        self.assertEqual(b.count("Do they close books monthly across more than one entity?"), 1)

    def test_answer_with_jev_keeps_not_stated_and_low_confidence_unknown(self):
        fake = {"a": {"choice": "yes", "confidence": 0.9}, "b": {"choice": "not_stated", "confidence": 0.99},
                "c": {"choice": "no", "confidence": 0.4}}
        orig = g.jev
        g.jev = lambda state, qs, key=None: fake
        try:
            out = g.answer_with_jev([{"id": k, "q": k} for k in fake], "evidence")
        finally:
            g.jev = orig
        self.assertEqual({k: v["answer"] for k, v in out.items()}, {"a": "yes", "b": "unknown", "c": "unknown"})

    def test_place_with_jev_batches_and_maps_none(self):
        calls = []

        def fake(state, qs, key=None):
            calls.append(len(qs))
            return {k: {"choice": "none" if i % 2 else "controller", "confidence": 0.8} for i, k in enumerate(qs)}
        orig, n = g.jev, g.CLASSIFIER["batch"]
        g.jev, g.CLASSIFIER["batch"] = fake, 3
        try:
            out = g.place_with_jev(self.items, [(i, f"t{i}", "") for i in range(7)], ["controller", "finance-ops-manager"])
        finally:
            g.jev, g.CLASSIFIER["batch"] = orig, n
        self.assertEqual(calls, [3, 3, 1])
        self.assertEqual((out[0][0], out[1][0]), ("controller", None))

    def test_unreachable_jev_raises_jev_unavailable(self):
        import urllib.error, urllib.request
        orig_open, orig_key = urllib.request.urlopen, g._env_key
        def boom(*a, **k):
            raise urllib.error.URLError("Tunnel connection failed: 403 Forbidden")
        urllib.request.urlopen, g._env_key = boom, (lambda name: "k")
        try:
            with self.assertRaises(g.JevUnavailable) as cm:
                g.jev("s", {"q": {"type": "noul", "instructions": "x"}})
            self.assertIn("couldn't reach Jev", str(cm.exception))
        finally:
            urllib.request.urlopen, g._env_key = orig_open, orig_key

    def test_env_key_reads_dotenv_without_env_var(self):
        write(self.r.root, ".env", "OTHER=1\nTEST_GTM_KEY='sekret'\n")
        orig = g.ROOT
        g.ROOT = self.r.root
        try:
            self.assertEqual(g._env_key("TEST_GTM_KEY"), "sekret")
            self.assertIsNone(g._env_key("MISSING_GTM_KEY"))
        finally:
            g.ROOT = orig

    def test_cli_qualify_and_brief(self):
        p = os.path.join(self.r.root, "answers.json")
        json.dump({"close-platform": {"multi-entity": {"answer": "no"}}}, open(p, "w"))
        out = self.r.cli("qualify", "--offering", "close-platform", "--answers", p).stdout
        self.assertIn("RULED OUT by multi-entity", out)
        self.assertIn("needs a backend", self.r.cli("qualify", "--offering", "close-platform", "--state", p).stderr)
        self.assertIn("# Call brief", self.r.cli("brief", "--offering", "close-platform").stdout)
        self.assertIn("pass --backend jev", self.r.cli("place", "--title", "Head of Accounting Systems").stdout)


class Loop(unittest.TestCase):
    """Phase 3: the quote log, the suggestions ledger, drift, counts."""

    def setUp(self):
        self.r = Repo()
        self.items, _ = self.r.items()

    def test_example_logs_are_clean(self):
        self.assertEqual(g.lint_loop(self.items, self.r.lib), ([], []))
        voice, _ = g.load_voice(self.r.lib)
        self.assertEqual(len(voice), 2)

    def test_escaped_pipe_stays_in_the_quote(self):
        self.assertEqual(g._cells("| a | it's 50\\|50 | c |"), ["a", "it's 50|50", "c"])

    def test_voice_problems(self):
        p = os.path.join(self.r.lib, "voice", "2026-09.md")
        edit(p, "| objection | close-platform | new | controller | open | internal |",
             "| gripe | nope | later | controller | open | secret |")
        edit(p, "| q-2026-09-10-acme-1 |", "| q-2026-09-03-northwind-1 |")
        problems, _ = g.lint_loop(self.items, self.r.lib)
        text = "\n".join(problems)
        for part in ("category `gripe`", "offering `nope`", "motion `later`", "permission must be", "also on line"):
            self.assertIn(part, text)

    def test_row_with_wrong_cell_count(self):
        write(self.r.lib, "voice/2026-10.md", "| " + " | ".join(g.VOICE_COLS) + " |\n|---|\n| too | few |\n")
        problems, _ = g.lint_loop(self.items, self.r.lib)
        self.assertTrue(any("2 cells, expected 12" in x for x in problems), problems)

    def test_quotes_link_must_resolve(self):
        edit(os.path.join(self.r.lib, "objections", "erp-does-this.md"), "motion: [new]", "motion: [new]\nquotes: [q-2026-09-03-northwind-1, q-missing]")
        problems, _ = g.lint_loop(*[self.r.items()[0]], self.r.lib)
        self.assertEqual([x for x in problems if "q-missing" in x and "isn't in the quote log" in x].__len__(), 1)

    def test_voice_select(self):
        rows, _ = g.load_voice(self.r.lib)
        self.assertEqual([r["id"] for r in g.voice_select(rows, category="objection")], ["q-2026-09-03-northwind-1"])
        self.assertEqual([r["id"] for r in g.voice_select(rows, public=True)], ["q-2026-09-10-acme-1"])
        self.assertEqual(g.voice_select(rows, since="2026-09-11"), [])

    def test_rejected_needs_a_reason_and_accept_proposed_flips(self):
        p = os.path.join(self.r.lib, "suggestions.md")
        edit(p, "| rejected | One 60-person buyer isn't a pattern; revisit at three. |", "| rejected | — |")
        open(p, "a").write("| s-2026-09-17-1 | 2026-09-17 | controller | Add \"Head of Close\" to titles | proposed | — | call 2026-09-16 |\n")
        _, warnings = g.lint_loop(self.items, self.r.lib)
        self.assertTrue(any("should say why" in w for w in warnings), warnings)
        self.assertEqual(g.accept_proposed(self.r.lib), 1)
        rows, _ = g.load_suggestions(self.r.lib)
        self.assertEqual([r["status"] for r in rows], ["accepted", "rejected", "accepted"])
        self.assertEqual(rows[2]["change"], 'Add "Head of Close" to titles')

    def test_counts(self):
        c = g.counts(self.items, "2026-09-01", self.r.lib)
        self.assertEqual(c["close-platform"]["quotes"], 2)
        self.assertEqual(c["close-platform"]["suggestions"], 2)

    def test_drift_lists_offering_pages_and_changed_repo_sources(self):
        subprocess.run(["git", "init", "-q", self.r.root], check=True)
        write(self.r.root, "notes/pricing.md", "v1")
        env = dict(os.environ, GIT_AUTHOR_DATE="2026-09-20T12:00:00", GIT_COMMITTER_DATE="2026-09-20T12:00:00")
        for cmd in (["add", "-A"], ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "pricing notes"]):
            subprocess.run(["git", "-C", self.r.root, *cmd], check=True, env=env)
        edit(os.path.join(self.r.lib, "use-cases", "close-books-faster.md"), "status: active\n", "status: active\nsources: [notes/pricing.md]\n")
        out = self.r.cli("drift").stdout
        self.assertIn("close-platform: https://example.com/pricing", out)
        self.assertIn("close-books-faster: `notes/pricing.md` changed", out)

    def test_cli(self):
        self.assertIn("1 of 2 quotes", self.r.cli("voice", "--category", "pain").stdout)
        self.assertIn("rejected", self.r.cli("suggestions", "--status", "rejected").stdout)
        self.assertIn("objection:", self.r.cli("extractors").stdout)
        self.assertIn("**close-platform**: 2 quotes", self.r.cli("counts", "--since", "2026-09-01").stdout)


class Dashboard(unittest.TestCase):
    def test_writes_one_self_contained_page(self):
        r = Repo({"library": "lib-dir", "company": "Tallyworks"})
        out = r.cli("dashboard").stdout
        self.assertIn("11 items, 2 quotes, 2 suggestions", out)
        html = open(os.path.join(r.lib, "dashboard.html"), encoding="utf-8").read()
        self.assertNotIn("__GTM_LIBRARY_DATA__", html)
        self.assertIn("<title>Tallyworks GTM library</title>", html)
        blob = html.split('id="lib-data">', 1)[1].split("</script>", 1)[0]
        data = json.loads(blob.replace("<\\/", "</"))
        self.assertEqual(len(data["items"]), 11)
        angle = [i for i in data["items"] if i["id"] == "second-entity-close"][0]
        self.assertEqual(angle["links"]["triggers"], ["second-entity"])
        self.assertIn("Approach", angle["sections"])

    def test_script_close_in_content_cannot_end_the_data_block(self):
        r = Repo()
        edit(os.path.join(r.lib, "objections", "erp-does-this.md"), "## Reframe\n", "## Reframe\n\nNever write </script> here.\n")
        r.cli("dashboard")
        html = open(os.path.join(r.lib, "dashboard.html"), encoding="utf-8").read()
        blob = html.split('id="lib-data">', 1)[1]
        self.assertLess(blob.index("<\\/script>"), blob.index("</script>"))


class Cli(unittest.TestCase):
    def test_lint_render_classify_export(self):
        r = Repo({"library": "lib-dir", "render_to": "out/ICP.md"})
        res = r.cli("lint")
        self.assertIn("0 errors", res.stdout)
        self.assertEqual(r.cli("render").returncode, 0)
        rendered = open(os.path.join(r.root, "out", "ICP.md")).read()
        for part in ("# ICPs", "# Personas", "Close Manager", "any of:", "generated from lib-dir/"):
            self.assertIn(part, rendered)
        write(r.root, "buyers.csv", "Title,Employee Size,Industry,Annual Revenues\nClose Manager,501-1000 employees,Software,50M-100M\nChef,11-50 employees,Restaurants,1M-5M\n")
        out = r.cli("classify", os.path.join(r.root, "buyers.csv"), "--offering", "close-platform").stdout
        self.assertIn("mid-market-finance-team x finance-ops-manager", out)
        self.assertIn("Chef", out)
        data = json.loads(r.cli("export").stdout)
        self.assertIn("controller", data)

    def test_lint_exit_code_on_error(self):
        r = Repo()
        write(r.lib, "icps/x.md", "---\nid: y\ntype: icp\nname: X\nstatus: live\nlast_confirmed: soon\n---\n")
        res = r.cli("lint")
        self.assertEqual(res.returncode, 1)
        self.assertIn("status `live`", res.stdout)
        self.assertIn("isn't a date", res.stdout)

    def test_default_library_path_without_config(self):
        root = tempfile.mkdtemp()
        shutil.copytree(EXAMPLE, os.path.join(root, "gtm-library"))
        env = dict(os.environ, GTM_LIBRARY_ROOT=root)
        res = subprocess.run([sys.executable, SCRIPT, "lint"], capture_output=True, text=True, env=env)
        self.assertIn("11 items", res.stdout)

    def test_competitor_dossiers_checked_against_competitors_dir(self):
        r = Repo({"library": "lib-dir", "competitors_dir": "comp"})
        p = os.path.join(r.lib, "competitors", "ledgerly.md")
        edit(p, "dossiers: []", "dossiers: [0926-ledgerly]")
        self.assertIn("`0926-ledgerly` has no file in comp/", r.cli("lint").stdout)
        write(r.root, "comp/0926-ledgerly.md", "x")
        self.assertIn("0 errors", r.cli("lint").stdout)

    def test_competitor_link_to_a_research_file_warns_not_errors(self):
        r = Repo({"library": "lib-dir", "competitors_dir": "comp"})
        write(r.root, "comp/0926-ledgerly.md", "x")
        edit(os.path.join(r.lib, "offerings", "close-platform.md"), "competitors: [ledgerly]", "competitors: [0926-ledgerly]")
        out = r.cli("lint").stdout
        self.assertIn("is a research file; link a competitor element", out)
        self.assertIn("0 errors", out)

    def test_match_messages(self):
        r = Repo()
        self.assertIn("No ICP fits", r.cli("match", "--title", "Controller", "--employees", "12").stdout)
        self.assertIn("No firmographics given", r.cli("match", "--title", "Controller").stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
