# -*- coding: utf-8 -*-
"""Ping Supabase so a free-tier project does not pause.

Supabase pauses a free project after 7 days without database activity, and a
paused project refuses reads and writes until it is restored. A page used a few
evenings a month would hit that almost every time, so the first sync after a
quiet week would fail. A scheduled ping every few days keeps it awake.

Config comes from supabase.py rather than repository secrets. Both values are
already public - they ship inside docs/index.html, which is the whole reason
schema.sql gives `anon` no table privileges - so putting them in secrets would
add setup steps and a second place to keep in sync, for no security gain. If you
ever point this at a project whose key is genuinely private, read them from the
environment here instead.

Uses only the standard library, so the workflow needs no install step.

Exit: 0 pinged (or nothing configured), 1 could not reach the project.
"""

import json
import sys
import time
import urllib.error
import urllib.request

import supabase

TIMEOUT = 30
# A paused project takes about 30 seconds to wake, and the request that wakes it
# may itself time out. Retrying is not politeness here, it is the mechanism.
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


def main():
    if not supabase.enabled():
        print("No Supabase project configured; nothing to keep awake.")
        return 0

    last = ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            status, body = ping()
            if status == 200:
                print("Awake. ping returned %s" % body)
                if attempt > 1:
                    print("Took %d attempts - the project was probably asleep." % attempt)
                return 0
            last = "HTTP %s - %s" % (status, body)
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace").strip()
            last = "HTTP %s - %s" % (e.code, detail)
            # A 4xx is a real problem with the call, not a sleeping project, so
            # retrying it just wastes four minutes and reports the same thing.
            if 400 <= e.code < 500:
                print("Request rejected: %s" % last)
                return 1
        except Exception as e:  # timeout, DNS, TLS, connection reset
            last = "%s: %s" % (type(e).__name__, e)

        print("Attempt %d/%d failed (%s)" % (attempt, ATTEMPTS, last))
        if attempt < ATTEMPTS:
            time.sleep(BACKOFF)

    print("Could not reach %s after %d attempts. Last error: %s"
          % (supabase.URL, ATTEMPTS, last))
    return 1


if __name__ == "__main__":
    sys.exit(main())
