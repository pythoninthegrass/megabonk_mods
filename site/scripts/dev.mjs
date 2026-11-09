import { watch } from 'node:fs';
import { spawn } from 'node:child_process';
import { syncDocs } from './sync-docs.mjs';

await syncDocs();
let pending;
let syncing = Promise.resolve();
const watcher = watch(new URL('../../docs/', import.meta.url), () => {
  clearTimeout(pending);
  pending = setTimeout(() => {
    syncing = syncing.then(() => syncDocs()).catch((error) => console.error('Docs sync failed:', error));
  }, 150);
});
const child = spawn(process.execPath, ['node_modules/astro/bin/astro.mjs', 'dev', '--host', '127.0.0.1', ...process.argv.slice(2)], { stdio: 'inherit' });
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => child.kill(signal));
child.on('exit', (code) => {
  clearTimeout(pending);
  watcher.close();
  process.exitCode = code ?? 0;
});
