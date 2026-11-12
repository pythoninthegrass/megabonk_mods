import { execFileSync, spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { deflateSync } from 'node:zlib';
import { fileURLToPath } from 'node:url';
import { SEED_MAKERS, seedLevels, signInPath } from './dev-seed.mjs';

const API = 'http://127.0.0.1:8090';
const REPO = fileURLToPath(new URL('../../', import.meta.url));
const DATA_DIR = `${REPO}pocketbase/pb_data_dev`;
const ADMIN = { identity: 'dev@dev.test', password: 'dev-password-not-a-secret' };
const POCKETBASE_VERSION = '0.40.6';

function findPocketbase() {
  if (process.env.POCKETBASE_BIN) return process.env.POCKETBASE_BIN;
  try {
    const mise = `${process.env.HOME}/.local/bin/mise`;
    const dir = execFileSync(
      mise,
      ['where', `github:pocketbase/pocketbase@${POCKETBASE_VERSION}`],
      {
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      },
    ).trim();
    return existsSync(`${dir}/pocketbase`) ? `${dir}/pocketbase` : null;
  } catch {
    return null;
  }
}

async function healthy() {
  try {
    return (await fetch(`${API}/api/health`)).ok;
  } catch {
    return false;
  }
}

async function request(path, token, init = {}) {
  const headers = { ...init.headers, ...(token ? { authorization: token } : {}) };
  const response = await fetch(`${API}${path}`, { ...init, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(`${init.method ?? 'GET'} ${path}: ${response.status} ${body.message ?? ''}`);
  }
  return body;
}

const json = (method, body) => ({
  method,
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify(body),
});

function coverPng() {
  const [width, height] = [120, 80];
  const row = Buffer.concat([Buffer.from([0]), Buffer.alloc(width * 3, 0)]);
  for (let x = 0; x < width; x++) row.set([200, 120, 40], 1 + x * 3);
  const crc = (buffer) => {
    let c = ~0;
    for (const byte of buffer) {
      c ^= byte;
      for (let k = 0; k < 8; k++) c = c & 1 ? (c >>> 1) ^ 0xedb88320 : c >>> 1;
    }
    return ~c >>> 0;
  };
  const chunk = (type, data) => {
    const body = Buffer.concat([Buffer.from(type), data]);
    const out = Buffer.alloc(body.length + 8);
    out.writeUInt32BE(data.length, 0);
    body.copy(out, 4);
    out.writeUInt32BE(crc(body), body.length + 4);
    return out;
  };
  const header = Buffer.alloc(13);
  header.writeUInt32BE(width, 0);
  header.writeUInt32BE(height, 4);
  header.set([8, 2, 0, 0, 0], 8);
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk('IHDR', header),
    chunk('IDAT', deflateSync(Buffer.concat(Array(height).fill(row)))),
    chunk('IEND', Buffer.alloc(0)),
  ]);
}

async function seed() {
  const { token: admin } = await request(
    '/api/collections/_superusers/auth-with-password',
    null,
    json('POST', ADMIN),
  );
  await request('/api/settings', admin, json('PATCH', { rateLimits: { enabled: false } }));
  const users = new Map();
  for (const { email, name } of SEED_MAKERS) {
    const filter = encodeURIComponent(`email = "${email}"`);
    let [user] = (await request(`/api/collections/users/records?filter=${filter}`, admin)).items;
    user ??= await request(
      '/api/collections/users/records',
      admin,
      json('POST', {
        email,
        name,
        password: 'dev-password-not-a-secret',
        passwordConfirm: 'dev-password-not-a-secret',
      }),
    );
    const { token } = await request(
      `/api/collections/users/impersonate/${user.id}`,
      admin,
      json('POST', { duration: 86400 }),
    );
    users.set(email, { user, token });
  }
  const existing = new Set(
    (await request('/api/collections/levels/records?perPage=500&fields=title', admin)).items.map((
      level,
    ) => level.title),
  );
  const cover = coverPng();
  for (const level of seedLevels().filter((entry) => !existing.has(entry.title))) {
    const form = new FormData();
    form.set('title', level.title);
    form.set(
      'level',
      new Blob([JSON.stringify({ schemaVersion: 1, title: level.title })], {
        type: 'application/json',
      }),
      'level.json',
    );
    form.set('cover', new Blob([cover], { type: 'image/png' }), 'cover.png');
    const created = await request('/api/collections/levels/records', users.get(level.maker).token, {
      method: 'POST',
      body: form,
    });
    if (level.hidden) {
      await request(
        `/api/collections/levels/records/${created.id}`,
        admin,
        json('PATCH', { hidden: true }),
      );
    }
  }
  console.log('\nDev API seeded. Sign in as a maker by opening the path on the dev server:');
  for (const maker of SEED_MAKERS) {
    const { user } = users.get(maker.email);
    console.log(`  ${(maker.name || 'Nameless').padEnd(8)} ${signInPath(maker)}  (/u/${user.id})`);
  }
  console.log();
}

// A session for a seeded maker, for the dev server's sign-in route.
export async function devSession(maker) {
  const { token: admin } = await request(
    '/api/collections/_superusers/auth-with-password',
    null,
    json('POST', ADMIN),
  );
  const filter = encodeURIComponent(`email = "${maker.email}"`);
  const [user] = (await request(`/api/collections/users/records?filter=${filter}`, admin)).items;
  const { token } = await request(
    `/api/collections/users/impersonate/${user.id}`,
    admin,
    json('POST', { duration: 86400 }),
  );
  return { token, record: user };
}

// Starts a local API for the gallery pages and returns a function that stops it.
export async function startDevApi() {
  if (await healthy()) {
    console.log(`Dev API: reusing the server already listening on ${API}; seeding skipped.`);
    return () => {};
  }
  const binary = findPocketbase();
  if (!binary) {
    console.warn(
      'Dev API: PocketBase not found. Run `task pocketbase:install` or set POCKETBASE_BIN; the gallery pages will show the unreachable state.',
    );
    return () => {};
  }
  execFileSync(
    binary,
    ['superuser', 'upsert', ADMIN.identity, ADMIN.password, `--dir=${DATA_DIR}`],
    { stdio: 'ignore' },
  );
  const child = spawn('sh', [`${REPO}pocketbase/entrypoint.sh`], {
    stdio: 'ignore',
    env: {
      ...process.env,
      PB_BIN: binary,
      PB_HTTP: '127.0.0.1:8090',
      PB_DATA_DIR: DATA_DIR,
      PB_HOOKS_DIR: `${REPO}pocketbase/pb_hooks`,
      PB_MIGRATIONS_DIR: `${REPO}pocketbase/pb_migrations`,
    },
  });
  const stop = () => child.kill('SIGTERM');
  for (let attempt = 0; attempt < 50 && !(await healthy()); attempt++) {
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  if (!(await healthy())) {
    stop();
    console.warn('Dev API: PocketBase did not become healthy; continuing without it.');
    return () => {};
  }
  try {
    await seed();
  } catch (error) {
    console.warn(`Dev API: seeding failed: ${error.message}`);
  }
  return stop;
}
