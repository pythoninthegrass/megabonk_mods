import assert from 'node:assert/strict';
import test from 'node:test';
import { viewRoute } from '../routes.mjs';

test('viewRoute maps share codes and account ids to their static pages', () => {
  assert.equal(viewRoute('/l/7N1-MVB-WKF'), '/levels/view/index.html');
  assert.equal(viewRoute('/l/7N1-MVB-WKF/'), '/levels/view/index.html');
  assert.equal(viewRoute('/u/abc123def456ghi'), '/creators/view/index.html');
  assert.equal(viewRoute('/u/abc123def456ghi/'), '/creators/view/index.html');
});

test('viewRoute maps a pack id to the pack page', () => {
  assert.equal(viewRoute('/p/thps'), '/packs/view/index.html');
  assert.equal(viewRoute('/p/my-pack_2/'), '/packs/view/index.html');
});

test('viewRoute leaves every other path alone', () => {
  for (
    const path of [
      '/',
      '/levels/',
      '/l/',
      '/l/7n1-mvb-wkf',
      '/u/short',
      '/u/ABC123DEF456GHI',
      '/u/abc123def456ghi/x',
      '/p/',
      '/p/Thps',
      '/p/thps/x',
    ]
  ) {
    assert.equal(viewRoute(path), null, path);
  }
});
