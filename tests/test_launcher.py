"""Black-box checks against the compiled launcher and an argv-recording engine.

No browser download, pip packages, or changes to the real user profile.
Run: python -m unittest discover -s tests -v
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"


def compile_c(source, target, definitions=()):
    if WINDOWS:
        args = ["cl", "/nologo", "/W4", "/WX", "/utf-8", "/O2",
                "/D_CRT_SECURE_NO_WARNINGS", *["/D" + d for d in definitions],
                str(source), "/Fe:" + str(target)]
    else:
        args = [os.environ.get("CC", "cc"), "-std=c11", "-Wall", "-Wextra",
                "-Werror", "-O2", *["-D" + d for d in definitions],
                str(source), "-o", str(target)]
    result = subprocess.run(args, cwd=target.parent, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"compiler failed:\n{result.stdout}\n{result.stderr}")


class LauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix="orc-build-")
        cls.binary = Path(cls.build.name) / ("orc.exe" if WINDOWS else "orc")
        cls.probe = Path(cls.build.name) / ("probe.exe" if WINDOWS else "probe")
        compile_c(ROOT / "launcher/launcher.c", cls.binary,
                  ('ENGINE_REL="engine/orc.exe"' if WINDOWS else 'ENGINE_REL="engine/orc"',
                   'SEED_REL="profile-seed/user.js"'))
        compile_c(ROOT / "tests/engine_probe.c", cls.probe)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="orc-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.install = self.root / "orc install ü"
        self.install.mkdir()
        self.launcher = self.install / self.binary.name
        shutil.copy2(self.binary, self.launcher)
        (self.install / "engine").mkdir()
        shutil.copy2(self.probe, self.install / "engine" / ("orc.exe" if WINDOWS else "orc"))
        seed = self.install / "profile-seed/user.js"
        seed.parent.mkdir()
        seed.write_text('// first-run seed\nuser_pref("orc.test", true);\n', encoding="utf-8")
        self.seed = seed
        self.capture = self.root / "capture.json"
        self.home = self.root / "User home ü"
        self.home.mkdir()
        self.env = os.environ.copy()
        for key in ("ORC_WORKSPACE", "ORC_WORKSPACE_DEPTH", "XDG_DATA_HOME", "APPDATA", "USERPROFILE"):
            self.env.pop(key, None)
        self.env.update(HOME=str(self.home), USERPROFILE=str(self.home),
                        APPDATA=str(self.home / "Roaming"), ORC_TEST_CAPTURE=str(self.capture))
        if WINDOWS:
            self.data = self.home / "Roaming/orc"
        elif MACOS:
            self.data = self.home / "Library/Application Support/orc"
        else:
            self.data = self.home / ".local/share/orc"

    def run_orc(self, *args, success=True):
        result = subprocess.run([str(self.launcher), *args], env=self.env,
                                cwd=self.root, capture_output=True, text=True, encoding="utf-8")
        if success:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def info(self, *args):
        return json.loads(self.run_orc(*args, "--orc-workspace-info").stdout)

    def launch(self, *args):
        self.capture.unlink(missing_ok=True)
        self.run_orc(*args)
        # Windows deliberately detaches the GUI engine; wait for its report.
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                return json.loads(self.capture.read_text(encoding="utf-8"))
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(0.02)
        self.fail("engine did not receive the launch")

    def test_default_profile_and_arguments_are_preserved(self):
        args = ["--headless", "https://nosuchmachine.net/?a=1&b=2", "", 'a"b',
                "space in a value", "trailing\\", 'slash\\"quote', "日本語", "--", "--orc-literal"]
        report = self.launch(*args)
        self.assertEqual(report["argv"][1:], ["-profile", str(self.data / "profile"), *args])
        self.assertEqual(report["workspace"], "/")
        self.assertEqual(report["depth"], "0")
        self.assertEqual((self.data / "profile/user.js").read_bytes(), self.seed.read_bytes())

    def test_branch_has_separate_profile_and_lineage(self):
        report = self.launch("--orc-workspace", "Blacksite/Research", "https://nosuchmachine.net/")
        profile = self.data / "workspaces/blacksite/children/research/profile"
        self.assertEqual(report["argv"][1:], ["-profile", str(profile), "-no-remote", "https://nosuchmachine.net/"])
        self.assertEqual(report["workspace"], "blacksite/research")
        self.assertEqual(report["depth"], "2")
        info = self.info("--orc-workspace", "blacksite/research")
        self.assertEqual(info, dict(workspace="blacksite/research", parent="blacksite", depth=2,
                                   max_depth=16, profile=str(profile)))
        self.assertFalse((self.data / "profile").exists())

    def test_child_parent_and_environment_context(self):
        self.env["ORC_WORKSPACE"] = "Blacksite"
        self.env["ORC_WORKSPACE_DEPTH"] = "999"  # recomputed, never trusted
        info = self.info("--orc-child", "Research", "--orc-child", "Experiment", "--orc-parent")
        self.assertEqual(info["workspace"], "blacksite/research")
        report = self.launch("--orc-child", "research")
        self.assertEqual((report["workspace"], report["depth"]), ("blacksite/research", "2"))
        self.assertEqual(self.info("--orc-parent")["workspace"], "/")
        self.assertEqual(self.info("--orc-workspace", "/", "--orc-parent")["parent"], None)

    def test_inspection_is_read_only_and_needs_no_engine(self):
        shutil.rmtree(self.install / "engine")
        info = self.info("--orc-workspace", "a/b")
        self.assertEqual(info["parent"], "a")
        self.assertFalse(self.data.exists())
        self.assertIn("--orc-child", self.run_orc("--orc-help").stdout)

    def test_existing_seed_and_profiles_are_not_overwritten(self):
        self.launch()
        userjs = self.data / "profile/user.js"
        userjs.write_text("// my settings", encoding="utf-8")
        (self.data / "profile/prefs.js").write_text("// private state", encoding="utf-8")
        self.launch("--orc-workspace", "a")
        self.launch()
        self.assertEqual(userjs.read_text(encoding="utf-8"), "// my settings")
        self.assertEqual((self.data / "profile/prefs.js").read_text(encoding="utf-8"), "// private state")
        self.assertEqual((self.data / "workspaces/a/profile/user.js").read_bytes(), self.seed.read_bytes())

    def test_reserved_profile_name_cannot_overlap_parent_storage(self):
        parent = Path(self.info("--orc-workspace", "a")["profile"])
        child = Path(self.info("--orc-workspace", "a/profile")["profile"])
        self.assertNotIn(parent, child.parents)
        self.assertNotIn(child, parent.parents)

    def test_invalid_names_are_rejected_before_writes(self):
        invalid = ["", ".", "..", "a/../b", "/absolute", "a/", "a//b", "a\\b", "a.b",
                   "-a", "_a", "a:b", "a b", "CON", "a/NuL", "com1", "LPT9", "é", "a" * 49,
                   "/".join(["x"] * 17)]
        for name in invalid:
            with self.subTest(name=name):
                self.run_orc("--orc-workspace", name, success=False)
        self.assertFalse(self.data.exists())
        self.assertFalse(self.capture.exists())

    def test_depth_and_segment_bounds(self):
        # The longest name at every level can exceed macOS PATH_MAX once
        # the home directory is included. Check the independent limits.
        name = "/".join(["x"] * 16)
        self.assertEqual(self.info("--orc-workspace", name)["depth"], 16)
        self.assertEqual(self.info("--orc-workspace", "x" * 48)["depth"], 1)
        self.run_orc("--orc-workspace", name, "--orc-child", "overflow", success=False)
        self.run_orc("--orc-child", "two/levels", success=False)
        self.assertEqual(self.info("--orc-child", "a-1_b")["workspace"], "a-1_b")

    def test_engine_profile_overrides_are_rejected(self):
        options = ["-profile", "--profile", "--PROFILE=x", "-P", "-ProfileManager", "--createprofile"]
        if WINDOWS:
            options.append("/profile")
        for option in options:
            with self.subTest(option=option):
                self.run_orc(option, "foreign", success=False)
                self.run_orc("--", option, "foreign", success=False)
        self.assertFalse(self.data.exists())

    def test_bad_environment_can_be_reset_explicitly(self):
        self.env["ORC_WORKSPACE"] = "../../foreign"
        self.run_orc("--orc-workspace-info", success=False)
        self.assertEqual(self.info("--orc-workspace", "/")["workspace"], "/")

    def test_unknown_and_missing_options_fail(self):
        for args in [("--orc-typo",), ("--orc-workspace",), ("--orc-child",)]:
            self.run_orc(*args, success=False)
        self.assertFalse(self.data.exists())

    def test_missing_engine_and_missing_seed_fail(self):
        self.seed.unlink()
        self.run_orc(success=False)
        self.assertFalse(self.capture.exists())
        shutil.rmtree(self.install / "engine")
        self.run_orc(success=False)

    def test_profile_path_collision_fails(self):
        self.data.mkdir(parents=True)
        (self.data / "profile").write_text("not a directory", encoding="utf-8")
        self.run_orc(success=False)
        self.assertFalse(self.capture.exists())

    def test_concurrent_first_runs_observe_a_complete_seed(self):
        seed = b"// large first-run settings file\n" * 32768
        self.seed.write_bytes(seed)
        processes = []
        paths = []
        for i in range(12):
            capture = self.root / f"concurrent-{i}.json"
            env = dict(self.env, ORC_TEST_CAPTURE=str(capture))
            processes.append(subprocess.Popen([str(self.launcher), "--orc-workspace", "shared"],
                                             env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE))
            paths.append(capture)
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, (stdout, stderr))
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
                break
            except (FileNotFoundError, json.JSONDecodeError):
                time.sleep(0.02)
        else:
            self.fail("concurrent engines did not report")
        self.assertEqual([r["seed_bytes"] for r in reports], [len(seed)] * len(paths))
        self.assertEqual((self.data / "workspaces/shared/profile/user.js").read_bytes(), seed)
        self.assertEqual(list(self.data.rglob("*.orc-*")), [])

    def test_failed_seed_can_be_retried_without_partial_settings(self):
        self.seed.unlink()
        self.seed.mkdir()
        self.run_orc(success=False)
        self.assertFalse((self.data / "profile/user.js").exists())
        self.seed.rmdir()
        self.seed.write_bytes(b"// recovered installation\n")
        self.assertEqual(self.launch()["seed_bytes"], self.seed.stat().st_size)

    def test_existing_profile_needs_no_seed_after_first_run(self):
        self.launch()
        self.seed.unlink()
        self.launch()

    def test_existing_settings_directory_is_rejected(self):
        (self.data / "profile/user.js").mkdir(parents=True)
        self.run_orc(success=False)
        self.assertFalse(self.capture.exists())

    def test_quotes_and_backslashes_survive_engine_forwarding(self):
        args = []
        for count in range(9):
            args += ["\\" * count, "before" + "\\" * count + '"after',
                     "spaces then " + "\\" * count]
        self.assertEqual(self.launch(*args)["argv"][3:], args)

    @unittest.skipUnless(WINDOWS, "Windows profile migration")
    def test_legacy_windows_profile_root_moves_without_losing_data(self):
        legacy = self.home / "Roaming/Nightware Labz/orc"
        marker = legacy / "profile/keep-me.txt"
        marker.parent.mkdir(parents=True)
        marker.write_text("existing profile data", encoding="utf-8")

        info = self.info()
        self.assertEqual(info["profile"], str(legacy / "profile"))
        self.assertTrue(marker.is_file())

        launched = self.launch()
        self.assertEqual(launched["profile"], str(self.data / "profile"))
        self.assertEqual((self.data / "profile/keep-me.txt").read_text(
            encoding="utf-8"), "existing profile data")
        self.assertFalse(legacy.exists())

    @unittest.skipIf(WINDOWS or MACOS, "XDG is Linux-specific")
    def test_xdg_home_is_respected_and_relative_values_are_ignored(self):
        xdg = self.home / "separate data"
        self.env["XDG_DATA_HOME"] = str(xdg)
        self.assertEqual(self.info()["profile"], str(xdg / "orc/profile"))
        self.env["XDG_DATA_HOME"] = "relative/path"
        self.assertEqual(self.info()["profile"], str(self.data / "profile"))

    @unittest.skipIf(WINDOWS, "POSIX permissions")
    def test_new_profile_is_private_even_with_permissive_umask(self):
        old = os.umask(0)
        try:
            self.launch("--orc-workspace", "a")
        finally:
            os.umask(old)
        profile = self.data / "workspaces/a/profile"
        self.assertEqual(profile.stat().st_mode & 0o777, 0o700)
        self.assertEqual((profile / "user.js").stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
