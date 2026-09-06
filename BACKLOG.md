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
**Done.** Every buying-guide row has an "I have this" checkbox; the panel under the dashboard
lists what is makeable now and what is one bottle short, naming the bottle. Drinks already
made are counted separately, under "made before, ready again", so "ready to make now" means
new to you.

The dependency was real: `ANCHOR_MAP` could not be computed against, so it was promoted into
`ingredients.py` as `MAP` + `PANTRY` and now drives both the jump links and the requirements.
That fixed three latent bugs on the way — `gin` matching inside `ginger`, only the first match
in a line ever resolving, and bare `rye` / `aged blended rum` / `Jamaican dark rum` matching
nothing at all.

Requirements are OR-groups, so `bourbon or rye` is satisfied by either. Pantry items never
count. Owned bottles are stored under `bar52:bottles:v1` and ride along in export/restore.

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
Separate tracks so everyone keeps their own ratings and notes, with a toggle in the dashboard
and a combined view. Cheap version of the shared-state problem below.

### 9b. Keep the Supabase project awake
**Done.** `.github/workflows/keepalive.yml` runs `keepalive.py` every three days, well inside the
7-day pause window, and on demand. A ping that cannot get through opens a `supabase`-labelled
issue rather than failing silently — a silent failure would mean the project pauses anyway and
nobody notices until a sync fails on someone's phone. The issue closes itself when the ping
succeeds again.

The retries are the wake mechanism: a paused project takes about 30 seconds to come back and the
waking request may itself time out. Four attempts, but never on a 4xx, which will not fix itself.
`keepalive.test.py` covers all of that against a stubbed network, including the
wakes-on-third-attempt case, and runs in CI.

Config comes from `supabase.py` rather than repository secrets, deviating from what this item
originally said: both values are already public in the page, so secrets would have added setup
steps and a second copy to keep in sync for no security gain.

Remaining risk: GitHub disables scheduled workflows in repositories inactive for 60 days. If this
repo goes quiet that long, the schedule stops and the project pauses regardless.

---

### 10. Genuinely shared state
**Done, via Supabase.** Each profile can hold a 26-character sync code; entering it on another
device gives that device the same notes. The page talks to two `SECURITY DEFINER` RPC functions
with plain `fetch` — no SDK, so the file stays self-contained.

Local-first: `localStorage` remains authoritative, and a sync pulls, merges, writes locally,
then pushes. The merge is a union rather than last-write-wins, so two devices that both logged a
drink keep both, and a note edited on each keeps both texts. A failed sync leaves local data
untouched.

The key ships in the public page, so `anon` has no table privileges at all — RLS alone would let
anyone list the table and harvest codes. See `schema.sql`.

Still open here: a code is a bearer token, so it is convenience-grade rather than secret-grade;
and there is no merge review before a sync lands (item 14).

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
- **Hide the top bar on scroll down** — it costs ~52px of every phone screen. Showing it again
  on scroll up is the usual pattern; worth it only if the bar starts feeling intrusive.
- **Accessibility and Lighthouse pass** — keyboard navigation through the filters and star
  ratings, contrast check on the muted greens, focus order through the tracking controls.
- ~~**Build on push**~~ — **done.** `.github/workflows/ci.yml` rebuilds on every push and fails
  if the committed `docs/index.html` differs from a fresh build, so a stale page cannot ship.

---

## Deliberately not doing

- **A framework.** The page is one file with no dependencies and loads instantly. React or a
  static site generator would add a toolchain for no gain at this size.
- **User accounts.** A handful of friends, not a service. Initials plus a sync code covers it;
  see item 10 for what that does and does not protect.
- **Auto-scraping recipe specs.** Specs legitimately vary between sources; the value here is in
  a human having chosen one and noted where it's contested.
