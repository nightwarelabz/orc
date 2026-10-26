# orc installers

Each platform package installs the pinned Gecko engine and Tractor search
service with orc's launcher, policies, profile seed, lowercase product name,
and canonical icon.

| OS | Output | Profile |
|---|---|---|
| Windows | NSIS setup executable and portable zip | `%APPDATA%\orc\profile` |
| macOS | zip containing `orc.app` | `~/Library/Application Support/orc/profile` |
| Linux | tarball containing `install.sh` | `$XDG_DATA_HOME/orc/profile`, otherwise `~/.local/share/orc/profile` |

## Invariants

- Every engine artifact is verified against both the SHA-256 pinned in
  `engine-manifest.json` and its publisher sidecar.
- Every Tractor archive is verified against the SHA-256 pinned in
  `tractor-manifest.json` and its release checksum list.
- The native launcher always selects orc's own profile and seeds
  `profile/user.js` and `chrome/userChrome.css` only when each file does not
  already exist. This sets up the dark green browser chrome without replacing
  a user's profile styling.
- `distribution/distribution.ini` enables profile chrome styling by default;
  the orc dark green colors apply to browser controls and tabs, not websites.
- User-visible strings are rewritten to `orc` and audited before packaging.
- Browser artwork, executables, app bundles, installers, uninstallers,
  shortcuts, desktop files, and taskbar/dock surfaces use the assets in
  `../branding/`.
- The updater inside the engine stays disabled; releases are controlled by
  orc's verified package pipeline.

## Platform layout

- **Windows:** the portable engine is staged under `engine/`; `orc.exe`
  launches it. The bundled `tractor/` tree supplies the local search service.
  Both executable resources and the NSIS UI use `orc.ico`.
- **macOS:** the engine app is nested inside `orc.app`. The outer and nested
  bundle plists use the name `orc`, and both bundles receive `orc.icns`
  before the inside-out ad-hoc seal. Tractor is nested in the outer app's
  Resources folder.
- **Linux:** the package contains `orc`, `engine/`, the full PNG icon
  ladder, `tractor/`, `orc.desktop`, and `install.sh`. Installation registers every
  icon size in the user's hicolor theme.

The release workflow builds all packages and publishes a top-level
`SHA256SUMS.txt` for tagged releases.
