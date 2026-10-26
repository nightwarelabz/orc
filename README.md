<p align="center">
  <img src="branding/orc-256.png" width="168" alt="orc">
</p>

<h1 align="center">orc</h1>

<p align="center"><strong>A recursive browser with explicit parent/child workspaces.</strong></p>

orc carries a pinned Gecko engine, a hardened policy layer, and isolated
browsing workspaces in one install for Windows, macOS, and Linux. Install
orc, open it, and the first run lands on Blacksite at
[nosuchmachine.net](https://nosuchmachine.net/).

The pixel orc face in [`branding/`](branding/) is the sole product mark.
The app, installers, shortcuts, desktop entries, taskbar and dock surfaces,
About pages, and repository documentation all use the same mark and the same
lowercase name: **orc**.

orc is built on Mozilla's open-source Gecko technology (MPL-2.0) and is not
officially associated with Mozilla or its products.

## Download

Get the current build from the
[Releases page](https://github.com/nightwarelabz/orc/releases), then verify it
against `SHA256SUMS.txt` from the same release.

| OS | Package | Notes |
|----|---------|-------|
| Windows (x86_64 / arm64) | `orc-<ver>-windows-<arch>-setup.exe` | per-user NSIS installer, no admin |
| Windows (x86_64 / arm64) | `orc-<ver>-windows-<arch>.zip` | portable: unzip anywhere, run `orc.exe` |
| macOS (arm64 / x86_64) | `orc-<ver>-macos-<arch>.zip` | unzip, drag `orc.app` to Applications |
| Linux (x86_64) | `orc-<ver>-linux-x86_64.tar.gz` | extract, run `./install.sh` (per-user, no root) |

### These builds are unsigned — for now

No paid code-signing identity is attached yet, so Windows and macOS will warn
on first launch.

- **Windows:** SmartScreen may show *Windows protected your PC*. Choose
  **More info → Run anyway** after verifying the checksum.
- **macOS:** follow the one-time Gatekeeper step below.
- **Linux:** `install.sh` is a short, readable per-user install script.

#### macOS first launch

orc is ad-hoc sealed, but it is not yet signed with an Apple Developer ID or
notarized. On first open, macOS may say it cannot verify `orc` and offer only
**Done** or **Move to Trash**.

1. Open `orc.app` once and dismiss the warning.
2. Open **System Settings → Privacy & Security**.
3. Find the message that `orc` was blocked, choose **Open Anyway**, and
   authenticate if asked.

The approval is remembered. The terminal equivalent is:

```sh
xattr -dr com.apple.quarantine /Applications/orc.app
```

The bundle is sealed and verified in CI, so a **damaged** verdict is not the
normal unsigned-app warning. If that appears, delete the download, fetch it
again, and verify `SHA256SUMS.txt` before opening it.

The pinned engine artifact is verified twice during every build: once against
the SHA-256 recorded in `installers/engine-manifest.json` and again against
the publisher's release sidecar.

## Install, per OS

- **Windows:** run the setup executable, or unzip the portable build and run
  `orc.exe`. The installed app lives in `%LOCALAPPDATA%\orc`; its profile is
  `%APPDATA%\orc\profile`. Uninstalling removes the program but preserves the
  profile.
- **macOS:** move `orc.app` to Applications and complete the one-time
  Gatekeeper approval. The profile is
  `~/Library/Application Support/orc/profile`.
- **Linux:** extract the archive, run `cd orc && ./install.sh`, then launch
  `orc`. The profile is `~/.local/share/orc/profile` or
  `$XDG_DATA_HOME/orc/profile`.

## Recursive workspaces

orc can branch a browsing session into named, independent contexts:

```sh
orc --orc-workspace blacksite --orc-child research https://nosuchmachine.net/
orc --orc-workspace blacksite/research --orc-workspace-info
orc --orc-workspace blacksite/research --orc-parent
```

Each branch has its own profile and explicit parent; nesting is bounded at 16
levels. Named branches run independently, but the same branch cannot be opened
twice because Gecko retains its normal profile lock. See
[WORKSPACES.md](WORKSPACES.md) for paths, inheritance, limits, and the
distinction between workspace state and web-frame recursion.

## How it is put together

- `launcher/launcher.c` — a small native launcher compiled per OS. It locates
  the bundled engine, creates orc's profile, seeds `user.js` and the default
  browser chrome stylesheet when absent, selects parent/child workspace
  profiles, exports their lineage, and forwards all other engine arguments.
- `distribution/policies.json` — the policy layer: no telemetry, Pocket, or
  sponsored content; HTTPS-only mode; strict tracking protection; uBlock
  Origin; DuckDuckGo; and Blacksite home/bookmarks.
- `distribution/distribution.ini` and `profile/chrome/userChrome.css` — the
  orc dark green default for browser chrome, tabs, and toolbar controls.
- `packaging/` — platform staging, complete display-string rebranding, icon
  replacement, and launcher builds.
- `installers/engine-manifest.json` — the pinned Gecko artifact set and SHA-256
  values.
- `branding/` — the canonical orc face: source art, transparent master, PNG
  ladder, Windows ICO, and macOS iconset.
- `fork/` — the source-build scaffold for a future direct Gecko fork.
- `DESIGN.md` — architectural decisions and boundaries.

## Building a release

Push a `v*` tag, or run the **release** workflow manually from Actions. CI
verifies the engine checksums, compiles the launcher, applies orc branding and
icons, audits the staged browser, builds each package, and publishes
`SHA256SUMS.txt` with tagged releases.

## Development checks

Run:

```sh
python -m unittest discover -s tests -v
```

A C compiler is required; on Windows, use a Visual Studio developer shell.
The checks use temporary profiles and never touch a real orc profile.
