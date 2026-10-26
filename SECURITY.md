# orc — security posture

This document states what orc does, what it refuses to do, and where its
boundaries are. If it disagrees with the shipped files, the files are the bug.

## The build

- Every engine artifact is pinned in `installers/engine-manifest.json` and
  verified twice before packaging: against the repository SHA-256 and the
  publisher's release sidecar.
- Engine updates arrive only through a newly verified orc release.
- Packages are built by the public workflow in this repository and release
  assets include `SHA256SUMS.txt`.
- v1 packages have no paid signing identity. The macOS bundle is ad-hoc sealed
  and verified in CI but is not Developer-ID signed or notarized. Windows
  SmartScreen also warns for unsigned releases.
- The packaging audit rejects any user-visible upstream name that survives
  rebranding. Platform checks verify that the canonical orc icon is wired into
  browser artwork, executables, app bundles, installers, and desktop surfaces.

## The browser

- Telemetry, studies, Pocket, and sponsored content are disabled by policy.
- HTTPS-only mode and strict tracking protection are enabled, including
  cryptomining, fingerprinting, and email-tracking protection.
- Total Cookie Protection is enabled.
- `privacy.resistFingerprinting` remains off by deliberate full-functionality
  policy because its normalized canvas, timezone, and timing behavior breaks
  some sites. Users may enable it in Settings.
- DNS-over-HTTPS is enabled with system-resolver fallback for captive portals
  and networks where encrypted DNS is unavailable.
- DuckDuckGo is the default search engine and suggestions are off.
- uBlock Origin is force-installed from Mozilla Add-ons and updates through
  Mozilla's signed extension channel.
- Form history is off. Cache and form data are sanitized at shutdown; browsing
  history and cookies remain under user control.
- Media, Widevine/EME, and WebGL are enabled. orc disables the upstream
  per-site WebGL prompt in autoconfig so available graphics support behaves as
  available support instead of failing until a temporary grant is made.
- The launcher uses a fixed relative engine path, invokes no shell, and
  forwards engine arguments verbatim after consuming orc workspace options.
  Engine profile selectors are reserved so they cannot escape the selected
  orc context.
- The default profile is stored in orc's own directory. Named parent/child
  workspaces use independent profiles and never copy credentials or state from
  their parent.
- Workspace names are canonicalized and limited to 16 levels. Named workspaces
  use Gecko's `-no-remote` behavior and normal profile locking.
- First-run settings are published completely before the engine starts without
  overwriting an existing `user.js`. POSIX profile directories use mode
  `0700` and new settings files use `0600`.

## The nest

- orc preserves Gecko's origin, framing, certificate, CSP, COOP, and COEP
  checks. Shipping a consistent engine does not grant pages permission to
  frame sites that forbid embedding.
- The pinned-engine CI fixture verifies four nested document levels, isolated
  workers, Wasm, shared memory, independent workspace storage, and a denied
  frame.
- The Blacksite lens is GET-only. It sends and relays no cookies, rejects
  private and loopback targets, revalidates every redirect, caps body size,
  and serves rewritten pages under a sandbox CSP without
  `allow-same-origin`.

## Reporting

Open an issue in this repository. orc has no telemetry or private diagnostic
upload channel.
