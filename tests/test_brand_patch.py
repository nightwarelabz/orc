import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "orc_brand_patch", ROOT / "packaging/brand-patch.py")
PATCHER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PATCHER)


class BrandPatchTests(unittest.TestCase):
    def test_display_name_replacement_is_case_insensitive(self):
        upstream = PATCHER.UPSTREAM_NAME
        source = (
            f"brand-short-name = {upstream}\n"
            f"-vendor-short-name = {upstream}\n"
            f"lowercase = {upstream.lower()}\n"
            f"uppercase = {upstream.upper()}\n"
        )
        patched = PATCHER.patch_text("brand.ftl", source)
        self.assertNotIn(upstream.casefold(), patched.casefold())
        self.assertEqual(patched.casefold().count("orc"), 4)

    def test_compiled_string_replacements_preserve_length(self):
        upstream = PATCHER.UPSTREAM_NAME.casefold().encode()
        for old, new in PATCHER.XUL_STRINGS:
            self.assertEqual(len(old), len(new))
            self.assertNotIn(upstream, new.lower())
            self.assertIn(b"orc", new)

    def test_assets_use_the_canonical_orc_face_and_wordmark(self):
        assets = PATCHER.derive_assets(str(ROOT / "branding"))
        base = PATCHER.BRAND_DIR_ENTRIES
        for name in ("icon16.png", "icon64.png", "icon128.png",
                     "about-logo.png", "about-logo-private.png"):
            self.assertEqual(assets[base + name][:8],
                             b"\x89PNG\r\n\x1a\n")
        self.assertIn(b">orc</text>", assets[base + "about-wordmark.svg"])
        self.assertIn(b"data:image/png;base64,",
                      assets[base + "about-logo.svg"])

    def test_macos_bundle_identity_is_rebranded(self):
        source = PATCHER.UPSTREAM_BUNDLE_ID + ".helper"
        result = PATCHER._sweep_plist_values(
            {"CFBundleIdentifier": source, "CFBundleDisplayName": "orc"})
        self.assertEqual(result["CFBundleIdentifier"],
                         "net.nosuchmachine.orc.engine.helper")
        self.assertNotIn(PATCHER.UPSTREAM_BUNDLE_ID,
                         result["CFBundleIdentifier"])


if __name__ == "__main__":
    unittest.main()
