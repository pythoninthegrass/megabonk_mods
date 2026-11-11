import {
  coverUrl,
  editCodeFromSearch,
  editFormState,
  levelFormData,
  mapName,
  pbErrorMessages,
  plural,
  relativeDate,
} from './gallery.js';
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
  pendingEdit: null,

  async init() {
    this.$store.session.loadProviders();
    this.pendingEdit = editCodeFromSearch(location.search);
    await this.loadMine();
    this.openRequestedEdit();
    this.$watch('$store.session.user', async () => {
      this.resetForm();
      await this.loadMine();
      this.openRequestedEdit();
    });
  },

  openRequestedEdit() {
    if (!this.pendingEdit || this.mineState !== 'ready') return;
    const level = this.mine.find((item) => item.code === this.pendingEdit);
    if (level) {
      this.edit(level);
    } else {
      this.errors = [
        `No level ${this.pendingEdit} was found in your account, so it cannot be edited here.`,
      ];
    }
    this.pendingEdit = null;
    const url = new URL(location.href);
    url.searchParams.delete('edit');
    history.replaceState(null, '', url);
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
    Object.assign(this, editFormState(level));
    this.errors = [];
    this.$refs.heading.scrollIntoView();
    this.$refs.heading.focus();
  },

  async submit() {
    this.errors = [];
    const form = levelFormData(this, {
      level: this.$refs.level.files[0],
      cover: this.$refs.cover.files[0],
      biome: this.$refs.biome.files[0],
    });
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
