import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import { createApp } from '../server.mjs';
import { runSmoke } from '../smoke.mjs';

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
