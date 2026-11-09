import assert from 'node:assert/strict';
import test from 'node:test';
import { copyCommand } from '../src/scripts/clipboard.js';

test('copies the exact command without changing quotes or indentation', async () => {
  const command = 'console(line="help player")\nstate()';
  let actual;
  const result = await copyCommand(command, {
    writeText: async (text) => {
      actual = text;
    },
  });
  assert.equal(actual, command);
  assert.deepEqual(result, { ok: true, message: 'Copied' });
});

test('an unavailable clipboard gives a recoverable manual-copy message', async () => {
  assert.deepEqual(await copyCommand('help', undefined), {
    ok: false,
    message: 'Select the command to copy it manually.',
  });
});

test('a denied clipboard permission does not report success', async () => {
  const result = await copyCommand('help', {
    writeText: async () => {
      throw new Error('denied');
    },
  });
  assert.equal(result.ok, false);
  assert.equal(result.message, 'Select the command to copy it manually.');
});
