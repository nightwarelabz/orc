#!/bin/sh
# Build the orc launcher for Linux or macOS.
#
# Usage: build-launcher.sh <linux|macos> <output-path> [arch]
#   arch (macOS only): arm64 | x86_64  (default: host arch)
set -eu
OS="${1:?usage: build-launcher.sh <linux|macos> <output-path> [arch]}"
OUT="${2:?usage: build-launcher.sh <linux|macos> <output-path> [arch]}"
ARCH="${3:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CC="${CC:-cc}"

case "$OS" in
  linux)
    ENGINE_REL='engine/librewolf'
    SEED_REL='profile-seed/user.js'
    "$CC" -O2 -Wall -Wextra -std=c11 \
      -DENGINE_REL="\"$ENGINE_REL\"" -DSEED_REL="\"$SEED_REL\"" \
      -o "$OUT" "$ROOT/launcher/launcher.c"
    ;;
  macos)
    ENGINE_REL='../Resources/engine/LibreWolf.app/Contents/MacOS/librewolf'
    SEED_REL='../Resources/profile-seed/user.js'
    ARCHFLAG=""
    if [ -n "$ARCH" ]; then ARCHFLAG="-arch $ARCH"; fi
    # shellcheck disable=SC2086
    clang -O2 -Wall -Wextra -std=c11 $ARCHFLAG \
      -DENGINE_REL="\"$ENGINE_REL\"" -DSEED_REL="\"$SEED_REL\"" \
      -o "$OUT" "$ROOT/launcher/launcher.c"
    ;;
  *)
    echo "build-launcher.sh: unknown OS '$OS' (want linux|macos)" >&2
    exit 2
    ;;
esac
echo "built $OUT ($OS${ARCH:+/$ARCH})"
