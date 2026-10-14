#!/usr/bin/env python3
"""Read subscription usage and work out how much a burn run may spend.

Python 3.11+, standard library only.

    python usage.py                      # current usage as JSON (auto: picks the source by platform)
    python usage.py --source codex-sessions
    python usage.py plan                 # usage + this run's budget, using config.toml
    python usage.py plan --weekly 61 --resets-at 2026-10-17T13:59:59Z --five-hour 12
                                         # same, with numbers you already have
                                         # (e.g. from Claude Desktop's get_usage tool)

Sources:
  codex-sessions     newest rate_limits snapshot in ~/.codex/sessions/**/*.jsonl
  claude-statusline  <burn home>/cache/claude-usage.json, written by claude_statusline_hook.py
  declared           no live numbers; the run is time-boxed by budget.declared_minutes_per_run

"auto" picks the source by platform (config.toml `platform`, or --platform):
  codex           codex-sessions
  claude-cli      claude-statusline
  claude-desktop  claude-statusline, as a fallback only. Desktop has an exact usage tool
                  (get_usage) that this script can't call: the skill calls it and passes
                  the numbers with --weekly/--resets-at/--five-hour.
  (no platform)   the freshest of codex-sessions and claude-statusline
If the platform's source has nothing, auto falls back to declared. It never reads the
other platform's numbers: a Codex reading says nothing about a Claude subscription.

plan adds stop_weekly_pct (end the run here) and stop_new_work_pct (stop starting new
work here; the gap is the handoff reserve, about 3 points, or 6 on the last run of the
week for the recap and retro).

Output is always one JSON object on stdout. Exit code 0 even when usage is unknown;
check the "source" and "ok" fields.
"""

import argparse
import json
import os
import sys
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

WEEK_MIN = 7 * 24 * 60
PLATFORMS = ("claude-desktop", "claude-cli", "codex")
# Points of weekly budget kept back for the handoff (commit, push, log, retro, notify).
# The last run of the week keeps more, for the weekly recap and its retro.
HANDOFF_RESERVE = 3.0
LAST_RUN_RESERVE = 6.0


def burn_home():
    env = os.environ.get("BURN_RATE_HOME")
    return Path(env).expanduser() if env else Path.home() / ".burn-rate"


def codex_home():
    env = os.environ.get("CODEX_HOME")
    return Path(env).expanduser() if env else Path.home() / ".codex"


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if dt else None


def parse_time(value):
    """Accept epoch seconds, epoch ms, or ISO 8601. Return aware UTC datetime or None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        secs = value / 1000 if value > 1e12 else value
        return datetime.fromtimestamp(secs, tz=timezone.utc)
    s = str(value).strip()
    if s.isdigit():
        return parse_time(int(s))
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def window(used_pct, resets_at):
    return {"used_pct": None if used_pct is None else round(float(used_pct), 1),
            "resets_at": iso(resets_at)}


def empty(source, note):
    return {"ok": False, "source": source, "observed_at": None, "age_minutes": None,
            "weekly": window(None, None), "five_hour": window(None, None), "note": note}


# ---------- Codex ----------

def _find_rate_limits(obj):
    if isinstance(obj, dict):
        if "rate_limits" in obj and isinstance(obj["rate_limits"], dict):
            return obj["rate_limits"]
        for v in obj.values():
            found = _find_rate_limits(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_rate_limits(v)
            if found:
                return found
    return None


def _codex_window(w, observed):
    if not isinstance(w, dict):
        return None, None, None
    used = w.get("used_percent", w.get("usedPercent"))
    minutes = w.get("window_minutes", w.get("windowMinutes"))
    resets = parse_time(w.get("resets_at", w.get("resetsAt")))
    if resets is None:
        secs = w.get("resets_in_seconds", w.get("resetsInSeconds"))
        if secs is not None and observed is not None:
            resets = observed + timedelta(seconds=float(secs))
    return used, minutes, resets


def read_codex():
    root = codex_home() / "sessions"
    if not root.is_dir():
        return empty("codex-sessions", f"no Codex sessions folder at {root}")
    files = sorted(root.rglob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:30]
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            if "rate_limits" not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            rl = _find_rate_limits(rec)
            if not rl:
                continue
            observed = parse_time(rec.get("timestamp")) or datetime.fromtimestamp(
                f.stat().st_mtime, tz=timezone.utc)
            weekly = five = (None, None)
            for key in ("primary", "secondary"):
                used, minutes, resets = _codex_window(rl.get(key), observed)
                if used is None:
                    continue
                is_weekly = (minutes or 0) >= WEEK_MIN * 0.9 if minutes else key == "secondary"
                if is_weekly:
                    weekly = (used, resets)
                else:
                    five = (used, resets)
            if weekly[0] is None and five[0] is None:
                continue
            return finish("codex-sessions", observed, weekly, five, f"from {f.name}")
    return empty("codex-sessions", "no rate_limits found in recent Codex sessions; run any Codex prompt once")


# ---------- Claude statusline cache ----------

def read_claude_statusline():
    path = burn_home() / "cache" / "claude-usage.json"
    if not path.is_file():
        return empty("claude-statusline", f"no cache at {path}; the statusline hook isn't installed or hasn't run yet")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return empty("claude-statusline", f"unreadable cache: {e}")
    if not isinstance(data, dict):
        return empty("claude-statusline", "unreadable cache: not a JSON object")
    rl = data.get("rate_limits") or {}
    observed = parse_time(data.get("captured_at"))
    wk = rl.get("seven_day") or {}
    fh = rl.get("five_hour") or {}
    return finish("claude-statusline", observed,
                  (wk.get("used_percentage"), parse_time(wk.get("resets_at"))),
                  (fh.get("used_percentage"), parse_time(fh.get("resets_at"))),
                  "cached from the Claude Code statusline")


def finish(source, observed, weekly, five, note):
    now = datetime.now(timezone.utc)
    age = None if observed is None else round((now - observed).total_seconds() / 60, 1)
    w_used, w_reset = weekly
    f_used, f_reset = five
    # A window that has already reset since we observed it is back to 0.
    if w_reset and w_reset <= now:
        w_used, w_reset = 0.0, w_reset + timedelta(days=7)
        note += "; weekly window reset since snapshot"
    if f_reset and f_reset <= now:
        f_used, f_reset = 0.0, None
    stale = age is not None and age > 60
    if stale:
        note += f"; snapshot is {int(age)} min old, treat as a lower bound"
    return {"ok": w_used is not None, "source": source, "observed_at": iso(observed),
            "age_minutes": age, "weekly": window(w_used, w_reset),
            "five_hour": window(f_used, f_reset), "note": note}


def read(source, platform=None):
    if source == "codex-sessions":
        return read_codex()
    if source == "claude-statusline":
        return read_claude_statusline()
    if source == "declared":
        return empty("declared", "no live usage; time-box the run")
    # auto: the platform decides the source.
    if platform == "codex":
        return _or_declared(read_codex())
    if platform == "claude-cli":
        return _or_declared(read_claude_statusline())
    if platform == "claude-desktop":
        r = _or_declared(read_claude_statusline())
        r["note"] += ("; on Claude Desktop call get_usage and pass its numbers with "
                      "--weekly/--resets-at/--five-hour instead")
        return r
    # No platform known: the freshest successful reading wins.
    results = [r for r in (read_codex(), read_claude_statusline()) if r["ok"]]
    if not results:
        return empty("declared", "no live usage source found; time-box the run")
    return min(results, key=lambda r: r["age_minutes"] if r["age_minutes"] is not None else 1e9)


def _or_declared(r):
    if r["ok"]:
        return r
    return empty("declared", f"{r['source']}: {r['note']}; time-box the run")


# ---------- planning ----------

def load_config():
    path = burn_home() / "config.toml"
    if not path.is_file():
        return {}
    with path.open("rb") as fh:
        return tomllib.load(fh)


def plan(usage, cfg, now=None):
    now = now or datetime.now(timezone.utc)
    b = cfg.get("budget", {})
    target = float(b.get("target_end_pct", 95))
    hard = float(b.get("hard_stop_pct", 97))
    ceiling = min(target, hard)
    five_stop = float(b.get("five_hour_stop_pct", 90))
    minutes = int(b.get("declared_minutes_per_run", 90))
    hours = sorted(cfg.get("schedule", {}).get("hours_before_reset", [36, 20, 6]), reverse=True)

    out = {"usage": usage, "now": iso(now)}
    used = usage["weekly"]["used_pct"]
    reset = parse_time(usage["weekly"]["resets_at"])
    five_used = usage["five_hour"]["used_pct"] or 0.0

    if used is None or reset is None:
        go, stop_at, new_work = True, None, None
        reason = f"no live weekly usage; work for {minutes} minutes, then wrap up"
        if used is not None:
            # Used is known but the reset isn't: no fair share, but the ceiling still holds.
            stop_at = round(ceiling, 1)
            new_work = round(max(used, ceiling - HANDOFF_RESERVE), 1)
            reason = (f"weekly reset unknown; work for {minutes} minutes or until weekly "
                      f"reaches {new_work}%, then wrap up")
            if used >= ceiling:
                go, reason = False, f"weekly usage {used}% is already at or past the target ({ceiling}%)"
            elif five_used >= five_stop:
                go, reason = False, f"5-hour window at {five_used}%; wait for it to reset"
        out.update(mode="time-boxed", go=go, minutes=minutes, stop_weekly_pct=stop_at,
                   stop_new_work_pct=new_work, handoff_reserve_pts=HANDOFF_RESERVE,
                   five_hour_stop_pct=five_stop, runs_left_including_this=None,
                   is_last_run_of_week=None, reason=reason)
        return out

    hours_left = (reset - now).total_seconds() / 3600
    # Runs still to come this week, counting this one. A run counts as "this one" if
    # we're within its slot (later than its start). Unscheduled/manual runs count as one.
    later_slots = [h for h in hours if h < hours_left - 0.5]
    runs_left = len(later_slots) + 1
    last = runs_left == 1
    room = max(0.0, target - used)
    allowance = room / runs_left
    stop_at = min(ceiling, used + allowance)
    reserve = LAST_RUN_RESERVE if last else HANDOFF_RESERVE
    new_work = max(used, stop_at - reserve)

    go = True
    reason = f"{room:.0f} points left to burn over {runs_left} run(s); this run may spend about {allowance:.0f}"
    if used >= ceiling:
        go, reason = False, f"weekly usage {used}% is already at or past the target ({ceiling}%)"
    elif allowance < 2:
        go, reason = False, f"only {allowance:.1f} points available for this run; not worth starting"
    elif five_used >= five_stop:
        go, reason = False, f"5-hour window at {five_used}%; wait for it to reset"

    out.update(mode="metered", go=go, stop_weekly_pct=round(stop_at, 1),
               stop_new_work_pct=round(new_work, 1), handoff_reserve_pts=reserve,
               five_hour_stop_pct=five_stop, runs_left_including_this=runs_left,
               hours_until_reset=round(hours_left, 1),
               is_last_run_of_week=last, reason=reason)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="read", choices=["read", "plan"])
    ap.add_argument("--source", default=None,
                    choices=["auto", "codex-sessions", "claude-statusline", "declared"])
    ap.add_argument("--weekly", type=float, help="weekly used %% you already know")
    ap.add_argument("--resets-at", help="weekly reset time you already know (ISO or epoch)")
    ap.add_argument("--five-hour", type=float, help="5-hour used %% you already know")
    ap.add_argument("--platform", choices=PLATFORMS,
                    help="platform for --source auto (default: platform in config.toml)")
    args = ap.parse_args(argv)

    cfg = load_config()
    if args.weekly is not None:
        usage = finish("provided", datetime.now(timezone.utc),
                       (args.weekly, parse_time(args.resets_at)),
                       (args.five_hour, None), "numbers passed on the command line")
    else:
        source = args.source or cfg.get("budget", {}).get("usage_source", "auto")
        platform = args.platform or cfg.get("platform")
        if source == "claude-desktop":
            # The script can't call the Desktop tool; auto falls back to the statusline cache.
            source, platform = "auto", "claude-desktop"
        usage = read(source, platform if platform in PLATFORMS else None)

    result = usage if args.command == "read" else plan(usage, cfg)
    json.dump(result, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
