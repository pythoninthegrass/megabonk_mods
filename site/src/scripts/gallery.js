import { isShareCode } from './levels.js';

const UNITS = [
  ['year', 365 * 24 * 60 * 60 * 1000],
  ['month', 30 * 24 * 60 * 60 * 1000],
  ['day', 24 * 60 * 60 * 1000],
  ['hour', 60 * 60 * 1000],
  ['minute', 60 * 1000],
];

export function relativeDate(stamp, now = Date.now()) {
  const time = Date.parse(String(stamp ?? '').replace(' ', 'T'));
  if (Number.isNaN(time)) return '';
  const age = Math.max(0, now - time);
  for (const [unit, size] of UNITS) {
    const count = Math.floor(age / size);
    if (count >= 1) return `${count} ${unit}${count === 1 ? '' : 's'} ago`;
  }
  return 'just now';
}

export function excerpt(text, max = 140) {
  const flat = String(text ?? '').replace(/\s+/g, ' ').trim();
  if (flat.length <= max) return flat;
  const cut = flat.slice(0, max);
  const boundary = cut.lastIndexOf(' ');
  return `${(boundary > 0 ? cut.slice(0, boundary) : cut).trimEnd()}…`;
}

export function coverUrl(base, record, thumb = '') {
  if (!record?.cover) return null;
  const url = `${base}/api/files/levels/${record.id}/${record.cover}`;
  return thumb ? `${url}?thumb=${thumb}` : url;
}

export function downloadUrl(base, code) {
  return isShareCode(code) ? `${base}/api/l/${code}/download` : null;
}

export function codeFromPath(pathname) {
  const match = /^\/l\/([^/]+)\/?$/.exec(String(pathname ?? ''));
  return match && isShareCode(match[1]) ? match[1] : null;
}

export function pbErrorMessages(error) {
  if (error?.status === 0) return ['Could not reach the gallery server. Try again in a moment.'];
  const data = error?.response?.data;
  const fields = data && typeof data === 'object'
    ? Object.entries(data)
      .filter(([, detail]) => typeof detail?.message === 'string')
      .map(([field, detail]) => `${field}: ${detail.message}`)
    : [];
  if (fields.length) return fields;
  const message = error?.response?.message;
  return [message || 'Something went wrong. Try again.'];
}

export function giscusAttrs({ repo, repoId, category, categoryId } = {}, code) {
  if (!repo || !repoId || !category || !categoryId || !isShareCode(code)) return null;
  return {
    'data-repo': repo,
    'data-repo-id': repoId,
    'data-category': category,
    'data-category-id': categoryId,
    'data-mapping': 'specific',
    'data-term': code,
    'data-reactions-enabled': '1',
    'data-input-position': 'top',
    'data-theme': 'light',
    'data-lang': 'en',
  };
}

const MAP_NAMES = { 1: 'Forest', 2: 'Desert', 8: 'Graveyard', 16: 'Dungeon', 64: 'Hell' };

export function mapName(map) {
  if (!map) return 'Not set';
  return MAP_NAMES[map] ?? `Map ${map}`;
}

export function plural(count, noun) {
  const n = count ?? 0;
  return `${n} ${noun}${n === 1 ? '' : 's'}`;
}

export function codeFromSearch(text) {
  const code = String(text ?? '').trim().toUpperCase();
  return isShareCode(code) ? code : null;
}
