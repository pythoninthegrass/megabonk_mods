import { createHash } from 'node:crypto';
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const TYPES = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.wasm': 'application/wasm',
  '.xml': 'application/xml; charset=utf-8',
};

const LEVEL_ROUTE = /^\/l\/[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}\/?$/;

function reply(res, status, headers, body) {
  res.writeHead(status, headers);
  res.end(body);
}

async function notFound(req, res, rootDir, pathname) {
  const extension = extname(pathname).toLowerCase();
  let page;
  if (extension === '' || extension === '.html') {
    try {
      page = await readFile(join(rootDir, '404.html'));
    } catch {
      page = undefined;
    }
  }
  if (!page) {
    reply(res, 404, { 'content-length': '0' });
    return;
  }
  reply(
    res,
    404,
    {
      'content-type': TYPES['.html'],
      'content-length': String(page.byteLength),
      'cache-control': 'no-cache',
    },
    req.method === 'HEAD' ? undefined : page,
  );
}

export function createApp({ root, htmlCacheControl = 'no-cache' }) {
  const rootDir = resolve(typeof root === 'string' ? root : fileURLToPath(root));
  return createServer(async (req, res) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      reply(res, 405, { allow: 'GET, HEAD', 'content-length': '0' });
      return;
    }
    let pathname;
    let url;
    try {
      url = new URL(req.url, 'http://site.local');
      pathname = decodeURIComponent(url.pathname);
    } catch {
      reply(res, 400, { 'content-length': '0' });
      return;
    }
    if (pathname.includes('\0')) {
      reply(res, 400, { 'content-length': '0' });
      return;
    }
    if (
      pathname === '/' && req.headers.host?.split(':')[0].toLowerCase() === 'docs.megabonkmod.party'
    ) {
      reply(res, 308, { location: `/home/${url.search}`, 'content-length': '0' });
      return;
    }
    if (pathname === '/docs' || pathname === '/docs/' || pathname === '/docs/index.md') {
      const destination = pathname.endsWith('.md') ? '/home.md' : '/home/';
      reply(res, 308, { location: destination + url.search, 'content-length': '0' });
      return;
    }
    if (pathname.startsWith('/docs/')) {
      reply(res, 308, {
        location: pathname.slice('/docs'.length) + url.search,
        'content-length': '0',
      });
      return;
    }
    if (LEVEL_ROUTE.test(pathname)) pathname = '/levels/view/index.html';
    if (pathname === '/' || pathname.endsWith('/')) pathname += 'index.html';
    const target = resolve(join(rootDir, pathname));
    if (target !== rootDir && !target.startsWith(rootDir + sep)) {
      await notFound(req, res, rootDir, pathname);
      return;
    }
    let body;
    try {
      if (!pathname.endsWith('index.html') && (await stat(target)).isDirectory()) {
        reply(res, 308, { location: `${url.pathname}/${url.search}`, 'content-length': '0' });
        return;
      }
      body = await readFile(target);
    } catch (error) {
      if (error.code === 'ENOENT' || error.code === 'EISDIR') {
        await notFound(req, res, rootDir, pathname);
        return;
      }
      reply(res, 500, { 'content-length': '0' });
      return;
    }
    const extension = extname(target).toLowerCase();
    const etag = `"${createHash('sha1').update(body).digest('base64url').slice(0, 22)}"`;
    const cacheControl = target.startsWith(join(rootDir, '_astro'))
      ? 'public, max-age=31536000, immutable'
      : extension === '.html'
      ? htmlCacheControl
      : 'public, max-age=3600';
    const matches = (req.headers['if-none-match'] ?? '').split(',').map((tag) =>
      tag.trim().replace(/^W\//, '')
    );
    if (matches.includes(etag)) {
      reply(res, 304, { etag, 'cache-control': cacheControl });
      return;
    }
    const headers = {
      'content-type': /\/wasm\.[\w-]+\.pagefind$/.test(target)
        ? 'application/wasm'
        : TYPES[extension] ?? 'application/octet-stream',
      'content-length': String(body.byteLength),
      'cache-control': cacheControl,
      etag,
    };
    reply(res, 200, headers, req.method === 'HEAD' ? undefined : body);
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = process.env.SITE_ROOT ?? new URL('dist/', import.meta.url);
  const host = process.env.HOST ?? '0.0.0.0';
  const port = Number(process.env.PORT ?? 8080);
  const server = createApp({
    root,
    htmlCacheControl: process.env.SITE_HTML_CACHE_CONTROL || undefined,
  });
  server.listen(port, host, () => console.log(`serving ${root} on http://${host}:${port}/`));
  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => server.close(() => process.exit(0)));
  }
}
