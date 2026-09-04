# Backlog

Ordered by priority, not by size. P0 items are load-bearing — they get harder to do the
longer real data accumulates. Each item notes why it matters and roughly what it touches.

---

## P0 — Do before logging many drinks

### 1. Stable IDs instead of positional numbers
Saved notes key off the sequential drink number, which `build.py` assigns from position in
`GROUPS`. Insert or reorder a drink and every note after it silently attaches to the wrong
cocktail. Switch the storage key to a slug (`last-word`, `jungle-bird`), keep the displayed
number as a purely visual index, and ship a one-time migration that maps existing numeric
keys to slugs using the current order.
*Touches:* `build.py` (slug generation), `tracker.py` (storage layer), plus a migration step.
**This blocks safe reordering, so it should land first.**

### 2. Move content to JSON
Convert `data.py` into `cocktails.json` and `bottles.json`; have the page fetch them at load.
Recipes become editable without a rebuild, the data becomes consumable by anything else you
build, and diffs in the repo turn readable. Keep `build.py` for the shell and CSS.
*Note:* `fetch()` on JSON needs a server — fine on Pages, breaks on `file://`. Either accept
that or inline the JSON as a `<script type="application/json">` block.

### 3. Keep the video links verified
**Done once, needs automating.** All 38 links were checked against YouTube's oEmbed endpoint
(`https://www.youtube.com/oembed?url=...&format=json`, which 404s on dead or private videos):
every one resolves, sits on the claimed channel, and has a title matching its drink. Links rot,
so wire that check into a monthly GitHub Action that opens an issue when one breaks. Remaining
content work: fill the 14 "no strong video match" gaps, and find a full tutorial to replace the
Fish House Punch Short.

---

### 3b. Keep the smoke test green
`smoke-test.mjs` exercises the tracker against a real DOM via jsdom — marking, rating,
filtering, persistence, unmarking. Run it after any change to `tracker.py`, and put it in CI:

```bash
npm install jsdom && node smoke-test.mjs
```

Coverage gaps worth adding: export/import round-trip, the merge logic on restore, and the
reset confirm path.

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
- **Real OHLQ URLs** — links currently route through a site-scoped Google search because OHLQ's
  search is JavaScript-rendered and its query parameter couldn't be verified. If you find it
  (check the network tab on a search), swap `ohlq_url()` for one less hop.
- **Accessibility and Lighthouse pass** — keyboard navigation through the filters and star
  ratings, contrast check on the muted greens, focus order through the tracking controls.
- **Build on push** — a GitHub Action that regenerates the HTML when the data changes, so nobody
  ships a stale page.

---

## Deliberately not doing

- **A framework.** The page is one file with no dependencies and loads instantly. React or a
  static site generator would add a toolchain for no gain at this size.
- **User accounts.** Two people. A shared key or an exported file covers it.
- **Auto-scraping recipe specs.** Specs legitimately vary between sources; the value here is in
  a human having chosen one and noted where it's contested.
