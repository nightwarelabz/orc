# orc — security posture

What orc does, what it refuses to do, and where the sharp edges are.
Plain statements; if a line here ever disagrees with the shipped
files, the files are wrong and this document is the bug report.

## The build

- The engine is **pinned** (LibreWolf 158.0.1-2) and every artifact is
  verified twice before packaging: against the sha256 recorded in
  `installers/engine-manifest.json` AND against the official
  dl.librewolf.net sidecar. Engine binaries are **unmodified**.
- The engine never self-updates out from under the pin. Engine
  updates arrive as new orc releases, re-verified the same way.
- Packages are built by the public workflow in this repo from the
  public sources in this repo. Release assets carry `SHA256SUMS.txt`.
- v1 packages carry **no paid identity**: the macOS bundle is
  ad-hoc sealed and verified in CI (structurally valid — never the
  "damaged" verdict), but not Developer-ID signed or notarized, so
  first open is right-click > Open. Windows SmartScreen will warn
  likewise. That is stated, not hidden.

## The browser

- Telemetry, studies, Pocket, sponsored content: off by policy.
- HTTPS-only mode on; tracking protection strict (incl. cryptomining,
  fingerprinting, email tracking); Total Cookie Protection on.
- `privacy.resistFingerprinting` is **off by deliberate choice**
  (Chase's full-functionality ruling): RFP normalizes canvas,
  timezone and timers in ways that break real sites. Tracking
  protection and Total Cookie Protection remain strict, and RFP is
  one toggle away in Settings for anyone who wants LibreWolf's
  harder posture.
- DNS-over-HTTPS is on, with fallback to the system resolver when
  DoH is unreachable (a fail-closed posture broke real networks —
  captive portals and filtered resolvers — and full functionality
  won the trade; stated here, not hidden).
- Search is DuckDuckGo by default with suggestions off; Google, Bing,
  Amazon and eBay search plugins are removed.
- uBlock Origin is force-installed from Mozilla Add-ons (Mozilla-
  signed, and thereafter updated through Mozilla's signed channel —
  deliberately not a bundled, stale-able copy).
- Form history off; cache and form data sanitized on shutdown;
  history and cookies are the user's and are kept.
- Media is fully enabled, including Widevine/EME: the proprietary
  Google CDM downloads on first use, as in Firefox. A browser that
  silently cannot play the web's media is not fully functional.
- The launcher is a small native program: fixed relative engine
  path, no shell, arguments forwarded verbatim, and a profile that
  lives in orc's own folder — separate from any Firefox/LibreWolf
  profile, seeded once and never overwritten.

## The nest (nosuchmachine.net inside orc)

- The site is a static page plus narrow, guarded functions. Its bench
  probes pass a shared SSRF guard (public targets only, DNS-checked,
  re-validated on every redirect hop).
- The in-OS orc room frames pages two ways: credentialless frames
  where the host browser supports them, and a same-origin **lens**
  elsewhere (Safari). The lens is GET-only, sends and relays no
  cookies, refuses private/loopback targets and this site itself,
  caps body size, and serves rewritten pages under a sandbox CSP
  without `allow-same-origin`.

## Reporting

Open an issue in this repo. There is no telemetry to opt out of and
no security contact form funnel — the repo is the contact.
