#!/usr/bin/env python3
"""Claude Code statusline hook that remembers your rate limits for Burn Rate.

Claude Code pipes a JSON blob to the statusline command after each response. On Pro/Max
plans it includes rate_limits.five_hour and rate_limits.seven_day. Headless runs
(`claude -p`) can't see that, so this hook saves the latest snapshot to
~/.burn-rate/cache/claude-usage.json for usage.py to read.

If you already had a statusline command, burn-setup stores it in
~/.burn-rate/cache/statusline-wrapped.txt and this hook passes the same input through
to it, so your statusline looks exactly as before. Otherwise it prints a short line.

Install (burn-setup does this for you, with your OK), in ~/.claude/settings.json:
    "statusLine": {"type": "command", "command": "python /path/to/claude_statusline_hook.py"}
On Windows, write the path with forward slashes (C:/Users/...); backslashes get eaten by bash.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def burn_home():
    env = os.environ.get("BURN_RATE_HOME")
    return Path(env).expanduser() if env else Path.home() / ".burn-rate"


def windows_bash():
    """Git Bash (or another bash) on PATH, but not System32's bash.exe, which starts WSL."""
    found = shutil.which("bash")
    if not found:
        return None
    def norm(p):
        return p.replace("/", "\\").rstrip("\\").lower()

    system32 = norm(os.environ.get("SystemRoot", r"C:\Windows")) + "\\system32\\"
    return None if norm(found).startswith(system32) else found


def run_wrapped(cmd, raw):
    """Run the user's original statusline command with the same input.

    Claude Code runs statusline commands through bash, also on Windows (Git Bash), so a
    wrapped command is usually bash syntax. Use bash there when it's on PATH; otherwise
    fall back to the system shell.
    """
    kw = {"input": raw, "capture_output": True, "text": True, "timeout": 5}
    if os.name == "nt":
        bash = windows_bash()
        if bash:
            return subprocess.run([bash, "-c", cmd], **kw)
    return subprocess.run(cmd, shell=True, **kw)


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        data = {}

    rl = data.get("rate_limits")
    cache = burn_home() / "cache"
    if isinstance(rl, dict) and rl:
        try:
            cache.mkdir(parents=True, exist_ok=True)
            snap = {"captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "rate_limits": rl}
            tmp = cache / "claude-usage.json.tmp"
            tmp.write_text(json.dumps(snap), encoding="utf-8")
            tmp.replace(cache / "claude-usage.json")
        except OSError:
            pass  # never break the statusline over a cache write

    wrapped = cache / "statusline-wrapped.txt"
    if wrapped.is_file():
        cmd = wrapped.read_text(encoding="utf-8").strip()
        if cmd:
            try:
                out = run_wrapped(cmd, raw)
                sys.stdout.write(out.stdout)
                return 0
            except (OSError, subprocess.SubprocessError):
                pass

    parts = []
    model = (data.get("model") or {}).get("display_name")
    if model:
        parts.append(model)
    if isinstance(rl, dict):
        fh = (rl.get("five_hour") or {}).get("used_percentage")
        wk = (rl.get("seven_day") or {}).get("used_percentage")
        if fh is not None:
            parts.append(f"5h {fh:.0f}%")
        if wk is not None:
            parts.append(f"week {wk:.0f}%")
    print(" · ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
