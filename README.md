# 52 Weeks Behind the Bar

A single-page cocktail curriculum: 52 drinks in 11 flavour families, with progress
tracking, notes, OHLQ availability links and shelf photos. Static — no backend,
no dependencies. Host it on GitHub Pages as-is.

**Live:** <https://jhester599.github.io/craft-cocktail-curriculum/>

## Files

| File | What it is |
|---|---|
| `docs/index.html` | The built page. Generated; do not edit. |
| `docs/synccheck.html` | Generated sync diagnostic. Only built when `supabase.py` is configured. |
| `docs/start.html` | Generated onboarding guide. Its sync sections disappear when sync is off. |
| `data.py` | **Content source.** All 52 cocktails (ingredients, method, video, note) and the whole bottle appendix. Edit here to change recipes or brands. |
| `tracker.py` | The progress/notes UI — CSS, dashboard markup, and the localStorage JavaScript. |
| `build.py` | Renders `data.py` + `tracker.py` into the HTML. Owns the page CSS, metric conversion, link generation and anchor mapping. |
| `ohlq.py` | **Ohio Liquor link data.** Product and category paths for the buying guide, plus the wave-name → appendix-item map. Contains no logic. |
| `ingredients.py` | **Ingredient → bottle map.** The ordered keyword table behind both the in-recipe jump links and the "what can I make tonight?" requirements. Order matters; see the module docstring. |
| `supabase.py` | **Sync config.** Project URL and publishable key. Both are public by design; leave `URL` empty to build with sync off. |
| `start.py` | Generates `docs/start.html`, the "Start here" guide linked from the profile row. |
| `keepalive.py` | Pings Supabase so the free-tier project does not pause. Standard library only. |
| `synccheck.py` | Generates `docs/synccheck.html`, a diagnostic page that exercises the sync backend from a real browser. |
| `schema.sql` | The Supabase table and the `pull`/`push`/`ping` functions. Run once in the SQL editor. Explains the security model. |
| `check-videos.mjs` | Checks every video link on the built page against YouTube's oEmbed endpoint. Run monthly by CI; `npm run check:videos` to run it by hand. |

## Build

```bash
python3 build.py          # or: npm run build
```

No Python packages required. Writes `docs/index.html` and prints a count of cocktails and
bottle links.

```bash
npm install               # jsdom, for the test only
npm test                  # 133 tracker checks + 14 link-checker checks
npm run serve             # http://localhost:8000
```

## Deployment

The site is served by GitHub Pages at
<https://jhester599.github.io/craft-cocktail-curriculum/>.

Configured under Settings → Pages → Source: *Deploy from a branch*, Branch: `main` / `docs`.
Pushing to `main` redeploys automatically — there is no deploy workflow, because Pages serves
the committed `docs/index.html` directly. The `docs/.nojekyll` file stops Jekyll from touching
the output.

Since the served file is the committed one, a push whose `docs/index.html` is out of date with
`data.py` would ship a stale page. That is what the CI staleness gate below exists to prevent.

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request:

1. `npm ci` — installs jsdom, the only dev dependency.
2. `python3 build.py` — regenerates the page.
3. **Staleness gate** — `git diff --quiet -- docs/`. Because Pages serves the *committed*
   HTML, editing `data.py` without rebuilding would silently ship a stale site. The check
   covers the whole directory, so `synccheck.html` cannot drift either. The job fails with the offending diff if the committed page does not match a
   fresh build. Fix it by running `python3 build.py` and committing the result.
4. `npm test` — the 133 jsdom checks plus 14 covering the link checker.
5. `python3 keepalive.test.py` — 12 checks on the Supabase keep-alive, no network needed.

The build is deterministic: same inputs, byte-identical output, no timestamps.

`.github/workflows/video-links.yml` runs on the 1st of each month, and on demand:

- `check-videos.mjs` resolves all 52 video links through YouTube's oEmbed endpoint,
  which 404s on a deleted or private video and reports the channel a video really
  belongs to.
- A dead link, or one that resolves to a channel the page does not claim, opens an
  issue labelled `video-links` — or comments on the existing one, so a persistent
  problem does not produce a new issue every month. The issue closes itself once
  everything resolves again.
- Title changes are reported but never fail the run; channels rename videos, and a
  monthly false alarm is how a check gets ignored.
- If *every* link fails at once the run exits 2 and opens nothing, on the grounds
  that 52 simultaneously dead videos means the network was blocked, not that the
  page rotted overnight.

`check-videos.test.mjs` drives all of that against a mocked endpoint, so the logic is
covered without depending on YouTube being reachable.

## How it works

- **Numbering** is assigned sequentially at build time from the order of `GROUPS`, so
  reordering or adding a drink renumbers everything automatically. The number is
  *only* a visual label.
- **Identity** is the slug, generated by `drink_slug()` in `build.py` from the cocktail
  name (`Last Word` &rarr; `last-word`, `Vieux Carré` &rarr; `vieux-carre`). It is what
  `data-id` carries and what saved notes key off, so drinks can be reordered or
  inserted freely. The build asserts slugs are unique and fails if two collide.
  Renaming a cocktail changes its slug and orphans its notes &mdash; if you rename one,
  migrate the key by hand.
- **Metric amounts** are generated, not stored. `add_metric()` in `build.py` rewrites
  `¾ oz` into `¾ oz (22.5 ml)` using a 30 ml jigger convention. Never hand-write ml
  into `data.py`.
- **Recipe → appendix links** and **bottle requirements** both come from `MAP` in
  `ingredients.py`: an ordered list of (keyword, appendix item name) pairs. This replaced
  the old `ANCHOR_MAP`, which linked only the *first* match in a line and matched on bare
  substrings — so `gin` matched inside `ginger`, and "bourbon or rye" lost half its
  meaning. `resolve_line()` in `build.py` now claims non-overlapping, word-boundary spans,
  most specific keyword first, so `"aged Jamaican rum"` still has to precede any bare
  `"rum"` entry. Appendix row ids are slugified from the item name, so renaming an
  appendix item breaks its inbound links unless `ingredients.MAP` is updated to match.

  Two build assertions keep this honest: every word of every ingredient line must be
  claimed by `MAP` or by `PANTRY` (the fresh/storecupboard list), and every item `MAP`
  names must exist as an appendix row. A new recipe naming something unknown fails the
  build rather than quietly producing wrong requirements.

- **What can I make tonight?** Each buying-guide row carries an "I have this" checkbox.
  The panel under the dashboard lists what is fully makeable and what is one bottle short,
  naming the bottle. Requirements are OR-groups — the Boulevardier's `bourbon or rye` is
  satisfied by either — computed at build time from the recipe text and baked into the
  page as `REQS`. Pantry items (citrus, simple syrup, egg white, soda) are never
  requirements, so they can never block a drink.
- **OHLQ links** are real ohlq.com URLs, held in `ohlq.py` and applied by `ohlq_url()`
  in three tiers: an exact `PRODUCTS` page for a bottle if one is known, else the
  `CATEGORIES` browse page for its appendix item, else the original
  `site:ohlq.com` Google search. Currently 14 product links and 139 category links,
  with no bottle left on the search fallback.

  **33 distinct URLs were opened by hand on 2026-09-04 and every one resolved**, which
  also corrected two mappings: Campari sits under `aperitif`, not `amaro`, and aged
  Jamaican rum under `dark`, not `gold`. One URL added while making those corrections —
  the Appleton Estate 12 product page — postdates that pass and has not been opened.
  Nothing is verified at build time —
  ohlq.com is unreachable from the build environment, so paths come from indexed
  search results rather than a live request. To re-check after edits, list the
  distinct URLs the page actually produces:

  ```bash
  python3 -c "import re,io;print('\n'.join(sorted({m.replace('&amp;','&') for m in re.findall(r'href=\"(https://www\.ohlq\.com[^\"]+)\"', io.open('docs/index.html',encoding='utf-8').read())})))"
  ```
 Category paths are the sturdier half — they recur across
  independent searches, follow one scheme, and survive a product being renamed or
  delisted. Product slugs cannot be derived from a brand name (`Smith &amp; Cross` lives
  at `smith-cross-traditional-jamaica-rum`), so `PRODUCTS` is small on purpose and only
  holds bottles whose page title unambiguously matched. If one turns out to 404, delete
  the entry: that bottle falls back to its category page and nothing else breaks.
- **NON_OHLQ** in `build.py` lists appendix items Ohio does not sell through state
  agencies (under 21% ABV, or not a spirit). Those render a "grocery / wine shop" tag
  instead of an availability link.
- **Video links** cover all 52 drinks. 38 were gathered from search results and checked
  against YouTube's oEmbed endpoint; the remaining 14 were sourced by hand and added
  later, and have *not* been through that check (YouTube is unreachable from the build
  environment). `data.py` still defines `NO_VIDEO`, and `cocktail_html()` still renders a
  "No strong video match found" note for it, so a drink added without a video degrades
  rather than breaking.

## Tracking data

Stored in `localStorage` under the key `bar52:v2:<initials>`, shaped as:

```json
{ "black-manhattan": { "made": true, "date": "Sep 4, 2026", "rating": 4, "note": "..." } }
```

Keys are cocktail slugs, so reordering or inserting drinks is safe &mdash; notes stay with
their cocktail no matter what number it is displayed as.

**Profiles.** Storage is namespaced per set of initials, so several people can share one
device without overwriting each other: `bar52:v2:JRH` and `bar52:bottles:v1:JRH`, with
`bar52:profiles` listing them and `bar52:current` remembering the selection. Initials are up
to three letters. A brand-new browser is asked for them on first load; dismissing that prompt
falls back to a profile called `YOU`, renameable from the picker. The prompt only appears when
the browser is genuinely empty — a visitor whose pre-profile notes are about to be adopted has
been using the site for months and is not asked.

On the first load under this scheme, anything already saved under the un-namespaced
`bar52:v2` / `bar52:bottles:v1` is **adopted** into that first profile rather than stranded,
and the old keys are left in place as a backup. Adoption never overwrites a profile that
already holds data, so it cannot re-run and clobber newer notes.

This is per-device separation and not privacy: anyone using the device can switch profiles and
read the notes.

## Onboarding

`docs/start.html` explains the tracking model to someone who has just been sent the link:
initials are a label rather than a login, and a sync code is a long string you type into a
second device. Neither is guessable from looking at the page. It is linked as **Start here**
next to the profile picker, emphasised until the visitor has notes or a sync code and quiet
afterwards.

It is generated, so its sync sections vanish (and its sections renumber) when `supabase.py`
is blank, rather than describing a feature that is not there. It is a separate page rather
than a modal so the URL can be sent along with the site link.

## Cross-device sync

Each profile can hold a **sync code** — 26 random characters, generated in the browser, stored
at `bar52:code:<initials>`. Enter the same code on another device and both see the same notes.
The code is the identity *and* the password: it names a row that cannot be enumerated.

`docs/index.html` talks to Supabase with plain `fetch` against two RPC endpoints. No SDK, no
toolchain — the page is still one self-contained file; what it gains is a *service* dependency,
not a library one.

**Local-first.** `localStorage` stays authoritative. A sync pulls the remote payload, merges it
into what is already here, writes that locally, then pushes the merged result. Merging is a
union — made and rated are OR'd, ratings take the max, and notes edited on both devices are
kept and joined rather than one silently winning. If the network is down, the project is
paused, or the call fails for any reason, local data is untouched and the page says so; nothing
is lost, the sync just has not happened yet.

Sync runs on load when a code is present, four seconds after any change, and on the **Sync now**
button.

**The security model** is in `schema.sql`, and it matters because the page is public: the
publishable key ships inside `docs/index.html` where anyone can read it. So `anon` holds no
privileges on the table at all. Row-level security alone would not be enough — a policy cannot
see the client's `WHERE` clause, so any select grant would let someone list every row and
harvest every code. Access goes through `SECURITY DEFINER` functions instead, and knowing a
code is the only way in.

What this is not: a code is a bearer token. Anyone holding one can read and write that
person's notes. Convenience-grade, not secret-grade.

**Checking it actually works.** The test suite drives sync against a mocked `fetch`, which proves
the merge logic but nothing about the network: CORS from the Pages origin, PostgREST accepting
the argument names, the grants behaving as intended. None of that can be checked from a build
environment that cannot reach supabase.co. So `docs/synccheck.html` runs those five checks from
whatever browser you open it in — including a phone — and reports each one:

    https://jhester599.github.io/craft-cocktail-curriculum/synccheck.html

It writes one throwaway row under a random code, names that code so you can delete it, and never
touches a real profile. The check that matters most is the last: a direct read of the `shelves`
table must be **refused**. If it returns rows, `anon` has a grant it should not and anyone with
the key could enumerate every sync code.

**Keeping it awake.** A free-tier project pauses after 7 days without database activity, and a
paused project refuses syncs until it is restored. `.github/workflows/keepalive.yml` runs
`keepalive.py` every three days to prevent that, and opens a `supabase`-labelled issue if the
ping cannot get through — a silent failure would mean the project pauses anyway and nobody finds
out until a sync fails on someone's phone.

The retry in that script is the mechanism, not politeness: a paused project takes about 30
seconds to wake, and the request that wakes it may itself time out. It retries four times, but
never retries a 4xx, which will not fix itself.

Config comes from `supabase.py`, not repository secrets. Both values are already public — they
ship inside `docs/index.html`, which is exactly why `schema.sql` gives `anon` no table
privileges — so secrets would add setup steps and a second place to keep in sync for no gain.

One catch: **GitHub disables scheduled workflows in repositories with no activity for 60 days.**
If the repo goes quiet that long, re-enable it from the Actions tab or the project will pause
regardless.

**Setup:** run `schema.sql` in the Supabase SQL editor, put the project URL and publishable key
in `supabase.py`, rebuild.

Owned bottles live per profile, under `bar52:bottles:v1:<initials>`, shaped as
`{ "b-campari": true }` where the key is the appendix row's DOM id. It is a separate key
because it describes the shelf rather than the drinks, and losing one should never take
the other with it. Export/restore carries it as a `bottles` field; an older export without
that field leaves the shelf untouched rather than clearing it.

**Migration from `bar52:v1`.** v1 keyed entries off the sequential drink number. On first
load the tracker reads v1, maps each numeric key through the current build order
(`SLUGS[n-1]`), and writes the result to v2. It runs only when v2 is absent, so it happens
exactly once. **`bar52:v1` is deliberately left in place** as a pre-migration backup and is
not touched by "Clear everything". Keys that are not numbers in range (already-slug keys,
anything unrecognised) are carried across unchanged rather than dropped.

Because the mapping depends on build order, migrate *before* reordering `GROUPS` &mdash; the
only way to read positional keys is against the order that wrote them.

Export/Restore round-trips this object wrapped in `{app, version, saved, entries}`, now at
`version: 2`. Restore accepts either shape: a v1 file with numeric keys is mapped through
the same order before merging. Restore merges rather than overwrites.

## Known next steps

- Merge review before a sync lands, so a restore cannot surprise you with concatenated notes.
- Separate profiles per bartender.
- Moving cocktail data to JSON so the page can fetch it and edits skip the rebuild.
- Print stylesheet; service worker for offline use.
