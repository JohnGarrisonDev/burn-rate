---
name: burn-usage
description: Show remaining subscription usage, when it resets, what the next Burn Rate run is projected to spend, and how much past burns used. Use when the user asks about usage, quota, limits, reset time, or budget for burns.
---

# burn-usage

Answer "how much do I have left, and what will Burn Rate do with it?" in a few lines. This skill only reads. It never changes config or schedules.

## Steps

Script paths below are relative to this skill's folder. Resolve the burn skill's folder (`../burn/`) to an absolute path first and run `python <abs path to burn skill>/scripts/usage.py ...`.

1. **Read usage** using the first source that works, per [../burn/references/budget.md](../burn/references/budget.md) step 1:
   - Claude Desktop: the `get_usage` tool.
   - Codex: `python ../burn/scripts/usage.py --source codex-sessions`
   - Claude Code CLI: `python ../burn/scripts/usage.py --source claude-statusline`
2. **Plan preview.** Run `python ../burn/scripts/usage.py plan` with the numbers (`--weekly`, `--resets-at`, `--five-hour` if you got them from a tool; on Claude Desktop always pass the `get_usage` numbers this way). This uses `config.toml`. Show both stops: new work ends at `stop_new_work_pct`, the run ends by `stop_weekly_pct`.
3. **Schedule.** From `config.toml` `[schedule]`, list the run times still ahead this week in the user's timezone. On Claude Desktop, cross-check with `mcp__scheduled-tasks__list_scheduled_tasks` (tasks named `burn-rate-run-*`) and show the real next run time.
4. **History.** From the active project's `burn/LOG.md`, pull weekly % at start and end for each run in the current and previous usage week.

## Output

Keep it short. Something like:

```
Weekly: 61% used, resets Sat Oct 17 09:59 EDT (in 21h)
5-hour: 12% used
Source: Claude Desktop (exact)

Burn plan: 2 runs left (Fri 2:00 PM, Sat 4:00 AM). Target is 95%, so each run gets about 17 points.
Next run would stop at 78%.

This week so far: run 1 went 35% → 61% (B-0012, B-0013, planning meeting).
Last week: ended at 94%, 3 runs, recap: burn/recaps/2026-10-10.md
```

Mention it plainly if:

- the source is stale or missing ("No live numbers; runs will time-box to 90 minutes"), with the fix (install the statusline hook, run one Codex prompt, etc.)
- usage is already past the target, so the remaining runs this week will skip
- the user is close to the 5-hour limit right now

If burn-setup hasn't run yet (no `config.toml`), still show the usage numbers, and say that burns aren't set up.
