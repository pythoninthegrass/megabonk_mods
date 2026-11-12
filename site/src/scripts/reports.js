export const REPORT_CATEGORIES = [
  { id: 'copyright', label: 'Copyright: it uses work I own' },
  { id: 'broken', label: 'Broken or does not work' },
  { id: 'inappropriate', label: 'Inappropriate content' },
  { id: 'other', label: 'Something else' },
];

export const COPYRIGHT_GOOD_FAITH =
  'I have a good faith belief that this use is not authorized by the copyright owner, its agent, or the law.';
export const COPYRIGHT_PERJURY =
  "The information in this report is accurate and, under penalty of perjury, I am the owner of the work, or an agent authorized to act on the owner's behalf.";

const COPYRIGHT_FIELDS = [
  'contactEmail',
  'contactAddress',
  'contactPhone',
  'work',
  'itemUrl',
  'signature',
];
const COPYRIGHT_FLAGS = ['goodFaith', 'accurate', 'fairUseConsidered'];

export function itemLink(origin, target) {
  return target.level ? `${origin}/l/${target.level.code}` : `${origin}/p/${target.pack.packId}`;
}

export function reportPayload({ userId, target, category, reason, copyright = {} }) {
  const payload = {
    user: userId,
    ...(target.level ? { level: target.level.id } : { pack: target.pack.id }),
    category,
    reason: reason.trim(),
  };
  if (category !== 'copyright') return payload;
  for (const name of COPYRIGHT_FIELDS) payload[name] = String(copyright[name] ?? '').trim();
  for (const name of COPYRIGHT_FLAGS) payload[name] = Boolean(copyright[name]);
  return payload;
}
