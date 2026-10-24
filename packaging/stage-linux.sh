#!/bin/sh
# Stage the Linux orc package.
#
# Extracts the pinned LibreWolf package tarball (its sha256 is
# verified by CI against installers/engine-manifest.json + the
# official sidecar before this script runs) and lays out:
#
#   orc/orc                     (launcher)
#   orc/engine/                 (the folder that held the librewolf binary)
#   orc/engine/distribution/    (orc's policies)
#   orc/profile-seed/user.js
#   orc/icons/                  (the face, PNG ladder)
#   orc/orc.desktop
#   orc/install.sh              (per-user install, no root)
#
# Usage: stage-linux.sh <librewolf.tar.xz> <version> <launcher-binary> [outdir]
set -eu
TARBALL="${1:?usage: stage-linux.sh <tarball> <version> <launcher> [outdir]}"
VERSION="${2:?version required}"
LAUNCHER="${3:?launcher binary required}"
OUTDIR="${4:-dist}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

[ -f "$TARBALL" ] || { echo "stage-linux: tarball not found: $TARBALL" >&2; exit 1; }
[ -x "$LAUNCHER" ] || { echo "stage-linux: launcher not executable: $LAUNCHER" >&2; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/orc-stage.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
tar -xJf "$TARBALL" -C "$WORK"
BIN="$(find "$WORK" -name 'librewolf' -type f | head -n 1)"
[ -n "$BIN" ] || { echo "stage-linux: librewolf binary not found in tarball" >&2; exit 1; }
ENGINE_DIR="$(dirname "$BIN")"

STAGE_ROOT="$OUTDIR/stage-linux-x86_64"
rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT/orc/profile-seed" "$STAGE_ROOT/orc/icons"
PKG="$STAGE_ROOT/orc"

cp "$LAUNCHER" "$PKG/orc"
chmod +x "$PKG/orc"
cp -r "$ENGINE_DIR" "$PKG/engine"
mkdir -p "$PKG/engine/distribution"
cp "$ROOT/distribution/policies.json" "$PKG/engine/distribution/policies.json"
cp "$ROOT/profile/user.js" "$PKG/profile-seed/user.js"
for s in 512 256 128 64 32 16; do
  cp "$ROOT/branding/orc-$s.png" "$PKG/icons/orc-$s.png"
done
cp "$ROOT/packaging/orc.desktop" "$PKG/orc.desktop"
cp "$ROOT/packaging/install.sh" "$PKG/install.sh"
chmod +x "$PKG/install.sh"

mkdir -p "$OUTDIR"
OUTTGZ="$OUTDIR/orc-$VERSION-linux-x86_64.tar.gz"
rm -f "$OUTTGZ"
tar -czf "$OUTTGZ" -C "$STAGE_ROOT" orc
(cd "$OUTDIR" && sha256sum "$(basename "$OUTTGZ")" > "$(basename "$OUTTGZ").sha256sum")
echo "staged $PKG"
echo "packed  $OUTTGZ"
