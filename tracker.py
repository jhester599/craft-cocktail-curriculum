# -*- coding: utf-8 -*-
# Progress tracking + notes UI (localStorage backed, works on GitHub Pages)

TRACK_CSS = '''
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

DASH_HTML = '''
  <section class="dash" id="dash">
    <div class="dash-top">
      <span class="dash-count"><b id="pcount">0</b> of 52 made</span>
      <span class="dash-sub" id="pnote">Nothing logged yet</span>
    </div>
    <div class="bar"><i id="pbar"></i></div>
    <div class="filters" role="group" aria-label="Filter drinks">
      <button data-filter="all" aria-pressed="true">All 52</button>
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
  var KEY = "bar52:v1";
  var data = {};
  try { data = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { data = {}; }

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
    document.getElementById("pbar").style.width = (made / 52 * 100) + "%";
    var rated = 0, sum = 0;
    for (var k in data) {
      if (data[k] && data[k].rating) { rated++; sum += data[k].rating; }
    }
    document.getElementById("pnote").textContent = made === 0
      ? "Nothing logged yet"
      : (52 - made) + " to go" + (rated ? " \u00b7 average rating " + (sum / rated).toFixed(1) : "");
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
    var payload = { app: "52-weeks-behind-the-bar", version: 1, saved: new Date().toISOString(), entries: data };
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
        var incoming = parsed.entries || parsed;
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
    if (!confirm("Erase every mark, rating and note? Download your notes first if you want a copy.")) return;
    data = {};
    try { localStorage.removeItem(KEY); } catch (e) {}
    fillNotes();
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

  fillNotes();
  render();
})();
</script>
'''

def track_block(n):
    return '''
      <div class="track">
        <div class="track-row">
          <button class="mk" data-id="%d" aria-pressed="false">
            <svg class="tick" viewBox="0 0 16 16" aria-hidden="true"><path d="m3 8.4 3.2 3.2L13 4.8"/></svg>
            <span>Mark as made</span>
          </button>
          <span class="stars" role="group" aria-label="Rating">
            <button data-id="%d" data-v="1" title="1 star" aria-label="1 star">&#9733;</button>
            <button data-id="%d" data-v="2" title="2 stars" aria-label="2 stars">&#9733;</button>
            <button data-id="%d" data-v="3" title="3 stars" aria-label="3 stars">&#9733;</button>
            <button data-id="%d" data-v="4" title="4 stars" aria-label="4 stars">&#9733;</button>
            <button data-id="%d" data-v="5" title="5 stars" aria-label="5 stars">&#9733;</button>
          </span>
          <span class="madeon"></span>
        </div>
        <textarea class="note" data-id="%d" rows="1"
          placeholder="Notes: what you changed, whose spec you liked, make it again?"></textarea>
      </div>''' % (n, n, n, n, n, n, n)
