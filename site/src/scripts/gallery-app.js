import Alpine from 'alpinejs';
import { availableProviders, isAdmin, pbErrorMessages } from './gallery.js';
import { moderation } from './moderation.js';
import { pb, PB_URL } from './pb.js';

const KNOWN_PROVIDERS = [
  { id: 'github', label: 'GitHub' },
  { id: 'google', label: 'Google' },
  { id: 'discord', label: 'Discord' },
];

function sessionStore() {
  return {
    providers: [],
    providersState: 'idle',
    user: pb.authStore.record,
    busy: false,
    error: '',
    async loadProviders() {
      if (this.providersState !== 'idle') return;
      this.providersState = 'loading';
      try {
        this.providers = availableProviders(
          await pb.collection('users').listAuthMethods(),
          KNOWN_PROVIDERS,
        );
        this.providersState = 'ready';
      } catch {
        this.providersState = 'error';
      }
    },
    get signInUnavailable() {
      return this.providersState === 'ready' && this.providers.length === 0;
    },
    get oauthEnabled() {
      return !import.meta.env.DEV;
    },
    get isAdmin() {
      return isAdmin(this.user);
    },
    get signedIn() {
      return Boolean(this.user) && this.user.collectionName !== '_superusers';
    },
    async signIn(provider) {
      this.busy = true;
      this.error = '';
      try {
        await pb.collection('users').authWithOAuth2({ provider });
      } catch (error) {
        this.error = pbErrorMessages(error).join(' ');
      } finally {
        this.busy = false;
      }
    },
    signOut() {
      pb.authStore.clear();
    },
  };
}

async function withDevSession(store) {
  const [
    { devSession },
    { DEV_ADMIN_EMAILS, DEV_SUPERUSER },
    { default: PocketBase, BaseAuthStore },
  ] = await Promise
    .all([
      import('./dev-session.js'),
      import('../../scripts/dev-seed.mjs'),
      import('pocketbase'),
    ]);
  Object.assign(
    store,
    devSession({
      pb,
      newClient: () => new PocketBase(PB_URL, new BaseAuthStore()),
      credentials: DEV_SUPERUSER,
      defaultEmail: DEV_ADMIN_EMAILS,
    }),
  );
}

export async function startGallery(components) {
  const store = Object.assign(sessionStore(), moderation({ pb }));
  if (import.meta.env.DEV) await withDevSession(store);
  Alpine.store('session', store);
  pb.authStore.onChange(() => {
    Alpine.store('session').user = pb.authStore.record;
  });
  if (import.meta.env.DEV) await store.signInDefault();
  for (const [name, component] of Object.entries(components)) Alpine.data(name, component);
  Alpine.start();
}
