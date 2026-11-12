const IMPERSONATION_SECONDS = 86400;

// Dev-only user switching and admin actions, merged into the session store; the superuser stays on a private client.
export function devSession({ pb, newClient, credentials }) {
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
        this.users = await admin
          .collection('users')
          .getFullList({ sort: 'email', fields: 'id,name,email' });
      } catch (error) {
        this.devError = `Could not list users: ${error.message}`;
      }
    },

    async switchUser(id) {
      this.devError = '';
      if (!id) {
        pb.authStore.clear();
        return;
      }
      try {
        const admin = await superuserClient();
        const client = await admin.collection('users').impersonate(id, IMPERSONATION_SECONDS);
        pb.authStore.save(client.authStore.token, client.authStore.record);
      } catch (error) {
        this.devError = `Could not sign in as that user: ${error.message}`;
      }
    },

    async adminDelete(level) {
      this.devError = '';
      try {
        const admin = await superuserClient();
        await admin.collection('levels').delete(level.id);
        return true;
      } catch (error) {
        this.devError = `Could not delete the level: ${error.message}`;
        return false;
      }
    },
  };
}
