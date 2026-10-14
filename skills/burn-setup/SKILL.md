---
name: burn-setup
description: First-time Burn Rate setup. Detect the platform (Claude Desktop, Claude Code CLI or Codex), check tools and logins, write the config, set up usage tracking, notifications and the weekly schedule, then start the first project. Use when the user says 'set up burn rate', 'install burn', or when no ~/.burn-rate/config.toml exists yet. Safe to re-run to repair or change a setup.
---

# burn-setup

Get a new user from "I cloned the repo" to "the company runs itself on Friday" in one sitting. Setup is always interactive: a human is here, so ask instead of guessing on anything that matters, and show what you're about to do before you do anything outside the burn home.

Read [../burn/references/guardrails.md](../burn/references/guardrails.md), [../burn/references/state.md](../burn/references/state.md) and [../burn/references/platforms.md](../burn/references/platforms.md) first.

Paths here are relative to this skill's folder. Resolve the burn skill's folder (`../burn/`) to an absolute path first and run scripts as `python <abs path to burn skill>/scripts/...`; the examples keep the short form. On Windows, give scripts Windows-style or forward-slash paths (`C:/Users/...`), not Git Bash's `/c/Users/...`, which Python can't open.

Keep the conversation short. Offer sensible defaults and let the user just say "yes". Group your questions; don't ask one at a time.

## 1. Already set up?

Look for `config.toml` in the burn home (`$BURN_RATE_HOME` or `~/.burn-rate`). If it exists, show a summary of it and ask what they want: repair, change settings (hand off to `burn-configure`), add a project (hand off to `burn-project`), or start over. Never overwrite an existing config without a clear yes. Back it up first as `config.toml.bak-<YYYY-MM-DD-HHMM>` (UTC).

## 2. Platform and tools

1. Detect the platform per platforms.md.
2. Check these. Collect the results and show them as one list:

   | Check | Command | If missing |
   |---|---|---|
   | Python 3.11+ | `python --version` (or `python3`) | Needed for the helper scripts. Point to python.org. |
   | git | `git --version` | Required. |
   | GitHub CLI, logged in | `gh auth status` | Required. Ask them to install it and run `gh auth login`. Product repos are created with it. Needs the `repo` and `workflow` scopes (`gh auth refresh -s repo,workflow` adds them; it's interactive, so they run it). |
   | Provider CLIs | Global: `az version`, `fly version`, `stripe --version`. Project-local or global: `wrangler`, `vercel`, `netlify`, `supabase`, `neonctl` (try the bare command, then `node_modules/.bin/<cli>` in the current folder). Run the probes in parallel. | Optional. Note which exist. `npx --no-install <cli> --version` can answer from npx's cache even when the CLI isn't installed anywhere; if that's the only hit, call it "available via npx (cached)", not installed. The project-local ones get installed as dev dependencies in the product repo later, so a missing one isn't a problem. Only the global ones need the user to install them. |

3. For each provider CLI that exists, check the login non-interactively (commands are in [../burn/references/providers/](../burn/references/providers/)). Don't run interactive logins yourself. If they want a provider that isn't logged in, give them the exact command to run.

Don't install anything globally yourself. Tell the user what to install and wait.

## 3. Ask the questions

Ask these together, with defaults filled in:

1. **GitHub owner** for product repos. Default: the logged-in `gh` user (`gh api user --jq .login`). Repos are always private.
2. **Timezone.** Default: detect it from the system, as an IANA name. On macOS/Linux, `readlink /etc/localtime` or `timedatectl` gives it. On Windows, `tzutil /g` gives a Windows name: map it to IANA ("Central Standard Time" → `America/Chicago`, "Eastern Standard Time" → `America/New_York`, "GMT Standard Time" → `Europe/London`), or ask if you're not sure.
3. **When to burn.** Default: three runs at 36, 20 and 6 hours before the weekly reset. Explain in one line what that means in their local time once you know the reset (step 4).
4. **Autonomy.** `act` (default: it decides and ships; only human gates wait) or `propose` (code goes up as PRs, big calls wait for them).
5. **Notifications.** On Claude Desktop the default is the built-in push; also offer an ntfy topic as a fallback, for when the push tool isn't available. Elsewhere, ntfy: generate a random topic like `burn-` plus 12 random lowercase letters and digits, and tell them to install the ntfy app and subscribe to it. Or a Discord/Slack webhook (stored as `env:BURN_WEBHOOK_URL`, never in the file), Pushover, or none.
6. **Hosting providers** to enable. Default: the ones whose CLI is installed and logged in. Plus GitHub, always. GitHub alone can't host the product (see [providers/github.md](../burn/references/providers/github.md)). If no other provider is logged in, recommend Cloudflare (`npx wrangler login`).
7. **Self-improvement.** Default `suggest`. Mention `local`, and mention `maintainer` for people developing the skills themselves.
8. **Budget.** Defaults: end the week at 95%, never above 97%. Most people keep these.

Recommend, in one or two sentences, that they use a separate cloud account or subscription for the company and set a billing alert there. The skills' spending caps are a second line of defense, not the first.

## 4. Write the burn home

1. Create the burn home folders: `workspace/`, `cache/`, `exports/`.
2. Copy [../burn/templates/config.toml](../burn/templates/config.toml) to `config.toml` and fill in their answers. Edit values in place and keep the comments.
3. Create an empty `projects.toml` (`active = ""`).
4. Validate: `python ../burn/scripts/config_check.py`. Fix anything it reports.

## 5. Usage tracking

Get the weekly reset time and record it as `schedule.weekly_reset` (e.g. `"Sat 13:59 UTC"`):

- **Claude Desktop:** call `get_usage`. Read the reset time of "Weekly · all models". Done.
- **Codex:** `python ../burn/scripts/usage.py --source codex-sessions`. If it finds nothing, ask them to run any short Codex prompt, then try again.
- **Claude Code CLI:** offer to install the statusline hook ([../burn/scripts/claude_statusline_hook.py](../burn/scripts/claude_statusline_hook.py)). Show the change before making it:
  - Read `~/.claude/settings.json`. If there's already a `statusLine.command`, save that command to `cache/statusline-wrapped.txt` so the hook passes through to it, and their statusline looks the same.
  - Set `statusLine` to `{"type": "command", "command": "python <absolute path to the hook>"}`. Write the path with forward slashes, also on Windows (`C:/Users/...`): Claude Code runs the command through bash, which eats backslashes.
  - The cache fills after their next interactive response. If they decline, runs will be time-boxed instead.

Then run `python ../burn/scripts/usage.py plan --preview` (on Desktop, pass the `get_usage` numbers with `--weekly`/`--resets-at`/`--five-hour`) and show the result, so they see what each scheduled run would get this week. `--preview` doesn't count this setup session as a run. Drop it if they choose to start research now (step 8), since then this session is a run.

On Codex, mention that the weekly window starts at the first use after the last one expires, so the reset time can move from week to week. The hourly gate (step 7) follows it.

## 6. Notifications

Send a test: on Desktop, call the `PushNotification` tool; elsewhere run `python ../burn/scripts/notify.py --title "Burn Rate" --message "Setup test. If you see this, notifications work."`. Ask if it arrived. Fix it before moving on. See [../burn/references/notify.md](../burn/references/notify.md).

## 7. Schedule

Work out the run times: take `weekly_reset`, subtract each `hours_before_reset`, convert to their local time, and round to the quarter hour. Show the list ("Thu 10:00 PM, Fri 2:00 PM, Sat 4:00 AM") and get a yes. Then create the jobs per platforms.md:

- **Claude Desktop:** one scheduled task per slot, named `burn-rate-run-1`, `-2`, `-3`, with a weekly cron. The scheduled-tasks tool runs cron in the computer's own timezone, not `schedule.timezone`. Convert from `weekly_reset` (UTC) into the system timezone for the cron, and if that differs from `schedule.timezone`, show the times in both. The prompt is `Use the burn skill to do a scheduled Burn Rate run.` Then tell them three things:
  1. Tasks only run while the app is open, and a missed one runs at the next launch.
  2. Keep the computer awake at those times.
  3. Click "Run now" on one task once, so the tool approvals are saved.
- **Claude Code CLI / Codex:** one hourly job that runs the wrapper (`../burn/scripts/run_burn.sh`, or `run_burn.ps1` on Windows), exactly as in platforms.md ("Claude Code CLI and Codex: one hourly job"). The wrapper's gate decides each hour whether a slot is due, so you don't create a job per slot. On Codex the reset moves, and the gate follows it. Show the exact crontab line or `Register-ScheduledTask` commands and create them only after a yes. If `command -v claude`/`codex` (or `where` on Windows) won't be on the scheduler's PATH, set `BURN_CLAUDE_BIN` / `BURN_CODEX_BIN` in the job. Then test it once by hand: `run_burn.sh` (or `.ps1`) without `--force` should log a `gate:` line to `<burn home>/logs/` saying when the next slot is. For Claude CLI, also propose the permission allowlist from platforms.md for the burn home's `.claude/settings.json`.

Never pick bypass-all-permissions modes for them. If headless runs need broader permissions, explain the trade-off and let them choose.

## 8. First project

Ask: start the company now (research runs in this session, using some of this week's usage), or let the first scheduled run do it?

Either way, take the run lock now ("Run lock" in [state.md](../burn/references/state.md)) and hold it until step 9. Setup changes state from here on. Then create the project via `../burn-project/SKILL.md` ("new"). This makes the private repo, the workspace clone, the state files and the `projects.toml` entry. If they chose to let the scheduled run do research, tell burn-project to **defer research**: it stops after the project is registered, and the first burn run sees `phase = "research"` and starts it.

If they said "now", research runs in this session like a burn run:

1. You already hold the run lock.
2. Use the step 5 plan's `stop_new_work_pct` and `stop_weekly_pct` as research's budget. Check usage as research goes ([budget.md](../burn/references/budget.md), step 3).
3. Go into `../burn-research/SKILL.md` ("called from burn-setup"). Stop at the end of a stage when you reach `stop_new_work_pct`; the next scheduled run resumes.
4. Write a LOG entry for it: `## <date> <time> UTC · run 1 of 1 · <platform>` with the usage numbers and the research stage reached.
5. Release the lock at step 9.

## 9. Wrap up

Finish with a short summary:

- where things live (burn home, project repo URL)
- when the next run is
- how to check in: `burn-notes` for what's happening, `burn-recap` on Mondays, `burn-usage` for budget
- that `burn/NEEDS_HUMAN.md` in the product repo is where the company will ask for things, and that they'll get a push when it does
- what's not set up yet (providers without logins, a statusline hook they declined), with the command to fix each

Tell them to re-check the run times after a daylight-saving change: a cron in local time drifts an hour against the UTC reset. `burn-configure` can move them.

Write a `burn/LOG.md` entry in the project: `## <date> <time> UTC · setup · <platform>`, then `Schedule <times>, notify <channel>.` Commit and push. If research ran in this session, release the run lock now.
