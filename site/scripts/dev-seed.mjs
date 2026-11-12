export const SEED_MAKERS = [
  { email: 'alice@dev.test', name: 'Alice', levels: 14 },
  { email: 'bob@dev.test', name: '', levels: 3 },
  { email: 'carol@dev.test', name: 'Carol', levels: 0 },
];

// Every level the dev API should hold; the first one is hidden to exercise the public filter.
export function seedLevels() {
  return SEED_MAKERS.flatMap(({ email, name, levels }) =>
    Array.from({ length: levels }, (_, index) => ({
      maker: email,
      title: `${name || 'Nameless'} level ${index + 1}`,
      hidden: email === SEED_MAKERS[0].email && index === 0,
    }))
  );
}

const SIGN_IN_PREFIX = '/__dev/signin/';

const slug = (maker) => maker.email.split('@')[0];

export function signInPath(maker) {
  return `${SIGN_IN_PREFIX}${slug(maker)}`;
}

export function makerFromSignInPath(pathname) {
  if (!pathname.startsWith(SIGN_IN_PREFIX)) return undefined;
  return SEED_MAKERS.find((maker) => slug(maker) === pathname.slice(SIGN_IN_PREFIX.length));
}

// Page that stores only the session fields the gallery pages read, then redirects.
export function signInPage({ token, record }, next) {
  const session = JSON.stringify({
    token,
    record: { id: record.id, name: record.name, collectionName: 'users' },
  }).replaceAll('<', '\\u003c');
  return `<!doctype html><meta charset="utf-8"><title>Signing in</title><script>localStorage.setItem('pocketbase_auth', JSON.stringify(${session}));location.replace(${
    JSON.stringify(next)
  });</script>`;
}
