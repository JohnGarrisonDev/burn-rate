#!/usr/bin/env python3
"""Send a Burn Rate push notification through the channel set in config.toml.

Python 3.11+, standard library only.

    python notify.py --title "NH-007 (cost)" --message "D1 near its free row limit" --priority high \
        --url https://github.com/jdoe/invoice-snap/blob/main/burn/NEEDS_HUMAN.md
    python notify.py --title "Burn run 2/3" --message "Shipped CSV export." --dry-run
    python notify.py ... --channel ntfy          # override [notify].channel for this message
    python notify.py ... --no-claude-push        # "auto", but skip the Claude Desktop tool

Channels:
  claude-push  Claude Desktop's PushNotification tool. This script can't call it; it says so
               and the agent calls the tool itself.
  ntfy         POST to ntfy_server/ntfy_topic with Title, Priority, Tags and Click headers.
  webhook      Discord- or Slack-compatible JSON. The URL comes from webhook_url_from.
  pushover     Pushover API. Keys come from pushover_user_from / pushover_token_from.
  none         Don't send.
  auto         claude-push on Claude Desktop, else ntfy if a topic is set, else webhook,
               else pushover, else nothing (prints a note).

Secrets are never read from config directly. A *_from field names a location:
  env:NAME     an environment variable
  file:PATH    a file holding only the value (~ is expanded)

The script refuses to send a message that looks like it contains a secret.

Prints one JSON object on stdout. Exit codes: 0 sent (or dry run, or nothing to do),
1 send failed or refused, 2 config or credential missing.
"""

import argparse
import base64
import json
import os
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TIMEOUT = 10
USER_AGENT = "burn-rate-notify/1"
CHANNELS = ("auto", "claude-push", "ntfy", "webhook", "pushover", "none")
PRIORITIES = ("min", "low", "default", "high", "urgent")
NTFY_PRIORITY = {"min": "1", "low": "2", "default": "3", "high": "4", "urgent": "5"}
PUSHOVER_PRIORITY = {"min": "-2", "low": "-1", "default": "0", "high": "1", "urgent": "1"}

SECRET_PATTERNS = [
    ("api key (sk-)", re.compile(r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_\-]{16,}")),
    ("Stripe key", re.compile(r"(?<![A-Za-z0-9])[sr]k_(?:live|test)_[A-Za-z0-9]{8,}")),
    ("GitHub token", re.compile(r"(?<![A-Za-z0-9])(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("Slack token", re.compile(r"(?<![A-Za-z0-9])xox[abposr]-[A-Za-z0-9\-]{10,}")),
    ("AWS access key", re.compile(r"(?<![A-Za-z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![0-9A-Z])")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*(?:PRIVATE KEY|CERTIFICATE)")),
    ("credential in URL", re.compile(r"[a-z][a-z0-9+.\-]*://[^\s:/@]+:[^\s@/]+@", re.I)),
    ("webhook URL", re.compile(
        r"https?://(?:[a-z0-9-]+\.)?(?:discord(?:app)?\.com/api/webhooks|hooks\.slack\.com)/\S+", re.I)),
    ("key=value secret", re.compile(
        r"(?i)(?:api[_-]?key|key|token|secret|password|passwd|pwd|auth)[\"']?\s*[=:]\s*[\"']?"
        r"(?=[A-Za-z0-9+/_\-=]*\d)(?=[A-Za-z0-9+/_\-=]*[A-Za-z])[A-Za-z0-9+/_\-=]{20,}")),
]


class ConfigError(Exception):
    """Config, or a credential it points to, is missing. Exit 2."""


class SendError(Exception):
    """The message couldn't be sent. Exit 1."""


# ---------- config and locations ----------

def burn_home():
    env = os.environ.get("BURN_RATE_HOME")
    return Path(env).expanduser() if env else Path.home() / ".burn-rate"


def load_config(path=None):
    path = Path(path) if path else burn_home() / "config.toml"
    if not path.is_file():
        raise ConfigError(f"no config at {path}; run the burn-setup skill first")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def resolve_location(location, what="credential"):
    """Turn "env:NAME" or "file:PATH" into the secret value. Never echoes the value."""
    loc = (location or "").strip()
    if not loc:
        raise ConfigError(f"no location set for {what}")
    kind, sep, ref = loc.partition(":")
    if not sep or not ref or kind not in ("env", "file", "keychain"):
        raise ConfigError(f"{what}: expected env:NAME or file:PATH, not a literal value. "
                          "Move the secret into an env var or a gitignored file.")
    if kind == "env":
        value = os.environ.get(ref, "")
        if not value.strip():
            raise ConfigError(f"{what}: environment variable {ref} is not set")
        return value.strip()
    if kind == "file":
        p = Path(ref).expanduser()
        try:
            value = p.read_text(encoding="utf-8").strip()
        except OSError:
            raise ConfigError(f"{what}: can't read {p}") from None
        if not value:
            raise ConfigError(f"{what}: {p} is empty")
        return value
    raise ConfigError(f"{what}: keychain locations aren't supported by notify.py; use env: or file:")


def find_secret(*texts):
    """Return the name of the first secret-looking pattern in any text, or None."""
    for text in texts:
        if not text:
            continue
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(text):
                return name
    return None


# ---------- channel choice ----------

def choose_channel(cfg, requested=None, allow_claude_push=True):
    """Return (channel, note). requested overrides [notify].channel."""
    n = cfg.get("notify", {})
    channel = (requested or n.get("channel") or "auto").strip().lower()
    if channel not in CHANNELS:
        raise ConfigError(f"unknown notify channel {channel!r}; use one of {', '.join(CHANNELS)}")
    if channel != "auto":
        if channel == "claude-push" and not allow_claude_push:
            return choose_channel(cfg, "auto", allow_claude_push=False)
        return channel, ""
    if allow_claude_push and cfg.get("platform") == "claude-desktop":
        return "claude-push", ""
    if n.get("ntfy_topic"):
        return "ntfy", ""
    if n.get("webhook_url_from"):
        return "webhook", ""
    if n.get("pushover_user_from") and n.get("pushover_token_from"):
        return "pushover", ""
    return "none", ("no notification channel is configured; set [notify] ntfy_topic, "
                    "webhook_url_from or pushover_*_from in config.toml")


# ---------- requests ----------

def _header(value):
    """HTTP headers are latin-1. Encode anything else as RFC 2047, which ntfy accepts."""
    try:
        value.encode("latin-1")
        return value
    except UnicodeEncodeError:
        return "=?UTF-8?B?" + base64.b64encode(value.encode("utf-8")).decode("ascii") + "?="


def build_request(channel, cfg, title, message, priority="default", url=None, tags=None):
    """Return a dict: method, url, headers, body (bytes), redacted_url."""
    n = cfg.get("notify", {})
    priority = priority if priority in PRIORITIES else "default"

    if channel == "ntfy":
        topic = (n.get("ntfy_topic") or "").strip()
        if not topic:
            raise ConfigError("ntfy: set [notify].ntfy_topic in config.toml")
        server = (n.get("ntfy_server") or "https://ntfy.sh").rstrip("/")
        headers = {"Title": _header(title), "Priority": NTFY_PRIORITY[priority],
                   "Content-Type": "text/plain; charset=utf-8"}
        if tags:
            headers["Tags"] = _header(",".join(tags))
        if url:
            headers["Click"] = url
        if n.get("ntfy_token_from"):
            headers["Authorization"] = "Bearer " + resolve_location(n["ntfy_token_from"], "ntfy token")
        return {"method": "POST", "url": f"{server}/{urllib.parse.quote(topic)}",
                "redacted_url": f"{server}/***", "headers": headers,
                "body": message.encode("utf-8")}

    if channel == "webhook":
        hook = resolve_location(n.get("webhook_url_from"), "webhook_url_from")
        text = f"**{title}**\n{message}" + (f"\n{url}" if url else "")
        host = urllib.parse.urlparse(hook).hostname or ""
        if host.endswith(("discord.com", "discordapp.com")):
            payload = {"content": text[:2000]}
        elif host.endswith("slack.com"):
            payload = {"text": text.replace("**", "*")}
        else:
            payload = {"text": text, "content": text[:2000]}
        return {"method": "POST", "url": hook, "redacted_url": f"https://{host or 'webhook'}/***",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(payload).encode("utf-8")}

    if channel == "pushover":
        user = resolve_location(n.get("pushover_user_from"), "pushover_user_from")
        token = resolve_location(n.get("pushover_token_from"), "pushover_token_from")
        form = {"token": token, "user": user, "title": title[:250], "message": message[:1024],
                "priority": PUSHOVER_PRIORITY[priority]}
        if url:
            form["url"] = url
        return {"method": "POST", "url": "https://api.pushover.net/1/messages.json",
                "redacted_url": "https://api.pushover.net/1/messages.json",
                "headers": {"Content-Type": "application/x-www-form-urlencoded"},
                "body": urllib.parse.urlencode(form).encode("utf-8")}

    raise ValueError(f"no request for channel {channel}")


def redact(req, secrets=()):
    """A printable copy of a request with secret values replaced."""
    body = req["body"].decode("utf-8", errors="replace")
    for s in secrets:
        if s:
            body = body.replace(s, "***").replace(urllib.parse.quote_plus(s), "***")
    headers = {k: ("***" if k.lower() == "authorization" else v) for k, v in req["headers"].items()}
    return {"method": req["method"], "url": req["redacted_url"], "headers": headers, "body": body}


def send(req, timeout=TIMEOUT):
    headers = dict(req["headers"], **{"User-Agent": USER_AGENT})
    r = urllib.request.Request(req["url"], data=req["body"], headers=headers, method=req["method"])
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        raise SendError(f"{req['redacted_url']} answered HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", e)
        raise SendError(f"couldn't reach {req['redacted_url']}: {reason}") from None


# ---------- main ----------

def _secret_values(channel, cfg):
    """Values to scrub from dry-run output. Best effort; missing ones are skipped."""
    n = cfg.get("notify", {})
    keys = {"webhook": ["webhook_url_from"], "pushover": ["pushover_user_from", "pushover_token_from"],
            "ntfy": ["ntfy_token_from"]}.get(channel, [])
    out = [n.get("ntfy_topic", "")] if channel == "ntfy" else []
    for k in keys:
        try:
            out.append(resolve_location(n.get(k), k))
        except ConfigError:
            pass
    return out


def emit(obj):
    json.dump(obj, sys.stdout)
    print()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--title", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--priority", default="default", choices=PRIORITIES)
    ap.add_argument("--url", help="link to open when the notification is tapped")
    ap.add_argument("--tags", default="", help="comma-separated ntfy tags, e.g. warning,money")
    ap.add_argument("--channel", choices=CHANNELS, help="override [notify].channel")
    ap.add_argument("--no-claude-push", action="store_true",
                    help="treat claude-push as unavailable (fall through to the next channel)")
    ap.add_argument("--config", help="path to config.toml (default: burn home)")
    ap.add_argument("--dry-run", action="store_true", help="print the request instead of sending it")
    args = ap.parse_args(argv)

    found = find_secret(args.title, args.message, args.url, args.tags)
    if found:
        emit({"ok": False, "delivered": False,
              "error": f"refused: the message looks like it contains a secret ({found}). "
                       "Remove it and say where to look instead."})
        return 1

    try:
        cfg = load_config(args.config)
        channel, note = choose_channel(cfg, args.channel, allow_claude_push=not args.no_claude_push)
        if channel == "none":
            emit({"ok": True, "delivered": False, "channel": "none",
                  "note": note or "notifications are off ([notify].channel = \"none\")"})
            return 0
        if channel == "claude-push":
            if args.dry_run:
                emit({"ok": True, "delivered": False, "channel": "claude-push", "dry_run": True,
                      "note": "dry run: would ask you to call the PushNotification tool with "
                              "this title and message"})
                return 0
            emit({"ok": True, "delivered": False, "channel": "claude-push",
                  "note": "call the PushNotification tool with this title and message "
                          "(load it with ToolSearch if it's deferred). If it isn't available, "
                          "rerun with --no-claude-push."})
            return 0
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        req = build_request(channel, cfg, args.title, args.message, args.priority, args.url, tags)
    except ConfigError as e:
        emit({"ok": False, "delivered": False, "error": str(e)})
        return 2

    if args.dry_run:
        emit({"ok": True, "delivered": False, "channel": channel, "dry_run": True,
              "request": redact(req, _secret_values(channel, cfg))})
        return 0
    try:
        status = send(req)
    except SendError as e:
        emit({"ok": False, "delivered": False, "channel": channel, "error": str(e)})
        return 1
    emit({"ok": True, "delivered": True, "channel": channel, "status": status})
    return 0


if __name__ == "__main__":
    sys.exit(main())
