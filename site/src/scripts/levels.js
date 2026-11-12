export const TAGS = ['Speedrun', 'Platforming', 'Survival', 'Puzzle', 'Showcase', 'Short'];

export const SORT_OPTIONS = [
  ['newest', 'Newest'],
  ['liked', 'Most liked'],
  ['downloads', 'Most downloaded'],
];

const CODE_PATTERN = /^[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}$/;
const SORTS = {
  newest: '-created',
  liked: '-likes,-created',
  downloads: '-downloads,-created',
};

export function isShareCode(value) {
  return typeof value === 'string' && CODE_PATTERN.test(value);
}

export function formatCode(raw) {
  if (typeof raw !== 'string' || raw.length !== 9) return null;
  const upper = raw.toUpperCase();
  const code = `${upper.slice(0, 3)}-${upper.slice(3, 6)}-${upper.slice(6)}`;
  return isShareCode(code) ? code : null;
}

export function normalizeCode(input) {
  if (typeof input !== 'string') return null;
  const compact = input.replace(/[\s-]/g, '').toUpperCase().replace(/O/g, '0').replace(
    /[IL]/g,
    '1',
  );
  return formatCode(compact);
}

export function slugify(title) {
  const slug = String(title ?? '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(
    /^-+|-+$/g,
    '',
  );
  return slug || 'level';
}

function quote(value) {
  return `'${value.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`;
}

export function buildFilter({ search = '', tag = '' } = {}) {
  const parts = [];
  const term = search.trim();
  if (term) parts.push(`(title ~ ${quote(term)} || description ~ ${quote(term)})`);
  if (TAGS.includes(tag)) parts.push(`tags ~ ${quote(tag)}`);
  return parts.join(' && ');
}

export function sortParam(sort) {
  return SORTS[sort] ?? SORTS.newest;
}

export function packList(packs) {
  if (!packs || typeof packs !== 'object' || Array.isArray(packs)) return [];
  return Object.entries(packs)
    .map(([id, version]) => ({ id, version: String(version) }))
    .sort((a, b) => a.id.localeCompare(b.id));
}
