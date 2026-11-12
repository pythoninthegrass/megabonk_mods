import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const EXPECTED = {
  '.css': 'text/css',
  '.html': 'text/html',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript',
  '.json': 'application/json',
  '.md': 'text/markdown',
  '.mjs': 'text/javascript',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.txt': 'text/plain',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml',
};

function fail(message) {
  throw new Error(message);
}

function failIf(condition, message) {
  if (condition) fail(message);
}

function localReferences(html) {
  const refs = new Set();
  for (const [, ref] of html.matchAll(/(?:src|href)="(\/[^"?#]*)"/g)) refs.add(ref);
  for (const [, srcset] of html.matchAll(/srcset="([^"]*)"/g)) {
    for (const candidate of srcset.split(',')) {
      const ref = candidate.trim().split(/\s+/)[0];
      if (ref.startsWith('/')) refs.add(ref);
    }
  }
  return refs;
}

function countKind(ref, kinds) {
  const extension = ref.slice(ref.lastIndexOf('.'));
  if (extension === '.css') return kinds.css++;
  if (extension === '.js' || extension === '.mjs') return kinds.js++;
  if (['.jpg', '.jpeg', '.png', '.webp', '.svg', '.ico'].includes(extension)) return kinds.images++;
}

export async function runSmoke(baseUrl) {
  const home = await fetch(new URL('/', baseUrl));
  failIf(home.status !== 200, `home page answered ${home.status}`);
  failIf(
    !(home.headers.get('content-type') ?? '').startsWith('text/html'),
    'home page is not text/html',
  );
  const html = await home.text();
  failIf(!html.includes('<h1'), 'home page has no <h1>');
  const refs = localReferences(html);
  const wiki = await fetch(new URL('/home/', baseUrl));
  failIf(wiki.status !== 200, `wiki answered ${wiki.status}`);
  const wikiHtml = await wiki.text();
  failIf(!wikiHtml.includes('Megabonk Level Editor wiki'), 'wiki title is missing');
  for (const ref of localReferences(wikiHtml)) refs.add(ref);
  refs.add('/player-guide.md');
  refs.add('/pagefind/pagefind.js');
  refs.add('/llms.txt');
  refs.add('/.well-known/security.txt');
  const kinds = { css: 0, js: 0, images: 0 };
  for (const ref of refs) countKind(ref, kinds);
  failIf(kinds.css < 1, 'the home page references no local CSS');
  failIf(kinds.js < 1, 'the home page references no local JavaScript');
  failIf(kinds.images < 1, 'the home page references no local images');
  for (const ref of refs) {
    const response = await fetch(new URL(ref, baseUrl));
    failIf(response.status !== 200, `${ref} answered ${response.status}`);
    const extension = ref.slice(ref.lastIndexOf('.'));
    const expected = ref.endsWith('/') ? 'text/html' : EXPECTED[extension];
    failIf(!expected, `${ref} has the unexpected extension ${extension}`);
    const served = (response.headers.get('content-type') ?? '').split(';')[0];
    failIf(served !== expected, `${ref} served as ${served}, expected ${expected}`);
    const bytes = (await response.arrayBuffer()).byteLength;
    failIf(bytes === 0, `${ref} was served empty`);
  }
  return { references: refs.size, ...kinds };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const target = process.argv[2] ?? 'http://127.0.0.1:8080/';
  try {
    const { references, css, js, images } = await runSmoke(target);
    console.log(
      `smoke ok: ${target} served ${references} local references (${css} css, ${js} js, ${images} images)`,
    );
  } catch (error) {
    console.error(`smoke failed: ${error.message}`);
    process.exitCode = 1;
  }
}
