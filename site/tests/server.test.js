import assert from 'node:assert/strict';
import test, { after } from 'node:test';
import { createApp } from '../server.mjs';
import { runSmoke } from '../smoke.mjs';
import { get } from 'node:http';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';

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

test('an unknown page answers 404 with the branded not-found page', async () => {
  const response = await fetch(`${base}does-not-exist`);
  assert.equal(response.status, 404);
  assert.match(response.headers.get('content-type'), /^text\/html/);
  assert.equal(response.headers.get('cache-control'), 'no-cache');
  const html = await response.text();
  assert.match(html, /<h1[^>]*>[\s\S]*Page[\s\S]*not found/);
  assert.match(html, /href="\/levels\/"/);
  assert.match(html, /<meta name="robots" content="noindex"/);
  assert.doesNotMatch(html, /<link rel="canonical"/);
});

test('a HEAD request for an unknown page answers 404 with html headers and no body', async () => {
  const response = await fetch(`${base}does-not-exist`, { method: 'HEAD' });
  assert.equal(response.status, 404);
  assert.match(response.headers.get('content-type'), /^text\/html/);
  assert.equal(await response.text(), '');
});

test('a missing asset answers 404 without the html page', async () => {
  const response = await fetch(`${base}missing.png`);
  assert.equal(response.status, 404);
  assert.equal(response.headers.get('content-length'), '0');
});

test('a malformed share code path answers the branded 404', async () => {
  const response = await fetch(`${base}l/not-a-code`);
  assert.equal(response.status, 404);
  assert.match(await response.text(), /Page not/);
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
      ['docs/player-guide/', '/player-guide/'],
      ['docs/player-guide.md', '/player-guide.md'],
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
      ['player-guide.md', 'text/markdown'],
      ['pagefind/pagefind.js', 'text/javascript'],
      ['pagefind/wasm.en.pagefind', 'application/wasm'],
    ]
  ) {
    const response = await fetch(new URL(path, base));
    assert.equal(response.status, 200, path);
    assert.ok(response.headers.get('content-type').startsWith(type), path);
  }
  assert.equal(
    (await fetch(new URL('player-guide', base), { redirect: 'manual' })).status,
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

test('html pages are revalidated on every load by default', async () => {
  for (const path of ['', 'levels/', 'l/7N1-MVB-WKF', 'does-not-exist']) {
    const response = await fetch(`${base}${path}`);
    assert.equal(response.headers.get('cache-control'), 'no-cache', path);
  }
});

test('static assets keep their cache lifetimes', async () => {
  const icon = await fetch(`${base}favicon.svg`);
  assert.equal(icon.headers.get('cache-control'), 'public, max-age=3600');
  const home = await (await fetch(base)).text();
  const asset = /\/_astro\/[^"']+\.css/.exec(home)?.[0];
  assert.ok(asset, 'the home page references a hashed stylesheet');
  assert.equal(
    (await fetch(`${base}${asset.slice(1)}`)).headers.get('cache-control'),
    'public, max-age=31536000, immutable',
  );
});

test('responses carry an ETag and a matching If-None-Match answers 304 without a body', async () => {
  const first = await fetch(`${base}levels/`);
  const etag = first.headers.get('etag');
  assert.match(etag, /^"[A-Za-z0-9_-]{22}"$/);
  const again = await fetch(`${base}levels/`, { headers: { 'if-none-match': etag } });
  assert.equal(again.status, 304);
  assert.equal(await again.text(), '');
  assert.equal(again.headers.get('etag'), etag);
  assert.equal(again.headers.get('cache-control'), 'no-cache');
  const stale = await fetch(`${base}levels/`, { headers: { 'if-none-match': '"old"' } });
  assert.equal(stale.status, 200);
});

test('the html cache header can be set when the app is created', async () => {
  const custom = createApp({
    root: new URL('../dist/', import.meta.url),
    htmlCacheControl: 'public, max-age=60',
  });
  await new Promise((resolve) => custom.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${custom.address().port}/`;
    assert.equal((await fetch(url)).headers.get('cache-control'), 'public, max-age=60');
    assert.equal(
      (await fetch(`${url}favicon.svg`)).headers.get('cache-control'),
      'public, max-age=3600',
    );
  } finally {
    custom.close();
  }
});

test('SITE_HTML_CACHE_CONTROL sets the html cache header of the running server', async () => {
  const port = await new Promise((resolve) => {
    const probe = createServer().listen(0, '127.0.0.1', () => {
      const { port } = probe.address();
      probe.close(() => resolve(port));
    });
  });
  const child = spawn(process.execPath, ['server.mjs'], {
    cwd: new URL('..', import.meta.url),
    env: {
      ...process.env,
      PORT: String(port),
      HOST: '127.0.0.1',
      SITE_HTML_CACHE_CONTROL: 'public, max-age=120',
    },
    stdio: ['ignore', 'pipe', 'inherit'],
  });
  try {
    await new Promise((resolve) => child.stdout.once('data', resolve));
    const response = await fetch(`http://127.0.0.1:${port}/`);
    assert.equal(response.headers.get('cache-control'), 'public, max-age=120');
  } finally {
    child.kill('SIGTERM');
  }
});

const SECURITY_HEADERS = {
  'strict-transport-security': 'max-age=63072000; includeSubDomains',
  'x-content-type-options': 'nosniff',
  'x-frame-options': 'DENY',
  'referrer-policy': 'strict-origin-when-cross-origin',
  'permissions-policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
  'cross-origin-opener-policy': 'same-origin-allow-popups',
  'cross-origin-resource-policy': 'same-origin',
};

test('every kind of response carries the security headers', async () => {
  const requests = [
    ['page', `${base}`],
    ['asset', `${base}favicon.svg`],
    ['not found', `${base}does-not-exist`],
    ['redirect', `${base}docs/`],
  ];
  for (const [label, url] of requests) {
    const response = await fetch(url, { redirect: 'manual' });
    for (const [name, value] of Object.entries(SECURITY_HEADERS)) {
      assert.equal(response.headers.get(name), value, `${label}: ${name}`);
    }
    assert.ok(response.headers.get('content-security-policy'), `${label}: content-security-policy`);
  }
});

test('a method not allowed response carries the security headers', async () => {
  const response = await fetch(base, { method: 'POST' });
  assert.equal(response.status, 405);
  assert.equal(response.headers.get('x-content-type-options'), 'nosniff');
});

test('the content security policy locks down plugins, base, forms and framing', async () => {
  const csp = (await fetch(base)).headers.get('content-security-policy');
  for (
    const directive of [
      "object-src 'none'",
      "base-uri 'self'",
      "frame-ancestors 'none'",
      "form-action 'self'",
    ]
  ) {
    assert.ok(csp.includes(directive), directive);
  }
});

test('the content security policy allows the configured API origin and giscus only', async () => {
  const custom = createApp({
    root: new URL('../dist/', import.meta.url),
    apiOrigin: 'https://api.example.test',
  });
  await new Promise((resolve) => custom.listen(0, '127.0.0.1', resolve));
  try {
    const response = await fetch(`http://127.0.0.1:${custom.address().port}/`);
    const policy = Object.fromEntries(
      response.headers.get('content-security-policy').split(';').map((part) => {
        const [name, ...sources] = part.trim().split(/\s+/);
        return [name, sources];
      }),
    );
    assert.ok(policy['connect-src'].includes('https://api.example.test'));
    assert.ok(policy['img-src'].includes('https://api.example.test'));
    assert.ok(policy['script-src'].includes('https://giscus.app'));
    assert.deepEqual(policy['frame-src'], ['https://giscus.app']);
  } finally {
    custom.close();
  }
});
