# Backlog

Ordered by priority, not by size. P0 items are load-bearing — they get harder to do the
longer real data accumulates. Each item notes why it matters and roughly what it touches.

---

## P0 — Do before logging many drinks

### 1. Stable IDs instead of positional numbers
**Done.** Storage moved from `bar52:v1` (keyed by sequential drink number) to `bar52:v2`
(keyed by slug, e.g. `last-word`, `jungle-bird`). `drink_slug()` in `build.py` derives the
slug from the cocktail name and the build fails on a collision; the displayed number is now
a purely visual index. A one-time migration maps existing numeric keys through the current
build order and leaves `v1` in place as a backup. Restore also accepts v1-shaped export
files. Covered by 18 checks in `smoke-test.mjs`.

*Remaining:* renaming a cocktail still changes its slug and orphans its notes. If that
becomes a real risk, add an explicit `"slug"` override field in `data.py`.

### 2. Move content to JSON
Convert `data.py` into `cocktails.json` and `bottles.json`; have the page fetch them at load.
Recipes become editable without a rebuild, the data becomes consumable by anything else you
build, and diffs in the repo turn readable. Keep `build.py` for the shell and CSS.
*Note:* `fetch()` on JSON needs a server — fine on Pages, breaks on `file://`. Either accept
that or inline the JSON as a `<script type="application/json">` block.

### 3. Keep the video links verified
**Done.** All 52 drinks carry a tutorial link, and the check is automated.

`check-videos.mjs` resolves every link through YouTube's oEmbed endpoint
(`https://www.youtube.com/oembed?url=...&format=json`, which 404s on a deleted or private
video and reports the channel a video actually belongs to).
`.github/workflows/video-links.yml` runs it on the 1st of each month and on demand: a dead
link, or one that resolves to a channel the page does not claim, opens a `video-links` issue
— or comments on the open one, so a lasting problem does not spawn a new issue every month —
and the issue closes itself once the links resolve again. Title changes are reported but never
fail the run. If every link fails at once it exits without opening anything, since that means
the network was blocked rather than the page rotting overnight.

Two caveats worth remembering:
- The original 38 links were checked against oEmbed by hand. The 14 added later were sourced
  by hand and have *not* been through that check — the first scheduled run will be the first
  time they are verified.
- Still open: find a full tutorial to replace the Fish House Punch Short.

---

### 3b. Keep the smoke test green
`smoke-test.mjs` exercises the tracker against a real DOM via jsdom — marking, rating,
filtering, persistence, unmarking, and the v1 &rarr; v2 slug migration. Run it after any
change to `tracker.py`, and put it in CI:

```bash
npm install jsdom && node smoke-test.mjs
```

Coverage gaps worth adding: a full export/import round-trip through the real `FileReader`,
the merge logic on restore, and the reset confirm path.

---

## P1 — Highest value for actually using this

### 4. "What can I make tonight?"
Let each appendix bottle be marked as owned, then surface which of the 52 are fully makeable
right now, and which are one bottle short (naming the bottle). This connects the recipe data
and the appendix data that already exist and is probably the single most useful feature on
this list.
*Depends on:* a machine-readable ingredient → bottle mapping, which `ANCHOR_MAP` already
approximates but should be promoted into the data rather than inferred by string matching.

### 5. Shopping list generator
Pick a set of upcoming drinks, get back the bottles you don't own, split into an OHLQ trip and
a grocery/wine-shop trip, each line linked. Printable or shareable as text.

### 6. Homemade components section
Orgeat, grenadine, honey syrup, honey-ginger syrup, demerara syrup, raspberry syrup, falernum,
bacon fat-wash, milk clarification are all referenced but never specified. They deserve their
own section with quantities, yield, and fridge life, cross-linked from the recipes that use them.

### 7. Batch and scaling calculator
Multiply any spec by N with output in ml, and a batching mode that adds a water allowance in
place of shaking dilution. Directly useful for the Fish House Punch and the Clarified Milk Punch,
and for making two of anything at once.

### 8. Offline support
A service worker so the page works in a basement bar with no signal. Small change, high
practical payoff, and it makes the "phone on the counter" use case reliable.

---

## P2 — Worth doing once the above settles

### 9. Two profiles
Separate tracks so you each keep your own ratings and notes, with a toggle in the dashboard and
a combined view. Cheap version of the shared-state problem below.

### 10. Genuinely shared state
The real fix for two people on two devices. Options, roughly in order of effort:
- **Supabase free tier** — a real table, anonymous auth or a shared key. Most capable.
- **A GitHub Gist via the API** — no new service, but needs a token in the browser, so only
  acceptable for a private repo or a scoped token.
- **Commit the export JSON to the repo** — zero infrastructure, manual, works today.
Worth deciding deliberately; each adds a dependency the current file doesn't have.

### 11. Ingredient search
"Show everything that uses Campari" or "everything I can make with what's open." Complements
item 4 and needs the same structured ingredient data.

### 12. Print stylesheet
One clean recipe card per page, without the tracking controls or navigation. Useful for taping a
spec to a cabinet door.

### 13. Season tags and a weekly suggestion
The report already recommends sequencing by season. Encode that as data and let the page suggest
this week's drink from what's unmade and in season.

### 14. Merge review on import
Restore currently merges blind. Showing what will change before committing avoids surprise
concatenated notes.

---

## P3 — Someday

- **Technique primers** — shaking vs stirring and why, dilution, egg-white handling, fat-washing,
  clarification, swizzling. Short, linked from the drinks that need them.
- **Glassware and tools appendix** — swizzle stick, Lewis bag, fine strainer, large-cube mould,
  the coupe/collins/Nick & Nora distinction.
- **Substitution matrix** — generalise what the Chartreuse entries do by hand: for each specialty
  bottle, what works instead and how the drink shifts.
- **Year two** — a bench of alternates for drinks that don't land, and 52 more once this is done.
- **Accessibility and Lighthouse pass** — keyboard navigation through the filters and star
  ratings, contrast check on the muted greens, focus order through the tracking controls.
- ~~**Build on push**~~ — **done.** `.github/workflows/ci.yml` rebuilds on every push and fails
  if the committed `docs/index.html` differs from a fresh build, so a stale page cannot ship.

---

## Deliberately not doing

- **A framework.** The page is one file with no dependencies and loads instantly. React or a
  static site generator would add a toolchain for no gain at this size.
- **User accounts.** Two people. A shared key or an exported file covers it.
- **Auto-scraping recipe specs.** Specs legitimately vary between sources; the value here is in
  a human having chosen one and noted where it's contested.
