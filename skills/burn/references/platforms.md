# Platforms

Burn Rate runs on three platforms. The skills are the same everywhere; only the pieces below differ. `config.toml` stores which one this install uses (`platform`), but always double-check at the start of a run, because someone might run a skill from a different app.

| | Claude Desktop | Claude Code CLI | Codex |
|---|---|---|---|
| `platform` value | `claude-desktop` | `claude-cli` | `codex` |
| Skills folder (user) | `~/.claude/skills/` | `~/.claude/skills/` | `~/.codex/skills/` |
| Skills folder (project) | `.claude/skills/` | `.claude/skills/` | `.agents/skills/` |
| Project instructions file | `CLAUDE.md` | `CLAUDE.md` | `AGENTS.md` |
| Usage | `get_usage` tool (exact) | statusline hook cache | session JSONL (`usage.py`) |
| Scheduling | Desktop scheduled tasks | cron / Task Scheduler + `claude -p` | cron / Task Scheduler + `codex exec` |
| Sub-agents | Agent tool | Agent tool | Codex sub-agents |
| Notifications | `PushNotification` tool, or ntfy | ntfy / webhook | ntfy / webhook |

Claude Desktop's Code tab and the Claude Code CLI share the same skills folder and settings, so one install covers both.

## Detecting the platform

Check in this order:

1. **Claude Desktop**: you have tools whose names start with `mcp__ccd_` or `mcp__scheduled-tasks__` (they may be deferred; search for them with ToolSearch). This is the richest platform. Use its tools.
2. **Claude Code CLI**: you're Claude, you have the Agent/Skill tools, and none of the Desktop tools exist.
3. **Codex**: you're running in Codex (you're an OpenAI model, there's a `~/.codex/` folder, and the instructions file convention is `AGENTS.md`).

If the detected platform differs from `config.toml`, use what you detected for this run and mention it in the log. Don't rewrite config unless the user asks (they might use both).

## Scheduling

Runs are placed relative to the weekly reset: `schedule.hours_before_reset` in config. Turn each into a real local day and time from `schedule.weekly_reset`. Example: reset Sat 13:59 UTC, slots `[36, 20, 6]` → Fri 01:59 UTC, Fri 17:59 UTC, Sat 07:59 UTC. Round to the nearest quarter hour.

Scheduled runs always start in the **burn home**, never in a project folder. The `burn` skill finds the active project from `projects.toml` itself, so renaming, switching or adding projects never breaks the schedule.

The prompt every scheduled run uses is the same:

```
Use the burn skill to do a scheduled Burn Rate run.
```

### Claude Desktop

Use the scheduled-tasks tools (`mcp__scheduled-tasks__create_scheduled_task` and friends). Create one task per slot, with weekly cron expressions in the user's **local** time (the tool uses local time, not UTC). Example for the slots above, in America/New_York (UTC-4):

- `burn-rate-run-1`: `0 22 * * 4` (Thu 22:00)
- `burn-rate-run-2`: `0 14 * * 5` (Fri 14:00)
- `burn-rate-run-3`: `0 4 * * 6` (Sat 04:00)

Tell the user:
- Desktop tasks only run while the app is open. A missed task runs the next time the app starts.
- Their computer needs to be awake. Suggest turning on the app's keep-awake setting.
- They should click "Run now" on one task once, so the tool approvals are saved and later runs don't stall on a prompt.

### Claude Code CLI

Headless command:

```
claude -p "Use the burn skill to do a scheduled Burn Rate run." --permission-mode acceptEdits
```

Runs need to use git, gh and provider CLIs without prompting. Rather than reaching for blanket bypass flags, set up an allowlist in the burn home's `.claude/settings.json` (it covers every project under `workspace/`) (`permissions.allow` for `Bash(git *)`, `Bash(gh *)`, `Bash(npm *)`, `Bash(python *)`, the enabled provider CLIs, and so on). Show the user the list and get an OK before writing it.

- **macOS/Linux**: a crontab line per slot, e.g. `0 22 * * 4 cd ~/.burn-rate && claude -p "..." >> ~/.burn-rate/cron.log 2>&1`
- **Windows**: Task Scheduler, one weekly trigger per slot:
  ```
  schtasks /Create /TN "BurnRate\run-1" /SC WEEKLY /D THU /ST 22:00 /TR "cmd /c cd /d %USERPROFILE%\.burn-rate && claude -p \"Use the burn skill to do a scheduled Burn Rate run.\" >> %USERPROFILE%\.burn-rate\cron.log 2>&1"
  ```

Show the exact command and get an OK before creating any OS scheduled job.

### Codex

Headless command:

```
codex exec --full-auto "Use the burn skill to do a scheduled Burn Rate run."
```

Start it in the burn home (`cd ~/.burn-rate`), so the workspace clones are inside Codex's writable sandbox. `--full-auto` runs inside Codex's workspace sandbox with network access governed by the user's Codex config. The run needs network for git, gh and deploys. If Codex's sandbox blocks network, tell the user which setting to change rather than switching to a "dangerous/bypass" mode yourself.

Schedule it with cron or Task Scheduler exactly as for the Claude CLI, swapping the command. If the user's Codex install has its own automations feature, it's fine to use that instead. Check `codex --help` for what's available.

## Usage

See [budget.md](budget.md). In short: Desktop → `get_usage`; Codex → `usage.py --source codex-sessions`; CLI → `usage.py --source claude-statusline`; otherwise time-box.

## Sub-agents (for meetings)

- **Claude (both)**: use the Agent tool. One sub-agent per attendee, launched in parallel in a single message. Give each one a self-contained brief (see [meetings.md](meetings.md)).
- **Codex**: ask Codex to spawn sub-agents, one per attendee, with the same briefs. Codex sub-agents have been generally available since March 2026. If spawning isn't available in this Codex setup, use the fallback.
- **Fallback**: role-play each attendee in turn yourself, writing each position before you read the next role's charter. It's cheaper and less independent. Say in the minutes that you used the fallback.

## Notifications

See [notify.md](notify.md). Desktop can use the `PushNotification` tool directly. Everything else goes through `scripts/notify.py` (ntfy, webhook, Pushover).

## Windows notes

- Use `python` (or `py`), not `python3`, on Windows.
- In Git Bash, paths look like `/c/Users/...`. In PowerShell, `C:\Users\...`. Scripts accept either.
- Don't run `Remove-Item -Recurse` on a folder that contains junctions (`install.ps1 -Link` makes them). It can follow the junction and delete the real skills.
