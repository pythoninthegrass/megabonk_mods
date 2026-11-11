#!/bin/sh
set -eu

DEFAULT_ORIGINS="https://megabonkmod.party,http://localhost:8080,http://127.0.0.1:8080,http://localhost:4321,http://127.0.0.1:4321"

exec "${PB_BIN:-/usr/local/bin/pocketbase}" serve \
  --http="${PB_HTTP:-0.0.0.0:8090}" \
  --dir="${PB_DATA_DIR:-/pb_data}" \
  --hooksDir="${PB_HOOKS_DIR:-/pb/pb_hooks}" \
  --migrationsDir="${PB_MIGRATIONS_DIR:-/pb/pb_migrations}" \
  --origins="${PB_ORIGINS:-$DEFAULT_ORIGINS}" \
  "$@"
