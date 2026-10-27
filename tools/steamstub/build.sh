#!/usr/bin/env bash
# Build the offline Steamworks stub into a PE32+ DLL (x64).
#   tools/steamstub/build.sh
set -euo pipefail
cd "$(dirname "$0")/../.."
# Prefer the real mingw-w64 GCC; some shells shadow it with a clang shim.
# Fall back to any x86_64-w64-mingw32-gcc on PATH.
CC="${CC:-/opt/homebrew/bin/x86_64-w64-mingw32-gcc}"
if [ ! -x "$CC" ] || ! "$CC" --version 2>/dev/null | grep -qi mingw; then
  CC="$(command -v x86_64-w64-mingw32-gcc 2>/dev/null || true)"
fi
if [ -z "$CC" ] || ! "$CC" --version 2>/dev/null | grep -qi mingw; then
  echo "missing a mingw-w64 x86_64 GCC (run: task game:mingw:install)" >&2
  exit 1
fi
OUT="tools/steamstub/steam_api64.dll"
"$CC" -O2 -shared -fPIC -o "$OUT" tools/steamstub/steamstub.c \
  && echo "built $OUT" \
  && ls -l "$OUT"
