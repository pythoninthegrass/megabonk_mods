import { pbErrorMessages } from './gallery.js';

// Site-owner actions on levels; the API rules decide who may actually run them.
export function moderation({ pb, confirm = (message) => globalThis.confirm(message) }) {
  return {
    adminError: '',

    async attempt(action) {
      try {
        await action();
        this.adminError = '';
        return true;
      } catch (error) {
        this.adminError = pbErrorMessages(error).join(' ');
        return false;
      }
    },

    async deleteLevel(level) {
      if (
        !confirm(`Delete "${level.title}"? This removes it, its likes and its reports for good.`)
      ) {
        return false;
      }
      return this.attempt(() => pb.collection('levels').delete(level.id));
    },

    setHidden(level, hidden) {
      return this.attempt(() => pb.collection('levels').update(level.id, { hidden }));
    },

    async toggleHidden(level) {
      const ok = await this.setHidden(level, !level.hidden);
      if (ok) level.hidden = !level.hidden;
      return ok;
    },

    setAccess(level, { viewers, blocked }) {
      return this.attempt(() => pb.collection('levels').update(level.id, { viewers, blocked }));
    },
  };
}
