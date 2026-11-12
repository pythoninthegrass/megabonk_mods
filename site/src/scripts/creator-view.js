import {
  coverUrl,
  CREATOR_FIELDS,
  creatorFilter,
  creatorIdFromPath,
  editUrl,
  isOwner,
  plural,
  sumCounts,
} from './gallery.js';
import { pb, PB_URL } from './pb.js';
import { cacheKey, readCached, writeCached } from './result-cache.js';

const PER_PAGE = 12;

export default () => ({
  id: null,
  creator: null,
  totals: { likes: 0, downloads: 0 },
  items: [],
  page: 1,
  totalPages: 1,
  totalItems: 0,
  state: 'loading',

  async init() {
    this.id = creatorIdFromPath(location.pathname);
    if (!this.id) {
      this.state = 'notfound';
      return;
    }
    this.page = Math.max(
      1,
      Number.parseInt(new URLSearchParams(location.search).get('page'), 10) || 1,
    );
    await this.load();
  },

  async deleteLevel(level) {
    if (await this.$store.session.deleteLevel(level)) await this.load();
  },

  applyResult({ creator, totals, items, totalPages, totalItems }) {
    this.creator = creator;
    this.totals = totals;
    this.items = items;
    this.totalPages = totalPages;
    this.totalItems = totalItems;
    document.title = `${this.name} · Megabonk Mod Party`;
    this.state = items.length ? 'ready' : 'empty';
  },

  async load() {
    const key = cacheKey('creator', pb.authStore.record, [this.id, this.page]);
    const cached = readCached(globalThis.sessionStorage, key);
    if (cached) this.applyResult(cached);
    else this.state = 'loading';
    const filter = creatorFilter(this.id);
    try {
      const creator = await pb.collection('users').getOne(this.id, { fields: CREATOR_FIELDS });
      const [rows, result] = await Promise.all([
        pb.collection('levels').getFullList({
          filter,
          fields: 'likes,downloads',
          requestKey: 'creator-totals',
        }),
        pb.collection('levels').getList(this.page, PER_PAGE, {
          filter,
          sort: '-created',
          requestKey: 'creator-levels',
        }),
      ]);
      const fresh = {
        creator,
        totals: sumCounts(rows),
        items: result.items,
        totalPages: result.totalPages,
        totalItems: result.totalItems,
      };
      writeCached(globalThis.sessionStorage, key, fresh);
      this.applyResult(fresh);
    } catch (error) {
      if (cached && error.status !== 404) return;
      this.state = error.status === 404 ? 'notfound' : 'error';
      return;
    }
    this.syncUrl();
  },

  syncUrl() {
    history.replaceState(null, '', this.page > 1 ? `?page=${this.page}` : location.pathname);
  },

  goTo(page) {
    this.page = page;
    return this.load().then(() => document.getElementById('results')?.scrollIntoView());
  },

  get name() {
    return this.creator?.name || 'Unknown maker';
  },
  get joined() {
    if (!this.creator) return '';
    const date = new Date(this.creator.created.replace(' ', 'T'));
    return date.toLocaleDateString(undefined, { dateStyle: 'medium' });
  },
  get showHeader() {
    return this.state === 'ready' || this.state === 'empty';
  },

  cover: (item, thumb) => coverUrl(PB_URL, item, thumb),
  editUrl,
  isOwner,
  plural,
});
