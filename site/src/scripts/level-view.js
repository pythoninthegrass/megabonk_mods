import {
  codeFromPath,
  coverUrl,
  downloadUrl,
  editUrl,
  giscusAttrs,
  isOwner,
  likeTitle,
  mapName,
  pbErrorMessages,
  plural,
  relativeDate,
} from './gallery.js';
import { packList } from './levels.js';
import { giscusConfig, pb, PB_URL } from './pb.js';

export default () => ({
  code: null,
  level: null,
  state: 'loading',
  liked: null,
  busy: false,
  copied: false,
  notice: '',
  reporting: false,
  reason: '',

  async init() {
    this.$store.session.loadProviders();
    this.code = codeFromPath(location.pathname);
    if (!this.code) {
      this.state = 'notfound';
      return;
    }
    try {
      this.level = await pb.collection('levels').getFirstListItem(
        pb.filter('code = {:code}', { code: this.code }),
        { expand: 'author' },
      );
    } catch (error) {
      this.state = error.status === 404 ? 'notfound' : 'error';
      return;
    }
    document.title = `${this.level.title} · Megabonk Mod Party`;
    this.state = 'ready';
    await this.loadLike();
    this.$watch('$store.session.user', () => this.loadLike());
    this.mountComments();
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

  async sendReport() {
    this.busy = true;
    this.notice = '';
    try {
      await pb.collection('reports').create({
        user: pb.authStore.record.id,
        level: this.level.id,
        reason: this.reason.trim(),
      });
      this.reporting = false;
      this.reason = '';
      this.notice = 'Report sent. Thank you.';
    } catch (error) {
      this.notice = pbErrorMessages(error).join(' ');
    } finally {
      this.busy = false;
    }
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
    return packList(this.level?.packs);
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
  editUrl,
  isOwner,
  mapName,
  plural,
});
