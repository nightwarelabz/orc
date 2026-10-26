# orc branding

## One name

The product name is **orc**.

- Always write it as lowercase `orc`.
- Do not expand it as an acronym.
- Do not attach another product name, company name, or “browser system” label
  to the displayed name.
- Generic prose may describe what orc does, but the brand itself remains
  exactly `orc`.

## One mark

The pixel orc face is the sole product mark. Do not substitute an upstream
logo, a company emblem, a drawn approximation, or a text-only placeholder
where an application icon is supported.

The canonical assets are:

- `orc-master-original.jpg` — original source art, preserved unchanged.
- `orc-icon-master.png` — transparent, padded master used for derivatives.
- `orc-512.png`, `orc-256.png`, `orc-128.png`, `orc-64.png`,
  `orc-32.png`, and `orc-16.png` — raster size ladder.
- `orc.ico` — Windows executable, installer, uninstaller, and shortcut icon.
- `orc.iconset/` — macOS source set used to build `orc.icns`.

Derivatives may change size or container format only. Do not redraw the face.

## Default color theme

The browser chrome opens in orc's dark green theme. Its charcoal-green base
(`#172117`), toolbar green (`#202d1e`), selected-tab green (`#344925`), and
focus green (`#7c9537`) are sampled from the canonical face artwork. The
theme styles browser chrome only; web pages keep their own colors. The
per-profile stylesheet is `profile/chrome/userChrome.css` and is seeded only
when the profile does not already have one.

## Required surfaces

| Surface | Name | Mark |
|---|---|---|
| Browser chrome and About pages | `orc` | orc face |
| Executables and app bundles | `orc` | orc face |
| Installer and uninstaller | `orc` | orc face |
| Start menu, desktop, taskbar, dock, and app launcher | `orc` | orc face |
| Private browsing and settings branding | `orc` | orc face |
| Release titles and package metadata | `orc` | orc face where supported |
| Repository README and project documentation | `orc` | orc face |

Packaging must fail if a user-visible upstream name or logo survives. The
repository tests also enforce the lowercase name and required platform icon
wiring so branding cannot silently drift.
