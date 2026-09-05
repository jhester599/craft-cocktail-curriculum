# -*- coding: utf-8 -*-
"""A standalone diagnostic page for the sync backend.

The tracker's own tests drive sync against a mocked fetch, which proves the
merge logic but says nothing about whether the browser can actually reach
Supabase: CORS from the Pages origin, PostgREST accepting the argument names,
the grants behaving as schema.sql intends. None of that can be checked from the
build environment, which cannot reach supabase.co at all.

So this page runs those checks from wherever you open it, and says plainly which
passed. Open it on the real site to prove the real origin works; open it on a
phone to prove it works there too.

It writes one throwaway row under a random code and names that code so you can
delete it afterwards. It never touches a real profile's data.
"""

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sync check &middot; Fifty-Two Weeks Behind the Bar</title>
<style>
:root{--ink:#0D120F;--panel:#141B16;--panel-2:#1A231D;--line:#2A362D;
  --bone:#EDE7DA;--muted:#98A395;--chart:#C9DA4E;--campari:#D0503A;--brass:#C9A253}
*{box-sizing:border-box}
body{margin:0;background:var(--ink);color:var(--bone);font-size:16px;line-height:1.6;
  font-family:Karla,"Helvetica Neue",Arial,sans-serif;-webkit-text-size-adjust:100%%}
.wrap{max-width:720px;margin:0 auto;padding:40px 20px 80px}
h1{font-family:Georgia,"Times New Roman",serif;font-weight:500;font-size:30px;margin:0 0 6px}
.sub{color:var(--muted);margin:0 0 24px;font-size:15px}
button{font:inherit;font-size:15px;color:var(--ink);background:var(--chart);border:0;
  border-radius:2px;padding:0 20px;min-height:48px;cursor:pointer;font-weight:700}
button:disabled{opacity:.5;cursor:default}
.row{border:1px solid var(--line);background:var(--panel);border-left:2px solid var(--line);
  padding:14px 16px;margin:10px 0}
.row.ok{border-left-color:var(--chart)}
.row.bad{border-left-color:var(--campari)}
.row.run{border-left-color:var(--brass)}
.row h2{font-size:15px;margin:0 0 4px;font-weight:700}
.row p{margin:0;color:var(--muted);font-size:14px;word-break:break-word}
.tag{font-size:12px;letter-spacing:.04em;text-transform:uppercase;margin-right:8px}
.ok .tag{color:var(--chart)}.bad .tag{color:var(--campari)}.run .tag{color:var(--brass)}
.meta{margin-top:28px;border-top:1px dotted var(--line);padding-top:16px;
  color:var(--muted);font-size:13.5px}
code{background:var(--panel-2);border:1px solid var(--line);padding:1px 5px;font-size:13px}
.verdict{margin:24px 0 0;padding:16px;border:1px solid var(--line);background:var(--panel-2);
  display:none}
.verdict.show{display:block}
.verdict b{font-size:17px}
</style>
</head>
<body>
<div class="wrap">
  <h1>Sync check</h1>
  <p class="sub">Runs the sync backend end to end from this browser, on this origin.
  Writes one throwaway row under a random code, then tells you how to delete it.
  Your own notes are never touched.</p>

  <button id="run">Run the checks</button>
  <div id="out"></div>
  <div class="verdict" id="verdict"></div>

  <div class="meta">
    <p>Origin: <code id="origin"></code><br>
    Project: <code>%(url)s</code></p>
  </div>
</div>
<script>
(function () {
  var URL_ = %(url_json)s, KEY = %(key_json)s;
  var out = document.getElementById("out");
  document.getElementById("origin").textContent = window.location.origin;

  function row(title) {
    var el = document.createElement("div");
    el.className = "row run";
    el.innerHTML = '<h2><span class="tag">running</span>' + title + '</h2><p></p>';
    out.appendChild(el);
    return {
      pass: function (m) { el.className = "row ok";
        el.querySelector(".tag").textContent = "pass"; el.querySelector("p").textContent = m; },
      fail: function (m) { el.className = "row bad";
        el.querySelector(".tag").textContent = "fail"; el.querySelector("p").textContent = m; }
    };
  }

  function rpc(fn, body) {
    return fetch(URL_ + "/rest/v1/rpc/" + fn, {
      method: "POST",
      headers: { "apikey": KEY, "Authorization": "Bearer " + KEY,
                 "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.text().then(function (t) { return { ok: r.ok, status: r.status, text: t }; });
    });
  }

  function code() {
    var a = "ABCDEFGHJKMNPQRSTVWXYZ23456789", s = "";
    var v = new Uint32Array(26);
    window.crypto.getRandomValues(v);
    for (var i = 0; i < 26; i++) s += a.charAt(v[i] %% a.length);
    return s;
  }

  document.getElementById("run").addEventListener("click", function () {
    var btn = this;
    btn.disabled = true;
    out.innerHTML = "";
    document.getElementById("verdict").className = "verdict";
    var TEST = code(), failures = 0;

    function note(r, cond, good, bad) { if (cond) r.pass(good); else { r.fail(bad); failures++; } }

    var r1 = row("1. Reachable from this browser (ping)");
    rpc("ping", {}).then(function (res) {
      note(r1, res.ok && res.text.indexOf("ok:") !== -1,
           "Reached the project and ran ping. CORS from this origin is fine. " + res.text,
           "HTTP " + res.status + " - " + (res.text || "no response body"));

      var r2 = row("2. Writing a row (push)");
      return rpc("push", { p_code: TEST, p_payload: { version: 2, profile: "TST",
                   entries: { "last-word": { made: true, note: "sync check" } },
                   bottles: { "b-campari": true } } })
        .then(function (res2) {
          note(r2, res2.ok, "Wrote a throwaway row. " + res2.text,
               "HTTP " + res2.status + " - " + res2.text);

          var r3 = row("3. Reading it back (pull)");
          return rpc("pull", { p_code: TEST }).then(function (res3) {
            var got = null;
            try { got = JSON.parse(res3.text); } catch (e) {}
            var round = !!(got && got.entries && got.entries["last-word"] &&
                           got.bottles && got.bottles["b-campari"]);
            note(r3, res3.ok && round,
                 "Round trip intact: the notes and the shelf came back unchanged.",
                 "HTTP " + res3.status + " - " + res3.text);

            var r4 = row("4. Short codes rejected");
            return rpc("pull", { p_code: "short" }).then(function (res4) {
              note(r4, !res4.ok,
                   "Rejected, as it should be - guessing short codes is not an option.",
                   "ACCEPTED a 5-character code. The length guard in schema.sql is not active.");

              var r5 = row("5. The table itself is not readable");
              return fetch(URL_ + "/rest/v1/shelves?select=*", {
                headers: { "apikey": KEY, "Authorization": "Bearer " + KEY }
              }).then(function (res5) {
                return res5.text().then(function (t5) {
                  note(r5, !res5.ok,
                       "Refused, as it should be. Nobody can list the table and harvest codes.",
                       "READABLE - HTTP " + res5.status + " returned " + t5.slice(0, 120) +
                       " . Anyone with the key could enumerate every sync code. Fix the grants.");

                  var v = document.getElementById("verdict");
                  v.className = "verdict show";
                  v.innerHTML = failures === 0
                    ? "<b>All five passed.</b><br>Sync works from this browser on this origin. " +
                      "Delete the test row when you are done:<br><br><code>delete from " +
                      "public.shelves where code = '" + TEST + "';</code>"
                    : "<b>" + failures + " check" + (failures === 1 ? "" : "s") + " failed.</b><br>" +
                      "Details above. The test row, if it was written, is under " +
                      "<code>" + TEST + "</code>.";
                  btn.disabled = false;
                });
              });
            });
          });
        });
    }).catch(function (e) {
      var r = row("Unexpected error");
      r.fail(String(e && e.message || e) +
             " - a network-level failure here usually means CORS or DNS, not the schema.");
      btn.disabled = false;
    });
  });
})();
</script>
</body>
</html>
"""


def render(url, key):
    import json
    return PAGE % {"url": url, "url_json": json.dumps(url), "key_json": json.dumps(key)}
