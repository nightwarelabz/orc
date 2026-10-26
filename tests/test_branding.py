import json
import re
import struct
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
UPSTREAM_NAME = ("libre" + "wolf").casefold()
OLD_ORG_NAME = ("nightware" + " labz").casefold()

TEXT_SUFFIXES = {
    ".c", ".cfg", ".desktop", ".h", ".js", ".json", ".md", ".nsi",
    ".ps1", ".py", ".sh", ".tmpl", ".yml",
}

PUBLIC_COPY = (
    "README.md",
    "DESIGN.md",
    "SECURITY.md",
    "UPDATES.md",
    "WORKSPACES.md",
    "branding/BRANDING.md",
    "installers/README.md",
    "packaging/orc.desktop",
)


def read(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


class BrandingContractTests(unittest.TestCase):
    def test_upstream_name_is_not_spelled_in_tracked_text(self):
        offenders = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts:
                continue
            if path.suffix not in TEXT_SUFFIXES and path.name != ".gitignore":
                continue
            body = path.read_text(encoding="utf-8").casefold()
            if UPSTREAM_NAME in body:
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f"upstream brand leaked into: {offenders}")

    def test_old_organization_is_not_used_as_product_brand(self):
        offenders = []
        for relative in PUBLIC_COPY:
            if OLD_ORG_NAME in read(relative).casefold():
                offenders.append(relative)
        self.assertEqual(offenders, [], f"old product branding remains in: {offenders}")

    def test_public_product_name_is_lowercase(self):
        pattern = re.compile(r"\b(?:Orc|ORC)\b")
        offenders = []
        for relative in PUBLIC_COPY:
            for line_number, line in enumerate(read(relative).splitlines(), 1):
                if pattern.search(line):
                    offenders.append(f"{relative}:{line_number}")
        self.assertEqual(offenders, [], f"non-lowercase product name in: {offenders}")

    def test_readme_leads_with_the_canonical_icon(self):
        body = read("README.md")
        self.assertIn('src="branding/orc-256.png"', body)
        self.assertIn('alt="orc"', body)
        self.assertIn("<h1 align=\"center\">orc</h1>", body)

    def test_png_ladder_has_exact_dimensions(self):
        for size in (16, 32, 64, 128, 256, 512):
            path = ROOT / "branding" / f"orc-{size}.png"
            data = path.read_bytes()
            self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n", path)
            width, height = struct.unpack(">II", data[16:24])
            self.assertEqual((width, height), (size, size), path)

    def test_platform_icon_assets_are_complete(self):
        self.assertTrue((ROOT / "branding/orc-icon-master.png").is_file())
        self.assertEqual((ROOT / "branding/orc.ico").read_bytes()[:4],
                         b"\x00\x00\x01\x00")
        iconset = ROOT / "branding/orc.iconset"
        expected = {
            "icon_16x16.png", "icon_16x16@2x.png",
            "icon_32x32.png", "icon_32x32@2x.png",
            "icon_128x128.png", "icon_128x128@2x.png",
            "icon_256x256.png", "icon_256x256@2x.png",
            "icon_512x512.png", "icon_512x512@2x.png",
        }
        self.assertTrue(expected.issubset({p.name for p in iconset.iterdir()}))

    def test_windows_uses_orc_name_and_icon(self):
        stage = read("packaging/stage-windows.ps1")
        installer = read("installers/nsis/orc.nsi")
        self.assertIn("--set-icon $orcIcon", stage)
        self.assertIn("--set-version-string 'ProductName' 'orc'", stage)
        self.assertIn('!define MUI_ICON "..\\..\\branding\\orc.ico"', installer)
        self.assertIn('!define MUI_UNICON "..\\..\\branding\\orc.ico"', installer)
        self.assertIn('VIAddVersionKey "FileDescription" "orc"', installer)
        self.assertIn('"DisplayIcon" "$INSTDIR\\orc.ico"', installer)

    def test_macos_uses_orc_name_and_icon(self):
        stage = read("packaging/stage-macos.sh")
        plist = read("packaging/Info.plist.tmpl")
        patcher = read("packaging/brand-patch.py")
        self.assertIn('"$APP/Contents/Resources/engine/orc.app" "$ICNS"', stage)
        self.assertIn("<string>orc.icns</string>", plist)
        self.assertIn('pl["CFBundleIconFile"] = "orc.icns"', patcher)
        self.assertIn('pl["CFBundleDisplayName"] = "orc"', patcher)

    def test_linux_registers_every_icon_size(self):
        desktop = read("packaging/orc.desktop")
        install = read("packaging/install.sh")
        self.assertIn("Name=orc", desktop)
        self.assertIn("Icon=orc", desktop)
        self.assertIn("for size in 16 32 64 128 256 512; do", install)
        self.assertIn('icons/orc-${size}.png', install)

    def test_manifest_templates_resolve(self):
        manifest = json.loads(read("installers/engine-manifest.json"))
        upstream = "".join(manifest["upstreamIdParts"])
        version = manifest["engineVersion"]
        source = (manifest["sourceTemplate"]
                  .replace("{upstream}", upstream)
                  .replace("{version}", version))
        self.assertTrue(source.startswith("https://"))
        self.assertTrue(source.endswith("/"))
        for artifact in manifest["artifacts"].values():
            filename = (artifact["fileTemplate"]
                        .replace("{upstream}", upstream)
                        .replace("{version}", version))
            self.assertTrue(filename.startswith(upstream + "-"))
            self.assertIn(version, filename)
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
