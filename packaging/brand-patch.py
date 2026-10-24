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


def do_audit(engine_dir: str) -> int:
    leftovers = []
    for jar in find_jars(engine_dir):
        with zipfile.ZipFile(jar, "r") as z:
            for info in z.infolist():
                if info.filename in IMAGE_PATHS or not swept(info.filename):
                    continue
                try:
                    text = z.read(info.filename).decode("utf-8")
                except UnicodeDecodeError:
                    continue
                if "LibreWolf" in text:
                    leftovers.append(f"{jar}:{info.filename}")
    ini = os.path.join(engine_dir, "application.ini")
    if os.path.isfile(ini) and "Name=LibreWolf" in open(ini).read():
        leftovers.append(f"{ini}:Name")
    if leftovers:
        print("brand-audit: LibreWolf still displayed in:", file=sys.stderr)
        for x in leftovers[:20]:
            print("  " + x, file=sys.stderr)
        return 1
    print("brand-audit: clean — no display file names LibreWolf")
    return 0


def do_macos(app: str) -> int:
    """Rename the engine bundle's display names + main executable."""
    touched = 0
    for root, dirs, _files in os.walk(app):
        for d in dirs:
            if not d.endswith(".app"):
                continue
            plist = os.path.join(root, d, "Contents", "Info.plist")
            if not os.path.isfile(plist):
                continue
            with open(plist, "rb") as fh:
                pl = plistlib.load(fh)
            dirty = False
            for key in ("CFBundleName", "CFBundleDisplayName"):
                val = pl.get(key)
                if isinstance(val, str) and "LibreWolf" in val:
                    pl[key] = val.replace("LibreWolf", "orc")
                    dirty = True
            if dirty:
                with open(plist, "wb") as fh:
                    plistlib.dump(pl, fh)
                touched += 1
    # The top bundle itself (os.walk visits children only).
    plist = os.path.join(app, "Contents", "Info.plist")
    with open(plist, "rb") as fh:
        pl = plistlib.load(fh)
    for key in ("CFBundleName", "CFBundleDisplayName"):
        val = pl.get(key)
        if isinstance(val, str) and "LibreWolf" in val:
            pl[key] = val.replace("LibreWolf", "orc")
    exe_dir = os.path.join(app, "Contents", "MacOS")
    old_exe = os.path.join(exe_dir, "librewolf")
    if os.path.isfile(old_exe):
        os.replace(old_exe, os.path.join(exe_dir, "orc"))
        pl["CFBundleExecutable"] = "orc"
        print("brand-patch: macOS engine executable -> orc")
    with open(plist, "wb") as fh:
        plistlib.dump(pl, fh)
    print(f"brand-patch: macOS plist names -> orc ({touched} helper bundles)")
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
