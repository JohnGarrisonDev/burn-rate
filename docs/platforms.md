# Platforms

Burn Rate runs on Claude Desktop, the Claude Code CLI and Codex. The skills are identical everywhere. What changes is how usage is read, how runs get scheduled, and how you get notified. The details the agent uses are in [skills/burn/references/platforms.md](../skills/burn/references/platforms.md); this page is the human version.

## Claude Desktop

The best-supported option.

- **Install:** `./install.sh --platform claude` (or `.\install.ps1 -Platform claude`). Desktop's Code tab and the Claude Code CLI share `~/.claude/skills/`, so this covers both.
- **Where runs start:** Desktop scheduled tasks have no working-folder setting. That's fine: the `burn` skill finds `~/.burn-rate` (or `BURN_RATE_HOME`) by itself.
- **Usage:** read directly from the app, so it's exact.
- **Schedule:** Desktop scheduled tasks, one per run. They show up under "Scheduled" in the sidebar.
- **Notifications:** Desktop push notifications.

Two things to know. Scheduled tasks only run while the app is open; if it's closed, a missed task runs the next time you open it. And your computer needs to be awake. The app has a keep-awake setting.

After setup, click "Run now" on one of the tasks once. Any tool approvals you give during that run are saved, so later runs don't stop and wait for a click.

## Claude Code CLI

- **Install:** same as Desktop.
- **Usage:** Claude Code passes your rate limits to the statusline. Setup offers a small hook that saves them to `~/.burn-rate/cache/claude-usage.json` so headless runs can read them. If you already have a statusline, the hook passes everything through to it, so yours looks the same. The numbers refresh whenever you use Claude Code interactively. A headless run may see numbers a few hours old and treats them as a minimum.
- **Schedule:** cron on macOS/Linux, Task Scheduler on Windows, running `claude -p "Use the burn skill to do a scheduled Burn Rate run." --permission-mode acceptEdits` from `~/.burn-rate`. Cron and Task Scheduler don't load your shell's PATH, so setup writes the full path to `claude` (found with `command -v claude`, or `where claude` on Windows). It shows you the exact lines before adding them.
- **Permissions:** headless runs need to use git, gh, npm and your provider CLIs without asking. Runs start in `~/.burn-rate`, and setup proposes an allowlist for `~/.burn-rate/.claude/settings.json` instead of turning permissions off.
- **Notifications:** ntfy, a Discord/Slack webhook, or Pushover.

## Codex

- **Install:** `./install.sh --platform codex` puts the skills in `~/.codex/skills/`.
- **Usage:** Codex writes your rate limits into its session logs (`~/.codex/sessions/`). Burn Rate reads the newest snapshot. If you haven't used Codex recently, run any short prompt once so there's a fresh one.
- **Schedule:** cron or Task Scheduler, running `codex exec --full-auto "Use the burn skill to do a scheduled Burn Rate run."` from `~/.burn-rate`, with the full path to `codex`, as for the Claude CLI. Runs need network access for git and deploys. If your Codex sandbox blocks network, setup tells you which setting to change.
- **Meetings:** Codex sub-agents.
- **Notifications:** ntfy, a Discord/Slack webhook, or Pushover.

## User or project install

Install for your user (the default). Both install scripts also take a project scope (`--scope project`, or `-Scope project`), which puts the skills in one folder's `.claude/skills/` or `.agents/skills/`. Scheduled runs start in the burn home (`~/.burn-rate`), so a project-scope install only works if that project folder is your burn home. If you're not sure, use user scope.

## Switching platforms

Run `burn-export` on the old setup. It writes a `HANDOFF.md` (plus a JSON file) that holds everything except secrets. Install the skills on the new platform and run `burn-import` with that file. The company's repo doesn't move. Only your settings, schedule and logins need recreating.

## Not supported

claude.ai chat and other chat-only apps. A burn run needs a shell, git and command-line tools.
