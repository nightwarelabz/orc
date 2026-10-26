#!/bin/sh
# Stage the Linux orc package.
#
# Extracts the pinned Gecko package tarball (its SHA-256 is
# verified by CI against installers/engine-manifest.json + the
# official sidecar before this script runs) and lays out:
#
#   orc/orc                     (launcher)
#   orc/engine/                 (pinned engine)
#   orc/tractor/                (pinned Tractor search service)
#   orc/engine/distribution/    (orc's policies)
#   orc/profile-seed/user.js and chrome/userChrome.css
#   orc/icons/                  (the face, PNG ladder)
#   orc/orc.desktop
#   orc/install.sh              (per-user install, no root)
#
# Usage: stage-linux.sh <engine.tar.xz> <tractor.tar.gz> <version> <launcher-binary> [outdir]
set -eu
TARBALL="${1:?usage: stage-linux.sh <engine.tar.xz> <tractor.tar.gz> <version> <launcher> [outdir]}"
TRACTOR_TARBALL="${2:?Tractor archive required}"
VERSION="${3:?version required}"
LAUNCHER="${4:?launcher binary required}"
OUTDIR="${5:-dist}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
UPSTREAM_SLUG="$(printf '%s%s' 'libre' 'wolf')"

[ -f "$TARBALL" ] || { echo "stage-linux: tarball not found: $TARBALL" >&2; exit 1; }
[ -f "$TRACTOR_TARBALL" ] || { echo "stage-linux: Tractor bundle not found: $TRACTOR_TARBALL" >&2; exit 1; }
[ -x "$LAUNCHER" ] || { echo "stage-linux: launcher not executable: $LAUNCHER" >&2; exit 1; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/orc-stage.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
tar -xJf "$TARBALL" -C "$WORK"
mkdir -p "$WORK/tractor"
tar -xzf "$TRACTOR_TARBALL" -C "$WORK/tractor"
BIN="$(find "$WORK" -name "$UPSTREAM_SLUG" -type f | head -n 1)"
[ -n "$BIN" ] || { echo "stage-linux: engine binary not found in tarball" >&2; exit 1; }
ENGINE_DIR="$(dirname "$BIN")"
TRACTOR_BIN="$(find "$WORK/tractor" -path '*/Tractor/Tractor' -type f | head -n 1)"
[ -n "$TRACTOR_BIN" ] || { echo "stage-linux: Tractor executable not found in bundle" >&2; exit 1; }

STAGE_ROOT="$OUTDIR/stage-linux-x86_64"
rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT/orc/profile-seed/chrome" "$STAGE_ROOT/orc/icons"
PKG="$STAGE_ROOT/orc"

cp "$LAUNCHER" "$PKG/orc"
chmod +x "$PKG/orc"
cp -r "$ENGINE_DIR" "$PKG/engine"
mkdir -p "$PKG/tractor"
cp -r "$(dirname "$TRACTOR_BIN")" "$PKG/tractor/Tractor"
# Full orc branding: the engine binaries take orc's name (the launcher
# execs engine/orc, which finds its -bin beside itself), and every
# display string + logo inside the engine is rebranded (the patch
# audits itself: it fails the stage if a display file still names
# the upstream product name).
mv "$PKG/engine/$UPSTREAM_SLUG" "$PKG/engine/orc"
mv "$PKG/engine/$UPSTREAM_SLUG-bin" "$PKG/engine/orc-bin"
python3 "$ROOT/packaging/brand-patch.py" patch "$PKG/engine" "$ROOT/branding"
mkdir -p "$PKG/engine/distribution"
cp "$ROOT/distribution/policies.json" "$PKG/engine/distribution/policies.json"
cp "$ROOT/distribution/distribution.ini" "$PKG/engine/distribution/distribution.ini"
# orc's autoconfig: append the WebGL compatibility block and verify it.
CFG="$PKG/engine/$UPSTREAM_SLUG.cfg"
[ -f "$CFG" ] || { echo "stage-linux: engine config not found" >&2; exit 1; }
if ! grep -q 'upstreamWebglPrompt' "$CFG"; then
  cat "$ROOT/packaging/orc-autoconfig.cfg" >> "$CFG"
fi
grep -q 'pref(upstreamWebglPrompt, false)' "$CFG" || { echo "stage-linux: orc autoconfig block missing" >&2; exit 1; }
cp "$ROOT/profile/user.js" "$PKG/profile-seed/user.js"
cp "$ROOT/profile/chrome/userChrome.css" "$PKG/profile-seed/chrome/userChrome.css"
cp "$ROOT/WORKSPACES.md" "$PKG/WORKSPACES.md"
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
