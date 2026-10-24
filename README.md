# orc

**ORC stands for Orchestration.** orc is Nightware Labz' own browser —
our version of LibreWolf, wrapped as a system you install once and run
anywhere. Its mark is the pixel orc face in `branding/` — orc's browser
icon and main icon everywhere.

Install orc, open it, and you're in Blacksite at nosuchmachine.net — with
the same engine, the same rules, and the same privacy posture on Windows,
macOS and Linux. No host browser decides how Blacksite behaves. That's
what browser-neutral means, and it's the recursion that matters: open
nosuchmachine.net *inside* orc and the whole nest — Blacksite OS,
phantom, the bench — runs there exactly as it does anywhere else,
because the engine it runs on is the one orc carries.

orc is built on Mozilla's open-source Gecko technology (the LibreWolf /
Firefox engine line, MPL-2.0). orc and Nightware Labz are not officially
associated with Mozilla or its products, or with the LibreWolf project.

## Download

Get the current build from the
[Releases page](https://github.com/nightwarelabz/orc/releases), and
check it against `SHA256SUMS.txt` from the same release.

| OS | Package | Notes |
|----|---------|-------|
| Windows (x86_64 / arm64) | `orc-<ver>-windows-<arch>-setup.exe` | per-user NSIS installer, no admin |
| Windows (x86_64 / arm64) | `orc-<ver>-windows-<arch>.zip` | portable: unzip anywhere, run `orc.exe` |
| macOS (arm64 / x86_64) | `orc-<ver>-macos-<arch>.zip` | unzip, drag `orc.app` to Applications |
| Linux (x86_64) | `orc-<ver>-linux-x86_64.tar.gz` | extract, run `./install.sh` (per-user, no root) |

### These builds are unsigned — for now

No code-signing certificate yet, so your OS will warn you. That's a
fact about v1, stated plainly, not a defect in the package:

- **Windows:** SmartScreen may say "Windows protected your PC" →
  *More info* → *Run anyway*.
- **macOS:** Gatekeeper may say orc can't be opened → right-click
  (Control-click) `orc.app` → *Open* → *Open*. (Or: System Settings →
  Privacy & Security → *Open Anyway*.)
- **Linux:** no warnings; `install.sh` is a short shell script — read
  it before you run it, it's meant to be read.

Inside, the engine is the **unmodified** LibreWolf build, verified
against two checksums (ours, pinned in
`installers/engine-manifest.json`, and LibreWolf's own published
sidecar) every time a package is built.

## Install, per OS

- **Windows:** run the setup .exe (installs to `%LOCALAPPDATA%\orc`,
  adds a Start Menu shortcut, registers an uninstaller), or unzip the
  portable build anywhere and run `orc.exe`. Your profile lives in
  `%APPDATA%\Nightware Labz\orc\profile`. Uninstalling removes the
  program; your profile stays unless you delete it yourself.
- **macOS:** unzip, move `orc.app` to Applications, right-click → Open
  the first time. Your profile lives in
  `~/Library/Application Support/orc/profile`.
- **Linux:** extract the tarball, `cd orc && ./install.sh`. It copies
  orc to `~/.local/share/orc`, links `~/.local/bin/orc`, and registers
  the desktop entry. Your profile lives in `~/.local/share/orc/profile`
  (or `$XDG_DATA_HOME/orc/profile`). Then just run `orc`.

First run on every OS lands on https://nosuchmachine.net/.

## How it's put together

- `launcher/launcher.c` — one small C file, compiled per OS in CI. It
  finds the engine beside itself, creates orc's profile folder and
  seeds `user.js` there **once** (your edits are never overwritten),
  and launches the engine with `-profile <orc profile>` plus whatever
  arguments you passed.
- `distribution/policies.json` — orc's policy layer, shipped inside the
  engine folder: no telemetry, no Pocket, no sponsored content,
  HTTPS-only, strict tracking protection, uBlock Origin force-installed,
  DuckDuckGo default, Blacksite home + toolbar bookmarks.
- `packaging/` — the staging scripts that download, verify, and wrap
  the engine per OS (`stage-windows.ps1`, `stage-macos.sh`,
  `stage-linux.sh`), plus the launcher build scripts.
- `installers/engine-manifest.json` — the pinned engine: LibreWolf
  158.0.1-2 from dl.librewolf.net, SHA-256 per artifact.
- `branding/` — the face: master, transparent cutout, PNG ladder,
  `orc.ico`, `orc.iconset`. Sizes and formats only; never redrawn.
- `fork/` — the v2 true-source-fork scaffold (branding + mozconfig),
  for when a wrapped engine is no longer enough.
- `DESIGN.md` — the checked options and why the wraparound won for v1.

## Building a release

Push a `v*` tag, or run the **release** workflow manually from the
Actions tab. CI verifies the engine checksums, compiles the launcher
on each OS, stages the packages, and — on a tag — publishes them as a
GitHub Release with `SHA256SUMS.txt`.
