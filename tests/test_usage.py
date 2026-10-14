"""Tests for skills/burn/scripts/usage.py. Run: python -m unittest discover tests"""

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("usage", ROOT / "skills/burn/scripts/usage.py")
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)

NOW = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
RESET = datetime(2026, 10, 17, 13, 59, 59, tzinfo=timezone.utc)  # 26h after NOW
CFG = {"budget": {"target_end_pct": 95, "hard_stop_pct": 97, "five_hour_stop_pct": 90},
       "schedule": {"hours_before_reset": [36, 20, 6]}}


def u(weekly, five=0.0, reset=RESET):
    return usage.finish("provided", NOW, (weekly, reset), (five, None), "", now=NOW)


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

    def test_skips_lines_that_are_not_objects(self):
        ts = datetime.now(timezone.utc)
        self.write_session({"secondary": {"used_percent": 44.0, "window_minutes": 10080}}, usage.iso(ts))
        f = next((Path(os.environ["CODEX_HOME"]) / "sessions").rglob("*.jsonl"))
        with f.open("a", encoding="utf-8") as fh:
            fh.write('["rate_limits"]\n"rate_limits"\n')
        r = usage.read_codex()
        self.assertTrue(r["ok"])
        self.assertEqual(r["weekly"]["used_pct"], 44.0)


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

    def test_cache_that_is_not_an_object(self):
        cache = Path(os.environ["BURN_RATE_HOME"]) / "cache"
        cache.mkdir(parents=True)
        (cache / "claude-usage.json").write_text("[1, 2]")
        self.assertFalse(usage.read_claude_statusline()["ok"])


class TestAutoByPlatform(EnvCase):
    """Both sources present: the platform decides, not the age of the snapshot."""

    def setUp(self):
        super().setUp()
        now = datetime.now(timezone.utc)
        reset = int((now + timedelta(days=2)).timestamp())
        # Claude cache: fresh, 40%.
        cache = Path(os.environ["BURN_RATE_HOME"]) / "cache"
        cache.mkdir(parents=True)
        (cache / "claude-usage.json").write_text(json.dumps({
            "captured_at": usage.iso(now),
            "rate_limits": {"seven_day": {"used_percentage": 40.0, "resets_at": reset}}}))
        # Codex session: three hours old, 70%.
        d = Path(os.environ["CODEX_HOME"]) / "sessions/2026/10/16"
        d.mkdir(parents=True)
        rec = {"timestamp": usage.iso(now - timedelta(hours=3)),
               "payload": {"rate_limits": {"secondary": {"used_percent": 70.0, "window_minutes": 10080,
                                                         "resets_at": reset}}}}
        (d / "rollout-1.jsonl").write_text(json.dumps(rec) + "\n")

    def test_codex_reads_codex_even_when_older(self):
        r = usage.read("auto", "codex")
        self.assertEqual(r["source"], "codex-sessions")
        self.assertEqual(r["weekly"]["used_pct"], 70.0)

    def test_claude_cli_reads_statusline(self):
        r = usage.read("auto", "claude-cli")
        self.assertEqual(r["source"], "claude-statusline")
        self.assertEqual(r["weekly"]["used_pct"], 40.0)

    def test_claude_desktop_falls_back_to_statusline_with_a_note(self):
        r = usage.read("auto", "claude-desktop")
        self.assertEqual(r["source"], "claude-statusline")
        self.assertIn("get_usage", r["note"])

    def test_no_platform_freshest_wins(self):
        self.assertEqual(usage.read("auto")["source"], "claude-statusline")

    def test_codex_never_borrows_claude_numbers(self):
        for f in (Path(os.environ["CODEX_HOME"]) / "sessions").rglob("*.jsonl"):
            f.unlink()
        r = usage.read("auto", "codex")
        self.assertEqual(r["source"], "declared")
        self.assertIsNone(r["weekly"]["used_pct"])

    def test_main_uses_config_platform(self):
        (Path(os.environ["BURN_RATE_HOME"]) / "config.toml").write_text('platform = "codex"\n')
        out = io.StringIO()
        with redirect_stdout(out):
            usage.main([])
        self.assertEqual(json.loads(out.getvalue())["source"], "codex-sessions")


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

    def test_stop_new_work_keeps_a_handoff_reserve(self):
        p = usage.plan(u(35.0), CFG, now=NOW)
        self.assertEqual(p["stop_new_work_pct"], 52.0)  # 55 - 3
        self.assertEqual(p["handoff_reserve_pts"], 3.0)

    def test_last_run_reserves_more_for_recap_and_retro(self):
        p = usage.plan(u(70.0), CFG, now=RESET - timedelta(hours=5))
        self.assertEqual(p["stop_new_work_pct"], 89.0)  # 95 - 6
        self.assertEqual(p["handoff_reserve_pts"], 6.0)

    def test_stop_new_work_never_below_current_usage(self):
        p = usage.plan(u(92.0), CFG, now=RESET - timedelta(hours=5))
        self.assertEqual(p["stop_weekly_pct"], 95.0)
        self.assertEqual(p["stop_new_work_pct"], 92.0)

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
        self.assertIsNone(p["stop_weekly_pct"])
        self.assertIsNone(p["stop_new_work_pct"])

    def test_known_usage_unknown_reset_still_respects_the_stops(self):
        # what --weekly without --resets-at produces
        cfg = {"budget": {"target_end_pct": 95, "hard_stop_pct": 97}}
        p = usage.plan(u(96.0, reset=None), cfg, now=NOW)
        self.assertEqual(p["mode"], "time-boxed")
        self.assertFalse(p["go"])
        p = usage.plan(u(60.0, reset=None), cfg, now=NOW)
        self.assertTrue(p["go"])
        self.assertEqual(p["stop_weekly_pct"], 95.0)
        self.assertEqual(p["stop_new_work_pct"], 92.0)

    def test_hard_stop_below_target_wins_without_reset(self):
        cfg = {"budget": {"target_end_pct": 95, "hard_stop_pct": 90}}
        self.assertFalse(usage.plan(u(91.0, reset=None), cfg, now=NOW)["go"])
        self.assertEqual(usage.plan(u(50.0, reset=None), cfg, now=NOW)["stop_weekly_pct"], 90.0)

    def test_main_weekly_without_resets_at(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"BURN_RATE_HOME": tmp}):
            out = io.StringIO()
            with redirect_stdout(out):
                usage.main(["plan", "--weekly", "98"])
        p = json.loads(out.getvalue())
        self.assertFalse(p["go"])
        self.assertEqual(p["mode"], "time-boxed")

    def test_old_snapshot_rolls_reset_into_the_future(self):
        now = datetime.now(timezone.utc)
        r = usage.finish("provided", now - timedelta(days=20), (50.0, now - timedelta(days=16)), (None, None), "")
        reset = usage.parse_time(r["weekly"]["resets_at"])
        self.assertGreater(reset, now)
        self.assertLessEqual(reset - now, timedelta(days=7))
        self.assertEqual(r["weekly"]["used_pct"], 0.0)

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


class TestGate(unittest.TestCase):
    CFG = {"schedule": {"hours_before_reset": [36, 20, 6]},
           "budget": {"target_end_pct": 95, "hard_stop_pct": 97, "five_hour_stop_pct": 90}}

    def u(self, weekly, reset, active=True):
        r = usage.finish("provided", NOW, (weekly, reset), (0.0, None), "", now=NOW)
        r["window_active"] = active
        return r

    def test_nothing_due_early_in_the_week(self):
        res, _ = usage.gate(self.u(10.0, NOW + timedelta(days=5)), self.CFG, "codex", now=NOW)
        self.assertFalse(res["run"])
        self.assertIn("next at", res["reason"])

    def test_slot_due_runs_once(self):
        reset = NOW + timedelta(hours=30)
        res, st = usage.gate(self.u(10.0, reset), self.CFG, "codex", now=NOW)
        self.assertTrue(res["run"])
        self.assertEqual(res["slot"], 36)
        again, _ = usage.gate(self.u(12.0, reset), self.CFG, "codex", now=NOW + timedelta(hours=1), state=st)
        self.assertFalse(again["run"])

    def test_missed_slots_collapse_into_one_run(self):
        res, st = usage.gate(self.u(10.0, NOW + timedelta(hours=5)), self.CFG, "codex", now=NOW)
        self.assertTrue(res["run"])
        self.assertEqual(st["done"], [36, 20, 6])

    def test_new_reset_starts_fresh_slots(self):
        reset = NOW + timedelta(hours=30)
        _, st = usage.gate(self.u(10.0, reset), self.CFG, "codex", now=NOW)
        later = NOW + timedelta(days=6, hours=20)
        res, _ = usage.gate(self.u(0.0, reset + timedelta(days=7)), self.CFG, "codex", now=later, state=st)
        self.assertTrue(res["run"])

    def test_inactive_codex_window_starts_one(self):
        res, st = usage.gate(self.u(0.0, NOW + timedelta(days=3), active=False), self.CFG, "codex", now=NOW)
        self.assertTrue(res["run"])
        again, _ = usage.gate(self.u(0.0, NOW + timedelta(days=3), active=False), self.CFG, "codex",
                              now=NOW + timedelta(hours=1), state=st)
        self.assertFalse(again["run"])

    def test_past_target_doesnt_run(self):
        res, _ = usage.gate(self.u(96.0, NOW + timedelta(hours=5)), self.CFG, "codex", now=NOW)
        self.assertFalse(res["run"])

    def test_desktop_never_uses_gate(self):
        res, _ = usage.gate(self.u(10.0, NOW + timedelta(hours=5)), self.CFG, "claude-desktop", now=NOW)
        self.assertFalse(res["run"])

    def test_no_reading_doesnt_run(self):
        res, _ = usage.gate(usage.empty("declared", ""), self.CFG, "claude-cli", now=NOW)
        self.assertFalse(res["run"])


class TestPreview(unittest.TestCase):
    def test_preview_counts_only_scheduled_slots(self):
        p = usage.plan(u(17.0, reset=NOW + timedelta(hours=70)), CFG, now=NOW, preview=True)
        self.assertEqual(p["runs_left_including_this"], 3)


if __name__ == "__main__":
    unittest.main()
