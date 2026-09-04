// Tests check-videos.mjs against a mocked oEmbed endpoint.
//
// The real endpoint cannot be reached from every environment, and even where it
// can, a test that depends on YouTube being up is not a test. So this runs the
// checker as a subprocess with globalThis.fetch replaced, which lets us drive
// every branch - healthy, dead, wrong channel, title drift, transient 5xx - and
// assert on the exit code and the generated report.

import { spawnSync } from 'node:child_process';
import { writeFileSync, readFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

let fail = 0;
const ok = (label, cond) => { console.log((cond ? 'PASS' : 'FAIL') + '  ' + label); if (!cond) fail++; };

const dir = mkdtempSync(join(tmpdir(), 'videocheck-'));

// A page with four drinks, each wired to a video id the mock treats differently.
const page = `<!doctype html><html><body>
${[
  ['last-word', 'Last Word', 'HEALTHY', 'The Educated Barfly'],
  ['jungle-bird', 'Jungle Bird', 'GONE', 'The Educated Barfly'],
  ['red-hook', 'Red Hook', 'OTHERCHAN', 'The Educated Barfly'],
  ['siesta', 'Siesta', 'RENAMED', 'Anders Erickson'],
  ['toronto', 'Toronto', 'FLAKY', 'The Educated Barfly (Short)'],
].map(([slug, name, id, chan]) => `
<article class="drink" data-id="${slug}">
  <h3>${name}</h3>
  <a class="video" href="https://www.youtube.com/watch?v=${id}"><span>Watch &middot; ${chan}</span></a>
</article>`).join('')}
</body></html>`;

const mock = `
let flaky = 0;
globalThis.fetch = async (url) => {
  const id = decodeURIComponent(url).match(/v=([A-Z]+)/)[1];
  const json = (o) => ({ ok: true, status: 200, json: async () => o });
  if (id === 'HEALTHY')   return json({ author_name: 'The Educated Barfly', title: 'The Last Word Cocktail' });
  if (id === 'GONE')      return { ok: false, status: 404 };
  if (id === 'OTHERCHAN') return json({ author_name: 'Some Other Channel', title: 'Red Hook' });
  if (id === 'RENAMED')   return json({ author_name: 'Anders Erickson', title: 'A Drink For Hot Days' });
  if (id === 'FLAKY')     return flaky++ === 0 ? { ok: false, status: 503 }
                                               : json({ author_name: 'The Educated Barfly', title: 'Toronto' });
  throw new Error('unexpected id ' + id);
};
`;

const pagePath = join(dir, 'index.html');
const mockPath = join(dir, 'mock.mjs');
const reportPath = join(dir, 'report.md');
writeFileSync(mockPath, mock);

// The checker reads docs/index.html relative to cwd, so give it a fake tree.
const docs = join(dir, 'docs');
spawnSync('mkdir', ['-p', docs]);
writeFileSync(join(docs, 'index.html'), page);
writeFileSync(pagePath, page);

const run = spawnSync(
  process.execPath,
  ['--import', mockPath, join(process.cwd(), 'check-videos.mjs'), '--report', reportPath],
  { cwd: dir, encoding: 'utf8' }
);

const out = run.stdout + run.stderr;
const report = readFileSync(reportPath, 'utf8');

ok('exits 1 when links are broken', run.status === 1);
ok('healthy link passes', /ok\s+Last Word/.test(out));
ok('dead link is caught', /FAIL\s+Jungle Bird/.test(out) && /HTTP 404/.test(out));
ok('wrong channel is caught', /FAIL\s+Red Hook/.test(out) && /Some Other Channel/.test(out));
ok('title drift is a note, not a failure', /note\s+Siesta/.test(out));
ok('transient 503 is retried, not reported dead', /ok\s+Toronto/.test(out));
ok('channel suffix "(Short)" still matches the channel', !/FAIL\s+Toronto/.test(out));

ok('report names the dead link', /### Dead links[\s\S]*Jungle Bird/.test(report));
ok('report separates the wrong-channel link', /### Resolved to the wrong channel[\s\S]*Red Hook/.test(report));
ok('report marks title drift advisory', /advisory[\s\S]*Siesta/.test(report));
ok('report counts only real failures', /\*\*2 video links need attention\.\*\*/.test(report));
ok('report tells you how to fix it', /python3 build\.py/.test(report));

// All-dead must read as an unreachable endpoint, not as total link rot.
writeFileSync(join(dir, 'allgone.mjs'),
  "globalThis.fetch = async () => ({ ok: false, status: 403 });");
const blocked = spawnSync(
  process.execPath,
  ['--import', join(dir, 'allgone.mjs'), join(process.cwd(), 'check-videos.mjs')],
  { cwd: dir, encoding: 'utf8' }
);
ok('all-dead exits 2, not 1', blocked.status === 2);
ok('all-dead explains it is a network problem',
   /could not be reached/.test(blocked.stdout + blocked.stderr));

console.log(fail ? `\n${fail} FAILURES` : '\nAll checks passed');
process.exit(fail ? 1 : 0);
