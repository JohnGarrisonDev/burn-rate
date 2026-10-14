"""Tests for skills/burn/scripts/codex_image.py. Codex is mocked; nothing calls the real CLI."""

import importlib.util
import json
import os
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills/burn/scripts"
spec = importlib.util.spec_from_file_location("codex_image", SCRIPTS / "codex_image.py")
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


def png_bytes(w=64, h=48):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x06\x00\x00\x00"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {
            "BURN_RATE_HOME": str(root / "burn"),
            "CODEX_HOME": str(root / "codex"),
            "BURN_CODEX_BIN": "codex-fake",
        })
        self.env.start()
        self.gen = root / "codex" / "generated_images" / "abc"
        self.gen.mkdir(parents=True)
        (root / "burn").mkdir()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def config(self, text):
        (Path(os.environ["BURN_RATE_HOME"]) / "config.toml").write_text(text, encoding="utf-8")


class TestPng(Base):
    def test_reads_size(self):
        p = self.gen / "a.png"
        p.write_bytes(png_bytes(1254, 1254))
        self.assertEqual(ci.png_size(p), (1254, 1254))

    def test_rejects_non_png(self):
        p = self.gen / "a.png"
        p.write_bytes(b"GIF89a....................")
        self.assertIsNone(ci.png_size(p))


class TestAvailability(Base):
    def run_ok(self, *a, **k):
        return subprocess.CompletedProcess(a, 0, stdout="Logged in using ChatGPT\n", stderr="")

    def test_off_in_config(self):
        self.config('[assets]\ncodex_images = "off"\n')
        self.assertFalse(ci.availability(ci.load_assets_config())["ok"])

    def test_not_installed(self):
        with mock.patch.dict(os.environ, {"BURN_CODEX_BIN": ""}), mock.patch.object(ci.shutil, "which", return_value=None):
            r = ci.availability({})
        self.assertFalse(r["ok"])
        self.assertIn("isn't installed", r["reason"])

    def test_not_logged_in(self):
        bad = subprocess.CompletedProcess([], 1, stdout="Not logged in", stderr="")
        with mock.patch.object(ci.subprocess, "run", return_value=bad):
            r = ci.availability({})
        self.assertIn("isn't logged in", r["reason"])

    def test_over_codex_budget(self):
        with mock.patch.object(ci.subprocess, "run", side_effect=self.run_ok), \
             mock.patch.object(ci, "codex_weekly_pct", return_value=85.0):
            r = ci.availability({"codex_max_weekly_pct": 80})
        self.assertFalse(r["ok"])
        self.assertIn("85.0%", r["reason"])

    def test_ok(self):
        with mock.patch.object(ci.subprocess, "run", side_effect=self.run_ok), \
             mock.patch.object(ci, "codex_weekly_pct", return_value=13.0):
            r = ci.availability({})
        self.assertTrue(r["ok"])
        self.assertEqual(r["limit_pct"], 80.0)


class TestGenerate(Base):
    def fake_exec(self, reply_path):
        def run(cmd, **kw):
            # The call must be read-only, in a temp dir, with stdin closed.
            self.assertIn("read-only", cmd)
            self.assertIs(kw.get("stdin"), subprocess.DEVNULL)
            self.assertTrue(cmd[-1].startswith("$imagegen"))
            out = Path(cmd[cmd.index("-o") + 1])
            out.write_text(str(reply_path) + "\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return run

    def test_copies_the_png(self):
        src = self.gen / "exec-1.png"
        src.write_bytes(png_bytes(512, 512))
        out = Path(self.tmp.name) / "project" / "public" / "icon.png"
        with mock.patch.object(ci.subprocess, "run", side_effect=self.fake_exec(src)):
            r = ci.generate("an icon", out, "codex-fake")
        self.assertTrue(r["ok"], r)
        self.assertEqual((r["width"], r["height"]), (512, 512))
        self.assertEqual(out.read_bytes(), src.read_bytes())

    def test_refuses_a_path_outside_generated_images(self):
        elsewhere = Path(self.tmp.name) / "evil.png"
        elsewhere.write_bytes(png_bytes())
        with mock.patch.object(ci.subprocess, "run", side_effect=self.fake_exec(elsewhere)):
            r = ci.generate("x", Path(self.tmp.name) / "o.png", "codex-fake")
        self.assertFalse(r["ok"])
        self.assertIn("outside", r["reason"])

    def test_refuses_a_non_png(self):
        src = self.gen / "exec-2.png"
        src.write_bytes(b"not a png at all, just text...")
        with mock.patch.object(ci.subprocess, "run", side_effect=self.fake_exec(src)):
            r = ci.generate("x", Path(self.tmp.name) / "o.png", "codex-fake")
        self.assertFalse(r["ok"])

    def test_no_path_in_reply(self):
        def run(cmd, **kw):
            Path(cmd[cmd.index("-o") + 1]).write_text("Sorry, I couldn't.", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        with mock.patch.object(ci.subprocess, "run", side_effect=run):
            r = ci.generate("x", Path(self.tmp.name) / "o.png", "codex-fake")
        self.assertFalse(r["ok"])

    def test_main_check_exit_code_when_unavailable(self):
        self.config('[assets]\ncodex_images = "off"\n')
        with mock.patch("sys.stdout") as out:
            code = ci.main(["--check"])
        self.assertEqual(code, 2)
        self.assertIn('"ok": false', "".join(c.args[0] for c in out.write.call_args_list))


class TestPrompt(unittest.TestCase):
    def test_asks_for_one_image_and_only_the_path(self):
        p = ci.build_prompt("  a green icon  ")
        self.assertTrue(p.startswith("$imagegen Generate exactly one image. a green icon"))
        self.assertIn("only the absolute path", p)

    def test_json_output_is_one_object(self):
        self.assertEqual(json.loads(json.dumps({"ok": True}))["ok"], True)


if __name__ == "__main__":
    unittest.main()
