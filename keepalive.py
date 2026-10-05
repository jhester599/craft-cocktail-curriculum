# -*- coding: utf-8 -*-
"""Ping Supabase so a free-tier project does not pause.

Supabase pauses a free project that has not seen "sufficient user database
activity over the past week", and a paused project refuses reads and writes
until it is restored from the dashboard. Sufficient is a volume, not a single
touch: their docs say "typically a few user requests to the database each day"
is enough. An earlier version of this pinged once every three days on the
theory that any one request resets a 7-day timer; the project was warned on
Sept 12 and paused on Oct 5 2026 with every one of those pings succeeding.

So each run makes several calls, and the workflow runs twice a day. That is
well clear of "a few each day" without being anything Supabase would notice.

Config comes from supabase.py rather than repository secrets. Both values are
already public - they ship inside docs/index.html, which is the whole reason
schema.sql gives `anon` no table privileges - so putting them in secrets would
add setup steps and a second place to keep in sync, for no security gain. If you
ever point this at a project whose key is genuinely private, read them from the
environment here instead.

Uses only the standard library, so the workflow needs no install step.

Exit: 0 pinged (or nothing configured), 1 could not reach the project.
"""

import sys
import time
import urllib.error
import urllib.request

import supabase

TIMEOUT = 30
# Calls per run, and the gap between them. Each one is a real query against a
# table (see ping() in schema.sql), which is what Supabase counts.
PINGS = 3
SPACING = 10
# Retries cover transient trouble - a timeout, a 502 from the gateway. They do
# not wake a paused project: a paused free project stays down until someone
# restores it from the dashboard, so a run that keeps failing means go and look.
ATTEMPTS = 4
BACKOFF = 20


def ping():
    req = urllib.request.Request(
        supabase.URL.rstrip("/") + "/rest/v1/rpc/ping",
        data=b"{}",
        method="POST",
        headers={
            "apikey": supabase.PUBLISHABLE_KEY,
            "Authorization": "Bearer " + supabase.PUBLISHABLE_KEY,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return r.status, r.read().decode("utf-8", "replace").strip()


def ping_with_retries():
    """One successful call, retrying transient failures. Returns (ok, detail)."""
    last = ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            status, body = ping()
            if status == 200:
                if attempt > 1:
                    body += " (after %d attempts)" % attempt
                return True, body
            last = "HTTP %s - %s" % (status, body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace").strip()
            last = "HTTP %s - %s" % (e.code, detail)
            # A 4xx is a real problem with the call, not a passing glitch, so
            # retrying it just wastes a minute and reports the same thing.
            if 400 <= e.code < 500:
                print("Request rejected: %s" % last)
                return False, last
        except Exception as e:  # timeout, DNS, TLS, connection reset
            last = "%s: %s" % (type(e).__name__, e)

        print("Attempt %d/%d failed (%s)" % (attempt, ATTEMPTS, last))
        if attempt < ATTEMPTS:
            time.sleep(BACKOFF)
    return False, last


def main():
    if not supabase.enabled():
        print("No Supabase project configured; nothing to keep awake.")
        return 0

    for n in range(1, PINGS + 1):
        ok, detail = ping_with_retries()
        if not ok:
            print("Could not reach %s after %d attempts. Last error: %s"
                  % (supabase.URL, ATTEMPTS, detail))
            print("If the project is paused, restore it from the Supabase dashboard -"
                  " requests alone will not bring it back.")
            return 1
        print("Ping %d/%d: %s" % (n, PINGS, detail))
        if n < PINGS:
            time.sleep(SPACING)

    print("Awake.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
