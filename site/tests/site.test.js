import assert from 'node:assert/strict';
import { access, readFile } from 'node:fs/promises';
import test from 'node:test';

const root = new URL('../dist/', import.meta.url);
const html = await readFile(new URL('index.html', root), 'utf8');

test('preserves the static showcase with the canonical domain', () => {
  assert.equal((html.match(/<h1\b/g) ?? []).length, 1);
  assert.match(html, /rel="canonical" href="https:\/\/megabonkmod\.party\/"/);
  for (const id of ['editor', 'console', 'mcp', 'start', 'editor-view', 'play-view']) {
    assert.ok(html.includes(`id="${id}"`), `${id} is present without client rendering`);
  }
});

test('all media and local assets resolve in the static output', async () => {
  for (const match of html.matchAll(/(?:src|href)="(\/[^"?#]*)"/g)) {
    await access(new URL(match[1].slice(1), root));
  }
  assert.equal((html.match(/class="video-placeholder"/g) ?? []).length, 2);
  assert.equal((html.match(/Video coming soon/g) ?? []).length, 2);
  assert.doesNotMatch(html, /<(?:video|iframe)\b/);
  assert.doesNotMatch(html, /<img\b[^>]*alt=""/);
});

test('contains truthful setup, formatted commands and non-scripted disclosures', () => {
  assert.doesNotMatch(
    html,
    /Public installer downloads aren’t available yet|No public release download yet/,
  );
  assert.match(html, /Windows build of Megabonk/);
  assert.match(html, /MEGABONK_DEV=true/);
  assert.match(html, /unofficial, fan-made mod/);
  assert.match(html, /<details>/);
  assert.match(html, /mcpServers/);
  assert.match(html, /level\.list/);
  assert.match(html, /scripts\/mcp_server\.py/);
  assert.match(
    html,
    /<a\b[^>]*href="https:\/\/thunderstore\.io\/c\/megabonk\/p\/BepInEx\/BepInExPack_IL2CPP\/"[^>]*>BepInEx 6 IL2CPP<\/a>/,
  );
  assert.match(html, /Megabonk Level Editor/);
  assert.match(html, /Thunderstore package does not include levels/);
  assert.doesNotMatch(html, /melon-loader\.com|included in default player packages/);
  assert.match(html, /do not activate it alongside MelonLoader/);
  assert.doesNotMatch(html, /<button[^>]*class="[^"]*copy-button/);
  assert.doesNotMatch(html, /Direction contract|SEED REFERENCE|OWN-WORLD/);
});

test('all fragment destinations exist', () => {
  for (const [, fragment] of html.matchAll(/href="#([^"]+)"/g)) {
    assert.ok(html.includes(`id="${fragment}"`), `missing #${fragment}`);
  }
});

test('start section links to the published player guide and Thunderstore release', () => {
  const start = html.match(/<section\b[^>]*id="start"[\s\S]*?<\/section>/)?.[0];
  assert.ok(start, 'start section exists');
  assert.match(start, /href="https:\/\/docs\.megabonkmod\.party\/docs\/player-guide\/"/);
  assert.match(
    start,
    /href="https:\/\/thunderstore\.io\/c\/megabonk\/p\/pythoninthegrass\/Megabonk_Level_Editor\/"/,
  );
  assert.doesNotMatch(start, /href="[^"]*\/blob\/main\/docs\/player-guide\.md"/);
  assert.doesNotMatch(start, /not.*available yet|No public release|development project/);
});

test('Docs uses the same navigation treatment as Source and links to the wiki', () => {
  const docs = html.match(
    /<a\b[^>]*href="https:\/\/docs\.megabonkmod\.party\/home\/"[^>]*>[\s\S]*?<\/a>/,
  )?.[0];
  assert.ok(docs, 'Docs navigation link is present');
  assert.match(docs, /class="source-link"/);
  assert.match(docs, />Docs\s*<svg\b/);
});

test('off-site links open safely in a new tab while local links stay in-page', () => {
  let externalCount = 0;
  for (const [anchor, href] of html.matchAll(/<a\b[^>]*href="([^"]+)"[^>]*>/g)) {
    const url = new URL(href, 'https://megabonkmod.party');
    if (url.origin === 'https://megabonkmod.party') {
      assert.doesNotMatch(anchor, /target="_blank"/, href);
      continue;
    }
    externalCount++;
    assert.match(anchor, /target="_blank"/, href);
    const rel = anchor.match(/rel="([^"]+)"/)?.[1].split(/\s+/) ?? [];
    assert.ok(rel.includes('noopener') && rel.includes('noreferrer'), href);
  }
  assert.ok(externalCount >= 10, 'checks Astro links and the Markdown setup link');
});
