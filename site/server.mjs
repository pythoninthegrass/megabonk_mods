import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
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
  '.mjs': 'text/javascript; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
};

function reply(res, status, headers, body) {
  res.writeHead(status, headers);
  res.end(body);
}

export function createApp({ root }) {
  const rootDir = resolve(typeof root === 'string' ? root : fileURLToPath(root));
  return createServer(async (req, res) => {
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      reply(res, 405, { allow: 'GET, HEAD', 'content-length': '0' });
      return;
    }
    let pathname;
    try {
      pathname = decodeURIComponent(new URL(req.url, 'http://site.local').pathname);
    } catch {
      reply(res, 400, { 'content-length': '0' });
      return;
    }
    if (pathname.includes('\0')) {
      reply(res, 400, { 'content-length': '0' });
      return;
    }
    if (pathname === '/' || pathname.endsWith('/')) pathname += 'index.html';
    const target = resolve(join(rootDir, pathname));
    if (target !== rootDir && !target.startsWith(rootDir + sep)) {
      reply(res, 404, { 'content-length': '0' });
      return;
    }
    let body;
    try {
      body = await readFile(target);
    } catch (error) {
      reply(res, error.code === 'ENOENT' || error.code === 'EISDIR' ? 404 : 500, { 'content-length': '0' });
      return;
    }
    const headers = {
      'content-type': TYPES[extname(target).toLowerCase()] ?? 'application/octet-stream',
      'content-length': String(body.byteLength),
      'cache-control': target.startsWith(join(rootDir, '_astro'))
        ? 'public, max-age=31536000, immutable'
        : target === join(rootDir, 'index.html')
          ? 'no-cache'
          : 'public, max-age=3600',
    };
    reply(res, 200, headers, req.method === 'HEAD' ? undefined : body);
  });
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = process.env.SITE_ROOT ?? new URL('dist/', import.meta.url);
  const host = process.env.HOST ?? '0.0.0.0';
  const port = Number(process.env.PORT ?? 8080);
  const server = createApp({ root });
  server.listen(port, host, () => console.log(`serving ${root} on http://${host}:${port}/`));
  for (const signal of ['SIGINT', 'SIGTERM']) {
    process.on(signal, () => server.close(() => process.exit(0)));
  }
}
