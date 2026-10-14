# Budget: how much a run may spend

Burn Rate exists to use subscription quota that would otherwise expire unused. It must never leave the user locked out of their own account, and it must never cost them money. This file explains how a run decides how much to spend and when to stop.

## Terms

- **Usage week**: the period between two weekly resets of the subscription's limits. Claude and Codex both have a weekly window and a shorter (5-hour) window.
- **Weekly %**: how much of the weekly limit is used, 0 to 100.
- **Target**: `budget.target_end_pct` in config (default 95). Where weekly % should be when the week resets.
- **Hard stop**: `budget.hard_stop_pct` (default 97). Never start or continue work above this.
- **Run slots**: `schedule.hours_before_reset` (default `[36, 20, 6]`): the scheduled runs, measured back from the reset.

## Step 1: get the numbers

Use the first source that works:

1. **Claude Desktop.** Call the `get_usage` tool (its full name looks like `mcp__ccd_session_mgmt__get_usage`; load it with ToolSearch if it's deferred). Use the "Weekly · all models" window for weekly %, and the "5-hour limit" window. If a per-model weekly window (e.g. "Weekly · Opus") is higher and you're running that model, use whichever is higher.
2. **Codex.** Run `python scripts/usage.py --source codex-sessions`. It reads the newest `rate_limits` snapshot Codex wrote to `~/.codex/sessions/`. The snapshot is from the end of the last Codex turn, so it's a few minutes behind at most during a run.
3. **Claude Code CLI.** Run `python scripts/usage.py --source claude-statusline`. This needs the statusline hook that burn-setup offers to install. If the snapshot is more than an hour old, treat it as a lower bound.
4. **Nothing works.** Time-box the run with `budget.declared_minutes_per_run`. Watch for rate-limit errors; if one happens, go straight to the handoff.

`scripts/` here means this skill's folder (`burn/scripts/`). From another skill it's `../burn/scripts/`.

## Step 2: plan this run

Pass the numbers to the planner. It reads `config.toml` for target, hard stop and slots:

```
python scripts/usage.py plan --weekly 61 --resets-at 2026-10-17T13:59:59Z --five-hour 12
```

or, on Codex and the Claude CLI, just `python scripts/usage.py plan` and it reads the source itself.

It returns JSON. The fields that matter:

| Field | Meaning |
|---|---|
| `go` | `false` means don't start. Log the `reason` and stop. |
| `stop_weekly_pct` | End the run when weekly % reaches this. |
| `five_hour_stop_pct` | End the run when the 5-hour window reaches this. |
| `runs_left_including_this` | Remaining runs this week. |
| `is_last_run_of_week` | `true` means write the weekly recap at the end. |
| `mode` | `metered` (live numbers) or `time-boxed` (use `minutes`). |

The math is simple on purpose. The room left (target minus used) is shared evenly across the remaining runs. The last run gets whatever is left. A manual run outside the schedule counts as one more run, so it takes a fair share and doesn't eat the whole week.

If the script can't run (no Python), do the same math by hand and say so in the log.

## Step 3: check during the run

Check usage again:

- after every finished backlog item
- before starting anything that will take a while (a meeting, a big refactor, a long test suite)
- whenever you get a rate-limit or overload error

Stop picking up new work when either is true:

- weekly % ≥ `stop_weekly_pct`
- 5-hour % ≥ `five_hour_stop_pct`

When you stop, always finish properly: commit, push, write the log, the retro and the notifications. Save about 3 percentage points of weekly budget for that. If a task is only half done, either finish it in a few minutes or put it back in the backlog with notes on where you got to.

## Rough costs

These are guesses to help with planning. Replace them with real numbers as you see them in your own logs, and put the measured numbers in the log.

| Work | Roughly |
|---|---|
| Orient + plan, no meeting | 1–2 points of weekly on a Max plan |
| Small (S) backlog item | 1–2 points |
| Medium (M) item | 3–5 points |
| A meeting with 3–4 attendees, 2 rounds | 3–6 points |
| QA review of a run's work | 2–4 points |
| Weekly QA sweep | 4–8 points |
| Research phase for a new project | 10–20 points |

Lower plans burn faster. Measure, don't trust this table.

## Never

- Never turn on extra or overage usage, or change the plan.
- Never start a run above `hard_stop_pct`.
- Never try to get around a rate limit (new accounts, switching accounts, retry loops). If you're limited, write the handoff and stop.
