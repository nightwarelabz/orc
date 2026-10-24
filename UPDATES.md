# How orc updates itself

Design (Chase's directive, 2026-10-24): automatic updates, allocated
dynamically in the background, applied by a single button that
carries a symbol and no words.

## Principles

- The engine never self-updates off the verified pin. App update
  stays off in policy: an upstream engine update would move orc to
  an unverified build and, on macOS, break the bundle seal.
- An orc update is an orc release. The machinery below delivers it.

## Flow

1. **Check.** On launch, and every 12 hours in-session, the bundled
   update extension asks GitHub for the latest orc release and
   compares versions.
2. **Allocate.** If a newer release exists, the extension downloads
   this platform's asset plus `SHA256SUMS.txt` in the background
   into an `orc-update` staging folder. No prompt, no blocking; the
   browser keeps working.
3. **Verify.** The native host (below) checks the staged asset's
   SHA-256 against the sums file and, on macOS, verifies the staged
   bundle's seal. A failed check deletes the stage silently.
4. **Signal.** The toolbar button is icon-only: two chasing arrows,
   no label, no tooltip text. Dim means current. Lit means a
   verified update is staged.
5. **Apply.** Pressing the button is the whole interaction: the
   browser closes, the host swaps the staged build in, and orc
   relaunches on it. If the new build fails to launch once, the
   host restores the previous tree it kept aside.

## Pieces

- **Extension** (`extension/`): the check, the background download,
  and the button. It holds no power beyond signalling.
- **Native host**: the orc launcher binary doubles as the Mozilla
  native-messaging host (`orc --native-host`) — it verifies,
  swaps, and relaunches. The launcher re-registers the host
  manifest at the standard per-OS Mozilla location on every start,
  so registration self-heals.
- **Apply per platform**: Linux and Windows-zip installs swap the
  `orc/` tree in place (user-writable installs). A Windows NSIS
  install under Program Files applies via the staged installer
  with elevation. macOS swaps the `.app` bundle at its existing
  path after its ad-hoc seal verifies.
