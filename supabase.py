# -*- coding: utf-8 -*-
"""Supabase connection details for cross-device sync.

Both values below are public by design. The page is served from GitHub Pages,
so anything the browser needs is readable by anyone who views source - there is
no such thing as a secret in a static site. The publishable key is the one
Supabase intends to be shipped to browsers, and `schema.sql` is written on the
assumption that everyone has it: `anon` holds no table privileges, and the only
reachable calls are pull/push/ping, each of which needs a sync code it cannot
enumerate.

Never put the service_role key here. That one bypasses every check.

Leave URL empty to build a page with sync switched off entirely - the sync
controls are not rendered and the tracker behaves exactly as it did before.
That keeps the repo usable by anyone who clones it without a Supabase project.
"""

URL = "https://dwvuljeiogcwrubcdhzc.supabase.co"
PUBLISHABLE_KEY = "sb_publishable_9NnKS6exiv9CFD7vd--D8g_U5eN1NnL"

# Sync codes are generated in the browser from crypto.getRandomValues.
#
# 12 characters of a 30-symbol alphabet is about 59 bits: roughly 5x10^17
# possibilities, which is far past brute-forcing over a network even without
# rate limits, while being short enough to read off one phone and type into
# another. The earlier 26 was security theatre at the cost of usability.
# Displayed in groups of four; the separators are stripped before use, so
# K7MP-2XQR-9TVB and k7mp2xqr9tvb are the same code.
#
# schema.sql refuses anything under 12, so the two must be changed together.
# Codes issued at the old length keep working - they are longer, not shorter.
CODE_LENGTH = 12


def enabled():
    return bool(URL and PUBLISHABLE_KEY)
