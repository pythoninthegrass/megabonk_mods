import assert from 'node:assert/strict';
import test from 'node:test';
import {
  COPYRIGHT_GOOD_FAITH,
  COPYRIGHT_PERJURY,
  itemLink,
  REPORT_CATEGORIES,
  reportPayload,
} from '../src/scripts/reports.js';

test('REPORT_CATEGORIES offers copyright first and the server categories only', () => {
  assert.deepEqual(REPORT_CATEGORIES.map((category) => category.id), [
    'copyright',
    'broken',
    'inappropriate',
    'other',
  ]);
});

test('itemLink builds the public address of a level or a pack', () => {
  assert.equal(
    itemLink('https://megabonkmod.party', { level: { code: '7N1-MVB-WKF' } }),
    'https://megabonkmod.party/l/7N1-MVB-WKF',
  );
  assert.equal(
    itemLink('https://megabonkmod.party', { pack: { packId: 'thps' } }),
    'https://megabonkmod.party/p/thps',
  );
});

test('the two statements are the agreed good-faith and perjury wording', () => {
  assert.match(COPYRIGHT_GOOD_FAITH, /good faith/i);
  assert.match(COPYRIGHT_PERJURY, /penalty of perjury/i);
});

test('a plain report sends the target, category and trimmed reason only', () => {
  assert.deepEqual(
    reportPayload({
      userId: 'u1',
      target: { level: { id: 'l1' } },
      category: 'broken',
      reason: '  crashes  ',
    }),
    { user: 'u1', level: 'l1', category: 'broken', reason: 'crashes' },
  );
});

test('a pack report targets the pack record', () => {
  assert.deepEqual(
    reportPayload({ userId: 'u1', target: { pack: { id: 'p1' } }, category: 'other', reason: 'x' }),
    { user: 'u1', pack: 'p1', category: 'other', reason: 'x' },
  );
});

test('a copyright report carries the contact, work, link, statements and signature', () => {
  const payload = reportPayload({
    userId: 'u1',
    target: { pack: { id: 'p1' } },
    category: 'copyright',
    reason: ' extra ',
    copyright: {
      contactEmail: ' a@b.test ',
      contactAddress: '',
      contactPhone: '',
      work: ' The map ',
      itemUrl: 'https://megabonkmod.party/p/thps',
      goodFaith: true,
      accurate: true,
      fairUseConsidered: true,
      signature: ' Rita Rightsholder ',
    },
  });
  assert.deepEqual(payload, {
    user: 'u1',
    pack: 'p1',
    category: 'copyright',
    reason: 'extra',
    contactEmail: 'a@b.test',
    contactAddress: '',
    contactPhone: '',
    work: 'The map',
    itemUrl: 'https://megabonkmod.party/p/thps',
    goodFaith: true,
    accurate: true,
    fairUseConsidered: true,
    signature: 'Rita Rightsholder',
  });
});

test('a non-copyright report never sends the copyright fields', () => {
  const payload = reportPayload({
    userId: 'u1',
    target: { level: { id: 'l1' } },
    category: 'other',
    reason: 'x',
    copyright: { work: 'leftover', signature: 'someone' },
  });
  assert.equal('work' in payload, false);
  assert.equal('signature' in payload, false);
});
