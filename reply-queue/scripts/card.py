"""Render queue cards for a chat surface from JSON, so the layout is never typed by hand.

The card shape is a page of prose in SKILL.md, and a run that types it freehand gets
it right most times. Most is not enough: one reply carded over five days came out in
four shapes — the draft properly fenced, the draft in single backticks (Slack renders
that as red inline code), the fence glued to the text, and the quote swallowing the
line below it because the blank line after it was missing. None of that survives a
template.

Usage:  python3 scripts/card.py cards.json

cards.json is one card object or a list. Each card is printed followed by a line
holding only ===END CARD===; post each block as its own message, verbatim.

Shape is chosen by the fields, per SKILL.md step 6: pass draft_link for Shape A (the
body lives in the mailbox, the card links it and quotes one preview line), or message
for Shape B (nowhere else to get the text, so the card fences it). Passing both is an
error, because then there are two copies of the reply and one of them is stale.

Fields:
  name        required
  profile     profile URL, optional
  title       optional; "title unknown" if missing
  company     optional
  email       optional
  campaign    required, the registry slug
  kind        "Reply", "Nudge" or "Hand"
  days        whole days since the anchor message (0 prints "today")
  quote       their words, one line (for a nudge, your last message)
  send_from   the channel they replied on; omitted on a Shape A card
  draft_link  link to the draft in the mailbox            → Shape A
  preview     one line of the drafted reply, quoted       → Shape A
  message     the whole drafted reply, fenced             → Shape B
  notes       required
  new_since   true when this person replied again after an earlier card
  mailbox     name for the mailbox in "Draft is in your <mailbox>"
"""
import json, sys, textwrap

RULE = "━" * 30
WRAP = 90  # chat code blocks do not wrap; a longer line is a horizontal scrollbar


def fence(text):
    out = []
    for para in text.strip("\n").split("\n"):
        if len(para) <= WRAP:
            out.append(para)
        else:
            out.extend(textwrap.wrap(para, WRAP, break_long_words=False, break_on_hyphens=False))
    return "\n".join(out).replace("```", "'''")


def render(c):
    for key in ("name", "campaign", "kind", "notes"):
        if not c.get(key):
            sys.exit(f"card for {c.get('name', '?')}: missing {key}")
    kind = c["kind"].capitalize()
    if kind not in ("Reply", "Nudge", "Hand"):
        sys.exit(f"card for {c['name']}: kind must be Reply, Nudge or Hand")
    if c.get("draft_link") and c.get("message"):
        sys.exit(f"card for {c['name']}: a linked draft is not also fenced on the card")

    name = f"<{c['profile']}|{c['name']}>" if c.get("profile") else c["name"]
    who = c.get("title") or "title unknown"
    if c.get("company"):
        who += f", {c['company']}"

    days = c.get("days")
    if kind == "Hand":
        since = "today" if not days else f"{days} days"
    else:
        whose = "your" if kind == "Nudge" else "their"
        since = "today" if not days else f"{days} day{'s' if days != 1 else ''} since {whose} message"

    head = f"*{name}* · {who}"
    if c.get("email"):
        head += f" · <mailto:{c['email']}>"

    lines = [RULE]
    if c.get("new_since"):
        lines.append("New since the last card:")
    lines += [head, f"Campaign: {c['campaign']}", f"*{kind}* · {since}"]

    quote = " ".join((c.get("quote") or "").split())
    if quote:
        lines += [f'> "{quote.strip(chr(34))}"', ""]  # blank line ends the blockquote

    if c.get("draft_link"):
        lines.append(f"Draft is in your {c.get('mailbox', 'mail')}: {c['draft_link']}")
        if c.get("preview"):
            lines += [f"> _{' '.join(c['preview'].split())}_", ""]
    else:
        if c.get("send_from"):
            lines.append(f"Send from: {c['send_from']}")
        if c.get("message"):
            lines += ["```", fence(c["message"]), "```", ""]

    lines.append(f"Notes: {' '.join(c['notes'].split())}")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    data = json.load(open(sys.argv[1]))
    for card in data if isinstance(data, list) else [data]:
        print(render(card))
        print("===END CARD===")
