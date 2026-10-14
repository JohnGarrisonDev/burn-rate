"""Tests for skills/burn/scripts/usage.py. Run: python -m unittest discover tests"""

import importlib.util
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("usage", ROOT / "skills/burn/scripts/usage.py")
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
RESET = datetime(2026, 10, 17, 13, 59, 59, tzinfo=timezone.utc)  # 26h after NOW
CFG = {"budget": {"target_end_pct": 95, "hard_stop_pct": 97, "five_hour_stop_pct": 90},
       "schedule": {"hours_before_reset": [36, 20, 6]}}


def u(weekly, five=0.0, reset=RESET):
    return usage.finish("provided", NOW, (weekly, reset), (five, None), "")


class EnvCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = {k: os.environ.get(k) for k in ("BURN_RATE_HOME", "CODEX_HOME")}
        os.environ["BURN_RATE_HOME"] = str(Path(self.tmp.name) / "burn")
        os.environ["CODEX_HOME"] = str(Path(self.tmp.name) / "codex")

    def tearDown(self):
        for k, v in self.old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()


class TestCodex(EnvCase):
    def write_session(self, rate_limits, ts):
        d = Path(os.environ["CODEX_HOME"]) / "sessions/2026/10/16"
        d.mkdir(parents=True)
        rec = {"timestamp": ts, "type": "event_msg",
               "payload": {"type": "token_count", "info": {}, "rate_limits": rate_limits}}
        (d / "rollout-1.jsonl").write_text('{"type":"session_meta"}\n' + json.dumps(rec) + "\n")

    def test_reads_primary_and_secondary_by_window(self):
        ts = datetime.now(timezone.utc)
        self.write_session({
            "primary": {"used_percent": 12.0, "window_minutes": 300,
                        "resets_at": int((ts + timedelta(hours=2)).timestamp())},
            "secondary": {"used_percent": 61.5, "window_minutes": 10080,
                          "resets_in_seconds": 3600 * 30},
        }, usage.iso(ts))
        r = usage.read_codex()
        self.assertTrue(r["ok"])
        self.assertEqual(r["weekly"]["used_pct"], 61.5)
        self.assertEqual(r["five_hour"]["used_pct"], 12.0)
        self.assertIsNotNone(r["weekly"]["resets_at"])

    def test_missing_folder(self):
        r = usage.read_codex()
        self.assertFalse(r["ok"])


class TestClaudeCache(EnvCase):
    def test_reads_cache(self):
        cache = Path(os.environ["BURN_RATE_HOME"]) / "cache"
        cache.mkdir(parents=True)
        reset = int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp())
        (cache / "claude-usage.json").write_text(json.dumps({
            "captured_at": usage.iso(datetime.now(timezone.utc)),
            "rate_limits": {"five_hour": {"used_percentage": 5, "resets_at": reset - 100000},
                            "seven_day": {"used_percentage": 40.2, "resets_at": reset}}}))
        r = usage.read_claude_statusline()
        self.assertTrue(r["ok"])
        self.assertEqual(r["weekly"]["used_pct"], 40.2)

    def test_auto_falls_back_to_declared(self):
        r = usage.read("auto")
        self.assertEqual(r["source"], "declared")
        self.assertFalse(r["ok"])


class TestPlan(unittest.TestCase):
    def test_splits_room_across_remaining_runs(self):
        # 26h left: the 20h and 6h slots are still ahead, so 3 runs including this one.
        p = usage.plan(u(35.0), CFG, now=NOW)
        self.assertTrue(p["go"])
        self.assertEqual(p["runs_left_including_this"], 3)
        self.assertEqual(p["stop_weekly_pct"], 55.0)
        self.assertFalse(p["is_last_run_of_week"])

    def test_last_run_takes_everything_to_target(self):
        p = usage.plan(u(70.0), CFG, now=RESET - timedelta(hours=5))
        self.assertEqual(p["runs_left_including_this"], 1)
        self.assertTrue(p["is_last_run_of_week"])
        self.assertEqual(p["stop_weekly_pct"], 95.0)

    def test_no_go_past_target(self):
        p = usage.plan(u(96.0), CFG, now=NOW)
        self.assertFalse(p["go"])

    def test_no_go_when_five_hour_is_full(self):
        p = usage.plan(u(30.0, five=92.0), CFG, now=NOW)
        self.assertFalse(p["go"])

    def test_time_boxed_without_usage(self):
        p = usage.plan(usage.empty("declared", ""), {"budget": {"declared_minutes_per_run": 45}}, now=NOW)
        self.assertEqual(p["mode"], "time-boxed")
        self.assertEqual(p["minutes"], 45)

    def test_window_that_already_reset_reads_zero(self):
        now = datetime.now(timezone.utc)
        r = usage.finish("provided", now, (80.0, now - timedelta(minutes=1)), (None, None), "")
        self.assertEqual(r["weekly"]["used_pct"], 0.0)


class TestParseTime(unittest.TestCase):
    def test_formats(self):
        a = usage.parse_time("2026-10-17T13:59:59Z")
        self.assertEqual(usage.parse_time(int(a.timestamp())), a)
        self.assertEqual(usage.parse_time(int(a.timestamp()) * 1000), a)
        self.assertIsNone(usage.parse_time("nonsense"))


if __name__ == "__main__":
    unittest.main()
