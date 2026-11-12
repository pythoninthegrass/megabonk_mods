import assert from 'node:assert/strict';
import test from 'node:test';
import { SEED_MAKERS, seedLevels, signInSnippet } from '../scripts/dev-seed.mjs';

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

test('signInSnippet stores the session the SDK reads from localStorage', () => {
  const snippet = signInSnippet({ token: 'tok', record: { id: 'abc' } });
  assert.equal(
    snippet,
    `localStorage.setItem('pocketbase_auth', ${
      JSON.stringify(JSON.stringify({ token: 'tok', record: { id: 'abc' } }))
    })`,
  );
});
