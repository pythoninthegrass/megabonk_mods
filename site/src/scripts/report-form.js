import { pbErrorMessages } from './gallery.js';
import { pb } from './pb.js';
import {
  COPYRIGHT_GOOD_FAITH,
  COPYRIGHT_PERJURY,
  itemLink,
  REPORT_CATEGORIES,
  reportPayload,
} from './reports.js';

const emptyCopyright = () => ({
  contactEmail: '',
  contactAddress: '',
  contactPhone: '',
  work: '',
  itemUrl: '',
  goodFaith: false,
  accurate: false,
  fairUseConsidered: false,
  signature: '',
});

// Alpine state and methods for the report form; the host component supplies reportTarget() as {level} or {pack}.
export const reportForm = () => ({
  reporting: false,
  category: 'other',
  reason: '',
  copyright: emptyCopyright(),
  categories: REPORT_CATEGORIES,
  goodFaithText: COPYRIGHT_GOOD_FAITH,
  perjuryText: COPYRIGHT_PERJURY,

  toggleReport() {
    this.reporting = !this.reporting;
    if (this.reporting) this.copyright.itemUrl ||= itemLink(location.origin, this.reportTarget());
  },

  get reportReady() {
    return this.category === 'copyright' || this.reason.trim() !== '';
  },

  async sendReport() {
    this.busy = true;
    this.notice = '';
    try {
      await pb.collection('reports').create(reportPayload({
        userId: pb.authStore.record.id,
        target: this.reportTarget(),
        category: this.category,
        reason: this.reason,
        copyright: this.copyright,
      }));
      this.reporting = false;
      this.reason = '';
      this.copyright = emptyCopyright();
      this.notice = this.category === 'copyright'
        ? 'Copyright report sent. A site owner will review it and may contact you for missing details.'
        : 'Report sent. Thank you.';
    } catch (error) {
      this.notice = pbErrorMessages(error).join(' ');
    } finally {
      this.busy = false;
    }
  },
});
