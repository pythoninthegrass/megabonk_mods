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

// One-line console snippet carrying only the session fields the pages read.
export function signInSnippet({ token, record }) {
  const session = {
    token,
    record: { id: record.id, name: record.name, collectionName: 'users' },
  };
  return `localStorage.setItem('pocketbase_auth',JSON.stringify(${JSON.stringify(session)}))`;
}
