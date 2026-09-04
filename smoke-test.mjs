import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
const html = readFileSync('docs/index.html','utf8');

const KEY = 'bar52:v2';
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
  const OWN_KEY = 'bar52:bottles:v1';
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
       !('b-campari' in JSON.parse(w.localStorage.getItem('bar52:v2') || '{}')));
  }
  {
    const { window: w } = load({ 'bar52:bottles:v1': { 'b-campari': true } });
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
    const { window: w } = load({ 'bar52:bottles:v1': { 'b-campari': true } });
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
    const { window: w } = load({ 'bar52:bottles:v1': { 'b-campari': true } });
    w.confirm = () => true;
    w.document.getElementById('reset').click();
    ok('reset clears the shelf too', !w.localStorage.getItem(OWN_KEY));
    ok('reset unticks the checkboxes',
       w.document.querySelector('.own input[data-bottle="b-campari"]').checked === false);
  }

  // Clarified Milk Punch asks for "12 oz spirit", so it needs no specific bottle.
  {
    const { window: w } = load({ 'bar52:bottles:v1': { 'b-campari': true } });
    ok('a drink with no bottle requirements is always makeable',
       listed(w).includes('clarified-milk-punch'));
  }
}

console.log(fail ? `\n${fail} FAILURES` : '\nAll checks passed');
process.exit(fail ? 1 : 0);
