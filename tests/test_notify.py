"""Tests for skills/burn/scripts/notify.py. No network. Run: python -m unittest discover tests"""

import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("notify", ROOT / "skills/burn/scripts/notify.py")
notify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notify)


def cfg(platform="claude-cli", **n):
    return {"platform": platform, "notify": n}


class TestSecretDetection(unittest.TestCase):
    def test_flags_common_secrets(self):
        samples = [
            "key is sk-ant-api03-abcdefghijklmnopqrstuvwxyz",
            "use sk_live_51Habcdefghijkl",
            "test key rk_test_abcdefgh12345",
            "ghp_abcdefghijklmnopqrstuvwxyz0123456789",
            "gho_abcdefghijklmnopqrstuvwxyz0123",
            "github_pat_11ABCDEFG0123456789_abcdefghij",
            "xoxb-1234567890-abcdefghij",
            "AKIAIOSFODNN7EXAMPLE",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "token=3f9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c",
            "api_key: 'dGhpcyBpcyBhIHNlY3JldCB2YWx1ZTEyMw=='",
            "postgres://app:hunter2secret@db.example.com/app",
        ]
        for s in samples:
            with self.subTest(s=s):
                self.assertIsNotNone(notify.find_secret(s))

    def test_flags_webhook_urls(self):
        samples = [
            "hook is https://discord.com/api/webhooks/1234567890/AbCdEf-ghIJ",
            "https://discordapp.com/api/webhooks/1/x",
            "https://ptb.discord.com/api/webhooks/1/x",
            "posted to https://hooks.slack.com/services/T000/B000/XXXXXXXX",
        ]
        for s in samples:
            with self.subTest(s=s):
                self.assertEqual(notify.find_secret(s), "webhook URL")
        for s in ("see https://discord.com/channels/1/2", "https://slack.com/help/articles/1",
                  "Set up a Discord webhook (BURN_WEBHOOK_URL)"):
            with self.subTest(s=s):
                self.assertIsNone(notify.find_secret(s))

    def test_main_refuses_a_webhook_url_in_the_message(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = notify.main(["--title", "t", "--message",
                                "new hook: https://hooks.slack.com/services/T0/B0/abcdef"])
        self.assertEqual(code, 1)
        self.assertNotIn("hooks.slack.com", out.getvalue())

    def test_ignores_normal_messages(self):
        samples = [
            "NH-007 (cost): Cloudflare D1 will hit its free row limit in ~2 weeks",
            "Burn run 2/3: shipped CSV export + signup fix. Week at 78%.",
            "task-scheduler ran; see https://github.com/jdoe/invoice-snap/blob/main/burn/NEEDS_HUMAN.md",
            "Primary key: users_table_identifier_column",
            "Set CLOUDFLARE_API_TOKEN with Workers + D1 edit scope",
        ]
        for s in samples:
            with self.subTest(s=s):
                self.assertIsNone(notify.find_secret(s))

    def test_main_refuses_and_exits_1(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = notify.main(["--title", "t", "--message", "ghp_abcdefghijklmnopqrstuvwxyz0123456789"])
        self.assertEqual(code, 1)
        self.assertNotIn("ghp_abc", out.getvalue())
        self.assertIn("refused", out.getvalue())


class TestLocations(unittest.TestCase):
    def test_env(self):
        with mock.patch.dict(os.environ, {"BURN_TEST_HOOK": " https://x.test/h \n"}):
            self.assertEqual(notify.resolve_location("env:BURN_TEST_HOOK"), "https://x.test/h")

    def test_env_missing_does_not_leak(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("BURN_TEST_MISSING", None)
            with self.assertRaises(notify.ConfigError) as ctx:
                notify.resolve_location("env:BURN_TEST_MISSING")
            self.assertIn("BURN_TEST_MISSING", str(ctx.exception))

    def test_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "token"
            p.write_text("abc123\n", encoding="utf-8")
            self.assertEqual(notify.resolve_location(f"file:{p}"), "abc123")
            with self.assertRaises(notify.ConfigError):
                notify.resolve_location(f"file:{Path(d) / 'nope'}")

    def test_literal_value_rejected(self):
        for loc in ("https://discord.com/api/webhooks/1/abc", "", "keychain:svc/acct", "plain"):
            with self.subTest(loc=loc), self.assertRaises(notify.ConfigError) as ctx:
                notify.resolve_location(loc)
            self.assertNotIn("discord.com/api", str(ctx.exception))


class TestChannelChoice(unittest.TestCase):
    def test_auto_prefers_claude_push_on_desktop(self):
        self.assertEqual(notify.choose_channel(cfg("claude-desktop", channel="auto", ntfy_topic="t"))[0],
                         "claude-push")

    def test_auto_skips_claude_push_when_asked(self):
        c = cfg("claude-desktop", channel="auto", ntfy_topic="t")
        self.assertEqual(notify.choose_channel(c, allow_claude_push=False)[0], "ntfy")

    def test_auto_order(self):
        self.assertEqual(notify.choose_channel(cfg(ntfy_topic="t", webhook_url_from="env:X"))[0], "ntfy")
        self.assertEqual(notify.choose_channel(cfg(webhook_url_from="env:X"))[0], "webhook")
        self.assertEqual(notify.choose_channel(
            cfg(pushover_user_from="env:U", pushover_token_from="env:T"))[0], "pushover")
        channel, note = notify.choose_channel(cfg())
        self.assertEqual(channel, "none")
        self.assertIn("ntfy_topic", note)

    def test_explicit_and_override(self):
        c = cfg("claude-desktop", channel="webhook", ntfy_topic="t")
        self.assertEqual(notify.choose_channel(c)[0], "webhook")
        self.assertEqual(notify.choose_channel(c, "ntfy")[0], "ntfy")
        self.assertEqual(notify.choose_channel(cfg(channel="claude-push", ntfy_topic="t"),
                                               allow_claude_push=False)[0], "ntfy")

    def test_unknown_channel(self):
        with self.assertRaises(notify.ConfigError):
            notify.choose_channel(cfg(channel="email"))


class TestPayloads(unittest.TestCase):
    def test_ntfy_headers(self):
        req = notify.build_request("ntfy", cfg(ntfy_server="https://ntfy.example/", ntfy_topic="burn-7f3k"),
                                   "NH-007 (cost)", "D1 near limit", "high", "https://github.com/x", ["money"])
        self.assertEqual(req["url"], "https://ntfy.example/burn-7f3k")
        self.assertEqual(req["headers"]["Title"], "NH-007 (cost)")
        self.assertEqual(req["headers"]["Priority"], "4")
        self.assertEqual(req["headers"]["Tags"], "money")
        self.assertEqual(req["headers"]["Click"], "https://github.com/x")
        self.assertEqual(req["body"], b"D1 near limit")
        self.assertNotIn("burn-7f3k", notify.redact(req, ["burn-7f3k"])["url"])

    def test_ntfy_non_latin_title(self):
        req = notify.build_request("ntfy", cfg(ntfy_topic="t"), "Recap ✓", "m")
        self.assertTrue(req["headers"]["Title"].startswith("=?UTF-8?B?"))

    def test_ntfy_needs_topic(self):
        with self.assertRaises(notify.ConfigError):
            notify.build_request("ntfy", cfg(), "t", "m")

    def test_webhook_discord_and_slack(self):
        with mock.patch.dict(os.environ, {"HOOK_D": "https://discord.com/api/webhooks/1/x",
                                          "HOOK_S": "https://hooks.slack.com/services/T/B/x"}):
            d = notify.build_request("webhook", cfg(webhook_url_from="env:HOOK_D"), "T", "M", url="https://u")
            s = notify.build_request("webhook", cfg(webhook_url_from="env:HOOK_S"), "T", "M")
        self.assertEqual(json.loads(d["body"]), {"content": "**T**\nM\nhttps://u"})
        self.assertEqual(json.loads(s["body"]), {"text": "*T*\nM"})
        self.assertNotIn("/x", d["redacted_url"])

    def test_pushover_form(self):
        with mock.patch.dict(os.environ, {"PO_USER": "uQiRzpo4DXghDmr9QzzfQu27cmVRsG",
                                          "PO_TOKEN": "azGDORePK8gMaC0QOYAMyEEuzJnyUi"}):
            c = cfg(pushover_user_from="env:PO_USER", pushover_token_from="env:PO_TOKEN")
            req = notify.build_request("pushover", c, "T", "M", "high")
            shown = notify.redact(req, notify._secret_values("pushover", c))
        self.assertIn("priority=1", req["body"].decode())
        self.assertNotIn("azGDORePK8", shown["body"])
        self.assertNotIn("uQiRzpo4", shown["body"])


class TestMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {"BURN_RATE_HOME": str(self.home)})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(notify, "send", return_value=200) as send:
            code = notify.main(["--title", "Burn run 1/3", "--message", "Shipped it.", *args])
        return code, json.loads(out.getvalue()), send

    def write_config(self, text):
        (self.home / "config.toml").write_text(text, encoding="utf-8")

    def test_missing_config_exits_2(self):
        code, out, send = self.run_main("--dry-run")
        self.assertEqual(code, 2)
        send.assert_not_called()

    def test_dry_run_does_not_send(self):
        self.write_config('platform = "codex"\n[notify]\nchannel = "auto"\nntfy_topic = "burn-abc"\n')
        code, out, send = self.run_main("--dry-run", "--priority", "high")
        self.assertEqual(code, 0)
        self.assertEqual(out["channel"], "ntfy")
        self.assertEqual(out["request"]["headers"]["Priority"], "4")
        self.assertNotIn("burn-abc", json.dumps(out))
        send.assert_not_called()

    def test_claude_push_returns_instruction(self):
        self.write_config('platform = "claude-desktop"\n[notify]\nchannel = "auto"\n')
        code, out, send = self.run_main()
        self.assertEqual(code, 0)
        self.assertEqual(out["channel"], "claude-push")
        self.assertFalse(out["delivered"])
        self.assertIn("PushNotification", out["note"])
        send.assert_not_called()

    def test_claude_push_dry_run(self):
        self.write_config('platform = "claude-desktop"\n[notify]\nchannel = "auto"\n')
        code, out, send = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out["channel"], "claude-push")
        self.assertTrue(out["dry_run"])
        self.assertFalse(out["delivered"])
        send.assert_not_called()

    def test_missing_env_credential_exits_2(self):
        self.write_config('platform = "codex"\n[notify]\nchannel = "webhook"\n'
                          'webhook_url_from = "env:BURN_TEST_NOT_SET"\n')
        os.environ.pop("BURN_TEST_NOT_SET", None)
        code, out, send = self.run_main()
        self.assertEqual(code, 2)
        send.assert_not_called()

    def test_send_failure_exits_1(self):
        self.write_config('platform = "codex"\n[notify]\nntfy_topic = "burn-abc"\n')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                mock.patch.object(notify, "send", side_effect=notify.SendError("boom")):
            code = notify.main(["--title", "t", "--message", "m"])
        self.assertEqual(code, 1)

    def test_success(self):
        self.write_config('platform = "codex"\n[notify]\nntfy_topic = "burn-abc"\n')
        code, out, send = self.run_main()
        self.assertEqual(code, 0)
        self.assertTrue(out["delivered"])
        send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
