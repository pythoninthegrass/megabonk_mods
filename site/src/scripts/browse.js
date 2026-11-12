import {
  codeFromSearch,
  coverUrl,
  creatorUrl,
  downloadUrl,
  editUrl,
  excerpt,
  isOwner,
  likesFilter,
  likeTitle,
  pbErrorMessages,
  plural,
  relativeDate,
} from './gallery.js';
import { buildFilter, sortParam, TAGS } from './levels.js';
import { pb, PB_URL } from './pb.js';

const PER_PAGE = 12;
const SORTS = [
  ['newest', 'Newest'],
  ['liked', 'Most liked'],
  ['downloads', 'Most downloaded'],
];

export default () => ({
  tags: TAGS,
  sorts: SORTS,
  search: '',
  tag: '',
  sort: 'newest',
  page: 1,
  totalPages: 1,
  totalItems: 0,
  items: [],
  state: 'loading',
  message: '',
  timer: null,
  likes: {},
  busyLikes: {},
  notice: '',

  async init() {
    const params = new URLSearchParams(location.search);
    this.search = params.get('q') ?? '';
    this.tag = TAGS.includes(params.get('tag')) ? params.get('tag') : '';
    this.sort = SORTS.some(([key]) => key === params.get('sort')) ? params.get('sort') : 'newest';
    this.page = Math.max(1, Number.parseInt(params.get('page'), 10) || 1);
    this.$watch('$store.session.user', () => this.loadLikes());
    await this.load();
  },

  queueSearch() {
    clearTimeout(this.timer);
    this.timer = setTimeout(() => this.refilter(), 300);
  },

  refilter() {
    clearTimeout(this.timer);
    const code = codeFromSearch(this.search);
    if (code) {
      location.assign(`/l/${code}`);
      return Promise.resolve();
    }
    this.page = 1;
    return this.load();
  },

  goTo(page) {
    this.page = page;
    return this.load().then(() => document.getElementById('results')?.scrollIntoView());
  },

  syncUrl() {
    const params = new URLSearchParams();
    if (this.search.trim()) params.set('q', this.search.trim());
    if (this.tag) params.set('tag', this.tag);
    if (this.sort !== 'newest') params.set('sort', this.sort);
    if (this.page > 1) params.set('page', String(this.page));
    const query = params.toString();
    history.replaceState(null, '', query ? `?${query}` : location.pathname);
  },

  async load() {
    this.state = 'loading';
    this.syncUrl();
    try {
      const result = await pb.collection('levels').getList(this.page, PER_PAGE, {
        filter: buildFilter({ search: this.search, tag: this.tag }),
        sort: sortParam(this.sort),
        expand: 'author',
      });
      this.items = result.items;
      this.totalPages = result.totalPages;
      this.totalItems = result.totalItems;
      this.state = result.items.length ? 'ready' : 'empty';
      await this.loadLikes();
    } catch (error) {
      this.items = [];
      this.message = error.status === 0 ? '' : pbErrorMessages(error).join(' ');
      this.state = 'error';
    }
  },

  async loadLikes() {
    this.likes = {};
    const filter = likesFilter(this.items.map((item) => item.id));
    if (!pb.authStore.isValid || !filter) return;
    try {
      const rows = await pb.collection('likes').getFullList({ filter });
      this.likes = Object.fromEntries(rows.map((row) => [row.level, row.id]));
    } catch {
      this.likes = {};
    }
  },

  async toggleLike(item) {
    if (!pb.authStore.isValid) {
      location.assign(`/l/${item.code}#social`);
      return;
    }
    if (this.busyLikes[item.id]) return;
    this.busyLikes[item.id] = true;
    this.notice = '';
    try {
      if (this.likes[item.id]) {
        await pb.collection('likes').delete(this.likes[item.id]);
        delete this.likes[item.id];
      } else {
        const like = await pb.collection('likes').create({
          user: pb.authStore.record.id,
          level: item.id,
        });
        this.likes[item.id] = like.id;
      }
      const fresh = await pb.collection('levels').getOne(item.id, { expand: 'author' });
      this.items = this.items.map((entry) => (entry.id === item.id ? fresh : entry));
    } catch (error) {
      this.notice = pbErrorMessages(error).join(' ');
    } finally {
      delete this.busyLikes[item.id];
    }
  },

  likeTitle(item) {
    return likeTitle(pb.authStore.isValid, Boolean(this.likes[item.id]));
  },

  get filtered() {
    return Boolean(this.search.trim() || this.tag);
  },

  clearFilters() {
    this.search = '';
    this.tag = '';
    return this.refilter();
  },

  creatorUrl,
  cover: (item, thumb) => coverUrl(PB_URL, item, thumb),
  downloadHref: (code) => downloadUrl(PB_URL, code),
  editUrl,
  excerpt,
  isOwner,
  plural,
  relativeDate,
  author: (item) => item.expand?.author?.name || 'Unknown maker',
});
