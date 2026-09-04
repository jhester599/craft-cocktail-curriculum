# -*- coding: utf-8 -*-
"""Ingredient text -> appendix bottle, as data rather than inference.

BACKLOG P1 #4 needs to know, for every drink, exactly which bottles it requires,
so the page can answer "what can I make tonight?". `ANCHOR_MAP` used to
approximate that by string-matching a recipe line and linking the first hit. It
was never complete enough to compute against:

  - `gin` matched inside `ginger`, so "honey-ginger syrup" resolved to London dry
    gin, and so did "ginger beer".
  - Only the first match in a line was ever used, so "bourbon or rye" and
    "Angostura or mole bitters" each lost half their meaning.
  - Bare "rye" (A La Louisiane, Vieux Carre), "aged blended rum" and "Jamaican
    dark rum" matched nothing at all, so those lines had no appendix link.

This module replaces it. `MAP` is the single ordered keyword table, used both for
the in-recipe jump links and for computing requirements; `PANTRY` names what is
deliberately not a bottle. `resolve_line()` in build.py walks MAP in order,
claiming non-overlapping word-boundary spans, so a specific keyword consumes its
text before a general one can match inside it.

ORDER IS SIGNIFICANT, exactly as it was for ANCHOR_MAP: the most specific
keyword must come first. "aged Jamaican rum" has to precede "rum", or the bare
entry claims the span first and the drink asks for the wrong bottle. The build
asserts that every ingredient line is fully accounted for, so a new recipe that
names something unknown fails the build instead of silently going missing.

The value is the appendix item name, which must match a row in data.APPENDIX -
the build asserts that too, since a typo here would otherwise produce a
requirement no checkbox can ever satisfy.
"""

# Ordered, most specific first. keyword -> appendix item name.
MAP = [
    # --- bitter liqueurs and amari -------------------------------------------
    ("green Chartreuse", "Green Chartreuse"),
    ("yellow Chartreuse", "Yellow Chartreuse"),
    ("Campari", "Campari"),
    ("Aperol", "Aperol"),
    ("Bénédictine", "Bénédictine"),
    ("Fernet-Branca", "Fernet-Branca"),
    ("Amaro Averna", "Amaro Averna"),
    ("Amaro Nonino Quintessentia", "Amaro Nonino"),
    ("Cynar", "Cynar"),
    ("Suze (gentian liqueur)", "Suze"),
    ("Suze", "Suze"),

    # --- other liqueurs ------------------------------------------------------
    ("maraschino liqueur", "Maraschino liqueur"),
    ("crème de violette", "Crème de violette"),
    ("Cointreau", "Triple sec / orange liqueur"),
    ("dry orange curaçao", "Orange curaçao"),
    ("dry curaçao", "Orange curaçao"),
    ("coffee liqueur", "Coffee liqueur"),
    ("velvet falernum", "Velvet falernum"),
    ("falernum", "Velvet falernum"),
    ("allspice dram", "Allspice (pimento) dram"),
    ("peach brandy", "Peach brandy"),
    ("absinthe", "Absinthe"),

    # --- fortified and aromatised wines --------------------------------------
    ("sweet vermouth", "Sweet vermouth"),
    ("Punt e Mes", "Sweet vermouth"),
    ("dry vermouth", "Dry vermouth"),
    ("Cocchi Americano", "Blanc aperitif"),
    ("Lillet Blanc", "Blanc aperitif"),

    # --- bitters -------------------------------------------------------------
    ("Angostura bitters", "Aromatic bitters"),
    ("Angostura", "Aromatic bitters"),
    ("Peychaud's bitters", "Creole bitters"),
    ("Peychaud's", "Creole bitters"),
    ("orange bitters", "Orange bitters"),
    ("mole bitters", "Mole / chocolate bitters"),
    ("Boker's bitters", "Aromatic bitters"),
    ("orange flower water", "Orange flower water"),

    # --- syrups and tiki components -----------------------------------------
    ("orgeat", "Orgeat"),
    ("cream of coconut", "Cream of coconut"),
    ("raspberry syrup", "Raspberry syrup"),
    ("rich demerara syrup", "Demerara / rich syrup"),
    ("demerara syrup", "Demerara / rich syrup"),
    ("rich syrup", "Demerara / rich syrup"),
    ("honey-ginger syrup", "Honey syrup"),
    ("honey syrup", "Honey syrup"),
    ("ginger beer", "Ginger beer"),
    ("grapefruit soda", "Grapefruit soda"),
    ("tomato juice", "Tomato juice"),

    # --- rum -----------------------------------------------------------------
    # Every one of these must precede the bare "rum" entry at the end.
    ("Smith &amp; Cross overproof Jamaican rum", "Overproof Jamaican"),
    ("overproof Jamaican rum", "Overproof Jamaican"),
    ("aged Jamaican rum", "Aged Jamaican"),
    ("Jamaican dark rum", "Aged Jamaican"),
    ("aged blended rum", "Aged Jamaican"),
    ("aged demerara rum", "Demerara"),
    ("blackstrap or dark rum", "Blackstrap"),
    ("blackstrap rum", "Blackstrap"),
    ("rhum agricole vieux", "Rhum agricole vieux"),
    ("rhum agricole", "Rhum agricole vieux"),
    ("Pusser's navy rum", "Navy rum"),
    ("navy rum", "Navy rum"),
    ("white rum", "White / light rum"),

    # --- whiskey -------------------------------------------------------------
    ("rye whiskey", "Rye, 100 proof"),
    ("bacon-fat-washed bourbon", "Bourbon"),
    ("bourbon", "Bourbon"),
    ("blended Scotch", "Blended Scotch"),
    ("Islay single malt", "Islay single malt"),
    ("rye", "Rye, 100 proof"),              # bare "rye": A La Louisiane, Vieux Carre

    # --- brandy --------------------------------------------------------------
    ("cognac", "Cognac"),
    ("bonded apple brandy or applejack", "Apple brandy / Calvados"),
    ("apple brandy or Calvados", "Apple brandy / Calvados"),
    ("Calvados or apple brandy", "Apple brandy / Calvados"),
    ("apple brandy", "Apple brandy / Calvados"),
    ("pisco", "Pisco"),

    # --- agave ---------------------------------------------------------------
    ("blanco tequila", "Blanco tequila"),
    ("reposado tequila", "Reposado tequila"),
    ("mezcal", "Mezcal"),

    # --- gin and vodka -------------------------------------------------------
    ("London dry gin", "London dry gin"),
    ("citron vodka", "Citrus vodka"),
    ("vodka", "Vodka"),
    ("gin", "London dry gin"),
    ("rum", "White / light rum"),           # bare "rum" last of all the rums
]

# Text that is deliberately not a bottle: fresh produce, storecupboard staples,
# garnishes, and the generic placeholders in the two build-your-own recipes.
# These never appear as a requirement, so they can never block a drink.
PANTRY = [
    "fresh lime or lemon juice", "fresh lemon or lime juice",
    "fresh lime juice", "fresh lemon juice", "fresh grapefruit juice",
    "fresh orange juice", "lime juice", "lemon juice", "grapefruit juice",
    "orange juice", "pineapple juice", "cranberry juice", "citrus juice",
    "demerara or simple syrup", "simple syrup", "sugar or syrup", "agave nectar",
    "Grade B maple syrup", "maple syrup", "grenadine (homemade pomegranate)",
    "grenadine",
    "egg white", "heavy cream", "hot whole milk", "whole milk", "milk",
    "fresh hot espresso", "espresso",
    "soda water to top", "soda water", "soda to top", "soda",
    "water or soda", "water",
    "large handful fresh basil", "fresh basil", "basil",
    "mint leaves", "mint",
    "Worcestershire", "hot sauce",
    "pinch horseradish, salt, pepper, celery salt", "horseradish",
    "pinch of salt", "salt",
    "spices or tea to taste", "spices", "tea",
    "spirit",            # Clarified Milk Punch: whatever you have
    "cherry", "cherries",
]
