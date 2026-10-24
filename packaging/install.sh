#!/bin/sh
# orc — per-user install (no root).
#
# Copies this tree to ~/.local/share/orc, points ~/.local/bin/orc at
# the launcher, and registers the desktop entry + icon. Your profile
# lives in ~/.local/share/orc/profile (created by the launcher on
# first run) — actually under $XDG_DATA_HOME/orc/profile when
# XDG_DATA_HOME is set; either way this script never touches it.
set -eu
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/.local/share/orc"

mkdir -p "$DEST" "$HOME/.local/bin" "$HOME/.local/share/applications" \
         "$HOME/.local/share/icons/hicolor/256x256/apps"
cp -r "$SRC/." "$DEST/"
chmod +x "$DEST/orc" "$DEST/engine/librewolf" 2>/dev/null || chmod +x "$DEST/orc"
ln -sf "$DEST/orc" "$HOME/.local/bin/orc"

# Desktop entry with absolute paths, so launchers find orc even when
# ~/.local/bin is not on PATH.
sed -e "s|^Exec=.*|Exec=$DEST/orc %u|" \
    -e "s|^Icon=.*|Icon=$DEST/icons/orc-256.png|" \
    "$SRC/orc.desktop" > "$HOME/.local/share/applications/orc.desktop"
cp "$SRC/icons/orc-256.png" "$HOME/.local/share/icons/hicolor/256x256/apps/orc.png"

command -v update-desktop-database >/dev/null 2>&1 && \
  update-desktop-database "$HOME/.local/share/applications" >/dev/null 2>&1 || true

echo "orc installed to $DEST"
echo "run it with: orc   (make sure ~/.local/bin is on your PATH)"
echo "remove it with: rm -rf $DEST ~/.local/bin/orc ~/.local/share/applications/orc.desktop"
