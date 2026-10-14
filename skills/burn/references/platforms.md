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

Install for the user. A project-scope install (`.claude/skills/` or `.agents/skills/` in one folder) only works if that folder is the burn home, because scheduled runs start there.

## Detecting the platform

Check in this order:

1. **Claude Desktop**: you have tools whose names start with `mcp__ccd_` or `mcp__scheduled-tasks__` (they may be deferred; search for them with ToolSearch). This is the richest platform. Use its tools.
2. **Claude Code CLI**: you're Claude, you have the Agent/Skill tools, and none of the Desktop tools exist.
3. **Codex**: you're running in Codex (you're an OpenAI model, there's a `~/.codex/` folder, and the instructions file convention is `AGENTS.md`).

If the detected platform differs from `config.toml`, use what you detected for this run and mention it in the log. Don't rewrite config unless the user asks (they might use both).

## Scheduling

Runs are placed relative to the weekly reset: `schedule.hours_before_reset` in config. Turn each into a real local day and time from `schedule.weekly_reset`. Example: reset Sat 13:59 UTC, slots `[36, 20, 6]` → Fri 01:59 UTC, Fri 17:59 UTC, Sat 07:59 UTC. Round to the nearest quarter hour.

Scheduled runs start in the **burn home** where the scheduler lets you set a working folder (cron, Task Scheduler, Codex), never in a project folder. Claude Desktop's scheduled tasks have no working-folder setting, and that's fine: the `burn` skill finds the burn home itself (step 0 of the burn skill is authoritative) and the active project from `projects.toml`, so renaming, switching or adding projects never breaks the schedule.

The prompt every scheduled run uses is the same:

```
Use the burn skill to do a scheduled Burn Rate run.
```

### Claude Desktop

Use the scheduled-tasks tools (`mcp__scheduled-tasks__create_scheduled_task` and friends). Create one task per slot, with weekly cron expressions in the **computer's own timezone** (the tool uses the system clock's timezone, not UTC and not `schedule.timezone`). Convert from `schedule.weekly_reset` (UTC); if the system timezone differs from `schedule.timezone`, show the user both. Example for the slots above, on a computer set to America/New_York (UTC-4):

- `burn-rate-run-1`: `0 22 * * 4` (Thu 22:00)
- `burn-rate-run-2`: `0 14 * * 5` (Fri 14:00)
- `burn-rate-run-3`: `0 4 * * 6` (Sat 04:00)

Tell the user:
- Desktop tasks only run while the app is open. A missed task runs the next time the app starts.
- Their computer needs to be awake. Suggest turning on the app's keep-awake setting.
- They should click "Run now" on one task once, so the tool approvals are saved and later runs don't stall on a prompt.
- A cron in local time drifts an hour against the UTC reset when daylight saving starts or ends. Re-check the run times after a change.
- Desktop scheduled tasks can't set environment variables, so a custom `BURN_RATE_HOME` doesn't reach scheduled runs. On Desktop, keep the burn home at the default `~/.burn-rate`, or set `BURN_RATE_HOME` system-wide for the user before the app starts.

### Claude Code CLI

Headless command:

```
<abs path to claude> -p "Use the burn skill to do a scheduled Burn Rate run." --permission-mode acceptEdits
```

cron and Task Scheduler don't load the user's shell PATH, so use the full path to the binary. Find it at setup time with `command -v claude` (macOS/Linux, Git Bash) or `where claude` (Windows), and write that into the job.

Runs need to use git, gh and provider CLIs without prompting. Rather than reaching for blanket bypass flags, set up an allowlist in the burn home's `.claude/settings.json` (it covers every project under `workspace/`) (`permissions.allow` for `Bash(git *)`, `Bash(gh *)`, `Bash(npm *)`, `Bash(python *)`, the enabled provider CLIs, and so on). Show the user the list and get an OK before writing it.

- **macOS/Linux**: a crontab line per slot, e.g. `0 22 * * 4 cd ~/.burn-rate && /usr/local/bin/claude -p "Use the burn skill to do a scheduled Burn Rate run." --permission-mode acceptEdits >> ~/.burn-rate/cron.log 2>&1`
- **Windows**: Task Scheduler, one weekly trigger per slot:
  ```
  schtasks /Create /TN "BurnRate\run-1" /SC WEEKLY /D THU /ST 22:00 /TR "cmd /c cd /d %USERPROFILE%\.burn-rate && \"C:\Users\<you>\AppData\Roaming\npm\claude.cmd\" -p \"Use the burn skill to do a scheduled Burn Rate run.\" --permission-mode acceptEdits >> %USERPROFILE%\.burn-rate\cron.log 2>&1"
  ```
  Replace the binary path with what `where claude` printed.

Show the exact command and get an OK before creating any OS scheduled job.

### Codex

Headless command:

```
<abs path to codex> exec --full-auto "Use the burn skill to do a scheduled Burn Rate run."
```

Start it in the burn home (`cd ~/.burn-rate`), so the workspace clones are inside Codex's writable sandbox. `--full-auto` runs inside Codex's workspace sandbox with network access governed by the user's Codex config. The run needs network for git, gh and deploys. If Codex's sandbox blocks network, tell the user which setting to change rather than switching to a "dangerous/bypass" mode yourself.

Schedule it with cron or Task Scheduler exactly as for the Claude CLI, swapping the command (full path from `command -v codex` or `where codex`). If the user's Codex install has its own automations feature, it's fine to use that instead. Check `codex --help` for what's available.

## Usage

See [budget.md](budget.md). In short: Desktop → `get_usage`; Codex → `usage.py --source codex-sessions`; CLI → `usage.py --source claude-statusline`; otherwise time-box.

## Sub-agents (for meetings)

- **Claude (both)**: use the Agent tool. One sub-agent per attendee, launched in parallel in a single message. Give each one a self-contained brief (see [meetings.md](meetings.md)).
- **Codex**: ask Codex to spawn sub-agents, one per attendee, with the same briefs. Codex sub-agents have been generally available since March 2026. If spawning isn't available in this Codex setup, use the fallback.
- **Fallback**: role-play each attendee in turn yourself, writing each position before you read the next role's charter. It's cheaper and less independent. Say in the minutes that you used the fallback.

## Notifications

See [notify.md](notify.md). Desktop can use the `PushNotification` tool directly. Everything else goes through `scripts/notify.py` (ntfy, webhook, Pushover).

## Manual-only skills

`burn-teardown` has `disable-model-invocation: true` in its frontmatter. Claude never picks it on its own, and the user runs it as `/burn-teardown`. Codex may ignore that key, so the skill also refuses to run unless the human asked for it in this conversation. Never invoke it from another skill, a scheduled run, or a sub-agent.

## Windows notes

- Use `python` (or `py`), not `python3`, on Windows.
- In Git Bash, paths look like `/c/Users/...`. In PowerShell, `C:\Users\...`. Python can't open `/c/...` paths: pass scripts Windows-style or forward-slash paths (`C:/Users/...`).
- Pipe secrets from Git Bash with `printf %s "$VAR" | ...`, not from Windows PowerShell 5.1, which adds a trailing newline to piped strings.
- Don't run `Remove-Item -Recurse` on a folder that contains junctions (`install.ps1 -Link` makes them). It can follow the junction and delete the real skills.
