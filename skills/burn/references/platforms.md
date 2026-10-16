# Platforms

Burn Rate runs on three platforms. The skills are the same everywhere; only the pieces below differ. `config.toml` stores which one this install uses (`platform`), but always double-check at the start of a run, because someone might run a skill from a different app.

| | Claude Desktop | Claude Code CLI | Codex |
|---|---|---|---|
| `platform` value | `claude-desktop` | `claude-cli` | `codex` |
| Skills folder (user) | `~/.claude/skills/` | `~/.claude/skills/` | `~/.codex/skills/` |
| Skills folder (project) | `.claude/skills/` | `.claude/skills/` | `.agents/skills/` |
| Project instructions file | `CLAUDE.md` | `CLAUDE.md` | `AGENTS.md` |
| Usage | `get_usage` tool (exact) | statusline hook cache | session JSONL (`usage.py`) |
| Scheduling | Desktop scheduled tasks, one per slot | one hourly job running `run_burn` (gate) | one hourly job running `run_burn` (gate) |
| Sub-agents | Agent tool | Agent tool | Codex sub-agents |
| Notifications | `PushNotification` tool, or ntfy | ntfy / webhook | ntfy / webhook |
| Image generation | Codex's image tool via `scripts/codex_image.py`, if Codex is logged in | same | built in (`$imagegen`) |

Claude Desktop's Code tab and the Claude Code CLI share the same skills folder and settings, so one install covers both.

Install for the user. A project-scope install (`.claude/skills/` or `.agents/skills/` in one folder) only works if that folder is the burn home, because scheduled runs start there.

## Detecting the platform

Check in this order:

1. **Claude Desktop**: you have tools whose names start with `mcp__ccd_` or `mcp__scheduled-tasks__` (they may be deferred; search for them with ToolSearch). This is the richest platform. Use its tools.
2. **Claude Code CLI**: you're Claude, you have the Agent/Skill tools, and none of the Desktop tools exist.
3. **Codex**: you're running in Codex (you're an OpenAI model, there's a `~/.codex/` folder, and the instructions file convention is `AGENTS.md`).

If the detected platform differs from `config.toml`, use what you detected for this run and mention it in the log. Don't rewrite config unless the user asks (they might use both).

## Scheduling

Runs are placed relative to the weekly reset: `schedule.hours_before_reset` in config. On Claude Desktop, turn each into a real local day and time from `schedule.weekly_reset`; on the CLI and Codex, the hourly gate does this for you every hour. Example: reset Sat 13:59 UTC, slots `[36, 20, 6]` → Fri 01:59 UTC, Fri 17:59 UTC, Sat 07:59 UTC. Round to the nearest quarter hour.

Scheduled runs start in the **burn home** (the wrapper `cd`s there), never in a project folder. Claude Desktop's scheduled tasks have no working-folder setting, and that's fine: the `burn` skill finds the burn home itself (step 0 of the burn skill is authoritative) and the active project from `projects.toml`, so renaming, switching or adding projects never breaks the schedule.

Every scheduled run on Claude Desktop uses this prompt. It checks the run lock first, before the skill loads, so a run that fires while another is still working skips at almost no cost:

```
Before doing anything else, check whether another Burn Rate run is still going. Look for the run lock file `.lock` in the burn home (`$BURN_RATE_HOME` if it's set, otherwise `~/.burn-rate`). If it exists and the start time it records (a `started=` line, or a UTC timestamp on its first line) is less than 6 hours ago, another run is still working: reply with one line, `Skipped: another Burn Rate run has been running since <that time>.`, and stop. Don't load any skill, open the project or change any file. If there's no lock file, or its time is 6 or more hours old (a run that crashed), use the burn skill to do a scheduled Burn Rate run.
```

The CLI and Codex wrappers do the same check in `usage.py gate` before they start an agent, so their prompt stays short: `Use the burn skill to do a scheduled Burn Rate run.`

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

### Claude Code CLI and Codex: one hourly job

Don't create one job per slot. Create **one job that runs every hour** and calls the wrapper in this skill's `scripts/` folder:

- macOS/Linux and Git Bash: `scripts/run_burn.sh`
- Windows: `scripts/run_burn.ps1`

Each hour the wrapper runs `usage.py gate`. The gate reads usage from files, without starting an agent, and checks whether a slot from `schedule.hours_before_reset` is due. Most hours it isn't, and the wrapper exits having spent nothing. When a slot is due, it records the slot in `<burn home>/cache/gate.json` and starts the agent with the right flags. If several slots were missed (the computer was asleep), they collapse into one run.

This matters most on Codex: its weekly window starts at the first use after the previous window expires, so the reset time moves. A fixed weekly cron would drift; the hourly gate just follows the reset. When no Codex window is active, the gate starts a burn, which opens a new window.

Logs go to `<burn home>/logs/YYYY-MM-DD.log`: one `gate:` line per hour, plus the agent's output when a run happens. `run_burn.sh --force` (or `run_burn.ps1 -Force`) skips the gate for a manual test.

cron and Task Scheduler don't load the user's shell PATH. If `claude` or `codex` isn't found, set `BURN_CLAUDE_BIN` or `BURN_CODEX_BIN` in the job to the full path (`command -v claude` / `where claude`).

**macOS/Linux** (crontab):

```
7 * * * * BURN_RATE_HOME="$HOME/.burn-rate" /bin/sh "<abs path to burn skill>/scripts/run_burn.sh"
```

**Windows** (Task Scheduler, from PowerShell):

```powershell
$a = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "<abs path to burn skill>\scripts\run_burn.ps1"'
$t = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(7) -RepetitionInterval (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName 'BurnRate\gate' -Action $a -Trigger $t -Settings (New-ScheduledTaskSettingsSet -StartWhenAvailable)
```

Show the exact job and get an OK before creating it. To pause burns, disable that one job.

### What the wrapper runs

Claude Code CLI:

```
<claude> -p "Use the burn skill to do a scheduled Burn Rate run." --permission-mode acceptEdits
```

Runs need to use git, gh and provider CLIs without prompting. Rather than reaching for blanket bypass flags, set up an allowlist in the burn home's `.claude/settings.json` (it covers every project under `workspace/`): `permissions.allow` for `Bash(git *)`, `Bash(gh *)`, `Bash(npm *)`, `Bash(npx *)`, `Bash(python *)`, the enabled provider CLIs, and so on. Show the user the list and get an OK before writing it.

Codex (tested with codex-cli 0.162):

```
<codex> --search exec --skip-git-repo-check --approve-for-me -c sandbox_workspace_write.network_access=true -C <burn home> "Use the burn skill to do a scheduled Burn Rate run." < /dev/null
```

- `--search` is a top-level flag, so it goes **before** `exec`. It turns on web search, which research and market checks need.
- `--approve-for-me` runs in the workspace-write sandbox and sends approval requests to Codex's automatic reviewer instead of waiting for a human. Don't combine it with `-s/--sandbox`; Codex rejects the pair. Older Codex versions used `--full-auto` for this. If `codex exec --help` doesn't list `--approve-for-me`, use whichever unattended workspace-write option it does list, and update the wrapper.
- `-c sandbox_workspace_write.network_access=true` lets git, gh, npm and deploy CLIs reach the network. The log banner should say `(network access enabled)`.
- `-C <burn home>` starts in the burn home, so the workspace clones are inside the writable sandbox. The burn home isn't a git repo, hence `--skip-git-repo-check`.
- stdin is closed: `codex exec` otherwise waits to read extra input.

Never use `--dangerously-bypass-approvals-and-sandbox` for burns. If the sandbox blocks something a run genuinely needs, tell the user which setting to change.

On Windows, Git operations inside the Codex sandbox occasionally fail with `CreateFileMapping ... Access is denied`. Retry the command once before treating it as a real failure.

## Usage

See [budget.md](budget.md). In short: Desktop → `get_usage`; Codex → `usage.py --source codex-sessions`; CLI → `usage.py --source claude-statusline`; otherwise time-box.

## Sub-agents (for meetings)

- **Claude (both)**: use the Agent tool. One sub-agent per attendee, launched in parallel in a single message. Give each one a self-contained brief (see [meetings.md](meetings.md)).
- **Codex**: ask Codex to spawn sub-agents, one per attendee, with the same briefs. Codex may limit how many children run at once (3 in testing). If a meeting has more attendees, run them in two batches with full briefs each; that's still independent and better than the fallback. Codex sub-agents have been generally available since March 2026. If spawning isn't available in this Codex setup, use the fallback.
- **Fallback**: role-play each attendee in turn yourself, writing each position before you read the next role's charter. It's cheaper and less independent. Say in the minutes that you used the fallback.

## Notifications

See [notify.md](notify.md). Desktop can use the `PushNotification` tool directly. Everything else goes through `scripts/notify.py` (ntfy, webhook, Pushover).

## Manual-only skills

`burn-teardown` has `disable-model-invocation: true` in its frontmatter. Claude never picks it on its own, and the user runs it as `/burn-teardown`. Codex may ignore that key, so the skill also refuses to run unless the human asked for it in this conversation. Never invoke it from another skill, a scheduled run, or a sub-agent.

## Windows notes

- Use `python` (or `py`), not `python3`, on Windows.
- In Git Bash, paths look like `/c/Users/...`. In PowerShell, `C:\Users\...`. Python can't open `/c/...` paths: pass scripts Windows-style or forward-slash paths (`C:/Users/...`).
- State files use non-ASCII characters (`·`, `→`, `—`). Windows PowerShell 5.1 pipes text to native programs as ASCII and turns them into `?`. Write files from Python with `encoding="utf-8"`, or from Git Bash, never by piping through PowerShell 5.1. After writing a LOG heading, check that the `·` survived; the first-run-of-week check depends on it.
- Deep paths (the burn home under a long user folder, plus git's object folders) can pass Windows' 260-character limit. Set `git config core.longpaths true` in each workspace clone (repo-local, not global).
- Pipe secrets from Git Bash with `printf %s "$VAR" | ...`, not from Windows PowerShell 5.1, which adds a trailing newline to piped strings.
- Don't run `Remove-Item -Recurse` on a folder that contains junctions (`install.ps1 -Link` makes them). It can follow the junction and delete the real skills.
- Code that contains backslashes (regexes, `\n`, Windows paths) goes into a file with the Write tool, or into a raw string (`r'''...'''`) in Python. Passed through a heredoc or a plain Python string, `\\` collapses to `\` and `\b` becomes a backspace, and the file breaks without an error.
- Extra git worktrees (state on the default branch while the code branch stays checked out for the QA reviewer) work well, with three cautions:
  - give each worktree its own preview port, or e2e tests can silently hit another worktree's server;
  - don't link `node_modules` with a junction: `git worktree remove --force` follows it and deletes the real one. Run `npm ci` in the worktree, or remove the junction first (`cmd /c rmdir <worktree>\node_modules`), and stop any preview server it started;
  - remove the worktree (after committing) before switching the main clone to the default branch to merge, or `git switch` fails with "already checked out".
