#!/usr/bin/env python3
"""Check a Burn Rate config.toml against the rules in templates/config.toml.

Python 3.11+, standard library only.

    python config_check.py                         # checks $BURN_RATE_HOME/config.toml (or ~/.burn-rate)
    python config_check.py path/to/config.toml
    python config_check.py new.toml --previous old.toml
                                                   # also flags gated changes between the two
    python config_check.py new.toml --previous old.toml --allow-gated
                                                   # gated changes become warnings (only when
                                                   # the user asked for them in person)

Prints one line per problem ("error: ..." or "warning: ...") and a summary line.
Exit code 1 if there is any error, 0 otherwise.

Gated changes are the ones a scheduled run may never make on its own:
  - raising providers.<name>.monthly_cap_usd   (only through an approved cost proposal)
  - turning on providers.stripe.live_mode_approved
  - raising budget.hard_stop_pct
"""

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

PLATFORMS = {"claude-desktop", "claude-cli", "codex"}
USAGE_SOURCES = {"auto", "claude-desktop", "claude-statusline", "codex-sessions", "declared"}
AUTONOMY = {"act", "propose"}
GIT_STRATEGIES = {"branch-merge", "pr", "main"}
CHANNELS = {"auto", "claude-push", "ntfy", "webhook", "pushover", "none"}
IMPROVE_MODES = {"off", "suggest", "local", "maintainer"}
LOCATION_RE = re.compile(r"^(env:[A-Za-z_][A-Za-z0-9_]*|cli:[A-Za-z0-9_.-]+|keychain:\S+|file:\S+)$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
SECRET_PATTERNS = [
    re.compile(r"sk_(live|test)_[A-Za-z0-9]{8,}"),
    re.compile(r"(rk|pk)_live_[A-Za-z0-9]{8,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"https://(discord(app)?\.com/api/webhooks|hooks\.slack\.com)/\S+"),
    re.compile(r"://[^/\s:@]+:[^/\s@]+@"),  # credentials inside a URL
]
KNOWN_TOP = {"version", "platform", "github_owner", "budget", "schedule", "autonomy", "git",
             "meetings", "recap", "notify", "self_improve", "providers"}


def burn_home():
    env = os.environ.get("BURN_RATE_HOME")
    return Path(env).expanduser() if env else Path.home() / ".burn-rate"


class Checker:
    def __init__(self, cfg):
        self.cfg = cfg
        self.errors = []
        self.warnings = []

    def err(self, key, msg):
        self.errors.append(f"error: {key}: {msg}")

    def warn(self, key, msg):
        self.warnings.append(f"warning: {key}: {msg}")

    def get(self, dotted):
        node = self.cfg
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return None
            node = node[part]
        return node

    # --- typed helpers. Each returns the value if it passed, else None. ---

    def required(self, key):
        value = self.get(key)
        if value is None:
            self.err(key, "missing")
        return value

    def number(self, key, lo=None, hi=None, integer=False):
        value = self.required(key)
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            self.err(key, f"must be a number, got {value!r}")
            return None
        if integer and not isinstance(value, int):
            self.err(key, f"must be a whole number, got {value!r}")
            return None
        if lo is not None and value < lo or hi is not None and value > hi:
            self.err(key, f"{value} is out of range ({lo} to {hi})")
            return None
        return value

    def boolean(self, key):
        value = self.required(key)
        if value is not None and not isinstance(value, bool):
            self.err(key, f"must be true or false, got {value!r}")
            return None
        return value

    def choice(self, key, options):
        value = self.required(key)
        if value is not None and value not in options:
            self.err(key, f"{value!r} is not one of: {', '.join(sorted(options))}")
            return None
        return value

    def string(self, key, required=True):
        value = self.get(key) if not required else self.required(key)
        if value is not None and not isinstance(value, str):
            self.err(key, f"must be a string, got {value!r}")
            return None
        return value

    def location(self, key, required=False):
        """A credential location like env:NAME or cli:gh. Empty is allowed unless required."""
        value = self.string(key, required=required)
        if not value:
            if required:
                self.err(key, "empty; say where the credential lives, e.g. env:NAME or cli:tool")
            return value
        if not LOCATION_RE.match(value):
            self.err(key, f"{value!r} is not a credential location (env:NAME, cli:tool, "
                          "keychain:service/account or file:path). Never put the value itself here")
            return None
        return value

    # --- the rules ---

    def run(self):
        c = self.cfg
        for key in c:
            if key not in KNOWN_TOP:
                self.warn(key, "unknown setting; it will be ignored")

        self.number("version", 1, 1, integer=True)
        self.choice("platform", PLATFORMS)
        self.string("github_owner")

        target = self.number("budget.target_end_pct", 50, 99)
        hard = self.number("budget.hard_stop_pct", 50, 99)
        if target is not None and hard is not None and hard < target:
            self.err("budget.hard_stop_pct", f"{hard} is below target_end_pct {target}; "
                                             "it must be at least the target")
        self.number("budget.five_hour_stop_pct", 50, 100)
        self.choice("budget.usage_source", USAGE_SOURCES)
        self.number("budget.declared_minutes_per_run", 10, 600, integer=True)

        self.check_schedule()

        self.choice("autonomy.mode", AUTONOMY)
        self.boolean("autonomy.can_create_repos")
        self.choice("git.strategy", GIT_STRATEGIES)

        self.boolean("meetings.enabled")
        self.number("meetings.max_attendees", 1, 8, integer=True)
        self.number("meetings.max_rounds", 1, 4, integer=True)
        self.boolean("meetings.weekly_planning")

        self.boolean("recap.enabled")
        self.boolean("recap.notify")

        self.check_notify()
        self.check_self_improve()
        self.check_providers()
        self.scan_secrets(c, "")

    def check_schedule(self):
        hours = self.required("schedule.hours_before_reset")
        if hours is not None:
            if not isinstance(hours, list) or not hours:
                self.err("schedule.hours_before_reset", "must be a non-empty list, e.g. [36, 20, 6]")
            else:
                for h in hours:
                    if isinstance(h, bool) or not isinstance(h, (int, float)) or not 0 < h < 168:
                        self.err("schedule.hours_before_reset",
                                 f"{h!r} must be a number of hours between 0 and 168")
                if len(set(hours)) != len(hours):
                    self.err("schedule.hours_before_reset", "has duplicate slots")
                if len(hours) > 7:
                    self.warn("schedule.hours_before_reset",
                              f"{len(hours)} runs a week; each one gets a thin slice of budget")
        tz = self.string("schedule.timezone")
        if tz:
            from zoneinfo import available_timezones
            known = available_timezones()  # empty on Windows without the tzdata package
            if known and tz not in known:
                self.warn("schedule.timezone", f"{tz!r} isn't a known IANA timezone")
            elif not known and not re.match(r"^(UTC|[A-Za-z]+(/[A-Za-z0-9_+-]+)+)$", tz):
                self.warn("schedule.timezone", f"{tz!r} doesn't look like an IANA timezone, e.g. Europe/London")
        self.string("schedule.weekly_reset")

    def check_notify(self):
        channel = self.choice("notify.channel", CHANNELS)
        self.boolean("notify.run_summaries")
        server = self.string("notify.ntfy_server")
        if server and not server.startswith(("https://", "http://")):
            self.err("notify.ntfy_server", f"{server!r} must start with https://")
        topic = self.string("notify.ntfy_topic")
        if channel == "ntfy" and not topic:
            self.err("notify.ntfy_topic", "channel is ntfy but no topic is set")
        if topic and len(topic) < 12:
            self.warn("notify.ntfy_topic", "short topics are easy to guess; use a long random one")
        webhook = self.location("notify.webhook_url_from")
        if channel == "webhook" and not webhook:
            self.err("notify.webhook_url_from", "channel is webhook but no location is set")
        for key in self.get("notify") or {}:
            if key.endswith("_from") and key not in ("webhook_url_from", "pushover_user_from",
                                                     "pushover_token_from"):
                self.location(f"notify.{key}")
        user = self.location("notify.pushover_user_from")
        token = self.location("notify.pushover_token_from")
        if channel == "pushover" and not (user and token):
            self.err("notify.pushover_user_from", "channel is pushover but user/token locations are missing")

    def check_self_improve(self):
        mode = self.choice("self_improve.mode", IMPROVE_MODES)
        path = self.string("self_improve.skills_repo_path")
        self.number("self_improve.every_n_runs", 0, 100, integer=True)
        upstream = self.boolean("self_improve.upstream_issues")
        repo = self.string("self_improve.upstream_repo")
        if mode == "maintainer":
            if not path:
                self.err("self_improve.skills_repo_path", "maintainer mode needs the path to a burn-rate clone")
            else:
                p = Path(path).expanduser()
                if not p.is_dir():
                    self.err("self_improve.skills_repo_path", f"{path} does not exist")
                elif not ((p / ".git").exists() and (p / "skills" / "burn" / "SKILL.md").is_file()
                          and (p / "tests" / "lint_skills.py").is_file()):
                    self.err("self_improve.skills_repo_path",
                             f"{path} is not a git clone of the burn-rate repo")
        if upstream:
            if not repo:
                self.err("self_improve.upstream_repo", "upstream_issues is on but no repo is set")
            elif not REPO_RE.match(repo):
                self.err("self_improve.upstream_repo", f"{repo!r} must look like owner/repo")

    def check_providers(self):
        providers = self.get("providers")
        if providers is None:
            return
        if not isinstance(providers, dict):
            self.err("providers", "must be a set of [providers.<name>] tables")
            return
        for name, table in providers.items():
            base = f"providers.{name}"
            if not isinstance(table, dict):
                self.err(base, "must be a table")
                continue
            enabled = self.boolean(f"{base}.enabled")
            self.location(f"{base}.credential", required=bool(enabled))
            self.number(f"{base}.monthly_cap_usd", 0, 100000)
            for key in table:
                if key.endswith("_from"):
                    self.location(f"{base}.{key}")
            if "live_mode_approved" in table:
                self.boolean(f"{base}.live_mode_approved")

    def scan_secrets(self, node, prefix):
        if isinstance(node, dict):
            for k, v in node.items():
                self.scan_secrets(v, f"{prefix}.{k}" if prefix else k)
        elif isinstance(node, list):
            for v in node:
                self.scan_secrets(v, prefix)
        elif isinstance(node, str):
            if any(p.search(node) for p in SECRET_PATTERNS):
                self.err(prefix, "looks like a secret value. Remove it, rotate it, and store "
                                 "only its location (e.g. env:NAME)")


def gated_changes(old, new):
    """List the changes between two configs that need a human's say-so."""
    changes = []

    def num(cfg, *path):
        node = cfg
        for p in path:
            node = node.get(p) if isinstance(node, dict) else None
        return node if isinstance(node, (int, float)) and not isinstance(node, bool) else None

    old_hard, new_hard = num(old, "budget", "hard_stop_pct"), num(new, "budget", "hard_stop_pct")
    if old_hard is not None and new_hard is not None and new_hard > old_hard:
        changes.append(f"budget.hard_stop_pct raised {old_hard} -> {new_hard}")
    old_p = old.get("providers", {}) if isinstance(old.get("providers"), dict) else {}
    new_p = new.get("providers", {}) if isinstance(new.get("providers"), dict) else {}
    for name, table in new_p.items():
        if not isinstance(table, dict):
            continue
        before = old_p.get(name, {}) if isinstance(old_p.get(name), dict) else {}
        a, b = num(before, "monthly_cap_usd") or 0, num(table, "monthly_cap_usd") or 0
        if b > a:
            changes.append(f"providers.{name}.monthly_cap_usd raised {a} -> {b}")
        if table.get("live_mode_approved") is True and before.get("live_mode_approved") is not True:
            changes.append(f"providers.{name}.live_mode_approved turned on")
    return changes


def check(cfg, previous=None, allow_gated=False):
    """Return (errors, warnings) for a parsed config dict."""
    c = Checker(cfg)
    c.run()
    if previous is not None:
        for change in gated_changes(previous, cfg):
            if allow_gated:
                c.warnings.append(f"warning: gated change (user asked in person): {change}")
            else:
                c.errors.append(f"error: gated change: {change}. Only the user, interactively, "
                                "or an approved NEEDS_HUMAN item may do this")
    return c.errors, c.warnings


def load(path):
    with open(Path(path).expanduser(), "rb") as fh:
        return tomllib.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a Burn Rate config.toml.")
    ap.add_argument("path", nargs="?", help="config file (default: burn home config.toml)")
    ap.add_argument("--previous", help="the config before the change, to catch gated changes")
    ap.add_argument("--allow-gated", action="store_true",
                    help="the user asked for the gated change in person; report it as a warning")
    args = ap.parse_args(argv)

    path = Path(args.path).expanduser() if args.path else burn_home() / "config.toml"
    try:
        cfg = load(path)
    except FileNotFoundError:
        print(f"error: {path} not found")
        return 1
    except tomllib.TOMLDecodeError as exc:
        print(f"error: {path} is not valid TOML: {exc}")
        return 1
    previous = None
    if args.previous:
        try:
            previous = load(args.previous)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            print(f"error: can't read --previous {args.previous}: {exc}")
            return 1

    errors, warnings = check(cfg, previous, args.allow_gated)
    for line in errors + warnings:
        print(line)
    print(f"{path}: {len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
