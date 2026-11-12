import assert from 'node:assert/strict';
import test from 'node:test';
import { devSession } from '../src/scripts/dev-session.js';

function fakeAuthStore() {
  return {
    token: '',
    record: null,
    get isValid() {
      return Boolean(this.token);
    },
    save(token, record) {
      this.token = token;
      this.record = record;
    },
    clear() {
      this.token = '';
      this.record = null;
    },
  };
}

function fakeStorage() {
  const data = new Map();
  return {
    getItem: (key) => data.get(key) ?? null,
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

function setup({ users = [{ id: 'u1', name: 'Alice', email: 'a@dev.test' }] } = {}) {
  const calls = [];
  const pb = { authStore: fakeAuthStore() };
  const newClient = () => {
    const client = {
      authStore: fakeAuthStore(),
      collection: (name) => ({
        async authWithPassword(identity, password) {
          calls.push(['auth', name, identity, password]);
          client.authStore.save('su-token', { id: 'su' });
        },
        getFullList: async () => users,
        impersonate: async (id) => {
          calls.push(['impersonate', id, client.authStore.token]);
          const target = { authStore: fakeAuthStore() };
          target.authStore.save(`token-${id}`, { id, collectionName: 'users' });
          return target;
        },
      }),
    };
    return client;
  };
  const storage = fakeStorage();
  const session = devSession({
    pb,
    newClient,
    credentials: { identity: 'dev@dev.test', password: 'pw' },
    defaultEmail: 'a@dev.test',
    storage,
  });
  return { pb, session, calls, storage };
}

test('the superuser signs in once, lazily, on a private client', async () => {
  const { pb, session, calls } = setup();
  assert.equal(calls.length, 0);
  await session.loadUsers();
  await session.loadUsers();
  assert.equal(calls.filter(([kind]) => kind === 'auth').length, 1);
  assert.deepEqual(calls[0], ['auth', '_superusers', 'dev@dev.test', 'pw']);
  assert.equal(pb.authStore.record, null);
});

test('loadUsers lists the accounts', async () => {
  const { session } = setup();
  await session.loadUsers();
  assert.deepEqual(session.users, [{ id: 'u1', name: 'Alice', email: 'a@dev.test' }]);
});

test('switchUser signs the page in as the user with the superuser token', async () => {
  const { pb, session, calls } = setup();
  await session.switchUser('u1');
  assert.deepEqual(calls.at(-1), ['impersonate', 'u1', 'su-token']);
  assert.equal(pb.authStore.token, 'token-u1');
  assert.equal(pb.authStore.record.id, 'u1');
});

test('switchUser with no id signs the page out', async () => {
  const { pb, session } = setup();
  await session.switchUser('u1');
  await session.switchUser(null);
  assert.equal(pb.authStore.record, null);
});

test('a failed user switch sets devError and leaves the session alone', async () => {
  const { pb, session } = setup();
  pb.authStore.save('keep', { id: 'keep' });
  session.devError = '';
  const broken = devSession({
    pb,
    newClient: () => ({
      authStore: fakeAuthStore(),
      collection: () => ({
        authWithPassword: async () => {
          throw new Error('down');
        },
      }),
    }),
    credentials: { identity: 'x', password: 'y' },
  });
  await broken.switchUser('u1');
  assert.match(broken.devError, /down/);
  assert.equal(pb.authStore.token, 'keep');
});

test('signInDefault signs in as the default user when nobody is signed in', async () => {
  const { pb, session } = setup();
  await session.signInDefault();
  assert.equal(pb.authStore.record.id, 'u1');
});

test('signInDefault leaves an existing session alone', async () => {
  const { pb, session, calls } = setup();
  pb.authStore.save('keep', { id: 'keep' });
  await session.signInDefault();
  assert.equal(pb.authStore.token, 'keep');
  assert.equal(calls.length, 0);
});

test('choosing anonymous stops the default sign-in until another user is chosen', async () => {
  const { pb, session } = setup();
  await session.switchUser(null);
  await session.signInDefault();
  assert.equal(pb.authStore.record, null);
  await session.switchUser('u1');
  pb.authStore.clear();
  await session.signInDefault();
  assert.equal(pb.authStore.record.id, 'u1');
});

test('signInDefault does nothing when no account has the default email', async () => {
  const { pb, session } = setup({ users: [{ id: 'u2', email: 'other@dev.test' }] });
  await session.signInDefault();
  assert.equal(pb.authStore.record, null);
});

test('loadUsers puts the default user first and keeps the rest in order', async () => {
  const ordered = devSession({
    pb: { authStore: fakeAuthStore() },
    newClient: () => ({
      authStore: fakeAuthStore(),
      collection: () => ({
        authWithPassword: async () => {},
        getFullList: async () => [
          { id: 'u1', email: 'a@dev.test' },
          { id: 'u2', email: 'b@dev.test' },
          { id: 'u3', email: 'c@dev.test' },
        ],
      }),
    }),
    credentials: { identity: 'x', password: 'y' },
    defaultEmail: 'b@dev.test',
    storage: fakeStorage(),
  });
  await ordered.loadUsers();
  assert.deepEqual(ordered.users.map((user) => user.id), ['u2', 'u1', 'u3']);
});
