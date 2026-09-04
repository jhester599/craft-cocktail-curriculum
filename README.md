# 52 Weeks Behind the Bar

A single-page cocktail curriculum: 52 drinks in 11 flavour families, with progress
tracking, notes, OHLQ availability links and shelf photos. Static — no backend,
no dependencies. Host it on GitHub Pages as-is.

## Files

| File | What it is |
|---|---|
| `docs/index.html` | The built page — the only file that gets served. Generated; do not edit. |
| `data.py` | **Content source.** All 52 cocktails (ingredients, method, video, note) and the whole bottle appendix. Edit here to change recipes or brands. |
| `tracker.py` | The progress/notes UI — CSS, dashboard markup, and the localStorage JavaScript. |
| `build.py` | Renders `data.py` + `tracker.py` into the HTML. Owns the page CSS, metric conversion, link generation and anchor mapping. |

## Build

```bash
python3 build.py          # or: npm run build
```

No Python packages required. Writes `docs/index.html` and prints a count of cocktails and
bottle links.

```bash
npm install               # jsdom, for the test only
npm test                  # smoke-test.mjs — 19 checks against a real DOM
npm run serve             # http://localhost:8000
```

**GitHub Pages:** Settings → Pages → deploy from branch, `main` / `docs`. The `docs/.nojekyll`
file is there to stop Jekyll from touching the output.

## How it works

- **Numbering** is assigned sequentially at build time from the order of `GROUPS`, so
  reordering or adding a drink renumbers everything automatically.
- **Metric amounts** are generated, not stored. `add_metric()` in `build.py` rewrites
  `¾ oz` into `¾ oz (22.5 ml)` using a 30 ml jigger convention. Never hand-write ml
  into `data.py`.
- **Recipe → appendix links** come from `ANCHOR_MAP` in `build.py`: an ordered list of
  (keyword, appendix item name) pairs. Longest/most specific keywords must come first —
  `"aged Jamaican rum"` has to precede any bare `"rum"` entry. Appendix row ids are
  slugified from the item name, so renaming an appendix item breaks its inbound links
  unless `ANCHOR_MAP` is updated to match.
- **OHLQ links** are Google site-scoped searches (`site:ohlq.com <brand>`) rather than
  direct OHLQ search URLs, because OHLQ's search is JavaScript-rendered and its query
  parameter could not be verified. If you find the real parameter, swap `ohlq_url()`.
- **NON_OHLQ** in `build.py` lists appendix items Ohio does not sell through state
  agencies (under 21% ABV, or not a spirit). Those render a "grocery / wine shop" tag
  instead of an availability link.
- **Video links** were gathered from search results and are not all verified. Ten drinks
  intentionally say "No strong video match found" rather than carry a guessed URL.

## Tracking data

Stored in `localStorage` under the key `bar52:v1`, shaped as:

```json
{ "12": { "made": true, "date": "Sep 4, 2026", "rating": 4, "note": "..." } }
```

Keys are the sequential drink numbers, so **renumbering drinks will desync existing
notes**. If you reorder the list, migrate saved data or switch the key to a stable slug
first. Export/Restore round-trips this object wrapped in `{app, version, saved, entries}`;
Restore merges rather than overwrites.

## Known next steps

- Shared state between two people needs a backend (Supabase free tier, or GitHub Issues
  via the API). `localStorage` is per-browser.
- Separate profiles per bartender.
- Moving cocktail data to JSON so the page can fetch it and edits skip the rebuild.
- Print stylesheet; service worker for offline use.
