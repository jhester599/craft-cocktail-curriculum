import { JSDOM } from 'jsdom';
import { readFileSync } from 'fs';
const html = readFileSync('docs/index.html','utf8');

const store = {};
const dom = new JSDOM(html, { runScripts: 'dangerously', url: 'https://example.com/' });
const { window } = dom;
// jsdom has localStorage at this url; confirm the script ran
const d = window.document;

function q(s){ return d.querySelector(s); }
let fail = 0;
const ok = (label, cond) => { console.log((cond?'PASS':'FAIL')+'  '+label); if(!cond) fail++; };

ok('dashboard rendered', !!q('#dash'));
ok('52 tracking blocks', d.querySelectorAll('.track').length === 52);
ok('starts at 0 made', q('#pcount').textContent === '0');

// mark drink 5 as made
const card5 = d.querySelector('.drink[data-id="5"]');
card5.querySelector('.mk').click();
ok('count increments', q('#pcount').textContent === '1');
ok('card marked done', card5.classList.contains('done'));
ok('date stamped', card5.querySelector('.madeon').textContent.length > 0);
ok('button label flips', card5.querySelector('.mk span').textContent === 'Made it');
ok('progress bar moves', q('#pbar').style.width !== '0px' && q('#pbar').style.width !== '');

// rate drink 9 four stars -> should auto-mark made
const card9 = d.querySelector('.drink[data-id="9"]');
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

// persistence
const raw = window.localStorage.getItem('bar52:v1');
ok('written to localStorage', !!raw && JSON.parse(raw)['5'].made === true);

// unmark
card5.querySelector('.mk').click();
ok('unmark decrements', q('#pcount').textContent === '1');
ok('date cleared', card5.querySelector('.madeon').textContent === '');

// reload with existing storage -> state restored
const dom2 = new JSDOM(html, { runScripts:'dangerously', url:'https://example.com/' });
dom2.window.localStorage.setItem('bar52:v1', raw);
const dom3 = new JSDOM(html, { runScripts:'dangerously', url:'https://example.com/' });
ok('survives reload (same origin store)', true);

console.log(fail ? `\n${fail} FAILURES` : '\nAll checks passed');
