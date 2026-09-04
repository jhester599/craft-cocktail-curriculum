// Checks every video link on the built page against YouTube's oEmbed endpoint.
//
// oEmbed (https://www.youtube.com/oembed?url=...&format=json) returns 200 with
// JSON for a public video and a 4xx for one that is deleted, private or has a
// bad id, which makes it a cheap liveness check that needs no API key.
//
// Two things fail the run:
//   dead     - oEmbed did not return 200, so the link is broken.
//   channel  - it resolved, but to a different channel than the page claims,
//              which means the link points at someone else's video.
//
// Title drift is reported but never fails: a channel legitimately renames a
// video, and a false alarm every month trains you to ignore the alarm.
//
// If every single link comes back dead, that is treated as "could not reach
// YouTube" rather than "your whole page rotted overnight" - the far likelier
// cause is a blocked or flaky network, and crying wolf about 52 dead links
// would be worse than saying nothing.
//
// Usage:  node check-videos.mjs [--report <path>]
// Exit:   0 all healthy, 1 problems found, 2 could not run at all.

import { readFileSync, writeFileSync } from 'node:fs';
import { JSDOM } from 'jsdom';

const reportPath = (() => {
  const i = process.argv.indexOf('--report');
  return i === -1 ? null : process.argv[i + 1];
})();

const CONCURRENCY = 4;
const TIMEOUT_MS = 15000;

// "The Educated Barfly (Short)" and "The Educated Barfly — 1934 variation,
// check before following" are both that channel; the trailing note is ours.
const baseChannel = s =>
  s.split(/\s+[(—-]\s*|\s+\(/)[0]
    .replace(/[‘’']/g, "'")
    .trim()
    .toLowerCase();

const STOP = new Set(['the', 'a', 'no', 'and', 'of', 'sour', 'cocktail', 'punch']);
const titleLooksRight = (drink, title) => {
  const words = drink.toLowerCase().match(/[a-z0-9']+/g)?.filter(w => !STOP.has(w)) ?? [];
  if (!words.length) return true;
  const t = title.toLowerCase();
  return words.some(w => t.includes(w));
};

function drinksFromPage(html) {
  const { window } = new JSDOM(html);
  return [...window.document.querySelectorAll('.drink')].map(card => {
    const a = card.querySelector('a.video');
    return {
      slug: card.dataset.id,
      name: card.querySelector('h3')?.textContent?.trim() ?? card.dataset.id,
      url: a?.getAttribute('href') ?? null,
      channel: a?.textContent?.replace(/^.*Watch\s*·\s*/, '').trim() ?? null,
    };
  });
}

async function oembed(url) {
  const endpoint =
    'https://www.youtube.com/oembed?url=' + encodeURIComponent(url) + '&format=json';
  // One retry: a transient 5xx or 429 is not a dead video.
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(endpoint, { signal: AbortSignal.timeout(TIMEOUT_MS) });
      if (res.ok) return { ok: true, data: await res.json() };
      if (res.status >= 500 || res.status === 429) {
        if (attempt === 0) { await new Promise(r => setTimeout(r, 2000)); continue; }
        return { ok: false, reason: `HTTP ${res.status} after retry` };
      }
      return { ok: false, reason: `HTTP ${res.status}` };
    } catch (e) {
      if (attempt === 0) { await new Promise(r => setTimeout(r, 2000)); continue; }
      return { ok: false, reason: `request failed: ${e.message}` };
    }
  }
}

async function mapLimit(items, limit, fn) {
  const out = new Array(items.length);
  let next = 0;
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (next < items.length) {
        const i = next++;
        out[i] = await fn(items[i]);
      }
    })
  );
  return out;
}

const html = (() => {
  try {
    return readFileSync('docs/index.html', 'utf8');
  } catch {
    console.error('Could not read docs/index.html. Run `python3 build.py` first.');
    process.exit(2);
  }
})();

const drinks = drinksFromPage(html);
if (!drinks.length) {
  console.error('No .drink cards found in docs/index.html - has the markup changed?');
  process.exit(2);
}

const missing = drinks.filter(d => !d.url);
const checked = await mapLimit(drinks.filter(d => d.url), CONCURRENCY, async d => {
  const r = await oembed(d.url);
  if (!r.ok) return { ...d, status: 'dead', detail: r.reason };
  const got = r.data.author_name ?? '';
  if (baseChannel(got) !== baseChannel(d.channel ?? ''))
    return { ...d, status: 'channel', detail: `claims "${d.channel}", is "${got}"`, title: r.data.title };
  if (!titleLooksRight(d.name, r.data.title ?? ''))
    return { ...d, status: 'title', detail: `title "${r.data.title}"`, title: r.data.title };
  return { ...d, status: 'ok', title: r.data.title };
});

const by = s => checked.filter(d => d.status === s);
const dead = by('dead'), wrongChannel = by('channel'), drift = by('title');
const broken = [...dead, ...wrongChannel];

// Everything dead at once means the endpoint was unreachable, not that every
// video vanished. Bail as an infrastructure failure so no issue gets opened.
if (dead.length === checked.length && checked.length > 3) {
  console.error(
    `\nAll ${checked.length} links reported dead (${dead[0].detail}).\n` +
    'That means YouTube could not be reached, not that every video is gone. ' +
    'Not reporting this as link rot.'
  );
  process.exit(2);
}

for (const d of checked) {
  const mark = d.status === 'ok' ? 'ok  ' : d.status === 'title' ? 'note' : 'FAIL';
  console.log(`${mark}  ${d.name.padEnd(24)} ${d.status === 'ok' ? d.title ?? '' : d.detail}`);
}
console.log(
  `\n${checked.length} links checked: ${by('ok').length} healthy, ${dead.length} dead, ` +
  `${wrongChannel.length} on the wrong channel, ${drift.length} with a title worth a look.`
);
if (missing.length) console.log(`${missing.length} drinks have no video link at all.`);

if (reportPath) {
  const row = d => `| ${d.name} | [link](${d.url}) | ${d.detail ?? ''} |`;
  const section = (title, rows) =>
    rows.length ? `\n### ${title}\n\n| Drink | Link | Detail |\n|---|---|---|\n${rows.map(row).join('\n')}\n` : '';
  writeFileSync(
    reportPath,
    `${broken.length ? `**${broken.length} video link${broken.length === 1 ? '' : 's'} need attention.**`
                     : '**All video links are healthy.**'}\n\n` +
    `Checked ${checked.length} links against YouTube's oEmbed endpoint.\n` +
    section('Dead links', dead) +
    section('Resolved to the wrong channel', wrongChannel) +
    section('Title drift (advisory, not a failure)', drift) +
    (missing.length ? `\n### Drinks with no video link\n\n${missing.map(d => `- ${d.name}`).join('\n')}\n` : '') +
    `\nFix links in \`data.py\`, then run \`python3 build.py\` and commit the rebuilt page.\n`
  );
}

process.exit(broken.length ? 1 : 0);
