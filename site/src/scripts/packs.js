const PACK_ID = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const MAX_PACK_BYTES = 30 * 1024 * 1024;
const PLATFORMS = [
  { id: 'windows', label: 'Windows', size: 'sizeWindows' },
  { id: 'linux', label: 'Linux', size: 'sizeLinux' },
];

export function isPackId(value) {
  return typeof value === 'string' && PACK_ID.test(value);
}

export function packUrl(id, version = '') {
  if (!isPackId(id)) return null;
  return version ? `/p/${id}?v=${encodeURIComponent(version)}` : `/p/${id}`;
}

export function packIdFromPath(pathname) {
  const match = /^\/p\/([^/]+)\/?$/.exec(String(pathname ?? ''));
  return match && isPackId(match[1]) ? match[1] : null;
}

export function packDownloadUrl(base, id, platform, version = '') {
  if (!isPackId(id) || !PLATFORMS.some((entry) => entry.id === platform)) return null;
  const url = `${base}/api/p/${id}/download?platform=${platform}`;
  return version ? `${url}&version=${encodeURIComponent(version)}` : url;
}

export function packPlatforms(pack) {
  if (!pack) return [];
  return PLATFORMS
    .filter((entry) => pack[entry.size] > 0)
    .map((entry) => ({ id: entry.id, label: entry.label, size: pack[entry.size] }));
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}

export function packFilter(id) {
  return isPackId(id) ? `packId = "${id}"` : null;
}

export function packsFilter(ids) {
  return ids.filter(isPackId).map(packFilter).join(' || ');
}

// Pairs each pack a level requires with what the gallery hosts under that id.
export function hostedPacks(required, hosted) {
  return Object.entries(required ?? {})
    .map(([id, version]) => {
      const versions = hosted
        .filter((record) => record.packId === id)
        .sort((a, b) => String(b.created).localeCompare(String(a.created)));
      const exact = versions.find((record) => record.version === String(version));
      const shown = exact ?? versions[0];
      return {
        id,
        version: String(version),
        hosted: Boolean(shown),
        mismatch: Boolean(shown) && !exact,
        ...(shown ? { hostedVersion: shown.version } : {}),
      };
    })
    .sort((a, b) => a.id.localeCompare(b.id));
}

export function packFormData({ packId, description, attested }, files) {
  const form = new FormData();
  form.set('packId', packId);
  form.set('description', description);
  form.set('attested', String(Boolean(attested)));
  for (const [field, file] of Object.entries(files)) {
    if (file) form.set(field, file);
  }
  return form;
}

export function packUploadTooLarge(files) {
  const total = files.reduce((sum, file) => sum + (file?.size ?? 0), 0);
  return total > MAX_PACK_BYTES
    ? `A pack can be at most 30 MiB in total; these files add up to ${formatBytes(total)}.`
    : '';
}
