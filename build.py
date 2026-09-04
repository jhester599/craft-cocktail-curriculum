# -*- coding: utf-8 -*-
import html as H
import json
import os
import re
import unicodedata
from urllib.parse import quote_plus
from data import GROUPS, APPENDIX, WAVES
from tracker import TRACK_CSS, dash_html, track_js, track_block
from ohlq import BASE as OHLQ_BASE, PRODUCTS, CATEGORIES, WAVE_ITEMS


# ---------------------------------------------------------------------------
# Metric conversion: appends an approximate ml figure after every imperial
# measurement in ingredient lines and method text.
# ---------------------------------------------------------------------------
FRAC = {"\u00bd":.5, "\u00bc":.25, "\u00be":.75, "\u2153":1/3, "\u2154":2/3, "\u215b":.125}
FRAC_CLASS = "".join(FRAC.keys())

def _ml(v, per):
    x = v * per
    x = round(x * 2) / 2
    return ("%g" % x)

def _oz_val(whole, frac):
    v = float(whole) if whole else 0.0
    if frac:
        v += FRAC[frac]
    return v

def add_metric(text):
    # ranges first: "3-5 oz" / "3\u20135 oz"
    def rng(m):
        a, b = float(m.group(1)), float(m.group(2))
        return "%s%s%s oz (%s\u2013%s ml)" % (m.group(1), m.group(3), m.group(2),
                                          _ml(a, 30), _ml(b, 30))
    text = re.sub(r"(\d+)([\u2013-])(\d+)\s*oz\b",
                  lambda m: "%s%s%s oz (%s\u2013%s ml)" % (
                      m.group(1), m.group(2), m.group(3),
                      _ml(float(m.group(1)), 30), _ml(float(m.group(3)), 30)),
                  text)
    # single oz amounts
    def one(m):
        v = _oz_val(m.group(1), m.group(2))
        if v == 0:
            return m.group(0)
        return "%s oz (%s ml)" % (m.group(0).replace(" oz", "").strip(), _ml(v, 30))
    text = re.sub(r"(\d+)?\s*([" + FRAC_CLASS + r"])?\s*oz\b(?!\s*\()", one, text)
    # teaspoons and cups
    text = re.sub(r"\b(\d+)\s*tsp\b(?!\s*\()",
                  lambda m: "%s tsp (%s ml)" % (m.group(1), _ml(float(m.group(1)), 5)), text)
    text = re.sub(r"\b(\d+)\s*cup\b(?!\s*\()",
                  lambda m: "%s cup (%s ml)" % (m.group(1), _ml(float(m.group(1)), 240)), text)
    return text

def strip_ent(s):
    return s.replace("&amp;", "&")

def img_url(brand):
    q = strip_ent(brand) + " bottle"
    return "https://www.google.com/search?tbm=isch&q=" + quote_plus(q)

BOTTLE_ICON = ('<svg class="bi" viewBox="0 0 12 20" aria-hidden="true">'
               '<path d="M4.6 1h2.8v3.6l1.7 3.1c.2.4.3.8.3 1.2V18a1 1 0 0 1-1 1H4.6a1 1 0 0 1-1-1V8.9c0-.4.1-.8.3-1.2L4.6 4.6V1z"/>'
               '<path d="M3.9 11h4.2"/></svg>')

PLAY_ICON = ('<svg class="pi" viewBox="0 0 16 16" aria-hidden="true">'
             '<path d="M2 3.2A1.2 1.2 0 0 1 3.2 2h9.6A1.2 1.2 0 0 1 14 3.2v9.6a1.2 1.2 0 0 1-1.2 1.2H3.2A1.2 1.2 0 0 1 2 12.8z"/>'
             '<path d="M6.6 5.4 10.4 8l-3.8 2.6z" class="pf"/></svg>')


# ---------------------------------------------------------------------------
# Links: OHLQ availability + shelf photo, and recipe -> appendix anchors
# ---------------------------------------------------------------------------
def drink_slug(name):
    """Stable storage key for a cocktail, derived from its name.

    Tracking data is keyed by this, never by position, so inserting or
    reordering a drink cannot reattach notes to the wrong cocktail.
    Accents are folded and apostrophes dropped so "Vieux Carre" and
    "Tommy's Margarita" give clean keys.
    """
    n = strip_ent(name)
    n = unicodedata.normalize("NFKD", n)
    n = "".join(ch for ch in n if not unicodedata.combining(ch))
    n = n.lower().replace("'", "").replace("\u2019", "")
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    if not n:
        raise ValueError("empty slug for cocktail name %r" % name)
    return n


def slugify(name):
    n = strip_ent(name).lower()
    n = n.replace("\u00e9", "e").replace("\u00e8", "e").replace("\u00e7", "c").replace("\u00e0", "a")
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return "b-" + n

# Items Ohio Liquor does not carry: under 21% ABV, or not a spirit at all.
NON_OHLQ = {
    "Aperol", "Sweet vermouth", "Dry vermouth", "Blanc aperitif",
    "Aromatic bitters", "Creole bitters", "Orange bitters", "Mole / chocolate bitters",
    "Orange flower water", "Orgeat", "Cream of coconut", "Raspberry syrup",
    "Demerara / rich syrup", "Honey syrup", "Ginger beer", "Grapefruit soda",
    "Tomato juice", "Cocktail cherries",
    # Waves-only: grenadine has no appendix row but is still a grocery buy.
    "Grenadine",
}

OHLQ_ICON = ('<svg class="oi" viewBox="0 0 16 16" aria-hidden="true">'
             '<circle cx="7" cy="7" r="4.6"/><path d="M10.4 10.4 14 14"/></svg>')
CAM_ICON = ('<svg class="oi" viewBox="0 0 16 16" aria-hidden="true">'
            '<path d="M2 5.2h3l1-1.6h4l1 1.6h3v7.4H2z"/><circle cx="8" cy="8.6" r="2.3"/></svg>')

def ohlq_url(brand, item=None):
    """Best known ohlq.com URL: exact product, else category shelf, else search.

    See ohlq.py for how the first two tiers were gathered and how far to trust
    them. The search fallback always resolves, so an unknown bottle is never a
    dead link.
    """
    path = PRODUCTS.get(strip_ent(brand))
    if path is None and item is not None:
        path = CATEGORIES.get(item)
    if path:
        return OHLQ_BASE + path
    return ("https://www.google.com/search?q="
            + quote_plus("site:ohlq.com " + strip_ent(brand)))

def is_homemade(brand):
    """Rows like 'Homemade 3:1' name a technique, not a bottle to go and buy."""
    return strip_ent(brand).lower().startswith("homemade")

def bottle_links(brand, in_ohlq=True, item=None):
    """Brand name + an availability link and a shelf-photo link."""
    if is_homemade(brand):
        return ('<span class="bwrap"><span class="bname">%s</span>'
                '<span class="blinks"><span class="none">make it yourself</span>'
                '</span></span>' % brand)
    out = '<span class="bwrap"><span class="bname">%s</span><span class="blinks">' % brand
    if in_ohlq:
        out += ('<a href="%s" target="_blank" rel="noopener" title="Check Ohio Liquor availability">'
                '%s<span>OHLQ</span></a>' % (ohlq_url(brand, item), OHLQ_ICON))
    else:
        out += '<span class="offsale" title="Under 21 percent ABV or not a spirit \u2014 sold in grocery and wine shops, not OHLQ">grocery / wine shop</span>'
    out += ('<a href="%s" target="_blank" rel="noopener" title="See what the label looks like">'
            '%s<span>Photo</span></a>' % (img_url(brand), CAM_ICON))
    out += "</span></span>"
    return out

# keyword in a recipe line -> appendix item it should jump to
ANCHOR_MAP = [
    ("green Chartreuse", "Green Chartreuse"), ("yellow Chartreuse", "Yellow Chartreuse"),
    ("Campari", "Campari"), ("Aperol", "Aperol"),
    ("B\u00e9n\u00e9dictine", "B\u00e9n\u00e9dictine"), ("Fernet-Branca", "Fernet-Branca"),
    ("Amaro Averna", "Amaro Averna"), ("Amaro Nonino Quintessentia", "Amaro Nonino"),
    ("Cynar", "Cynar"), ("Suze", "Suze"),
    ("maraschino liqueur", "Maraschino liqueur"), ("cr\u00e8me de violette", "Cr\u00e8me de violette"),
    ("Cointreau", "Triple sec / orange liqueur"),
    ("dry orange cura\u00e7ao", "Orange cura\u00e7ao"), ("dry cura\u00e7ao", "Orange cura\u00e7ao"),
    ("coffee liqueur", "Coffee liqueur"),
    ("velvet falernum", "Velvet falernum"), ("falernum", "Velvet falernum"),
    ("allspice dram", "Allspice (pimento) dram"), ("peach brandy", "Peach brandy"),
    ("absinthe", "Absinthe"),
    ("sweet vermouth", "Sweet vermouth"), ("Punt e Mes", "Sweet vermouth"),
    ("dry vermouth", "Dry vermouth"),
    ("Cocchi Americano", "Blanc aperitif"), ("Lillet Blanc", "Blanc aperitif"),
    ("Angostura", "Aromatic bitters"), ("Peychaud's", "Creole bitters"),
    ("orange bitters", "Orange bitters"), ("mole bitters", "Mole / chocolate bitters"),
    ("orange flower water", "Orange flower water"),
    ("orgeat", "Orgeat"), ("cream of coconut", "Cream of coconut"),
    ("raspberry syrup", "Raspberry syrup"), ("demerara syrup", "Demerara / rich syrup"),
    ("honey-ginger syrup", "Honey syrup"), ("honey syrup", "Honey syrup"),
    ("ginger beer", "Ginger beer"), ("grapefruit soda", "Grapefruit soda"),
    ("tomato juice", "Tomato juice"),
    ("Smith &amp; Cross overproof Jamaican rum", "Overproof Jamaican"),
    ("aged Jamaican rum", "Aged Jamaican"), ("aged demerara rum", "Demerara"),
    ("blackstrap or dark rum", "Blackstrap"), ("blackstrap rum", "Blackstrap"),
    ("rhum agricole vieux", "Rhum agricole vieux"),
    ("Pusser's navy rum", "Navy rum"), ("white rum", "White / light rum"),
    ("rye whiskey", "Rye, 100 proof"), ("bourbon or rye", "Bourbon"), ("bourbon", "Bourbon"),
    ("blended Scotch", "Blended Scotch"), ("Islay single malt", "Islay single malt"),
    ("cognac", "Cognac"),
    ("bonded apple brandy or applejack", "Apple brandy / Calvados"),
    ("apple brandy or Calvados", "Apple brandy / Calvados"),
    ("Calvados or apple brandy", "Apple brandy / Calvados"),
    ("pisco", "Pisco"),
    ("blanco tequila", "Blanco tequila"), ("reposado tequila", "Reposado tequila"),
    ("mezcal", "Mezcal"),
    ("London dry gin", "London dry gin"), ("citron vodka", "Citrus vodka"),
    ("vodka", "Vodka"), ("gin", "London dry gin"),
]

def link_ingredients(line):
    """Wrap the first matching ingredient keyword in a jump link to the appendix."""
    low = line.lower()
    for kw, item in ANCHOR_MAP:
        i = low.find(kw.lower())
        if i == -1:
            continue
        return (line[:i] + '<a class="jump" href="#%s" title="Jump to buying guide">%s</a>'
                % (slugify(item), line[i:i+len(kw)]) + line[i+len(kw):])
    return line

def brand_link(brand):
    return ('<a class="bottle" href="%s" target="_blank" rel="noopener">%s<span>%s</span></a>'
            % (img_url(brand), BOTTLE_ICON, brand))

def cocktail_html(c):
    ings = "".join("<li>%s</li>" % link_ingredients(add_metric(i)) for i in c["ing"])
    if c["video"]:
        vid = ('<a class="video" href="%s" target="_blank" rel="noopener">%s'
               '<span>Watch &middot; %s</span></a>' % (c["video"], PLAY_ICON, c["channel"]))
    else:
        vid = '<p class="novideo">No strong video match found. Try searching the drink name on the Educated Barfly or Anders Erickson channels.</p>'
    return """
    <article class="drink" id="d%d" data-id="%s">
      <header class="drink-head">
        <span class="num">%02d</span>
        <h3>%s</h3>
        <p class="tags"><span class="tag">%s</span><span class="tag alt">%s</span></p>
      </header>
      <ul class="ings">%s</ul>
      <p class="method">%s</p>
      %s
      <p class="why">%s</p>%s
    </article>""" % (c["n"], c["slug"], c["n"], c["name"], c["family"], c["spirit"], ings, add_metric(c["method"]), vid, c["note"], track_block(c["slug"]))

def group_html(g):
    drinks = "".join(cocktail_html(c) for c in g["cocktails"])
    return """
  <section class="group" id="%s">
    <div class="group-head">
      <h2>%s</h2>
      <p class="group-intro">%s</p>
    </div>
    %s
  </section>""" % (g["id"], g["title"], g["intro"], drinks)

def appendix_html(sec):
    rows = ""
    for item, primary, alts, note in sec["rows"]:
        ok = item not in NON_OHLQ
        alt_html = ("".join(bottle_links(a, ok, item) for a in alts) if alts
                    else '<span class="none">Make it yourself</span>')
        rows += """
      <div class="brow" id="%s">
        <div class="bitem">%s</div>
        <div class="bcols">
          <div class="bcol"><span class="blab">First choice</span>%s</div>
          <div class="bcol"><span class="blab">Also works</span>%s</div>
        </div>
        <p class="bnote">%s</p>
      </div>""" % (slugify(item), item, bottle_links(primary, ok, item), alt_html, note)
    return """
  <section class="apx" id="%s">
    <h3>%s</h3>
    <p class="apx-blurb">%s</p>
    %s
  </section>""" % (sec["id"], sec["title"], sec["blurb"], rows)

def wave_html(name, blurb, items):
    # The waves name bottles loosely, so resolve each to the appendix item it
    # means. Without this every wave entry rendered an OHLQ link, including the
    # under-21% ABV ones the appendix correctly sends to a grocery store.
    links = ""
    for i in items:
        item = WAVE_ITEMS.get(strip_ent(i))
        links += bottle_links(i, item not in NON_OHLQ, item)
    return """
    <div class="wave">
      <h4>%s</h4>
      <p>%s</p>
      <div class="wavelist">%s</div>
    </div>""" % (name, blurb, links)

# The number is a purely visual index reassigned from position on every
# build. The slug is the identity that saved notes hang off.
_seq = 0
SLUGS = []
_seen = {}
for _g in GROUPS:
    for _c in _g["cocktails"]:
        _seq += 1
        _c["n"] = _seq
        _c["slug"] = drink_slug(_c["name"])
        if _c["slug"] in _seen:
            raise SystemExit("duplicate slug %r: %r and %r"
                             % (_c["slug"], _seen[_c["slug"]], _c["name"]))
        _seen[_c["slug"]] = _c["name"]
        SLUGS.append(_c["slug"])

TOTAL = len(SLUGS)

# Every bottle named in the buying-order waves must resolve to an appendix item,
# or it silently loses its category link and its grocery/OHLQ classification.
_unmapped = sorted({strip_ent(i) for _n, _b, items in WAVES for i in items}
                   - set(WAVE_ITEMS))
assert not _unmapped, "wave bottles missing from ohlq.WAVE_ITEMS: %s" % _unmapped

# Categories are keyed by appendix item name; a typo there fails silently too.
_items = {item for sec in APPENDIX for item, _p, _a, _n in sec["rows"]}
_stray = sorted(set(CATEGORIES) - _items)
assert not _stray, "ohlq.CATEGORIES keys match no appendix item: %s" % _stray

nav = "".join('<a href="#%s">%s</a>' % (g["id"], g["title"]) for g in GROUPS)
apx_nav = "".join('<a href="#%s">%s</a>' % (s["id"], s["title"]) for s in APPENDIX)

TALLY = [("Whiskey", 8), ("Gin", 8), ("Rum", 8), ("Brandy &amp; cognac", 8),
         ("Agave", 7), ("Amaro &amp; bitter", 7), ("Vodka", 6)]
tally_html = "".join('<li><span class="tn">%d</span>%s</li>' % (n, k) for k, n in TALLY)

CSS = """
:root{
  --ink:#0D120F; --panel:#141B16; --panel-2:#1A231D; --line:#2A362D;
  --bone:#EDE7DA; --muted:#98A395; --chart:#C9DA4E; --campari:#D0503A; --brass:#C9A253;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--ink);color:var(--bone);
  font-family:Karla,"Helvetica Neue",Arial,sans-serif;font-size:17px;line-height:1.6;
  -webkit-text-size-adjust:100%;}
.wrap{max-width:760px;margin:0 auto;padding:0 22px 100px}
a{color:inherit}
h1,h2,h3,h4{font-family:"Bodoni Moda",Georgia,"Times New Roman",serif;font-weight:500;margin:0;
  font-optical-sizing:none;}

/* ---- masthead ---- */
.mast{padding:76px 0 34px;border-bottom:1px solid var(--line)}
.mast h1{font-size:clamp(40px,10vw,68px);line-height:1.02;letter-spacing:-.01em}
.mast h1 em{font-style:italic;color:var(--chart)}
.mast .sub{color:var(--muted);margin:18px 0 0;max-width:52ch}
.tally{list-style:none;padding:0;margin:30px 0 0;display:flex;flex-wrap:wrap;gap:8px}
.tally li{background:var(--panel);border:1px solid var(--line);border-radius:2px;
  padding:7px 11px;font-size:13.5px;color:var(--muted);display:flex;gap:7px;align-items:baseline}
.tn{font-family:"Bodoni Moda",Georgia,serif;font-size:18px;color:var(--chart);font-optical-sizing:none;}

/* ---- contents ---- */
.contents{padding:34px 0;border-bottom:1px solid var(--line)}
.contents h2{font-size:15px;font-family:Karla,sans-serif;font-weight:700;letter-spacing:.02em;
  color:var(--muted);margin-bottom:14px}
.contents a{display:block;text-decoration:none;padding:11px 0;border-bottom:1px dotted var(--line);
  font-family:"Bodoni Moda",Georgia,serif;font-size:19px;font-optical-sizing:none;min-height:44px}
.contents a:hover,.contents a:focus-visible{color:var(--chart)}
.contents .apxlinks a{font-family:Karla,sans-serif;font-size:15.5px;color:var(--muted)}

/* ---- groups ---- */
.group{padding:56px 0 10px;border-bottom:1px solid var(--line)}
.group-head{margin-bottom:34px}
.group h2{font-size:clamp(27px,6vw,38px);line-height:1.12;color:var(--chart)}
.group-intro{color:var(--muted);margin:14px 0 0;max-width:60ch}

.drink{background:var(--panel);border:1px solid var(--line);border-left:2px solid var(--brass);
  padding:24px 22px;margin-bottom:18px}
.drink-head{margin-bottom:16px}
.num{font-family:"Bodoni Moda",Georgia,serif;font-size:13px;color:var(--muted);display:block;margin-bottom:4px;font-optical-sizing:none;}
.drink h3{font-size:26px;line-height:1.15}
.tags{margin:9px 0 0;display:flex;flex-wrap:wrap;gap:6px}
.tag{font-size:12px;letter-spacing:.02em;color:var(--muted);border:1px solid var(--line);
  padding:3px 8px;border-radius:999px}
.tag.alt{color:var(--brass);border-color:#3B3322}
.ings{list-style:none;padding:0;margin:0 0 14px}
.ings li{padding:6px 0;border-bottom:1px dotted var(--line);font-size:16.5px}
.ings li:last-child{border-bottom:none}
.method{margin:0 0 16px;font-size:15.5px;color:var(--muted)}
.why{margin:16px 0 0;font-size:15.5px;padding-top:14px;border-top:1px dotted var(--line)}

.video{display:inline-flex;align-items:center;gap:9px;text-decoration:none;
  background:var(--panel-2);border:1px solid var(--line);padding:9px 14px;font-size:14.5px}
.video:hover,.video:focus-visible{border-color:var(--chart);color:var(--chart)}
.pi{width:16px;height:16px;flex:none;fill:none;stroke:currentColor;stroke-width:1.3}
.pi .pf{fill:currentColor;stroke:none}
.novideo{margin:0;font-size:14.5px;color:var(--muted);font-style:italic;
  border-left:2px solid var(--line);padding-left:12px}

/* ---- bottle links ---- */
.bottle{display:inline-flex;align-items:center;gap:6px;text-decoration:none;
  border-bottom:1px solid #38452F;padding-bottom:1px;margin:0 2px 4px 0}
.bottle:hover,.bottle:focus-visible{color:var(--chart);border-bottom-color:var(--chart)}
.bi{width:11px;height:17px;flex:none;fill:none;stroke:currentColor;stroke-width:1.2;
  stroke-linejoin:round;opacity:.7}
.bottle span{font-size:15.5px}

/* ---- appendix ---- */
.apxwrap{padding-top:56px}
.apxwrap>h2{font-size:clamp(27px,6vw,38px);color:var(--chart)}
.apxwrap>.lead{color:var(--muted);max-width:60ch;margin:14px 0 0}
.apx{padding:40px 0 6px;border-bottom:1px solid var(--line)}
.apx h3{font-size:23px}
.apx-blurb{color:var(--muted);font-size:15.5px;margin:8px 0 22px;max-width:58ch}
.brow{background:var(--panel);border:1px solid var(--line);padding:18px;margin-bottom:12px}
.bitem{font-family:"Bodoni Moda",Georgia,serif;font-size:20px;margin-bottom:12px;font-optical-sizing:none;}
.bcols{display:grid;grid-template-columns:1fr;gap:12px}
.blab{display:block;font-size:12px;color:var(--muted);margin-bottom:5px}
.bcol:first-child .bottle span{color:var(--bone)}
.bcol:last-child .bottle span{color:var(--muted);font-size:14.5px}
.none{color:var(--muted);font-size:14.5px;font-style:italic}
.bnote{margin:14px 0 0;font-size:14.5px;color:var(--muted);padding-top:12px;
  border-top:1px dotted var(--line)}

/* ---- waves ---- */
.waves{padding:44px 0;border-bottom:1px solid var(--line)}
.waves>h3{font-size:23px;margin-bottom:8px}
.waves>p.lead{color:var(--muted);font-size:15.5px;margin:0 0 24px;max-width:58ch}
.wave{border-left:2px solid var(--chart);padding:2px 0 2px 18px;margin-bottom:26px}
.wave h4{font-size:19px}
.wave p{color:var(--muted);font-size:14.5px;margin:4px 0 12px}
.wavelist{display:flex;flex-wrap:wrap;gap:4px 16px}

/* ---- notes ---- */
.notes{padding:44px 0 0}
.notes h3{font-size:23px;margin-bottom:16px}
.notes ul{padding-left:0;list-style:none;margin:0}
.notes li{border-left:2px solid var(--campari);padding:2px 0 2px 16px;margin-bottom:18px;
  font-size:15.5px;color:var(--muted)}
.notes li b{color:var(--bone);font-weight:700}
footer{margin-top:56px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--muted);font-size:13.5px}

@media (min-width:640px){
  .bcols{grid-template-columns:1fr 1fr;gap:20px}
  .drink{padding:28px 26px}
}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}

/* ---- jump links from recipe to buying guide ---- */
.jump{text-decoration:none;border-bottom:1px dashed #4A5A3C;padding-bottom:1px}
.jump:hover,.jump:focus-visible{color:var(--chart);border-bottom-color:var(--chart)}

/* ---- bottle rows with availability + photo ---- */
.bwrap{display:block;margin-bottom:12px}
.bwrap:last-child{margin-bottom:0}
.bname{display:block;font-size:15.5px;line-height:1.35}
.blinks{display:flex;flex-wrap:wrap;gap:6px;margin-top:5px}
.blinks a{display:inline-flex;align-items:center;gap:5px;text-decoration:none;
  border:1px solid var(--line);background:var(--panel-2);padding:6px 12px;min-height:44px;
  font-size:12.5px;color:var(--muted)}
.blinks a:hover,.blinks a:focus-visible{color:var(--chart);border-color:var(--chart)}
.oi{width:12px;height:12px;flex:none;fill:none;stroke:currentColor;stroke-width:1.4}
.offsale{font-size:12px;color:var(--brass);border:1px dotted #3B3322;padding:6px 12px;
  display:inline-flex;align-items:center;min-height:44px}
.bcol:last-child .bname{color:var(--muted);font-size:14.5px}
.brow{scroll-margin-top:16px}
.brow:target{border-color:var(--chart)}
.wavelist{display:block}
.wavelist .bwrap{display:inline-block;vertical-align:top;width:100%;max-width:230px;
  margin:0 18px 14px 0}
:focus-visible{outline:2px solid var(--chart);outline-offset:3px}
""" + TRACK_CSS

NOTES = [
    ("The video links have been verified.", "All 38 were checked against YouTube's oEmbed endpoint: every one resolves, sits on the channel claimed, and carries a title matching its drink. Fourteen drinks say no strong match rather than carry a guessed URL &mdash; the same channels very likely cover them, so a quick channel search is worth a try. Links do rot over time; re-running the check periodically is on the backlog."),
    ("Two links come with asterisks.", "The Fish House Punch link is a YouTube Short rather than a full tutorial. The Cosmopolitan link is confirmed to be the Educated Barfly's 1934 variation, not the modern Cecchini build in the spec above &mdash; treat it as background, not as instructions."),
    ("Specs legitimately vary.", "The Boulevardier, White Negroni, Vieux Carré, Division Bell, Mai Tai and Aviation all have competing accepted ratios. The versions here are cross-checked against Difford's, Punch, Imbibe, Death &amp; Co and Smuggler's Cove — treat them as starting points and adjust to your palate."),
    ("Chartreuse is now down to two drinks.", "The Carthusian monks capped production in 2021 and moved to strict allocation in early 2023, and that policy has not shifted since — the shortage is a deliberate decision, not a supply-chain problem, and it hits the US far harder than Europe. Rather than build a year around a bottle you may never find, only the Last Word and the Naked &amp; Famous call for it, and both list a substitute in the build. Faccia Brutto Centerbe is the closest green stand-in; Strega covers the yellow."),
    ("Classification involved judgement calls.", "The Black Manhattan is counted as amaro-forward because Averna fully replaces the vermouth, and the Aviation is tallied in the bitter column to keep the spirit spread even. Move them if you disagree — the drinks are unaffected."),
    ("Metric figures are rounded to a 30 ml jigger.", "The convention most metric recipes use, so ¾ oz reads as 22.5 ml rather than the literal 22.2. Close enough that the balance holds; use one system throughout a given drink rather than mixing them."),
]
notes_html = "".join("<li><b>%s</b> %s</li>" % (a, b) for a, b in NOTES)

groups_html = "".join(group_html(g) for g in GROUPS)
apx_sections = "".join(appendix_html(s) for s in APPENDIX)
waves_html = "".join(wave_html(*w) for w in WAVES)

doc = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Fifty-Two Weeks Behind the Bar</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400;0,6..96,500;1,6..96,400&family=Karla:wght@400;700&display=swap" rel="stylesheet">
<style>%s</style>
</head>
<body>
<div class="wrap">

  <header class="mast">
    <h1>Fifty-two weeks<br><em>behind the bar</em></h1>
    <p class="sub">A year of lesser-known classics, modern craft drinks and regional oddities for two people who have already made every Old Fashioned, Margarita and Manhattan they need to. Grouped by family so each week builds on the last. Ingredients in each recipe link straight to the buying guide, and every bottle there carries an Ohio Liquor stock check and a photo of the label. Measurements are given in both ounces and millilitres, and only two drinks call for Chartreuse — both with substitutes written into the build.</p>
    <ul class="tally">%s</ul>
  </header>

  %s

  <nav class="contents">
    <h2>Eleven families</h2>
    %s
    <div class="apxlinks" style="margin-top:20px">
      <h2>Buying guide</h2>
      %s
    </div>
  </nav>

  %s

  <div class="apxwrap">
    <h2>What to buy</h2>
    <p class="lead">Brands chosen for how they perform in these specific recipes, not for prestige. First choice is the workhorse most bartenders reach for; the alternates are either legitimate substitutes or cheaper and easier to find. Every bottle has two links: OHLQ checks live Ohio Liquor stock, and Photo shows you the label so you can spot it on a shelf. Anything marked grocery / wine shop sits under 21 percent ABV, so Ohio does not sell it through OHLQ at all &mdash; look for it at Heinen's, Giant Eagle or a wine shop instead.</p>
    %s

    <section class="waves">
      <h3>Buying order</h3>
      <p class="lead">Three waves, sequenced so the earliest purchases unlock the most drinks.</p>
      %s
    </section>

    <section class="notes">
      <h3>Before you start</h3>
      <ul>%s</ul>
    </section>
  </div>

  <footer>Fifty-two drinks across eleven families. Sequence them by season rather than by number: stirred and spirit-forward in winter, gin and agave in spring, rum and tiki through summer, amaro in autumn.</footer>
</div>

%s
</body>
</html>
""" % (CSS, tally_html, dash_html(TOTAL), nav, apx_nav, groups_html,
       apx_sections, waves_html, notes_html, track_js(SLUGS))

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "index.html")
os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(doc)

print("wrote", OUT)
print("bytes:", len(doc))
n = sum(len(g["cocktails"]) for g in GROUPS)
print("cocktails:", n)
print("bottle links:", doc.count('tbm=isch'))
_cat_urls = {OHLQ_BASE + c for c in CATEGORIES.values()}
_prod_urls = {OHLQ_BASE + c for c in PRODUCTS.values()}
_hrefs = re.findall(r'href="([^"]+)"', doc)
print("ohlq links: %d product, %d category, %d search fallback"
      % (sum(h in _prod_urls for h in _hrefs),
         sum(h in _cat_urls for h in _hrefs),
         sum("site%3Aohlq.com" in h for h in _hrefs)))
print("slugs:", len(SLUGS), "unique:", len(set(SLUGS)))
