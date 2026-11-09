import assert from 'node:assert/strict';
import test from 'node:test';
import { copyPage } from '../src/scripts/copy-page.js';

const markdown = '# Player guide\n\nSome `code`.\n';
const fetcher = async () => new Response(markdown);

test('copy fetches the exact raw Markdown endpoint', async () => {
  let copied;
  await copyPage('/docs/player-guide.md', {
    document: {},
    clipboard: {
      writeText: async (text) => {
        copied = text;
      },
    },
    fetcher: async (url) => {
      assert.equal(url, '/docs/player-guide.md');
      return new Response(markdown);
    },
  });
  assert.equal(copied, markdown);
});

test('a failed fetch never copies an error page', async () => {
  await assert.rejects(
    copyPage('/bad.md', {
      document: {},
      clipboard: { writeText: () => assert.fail('must not copy') },
      fetcher: async () => new Response('Not found', { status: 404 }),
    }),
    /404/,
  );
});

for (const denied of [false, true]) {
  test(`clipboard fallback copies, removes textarea and restores focus (${denied ? 'denied' : 'unavailable'})`, async () => {
    let removed = false;
    let focused = false;
    const textarea = {
      style: {},
      setAttribute() {},
      focus() {},
      select() {},
      remove() {
        removed = true;
      },
    };
    const document = {
      activeElement: {
        focus() {
          focused = true;
        },
      },
      body: {
        appendChild(node) {
          assert.equal(node, textarea);
        },
      },
      createElement: () => textarea,
      execCommand(command) {
        assert.equal(command, 'copy');
        assert.equal(textarea.value, markdown);
        return true;
      },
    };
    await copyPage('/docs/player-guide.md', {
      document,
      fetcher,
      clipboard: denied
        ? {
          writeText: async () => {
            throw new Error('denied');
          },
        }
        : undefined,
    });
    assert.ok(removed && focused);
    document.execCommand = () => false;
    await assert.rejects(
      copyPage('/docs/player-guide.md', { document, fetcher }),
      /Clipboard unavailable/,
    );
  });
}
