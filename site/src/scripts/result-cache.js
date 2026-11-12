const PREFIX = 'levels-cache:';

export const cacheKey = (scope, user, parts) =>
  PREFIX + JSON.stringify([scope, user?.id ?? null, ...parts]);

export function readCached(storage, key) {
  try {
    return JSON.parse(storage?.getItem(key) ?? 'null');
  } catch {
    return null;
  }
}

export function writeCached(storage, key, value) {
  try {
    storage?.setItem(key, JSON.stringify(value));
  } catch {
    // Storage can be full or blocked; the cache is only an optimisation.
  }
}
