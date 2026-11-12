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
    'data-strict': '1',
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

export function availableProviders(methods, known) {
  const oauth = methods?.oauth2;
  if (!oauth?.enabled || !Array.isArray(oauth.providers)) return [];
  const configured = new Set(oauth.providers.map((provider) => provider.name));
  return known.filter((provider) => configured.has(provider.id));
}

export function editUrl(code) {
  return isShareCode(code) ? `/levels/upload/?edit=${code}` : null;
}

export function levelUrl(code) {
  return isShareCode(code) ? `/l/${code}` : null;
}

export function editCodeFromSearch(search) {
  return codeFromSearch(new URLSearchParams(search ?? '').get('edit'));
}

export function isOwner(user, level) {
  return Boolean(user?.id) && user.id === level?.author;
}

export function isAdmin(user) {
  return Boolean(user?.admin);
}

export function withAccess(ids, id, add) {
  const current = ids ?? [];
  if (!id) return current;
  return add ? [...new Set([...current, id])] : current.filter((entry) => entry !== id);
}

export function editFormState(level) {
  return { description: level?.description ?? '', chosen: [...(level?.tags ?? [])] };
}

export function levelFormData({ description, chosen }, files) {
  const form = new FormData();
  form.set('description', description);
  if (chosen.length === 0) form.set('tags', '');
  for (const tag of chosen) form.append('tags', tag);
  for (const [field, file] of Object.entries(files)) {
    if (file) form.set(field, file);
  }
  return form;
}

export function likesFilter(levelIds) {
  return levelIds
    .filter((id) => typeof id === 'string' && /^[a-z0-9]{15}$/.test(id))
    .map((id) => `level = "${id}"`)
    .join(' || ');
}

export function likeTitle(signedIn, liked) {
  if (!signedIn) return 'Sign in to like this level';
  return liked ? 'Remove your like' : 'Like this level';
}

export const CREATOR_FIELDS = 'id,name,created';

const CREATOR_ID = /^[a-z0-9]{15}$/;

export function creatorIdFromPath(pathname) {
  const match = /^\/u\/([^/]+)\/?$/.exec(String(pathname ?? ''));
  return match && CREATOR_ID.test(match[1]) ? match[1] : null;
}

export function creatorUrl(id) {
  return typeof id === 'string' && CREATOR_ID.test(id) ? `/u/${id}` : null;
}

export function creatorFilter(id) {
  return typeof id === 'string' && CREATOR_ID.test(id) ? `author = "${id}"` : null;
}

export function sumCounts(rows) {
  return rows.reduce(
    (total, row) => ({
      likes: total.likes + (row.likes ?? 0),
      downloads: total.downloads + (row.downloads ?? 0),
    }),
    { likes: 0, downloads: 0 },
  );
}
