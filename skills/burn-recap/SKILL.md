---
name: burn-recap
description: Write or show the weekly Burn Rate recap for one usage week (what shipped, decisions, budget burned, open human items, retro, next week's plan). The burn skill uses it on the last run of the week; users run it to see the latest recap or a given week's, and it rebuilds a missing one from the log and git history. Use when the user asks for the recap, the weekend summary, or what happened last week.
---

# burn-recap: the weekly recap

One recap per usage week, in the product repo at `burn/recaps/<reset date>.md`. The reset date is the UTC date of the weekly reset that **ends** the week, as `YYYY-MM-DD`. The week runs from the previous reset (7 days earlier) to that reset.

Two modes:

- **Writing a recap**: called by the `burn` skill at the end of the last run of the week (step 7 of `../burn/SKILL.md`).
- **Showing a recap**: the user asks for it, usually on Monday. Show the latest one, or the week they name. If that week has no recap, build it first.

Paths here are relative to this skill's folder. The shared library is in `../burn/`: [state](../burn/references/state.md), [human inbox](../burn/references/human-inbox.md), [budget](../burn/references/budget.md), [meetings](../burn/references/meetings.md), [notifications](../burn/references/notify.md), [style](../burn/references/style.md). The template is [../burn/templates/recap.md](../burn/templates/recap.md).

Follow [../burn/references/guardrails.md](../burn/references/guardrails.md). In particular: no secrets in a recap, and be honest. A thin week gets a short, plain recap, not a padded one.

## Find the week

1. Read `config.toml` in the burn home (`$BURN_RATE_HOME` or `~/.burn-rate`) and `projects.toml` for the active project. `cd` into its workspace clone and `git pull --rebase`.
2. Get the reset time that ends the week:
   - From `burn`: use `resets_at` from this run's usage reading.
   - Otherwise: use the latest usage reading ([budget.md](../burn/references/budget.md), step 1), or `schedule.weekly_reset` in config. A reset that is still in the future means that week isn't over yet; the latest *finished* week ended 7 days earlier.
3. `week_end` = that reset. `week_start` = `week_end` minus 7 days. The file is `burn/recaps/<week_end as YYYY-MM-DD>.md`.

Example: reset is Sat 2026-10-17 13:59 UTC. The week is 2026-10-10 13:59 to 2026-10-17 13:59, and the file is `burn/recaps/2026-10-17.md`.

## Gather the material

Everything comes from files and git. Nothing comes from memory.

| Source | What to take |
|---|---|
| `burn/LOG.md` | Entries dated inside the week: runs, weekly % start and end per run, items done, what shipped, skips and failures. |
| `git log --since=<week_start> --until=<week_end> --oneline --no-merges` on the default branch | The changelog. Item IDs (`B-0042: ...`) tie commits to backlog items. Also check merged PRs: `gh pr list --state merged --search "merged:>=<week_start date>"`. |
| `burn/BACKLOG.md` | Done items with dates in the week, each with its role (eng, product, design, growth, ops, research). Top of "Up next" for the plan. |
| `burn/DECISIONS.md` | Entries dated in the week. |
| `burn/meetings/` | Files whose date is in the week. |
| `burn/NEEDS_HUMAN.md` | Every open item, oldest first. Items resolved during the week. |
| `burn/INFRA.md` | Resources created or removed in the week, the headroom table, any monthly cost. |
| `burn/project.toml`, `burn/ROADMAP.md` | Phase, milestones ticked this week, URLs. |
| `burn/SKILL_FEEDBACK.md` | Count of entries this week (for the retro line). |
| `burn/qa/` and the `QA:` lines in LOG.md | Sweep scores and their change since the previous sweep; blockers found and fixed in QA reviews; `qa` items filed. |
| Product analytics, if the project has any wired up | Real numbers only. If there's no source, say "No metrics yet". |

If a run's LOG entry is missing its usage numbers, write `?` in the budget table. Don't estimate and present it as measured.

## Write it

Copy the template and fill it in. Sections, in order:

1. **Title and headline.** `# Week ending <date> · <product name>`, then one sentence: the most important thing that happened, and the most important thing waiting on the human. Then one line with the phase, milestone progress, runs done out of scheduled, and where weekly % ended against the target.
2. **Shipped.** User-visible results, each with a link: PR, deploy URL, or commit. Merged-but-not-deployed counts; say so.
3. **Changelog.** Grouped by area: Product, Engineering, Design, Growth, Ops / infra, Research, Quality. Use the backlog item's role to pick the group. One line per change, with the item ID. Leave out empty groups.
4. **Decisions and meetings.** One line each, with the D- number or a link to the minutes.
5. **Budget.** A table, one row per run (including skipped ones), with weekly % start and end and points burned. Then a **Week** row: first start, last end, total points, and the target. Note anything that cost far more than expected.
6. **Product metrics.** Only if there are real ones.
7. **Quality.** QA review totals from the week's `QA:` log lines, and the sweep's scores with last week's in brackets. Call out anything that got worse, and any week with no sweep. See [quality.md](../burn/references/quality.md).
8. **Infra and costs.** New and removed resources, headroom above 70%, any spend, any cap changes and the NH item that approved them.
9. **Needs you.** Every open NH item: ID, type, one-line title. Put high-priority ones first and bold them. This is the one reminder a high-priority item gets ([human-inbox.md](../burn/references/human-inbox.md), "Notify"): if a high-priority item already appears in an earlier file in `burn/recaps/`, list it without the bold and write "(reminded <date>)". Link to NEEDS_HUMAN.md on GitHub.
10. **Retro.** What went well, what went badly, and one change for next week. See "The weekly retro" below.
11. **Next week.** Three to five items, in order, from the top of the backlog and the current milestone. Say which milestone they move.

Links: when the repo has a GitHub remote, link files as `https://github.com/<owner>/<repo>/blob/<default branch>/burn/...`. Otherwise use paths relative to `burn/recaps/`.

Voice, per [style.md](../burn/references/style.md): short sentences, specific numbers, item IDs, no adjectives doing the work of facts. "Shipped CSV export (B-0014), live on preview" beats "Made great progress on data features". If the week went badly, the headline says so.

Keep it to roughly one screen. Cut before you add.

## The weekly retro

This is the "Weekly retro" standing meeting from [meetings.md](../burn/references/meetings.md).

- If `meetings.enabled` is on and at least 6 points of budget remain before `stop_weekly_pct`, run it as a short meeting per "Weekly retro" in meetings.md: product, eng and ops, one round. Save the minutes to `burn/meetings/<date>-weekly-retro.md` and link them from the recap.
- Otherwise write the retro yourself from the week's LOG entries and SKILL_FEEDBACK entries. Say "(written by the chair, no meeting)" at the end of the section.

Either way, the retro is three short parts: went well, went badly, one change. The change becomes a backlog item or a STEERING-style note to the next run in the LOG entry. Problems with the skills themselves go to SKILL_FEEDBACK.md, not the recap.

## Writing a recap (called by burn)

1. Find the week and gather the material as above. This run's LOG entry may not be finished yet; use what you know about this run.
2. If budget allows, run the weekly retro meeting. If not, write it yourself.
3. Write `burn/recaps/<date>.md`. If a file for that week already exists (a re-run, or a manual run after the last scheduled one), update it in place rather than writing a second.
4. Leave committing to `burn`: it commits all state files in its step 7.
5. If `recap.enabled` and `recap.notify` are both true, send one notification per [notify.md](../burn/references/notify.md), after `burn` has pushed (so the link works). Title `Weekly recap`, message in one line, nothing secret:
   `3 runs, shipped CSV export + signup. Week ended at 94%. NH-004 (high) still needs you.`
   Include the GitHub link to the file if there is a remote.

If `recap.enabled` is false, skip all of this.

## Showing a recap (user asks)

1. Find the week the user means. "Latest" or nothing → the most recent finished week. A date ("the 10th", "2026-10-10") → the week that contains it. "Two weeks ago" → count back from the latest.
2. If `burn/recaps/<date>.md` exists, show it. Print it as written; don't summarize a summary. After it, add at most three lines on what changed since it was written: NH items answered since, runs since, anything newly blocked.
3. If it doesn't exist but LOG.md has entries in that week, build it (next section), then show it.
4. If the week has no LOG entries at all, say so plainly ("No runs that week. The schedule may have been off, or the app was closed.") and list the weeks that do have recaps.
5. If the user asks for "all recaps" or a list, show one line per file: date and headline.

## Building a missing recap

A week can end without a recap: the last run crashed, ran out of budget before step 7, or never ran.

1. Gather the material exactly as above. Use LOG.md, DECISIONS.md, `burn/meetings/`, NEEDS_HUMAN.md, and the git log between the two resets. Git history is the ground truth when LOG.md is missing entries.
2. Don't run a retro meeting. Write the retro yourself and mark it "(rebuilt after the week ended)".
3. Add one line under the headline: `Rebuilt on <today> from the log and git history; the last run didn't write a recap.` If you can tell why (a LOG entry that ends mid-run, a skip for budget), say why.
4. Write the file, commit it to the default branch as `recap: week ending <date> (rebuilt)`, and push. If a run is in progress (the burn home `.lock` exists and is under 6 hours old), write the file but don't commit; the running burn will pick it up.
5. Notify per the rules above only if this is the latest week and the user isn't the one who asked. If they asked, they're already reading it.

## Don'ts

- Don't invent metrics, users, or progress. "No users yet" is a fine line.
- Don't copy secrets, tokens, `.env` content, or internal-only URLs with credentials into the recap.
- Don't nag. One reminder per high-priority item, ever.
- Don't rewrite an old recap to make a week look better. Corrections go in as a dated line at the bottom: `Correction 2026-10-20: the export shipped in run 3, not run 2.`
