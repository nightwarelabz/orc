# orc wraparound installers

One job per OS: lay down the pinned engine + orc's distribution layer,
register orc with its own profile, get out of the way.

| OS      | Form                             | Engine source (pinned)        | Profile folder |
|---------|----------------------------------|-------------------------------|----------------|
| Windows | NSIS installer (.exe) + portable zip | LibreWolf windows portable zip | `%APPDATA%\Nightware Labz\orc\profile` |
| macOS   | .zip holding `orc.app`           | LibreWolf macOS .dmg          | `~/Library/Application Support/orc/profile` |
| Linux   | tarball + `install.sh`           | LibreWolf linux package tar.xz | `$XDG_DATA_HOME/orc/profile`, else `~/.local/share/orc/profile` |

Rules:
- Engine binaries are **unmodified** upstream builds (LibreWolf
  158.0.1-2, MPL-2.0), pinned in `engine-manifest.json` with SHA-256
  per artifact. Every build verifies twice — against the manifest and
  against the official `.sha256sum` sidecar at dl.librewolf.net — and a
  mismatch on either stops the build.
- The wrap (launcher, `../launcher/launcher.c`) does exactly three
  things: ensure orc's profile folder exists, seed `profile/user.js`
  into it the first time only, and exec the engine with
  `-profile <orc profile>` plus the user's arguments.
- `distribution/policies.json` rides **inside** the engine folder
  (`engine/distribution/` on Windows/Linux;
  `LibreWolf.app/Contents/Resources/distribution/` inside the nested
  app on macOS) — that is where Gecko reads it from.
- Uninstall removes the program and leaves the profile alone: their
  history is theirs. (Windows: the NSIS uninstaller says so in its
  script; macOS/Linux: delete the app/tree — the profile is elsewhere.)

## Per-OS packaging

- **Windows** — `../packaging/stage-windows.ps1` downloads + verifies
  the portable zip itself, stages `orc.exe` (launcher, built by
  `../packaging/build-launcher.ps1` with the face as its icon) beside
  `engine/`, and zips a portable build. `nsis/orc.nsi` then wraps the
  staged tree into the per-user setup .exe (Start Menu shortcut,
  optional desktop shortcut, Add/Remove Programs entry).
- **macOS** — `../packaging/stage-macos.sh` mounts the pinned .dmg and
  nests the untouched `LibreWolf.app` inside `orc.app` under
  `Contents/Resources/engine/`, with the launcher as
  `Contents/MacOS/orc`, the icon as `Contents/Resources/orc.icns`
  (CI builds it from `../branding/orc.iconset` with iconutil), the
  profile seed under `Contents/Resources/profile-seed/`, and
  `Info.plist` rendered from `../packaging/Info.plist.tmpl`
  (bundle id `net.nosuchmachine.orc`).
- **Linux** — `../packaging/stage-linux.sh` stages the launcher as
  `orc` beside `engine/`, icons, `orc.desktop`, and `install.sh`,
  which installs per-user into `~/.local/share/orc` with a
  `~/.local/bin/orc` symlink and a desktop entry. No root, no package
  manager.

## Unsigned, for now

v1 ships unsigned: Windows SmartScreen and macOS Gatekeeper warn on
first run (README.md in the repo root has the exact steps). Signing +
notarization come when there are certificates to sign with; nothing
about the packages pretends otherwise.
