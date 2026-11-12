import { pbErrorMessages, plural, relativeDate } from './gallery.js';
import { packFormData, packUploadTooLarge, packUrl } from './packs.js';
import { pb } from './pb.js';

export default () => ({
  mine: [],
  mineState: 'idle',
  packId: '',
  description: '',
  attested: false,
  errors: [],
  busy: false,
  confirmDelete: null,

  async init() {
    this.$store.session.loadProviders();
    await this.loadMine();
    this.$watch('$store.session.user', () => this.loadMine());
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
      this.mine = await pb.collection('packs').getFullList({
        filter: pb.filter('author = {:id}', { id: user.id }),
        sort: '-created',
      });
      this.mineState = 'ready';
    } catch (error) {
      this.errors = pbErrorMessages(error);
      this.mineState = 'error';
    }
  },

  async submit() {
    this.errors = [];
    const files = {
      manifest: this.$refs.manifest.files[0],
      attachments: this.$refs.attachments.files[0],
      bundleWindows: this.$refs.bundleWindows.files[0],
      bundleLinux: this.$refs.bundleLinux.files[0],
    };
    const tooLarge = packUploadTooLarge(Object.values(files));
    if (tooLarge) {
      this.errors = [tooLarge];
      return;
    }
    this.busy = true;
    try {
      const created = await pb.collection('packs').create(packFormData(this, files));
      location.assign(packUrl(created.packId, created.version));
    } catch (error) {
      this.errors = pbErrorMessages(error);
    } finally {
      this.busy = false;
    }
  },

  async remove(pack) {
    try {
      await pb.collection('packs').delete(pack.id);
      this.confirmDelete = null;
      await this.loadMine();
    } catch (error) {
      this.errors = pbErrorMessages(error);
    }
  },

  packUrl,
  plural,
  relativeDate,
});
