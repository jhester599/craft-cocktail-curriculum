import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
const html = readFileSync('docs/index.html','utf8');

// Storage is namespaced per profile; a fresh load creates the default "YOU".
const PROFILE = 'YOU';
const KEY = `bar52:v2:${PROFILE}`;
const OWN = `bar52:bottles:v1:${PROFILE}`;
const OLD_KEY = 'bar52:v1';

let fail = 0;
const ok = (label, cond) => { console.log((cond?'PASS':'FAIL')+'  '+label); if(!cond) fail++; };

// Build a document, optionally seeding localStorage *before* the inline
// tracker script runs, which is what the migration path needs.
function load(seed) {
  const dom = new JSDOM(html, {
    runScripts: 'dangerously',
    url: 'https://example.com/',
    beforeParse(window) {
      if (seed) for (const [k, v] of Object.entries(seed)) {
        window.localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
      }
      // jsdom does not implement prompt and logs a stack trace per call. The
      // first-run flow calls it, so stub it: null is "dismissed", which is the
      // behaviour every test outside the first-run block expects.
      window.prompt = () => null;
    },
  });
  return dom;
}

const dom = load();
const { window } = dom;
const d = window.document;
function q(s){ return d.querySelector(s); }

ok('dashboard rendered', !!q('#dash'));
ok('52 tracking blocks', d.querySelectorAll('.track').length === 52);
ok('starts at 0 made', q('#pcount').textContent === '0');

// mark the Boulevardier (drink 5) as made
const card5 = d.querySelector('.drink[data-id="boulevardier"]');
card5.querySelector('.mk').click();
ok('count increments', q('#pcount').textContent === '1');
ok('card marked done', card5.classList.contains('done'));
ok('date stamped', card5.querySelector('.madeon').textContent.length > 0);
ok('button label flips', card5.querySelector('.mk span').textContent === 'Made it');
ok('progress bar moves', q('#pbar').style.width !== '0px' && q('#pbar').style.width !== '');

// rate the Old Pal (drink 9) four stars -> should auto-mark made
const card9 = d.querySelector('.drink[data-id="old-pal"]');
card9.querySelectorAll('.stars button')[3].click();
ok('rating auto-marks made', q('#pcount').textContent === '2');
ok('4 stars lit', card9.querySelectorAll('.stars button.on').length === 4);
ok('avg rating shown', /average rating 4\.0/.test(q('#pnote').textContent));

// filters
d.querySelector('.filters button[data-filter="done"]').click();
ok('filter done shows 2', d.querySelectorAll('.drink:not(.hide)').length === 2);
ok('empty groups hidden', d.querySelectorAll('.group.hide').length > 0);
d.querySelector('.filters button[data-filter="top"]').click();
ok('filter rated4+ shows 1', d.querySelectorAll('.drink:not(.hide)').length === 1);
d.querySelector('.filters button[data-filter="all"]').click();
ok('filter all restores 52', d.querySelectorAll('.drink:not(.hide)').length === 52);

// persistence, now keyed by slug
const raw = window.localStorage.getItem(KEY);
ok('written to localStorage', !!raw && JSON.parse(raw)['boulevardier'].made === true);
ok('no positional keys written', !!raw && !Object.keys(JSON.parse(raw)).some(k => /^\d+$/.test(k)));

// unmark
card5.querySelector('.mk').click();
ok('unmark decrements', q('#pcount').textContent === '1');
ok('date cleared', card5.querySelector('.madeon').textContent === '');

// reload with existing storage -> state actually restored
{
  const dom2 = load({ [KEY]: raw });
  const d2 = dom2.window.document;
  ok('survives reload (state restored)',
     d2.querySelector('#pcount').textContent === '2'
     && d2.querySelector('.drink[data-id="boulevardier"]').classList.contains('done'));
}

// ---------------------------------------------------------------------------
// Migration: v1 keyed notes off the sequential drink number.
// ---------------------------------------------------------------------------
console.log('\n-- migration --');

const v1 = {
  '1':  { made: true, date: 'Sep 1, 2026', rating: 5, note: 'the blueprint' },
  '9':  { made: true, date: 'Sep 2, 2026', rating: 3 },
  '52': { made: true, date: 'Sep 3, 2026', note: 'showpiece' },
};

{
  const m = load({ [OLD_KEY]: v1 });
  const w = m.window, dm = w.document;
  const out = JSON.parse(w.localStorage.getItem(KEY) || '{}');

  ok('v1 migrated to v2 on first load', Object.keys(out).length === 3);
  ok('numeric 1 maps to first drink by order', !!out['last-word'] && out['last-word'].rating === 5);
  ok('numeric 9 maps to ninth drink by order', !!out['old-pal'] && out['old-pal'].date === 'Sep 2, 2026');
  ok('numeric 52 maps to last drink by order', !!out['clarified-milk-punch'] && out['clarified-milk-punch'].note === 'showpiece');
  ok('notes survive the move', out['last-word'].note === 'the blueprint');
  ok('no numeric keys remain', !Object.keys(out).some(k => /^\d+$/.test(k)));

  // v1 is a backup, not something to consume and delete
  ok('v1 left in place', !!w.localStorage.getItem(OLD_KEY));
  ok('v1 unchanged', JSON.stringify(JSON.parse(w.localStorage.getItem(OLD_KEY))) === JSON.stringify(v1));

  // and the migrated state is actually on screen
  ok('migrated state renders', dm.querySelector('#pcount').textContent === '3');
  ok('migrated card marked done', dm.querySelector('.drink[data-id="last-word"]').classList.contains('done'));
  ok('migrated note fills textarea',
     dm.querySelector('.drink[data-id="last-word"] .note').value === 'the blueprint');
}

// runs once: an existing v2 wins and v1 is ignored
{
  const m = load({
    [OLD_KEY]: v1,
    [KEY]: { 'paper-plane': { made: true, date: 'Sep 4, 2026' } },
  });
  const w = m.window;
  const out = JSON.parse(w.localStorage.getItem(KEY) || '{}');
  ok('migration does not re-run over v2', !out['last-word'] && !!out['paper-plane']);
  ok('v2 count reflects v2 only', m.window.document.querySelector('#pcount').textContent === '1');
}

// unmappable keys are carried across rather than dropped
{
  const m = load({ [OLD_KEY]: { '99': { made: true }, 'already-a-slug': { made: true } } });
  const out = JSON.parse(m.window.localStorage.getItem(KEY) || '{}');
  ok('out-of-range key preserved', !!out['99']);
  ok('slug-shaped key preserved', !!out['already-a-slug']);
}

// a file exported from v1 restores onto the right drinks
{
  const m = load();
  const w = m.window, dm = w.document;
  const payload = { app: '52-weeks-behind-the-bar', version: 1, entries: v1 };

  // drive the import handler directly with a stubbed FileReader
  const realFR = w.FileReader;
  w.FileReader = class {
    readAsText() { this.result = JSON.stringify(payload); this.onload(); }
  };
  const input = dm.getElementById('importfile');
  Object.defineProperty(input, 'files', { value: [{ name: 'notes.json' }], configurable: true });
  input.dispatchEvent(new w.Event('change'));
  w.FileReader = realFR;

  const out = JSON.parse(w.localStorage.getItem(KEY) || '{}');
  ok('v1 export imports onto slugs', !!out['last-word'] && !!out['clarified-milk-punch']);
  ok('imported note lands on right drink', out['last-word'].note === 'the blueprint');
  ok('import writes no numeric keys', !Object.keys(out).some(k => /^\d+$/.test(k)));
}

// ---------------------------------------------------------------------------
// OHLQ links: product page, category shelf, grocery tag, no dead ends
// ---------------------------------------------------------------------------
{
  const hrefs = [...d.querySelectorAll('a[href]')].map(a => a.getAttribute('href'));
  const ohlq = hrefs.filter(h => h.startsWith('https://www.ohlq.com/'));

  ok('every bottle links to ohlq.com directly', ohlq.length > 100);
  ok('no google site: search hops remain',
     !hrefs.some(h => h.includes('site%3Aohlq.com') || h.includes('site:ohlq.com')));
  ok('every ohlq link is under /liquor/',
     ohlq.every(h => h.startsWith('https://www.ohlq.com/liquor/')));

  // A confirmed product page, whose slug is nothing like the brand string.
  const bottleLink = name => {
    const el = [...d.querySelectorAll('.bname')].find(n => n.textContent === name);
    return el && el.parentElement.querySelector('a[href*="ohlq.com"]');
  };
  ok('confirmed product resolves to its product page',
     bottleLink('Smith & Cross')?.getAttribute('href')
       === 'https://www.ohlq.com/liquor/rum/dark/smith-cross-traditional-jamaica-rum');

  // Unharvested bottles fall back to the category shelf rather than a dead link.
  ok('unharvested bottle falls back to its category',
     bottleLink('Cimarrón Blanco')?.getAttribute('href')
       === 'https://www.ohlq.com/liquor/tequila?producttype=blanco');

  // Regression: wave_html used to hand every wave bottle an OHLQ link, even the
  // under-21% ABV ones the appendix sends to a grocery store.
  const waves = d.querySelector('.waves');
  const waveBottle = name =>
    [...waves.querySelectorAll('.bname')].find(n => n.textContent === name)?.parentElement;
  ok('low-ABV wave bottle shows the grocery tag',
     !!waveBottle('Aperol')?.querySelector('.offsale'));
  ok('low-ABV wave bottle has no OHLQ link',
     !waveBottle('Aperol')?.querySelector('a[href*="ohlq.com"]'));
  ok('spirit wave bottle still links to OHLQ',
     !!waveBottle('Campari')?.querySelector('a[href*="ohlq.com"]'));

  // Regression: "Homemade" is a technique, not a bottle to go and buy.
  const homemade = [...d.querySelectorAll('.bname')].filter(n => /^Homemade/.test(n.textContent));
  ok('homemade rows exist', homemade.length > 0);
  ok('homemade rows offer no shopping links',
     homemade.every(n => n.parentElement.querySelectorAll('a').length === 0));
}

// ---------------------------------------------------------------------------
// Video links: one per drink, well formed, consistent channel naming
// ---------------------------------------------------------------------------
{
  const cards = [...d.querySelectorAll('.drink')];
  const vids = cards.map(c => c.querySelector('a.video'));
  ok('every drink has a video link', vids.every(Boolean));
  ok('no "no strong match" notes remain', d.querySelectorAll('.novideo').length === 0);
  ok('every video href is a youtube url',
     vids.filter(Boolean).every(a => /^https:\/\/www\.youtube\.com\//.test(a.getAttribute('href'))));
  ok('every video link names its channel',
     vids.filter(Boolean).every(a => /Watch · .+/.test(a.textContent)));

  // Same channel spelled two ways once shipped as two different names.
  const channels = new Set(vids.filter(Boolean)
    .map(a => a.textContent.replace(/^.*Watch · /, '').trim()));
  ok('channel naming is not split by spelling',
     !([...channels].some(c => c.startsWith('Truffle ')) &&
       [...channels].some(c => c.startsWith('Truffles '))));
}

// ---------------------------------------------------------------------------
// What can I make tonight: ownership checkboxes and makeability
// ---------------------------------------------------------------------------
{
  const OWN_KEY = OWN;
  const tick = (w, id) => {
    const box = w.document.querySelector(`.own input[data-bottle="${id}"]`);
    box.checked = true;
    box.dispatchEvent(new w.Event('change', { bubbles: true }));
    return box;
  };
  const panelText = w => w.document.getElementById('tonight').textContent;
  const listed = w => [...w.document.querySelectorAll('#tonight a[href^="#"]')]
    .map(a => a.getAttribute('href').slice(1));

  {
    const { window: w } = load();
    ok('every buying-guide row has an ownership checkbox',
       w.document.querySelectorAll('.brow').length ===
       w.document.querySelectorAll('.own input[data-bottle]').length);
    ok('tonight panel exists', !!w.document.getElementById('tonight'));
    ok('empty shelf shows the prompt, not a zero list',
       /Tick/.test(panelText(w)) && !/ready to make now/.test(panelText(w)));
  }

  // Last Word = gin + green Chartreuse + maraschino. Tick all three.
  {
    const { window: w } = load();
    tick(w, 'b-london-dry-gin');
    tick(w, 'b-green-chartreuse');
    ok('two of three bottles leaves it one short',
       /one bottle short/.test(panelText(w)) && listed(w).includes('last-word'));
    ok('the missing bottle is named', /Maraschino liqueur/.test(panelText(w)));

    tick(w, 'b-maraschino-liqueur');
    ok('all three bottles makes it makeable',
       /ready to make now/.test(panelText(w)) && listed(w).includes('last-word'));
    ok('a makeable drink is no longer listed as short',
       !/Maraschino liqueur/.test(panelText(w)));
  }

  // OR-group: the Boulevardier takes bourbon OR rye, plus vermouth and Campari.
  {
    const { window: w } = load();
    tick(w, 'b-sweet-vermouth');
    tick(w, 'b-campari');
    tick(w, 'b-rye-100-proof');
    ok('rye alone satisfies the "bourbon or rye" requirement',
       listed(w).includes('boulevardier') && /ready to make now/.test(panelText(w)));
  }
  {
    const { window: w } = load();
    tick(w, 'b-sweet-vermouth');
    tick(w, 'b-campari');
    tick(w, 'b-bourbon');
    ok('bourbon alone satisfies it too', listed(w).includes('boulevardier'));
  }

  // Persistence and round-trip.
  {
    const { window: w } = load();
    tick(w, 'b-campari');
    const saved = JSON.parse(w.localStorage.getItem(OWN_KEY) || '{}');
    ok('ownership persists under its own key', saved['b-campari'] === true);
    ok('ownership does not leak into the notes key',
       !('b-campari' in JSON.parse(w.localStorage.getItem(KEY) || '{}')));
  }
  {
    const { window: w } = load({ [OWN]: { 'b-campari': true } });
    ok('saved ownership restores the checkbox on load',
       w.document.querySelector('.own input[data-bottle="b-campari"]').checked === true);
    ok('an owned row is marked', !!w.document.querySelector('.brow#b-campari.have'));
  }

  // Export/restore has to carry the shelf, or a restore silently empties it.
  {
    const { window: w } = load();
    tick(w, 'b-campari');
    let captured = null;
    w.Blob = class { constructor(parts) { captured = parts.join(''); } };
    w.URL.createObjectURL = () => 'blob:x';
    w.URL.revokeObjectURL = () => {};
    // The download anchor's click would make jsdom attempt a real navigation,
    // which it cannot do and reports as a stack trace long after the assertion
    // has passed. Silence it so a genuine failure is not buried in noise.
    w.HTMLAnchorElement.prototype.click = function () {};
    w.document.getElementById('export').click();
    const payload = JSON.parse(captured);
    ok('export carries owned bottles', payload.bottles && payload.bottles['b-campari'] === true);
    ok('export still carries drink entries', 'entries' in payload);
  }
  {
    const { window: w } = load();
    const file = JSON.stringify({ app: '52-weeks-behind-the-bar', version: 2,
                                  entries: {}, bottles: { 'b-campari': true } });
    const realFR = w.FileReader;
    w.FileReader = class { readAsText() { this.result = file; this.onload(); } };
    const input = w.document.getElementById('importfile');
    Object.defineProperty(input, 'files', { value: [{ name: 'n.json' }], configurable: true });
    input.dispatchEvent(new w.Event('change'));
    w.FileReader = realFR;
    ok('restore merges owned bottles',
       JSON.parse(w.localStorage.getItem(OWN_KEY) || '{}')['b-campari'] === true);
    ok('restore ticks the checkbox it merged',
       w.document.querySelector('.own input[data-bottle="b-campari"]').checked === true);
  }
  {
    // A pre-ownership export has no `bottles` key; that must not wipe the shelf.
    const { window: w } = load({ [OWN]: { 'b-campari': true } });
    const file = JSON.stringify({ app: '52-weeks-behind-the-bar', version: 2, entries: {} });
    const realFR = w.FileReader;
    w.FileReader = class { readAsText() { this.result = file; this.onload(); } };
    const input = w.document.getElementById('importfile');
    Object.defineProperty(input, 'files', { value: [{ name: 'n.json' }], configurable: true });
    input.dispatchEvent(new w.Event('change'));
    w.FileReader = realFR;
    ok('restoring an older export leaves the shelf alone',
       JSON.parse(w.localStorage.getItem(OWN_KEY) || '{}')['b-campari'] === true);
  }
  {
    const { window: w } = load({ [OWN]: { 'b-campari': true } });
    w.confirm = () => true;
    w.document.getElementById('reset').click();
    ok('reset clears the shelf too', !w.localStorage.getItem(OWN_KEY));
    ok('reset unticks the checkboxes',
       w.document.querySelector('.own input[data-bottle="b-campari"]').checked === false);
  }

  // Clarified Milk Punch asks for "12 oz spirit", so it needs no specific bottle.
  {
    const { window: w } = load({ [OWN]: { 'b-campari': true } });
    ok('a drink with no bottle requirements is always makeable',
       listed(w).includes('clarified-milk-punch'));
  }
}

// ---------------------------------------------------------------------------
// Profiles: several people, one device
// ---------------------------------------------------------------------------
{
  const pick = (w, who) => {
    const sel = w.document.getElementById('profile');
    sel.value = who;
    sel.dispatchEvent(new w.Event('change', { bubbles: true }));
  };

  {
    const { window: w } = load();
    ok('a default profile exists',
       JSON.parse(w.localStorage.getItem('bar52:profiles') || '[]')[0] === PROFILE);
    ok('the picker lists it', w.document.getElementById('profile').value === PROFILE);
  }

  // Adoption: data saved before profiles existed belongs to someone.
  {
    const { window: w } = load({
      'bar52:v2': { 'jungle-bird': { made: true, note: 'keep me' } },
      'bar52:bottles:v1': { 'b-campari': true },
    });
    const adopted = JSON.parse(w.localStorage.getItem(KEY) || '{}');
    ok('pre-profile notes are adopted, not stranded',
       adopted['jungle-bird'] && adopted['jungle-bird'].note === 'keep me');
    ok('pre-profile shelf is adopted',
       JSON.parse(w.localStorage.getItem(OWN) || '{}')['b-campari'] === true);
    ok('the pre-profile keys are left as a backup',
       !!w.localStorage.getItem('bar52:v2') && !!w.localStorage.getItem('bar52:bottles:v1'));
  }

  // Adoption must not re-run over a profile that already has data.
  {
    const { window: w } = load({
      'bar52:v2': { 'jungle-bird': { made: true, note: 'old' } },
      [KEY]: { 'last-word': { made: true, note: 'newer' } },
    });
    const kept = JSON.parse(w.localStorage.getItem(KEY) || '{}');
    ok('adoption never overwrites an existing profile',
       kept['last-word'] && kept['last-word'].note === 'newer' && !kept['jungle-bird']);
  }

  // Isolation is the whole point.
  {
    const { window: w } = load({
      'bar52:profiles': ['JRH', 'ABC'],
      'bar52:current': 'JRH',
      'bar52:v2:JRH': { 'last-word': { made: true, note: 'mine' } },
      'bar52:bottles:v1:JRH': { 'b-campari': true },
      'bar52:v2:ABC': {},
    });
    ok('starts on the remembered profile', w.document.getElementById('pcount').textContent === '1');
    ok('three-letter initials are supported',
       [...w.document.getElementById('profile').options].map(o => o.value).join() === 'JRH,ABC');

    pick(w, 'ABC');
    ok('switching shows the other profile as empty',
       w.document.getElementById('pcount').textContent === '0');
    ok('the shelf switches too',
       w.document.querySelector('.own input[data-bottle="b-campari"]').checked === false);
    ok('notes do not bleed across profiles',
       w.document.querySelector('.note[data-id="last-word"]').value === '');
    ok('the switch is remembered', w.localStorage.getItem('bar52:current') === 'ABC');

    pick(w, 'JRH');
    ok('switching back restores the first profile',
       w.document.getElementById('pcount').textContent === '1' &&
       w.document.querySelector('.note[data-id="last-word"]').value === 'mine');
  }

  // Writing under one profile must not touch another.
  {
    const { window: w } = load({
      'bar52:profiles': ['JRH', 'ABC'],
      'bar52:current': 'ABC',
      'bar52:v2:JRH': { 'last-word': { made: true } },
    });
    w.document.querySelector('.drink[data-id="jungle-bird"] .mk').click();
    ok('a write lands in the current profile',
       !!JSON.parse(w.localStorage.getItem('bar52:v2:ABC') || '{}')['jungle-bird']);
    ok('a write leaves other profiles alone',
       JSON.stringify(JSON.parse(w.localStorage.getItem('bar52:v2:JRH'))) ===
       JSON.stringify({ 'last-word': { made: true } }));
  }

  // Reset is scoped to the person in front of you.
  {
    const { window: w } = load({
      'bar52:profiles': ['JRH', 'ABC'],
      'bar52:current': 'ABC',
      'bar52:v2:JRH': { 'last-word': { made: true } },
      'bar52:v2:ABC': { 'jungle-bird': { made: true } },
    });
    w.confirm = () => true;
    w.document.getElementById('reset').click();
    ok('reset clears the current profile', !w.localStorage.getItem('bar52:v2:ABC'));
    ok('reset spares the others', !!w.localStorage.getItem('bar52:v2:JRH'));
  }

  // Export should say who it belongs to, so a restore cannot land blind.
  {
    const { window: w } = load({ 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH' });
    let captured = null;
    w.Blob = class { constructor(parts) { captured = parts.join(''); } };
    w.URL.createObjectURL = () => 'blob:x';
    w.URL.revokeObjectURL = () => {};
    // The download anchor's click would make jsdom attempt a real navigation,
    // which it cannot do and reports as a stack trace long after the assertion
    // has passed. Silence it so a genuine failure is not buried in noise.
    w.HTMLAnchorElement.prototype.click = function () {};
    w.document.getElementById('export').click();
    ok('export names its profile', JSON.parse(captured).profile === 'JRH');
  }
}

// ---------------------------------------------------------------------------
// Cross-device sync (Supabase RPC, mocked - the real endpoint is not a test
// dependency and is unreachable from some environments anyway)
// ---------------------------------------------------------------------------
{
  const CODE = 'ABCDEFGHJKMNPQRSTVWXYZ2345';
  const settle = () => new Promise(r => setTimeout(r, 0));

  // Load with fetch stubbed. `remote` is what pull() returns; every call made
  // is recorded so we can assert on what actually went over the wire.
  function loadSync(seed, remote, opts = {}) {
    const calls = [];
    const dom = new JSDOM(html, {
      runScripts: 'dangerously',
      url: 'https://example.com/',
      beforeParse(window) {
        window.prompt = () => null;
        for (const [k, v] of Object.entries(seed || {})) {
          window.localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
        }
        window.fetch = (url, init) => {
          const fn = String(url).split('/rpc/')[1];
          const body = JSON.parse(init.body);
          calls.push({ fn, body, headers: init.headers });
          if (opts.fail) return Promise.resolve({ ok: false, status: 500 });
          return Promise.resolve({
            ok: true, status: 200,
            json: () => Promise.resolve(fn === 'pull' ? (remote || {}) : '2026-09-05T00:00:00Z'),
          });
        };
      },
    });
    return { window: dom.window, calls };
  }

  ok('sync controls are rendered when configured',
     !!d.getElementById('syncnow') && !!d.getElementById('synccode'));

  // No code: nothing should go over the wire.
  {
    const { window: w, calls } = loadSync({}, {});
    w.document.getElementById('syncnow').click();
    await settle();
    ok('no sync code means no network call', calls.length === 0);
    ok('and the page says so', /No sync code/.test(w.document.getElementById('syncstat').textContent));
  }

  // With a code, a sync pulls then pushes.
  {
    const { window: w, calls } = loadSync(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': CODE },
      { entries: {}, bottles: {} });
    await settle(); await settle();
    ok('a stored code syncs on load', calls.length >= 1 && calls[0].fn === 'pull');
    ok('pull sends the code', calls[0].body.p_code === CODE);
    ok('the key is sent as apikey and bearer',
       calls[0].headers.apikey.startsWith('sb_publishable_') &&
       calls[0].headers.Authorization === 'Bearer ' + calls[0].headers.apikey);
    const push = calls.find(c => c.fn === 'push');
    ok('push follows pull', !!push);
    ok('push names the profile', push.body.p_payload.profile === 'JRH');
  }

  // The merge is a union, not last-write-wins.
  {
    const { window: w, calls } = loadSync(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': CODE,
        'bar52:v2:JRH': { 'last-word': { made: true, note: 'mine' } },
        'bar52:bottles:v1:JRH': { 'b-campari': true } },
      { entries: { 'jungle-bird': { made: true, note: 'theirs' } },
        bottles: { 'b-suze': true } });
    await settle(); await settle();
    const local = JSON.parse(w.localStorage.getItem('bar52:v2:JRH') || '{}');
    ok('remote-only drinks arrive', !!local['jungle-bird']);
    ok('local-only drinks survive', !!local['last-word']);
    const shelf = JSON.parse(w.localStorage.getItem('bar52:bottles:v1:JRH') || '{}');
    ok('shelves are unioned', shelf['b-campari'] === true && shelf['b-suze'] === true);
    ok('the merged state is what gets pushed',
       !!calls.find(c => c.fn === 'push' && c.body.p_payload.entries['jungle-bird']
                                         && c.body.p_payload.entries['last-word']));
  }

  // Both sides edited the same note: keep both rather than drop one.
  {
    const { window: w } = loadSync(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': CODE,
        'bar52:v2:JRH': { 'last-word': { made: true, note: 'too sweet' } } },
      { entries: { 'last-word': { made: true, note: 'more lime' } } });
    await settle(); await settle();
    const note = JSON.parse(w.localStorage.getItem('bar52:v2:JRH'))['last-word'].note;
    ok('conflicting notes are kept, not dropped',
       note.includes('too sweet') && note.includes('more lime'));
  }

  // A failed sync must never damage what is on the device.
  {
    const { window: w } = loadSync(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': CODE,
        'bar52:v2:JRH': { 'last-word': { made: true, note: 'mine' } } },
      {}, { fail: true });
    await settle(); await settle();
    ok('a failed sync leaves local data intact',
       JSON.parse(w.localStorage.getItem('bar52:v2:JRH'))['last-word'].note === 'mine');
    ok('and says so without claiming loss',
       /Sync failed/.test(w.document.getElementById('syncstat').textContent) &&
       /safe/.test(w.document.getElementById('syncstat').textContent));
  }

  // rpc() can throw synchronously, before any promise exists to catch on. That
  // used to escape the handler and surface as an uncaught page error.
  {
    const dom = new JSDOM(html, {
      runScripts: 'dangerously', url: 'https://example.com/',
      beforeParse(w) {
        w.prompt = () => null;
        w.localStorage.setItem('bar52:code:YOU', CODE);
        w.fetch = () => { throw new Error('boom'); };
      },
    });
    const stat = dom.window.document.getElementById('syncstat');
    ok('a synchronous fetch failure is caught, not thrown',
       /Sync failed \(boom\)/.test(stat.textContent));
    ok('and it still says local data is safe', /safe/.test(stat.textContent));
  }
  {
    const dom = new JSDOM(html, {
      runScripts: 'dangerously', url: 'https://example.com/',
      beforeParse(w) { w.prompt = () => null; w.localStorage.setItem('bar52:code:YOU', CODE); },
    });
    ok('a browser with no fetch says so rather than erroring',
       /cannot sync/.test(dom.window.document.getElementById('syncstat').textContent));
  }

  // Codes are per profile: one person's code must not sync another's notes.
  {
    const { window: w, calls } = loadSync(
      { 'bar52:profiles': ['JRH', 'ABC'], 'bar52:current': 'ABC',
        'bar52:code:JRH': CODE },
      {});
    await settle();
    ok('a profile without a code does not sync', calls.length === 0);
  }
}

// ---------------------------------------------------------------------------
// "Start here" onboarding link
// ---------------------------------------------------------------------------
{
  const link = w => w.document.getElementById('starthere');

  {
    const { window: w } = load();
    ok('the start-here link exists', !!link(w));
    ok('it sits with the profile controls', !!link(w).closest('.who'));
    ok('it points at the guide', link(w).getAttribute('href') === 'start.html');
    ok('a first visit gets the emphasised version', link(w).classList.contains('new'));
  }

  // Someone mid-way through the year does not need it shouting at them.
  {
    const { window: w } = load({ [KEY]: { 'last-word': { made: true } } });
    ok('it quietens down once there are notes', !link(w).classList.contains('new'));
  }
  {
    const { window: w } = load({ 'bar52:code:YOU': 'ABCDEFGHJKMNPQRSTVWXYZ2345' });
    ok('a configured sync code also quietens it', !link(w).classList.contains('new'));
  }

  // The guide itself has to survive being generated.
  {
    const guide = readFileSync('docs/start.html', 'utf8');
    const g = new JSDOM(guide).window.document;
    ok('the guide has a title', /Start here/.test(g.querySelector('title').textContent));
    ok('the guide links back to the drinks',
       [...g.querySelectorAll('a')].some(a => a.getAttribute('href') === './'));
    ok('the guide names both sync buttons',
       /My sync code/.test(g.body.textContent) && /Link a device/.test(g.body.textContent));
    ok('the guide says which device each button belongs on',
       /device you have been using/.test(g.body.textContent) &&
       /device you are adding/.test(g.body.textContent));
    ok('the guide warns against the mistake that breaks it',
       /Do not press/.test(g.body.textContent));
    ok('the guide is blunt about what the code protects',
       /cannot be revoked/.test(g.body.textContent));
    ok('the guide says initials are not a password',
       /not a password/i.test(g.body.textContent));
    ok('no unsubstituted template placeholders', !/%\([a-z_]+\)s/.test(guide));
  }
}

// ---------------------------------------------------------------------------
// First run: ask who this is, rather than seating everyone in YOU
// ---------------------------------------------------------------------------
{
  function firstRun(seed, answer) {
    return new JSDOM(html, {
      runScripts: 'dangerously', url: 'https://example.com/',
      beforeParse(w) {
        for (const [k, v] of Object.entries(seed || {})) {
          w.localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
        }
        w.prompt = () => answer;
      },
    }).window;
  }
  const profilesOf = w => JSON.parse(w.localStorage.getItem('bar52:profiles') || '[]');

  {
    const w = firstRun({}, 'jrh');
    ok('a new visitor is asked, and gets their own profile', profilesOf(w)[0] === 'JRH');
    ok('initials are normalised to upper case',
       w.localStorage.getItem('bar52:current') === 'JRH');
    ok('the default profile is not left lying around', profilesOf(w).length === 1);
  }
  {
    const w = firstRun({}, null);
    ok('dismissing the prompt falls back to the old behaviour', profilesOf(w)[0] === 'YOU');
  }
  {
    const w = firstRun({}, '!!@#$');
    ok('an answer with no letters falls back too', profilesOf(w)[0] === 'YOU');
  }
  {
    const w = firstRun({}, 'jonathan');
    ok('a long answer is trimmed to three letters', profilesOf(w)[0] === 'JON');
  }

  // Someone with existing notes is not a new visitor and must not be prompted.
  {
    const w = firstRun({ 'bar52:v2': { 'last-word': { made: true, note: 'mine' } } }, 'XXX');
    ok('a browser with adopted notes is not prompted', profilesOf(w)[0] === 'YOU');
    ok('and those notes survive',
       JSON.parse(w.localStorage.getItem('bar52:v2:YOU'))['last-word'].note === 'mine');
  }
  {
    const w = firstRun({ 'bar52:v1': { '1': { made: true } } }, 'XXX');
    ok('a browser with v1 data is not prompted either', profilesOf(w)[0] === 'YOU');
  }
  {
    const w = firstRun({ 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH' }, 'XXX');
    ok('an established profile is never re-prompted',
       profilesOf(w).join() === 'JRH' && w.localStorage.getItem('bar52:current') === 'JRH');
  }
}

// ---------------------------------------------------------------------------
// Fixed top bar and slide-out sections
// ---------------------------------------------------------------------------
{
  const { window: w } = load();
  const D = w.document;
  const drawer = D.getElementById('drawer');
  const btn = D.getElementById('menubtn');

  ok('there is a fixed top bar', !!D.querySelector('.topbar'));
  ok('the profile picker lives in the bar', !!D.querySelector('.topbar #profile'));
  ok('and no longer in the dashboard', !D.querySelector('.dash #profile'));
  ok('the deliberate, occasional controls stay in the dashboard',
     !!D.querySelector('.dash #addprofile') && !!D.querySelector('.dash #renameprofile') &&
     !!D.querySelector('.dash #synccode') && !!D.querySelector('.dash #syncnow'));
  ok('the bar carries a sync indicator', !!D.querySelector('.topbar #syncdot'));

  // A fixed bar hides anchor targets underneath it unless every jump target
  // clears it. There are 150+ jump links into the buying guide.
  const css = html;
  ok('jump targets clear the bar',
     /scroll-margin-top:calc\(var\(--topbar\)/.test(css));
  ok('the page is padded for the bar', /body\{padding-top:var\(--topbar\)\}/.test(css));

  ok('the drawer lists every family and appendix section',
     drawer.querySelectorAll('nav a[href^="#"]').length >=
       D.querySelectorAll('.group').length + D.querySelectorAll('.apx').length);
  ok('the drawer links to the guide',
     !!drawer.querySelector('a[href="start.html"]'));
  ok('every drawer target exists on the page',
     [...drawer.querySelectorAll('a[href^="#"]')]
       .every(a => !!D.getElementById(a.getAttribute('href').slice(1))));

  ok('the drawer starts closed', !drawer.classList.contains('open'));
  ok('and says so', btn.getAttribute('aria-expanded') === 'false' &&
                    drawer.getAttribute('aria-hidden') === 'true');

  btn.click();
  ok('the menu button opens it', drawer.classList.contains('open'));
  ok('aria keeps up', btn.getAttribute('aria-expanded') === 'true' &&
                      drawer.getAttribute('aria-hidden') === 'false');
  ok('focus moves into the drawer', drawer.contains(D.activeElement));

  D.dispatchEvent(new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  ok('Escape closes it', !drawer.classList.contains('open'));
  ok('and focus returns to the button', D.activeElement === btn);

  btn.click();
  D.getElementById('scrim').click();
  ok('tapping outside closes it', !drawer.classList.contains('open'));

  btn.click();
  drawer.querySelector('nav a').click();
  ok('choosing a section closes it', !drawer.classList.contains('open'));
}

// ---------------------------------------------------------------------------
// Two-device linking, which is where the old single-prompt design failed
// ---------------------------------------------------------------------------
{
  const settle = () => new Promise(r => setTimeout(r, 0));
  // A stand-in for the server: one shelf, keyed by code, shared between the
  // two "devices" below exactly as the real table would be.
  const server = {};
  function device(seed, typed) {
    let alerted = null;
    const dom = new JSDOM(html, {
      runScripts: 'dangerously', url: 'https://example.com/',
      beforeParse(w) {
        for (const [k, v] of Object.entries(seed || {})) {
          w.localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
        }
        w.alert = m => { alerted = m; };
        w.prompt = () => typed;
        w.fetch = (url, init) => {
          const fn = String(url).split('/rpc/')[1];
          const b = JSON.parse(init.body);
          if (fn === 'pull')
            return Promise.resolve({ ok: true, status: 200,
              json: () => Promise.resolve(server[b.p_code] || {}) });
          server[b.p_code] = b.p_payload;
          return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve('t') });
        };
      },
    });
    return { w: dom.window, alerted: () => alerted };
  }

  // Device one: has notes, presses "My sync code".
  const established = { 'bar52:profiles': ['YOU'], 'bar52:current': 'YOU' };
  const one = device({ ...established,
    'bar52:v2:YOU': { 'last-word': { made: true, note: 'from the laptop' } } });
  one.w.document.getElementById('synccode').click();
  await settle(); await settle();
  const code = one.w.localStorage.getItem('bar52:code:YOU');

  ok('the code is short enough to type', code.length === 12);
  ok('it is shown in a panel, not an alert',
     one.w.document.getElementById('codepanel').hidden === false && one.alerted() === null);
  ok('shown in groups of four',
     /[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}/.test(
       one.w.document.getElementById('codeval').textContent));
  ok('the code is selectable rather than trapped in a dialog',
     /user-select:all/.test(html));
  ok('and it tells you which button to press on the other device',
     /Link a device/.test(one.w.document.getElementById('codehint').textContent));
  ok('it warns that the code is the only way back',
     /no way back/.test(one.w.document.getElementById('codewarn').textContent));
  ok('device one uploaded its notes', !!server[code] && !!server[code].entries['last-word']);

  // Device two: types the code in with the formatting and wrong case a person
  // would actually produce.
  const messy = code.replace(/(.{4})(?=.)/g, '$1-').toLowerCase();
  const two = device({ ...established,
    'bar52:v2:YOU': { 'jungle-bird': { made: true, note: 'from the phone' } } }, messy);
  two.w.document.getElementById('synclink').click();
  await settle(); await settle(); await settle();

  ok('a dashed, lower-case code is accepted',
     two.w.localStorage.getItem('bar52:code:YOU') === code);
  const merged = JSON.parse(two.w.localStorage.getItem('bar52:v2:YOU') || '{}');
  ok('device two receives device one\'s notes',
     merged['last-word'] && merged['last-word'].note === 'from the laptop');
  ok('and keeps its own', merged['jungle-bird'] && merged['jungle-bird'].note === 'from the phone');
  ok('the shared shelf now holds both',
     !!server[code].entries['last-word'] && !!server[code].entries['jungle-bird']);
  ok('the status says it synced',
     /Synced/.test(two.w.document.getElementById('syncstat').textContent));

  // A code that is obviously too short is refused with an explanation.
  const short = device({ ...established }, 'ABC');
  short.w.document.getElementById('synclink').click();
  await settle();
  ok('a too-short code is refused', !short.w.localStorage.getItem('bar52:code:YOU'));
  ok('and the refusal says how long it should be', /12/.test(short.alerted()));
}

// ---------------------------------------------------------------------------
// The label follows the data, and legacy over-long codes can be shortened
// ---------------------------------------------------------------------------
{
  const settle = () => new Promise(r => setTimeout(r, 0));
  const CODE12 = 'K7MP2XQR9TVB';
  const OLD26 = 'ABCDEFGHJKMNPQRSTVWXYZ2345';

  function dev(seed, remote, opts = {}) {
    let alerted = null;
    const dom = new JSDOM(html, {
      runScripts: 'dangerously', url: 'https://example.com/',
      beforeParse(w) {
        for (const [k, v] of Object.entries(seed || {})) {
          w.localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
        }
        w.alert = m => { alerted = m; };
        w.confirm = () => opts.confirm !== false;
        w.prompt = () => opts.typed ?? null;
        w.fetch = (url, init) => Promise.resolve({
          ok: true, status: 200,
          json: () => Promise.resolve(
            String(url).endsWith('pull') ? (remote || {}) : 't'),
        });
      },
    });
    return { w: dom.window, alerted: () => alerted };
  }

  // The phone: linked, but still calling itself YOU. This is the reported bug.
  {
    const { w } = dev(
      { 'bar52:profiles': ['YOU'], 'bar52:current': 'YOU', 'bar52:code:YOU': CODE12 },
      { version: 2, profile: 'JRH',
        entries: { 'last-word': { made: true, note: 'from the laptop' } }, bottles: {} });
    await settle(); await settle();

    ok('the linked device takes the name from the data',
       w.localStorage.getItem('bar52:current') === 'JRH');
    ok('the picker shows it', w.document.getElementById('profile').value === 'JRH');
    ok('YOU is gone rather than left as a duplicate',
       JSON.parse(w.localStorage.getItem('bar52:profiles')).join() === 'JRH');
    ok('the notes moved with the name',
       !!JSON.parse(w.localStorage.getItem('bar52:v2:JRH') || '{}')['last-word']);
    ok('nothing is left behind under the old name',
       !w.localStorage.getItem('bar52:v2:YOU'));
    ok('the sync code moved too, so the device stays linked',
       w.localStorage.getItem('bar52:code:JRH') === CODE12 &&
       !w.localStorage.getItem('bar52:code:YOU'));
  }

  // But not if that would collide with a real second profile on this device.
  {
    const { w } = dev(
      { 'bar52:profiles': ['YOU', 'JRH'], 'bar52:current': 'YOU',
        'bar52:code:YOU': CODE12, 'bar52:v2:JRH': { 'jungle-bird': { made: true } } },
      { version: 2, profile: 'JRH', entries: {}, bottles: {} });
    await settle(); await settle();
    ok('an existing local profile of that name is not clobbered',
       w.localStorage.getItem('bar52:current') === 'YOU' &&
       !!JSON.parse(w.localStorage.getItem('bar52:v2:JRH'))['jungle-bird']);
    ok('and the page explains why the name did not change',
       /already has a JRH profile/.test(w.document.getElementById('syncstat').textContent));
    ok('and the explanation survives the success message',
       /Synced/.test(w.document.getElementById('syncstat').textContent));
  }

  // A code from before the length was cut can be swapped for a short one.
  {
    const { w, alerted } = dev(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': OLD26 },
      { entries: {}, bottles: {} });
    w.document.getElementById('synccode').click();
    await settle();
    ok('an over-long code offers a shorter one',
       w.document.getElementById('codeshorten').hidden === false);
    w.document.getElementById('codeshorten').click();
    await settle();
    const now = w.localStorage.getItem('bar52:code:JRH');
    ok('an over-long code is replaced when you accept', now.length === 12);
    ok('and the new one is shown in groups of four',
       /[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}/.test(
         w.document.getElementById('codeval').textContent));
    ok('the offer goes away once taken',
       w.document.getElementById('codeshorten').hidden === true);
  }
  {
    const { w } = dev(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': OLD26 },
      { entries: {}, bottles: {} }, { confirm: false });
    w.document.getElementById('synccode').click();
    await settle();
    w.document.getElementById('codeshorten').click();
    await settle();
    ok('declining keeps the old code working',
       w.localStorage.getItem('bar52:code:JRH') === OLD26);
  }
  {
    const { w } = dev(
      { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH', 'bar52:code:JRH': CODE12 },
      { entries: {}, bottles: {} });
    w.document.getElementById('synccode').click();
    await settle();
    ok('a code already at the right length is left alone',
       w.localStorage.getItem('bar52:code:JRH') === CODE12);
    ok('and is not offered a replacement',
       w.document.getElementById('codeshorten').hidden === true);
  }
}

// ---------------------------------------------------------------------------
// Copying the sync code, which is the one string that must leave the device
// ---------------------------------------------------------------------------
{
  const settle = () => new Promise(r => setTimeout(r, 0));
  const seed = { 'bar52:profiles': ['JRH'], 'bar52:current': 'JRH',
                 'bar52:code:JRH': 'K7MP2XQR9TVB' };

  function panelDev(clipboard) {
    const dom = new JSDOM(html, {
      runScripts: 'dangerously', url: 'https://example.com/',
      beforeParse(w) {
        for (const [k, v] of Object.entries(seed)) w.localStorage.setItem(k, JSON.stringify(v).replace(/^"|"$/g, ''));
        w.localStorage.setItem('bar52:profiles', JSON.stringify(['JRH']));
        w.prompt = () => null;
        w.fetch = () => Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
        if (clipboard) w.navigator.clipboard = clipboard;
      },
    });
    return dom.window;
  }

  {
    let copied = null;
    const w = panelDev({ writeText: t => { copied = t; return Promise.resolve(); } });
    w.document.getElementById('synccode').click();
    w.document.getElementById('codecopy').click();
    await settle();
    ok('the copy button copies the code', copied === 'K7MP2XQR9TVB');
    ok('it copies without the display dashes', !/-/.test(copied));
    ok('and confirms it did', w.document.getElementById('codecopy').textContent === 'Copied');
  }

  // A refused clipboard permission must not leave a button that does nothing.
  {
    const w = panelDev({ writeText: () => Promise.reject(new Error('denied')) });
    w.document.getElementById('synccode').click();
    w.document.getElementById('codecopy').click();
    await settle();
    ok('a refused clipboard tells you to copy it yourself',
       /Select it/.test(w.document.getElementById('codecopy').textContent));
  }

  // Older browsers have no clipboard API at all.
  {
    const w = panelDev(null);
    w.document.getElementById('synccode').click();
    ok('no clipboard API does not break the panel',
       w.document.getElementById('codepanel').hidden === false);
    w.document.getElementById('codecopy').click();
    await settle();
    ok('and the button still responds',
       w.document.getElementById('codecopy').textContent !== 'Copy');
  }
}

console.log(fail ? `\n${fail} FAILURES` : '\nAll checks passed');
process.exit(fail ? 1 : 0);
