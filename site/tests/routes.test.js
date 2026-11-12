import assert from 'node:assert/strict';
import test from 'node:test';
import { viewRoute } from '../routes.mjs';

test('viewRoute maps share codes and account ids to their static pages', () => {
  assert.equal(viewRoute('/l/7N1-MVB-WKF'), '/levels/view/index.html');
  assert.equal(viewRoute('/l/7N1-MVB-WKF/'), '/levels/view/index.html');
  assert.equal(viewRoute('/u/abc123def456ghi'), '/creators/view/index.html');
  assert.equal(viewRoute('/u/abc123def456ghi/'), '/creators/view/index.html');
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
    ]
  ) {
    assert.equal(viewRoute(path), null, path);
  }
});
