import assert from 'node:assert/strict';
import test from 'node:test';
import {
  makerFromSignInPath,
  SEED_MAKERS,
  seedLevels,
  signInPage,
  signInPath,
} from '../scripts/dev-seed.mjs';

test('the seed covers a named maker, a nameless maker and a maker with no levels', () => {
  assert.ok(SEED_MAKERS.some((maker) => maker.name && maker.levels > 12));
  assert.ok(SEED_MAKERS.some((maker) => maker.name === '' && maker.levels > 0));
  assert.ok(SEED_MAKERS.some((maker) => maker.levels === 0));
});

test('seedLevels yields unique titles with exactly one hidden level', () => {
  const levels = seedLevels();
  assert.equal(new Set(levels.map((level) => level.title)).size, levels.length);
  assert.equal(levels.filter((level) => level.hidden).length, 1);
  assert.equal(levels.length, SEED_MAKERS.reduce((sum, maker) => sum + maker.levels, 0));
  assert.ok(levels.every((level) => SEED_MAKERS.some((maker) => maker.email === level.maker)));
});

test('every maker has a short sign-in path that resolves back to them', () => {
  for (const maker of SEED_MAKERS) {
    const path = signInPath(maker);
    assert.ok(path.length <= 40, path);
    assert.equal(makerFromSignInPath(path), maker);
  }
  assert.equal(makerFromSignInPath('/__dev/signin/nobody'), undefined);
  assert.equal(makerFromSignInPath('/levels/'), undefined);
});

test('signInPage stores a compact session then redirects', () => {
  const page = signInPage({
    token: 'tok',
    record: { id: 'abc', name: 'Al"ice', email: 'a@dev.test' },
  }, '/u/abc');
  assert.match(page, /localStorage\.setItem\('pocketbase_auth', JSON\.stringify\(/);
  assert.match(page, /location\.replace\("\/u\/abc"\)/);
  assert.doesNotMatch(page, /a@dev\.test/);
  assert.match(page, /Al\\"ice/);
});
