import { creatorUrl, pbErrorMessages, plural, relativeDate } from './gallery.js';
import {
  formatBytes,
  isPackId,
  packDownloadUrl,
  packFilter,
  packIdFromPath,
  packPlatforms,
} from './packs.js';
import { pb, PB_URL } from './pb.js';
import { reportForm } from './report-form.js';

export default () => ({
  id: null,
  versions: [],
  pack: null,
  state: 'loading',
  busy: false,
  notice: '',
  ...reportForm(),

  async init() {
    this.$store.session.loadProviders();
    this.id = packIdFromPath(location.pathname);
    if (!isPackId(this.id)) {
      this.state = 'notfound';
      return;
    }
    await this.load();
    this.$watch('$store.session.user', () => this.load());
  },

  async load() {
    try {
      this.versions = await pb.collection('packs').getFullList({
        filter: packFilter(this.id),
        sort: '-created',
        expand: 'author',
      });
    } catch (error) {
      this.state = 'error';
      this.notice = pbErrorMessages(error).join(' ');
      return;
    }
    const wanted = new URLSearchParams(location.search).get('v');
    this.pack = this.versions.find((record) => record.version === wanted) ?? this.versions[0] ??
      null;
    this.state = this.pack ? 'ready' : 'notfound';
    if (this.pack) document.title = `${this.id} ${this.pack.version} · Megabonk Mod Party`;
  },

  reportTarget() {
    return { pack: this.pack };
  },

  downloadFor(platform) {
    return packDownloadUrl(PB_URL, this.id, platform, this.pack.version);
  },

  get platforms() {
    return packPlatforms(this.pack);
  },
  get author() {
    return this.pack?.expand?.author?.name || 'Unknown maker';
  },
  get uploaded() {
    return this.pack ? relativeDate(this.pack.created) : '';
  },
  get unzipTo() {
    return `UserData/LevelPacks/${this.id}/`;
  },
  creatorUrl,
  formatBytes,
  plural,
});
