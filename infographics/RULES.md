# infographic-render — learned rules

Rules this skill has earned. Read before writing a spec; add to it when the same mistake happens twice (Charlie Hills' rule: a mistake made twice becomes permanent). Each rule says what went wrong, and the fix.

## Copy

1. **The headline states the finding, not the topic.** "The SaaSpocalypse was already fading", not "SaaSpocalypse trend". A reader who never opens the caption should still get the point. (All five creator studies.)
2. **One highlighted word or short phrase per title**, and it is the idea the post teaches. Mark it `[[like this]]`. Never highlight a whole title.
3. **Every number traces to a source**, stated in `note` on the image. No source, no number. Estimates say so on the graphic.
4. **Reword before whitelisting.** When the spellchecker flags a real-but-obscure word ("ownable"), prefer plainer copy over adding it to `wordlist.txt`. Whitelist only names and product terms.
5. **Hyphenated title words can break at the hyphen** ("Comment-to- / get"). If it looks bad in the render, rephrase the title.
6. **Cut copy before shrinking type.** If the check says text was shrunk below about 92%, trim words or drop an item; don't accept small type.

## Layout

7. **Cycle diagrams: arrows must be visible between cards.** Early renders drew arcs under the cards and hid the arrowheads. The layout script now clips arcs to the gaps; if a ring has more than 6 stages, check the arrows by eye.
8. **Fixed canvases must not have dead bands.** Cards that stretched to full height left 40% of the split graphic empty. The renderer now grows text into spare space (up to 130%) and centers the rest.
9. **Uneven dates need a time axis.** Milestones at irregular dates on an evenly spaced axis distort the slope. Use `"time": true` in trend data.
10. **Label positions must not touch axis ticks.** The first-value label now sits beside the point on the side the line isn't heading.
11. **Growing text can make positioned cards collide.** The fit loop treats card overlap like overflow.

## Review

12. **Passing checks is not done.** The automated checks passed on graphics with hidden arrows and empty bands. Always look at the full-size PNG and the 360px preview before calling it done.
13. **Look at the phone preview first.** Most people see the graphic at about 360px wide; if the title and the highlighted word don't read there in two seconds, the graphic fails no matter how the full size looks.

## Learned on the first real topic

14. **Pull numbers from the chapter that cites the source, not from a summary.** The playbook summarized "561% more reach" as "roughly 5.6x"; 561% more is about 6.6x as much. Use the source's own wording on the graphic.
15. **Row labels are set in uppercase, which mangles mixed-case words** ("DMs" became "DMS"). Pick a label that survives uppercase ("Messages").
16. **Control title breaks with `\n`** when balanced wrapping still splits a sentence badly ("The founder talks. The / agent…").
17. **Don't squeeze a variant that fails the overflow check.** Four stats with sources don't fit a square; drop the variant rather than shrink the type.
