import { coverUrl, mapName, pbErrorMessages, plural, relativeDate } from './gallery.js';
import { TAGS } from './levels.js';
import { pb, PB_URL } from './pb.js';

export default () => ({
  tags: TAGS,
  mine: [],
  mineState: 'idle',
  editing: null,
  description: '',
  chosen: [],
  errors: [],
  busy: false,
  confirmDelete: null,

  async init() {
    await this.loadMine();
    this.$watch('$store.session.user', () => {
      this.resetForm();
      return this.loadMine();
    });
  },

  async loadMine() {
    const user = pb.authStore.record;
    if (!user) {
      this.mine = [];
      this.mineState = 'idle';
      return;
    }
    this.mineState = 'loading';
    try {
      const result = await pb.collection('levels').getList(1, 50, {
        filter: pb.filter('author = {:id}', { id: user.id }),
        sort: '-created',
      });
      this.mine = result.items;
      this.mineState = 'ready';
    } catch (error) {
      this.errors = pbErrorMessages(error);
      this.mineState = 'error';
    }
  },

  resetForm() {
    this.editing = null;
    this.description = '';
    this.chosen = [];
    this.errors = [];
    this.$refs.form?.reset();
  },

  edit(level) {
    this.editing = level;
    this.description = level.description ?? '';
    this.chosen = [...(level.tags ?? [])];
    this.errors = [];
    this.$refs.heading.scrollIntoView();
    this.$refs.heading.focus();
  },

  async submit() {
    this.errors = [];
    const form = new FormData();
    form.set('description', this.description);
    if (this.chosen.length === 0) form.set('tags', '');
    for (const tag of this.chosen) form.append('tags', tag);
    for (const field of ['level', 'cover', 'biome']) {
      const file = this.$refs[field].files[0];
      if (file) form.set(field, file);
    }
    this.busy = true;
    try {
      const collection = pb.collection('levels');
      if (this.editing) {
        await collection.update(this.editing.id, form);
        this.resetForm();
        await this.loadMine();
      } else {
        const created = await collection.create(form);
        location.assign(`/l/${created.code}`);
      }
    } catch (error) {
      this.errors = pbErrorMessages(error);
    } finally {
      this.busy = false;
    }
  },

  askDelete(level) {
    this.confirmDelete = level.id;
    this.$nextTick(() => this.$root.querySelector(`[data-cancel="${level.id}"]`)?.focus());
  },

  cancelDelete(level) {
    this.confirmDelete = null;
    setTimeout(() => this.$root.querySelector(`[data-delete="${level.id}"]`)?.focus(), 0);
  },

  async remove(level) {
    try {
      await pb.collection('levels').delete(level.id);
      this.confirmDelete = null;
      if (this.editing?.id === level.id) this.resetForm();
      await this.loadMine();
    } catch (error) {
      this.errors = pbErrorMessages(error);
    }
  },

  cover: (level) => coverUrl(PB_URL, level, '320x0'),
  plural,
  relativeDate,
  mapName,
});
