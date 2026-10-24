# orc branding

- **Name:** orc — **ORC = Orchestration** (Chase, 2026-10-24). Written
  lowercase: `orc`. Expanded form: "ORC — Orchestration".
- **Mark:** the pixel orc face Chase chose on 2026-10-24 as orc's
  browser icon and main icon everywhere. Green, tusked, unimpressed —
  the browser that guards the gate.
- **Files here:**
  - `orc-master-original.jpg` — Chase's uploaded art, untouched.
  - `orc-icon-master.png` — the master icon: white background removed
    (flood-fill from the edges; the face's own outline is untouched),
    centered on a transparent square with 6% padding.
  - `orc-512/256/128/64/32/16.png` — the size ladder, Lanczos from the master.
  - `orc.ico` — Windows icon (16–256 ladder inside).
  - `orc.iconset/` — macOS iconset; `iconutil -c icns orc.iconset` on a
    Mac produces `orc.icns` for the app bundle / Firefox branding dir.
  - The v2 fork takes these into `browser/branding/orc/` (default16/32/48,
    default256, mozicon128, VisualElements logos derive from the ladder).
- **On the site:** Blacksite OS serves `public/orc/orc-64.png` (desktop,
  taskbar, launcher — via a deliberate exception in the house icon set),
  `orc-128.png`, and `orc-256.png` (the orc room's hero plate).
- **Never:** Firefox or LibreWolf logos/names as orc's brand (trademark),
  and no redrawing the face — derivatives are sizes and formats only.
