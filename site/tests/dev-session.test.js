import assert from 'node:assert/strict';
import test from 'node:test';
import { devSession } from '../src/scripts/dev-session.js';

function fakeAuthStore() {
  return {
    token: '',
    record: null,
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

function setup({ users = [{ id: 'u1', name: 'Alice' }], failDelete = false } = {}) {
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
        delete: async (id) => {
          calls.push(['delete', name, id, client.authStore.token]);
          if (failDelete) throw new Error('nope');
        },
      }),
    };
    return client;
  };
  const session = devSession({
    pb,
    newClient,
    credentials: { identity: 'dev@dev.test', password: 'pw' },
  });
  return { pb, session, calls };
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
  assert.deepEqual(session.users, [{ id: 'u1', name: 'Alice' }]);
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

test('adminDelete removes the level with the superuser token', async () => {
  const { session, calls } = setup();
  assert.equal(await session.adminDelete({ id: 'l1' }), true);
  assert.deepEqual(calls.at(-1), ['delete', 'levels', 'l1', 'su-token']);
});

test('a failed delete reports false and sets devError', async () => {
  const { session } = setup({ failDelete: true });
  assert.equal(await session.adminDelete({ id: 'l1' }), false);
  assert.match(session.devError, /nope/);
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
