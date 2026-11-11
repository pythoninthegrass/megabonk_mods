import PocketBase from 'pocketbase';

export const PB_URL = (import.meta.env.PUBLIC_PB_URL || 'http://127.0.0.1:8090').replace(/\/$/, '');
export const pb = new PocketBase(PB_URL);

export const giscusConfig = {
  repo: import.meta.env.PUBLIC_GISCUS_REPO,
  repoId: import.meta.env.PUBLIC_GISCUS_REPO_ID,
  category: import.meta.env.PUBLIC_GISCUS_CATEGORY,
  categoryId: import.meta.env.PUBLIC_GISCUS_CATEGORY_ID,
};
