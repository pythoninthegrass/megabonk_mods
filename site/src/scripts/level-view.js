import {
  codeFromPath,
  coverUrl,
  creatorUrl,
  downloadUrl,
  editUrl,
  giscusAttrs,
  isOwner,
  likeTitle,
  mapName,
  pbErrorMessages,
  plural,
  relativeDate,
  withAccess,
} from './gallery.js';
import { packList } from './levels.js';
import { hostedPacks, packsFilter, packUrl } from './packs.js';
import { giscusConfig, pb, PB_URL } from './pb.js';
import { reportForm } from './report-form.js';

export default () => ({
  code: null,
  level: null,
  state: 'loading',
  liked: null,
  busy: false,
  copied: false,
  notice: '',
  hosted: null,
  users: [],
  ...reportForm(),
  accessGroups: [
    { field: 'viewers', title: 'Can see it while hidden' },
    { field: 'blocked', title: 'Cannot see it' },
  ],

  async init() {
    this.$store.session.loadProviders();
    this.code = codeFromPath(location.pathname);
    if (!this.code) {
      this.state = 'notfound';
      return;
    }
    if (!(await this.fetchLevel())) return;
    document.title = `${this.level.title} · Megabonk Mod Party`;
    await this.loadLike();
    this.loadHostedPacks();
    this.$watch('$store.session.user', () => {
      this.fetchLevel();
      this.loadLike();
    });
    this.mountComments();
  },

  async fetchLevel() {
    try {
      this.level = await pb.collection('levels').getFirstListItem(
        pb.filter('code = {:code}', { code: this.code }),
        { expand: 'author' },
      );
      this.state = 'ready';
      return true;
    } catch (error) {
      this.state = error.status === 404 ? 'notfound' : 'error';
      return false;
    }
  },

  async loadHostedPacks() {
    const ids = Object.keys(this.level.packs ?? {});
    if (!ids.length) return;
    try {
      const records = await pb.collection('packs').getFullList({
        filter: packsFilter(ids),
        fields: 'packId,version,created',
        sort: '-created',
      });
      this.hosted = hostedPacks(this.level.packs, records);
    } catch {
      this.hosted = null;
    }
  },

  async loadUsers() {
    if (this.users.length) return;
    try {
      this.users = await pb.collection('users').getFullList({ fields: 'id,name', sort: 'name' });
    } catch (error) {
      this.notice = pbErrorMessages(error).join(' ');
    }
  },

  userName(id) {
    return this.users.find((user) => user.id === id)?.name || id;
  },

  accessIds(field) {
    return this.level?.[field] ?? [];
  },

  accessCandidates(field) {
    const taken = this.accessIds(field);
    return this.users.filter((user) => !taken.includes(user.id));
  },

  async changeAccess(field, id, add) {
    const ids = withAccess(this.accessIds(field), id, add);
    const next = {
      viewers: this.accessIds('viewers'),
      blocked: this.accessIds('blocked'),
      [field]: ids,
    };
    if (await this.$store.session.setAccess(this.level, next)) this.level[field] = ids;
  },

  async deleteLevel(level) {
    if (await this.$store.session.deleteLevel(level)) location.assign('/levels/');
  },

  async loadLike() {
    this.liked = null;
    if (!pb.authStore.isValid) return;
    try {
      this.liked = await pb.collection('likes').getFirstListItem(
        pb.filter('level = {:id}', { id: this.level.id }),
      );
    } catch (error) {
      if (error.status !== 404) this.notice = pbErrorMessages(error).join(' ');
    }
  },

  async refreshCounts() {
    this.level = await pb.collection('levels').getOne(this.level.id, { expand: 'author' });
  },

  likeFromCounts() {
    if (!pb.authStore.isValid) {
      document.getElementById('social')?.scrollIntoView({ behavior: 'smooth' });
      return;
    }
    return this.toggleLike();
  },

  likeTitle() {
    return likeTitle(pb.authStore.isValid, Boolean(this.liked));
  },

  async toggleLike() {
    if (this.busy) return;
    this.busy = true;
    this.notice = '';
    try {
      if (this.liked) {
        await pb.collection('likes').delete(this.liked.id);
        this.liked = null;
      } else {
        this.liked = await pb.collection('likes').create({
          user: pb.authStore.record.id,
          level: this.level.id,
        });
      }
      await this.refreshCounts();
    } catch (error) {
      this.notice = pbErrorMessages(error).join(' ');
    } finally {
      this.busy = false;
    }
  },

  reportTarget() {
    return { level: this.level };
  },

  async copyCode() {
    try {
      await navigator.clipboard.writeText(this.code);
      this.copied = true;
      setTimeout(() => (this.copied = false), 2000);
    } catch {
      this.notice = `Copy this code by hand: ${this.code}`;
    }
  },

  mountComments() {
    const host = this.$refs.comments;
    const attrs = giscusAttrs(giscusConfig, this.code);
    if (!host || !attrs) return;
    const script = document.createElement('script');
    script.src = 'https://giscus.app/client.js';
    script.async = true;
    script.crossOrigin = 'anonymous';
    for (const [name, value] of Object.entries(attrs)) script.setAttribute(name, value);
    host.replaceChildren(script);
  },

  get commentsConfigured() {
    return giscusAttrs(giscusConfig, this.code) !== null;
  },

  get packs() {
    return this.hosted ??
      packList(this.level?.packs).map((pack) => ({ ...pack, hosted: false, mismatch: false }));
  },
  get anyHosted() {
    return this.packs.some((pack) => pack.hosted);
  },
  get anyUnhosted() {
    return this.packs.some((pack) => !pack.hosted);
  },
  get download() {
    return downloadUrl(PB_URL, this.code);
  },
  get cover() {
    return coverUrl(PB_URL, this.level);
  },
  get author() {
    return this.level?.expand?.author?.name || 'Unknown maker';
  },
  get uploaded() {
    if (!this.level) return '';
    const date = new Date(this.level.created.replace(' ', 'T'));
    return `${date.toLocaleDateString(undefined, { dateStyle: 'medium' })} (${
      relativeDate(this.level.created)
    })`;
  },
  creatorUrl,
  editUrl,
  isOwner,
  mapName,
  packUrl,
  plural,
});
