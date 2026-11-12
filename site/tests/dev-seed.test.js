import assert from 'node:assert/strict';
import test from 'node:test';
import {
  DEV_ADMIN_EMAILS,
  makerFromSignInPath,
  SEED_ACCESS,
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

test('seedLevels yields unique titles, two hidden levels and one real cover', () => {
  const levels = seedLevels();
  assert.equal(new Set(levels.map((level) => level.title)).size, levels.length);
  assert.equal(levels.filter((level) => level.hidden).length, 2);
  const covered = levels.filter((level) => level.cover);
  assert.deepEqual(covered.map((level) => [level.title, level.cover, level.hidden]), [
    ['Nameless level 3', 'bramblecrown-hill.png', true],
  ]);
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

test('the seed includes a site owner whose email is on the admin allowlist', () => {
  const owner = SEED_MAKERS.find((maker) => maker.name === 'Owner');
  assert.ok(owner && owner.levels > 0);
  assert.equal(DEV_ADMIN_EMAILS, owner.email);
});

test('the seeded visibility lists name real levels and makers', () => {
  const titles = new Set(seedLevels().map((level) => level.title));
  const emails = new Set(SEED_MAKERS.map((maker) => maker.email));
  assert.ok(SEED_ACCESS.some((entry) => entry.viewers?.length));
  assert.ok(SEED_ACCESS.some((entry) => entry.blocked?.length));
  for (const entry of SEED_ACCESS) {
    assert.ok(titles.has(entry.title), entry.title);
    for (const email of [...(entry.viewers ?? []), ...(entry.blocked ?? [])]) {
      assert.ok(emails.has(email), email);
    }
  }
});

test('signInPage keeps the admin flag so the owner sees the moderation controls', () => {
  const page = signInPage({ token: 't', record: { id: 'abc', name: 'Owner', admin: true } }, '/');
  assert.match(page, /"admin":true/);
});
