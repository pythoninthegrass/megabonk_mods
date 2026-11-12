import assert from 'node:assert/strict';
import test from 'node:test';
import {
  formatBytes,
  hostedPacks,
  isPackId,
  packDownloadUrl,
  packFilter,
  packFormData,
  packIdFromPath,
  packPlatforms,
  packsFilter,
  packUploadTooLarge,
  packUrl,
} from '../src/scripts/packs.js';

test('isPackId accepts a safe lowercase folder name only', () => {
  for (const id of ['thps', 'a', 'my-pack_2', '0day']) assert.equal(isPackId(id), true, id);
  for (const id of ['', 'Thps', '-x', '_x', 'a b', '../x', 'a.b', 'a'.repeat(65), undefined, 5]) {
    assert.equal(isPackId(id), false, String(id));
  }
});

test('packUrl and packIdFromPath round-trip a pack id', () => {
  assert.equal(packUrl('thps'), '/p/thps');
  assert.equal(packUrl('thps', '2.0.1'), '/p/thps?v=2.0.1');
  assert.equal(packUrl('Bad Id'), null);
  assert.equal(packIdFromPath('/p/thps'), 'thps');
  assert.equal(packIdFromPath('/p/thps/'), 'thps');
  assert.equal(packIdFromPath('/p/Thps'), null);
  assert.equal(packIdFromPath('/p/thps/extra'), null);
  assert.equal(packIdFromPath('/levels/'), null);
});

test('packDownloadUrl names the platform and optionally the version', () => {
  assert.equal(
    packDownloadUrl('http://pb', 'thps', 'windows'),
    'http://pb/api/p/thps/download?platform=windows',
  );
  assert.equal(
    packDownloadUrl('http://pb', 'thps', 'linux', '2.0.1'),
    'http://pb/api/p/thps/download?platform=linux&version=2.0.1',
  );
  assert.equal(packDownloadUrl('http://pb', 'thps', 'mac'), null);
  assert.equal(packDownloadUrl('http://pb', '../x', 'linux'), null);
});

test('packPlatforms lists the platforms that have a bundle', () => {
  assert.deepEqual(packPlatforms({ sizeWindows: 10, sizeLinux: 20 }).map((p) => p.id), [
    'windows',
    'linux',
  ]);
  assert.deepEqual(packPlatforms({ sizeWindows: 0, sizeLinux: 5 }).map((p) => p.id), ['linux']);
  assert.deepEqual(packPlatforms({ sizeWindows: 10, sizeLinux: 5 })[0], {
    id: 'windows',
    label: 'Windows',
    size: 10,
  });
  assert.deepEqual(packPlatforms(null), []);
});

test('formatBytes uses the largest sensible unit', () => {
  assert.equal(formatBytes(0), '0 B');
  assert.equal(formatBytes(900), '900 B');
  assert.equal(formatBytes(1536), '1.5 KiB');
  assert.equal(formatBytes(5 * 1024 * 1024), '5.0 MiB');
});

test('packFilter and packsFilter quote only safe ids', () => {
  assert.equal(packFilter('thps'), 'packId = "thps"');
  assert.equal(packFilter('x" || 1=1'), null);
  assert.equal(packsFilter(['a', 'b', 'bad id']), 'packId = "a" || packId = "b"');
  assert.equal(packsFilter([]), '');
});

test('hostedPacks marks a pack hosted with a matching version as current', () => {
  const rows = hostedPacks({ thps: '2.0.1' }, [
    { packId: 'thps', version: '2.0.1', created: '2026-11-02 00:00:00.000Z' },
  ]);
  assert.deepEqual(rows, [
    { id: 'thps', version: '2.0.1', hosted: true, mismatch: false, hostedVersion: '2.0.1' },
  ]);
});

test('hostedPacks flags a mismatch and names the newest hosted version', () => {
  const rows = hostedPacks({ thps: '1.0.0' }, [
    { packId: 'thps', version: '1.5.0', created: '2026-11-01 00:00:00.000Z' },
    { packId: 'thps', version: '2.0.0', created: '2026-11-03 00:00:00.000Z' },
  ]);
  assert.equal(rows[0].hosted, true);
  assert.equal(rows[0].mismatch, true);
  assert.equal(rows[0].hostedVersion, '2.0.0');
});

test('hostedPacks treats an older hosted version that equals the recorded one as a match', () => {
  const rows = hostedPacks({ thps: '1.5.0' }, [
    { packId: 'thps', version: '1.5.0', created: '2026-11-01 00:00:00.000Z' },
    { packId: 'thps', version: '2.0.0', created: '2026-11-03 00:00:00.000Z' },
  ]);
  assert.equal(rows[0].mismatch, false);
  assert.equal(rows[0].hostedVersion, '1.5.0');
});

test('hostedPacks keeps a pack that is not hosted and sorts by id', () => {
  const rows = hostedPacks({ zzz: '1', thps: '2' }, []);
  assert.deepEqual(rows.map((row) => [row.id, row.hosted, row.mismatch]), [
    ['thps', false, false],
    ['zzz', false, false],
  ]);
  assert.deepEqual(hostedPacks(undefined, []), []);
});

test('packFormData carries the attestation, description and files', () => {
  const manifest = new Blob(['{}']);
  const form = packFormData(
    { packId: 'thps', description: 'Hello', attested: true },
    { manifest, attachments: null, bundleWindows: new Blob(['x']), bundleLinux: undefined },
  );
  assert.equal(form.get('packId'), 'thps');
  assert.equal(form.get('description'), 'Hello');
  assert.equal(form.get('attested'), 'true');
  assert.ok(form.get('manifest'));
  assert.ok(form.get('bundleWindows'));
  assert.equal(form.has('attachments'), false);
  assert.equal(form.has('bundleLinux'), false);
});

test('packUploadTooLarge compares the combined file size with 30 MiB', () => {
  const file = (size) => ({ size });
  assert.equal(packUploadTooLarge([file(10), null, undefined, file(20)]), '');
  assert.equal(packUploadTooLarge([file(30 * 1024 * 1024)]), '');
  assert.match(
    packUploadTooLarge([file(30 * 1024 * 1024), file(1)]),
    /30 MiB.*30\.0 MiB/,
  );
});
