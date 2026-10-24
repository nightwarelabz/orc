#!/usr/bin/env python3
"""orc brand patch — applied to the staged engine at package time.

Replaces every user-visible "LibreWolf" surface inside the engine
with orc branding:
- brand strings in all locales (brand.ftl / brand.properties /
  brand.dtd) and every other display-string file in the omni.ja
  archives (error pages, dialogs, settings labels);
- the branding logos/icons, swapped for the orc face — derived at
  patch time from branding/orc-512.png with the stdlib PNG codec
  below, so no binary assets need to live beside this script;
- application.ini's app name;
- (macOS mode) the engine bundle's plist display names and its
  main executable name.

Deliberately untouched:
- license / legal material (MPL attribution stays exactly as shipped);
- code (JS logic, pref names like librewolf.*, resource paths);
- the user agent and internal identifiers.

Usage:
  brand-patch.py patch <engine_dir> <branding_dir>
  brand-patch.py audit <engine_dir>     # exit 1 if a swept display
                                        # file still names LibreWolf
  brand-patch.py macos <LibreWolf.app>  # plist names + exe rename

Stdlib only, so every CI runner can run it as-is.
"""

import base64
import io
import os
import plistlib
import re
import struct
import sys
import zipfile
import zlib

SWEEP_EXTS = (".ftl", ".properties", ".dtd", ".xhtml", ".html",
              ".htm", ".txt", ".svg")
EXCLUDE_PARTS = ("license", "legal", "thirdparty", "third-party")

BRAND_DIR_ENTRIES = "chrome/browser/content/branding/"
IMAGE_PATHS = {
    BRAND_DIR_ENTRIES + "icon16.png": ("icon", 16),
    BRAND_DIR_ENTRIES + "icon32.png": ("icon", 32),
    BRAND_DIR_ENTRIES + "icon48.png": ("icon", 48),
    BRAND_DIR_ENTRIES + "icon64.png": ("icon", 64),
    BRAND_DIR_ENTRIES + "icon128.png": ("icon", 128),
    BRAND_DIR_ENTRIES + "about-logo.png": ("icon", 192),
    BRAND_DIR_ENTRIES + "about-logo@2x.png": ("icon", 384),
    BRAND_DIR_ENTRIES + "about-logo-private.png": ("icon", 192),
    BRAND_DIR_ENTRIES + "about-logo-private@2x.png": ("icon", 384),
    BRAND_DIR_ENTRIES + "about.png": ("plate", 0),
    BRAND_DIR_ENTRIES + "about-wordmark.svg": ("wordmark", 0),
    BRAND_DIR_ENTRIES + "firefox-wordmark.svg": ("wordmark", 0),
    "chrome/browser/skin/classic/browser/preferences/category-librewolf.svg":
        ("category", 0),
}

# ---------------------------------------------------------------- PNG codec
# Minimal PNG decode (8-bit, non-interlaced) + encode, stdlib only —
# enough for our own generated ladder files.


def png_decode(data: bytes):
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    idat = bytearray()
    plte = None
    trns = None
    w = h = depth = ctype = None
    while pos < len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype, _comp, _filt, inter = struct.unpack(
                ">IIBBBBB", chunk)
            assert depth == 8 and inter == 0, "unsupported PNG shape"
        elif typ == b"PLTE":
            plte = chunk
        elif typ == b"tRNS":
            trns = chunk
        elif typ == b"IDAT":
            idat.extend(chunk)
        pos += 12 + ln
    raw = zlib.decompress(bytes(idat))
    nch = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * nch
    px = bytearray(w * h * 4)
    prev = bytearray(stride)
    ppos = 0
    for y in range(h):
        f = raw[ppos]
        ppos += 1
        line = bytearray(raw[ppos:ppos + stride])
        ppos += stride
        if f == 1:
            for i in range(nch, stride):
                line[i] = (line[i] + line[i - nch]) & 0xFF
        elif f == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif f == 3:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif f == 4:
            for i in range(stride):
                a = line[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        for x in range(w):
            o = (y * w + x) * 4
            s = x * nch
            if ctype == 6:
                px[o:o + 4] = line[s:s + 4]
            elif ctype == 2:
                px[o:o + 3] = line[s:s + 3]
                px[o + 3] = 255
            elif ctype == 0:
                px[o] = px[o + 1] = px[o + 2] = line[s]
                px[o + 3] = 255
            elif ctype == 4:
                px[o] = px[o + 1] = px[o + 2] = line[s]
                px[o + 3] = line[s + 1]
            elif ctype == 3:
                idx = line[s]
                px[o:o + 3] = plte[idx * 3:idx * 3 + 3]
                px[o + 3] = trns[idx] if trns and idx < len(trns) else 255
        prev = line
    return w, h, px


def png_encode(w: int, h: int, px: bytearray) -> bytes:
    raw = bytearray()
    stride = w * 4
    for y in range(h):
        raw.append(0)
        raw.extend(px[y * stride:(y + 1) * stride])

    def chunk(typ, body):
        c = struct.pack(">I", len(body)) + typ + body
        return c + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", zlib.compress(bytes(raw), 6)) +
            chunk(b"IEND", b""))


def resize(w, h, px, n):
    """Bilinear resize of an RGBA buffer to n x n."""
    out = bytearray(n * n * 4)
    for y in range(n):
        sy = (y + 0.5) * h / n - 0.5
        y0 = max(0, int(sy))
        y1 = min(h - 1, y0 + 1)
        fy = min(1.0, max(0.0, sy - y0))
        for x in range(n):
            sx = (x + 0.5) * w / n - 0.5
            x0 = max(0, int(sx))
            x1 = min(w - 1, x0 + 1)
            fx = min(1.0, max(0.0, sx - x0))
            o = (y * n + x) * 4
            for ch in range(4):
                v = (px[(y0 * w + x0) * 4 + ch] * (1 - fx) * (1 - fy) +
                     px[(y0 * w + x1) * 4 + ch] * fx * (1 - fy) +
                     px[(y1 * w + x0) * 4 + ch] * (1 - fx) * fy +
                     px[(y1 * w + x1) * 4 + ch] * fx * fy)
                out[o + ch] = int(v + 0.5)
    return out


def derive_assets(branding_dir: str) -> dict:
    with open(os.path.join(branding_dir, "orc-512.png"), "rb") as fh:
        w, h, px = png_decode(fh.read())
    assets = {}
    cache = {}

    def icon(n):
        if n not in cache:
            cache[n] = png_encode(n, n, resize(w, h, px, n))
        return cache[n]

    for path, (kind, n) in IMAGE_PATHS.items():
        if kind == "icon":
            assets[path] = icon(n)
        elif kind == "plate":
            pw, ph = 300, 236
            plate = bytearray(pw * ph * 4)
            for i in range(pw * ph):
                plate[i * 4:i * 4 + 4] = bytes((24, 24, 28, 255))
            face = resize(w, h, px, 170)
            ox, oy = (pw - 170) // 2, (ph - 170) // 2
            for y in range(170):
                for x in range(170):
                    s = (y * 170 + x) * 4
                    a = face[s + 3] / 255.0
                    if a == 0:
                        continue
                    d = ((oy + y) * pw + (ox + x)) * 4
                    for ch in range(3):
                        plate[d + ch] = int(face[s + ch] * a +
                                            plate[d + ch] * (1 - a))
            assets[path] = png_encode(pw, ph, plate)
        elif kind == "wordmark":
            assets[path] = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="336" '
                'height="48" viewBox="0 0 336 48"><text x="0" y="36" '
                'font-family="sans-serif" font-size="38" '
                'font-weight="bold" fill="#e8e8e8">orc</text></svg>\n'
            ).encode()
        elif kind == "category":
            b64 = base64.b64encode(icon(64)).decode()
            assets[path] = (
                '<svg xmlns="http://www.w3.org/2000/svg" width="32" '
                'height="32" viewBox="0 0 32 32"><image width="32" '
                f'height="32" href="data:image/png;base64,{b64}"/>'
                '</svg>\n').encode()
    return assets


# ---------------------------------------------------------------- patching


def swept(name: str) -> bool:
    low = name.lower()
    if any(p in low for p in EXCLUDE_PARTS):
        return False
    return low.endswith(SWEEP_EXTS)


def patch_text(name: str, text: str) -> str:
    text = text.replace("https://librewolf.net/", "https://nosuchmachine.net/")
    text = text.replace("LibreWolf", "orc")
    if name.endswith("brand.ftl"):
        text = re.sub(r"(-vendor-short-name\s*=\s*)orc",
                      r"\1Nightware Labz", text)
    elif name.endswith("brand.properties"):
        text = re.sub(r"(vendorShortName\s*=\s*)orc",
                      r"\1Nightware Labz", text)
    elif name.endswith("brand.dtd"):
        text = re.sub(r'(ENTITY\s+vendorShortName\s+")orc',
                      r"\1Nightware Labz", text)
    return text


# Branding constants that live in code files. The profile location is
# pinned by the launcher (-profile), so renaming the basename cannot
# orphan a profile; what it changes is every surface that reads the
# app identity from AppConstants (backup folder, legacy display name).
CONST_FILES = ("modules/AppConstants.sys.mjs", "BackupService.sys.mjs")


def patch_consts(name: str, text: str) -> str:
    if name.endswith("AppConstants.sys.mjs"):
        text = text.replace('MOZ_APP_BASENAME: "LibreWolf"',
                            'MOZ_APP_BASENAME: "orc"')
        text = text.replace('MOZ_APP_DISPLAYNAME_DO_NOT_USE: "LibreWolf"',
                            'MOZ_APP_DISPLAYNAME_DO_NOT_USE: "orc"')
    if name.endswith("BackupService.sys.mjs"):
        text = text.replace('"Restore LibreWolf"', '"Restore orc"')
    return text


def patch_jar(jar_path: str, assets: dict) -> int:
    changed = 0
    tmp = jar_path + ".brandtmp"
    with zipfile.ZipFile(jar_path, "r") as zin, \
            zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            new = data
            if info.filename in assets:
                new = assets[info.filename]
            elif info.filename.endswith(CONST_FILES):
                try:
                    new = patch_consts(
                        info.filename,
                        data.decode("utf-8")).encode("utf-8")
                except UnicodeDecodeError:
                    new = data
            elif swept(info.filename):
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError:
                    text = None
                if text is not None:
                    new = patch_text(info.filename, text).encode("utf-8")
            if new != data:
                changed += 1
            ni = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            ni.internal_attr = info.internal_attr
            ni.create_system = info.create_system
            zout.writestr(ni, new)
    os.replace(tmp, jar_path)
    return changed


def find_jars(engine_dir: str):
    return [p for p in (os.path.join(engine_dir, "browser", "omni.ja"),
                        os.path.join(engine_dir, "omni.ja"))
            if os.path.isfile(p)]


def do_patch(engine_dir: str, branding_dir: str) -> int:
    assets = derive_assets(branding_dir)
    total = 0
    for jar in find_jars(engine_dir):
        n = patch_jar(jar, assets)
        print(f"brand-patch: {jar}: {n} entries rebranded")
        total += n
    # Loose display text outside the jars (updater.ini, the cfg).
    for root, _dirs, files in os.walk(engine_dir):
        if any(p in root.lower() for p in EXCLUDE_PARTS):
            continue
        for fn in files:
            if not fn.lower().endswith((".ini", ".cfg")):
                continue
            if fn in ("precomplete", "removed-files"):
                continue
            path = os.path.join(root, fn)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    body = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            body2 = patch_text(fn, body)
            if body2 != body:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(body2)
                print(f"brand-patch: loose file rebranded: {path}")
                total += 1
    ini = os.path.join(engine_dir, "application.ini")
    if os.path.isfile(ini):
        with open(ini, "r", encoding="utf-8") as fh:
            body = fh.read()
        body2 = body.replace("Name=LibreWolf", "Name=orc")
        if body2 != body:
            with open(ini, "w", encoding="utf-8") as fh:
                fh.write(body2)
            print("brand-patch: application.ini Name=orc")
            total += 1
    if total == 0:
        print("brand-patch: NOTHING changed — wrong engine dir?",
              file=sys.stderr)
        return 1
    return do_audit(engine_dir)


# Strings that are identity plumbing, not display copy. They stay:
# bundle identifiers and designated requirements (changing them breaks
# the identity they name), license/legal files, install bookkeeping
# lists, and compiled-in directory defaults read only on a bare
# engine run (the launcher always pins -profile and the brand name
# shown by the OS comes from the plists + AppConstants, both swept).
DISPLAY_PATTERNS = ("LibreWolf Update", "LibreWolf 158", "uses Apple Events",
                    "will be able to", "needs access", "needs this access",
                    "reinstall LibreWolf", "Running LibreWolf",
                    "Restore LibreWolf", "MOZ_APP_BASENAME",
                    "MOZ_APP_DISPLAYNAME", "LibreWolf GPU Helper",
                    "LibreWolf Media Plugin Helper",
                    "GetInfoString")


def _classify_hit(path: str, ctx: str) -> bool:
    """True = a display surface still shows the old name."""
    low = path.lower()
    if any(p in low for p in EXCLUDE_PARTS):
        return False
    if os.path.basename(path) in ("precomplete", "removed-files"):
        return False
    if "_codesignature" in low:
        return False
    if "net.librewolf" in ctx:
        rest = ctx.replace("net.librewolf", "")
        if "LibreWolf" not in rest and "anchor apple" not in ctx:
            return False
    if "anchor apple" in ctx or "certificate" in ctx:
        return False
    if path.endswith((".plist", ".ini", ".cfg", ".txt")):
        return True
    if ".ja:" in path:  # an omni entry: display if it is a swept kind
        entry = path.rsplit(":", 1)[-1].lower()
        if entry.endswith(SWEEP_EXTS) or entry.endswith(CONST_FILES):
            return True
    if any(pat in ctx for pat in DISPLAY_PATTERNS):
        return True
    return False


def do_audit(engine_dir: str) -> int:
    leftovers = []
    internal = 0
    # omni archives + loose files: one byte census over everything.
    targets = []
    for jar in find_jars(engine_dir):
        with zipfile.ZipFile(jar, "r") as z:
            for info in z.infolist():
                targets.append((f"{jar}:{info.filename}",
                                z.read(info.filename)))
    for root, _dirs, files in os.walk(engine_dir):
        for fn in files:
            path = os.path.join(root, fn)
            if path in find_jars(engine_dir):
                continue
            try:
                with open(path, "rb") as fh:
                    targets.append((path, fh.read()))
            except OSError:
                continue
    for path, data in targets:
        if b"LibreWolf" not in data:
            continue
        text = data.decode("utf-8", "replace")
        for ln in text.splitlines():
            if "LibreWolf" in ln:
                if _classify_hit(path, ln.strip()):
                    leftovers.append(f"{path}: {ln.strip()[:90]}")
                else:
                    internal += 1
    if leftovers:
        print("brand-audit: LibreWolf still DISPLAYED in:", file=sys.stderr)
        for x in leftovers[:25]:
            print("  " + x, file=sys.stderr)
        return 1
    print(f"brand-audit: clean — no display surface names LibreWolf "
          f"({internal} internal identifier mentions left, by design)")
    return 0


def _sweep_plist_values(obj, key=None):
    """Replace the brand in every display string of a plist value.
    Identity plumbing is left alone: bundle identifiers and code
    requirement strings must keep pointing at the same identity."""
    if isinstance(obj, str):
        if key == "CFBundleIdentifier" or "net.librewolf" in obj:
            return obj
        if "anchor apple" in obj or "certificate" in obj:
            return obj
        return obj.replace("LibreWolf", "orc")
    if isinstance(obj, dict):
        return {k: _sweep_plist_values(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sweep_plist_values(v, key) for v in obj]
    return obj


def do_macos(app: str) -> int:
    """Full macOS pass over the engine bundle: every plist display
    string (usage descriptions, GetInfoString, helper names), the
    helper executables' names, and the two user-facing error strings
    compiled into XUL. Runs before the seal, like everything else."""
    bundles = [app]
    for root, dirs, _files in os.walk(app):
        for d in dirs:
            if d.endswith(".app"):
                bundles.append(os.path.join(root, d))
    for bundle in bundles:
        plist = os.path.join(bundle, "Contents", "Info.plist")
        if not os.path.isfile(plist):
            continue
        with open(plist, "rb") as fh:
            pl = plistlib.load(fh)
        pl = _sweep_plist_values(pl)
        if bundle == app and "CFBundleDisplayName" not in pl:
            pl["CFBundleDisplayName"] = "orc"
        # helper executables take the new name their plist now claims
        exe = pl.get("CFBundleExecutable")
        macos_dir = os.path.join(bundle, "Contents", "MacOS")
        if isinstance(exe, str) and exe.startswith("orc ") and os.path.isdir(macos_dir):
            for fn in os.listdir(macos_dir):
                if fn.startswith("LibreWolf ") and fn[10:] == exe[4:]:
                    os.replace(os.path.join(macos_dir, fn),
                               os.path.join(macos_dir, exe))
                    print(f"brand-patch: helper executable -> {exe}")
        with open(plist, "wb") as fh:
            plistlib.dump(pl, fh)
    # main executable rename (Contents/MacOS/librewolf -> orc)
    plist = os.path.join(app, "Contents", "Info.plist")
    with open(plist, "rb") as fh:
        pl = plistlib.load(fh)
    exe_dir = os.path.join(app, "Contents", "MacOS")
    old_exe = os.path.join(exe_dir, "librewolf")
    if os.path.isfile(old_exe):
        os.replace(old_exe, os.path.join(exe_dir, "orc"))
        pl["CFBundleExecutable"] = "orc"
        with open(plist, "wb") as fh:
            plistlib.dump(pl, fh)
        print("brand-patch: macOS engine executable -> orc")
    # user-facing error strings compiled into XUL (the profile-dir
    # table entry beside them is internal and stays).
    xul = os.path.join(exe_dir, "XUL")
    if os.path.isfile(xul):
        with open(xul, "rb") as fh:
            blob = fh.read()
        for old, new in ((b"reinstall LibreWolf?",
                          b"reinstall orc?" + b"\x00" * 6),
                         (b"Running LibreWolf as root",
                          b"Running orc" + b"\x00" * 6 + b" as root")):
            if old in blob:
                blob = blob.replace(old, new)
                print(f"brand-patch: XUL error string rebranded: {old[:28]}")
        with open(xul, "wb") as fh:
            fh.write(blob)
    print(f"brand-patch: macOS pass complete ({len(bundles)} bundles)")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "patch":
        sys.exit(do_patch(sys.argv[2], sys.argv[3]))
    if len(sys.argv) >= 3 and sys.argv[1] == "audit":
        sys.exit(do_audit(sys.argv[2]))
    if len(sys.argv) >= 3 and sys.argv[1] == "macos":
        sys.exit(do_macos(sys.argv[2]))
    print(__doc__)
    sys.exit(2)
