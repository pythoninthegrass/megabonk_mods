import Alpine from 'alpinejs';
import { pbErrorMessages } from './gallery.js';
import { pb } from './pb.js';

const PROVIDERS = [
  { id: 'github', label: 'GitHub' },
  { id: 'google', label: 'Google' },
  { id: 'discord', label: 'Discord' },
];

function sessionStore() {
  return {
    providers: PROVIDERS,
    user: pb.authStore.record,
    busy: false,
    error: '',
    get signedIn() {
      return Boolean(this.user);
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

export function startGallery(components) {
  Alpine.store('session', sessionStore());
  pb.authStore.onChange(() => {
    Alpine.store('session').user = pb.authStore.record;
  });
  for (const [name, component] of Object.entries(components)) Alpine.data(name, component);
  Alpine.start();
}
