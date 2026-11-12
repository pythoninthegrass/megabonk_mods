import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test, { after } from 'node:test';
import { createApp } from '../server.mjs';

const workDir = await mkdtemp(join(tmpdir(), 'level-route-'));
const root = join(workDir, 'dist');
await mkdir(join(root, 'levels', 'view'), { recursive: true });
await writeFile(join(root, 'index.html'), '<h1>home</h1>');
await writeFile(join(root, 'levels', 'view', 'index.html'), '<h1>level view</h1>');
await mkdir(join(root, 'creators', 'view'), { recursive: true });
await writeFile(join(root, 'creators', 'view', 'index.html'), '<h1>creator view</h1>');
await writeFile(join(root, 'inside.txt'), 'inside');
await writeFile(join(workDir, 'outside.txt'), 'outside');

const server = createApp({ root });
await new Promise((resolve, reject) => {
  server.once('error', reject);
  server.listen(0, '127.0.0.1', resolve);
});
after(async () => {
  server.close();
  await rm(workDir, { recursive: true, force: true });
});
const base = `http://127.0.0.1:${server.address().port}/`;

test('a share code path serves the level view page', async () => {
  const response = await fetch(`${base}l/7N1-MVB-WKF`);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type'), /^text\/html/);
  assert.equal(await response.text(), '<h1>level view</h1>');
});

test('a trailing slash and a query string still serve the view page', async () => {
  for (const path of ['l/7N1-MVB-WKF/', 'l/7N1-MVB-WKF?ref=card']) {
    const response = await fetch(`${base}${path}`);
    assert.equal(response.status, 200, path);
    assert.equal(await response.text(), '<h1>level view</h1>', path);
  }
});

test('HEAD on a share code path has the view headers and no body', async () => {
  const response = await fetch(`${base}l/7N1-MVB-WKF`, { method: 'HEAD' });
  assert.equal(response.status, 200);
  assert.equal((await response.arrayBuffer()).byteLength, 0);
});

test('anything that is not a canonical share code answers 404', async () => {
  for (
    const path of [
      'l/',
      'l/7N1-MVB-WKF/extra',
      'l/7n1-mvb-wkf',
      'l/7N1MVBWKF',
      'l/7N1-MVB-WKU',
      'l/7N1-MVB-WKI',
      'l/7N1-MVB-WKFF',
      'l/7N1-MVB-WKF%00',
    ]
  ) {
    const status = (await fetch(`${base}${path}`, { redirect: 'manual' })).status;
    assert.ok(status === 404 || status === 400, `${path} answered ${status}`);
  }
});

test('encoded traversal under the share code prefix never reaches a file outside the root', async () => {
  for (const path of ['l/..%2f..%2foutside.txt', 'l/%2e%2e%2f%2e%2e%2foutside.txt']) {
    const response = await fetch(`${base}${path}`, { redirect: 'manual' });
    assert.equal(response.status, 404, path);
  }
});

test('other paths are unaffected by the share code route', async () => {
  assert.equal(await (await fetch(base)).text(), '<h1>home</h1>');
  assert.equal(await (await fetch(`${base}inside.txt`)).text(), 'inside');
  assert.equal((await fetch(`${base}levels/view/`)).status, 200);
});

test('POST to a share code path answers 405', async () => {
  assert.equal((await fetch(`${base}l/7N1-MVB-WKF`, { method: 'POST' })).status, 405);
});

test('an account id path serves the creator view page', async () => {
  for (const path of ['u/abc123def456ghi', 'u/abc123def456ghi/', 'u/abc123def456ghi?page=2']) {
    const response = await fetch(`${base}${path}`);
    assert.equal(response.status, 200, path);
    assert.equal(await response.text(), '<h1>creator view</h1>', path);
  }
});

test('anything that is not a well-formed account id answers 404', async () => {
  for (
    const path of [
      'u/',
      'u/short',
      'u/abc123def456ghix',
      'u/ABC123DEF456GHI',
      'u/abc123def456ghi/extra',
      'u/..%2f..%2foutside.txt',
      'u/abc123def456gh%00',
    ]
  ) {
    const status = (await fetch(`${base}${path}`, { redirect: 'manual' })).status;
    assert.ok(status === 404 || status === 400, `${path} answered ${status}`);
  }
});

test('POST to an account id path answers 405', async () => {
  assert.equal((await fetch(`${base}u/abc123def456ghi`, { method: 'POST' })).status, 405);
});
