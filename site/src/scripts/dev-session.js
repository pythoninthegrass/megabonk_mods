const IMPERSONATION_SECONDS = 86400;
const ANONYMOUS_KEY = 'devAnonymous';

// Dev-only user switching, merged into the session store; the superuser stays on a private client.
export function devSession(
  { pb, newClient, credentials, defaultEmail, storage = globalThis.localStorage },
) {
  let superuser = null;
  const superuserClient = async () => {
    if (!superuser) {
      const client = newClient();
      await client.collection('_superusers').authWithPassword(
        credentials.identity,
        credentials.password,
      );
      superuser = client;
    }
    return superuser;
  };

  return {
    users: [],
    devError: '',

    async loadUsers() {
      try {
        const admin = await superuserClient();
        const users = await admin
          .collection('users')
          .getFullList({ sort: 'email', fields: 'id,name,email' });
        const isDefault = (user) => user.email === defaultEmail;
        this.users = [...users.filter(isDefault), ...users.filter((user) => !isDefault(user))];
      } catch (error) {
        this.devError = `Could not list users: ${error.message}`;
      }
    },

    // Signs in as the default user unless a session exists or anonymous was chosen on purpose.
    async signInDefault() {
      if (pb.authStore.isValid || storage?.getItem(ANONYMOUS_KEY)) return;
      await this.loadUsers();
      const user = this.users.find((entry) => entry.email === defaultEmail);
      if (user) await this.switchUser(user.id);
    },

    async switchUser(id) {
      this.devError = '';
      if (!id) {
        storage?.setItem(ANONYMOUS_KEY, '1');
        pb.authStore.clear();
        return;
      }
      storage?.removeItem(ANONYMOUS_KEY);
      try {
        const admin = await superuserClient();
        const client = await admin.collection('users').impersonate(id, IMPERSONATION_SECONDS);
        pb.authStore.save(client.authStore.token, client.authStore.record);
      } catch (error) {
        this.devError = `Could not sign in as that user: ${error.message}`;
      }
    },
  };
}
