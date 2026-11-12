import assert from 'node:assert/strict';
import test from 'node:test';
import { cacheKey, readCached, writeCached } from '../src/scripts/result-cache.js';

const memoryStorage = () => {
  const map = new Map();
  return {
    getItem: (key) => map.get(key) ?? null,
    setItem: (key, value) => map.set(key, value),
  };
};

test('cacheKey differs by scope, user and every part', () => {
  const user = { id: 'a' };
  const keys = new Set([
    cacheKey('browse', user, [1, '', '', 'newest']),
    cacheKey('creator', user, [1, '', '', 'newest']),
    cacheKey('browse', { id: 'b' }, [1, '', '', 'newest']),
    cacheKey('browse', user, [2, '', '', 'newest']),
    cacheKey('browse', user, [1, 'x', '', 'newest']),
    cacheKey('browse', user, [1, '', 'forest', 'newest']),
    cacheKey('browse', user, [1, '', '', 'liked']),
  ]);
  assert.equal(keys.size, 7);
});

test('cacheKey treats a signed-out visitor as one user', () => {
  assert.equal(cacheKey('browse', null, [1]), cacheKey('browse', undefined, [1]));
});

test('readCached returns what writeCached stored', () => {
  const storage = memoryStorage();
  const value = { items: [{ id: 1 }], totalPages: 3, totalItems: 30 };
  writeCached(storage, 'k', value);
  assert.deepEqual(readCached(storage, 'k'), value);
});

test('readCached returns null for a missing or corrupt entry', () => {
  const storage = memoryStorage();
  assert.equal(readCached(storage, 'missing'), null);
  storage.setItem('bad', '{not json');
  assert.equal(readCached(storage, 'bad'), null);
});

test('readCached and writeCached tolerate unavailable storage', () => {
  const broken = {
    getItem() {
      throw new Error('blocked');
    },
    setItem() {
      throw new Error('blocked');
    },
  };
  assert.equal(readCached(broken, 'k'), null);
  assert.doesNotThrow(() => writeCached(broken, 'k', {}));
  assert.equal(readCached(undefined, 'k'), null);
});
