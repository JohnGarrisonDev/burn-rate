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
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def burn_home():
    env = os.environ.get("BURN_RATE_HOME")
    return Path(env).expanduser() if env else Path.home() / ".burn-rate"


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
                out = subprocess.run(cmd, input=raw, shell=True, capture_output=True,
                                     text=True, timeout=5)
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
