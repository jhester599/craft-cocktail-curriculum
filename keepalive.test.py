# -*- coding: utf-8 -*-
"""Checks keepalive.py's branching without touching the network.

The interesting case is a project that is asleep: the first requests fail while
it wakes, and the retry is the mechanism that wakes it rather than politeness.
A version that gave up on the first timeout would report a healthy project as
broken every time it had been idle.

Run: python3 keepalive.test.py
"""

import io
import sys
import urllib.error
from unittest import mock

import keepalive
import supabase

fail = 0


def check(label, cond):
    global fail
    print(("PASS" if cond else "FAIL") + "  " + label)
    if not cond:
        fail += 1


class Resp:
    def __init__(self, status, body):
        self.status, self._body = status, body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def run(urlopen, configured=True):
    """Run main() with the network stubbed and backoff removed."""
    buf, real = io.StringIO(), sys.stdout
    sys.stdout = buf
    try:
        with mock.patch.object(supabase, "URL", supabase.URL if configured else ""), \
             mock.patch.object(keepalive, "BACKOFF", 0), \
             mock.patch("urllib.request.urlopen", urlopen):
            return keepalive.main(), buf.getvalue()
    finally:
        sys.stdout = real


healthy = lambda *a, **k: Resp(200, b"ok:0")


def unauthorized(*a, **k):
    raise urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b"bad key"))


def unavailable(*a, **k):
    raise urllib.error.HTTPError("u", 503, "Unavailable", {}, io.BytesIO(b"waking"))


def unreachable(*a, **k):
    raise TimeoutError("timed out")


code, out = run(healthy)
check("a healthy project exits 0", code == 0)
check("and says it is awake", "Awake" in out)

code, out = run(healthy, configured=False)
check("an unconfigured project is not a failure", code == 0)
check("and says there is nothing to keep awake", "nothing to keep awake" in out)

calls = {"n": 0}


def wakes_on_third(*a, **k):
    calls["n"] += 1
    if calls["n"] < 3:
        raise TimeoutError("timed out")
    return Resp(200, b"ok:0")


code, out = run(wakes_on_third)
check("a sleeping project is woken by the retries", code == 0)
check("and the wake is reported, not hidden", "attempts" in out)

code, out = run(unauthorized)
check("a rejected request fails", code == 1)
check("a 4xx is not retried - it will not fix itself",
      out.count("Attempt") == 0 and "401" in out)

code, out = run(unavailable)
check("a persistent 5xx fails after retrying", code == 1)
check("and it did retry", out.count("Attempt") == keepalive.ATTEMPTS)

code, out = run(unreachable)
check("an unreachable project fails", code == 1)
check("and names the project it could not reach", supabase.URL in out)

print("\n%d FAILURES" % fail if fail else "\nAll checks passed")
sys.exit(1 if fail else 0)
