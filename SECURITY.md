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
- WebGL is on, without LibreWolf's per-site permission prompt: the
  engine orc ships (LibreWolf 158) blocks every WebGL context until
  the site is granted permission from a small address-bar icon, and
  the grant is temporary — pages then report "WebGL is not
  available" in a browser that has it enabled. orc turns the prompt
  off in the engine's autoconfig (`librewolf.webgl.prompt=false`),
  so WebGL simply works, as in Firefox. The fingerprinting exposure
  WebGL carries is the same trade as the RFP choice above: stated,
  not hidden.
- The launcher is a small native program: fixed relative engine
  path, no shell, engine arguments forwarded verbatim after consuming
  Orc's workspace options. Engine profile selectors are reserved so
  they cannot redirect a launch outside the selected Orc context.
- The default profile stays in Orc's existing folder, separate from
  any Firefox/LibreWolf profile. Named parent/child workspaces have
  independent profiles; they do not copy credentials or state from
  their parent. Names are canonicalized and bounded to 16 levels.
  This separates browser state, not OS process privileges.
- Named workspaces use Gecko's `-no-remote` flag and profile locks:
  one branch cannot hand its launch to a running parent, and two
  processes cannot open the same profile concurrently. Selecting a
  parent does not close or focus existing browser windows.
- First-run settings are published completely before the engine starts,
  without overwriting a pre-existing `user.js`. On POSIX systems, new
  profile directories use mode `0700` and new settings files `0600`.
  Existing profile permissions and user settings are preserved.

## The nest (nosuchmachine.net inside orc)

- Orc preserves Gecko's origin, framing, certificate, CSP, COOP, and
  COEP checks. Shipping the engine makes its capabilities consistent;
  it does not make cross-origin isolation automatic or grant pages
  permission to frame sites that forbid embedding. The pinned-engine
  CI fixture verifies four nested document levels, isolated workers,
  Wasm, shared memory, independent workspace storage, and a denied frame.
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
