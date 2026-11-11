import assert from 'node:assert/strict';
import test from 'node:test';
import {
  buildFilter,
  formatCode,
  isShareCode,
  normalizeCode,
  packList,
  slugify,
  sortParam,
} from '../src/scripts/levels.js';

test('formatCode groups nine characters as XXX-XXX-XXX', () => {
  assert.equal(formatCode('7n1mvbwkf'), '7N1-MVB-WKF');
});

test('formatCode rejects input that is not nine characters', () => {
  assert.equal(formatCode('7N1MVB'), null);
  assert.equal(formatCode('7N1MVBWKFX'), null);
});

test('isShareCode accepts only the dashed Crockford form', () => {
  assert.equal(isShareCode('7N1-MVB-WKF'), true);
  assert.equal(isShareCode('7n1-mvb-wkf'), false);
  assert.equal(isShareCode('7N1MVBWKF'), false);
  assert.equal(isShareCode('7N1-MVB-WKU'), false, 'U is not in the Crockford alphabet');
  assert.equal(isShareCode('7N1-MVB-WKI'), false, 'I is not in the Crockford alphabet');
  assert.equal(isShareCode('../../etc'), false);
  assert.equal(isShareCode(undefined), false);
});

test('normalizeCode tolerates case, spacing and the Crockford lookalikes', () => {
  assert.equal(normalizeCode(' 7n1 mvb wkf '), '7N1-MVB-WKF');
  assert.equal(normalizeCode('7N1-MVB-WKF'), '7N1-MVB-WKF');
  assert.equal(normalizeCode('oil-oil-oil'), '011-011-011');
});

test('normalizeCode returns null for anything that cannot be a code', () => {
  assert.equal(normalizeCode(''), null);
  assert.equal(normalizeCode('too short'), null);
  assert.equal(normalizeCode('7N1-MVB-WK!'), null);
  assert.equal(normalizeCode(null), null);
});

test('slugify makes a filename-safe lowercase slug', () => {
  assert.equal(slugify('Bramblecrown Hill'), 'bramblecrown-hill');
  assert.equal(slugify('  THPS: Warehouse (v2)!  '), 'thps-warehouse-v2');
  assert.equal(slugify('a/b\\c..d'), 'a-b-c-d');
});

test('slugify falls back to level when nothing usable remains', () => {
  assert.equal(slugify(''), 'level');
  assert.equal(slugify('!!!'), 'level');
  assert.equal(slugify('スイッチ'), 'level');
  assert.equal(slugify(undefined), 'level');
});

test('buildFilter is empty without a search or tag', () => {
  assert.equal(buildFilter({}), '');
  assert.equal(buildFilter({ search: '   ', tag: '' }), '');
});

test('buildFilter matches title and description for a search term', () => {
  assert.equal(
    buildFilter({ search: 'forest' }),
    "(title ~ 'forest' || description ~ 'forest')",
  );
});

test('buildFilter combines search and tag', () => {
  assert.equal(
    buildFilter({ search: 'forest', tag: 'Speedrun' }),
    "(title ~ 'forest' || description ~ 'forest') && tags ~ 'Speedrun'",
  );
});

test('buildFilter escapes quotes so a search cannot break out of the string', () => {
  const filter = buildFilter({ search: "x' || hidden = true || title ~ '" });
  assert.equal(
    filter,
    "(title ~ 'x\\' || hidden = true || title ~ \\'' || description ~ 'x\\' || hidden = true || title ~ \\'')",
  );
});

test('buildFilter escapes a trailing backslash so it cannot eat the closing quote', () => {
  assert.equal(
    buildFilter({ search: 'a\\' }),
    "(title ~ 'a\\\\' || description ~ 'a\\\\')",
  );
});

test('buildFilter drops tags outside the fixed set', () => {
  assert.equal(buildFilter({ tag: "Speedrun' || 1=1" }), '');
});

test('sortParam maps each choice and defaults to newest', () => {
  assert.equal(sortParam('newest'), '-created');
  assert.equal(sortParam('liked'), '-likes,-created');
  assert.equal(sortParam('downloads'), '-downloads,-created');
  assert.equal(sortParam('bogus'), '-created');
  assert.equal(sortParam(undefined), '-created');
});

test('packList turns the packs object into sorted id and version rows', () => {
  assert.deepEqual(packList({ thps: '2.0.21', alpha: '1.0.0' }), [
    { id: 'alpha', version: '1.0.0' },
    { id: 'thps', version: '2.0.21' },
  ]);
});

test('packList tolerates missing or malformed packs', () => {
  assert.deepEqual(packList(undefined), []);
  assert.deepEqual(packList(null), []);
  assert.deepEqual(packList('thps'), []);
  assert.deepEqual(packList([]), []);
});
