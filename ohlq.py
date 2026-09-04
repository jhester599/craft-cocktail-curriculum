# -*- coding: utf-8 -*-
"""Ohio Liquor link data.

OHLQ's own search is JavaScript-rendered and its query parameter could not be
verified, so links used to route through a `site:ohlq.com` Google search. This
module replaces that hop with real ohlq.com URLs wherever one is known.

Three tiers, best first, applied by `ohlq_url()` in build.py:

  1. PRODUCTS   - an exact product page for a specific bottle.
  2. CATEGORIES - the browse page for an appendix item's spirit category,
                  which lands you on a filtered shelf one click from the bottle.
  3. fallback   - the original Google search, for anything not covered above.

HOW THIS DATA WAS GATHERED, AND WHAT THAT IS WORTH
--------------------------------------------------
Every path here came from search results that returned an indexed ohlq.com URL.
ohlq.com is not reachable from the build environment, so none was fetched during
the build - but 33 distinct URLs the page produced were opened by hand on
2026-09-04 and every one resolved. Two mappings were corrected by that pass:
Campari was confirmed to sit under aperitif rather than amaro, and aged Jamaican
rum was found under `dark` rather than `gold`. The Appleton Estate 12 product
entry was added while making those corrections and so has NOT been opened.

Anything added later has NOT been through that check. Open a new URL before
adding it, and re-run the check if links start looking stale - see the README
for how to regenerate the list of distinct URLs.

CATEGORIES is the sturdier half. Each of those paths appeared repeatedly across
independent searches, they follow one obvious scheme (`/liquor/<spirit>` plus
`?producttype=` / `?productsubtype=` filters), and a category page survives a
product being renamed, resized or delisted.

PRODUCTS is deliberately thin. Product slugs cannot be derived from a brand name
- "Smith &amp; Cross" lives at `smith-cross-traditional-jamaica-rum` - so each
one has to be harvested individually, and harvesting turned out to be
unreliable: a third of brands returned nothing at all (Campari included, which
Ohio certainly sells), and several products returned two competing paths with
identical page titles. Only entries whose page title unambiguously matched the
brand are listed. Everything else deliberately falls through to its category.

So: adding a PRODUCTS entry is a claim that a specific page exists, and the
honest way to make that claim is to open the URL first. If one 404s, delete it -
the bottle falls back to its category page and the site keeps working.
"""

BASE = "https://www.ohlq.com"

# Brand exactly as written in data.py (after &amp; -> &) -> product page path.
# Only brands whose OHLQ page title unambiguously matched. See module docstring.
PRODUCTS = {
    "Green Chartreuse": "/liquor/cordial/aperitif/green-chartreuse",
    "D.O.M. Bénédictine": "/liquor/cordial/benedictine-dom-french-liqueur",
    "Fernet-Branca": "/liquor/cordial/fernet-branca",
    "Averna": "/liquor/cordial/amaro/averna",
    "Pernod Absinthe": "/liquor/cordial/pernod-absinthe",
    "Smith & Cross": "/liquor/rum/dark/smith-cross-traditional-jamaica-rum",
    "Del Maguey Vida": "/liquor/tequila/mezcal/del-maguey-vida-mezcal",
    # OHLQ lists the 12-year as "Appleton Estate Rare Casks 12 YR".
    "Appleton Estate 12 Year": "/liquor/rum/dark/appleton-estate-rare-casks-12-yr",
    "Appleton Estate 12": "/liquor/rum/dark/appleton-estate-rare-casks-12-yr",
    "El Tesoro Reposado": "/liquor/tequila/reposado/el-tesoro-reposado-tequila",
    "Sipsmith": "/liquor/gin/london-dry/sipsmith-london-dry-gin",
    "Macchu Pisco": "/liquor/brandy/macchu-pisco",
    "Laphroaig 10":
        "/liquor/whiskey/scotch/single-malt/laphroaig-10-year-old-single-malt-islay-scotch-whi",
}

# Appendix item name -> category browse page path. Keyed by item rather than by
# brand so every bottle in a row inherits it, alternates included.
CATEGORIES = {
    # Bitter liqueurs and amari
    "Campari": "/liquor/cordial?producttype=aperitif",
    "Green Chartreuse": "/liquor/cordial?producttype=aperitif",
    "Yellow Chartreuse": "/liquor/cordial?producttype=aperitif",
    "Suze": "/liquor/cordial?producttype=aperitif",
    "Bénédictine": "/liquor/cordial",
    "Fernet-Branca": "/liquor/cordial?producttype=amaro",
    "Amaro Averna": "/liquor/cordial?producttype=amaro",
    "Amaro Nonino": "/liquor/cordial?producttype=amaro",
    "Cynar": "/liquor/cordial?producttype=amaro",

    # Other liqueurs
    "Maraschino liqueur": "/liquor/cordial",
    "Crème de violette": "/liquor/cordial",
    "Triple sec / orange liqueur": "/liquor/cordial?producttype=triple-sec",
    "Orange curaçao": "/liquor/cordial?producttype=triple-sec",
    "Coffee liqueur": "/liquor/cordial",
    "Velvet falernum": "/liquor/cordial",
    "Allspice (pimento) dram": "/liquor/cordial",
    "Peach brandy": "/liquor/cordial",
    "Absinthe": "/liquor/cordial",

    # Rum
    "Overproof Jamaican": "/liquor/rum?producttype=overproof",
    "Aged Jamaican": "/liquor/rum?producttype=dark",
    "Demerara": "/liquor/rum?producttype=dark",
    "Blackstrap": "/liquor/rum?producttype=dark",
    "Rhum agricole vieux": "/liquor/rum?producttype=agricole",
    "Navy rum": "/liquor/rum?producttype=dark",
    "White / light rum": "/liquor/rum?producttype=white",

    # Whiskey
    "Rye, 100 proof": "/liquor/whiskey?productsubtype=rye&producttype=american",
    "Bourbon": "/liquor/whiskey?productsubtype=bourbon&producttype=american",
    "Blended Scotch": "/liquor/whiskey?producttype=scotch",
    "Islay single malt": "/liquor/whiskey?productsubtype=single-malt&producttype=scotch",

    # Brandy
    "Cognac": "/liquor/brandy?producttype=cognac",
    "Apple brandy / Calvados": "/liquor/brandy",
    "Pisco": "/liquor/brandy",

    # Agave
    "Blanco tequila": "/liquor/tequila?producttype=blanco",
    "Reposado tequila": "/liquor/tequila?producttype=reposado",
    "Mezcal": "/liquor/tequila?producttype=mezcal",

    # Gin and vodka
    "London dry gin": "/liquor/gin?producttype=london-dry",
    "Gin for floral & herbal builds": "/liquor/gin",
    "Vodka": "/liquor/vodka",
    "Citrus vodka": "/liquor/vodka?producttype=flavored",
}

# The buying-order waves name bottles loosely, so they cannot be matched to the
# appendix by string equality. Map each loose name onto the appendix item it
# means; that gives the wave list both a category link and - importantly - the
# right in_ohlq flag, which it previously did not have at all.
WAVE_ITEMS = {
    "Campari": "Campari",
    "Luxardo Maraschino": "Maraschino liqueur",
    "Cocchi Vermouth di Torino": "Sweet vermouth",
    "Dolin Dry Vermouth": "Dry vermouth",
    "Cocchi Americano": "Blanc aperitif",
    "Angostura Bitters": "Aromatic bitters",
    "Peychaud's Bitters": "Creole bitters",
    "Regans' Orange Bitters No. 6": "Orange bitters",
    "Beefeater Gin": "London dry gin",
    "Rittenhouse Rye": "Rye, 100 proof",
    "Old Forester 100 Proof": "Bourbon",
    "Cointreau": "Triple sec / orange liqueur",

    "Aperol": "Aperol",
    "Bénédictine": "Bénédictine",
    "Punt e Mes": "Sweet vermouth",
    "Pierre Ferrand 1840 Cognac": "Cognac",
    "Cimarrón Blanco Tequila": "Blanco tequila",
    "Del Maguey Vida Mezcal": "Mezcal",
    "Appleton Estate 12": "Aged Jamaican",
    "Smith & Cross Rum": "Overproof Jamaican",

    "Suze": "Suze",
    "Cynar": "Cynar",
    "Fernet-Branca": "Fernet-Branca",
    "Amaro Averna": "Amaro Averna",
    "Amaro Nonino": "Amaro Nonino",
    "Rothman & Winter Crème de Violette": "Crème de violette",
    "Velvet Falernum": "Velvet falernum",
    "St. Elizabeth Allspice Dram": "Allspice (pimento) dram",
    "Hamilton 86 Demerara": "Demerara",
    "Rhum J.M VSOP": "Rhum agricole vieux",
    "Pusser's Rum": "Navy rum",
    "Laird's Bottled-in-Bond Apple Brandy": "Apple brandy / Calvados",
    "Campo de Encanto Pisco": "Pisco",
    "Rothman & Winter Orchard Peach": "Peach brandy",
    "Laphroaig 10": "Islay single malt",
    "Mr Black Coffee Liqueur": "Coffee liqueur",
    "Faccia Brutto Centerbe": "Green Chartreuse",
    "Strega": "Yellow Chartreuse",
    # Grenadine has no appendix row of its own; "Grenadine" exists in
    # build.NON_OHLQ purely so this wave entry resolves as a grocery item.
    "Small Hand Foods Grenadine": "Grenadine",
}
