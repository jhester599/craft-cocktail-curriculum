# -*- coding: utf-8 -*-
# Progress tracking + notes UI (localStorage backed, works on GitHub Pages)
#
# Storage is keyed by cocktail slug, never by position, so reordering or
# inserting a drink cannot reattach notes to the wrong cocktail. build.py
# passes the ordered slug list in; the displayed number is only a label.
import json

TRACK_CSS = '''
/* ---- own-this checkbox on each buying-guide row ---- */
.own{display:inline-flex;align-items:center;gap:8px;cursor:pointer;
  min-height:44px;padding:2px 2px;margin:-6px 0 6px;font-size:13.5px;color:var(--muted);
  -webkit-tap-highlight-color:transparent}
.own input{appearance:none;-webkit-appearance:none;margin:0;flex:none;
  width:20px;height:20px;border:1px solid var(--line);background:var(--panel-2);
  border-radius:2px;position:relative;cursor:pointer}
.own input:checked{border-color:var(--chart);background:var(--chart)}
.own input:checked::after{content:"";position:absolute;left:6px;top:2px;
  width:5px;height:10px;border:solid var(--ink);border-width:0 2px 2px 0;transform:rotate(45deg)}
.own input:focus-visible{outline:2px solid var(--chart);outline-offset:2px}
.own:hover{color:var(--bone)}
.brow.have{border-left:2px solid var(--chart)}
.brow.have .own{color:var(--chart)}

/* ---- what can I make tonight ---- */
.tonight{background:var(--panel);border:1px solid var(--line);
  border-left:2px solid var(--chart);padding:20px 18px;margin:0 0 18px}
.tonight h3{font-size:20px;margin:0 0 4px}
.tonight .tsub{color:var(--muted);font-size:14px;margin:0 0 14px}
.tonight .tgroup{margin-bottom:16px}
.tonight .tgroup:last-child{margin-bottom:0}
.tonight .tlab{display:block;font-size:12px;letter-spacing:.02em;color:var(--muted);
  margin-bottom:7px;text-transform:uppercase}
.tonight .tlab b{color:var(--chart);font-family:"Bodoni Moda",Georgia,serif;
  font-size:15px;letter-spacing:0}
.tonight ul{list-style:none;padding:0;margin:0;display:flex;flex-wrap:wrap;gap:6px}
.tonight li a{display:inline-block;text-decoration:none;font-size:14px;
  border:1px solid var(--line);background:var(--panel-2);padding:7px 11px;
  min-height:36px;line-height:20px}
.tonight li a:hover,.tonight li a:focus-visible{border-color:var(--chart);color:var(--chart)}
.tonight li .short{color:var(--brass);font-size:12.5px}
.tonight .tempty{color:var(--muted);font-size:14.5px;margin:0}
.tonight .tempty a{color:var(--chart)}

/* ---- progress dashboard ---- */
.dash{background:var(--panel);border:1px solid var(--line);padding:20px;margin:30px 0 0}
.dash-top{display:flex;flex-wrap:wrap;align-items:baseline;gap:10px;justify-content:space-between}
.dash-count{font-family:"Bodoni Moda",Georgia,serif;font-size:26px;font-optical-sizing:none;}
.dash-count b{color:var(--chart);font-weight:500}
.dash-sub{color:var(--muted);font-size:13.5px}
.bar{height:6px;background:var(--panel-2);border:1px solid var(--line);margin:14px 0 0;position:relative}
.bar i{display:block;height:100%;background:var(--chart);width:0}
.filters{display:flex;flex-wrap:wrap;gap:6px;margin-top:16px}
.filters button,.tools button,.tools label{font-family:inherit;font-size:12.5px;color:var(--muted);
  background:var(--panel-2);border:1px solid var(--line);padding:6px 14px;cursor:pointer;
  min-height:44px;display:inline-flex;align-items:center}
.filters button[aria-pressed="true"]{color:var(--ink);background:var(--chart);border-color:var(--chart)}
.filters button:hover,.tools button:hover,.tools label:hover{color:var(--chart);border-color:var(--chart)}
.filters button[aria-pressed="true"]:hover{color:var(--ink)}
.tools{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px;padding-top:14px;
  border-top:1px dotted var(--line)}
.tools input[type=file]{display:none}
.tools .danger:hover{color:var(--campari);border-color:var(--campari)}
.dash-note{color:var(--muted);font-size:12.5px;margin:12px 0 0;line-height:1.5}

/* ---- per-drink tracking ---- */
.track{margin-top:16px;padding-top:14px;border-top:1px dotted var(--line)}
.track-row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.mk{font-family:inherit;font-size:13px;color:var(--muted);background:var(--panel-2);
  border:1px solid var(--line);padding:7px 16px;cursor:pointer;display:inline-flex;
  align-items:center;gap:7px;min-height:44px}
.mk:hover{color:var(--chart);border-color:var(--chart)}
.mk[aria-pressed="true"]{color:var(--ink);background:var(--chart);border-color:var(--chart)}
.mk[aria-pressed="true"]:hover{color:var(--ink)}
.mk .tick{width:13px;height:13px;fill:none;stroke:currentColor;stroke-width:2}
.stars{display:inline-flex;gap:0}
.stars button{background:none;border:none;padding:0;cursor:pointer;color:var(--line);
  font-size:20px;line-height:1;font-family:inherit;min-width:44px;min-height:44px;
  display:inline-flex;align-items:center;justify-content:center}
.stars button.on{color:var(--brass)}
.stars button:hover{color:var(--chart)}
.madeon{font-size:12.5px;color:var(--muted)}
.note{width:100%;margin-top:10px;background:var(--panel-2);border:1px solid var(--line);
  color:var(--bone);font-family:inherit;font-size:14.5px;line-height:1.5;padding:10px 12px;
  resize:vertical;min-height:82px}
.note::placeholder{color:#5F6A5C}
.note:focus{border-color:var(--chart);outline:none}
.drink.done{border-left-color:var(--chart)}
.drink.hide{display:none}
.group.hide{display:none}
.saveflash{font-size:12px;color:var(--chart);opacity:0;transition:opacity .25s}
.saveflash.on{opacity:1}
@media (prefers-reduced-motion:reduce){.saveflash{transition:none}}
'''

_DASH_HTML = '''
  <section class="dash" id="dash">
    <div class="dash-top">
      <span class="dash-count"><b id="pcount">0</b> of %(total)d made</span>
      <span class="dash-sub" id="pnote">Nothing logged yet</span>
    </div>
    <div class="bar"><i id="pbar"></i></div>
    <div class="filters" role="group" aria-label="Filter drinks">
      <button data-filter="all" aria-pressed="true">All %(total)d</button>
      <button data-filter="todo" aria-pressed="false">Still to make</button>
      <button data-filter="done" aria-pressed="false">Made</button>
      <button data-filter="top" aria-pressed="false">Rated 4+</button>
      <button data-filter="noted" aria-pressed="false">Has notes</button>
    </div>
    <div class="tools">
      <button id="export">Download my notes</button>
      <label for="importfile">Restore from file</label>
      <input type="file" id="importfile" accept="application/json,.json">
      <button id="reset" class="danger">Clear everything</button>
      <span class="saveflash" id="flash">Saved</span>
    </div>
    <p class="dash-note">Progress and notes are stored in this browser only, so they stay
    private and work offline &mdash; but they do not follow you to another device or survive
    clearing site data. Download your notes now and then and commit the file to the repo as a
    backup; Restore reads it back in and merges it with whatever is already here.</p>
  </section>
'''

TRACK_JS = r'''
<script>
(function () {
  // Ordered slugs, build-time. Index i is the drink displayed as number i+1.
  var SLUGS = __SLUGS__;
  // slug -> list of OR-groups of bottle ids. [["b-bourbon","b-rye-100-proof"]]
  // means bourbon OR rye satisfies that requirement.
  var REQS = __REQS__;
  var BOTTLES = __BOTTLES__;
  var KEY = "bar52:v2";
  var OLD_KEY = "bar52:v1";
  // Which bottles you own. Separate key: it is about the shelf, not the drinks,
  // and losing one should never take the other with it.
  var OWN_KEY = "bar52:bottles:v1";

  function read(k) {
    try { return JSON.parse(localStorage.getItem(k) || "null"); } catch (e) { return null; }
  }

  // One-time migration. v1 keyed entries off the sequential drink number, so
  // the only way to interpret them is against the order that produced them -
  // which is the order still on the page. v1 is deliberately left in place.
  function migrate() {
    var v1 = read(OLD_KEY);
    if (!v1 || typeof v1 !== "object") return {};
    var out = {}, moved = 0;
    for (var k in v1) {
      if (!Object.prototype.hasOwnProperty.call(v1, k)) continue;
      var n = parseInt(k, 10);
      if (String(n) === String(k).trim() && n >= 1 && n <= SLUGS.length) {
        out[SLUGS[n - 1]] = v1[k];
        moved++;
      } else {
        // Already a slug, or something unrecognised - carry it across as-is
        // rather than drop it.
        out[k] = v1[k];
      }
    }
    if (moved || Object.keys(out).length) {
      try { localStorage.setItem(KEY, JSON.stringify(out)); } catch (e) {}
    }
    return out;
  }

  var data = read(KEY);
  if (!data || typeof data !== "object") data = migrate();

  var own = read(OWN_KEY);
  if (!own || typeof own !== "object") own = {};
  function saveOwn() {
    try { localStorage.setItem(OWN_KEY, JSON.stringify(own)); } catch (e) {}
  }

  var flash = document.getElementById("flash"), flashT;
  function save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(data));
      flash.classList.add("on");
      clearTimeout(flashT);
      flashT = setTimeout(function () { flash.classList.remove("on"); }, 1200);
    } catch (e) {
      flash.textContent = "Could not save - storage may be blocked";
      flash.classList.add("on");
    }
    render();
  }
  function rec(id) { return data[id] || (data[id] = {}); }

  function today() {
    var d = new Date();
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  var filter = "all";

  // A drink is makeable when every OR-group has at least one owned bottle.
  // Missing groups are reported by name so "one bottle short" can say which.
  function missingFor(slug) {
    var groups = REQS[slug] || [], out = [];
    for (var i = 0; i < groups.length; i++) {
      var g = groups[i], have = false;
      for (var j = 0; j < g.length; j++) if (own[g[j]]) { have = true; break; }
      if (!have) out.push(g);
    }
    return out;
  }

  function nameFor(group) {
    var names = [];
    for (var i = 0; i < group.length; i++) names.push(BOTTLES[group[i]] || group[i]);
    return names.join(" or ");
  }

  function renderTonight() {
    var box = document.getElementById("tonight");
    if (!box) return;
    var ownedCount = 0;
    for (var k in own) if (own[k]) ownedCount++;

    var now = [], oneShort = [];
    for (var i = 0; i < SLUGS.length; i++) {
      var slug = SLUGS[i];
      var card = document.querySelector('.drink[data-id="' + slug + '"]');
      if (!card) continue;
      var name = card.querySelector("h3") ? card.querySelector("h3").textContent : slug;
      var miss = missingFor(slug);
      if (miss.length === 0) now.push({ slug: slug, name: name });
      else if (miss.length === 1) oneShort.push({ slug: slug, name: name, need: nameFor(miss[0]) });
    }

    if (ownedCount === 0) {
      box.innerHTML =
        '<h3>What can I make tonight?</h3>' +
        '<p class="tempty">Tick <b>I have this</b> against the bottles on your shelf in ' +
        '<a href="#apxwrap">the buying guide</a>, and this will tell you which of the ' +
        SLUGS.length + ' you can make right now &mdash; and which are one bottle short.</p>';
      return;
    }

    function list(items, extra) {
      var out = '<ul>';
      for (var i = 0; i < items.length; i++) {
        out += '<li><a href="#' + items[i].slug + '">' + items[i].name +
               (extra ? ' <span class="short">&middot; ' + items[i].need + '</span>' : '') +
               '</a></li>';
      }
      return out + '</ul>';
    }

    var html =
      '<h3>What can I make tonight?</h3>' +
      '<p class="tsub">' + ownedCount + ' bottle' + (ownedCount === 1 ? '' : 's') +
      ' on the shelf.</p>';

    html += '<div class="tgroup"><span class="tlab"><b>' + now.length + '</b> ready to make now</span>';
    html += now.length ? list(now, false)
                       : '<p class="tempty">Nothing yet &mdash; keep ticking.</p>';
    html += '</div>';

    if (oneShort.length) {
      html += '<div class="tgroup"><span class="tlab"><b>' + oneShort.length +
              '</b> one bottle short</span>' + list(oneShort, true) + '</div>';
    }
    box.innerHTML = html;
  }

  function render() {
    var made = 0, cards = document.querySelectorAll(".drink");
    for (var i = 0; i < cards.length; i++) {
      var card = cards[i], id = card.dataset.id, r = data[id] || {};
      if (r.made) made++;
      card.classList.toggle("done", !!r.made);

      var btn = card.querySelector(".mk");
      btn.setAttribute("aria-pressed", r.made ? "true" : "false");
      btn.querySelector("span").textContent = r.made ? "Made it" : "Mark as made";

      var on = card.querySelector(".madeon");
      on.textContent = r.made && r.date ? r.date : "";

      var stars = card.querySelectorAll(".stars button");
      for (var s = 0; s < stars.length; s++) {
        stars[s].classList.toggle("on", (r.rating || 0) >= s + 1);
      }

      var show = filter === "all"
        || (filter === "todo" && !r.made)
        || (filter === "done" && !!r.made)
        || (filter === "top" && (r.rating || 0) >= 4)
        || (filter === "noted" && !!(r.note && r.note.trim()));
      card.classList.toggle("hide", !show);
    }

    var groups = document.querySelectorAll(".group");
    for (var g = 0; g < groups.length; g++) {
      var vis = groups[g].querySelectorAll(".drink:not(.hide)").length;
      groups[g].classList.toggle("hide", vis === 0);
    }

    document.getElementById("pcount").textContent = made;
    document.getElementById("pbar").style.width = (made / SLUGS.length * 100) + "%";
    var rated = 0, sum = 0;
    for (var k in data) {
      if (data[k] && data[k].rating) { rated++; sum += data[k].rating; }
    }
    document.getElementById("pnote").textContent = made === 0
      ? "Nothing logged yet"
      : (SLUGS.length - made) + " to go" + (rated ? " \u00b7 average rating " + (sum / rated).toFixed(1) : "");

    renderTonight();
  }

  document.addEventListener("click", function (e) {
    var mk = e.target.closest(".mk");
    if (mk) {
      var r = rec(mk.dataset.id);
      r.made = !r.made;
      if (r.made && !r.date) r.date = today();
      if (!r.made) delete r.date;
      save();
      return;
    }
    var st = e.target.closest(".stars button");
    if (st) {
      var rr = rec(st.dataset.id), v = parseInt(st.dataset.v, 10);
      rr.rating = rr.rating === v ? 0 : v;
      if (rr.rating && !rr.made) { rr.made = true; rr.date = rr.date || today(); }
      save();
      return;
    }
    var f = e.target.closest(".filters button");
    if (f) {
      filter = f.dataset.filter;
      var all = document.querySelectorAll(".filters button");
      for (var i = 0; i < all.length; i++) {
        all[i].setAttribute("aria-pressed", all[i] === f ? "true" : "false");
      }
      render();
    }
  });

  document.addEventListener("change", function (e) {
    var box = e.target.closest(".own input[data-bottle]");
    if (!box) return;
    var id = box.dataset.bottle;
    if (box.checked) own[id] = true; else delete own[id];
    var row = box.closest(".brow");
    if (row) row.classList.toggle("have", !!box.checked);
    saveOwn();
    renderTonight();
  });

  var noteT;
  document.addEventListener("input", function (e) {
    if (!e.target.classList.contains("note")) return;
    var el = e.target;
    el.style.height = "auto";
    el.style.height = el.scrollHeight + "px";
    clearTimeout(noteT);
    noteT = setTimeout(function () {
      var r = rec(el.dataset.id);
      r.note = el.value;
      if (!r.note) delete r.note;
      save();
    }, 500);
  });

  document.getElementById("export").addEventListener("click", function () {
    var payload = { app: "52-weeks-behind-the-bar", version: 2,
                    saved: new Date().toISOString(), entries: data, bottles: own };
    var blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "bar-notes-" + new Date().toISOString().slice(0, 10) + ".json";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  });

  document.getElementById("importfile").addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    if (!file) return;
    var fr = new FileReader();
    fr.onload = function () {
      try {
        var parsed = JSON.parse(fr.result);
        var raw = parsed.entries || parsed;
        var incoming = {};
        for (var key in raw) {
          if (!Object.prototype.hasOwnProperty.call(raw, key)) continue;
          var num = parseInt(key, 10);
          var mapped = (String(num) === String(key).trim() && num >= 1 && num <= SLUGS.length)
            ? SLUGS[num - 1] : key;
          incoming[mapped] = raw[key];
        }
        for (var id in incoming) {
          var a = data[id] || {}, b = incoming[id] || {};
          data[id] = {
            made: a.made || b.made || false,
            date: a.date || b.date,
            rating: Math.max(a.rating || 0, b.rating || 0) || undefined,
            note: [a.note, b.note].filter(function (n) { return n && n.trim(); })
                    .filter(function (n, i, arr) { return arr.indexOf(n) === i; })
                    .join("\n\n") || undefined
          };
        }
        // Older exports have no `bottles` key; absent means "nothing to merge",
        // never "the shelf is empty".
        if (parsed.bottles && typeof parsed.bottles === "object") {
          for (var b in parsed.bottles) {
            if (parsed.bottles[b]) own[b] = true;
          }
          saveOwn();
          fillOwn();
        }
        save();
        fillNotes();
        flash.textContent = "Restored";
      } catch (err) {
        flash.textContent = "That file could not be read";
        flash.classList.add("on");
      }
    };
    fr.readAsText(file);
    e.target.value = "";
  });

  document.getElementById("reset").addEventListener("click", function () {
    if (!confirm("Erase every mark, rating, note and owned bottle? Download your notes first if you want a copy.")) return;
    data = {};
    own = {};
    try { localStorage.removeItem(KEY); localStorage.removeItem(OWN_KEY); } catch (e) {}
    // v1 is left alone on purpose: it is the pre-migration backup.
    fillNotes();
    fillOwn();
    render();
  });

  function fillNotes() {
    var notes = document.querySelectorAll(".note");
    for (var i = 0; i < notes.length; i++) {
      var el = notes[i], r = data[el.dataset.id] || {};
      el.value = r.note || "";
      el.style.height = "auto";
      if (el.value) el.style.height = el.scrollHeight + "px";
    }
  }

  function fillOwn() {
    var boxes = document.querySelectorAll(".own input[data-bottle]");
    for (var i = 0; i < boxes.length; i++) {
      var el = boxes[i], has = !!own[el.dataset.bottle];
      el.checked = has;
      var row = el.closest(".brow");
      if (row) row.classList.toggle("have", has);
    }
  }

  fillNotes();
  fillOwn();
  render();
})();
</script>
'''

def dash_html(total):
    """Dashboard markup. Totals come from the build, not a hardcoded 52."""
    return _DASH_HTML % {"total": total}


def track_js(slugs, reqs, bottles):
    """The storage JS with the build's slugs, requirements and bottles baked in."""
    return (TRACK_JS
            .replace("__SLUGS__", json.dumps(list(slugs)))
            .replace("__REQS__", json.dumps(reqs, sort_keys=True))
            .replace("__BOTTLES__", json.dumps(bottles, sort_keys=True, ensure_ascii=False)))


def own_block(bottle_id):
    """The "I have this" checkbox for one buying-guide row."""
    return ('<label class="own"><input type="checkbox" data-bottle="%s">'
            '<span>I have this</span></label>' % bottle_id)


# Filled in by the tracker JS once it knows what is on the shelf.
TONIGHT_HTML = '<section class="tonight" id="tonight"></section>'



def track_block(slug):
    return '''
      <div class="track">
        <div class="track-row">
          <button class="mk" data-id="%s" aria-pressed="false">
            <svg class="tick" viewBox="0 0 16 16" aria-hidden="true"><path d="m3 8.4 3.2 3.2L13 4.8"/></svg>
            <span>Mark as made</span>
          </button>
          <span class="stars" role="group" aria-label="Rating">
            <button data-id="%s" data-v="1" title="1 star" aria-label="1 star">&#9733;</button>
            <button data-id="%s" data-v="2" title="2 stars" aria-label="2 stars">&#9733;</button>
            <button data-id="%s" data-v="3" title="3 stars" aria-label="3 stars">&#9733;</button>
            <button data-id="%s" data-v="4" title="4 stars" aria-label="4 stars">&#9733;</button>
            <button data-id="%s" data-v="5" title="5 stars" aria-label="5 stars">&#9733;</button>
          </span>
          <span class="madeon"></span>
        </div>
        <textarea class="note" data-id="%s" rows="1"
          placeholder="Notes: what you changed, whose spec you liked, make it again?"></textarea>
      </div>''' % (slug, slug, slug, slug, slug, slug, slug)
