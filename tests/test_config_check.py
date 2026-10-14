"""Tests for skills/burn/scripts/config_check.py. Run: python -m unittest discover tests"""

import copy
import importlib.util
import io
import tempfile
import tomllib
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "skills/burn/templates/config.toml"
spec = importlib.util.spec_from_file_location("config_check", ROOT / "skills/burn/scripts/config_check.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)


def base():
    with open(TEMPLATE, "rb") as fh:
        return tomllib.load(fh)


def errors_for(cfg, **kw):
    return cc.check(cfg, **kw)[0]


class TemplateTests(unittest.TestCase):
    def test_shipped_template_passes(self):
        errors, _ = cc.check(base())
        self.assertEqual(errors, [])

    def test_cli_exit_codes(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(cc.main([str(TEMPLATE)]), 0)
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "config.toml"
            bad.write_text(TEMPLATE.read_text(encoding="utf-8").replace(
                "target_end_pct = 95", "target_end_pct = 120"), encoding="utf-8")
            with redirect_stdout(out):
                self.assertEqual(cc.main([str(bad)]), 1)
            self.assertIn("budget.target_end_pct", out.getvalue())
            broken = Path(tmp) / "broken.toml"
            broken.write_text("platform = [", encoding="utf-8")
            with redirect_stdout(out):
                self.assertEqual(cc.main([str(broken)]), 1)
            with redirect_stdout(out):
                self.assertEqual(cc.main([str(Path(tmp) / "missing.toml")]), 1)


class BudgetTests(unittest.TestCase):
    def test_target_range(self):
        for bad in (49, 100, "95", True):
            cfg = base()
            cfg["budget"]["target_end_pct"] = bad
            self.assertTrue(errors_for(cfg), bad)
        for good in (50, 80, 99):
            cfg = base()
            cfg["budget"]["target_end_pct"] = good
            cfg["budget"]["hard_stop_pct"] = 99
            self.assertEqual(errors_for(cfg), [], good)

    def test_hard_stop_must_be_at_least_target_and_at_most_99(self):
        cfg = base()
        cfg["budget"]["target_end_pct"] = 96
        cfg["budget"]["hard_stop_pct"] = 95
        self.assertTrue(any("hard_stop_pct" in e for e in errors_for(cfg)))
        cfg["budget"]["hard_stop_pct"] = 100
        self.assertTrue(any("hard_stop_pct" in e for e in errors_for(cfg)))
        cfg["budget"]["hard_stop_pct"] = 96
        self.assertEqual(errors_for(cfg), [])

    def test_missing_key(self):
        cfg = base()
        del cfg["budget"]["five_hour_stop_pct"]
        self.assertTrue(any("five_hour_stop_pct: missing" in e for e in errors_for(cfg)))


class ChoiceAndScheduleTests(unittest.TestCase):
    def test_bad_choices(self):
        for section, key, value in [(None, "platform", "cursor"), ("git", "strategy", "yolo"),
                                    ("autonomy", "mode", "full"), ("notify", "channel", "sms"),
                                    ("self_improve", "mode", "auto")]:
            cfg = base()
            (cfg[section] if section else cfg)[key] = value
            self.assertTrue(errors_for(cfg), key)

    def test_schedule(self):
        for bad in ([], [0], [200], [20, 20], "36,20,6"):
            cfg = base()
            cfg["schedule"]["hours_before_reset"] = bad
            self.assertTrue(errors_for(cfg), bad)
        cfg = base()
        cfg["schedule"]["hours_before_reset"] = [48, 12.5]
        self.assertEqual(errors_for(cfg), [])


class AssetsTests(unittest.TestCase):
    def test_section_is_optional(self):
        cfg = base()
        cfg.pop("assets", None)
        self.assertEqual(errors_for(cfg), [])

    def test_valid_values(self):
        for mode in ("auto", "on", "off"):
            cfg = base()
            cfg["assets"] = {"codex_images": mode, "codex_max_weekly_pct": 60}
            self.assertEqual(errors_for(cfg), [], mode)

    def test_bad_values(self):
        for bad in ({"codex_images": "sometimes"}, {"codex_max_weekly_pct": 5},
                    {"codex_max_weekly_pct": 150}, {"codex_max_weekly_pct": True},
                    {"codex_max_weekly_pct": "80"}):
            cfg = base()
            cfg["assets"] = bad
            self.assertTrue(errors_for(cfg), bad)


class SecretTests(unittest.TestCase):
    def test_credential_must_be_a_location(self):
        cfg = base()
        cfg["providers"]["cloudflare"]["credential"] = "abc123def456"
        self.assertTrue(any("providers.cloudflare.credential" in e for e in errors_for(cfg)))

    def test_secret_values_are_caught(self):
        cfg = base()
        cfg["notify"]["webhook_url_from"] = "https://discord.com/api/webhooks/123/abcdef"
        errs = errors_for(cfg)
        self.assertTrue(any("webhook_url_from" in e for e in errs))
        cfg = base()
        cfg["github_owner"] = "ghp_" + "a" * 36
        self.assertTrue(any("looks like a secret" in e for e in errors_for(cfg)))

    def test_notify_locations_are_env_or_file_only(self):
        for bad in ("cli:gh", "keychain:burn/webhook", "env:", "env:1BAD", "file:", "plain-value"):
            cfg = base()
            cfg["notify"]["webhook_url_from"] = bad
            self.assertTrue(any("notify.webhook_url_from" in e for e in errors_for(cfg)), bad)
        cfg = base()
        cfg["notify"]["ntfy_token_from"] = "keychain:ntfy/token"
        self.assertTrue(any("notify.ntfy_token_from" in e for e in errors_for(cfg)))
        for good in ("env:BURN_WEBHOOK_URL", "file:~/.burn-rate/webhook.txt"):
            cfg = base()
            cfg["notify"]["webhook_url_from"] = good
            self.assertEqual(errors_for(cfg), [], good)

    def test_file_locations_may_contain_spaces(self):
        cfg = base()
        cfg["notify"]["pushover_user_from"] = r"file:C:\Users\Jane Doe\.burn-rate\pushover user.txt"
        cfg["notify"]["pushover_token_from"] = "file:/home/jane/My Secrets/pushover-token"
        cfg["providers"]["cloudflare"]["account_id_from"] = "file:~/Cloud Stuff/account id"
        self.assertEqual(errors_for(cfg), [])
        cfg["providers"]["cloudflare"]["credential"] = "env:HAS SPACE"
        self.assertTrue(any("providers.cloudflare.credential" in e for e in errors_for(cfg)))

    def test_ntfy_needs_topic(self):
        cfg = base()
        cfg["notify"]["channel"] = "ntfy"
        self.assertTrue(errors_for(cfg))
        cfg["notify"]["ntfy_topic"] = "burn-7f3k2q9x4m"
        self.assertEqual(errors_for(cfg), [])


class SelfImproveTests(unittest.TestCase):
    def test_maintainer_needs_a_burn_rate_clone(self):
        cfg = base()
        cfg["self_improve"]["mode"] = "maintainer"
        self.assertTrue(errors_for(cfg))
        with tempfile.TemporaryDirectory() as tmp:
            cfg["self_improve"]["skills_repo_path"] = tmp
            self.assertTrue(any("not a git clone" in e for e in errors_for(cfg)))
            (Path(tmp) / ".git").mkdir()
            (Path(tmp) / "skills/burn").mkdir(parents=True)
            (Path(tmp) / "skills/burn/SKILL.md").write_text("x", encoding="utf-8")
            (Path(tmp) / "tests").mkdir()
            (Path(tmp) / "tests/lint_skills.py").write_text("x", encoding="utf-8")
            self.assertEqual(errors_for(cfg), [])

    def test_upstream_repo_shape(self):
        cfg = base()
        cfg["self_improve"]["upstream_issues"] = True
        self.assertTrue(errors_for(cfg))
        cfg["self_improve"]["upstream_repo"] = "jdoe/burn-rate"
        self.assertEqual(errors_for(cfg), [])


class GatedChangeTests(unittest.TestCase):
    def test_cap_raise_is_gated(self):
        old = base()
        new = copy.deepcopy(old)
        new["providers"]["cloudflare"]["monthly_cap_usd"] = 5
        self.assertTrue(any("gated change" in e for e in errors_for(new, previous=old)))
        errors, warnings = cc.check(new, previous=old, allow_gated=True)
        self.assertEqual(errors, [])
        self.assertTrue(any("monthly_cap_usd" in w and "NEEDS_HUMAN" in w for w in warnings))

    def test_lowering_is_not_gated(self):
        old = base()
        old["providers"]["cloudflare"]["monthly_cap_usd"] = 5
        new = copy.deepcopy(old)
        new["providers"]["cloudflare"]["monthly_cap_usd"] = 0
        new["budget"]["hard_stop_pct"] = 96
        self.assertEqual(errors_for(new, previous=old), [])

    def test_live_mode_and_hard_stop_are_gated(self):
        old = base()
        new = copy.deepcopy(old)
        new["providers"]["stripe"]["live_mode_approved"] = True
        new["budget"]["hard_stop_pct"] = 99
        errs = errors_for(new, previous=old)
        self.assertEqual(len([e for e in errs if "gated change" in e]), 2)


if __name__ == "__main__":
    unittest.main()
