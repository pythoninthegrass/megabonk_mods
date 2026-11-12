import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import {
  availableProviders,
  codeFromPath,
  codeFromSearch,
  coverUrl,
  CREATOR_FIELDS,
  creatorFilter,
  creatorIdFromPath,
  creatorUrl,
  downloadUrl,
  editCodeFromSearch,
  editFormState,
  editUrl,
  excerpt,
  giscusAttrs,
  isOwner,
  levelFormData,
  likesFilter,
  likeTitle,
  mapName,
  pbErrorMessages,
  plural,
  relativeDate,
  sumCounts,
} from '../src/scripts/gallery.js';
import { buildFilter } from '../src/scripts/levels.js';

const NOW = Date.parse('2026-11-11T12:00:00Z');

test('relativeDate reads PocketBase timestamps as UTC', () => {
  assert.equal(relativeDate('2026-11-11 11:59:30.000Z', NOW), 'just now');
  assert.equal(relativeDate('2026-11-11 11:55:00.000Z', NOW), '5 minutes ago');
  assert.equal(relativeDate('2026-11-11 11:00:00.000Z', NOW), '1 hour ago');
  assert.equal(relativeDate('2026-11-09 12:00:00.000Z', NOW), '2 days ago');
  assert.equal(relativeDate('2026-08-11 12:00:00.000Z', NOW), '3 months ago');
  assert.equal(relativeDate('2024-11-11 12:00:00.000Z', NOW), '2 years ago');
});

test('relativeDate returns an empty string for an unreadable date', () => {
  assert.equal(relativeDate('', NOW), '');
  assert.equal(relativeDate('not a date', NOW), '');
  assert.equal(relativeDate(undefined, NOW), '');
});

test('excerpt collapses whitespace and cuts long text at a word boundary', () => {
  assert.equal(excerpt('  a\n\n b   c ', 50), 'a b c');
  assert.equal(excerpt('one two three four', 10), 'one two…');
  assert.equal(excerpt('', 10), '');
  assert.equal(excerpt(undefined, 10), '');
});

test('excerpt keeps a single overlong word instead of returning nothing', () => {
  assert.equal(excerpt('abcdefghijklmnop', 5), 'abcde…');
});

test('coverUrl points at the PocketBase file route with an optional thumb', () => {
  const record = { id: 'rec123', cover: 'cover_x1.png' };
  assert.equal(
    coverUrl('http://pb.test', record),
    'http://pb.test/api/files/levels/rec123/cover_x1.png',
  );
  assert.equal(
    coverUrl('http://pb.test', record, '320x0'),
    'http://pb.test/api/files/levels/rec123/cover_x1.png?thumb=320x0',
  );
});

test('coverUrl returns null when the record has no cover', () => {
  assert.equal(coverUrl('http://pb.test', { id: 'rec123', cover: '' }), null);
});

test('downloadUrl uses the counted download route', () => {
  assert.equal(
    downloadUrl('http://pb.test', '7N1-MVB-WKF'),
    'http://pb.test/api/l/7N1-MVB-WKF/download',
  );
});

test('downloadUrl refuses anything that is not a share code', () => {
  assert.equal(downloadUrl('http://pb.test', '../admin'), null);
});

test('codeFromPath reads the code from /l/<code>', () => {
  assert.equal(codeFromPath('/l/7N1-MVB-WKF'), '7N1-MVB-WKF');
  assert.equal(codeFromPath('/l/7N1-MVB-WKF/'), '7N1-MVB-WKF');
});

test('codeFromPath returns null for a malformed or missing code', () => {
  assert.equal(codeFromPath('/l/'), null);
  assert.equal(codeFromPath('/l/7N1-MVB'), null);
  assert.equal(codeFromPath('/l/7n1-mvb-wkf'), null);
  assert.equal(codeFromPath('/levels/view/'), null);
  assert.equal(codeFromPath('/l/7N1-MVB-WKF/extra'), null);
});

test('pbErrorMessages lists each field error from a PocketBase response', () => {
  const error = {
    status: 400,
    message: 'Failed to create record.',
    response: {
      message: 'Failed to create record.',
      data: {
        level: {
          code: 'validation_invalid_level_file',
          message: 'Invalid level file: title is required',
        },
        cover: { code: 'validation_required', message: 'Cannot be blank.' },
      },
    },
  };
  assert.deepEqual(pbErrorMessages(error), [
    'level: Invalid level file: title is required',
    'cover: Cannot be blank.',
  ]);
});

test('pbErrorMessages falls back to the response message', () => {
  const error = {
    status: 403,
    message: 'x',
    response: { message: 'Only admins can do that.', data: {} },
  };
  assert.deepEqual(pbErrorMessages(error), ['Only admins can do that.']);
});

test('pbErrorMessages reports an unreachable server', () => {
  assert.deepEqual(pbErrorMessages({ status: 0, message: 'fetch failed' }), [
    'Could not reach the gallery server. Try again in a moment.',
  ]);
});

test('pbErrorMessages tolerates a non-error value', () => {
  assert.deepEqual(pbErrorMessages(undefined), ['Something went wrong. Try again.']);
});

test('buildFilter keeps hostile search text inside one quoted literal', () => {
  const filter = buildFilter({ search: `x') || hidden = true || (title ~ 'y\\` });
  assert.equal(
    filter,
    `(title ~ 'x\\') || hidden = true || (title ~ \\'y\\\\' || description ~ 'x\\') || hidden = true || (title ~ \\'y\\\\')`,
  );
});

test('buildFilter drops a tag outside the fixed set', () => {
  assert.equal(buildFilter({ tag: `Puzzle' || hidden = true || tags ~ 'x` }), '');
});

const GISCUS = { repo: 'o/r', repoId: 'R_1', category: 'Levels', categoryId: 'DIC_1' };

test('giscusAttrs keys the thread by the share code with specific mapping', () => {
  assert.deepEqual(giscusAttrs(GISCUS, '7N1-MVB-WKF'), {
    'data-repo': 'o/r',
    'data-repo-id': 'R_1',
    'data-category': 'Levels',
    'data-category-id': 'DIC_1',
    'data-mapping': 'specific',
    'data-term': '7N1-MVB-WKF',
    'data-strict': '1',
    'data-reactions-enabled': '1',
    'data-input-position': 'top',
    'data-theme': 'light',
    'data-lang': 'en',
  });
});

test('giscusAttrs returns null while any setting is unset', () => {
  for (const key of Object.keys(GISCUS)) {
    assert.equal(giscusAttrs({ ...GISCUS, [key]: '' }, '7N1-MVB-WKF'), null);
    assert.equal(giscusAttrs({ ...GISCUS, [key]: undefined }, '7N1-MVB-WKF'), null);
  }
});

test('giscusAttrs returns null for a malformed code', () => {
  assert.equal(giscusAttrs(GISCUS, 'nope'), null);
});

test('mapName names the biomes the level format defines', () => {
  assert.equal(mapName(1), 'Forest');
  assert.equal(mapName(2), 'Desert');
  assert.equal(mapName(8), 'Graveyard');
  assert.equal(mapName(16), 'Dungeon');
  assert.equal(mapName(64), 'Hell');
});

test('mapName leaves an unset or unknown map unnamed', () => {
  assert.equal(mapName(0), 'Not set');
  assert.equal(mapName(undefined), 'Not set');
  assert.equal(mapName(99), 'Map 99');
});

test('pbErrorMessages uses the response message when a field detail is not a message', () => {
  const error = {
    status: 400,
    message: 'x',
    response: {
      message: 'Invalid level file: title is required',
      data: {
        level: {
          code: { code: 'validation_invalid_value', message: 'Invalid value.' },
          message: { code: 'validation_invalid_value', message: 'Invalid value.' },
        },
      },
    },
  };
  assert.deepEqual(pbErrorMessages(error), ['Invalid level file: title is required']);
});

test('plural counts a noun with the right ending', () => {
  assert.equal(plural(0, 'like'), '0 likes');
  assert.equal(plural(1, 'like'), '1 like');
  assert.equal(plural(2, 'download'), '2 downloads');
  assert.equal(plural(undefined, 'like'), '0 likes');
});

test('codeFromSearch recognises a pasted dashed share code', () => {
  assert.equal(codeFromSearch('7N1-MVB-WKF'), '7N1-MVB-WKF');
  assert.equal(codeFromSearch('  7n1-mvb-wkf '), '7N1-MVB-WKF');
});

test('codeFromSearch ignores ordinary search text, even nine letters long', () => {
  assert.equal(codeFromSearch('bramble'), null);
  assert.equal(codeFromSearch('gardenkit'), null);
  assert.equal(codeFromSearch('7N1MVBWKF'), null);
  assert.equal(codeFromSearch(''), null);
  assert.equal(codeFromSearch(undefined), null);
});

const KNOWN = [
  { id: 'github', label: 'GitHub' },
  { id: 'google', label: 'Google' },
  { id: 'discord', label: 'Discord' },
];

test('availableProviders keeps the known providers the server has configured', () => {
  const methods = {
    oauth2: { enabled: true, providers: [{ name: 'discord' }, { name: 'github' }] },
  };
  assert.deepEqual(availableProviders(methods, KNOWN).map((p) => p.id), ['github', 'discord']);
});

test('availableProviders ignores providers the site has no button for', () => {
  const methods = {
    oauth2: { enabled: true, providers: [{ name: 'gitlab' }, { name: 'google' }] },
  };
  assert.deepEqual(availableProviders(methods, KNOWN).map((p) => p.id), ['google']);
});

test('availableProviders is empty when sign-in is off or the response is unusable', () => {
  assert.deepEqual(
    availableProviders({ oauth2: { enabled: false, providers: [{ name: 'github' }] } }, KNOWN),
    [],
  );
  assert.deepEqual(availableProviders({}, KNOWN), []);
  assert.deepEqual(availableProviders(undefined, KNOWN), []);
});

test('editUrl links to the upload page with the share code to edit', () => {
  assert.equal(editUrl('7N1-MVB-WKF'), '/levels/upload/?edit=7N1-MVB-WKF');
});

test('editUrl refuses anything that is not a share code', () => {
  assert.equal(editUrl('not-a-code'), null);
  assert.equal(editUrl(undefined), null);
});

test('editCodeFromSearch reads a share code from the edit parameter', () => {
  assert.equal(editCodeFromSearch('?edit=7n1-mvb-wkf'), '7N1-MVB-WKF');
  assert.equal(editCodeFromSearch('?q=x&edit=7N1-MVB-WKF'), '7N1-MVB-WKF');
});

test('editCodeFromSearch ignores a missing or malformed edit parameter', () => {
  assert.equal(editCodeFromSearch(''), null);
  assert.equal(editCodeFromSearch('?edit='), null);
  assert.equal(editCodeFromSearch('?edit=../../x'), null);
});

test('isOwner is true only when a signed-in user authored the level', () => {
  assert.equal(isOwner({ id: 'u1' }, { author: 'u1' }), true);
  assert.equal(isOwner({ id: 'u1' }, { author: 'u2' }), false);
  assert.equal(isOwner(null, { author: 'u1' }), false);
  assert.equal(isOwner({ id: 'u1' }, null), false);
  assert.equal(isOwner({ id: undefined }, { author: undefined }), false);
});

test('editFormState carries the existing description and tags into the form', () => {
  const level = { description: 'A hill of brambles.', tags: ['Platforming', 'Short'] };
  const state = editFormState(level);
  assert.deepEqual(state, { description: 'A hill of brambles.', chosen: ['Platforming', 'Short'] });
  state.chosen.push('Puzzle');
  assert.deepEqual(level.tags, ['Platforming', 'Short'], 'the level record is not mutated');
});

test('editFormState defaults a level without a description or tags', () => {
  assert.deepEqual(editFormState({}), { description: '', chosen: [] });
});

test('levelFormData resends the existing description and tags unchanged on save', () => {
  const form = levelFormData(
    editFormState({ description: 'Keep me.', tags: ['Speedrun', 'Short'] }),
    {},
  );
  assert.equal(form.get('description'), 'Keep me.');
  assert.deepEqual(form.getAll('tags'), ['Speedrun', 'Short']);
});

test('levelFormData clears the tags when none are chosen and adds only chosen files', () => {
  const cover = new Blob(['x'], { type: 'image/png' });
  const form = levelFormData({ description: '', chosen: [] }, { cover, level: undefined });
  assert.equal(form.get('tags'), '');
  assert.ok(form.get('cover') instanceof Blob);
  assert.equal(form.has('level'), false);
});

test('likesFilter matches any of the given level ids', () => {
  assert.equal(
    likesFilter(['abc123def456ghi', 'zzz999yyy888xxx']),
    'level = "abc123def456ghi" || level = "zzz999yyy888xxx"',
  );
});

test('likesFilter drops anything that is not a PocketBase record id', () => {
  assert.equal(
    likesFilter(['abc123def456ghi', '" || 1=1 || "', '', undefined, 42]),
    'level = "abc123def456ghi"',
  );
  assert.equal(likesFilter(['nope']), '');
  assert.equal(likesFilter([]), '');
});

test('likeTitle says what clicking the heart will do', () => {
  assert.equal(likeTitle(false, false), 'Sign in to like this level');
  assert.equal(likeTitle(true, false), 'Like this level');
  assert.equal(likeTitle(true, true), 'Remove your like');
});

const ID = 'abc123def456ghi';

test('creatorIdFromPath accepts only a 15 character lowercase alphanumeric id', () => {
  assert.equal(creatorIdFromPath(`/u/${ID}`), ID);
  assert.equal(creatorIdFromPath(`/u/${ID}/`), ID);
  for (
    const path of [
      '/u/',
      '/u/short',
      `/u/${ID}x`,
      `/u/${ID.toUpperCase()}`,
      `/u/${ID}/extra`,
      `/x/${ID}`,
      null,
    ]
  ) {
    assert.equal(creatorIdFromPath(path), null, String(path));
  }
});

test('creatorUrl links by account id and rejects anything else', () => {
  assert.equal(creatorUrl(ID), `/u/${ID}`);
  assert.equal(creatorUrl('bad id'), null);
  assert.equal(creatorUrl(undefined), null);
});

test('creatorFilter matches the author id exactly', () => {
  assert.equal(creatorFilter(ID), `author = "${ID}"`);
  assert.equal(creatorFilter('x" || true'), null);
});

test('sumCounts totals likes and downloads and tolerates missing values', () => {
  assert.deepEqual(sumCounts([{ likes: 2, downloads: 5 }, { likes: 1 }, {}]), {
    likes: 3,
    downloads: 5,
  });
  assert.deepEqual(sumCounts([]), { likes: 0, downloads: 0 });
});

test('the creator page requests only public account fields', async () => {
  assert.equal(CREATOR_FIELDS, 'id,name,created');
  for (const file of ['src/scripts/creator-view.js', 'src/pages/creators/view/index.astro']) {
    assert.doesNotMatch(await readFile(file, 'utf8'), /email|verified|username/i, file);
  }
});
