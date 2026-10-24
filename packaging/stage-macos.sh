#!/bin/sh
# Stage the macOS orc package.
#
# Mounts a LibreWolf .dmg (its sha256 is verified by CI against
# installers/engine-manifest.json + the official sidecar before this
# script runs), and builds orc.app around the unmodified LibreWolf.app:
#
#   orc.app/Contents/MacOS/orc                              (launcher)
#   orc.app/Contents/Resources/engine/LibreWolf.app         (engine, intact)
#   orc.app/Contents/Resources/engine/LibreWolf.app/Contents/Resources/distribution/
#   orc.app/Contents/Resources/profile-seed/user.js
#   orc.app/Contents/Resources/orc.icns
#   orc.app/Contents/Info.plist                             (from template)
#
# Usage: stage-macos.sh <librewolf.dmg> <arm64|x86_64> <version> <launcher-binary> [outdir]
# Env:   ORC_ICNS=/path/to/orc.icns  (default: dist/orc.icns)
set -eu
DMG="${1:?usage: stage-macos.sh <dmg> <arch> <version> <launcher> [outdir]}"
ARCH="${2:?arch required (arm64|x86_64)}"
VERSION="${3:?version required}"
LAUNCHER="${4:?launcher binary required}"
OUTDIR="${5:-dist}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICNS="${ORC_ICNS:-$OUTDIR/orc.icns}"

[ -f "$DMG" ] || { echo "stage-macos: dmg not found: $DMG" >&2; exit 1; }
[ -x "$LAUNCHER" ] || { echo "stage-macos: launcher not executable: $LAUNCHER" >&2; exit 1; }
[ -f "$ICNS" ] || { echo "stage-macos: orc.icns not found at $ICNS (build it: iconutil -c icns branding/orc.iconset -o $ICNS)" >&2; exit 1; }

MNT="$(mktemp -d /tmp/orc-mnt.XXXXXX)"
WORK="$(mktemp -d /tmp/orc-stage.XXXXXX)"
cleanup() {
  hdiutil detach "$MNT" >/dev/null 2>&1 || true
  rm -rf "$MNT" "$WORK"
}
trap cleanup EXIT

hdiutil attach -nobrowse -readonly -mountpoint "$MNT" "$DMG" >/dev/null
SRC_APP="$(find "$MNT" -maxdepth 2 -name 'LibreWolf.app' -type d | head -n 1)"
[ -n "$SRC_APP" ] || { echo "stage-macos: LibreWolf.app not found in dmg" >&2; exit 1; }

STAGE_ROOT="$OUTDIR/stage-macos-$ARCH"
rm -rf "$STAGE_ROOT"
mkdir -p "$STAGE_ROOT"
APP="$STAGE_ROOT/orc.app"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/engine" "$APP/Contents/Resources/profile-seed"

# The engine rides inside, byte-for-byte as upstream shipped it.
ditto "$SRC_APP" "$APP/Contents/Resources/engine/LibreWolf.app"
hdiutil detach "$MNT" >/dev/null

# orc's policy layer lives inside the nested app's Resources.
mkdir -p "$APP/Contents/Resources/engine/LibreWolf.app/Contents/Resources/distribution"
cp "$ROOT/distribution/policies.json" \
   "$APP/Contents/Resources/engine/LibreWolf.app/Contents/Resources/distribution/policies.json"

cp "$LAUNCHER" "$APP/Contents/MacOS/orc"
chmod +x "$APP/Contents/MacOS/orc"
cp "$ROOT/profile/user.js" "$APP/Contents/Resources/profile-seed/user.js"
cp "$ICNS" "$APP/Contents/Resources/orc.icns"
sed "s/__VERSION__/$VERSION/g" "$ROOT/packaging/Info.plist.tmpl" > "$APP/Contents/Info.plist"
printf 'APPL????' > "$APP/Contents/PkgInfo"

mkdir -p "$OUTDIR"
OUTZIP="$OUTDIR/orc-$VERSION-macos-$ARCH.zip"
rm -f "$OUTZIP"
# ditto is the macOS-correct way to zip an .app (keeps resource forks
# and symlinks); fall back to zip -y anywhere else.
if command -v ditto >/dev/null 2>&1; then
  ditto -c -k --keepParent "$APP" "$OUTZIP"
else
  (cd "$STAGE_ROOT" && zip -r -y -q "$OLDPWD/$OUTZIP" orc.app)
fi
if command -v shasum >/dev/null 2>&1; then
  (cd "$OUTDIR" && shasum -a 256 "$(basename "$OUTZIP")" > "$(basename "$OUTZIP").sha256sum")
fi
echo "staged $APP"
echo "packed  $OUTZIP"
