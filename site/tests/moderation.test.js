import assert from 'node:assert/strict';
import test from 'node:test';
import { moderation } from '../src/scripts/moderation.js';

function setup({ confirmed = true, fail = false } = {}) {
  const calls = [];
  const collection = (name) => ({
    delete: async (id) => {
      calls.push(['delete', name, id]);
      if (fail) throw { response: { message: 'Only admins can do that.' } };
    },
    update: async (id, body) => {
      calls.push(['update', name, id, body]);
      if (fail) throw { response: { message: 'Only admins can do that.' } };
      return { id, ...body };
    },
  });
  const prompts = [];
  const session = moderation({
    pb: { collection },
    confirm: (message) => {
      prompts.push(message);
      return confirmed;
    },
  });
  return { session, calls, prompts };
}

test('deleteLevel asks first, naming the level, then deletes it', async () => {
  const { session, calls, prompts } = setup();
  assert.equal(await session.deleteLevel({ id: 'l1', title: 'Warehouse' }), true);
  assert.match(prompts[0], /Warehouse/);
  assert.deepEqual(calls, [['delete', 'levels', 'l1']]);
});

test('deleteLevel does nothing when the prompt is declined', async () => {
  const { session, calls } = setup({ confirmed: false });
  assert.equal(await session.deleteLevel({ id: 'l1', title: 'Warehouse' }), false);
  assert.deepEqual(calls, []);
});

test('a failed delete reports false and sets adminError', async () => {
  const { session } = setup({ fail: true });
  assert.equal(await session.deleteLevel({ id: 'l1', title: 'x' }), false);
  assert.equal(session.adminError, 'Only admins can do that.');
});

test('setHidden updates the hidden flag', async () => {
  const { session, calls } = setup();
  assert.equal(await session.setHidden({ id: 'l1' }, true), true);
  assert.deepEqual(calls, [['update', 'levels', 'l1', { hidden: true }]]);
});

test('setAccess replaces both visibility lists', async () => {
  const { session, calls } = setup();
  assert.equal(await session.setAccess({ id: 'l1' }, { viewers: ['u1'], blocked: [] }), true);
  assert.deepEqual(calls, [['update', 'levels', 'l1', { viewers: ['u1'], blocked: [] }]]);
});

test('a successful action clears the previous error', async () => {
  const { session } = setup();
  session.adminError = 'stale';
  await session.setHidden({ id: 'l1' }, false);
  assert.equal(session.adminError, '');
});

test('toggleHidden flips the flag on the level once the update succeeds', async () => {
  const { session, calls } = setup();
  const level = { id: 'l1', hidden: false };
  assert.equal(await session.toggleHidden(level), true);
  assert.equal(level.hidden, true);
  assert.deepEqual(calls, [['update', 'levels', 'l1', { hidden: true }]]);
});

test('toggleHidden leaves the flag alone when the update fails', async () => {
  const { session } = setup({ fail: true });
  const level = { id: 'l1', hidden: true };
  assert.equal(await session.toggleHidden(level), false);
  assert.equal(level.hidden, true);
});
