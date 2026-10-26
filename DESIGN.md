# orc — design and checked options

orc is a recursive browser that carries the same pinned Gecko engine,
policies, profile defaults, and workspace model on Windows, macOS, and Linux.
The goal is browser neutrality: Blacksite and any other site run against the
engine orc ships instead of inheriting whichever engine happens to be present
on the host.

## Options checked

1. **Host WebView shell — rejected.** A system WebView would produce different
   behavior on each OS. An Electron shell would ship a consistent engine, but
   it would make the project Chromium-only.
2. **Pinned Gecko distribution — current architecture.** orc wraps a verified
   upstream Gecko artifact with its own launcher, name, icon, policy layer,
   profile seed, and workspace boundary. This is portable and releaseable
   without a full browser build farm.
3. **Direct Gecko source build — prepared for a later version.** The
   `fork/` scaffold records the branding and build direction for moving the
   current distribution layer into a full source build.

The bundled engine remains MPL-2.0. Upstream legal notices are preserved as
legal material; no upstream name or logo is used as product branding.

## Architecture

```text
installer
  └─ orc launcher
       ├─ engine/        pinned Gecko runtime
       ├─ tractor/       pinned Tractor local search service
       ├─ distribution/  policies.json, distribution.ini
       ├─ defaults/pref/ autoconfig
       └─ profile-seed/  user.js, chrome/userChrome.css
  profile               orc-owned user data
  updates               verified orc releases
```

- **Home / first run:** https://nosuchmachine.net/
- **Default search:** Tractor's local recursive search page; DuckDuckGo web
  results and Wikimedia Commons images are enabled by default.
- **Content blocking:** uBlock Origin is installed by policy.
- **Privacy:** telemetry, studies, Pocket, and sponsored content are disabled.
- **Media and graphics:** WebGL and media playback remain functional.
- **Default appearance:** the browser chrome uses orc's dark green palette;
  websites retain their own page colors.
- **Branding:** the name is lowercase `orc`; every supported icon surface
  uses the canonical face from `branding/`.

## Recursive workspace boundary

The launcher models a workspace as a canonical path with an explicit parent
and a maximum depth of 16. `--orc-child` descends into a separate profile,
`--orc-parent` selects its ancestor, and `--orc-workspace-info` reports
lineage without launching the engine or writing profile data.

Each branch is seeded independently. Cookies, permissions, saved passwords,
and sessions are not copied from the parent. Named branches use Gecko's
`-no-remote` mode so a URL cannot be handed to a different running context.
This creates browser-state separation, not a new OS security sandbox.

[WORKSPACES.md](WORKSPACES.md) defines the command-line contract, canonical
paths, inheritance rules, and limits. Native tests run on Windows, macOS, and
Linux; Linux CI also exercises nested documents, workers, Wasm, shared memory,
isolated storage, and a server-denied frame with the staged browser.

## orc inside Blacksite OS

Blacksite exposes an orc room that links visitors to the native download and
may preview pages that allow framing. CSP, COOP, COEP, certificate checks, and
`X-Frame-Options` remain enforced. The in-OS room is a doorway to orc, not a
replacement engine.

## Branding contract

- The displayed name is exactly **orc**, always lowercase and never expanded.
- The canonical mark is the pixel orc face in `branding/`.
- The same face is used for browser chrome, About/private-browsing artwork,
  executables, app bundles, installers, shortcuts, launchers, taskbar/dock
  surfaces, releases, and repository presentation.
- User-visible upstream names and logos are rejected by the packaging audit.

See [branding/BRANDING.md](branding/BRANDING.md) for the required surface
matrix and asset inventory.

## Status

The repository ships the native launcher, platform staging scripts, release
packaging, policy layer, branding pipeline, and recursive workspace profiles.
Paid Windows signing and macOS notarization remain future work.
[UPDATES.md](UPDATES.md) describes the planned updater and is not a claim that
the updater is already implemented.
