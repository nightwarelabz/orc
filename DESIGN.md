# orc — design and checked options

Chase's directive (2026-10-24): port our own version of LibreWolf, name it
**orc**, and build our own **wraparound browser system** with it, so we are
truly browser-neutral — people install orc, run it, and use
nosuchmachine.net and anything else they desire.

## What "browser-neutral" has to mean

Blacksite OS today only runs inside someone else's browser — and it shows:
COEP/Safari quirks, Chromium-only corners, and every host browser's own
rules. Neutral means **the engine ships with orc**, identical on every OS,
so Blacksite behaves the same everywhere. That rules out any shell that
borrows the host's engine.

## Options checked

1. **Host-WebView shell (Tauri / Electron / Wails) — REJECTED as the main line.**
   Tauri/Wails render with the OS webview (WebView2 on Windows, WebKit on
   macOS/Linux) — that is the opposite of neutral, it's three engines in a
   trenchcoat. Electron ships Chromium: neutral, but Chromium, with none of
   LibreWolf's posture, and it would make Blacksite a Chromium monoculture
   app instead of a web citizen.

2. **Distribution wrap around the Gecko engine — CHOSEN for v1 (the wraparound).**
   Mozilla's official distribution mechanism: a `distribution/` folder with
   `policies.json`, plus autoconfig + a seeded profile (`user.js`).
   orc wraps **unmodified LibreWolf/Firefox engine binaries**, adds its own
   name, branding, profile folder, home (nosuchmachine.net), hardening and
   update checks. Because the engine binary itself ships in the installer,
   the same Gecko runs on Windows, macOS and Linux — neutral by
   construction, shippable now, no 30 GB build farm.
   - License: engine MPL-2.0. LibreWolf itself is MPL-2.0.
   - Trademark law (checked): modified/rebranded builds may NOT use the
     Firefox or LibreWolf name/logo as their user-facing brand. `orc` is
     its own name and mark — compliant by design. We may state in words
     that orc is built on Mozilla's open-source Gecko technology, with the
     required "not officially associated with Mozilla" line.

3. **True source fork of LibreWolf — PREPARED for v2, not the v1 gate.**
   LibreWolf's own road: fetch Firefox source, patch, build with
   `--with-branding=browser/branding/orc` and a mozconfig. Real numbers
   from LibreWolf's build docs: 2–4 h per build, ≥8 GB RAM, ~30 GB disk,
   per-OS builders, plus Windows code-signing and macOS notarization for
   installers people can actually run. That is a CI project, not a first
   ship. `fork/mozconfig` + `fork/README.md` in this repo hold the scaffold
   so v2 is a continuation, not a restart.

## The wraparound system (v1 architecture)

```
installer (per OS)
  └─ orc launcher (tiny native shim, per OS — installers/)
       ├─ engine/        LibreWolf binaries, unmodified (MPL-2.0)
       ├─ distribution/  policies.json  ← this repo, versioned
       ├─ defaults/pref/ autoconfig.js → orc.cfg
       └─ profile seed/  user.js (LibreWolf posture, orc home)
  profile (user's machine, orc's own folder — never Firefox's)
  updates: engine follows LibreWolf releases; the wrap checks
           nightwarelabz/orc releases and re-seeds distribution/
           without touching the user's profile data.
```

- **Home / first run:** https://nosuchmachine.net/ (Blacksite OS at `/`).
- **Default search:** DuckDuckGo. Google/Bing/Amazon/eBay engines removed
  by policy; user can re-add — it's their browser.
- **Blocker:** uBlock Origin force-installed by policy (LibreWolf does the same).
- **No account, no telemetry, no Pocket, no sponsored anything** — by policy,
  not by promise.
- **Blacksite inside orc:** with our own engine there is no foreign CSP/
  COEP lottery: Blacksite's headers are served as authored, phantom's
  SharedArrayBuffer ring gets cross-origin isolation on our terms, and the
  OS's Wasm/worker scope works identically for every user.

## orc inside Blacksite OS (the third surface)

Blacksite also gets an **orc app window** — a browsing room whose job is to
hand the visitor *out* to orc proper (download/install) and, for pages that
allow framing, preview them in-OS. Honest limit: the OS CSP currently has
no `frame-src`, so external frames are blocked by `default-src 'self'`;
adding `frame-src https:` to the OS scope is part of that integration and
many sites still refuse framing (X-Frame-Options) — those open in orc/
the system browser instead. The in-OS app is a door, not a fake engine.

## Naming / brand

- Name: **orc** (all lowercase) — **ORC = Orchestration** (Chase,
  2026-10-24). House: Nightware Labz.
- Mark: **the pixel orc face Chase chose** (2026-10-24) as orc's browser
  icon and main icon everywhere — see `branding/BRANDING.md` for the
  master, the transparent cutout, and the full size ladder (PNG/ICO/
  iconset). In Blacksite OS it rides as an image by deliberate exception
  to the drawn-icon house style; everywhere else it is the app icon.
- Never use Firefox/LibreWolf logos or names in orc's user-facing brand.

## Status

Prepared locally (2026-10-24): this design, validated `policies.json`,
hardening `user.js`, fork scaffold notes, installer plan.
NOT yet: engine binaries bundled, installers built, signed, or published;
in-OS orc app not yet integrated. Next steps in README.md.
