import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import { createApp } from '../server.mjs';
import { runSmoke } from '../smoke.mjs';
import { get } from 'node:http';

const server = createApp({ root: new URL('../dist/', import.meta.url) });
await new Promise((resolve, reject) => {
  server.once('error', reject);
  server.listen(0, '127.0.0.1', resolve);
});
after(() => server.close());
const base = `http://127.0.0.1:${server.address().port}/`;

test('the home page and every referenced local CSS, script and image are served', async () => {
  const { css, js, images, references } = await runSmoke(base);
  assert.ok(css >= 1, 'at least one stylesheet is referenced and served');
  assert.ok(js >= 1, 'at least one script is referenced and served');
  assert.ok(images >= 1, 'at least one image is referenced and served');
  assert.ok(references >= css + js + images, 'counts add up against the reference set');
});

test('unknown paths answer 404', async () => {
  assert.equal((await fetch(`${base}does-not-exist`)).status, 404);
});

test('docs hostname root redirects to the wiki, preserving queries', async () => {
  const response = await new Promise((resolve, reject) => {
    get(`${base}?from=home`, { headers: { host: 'docs.megabonkmod.party' } }, (res) => {
      res.resume();
      resolve(res);
    }).on('error', reject);
  });
  assert.equal(response.statusCode, 308);
  assert.equal(response.headers.location, '/home/?from=home');
});

test('legacy wiki home URLs redirect without affecting guide routes', async () => {
  for (
    const [path, destination] of [
      ['docs/', '/home/'],
      ['docs', '/home/'],
      ['docs/index.md', '/home.md'],
    ]
  ) {
    const response = await fetch(new URL(`${path}?legacy=1`, base), { redirect: 'manual' });
    assert.equal(response.status, 308, path);
    assert.equal(response.headers.get('location'), `${destination}?legacy=1`, path);
  }
});

test('wiki routes, raw Markdown and search assets have correct content types', async () => {
  for (
    const [path, type] of [
      ['home/', 'text/html'],
      ['home.md', 'text/markdown'],
      ['docs/player-guide.md', 'text/markdown'],
      ['pagefind/pagefind.js', 'text/javascript'],
      ['pagefind/wasm.en.pagefind', 'application/wasm'],
    ]
  ) {
    const response = await fetch(new URL(path, base));
    assert.equal(response.status, 200, path);
    assert.ok(response.headers.get('content-type').startsWith(type), path);
  }
  assert.equal(
    (await fetch(new URL('docs/player-guide', base), { redirect: 'manual' })).status,
    308,
  );
});

test('an encoded traversal never escapes the served root', async () => {
  assert.equal((await fetch(`${base}%2e%2e%2fpackage.json`)).status, 404);
});

test('non-GET requests answer 405', async () => {
  assert.equal((await fetch(base, { method: 'POST' })).status, 405);
});

test('HEAD answers with the same status and headers but no body', async () => {
  const response = await fetch(base, { method: 'HEAD' });
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type') ?? '', /^text\/html/);
  assert.equal((await response.arrayBuffer()).byteLength, 0);
});
