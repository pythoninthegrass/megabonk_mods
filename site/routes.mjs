const LEVEL_ROUTE = /^\/l\/[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}-[0-9A-HJKMNP-TV-Z]{3}\/?$/;
const PACK_ROUTE = /^\/p\/[a-z0-9][a-z0-9_-]{0,63}\/?$/;
const CREATOR_ROUTE = /^\/u\/[a-z0-9]{15}\/?$/;

// Static page that serves a share link, pack address or creator address, or null for any other path.
export function viewRoute(pathname) {
  if (LEVEL_ROUTE.test(pathname)) return '/levels/view/index.html';
  if (CREATOR_ROUTE.test(pathname)) return '/creators/view/index.html';
  if (PACK_ROUTE.test(pathname)) return '/packs/view/index.html';
  return null;
}
