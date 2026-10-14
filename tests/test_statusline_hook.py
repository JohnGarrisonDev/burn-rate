"""Tests for skills/burn/scripts/claude_statusline_hook.py. Run: python -m unittest discover tests"""

import importlib.util
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("hook", ROOT / "skills/burn/scripts/claude_statusline_hook.py")
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class TestRunWrapped(unittest.TestCase):
    def run_with(self, os_name, bash):
        with mock.patch.object(hook.os, "name", os_name), \
                mock.patch.object(hook, "windows_bash", return_value=bash), \
                mock.patch.object(hook.subprocess, "run") as run:
            hook.run_wrapped("echo hi", "{}")
        return run.call_args

    def test_windows_uses_bash_when_available(self):
        args, kw = self.run_with("nt", r"C:\Program Files\Git\bin\bash.exe")
        self.assertEqual(args[0], [r"C:\Program Files\Git\bin\bash.exe", "-c", "echo hi"])
        self.assertNotIn("shell", kw)
        self.assertEqual(kw["input"], "{}")

    def test_windows_without_bash_uses_the_shell(self):
        args, kw = self.run_with("nt", None)
        self.assertEqual(args[0], "echo hi")
        self.assertTrue(kw["shell"])

    def test_posix_uses_the_shell(self):
        args, kw = self.run_with("posix", "/bin/bash")
        self.assertEqual(args[0], "echo hi")
        self.assertTrue(kw["shell"])

    def test_wsl_launcher_is_not_used(self):
        with mock.patch.object(hook.shutil, "which", return_value=r"C:\Windows\System32\bash.exe"), \
                mock.patch.dict(hook.os.environ, {"SystemRoot": r"C:\Windows"}):
            self.assertIsNone(hook.windows_bash())


if __name__ == "__main__":
    unittest.main()
