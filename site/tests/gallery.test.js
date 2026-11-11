import assert from 'node:assert/strict';
import test from 'node:test';
import {
  codeFromPath,
  codeFromSearch,
  coverUrl,
  downloadUrl,
  excerpt,
  giscusAttrs,
  mapName,
  pbErrorMessages,
  plural,
  relativeDate,
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
