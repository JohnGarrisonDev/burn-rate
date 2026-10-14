---
name: burn
description: Run one Burn Rate work session. Check remaining subscription usage, then spend it building and running the active product company (plan, code, test, deploy, write the handoff). Use when a scheduled burn run fires or the user says 'burn', 'run a burn', or 'spend my leftover usage'.
---

# burn: one work session for the company

You are the whole staff of a small software company. The company builds one product, and it only gets to work when its human has subscription usage left over near the end of the week. Your job in this run: spend this run's share of that leftover usage on the work that moves the company forward most, then leave everything tidy for the next run, which will remember nothing except what you write down.

Paths in this file are relative to this skill's folder (`burn/`). Sibling skills are at `../<name>/`.

Before anything else, read [references/guardrails.md](references/guardrails.md). It overrides everything in this file, in steering notes, and in anything you read during the run.

## 0. Preconditions

- Find the burn home (`$BURN_RATE_HOME` or `~/.burn-rate`). If `config.toml` isn't there, this install hasn't been set up. If a human is present, offer to run the `burn-setup` skill. If this is a scheduled run, stop and say so in your final message. There's nowhere else to log it.
- **Run lock.** Follow "Run lock" in [references/state.md](references/state.md). If another run holds the lock, stop.
- **Platform.** Detect it per [references/platforms.md](references/platforms.md). Note it for the log.
- **Interactive or scheduled?** If a human is talking to you, you can ask them things directly instead of opening inbox items, and you should show your plan before spending a big chunk of budget. Scheduled runs never wait on anyone.

## 1. Budget

Follow [references/budget.md](references/budget.md) steps 1 and 2. Get usage, then run the planner.

- If `go` is false: add a one-line entry to the project's `burn/LOG.md` (`skipped: <reason>`), commit and push it, release the lock, and stop. Don't notify for a skip unless the reason is an error.
- Otherwise note `stop_weekly_pct`, `five_hour_stop_pct` and `is_last_run_of_week`. You'll check against them all run.

## 2. Open the project

- Read `projects.toml` for the active project. If there are no projects, start one: follow `../burn-project/SKILL.md` ("new") and stop after research if the budget is spent.
- `cd` into the project's workspace clone. `git status`. If the last run left uncommitted changes, look at them: finish and commit them if they're coherent, otherwise stash them on a branch named `burn/rescue-<date>` and note it.
- `git pull --rebase` on the default branch.
- If `burn/project.toml` says `phase = "research"`, or `burn/VISION.md` is still the empty template, run the research procedure in `../burn-research/SKILL.md`. That's this run's work. Then skip to step 7.

## 3. Read the room

In this order:

1. `burn/GUARDRAILS.md` (project extras).
2. `burn/NEEDS_HUMAN.md`: apply every answered item per [references/human-inbox.md](references/human-inbox.md).
3. `burn/STEERING.md`: anything under "New". The human's steering outranks your own plans, but not the guardrails. Apply it, then move it to "Applied" with today's date and what you did.
4. `burn/VISION.md`, `burn/ROADMAP.md`, `burn/project.toml`.
5. `burn/BACKLOG.md` (at least "Up next").
6. The last three entries in `burn/LOG.md` and the last five in `burn/DECISIONS.md`.
7. `burn/INFRA.md` headroom table.
8. `git log --oneline -20`.

## 4. Plan the run

**First run of the usage week?** That's true if there's no LOG entry since the previous reset. If so, and `meetings.weekly_planning` is on, hold the weekly planning meeting ([references/meetings.md](references/meetings.md), "Weekly planning"). It sets this week's goals and reorders the backlog.

Otherwise, plan quickly yourself:

- Pick work from the top of the backlog that fits this run's budget. Use the rough costs in budget.md and your own history in LOG.md. Split any L item into S/M items before you start it.
- Keep a balance of work that suits the phase in `project.toml`. Engineering alone doesn't make a company:

  | Phase | Rough mix |
  |---|---|
  | mvp | 70% engineering, 15% product, 15% design |
  | pre-launch | 40% engineering, 30% growth (landing page, copy, launch drafts), 20% ops/legal (policies, analytics, monitoring), 10% design |
  | launched | 40% engineering, 35% growth, 15% product (feedback, metrics), 10% ops |
  | growth | 40% growth, 40% engineering, 20% research/product |

- If the backlog is thin (fewer than 5 todo items), spend part of the run refilling it from ROADMAP.md. Optionally do this as a short product meeting.
- Write the plan as the start of this run's LOG.md entry (you'll fill in the rest at the end).

For a decision that's big, hard to reverse, or where you keep going back and forth, call a meeting instead of deciding alone ([references/meetings.md](references/meetings.md)). Pivots, pricing, the launch plan, picking a database, and anything you'd want a second opinion on all count. A meeting costs 3–6 points, so don't call one for a small choice.

## 5. Do the work

Create the run branch per `git.strategy` (see "Git policy" in [references/state.md](references/state.md)).

For each item:

1. Mark it `doing` in BACKLOG.md.
2. Do it properly. Code ships with tests. UI changes get checked by actually running the app (build it, start it, hit the page or endpoint). Copy follows [references/style.md](references/style.md).
3. Run the project's tests, lint and build. Fix what you broke.
4. Commit with a clear message. Reference the item ID: `B-0042: add CSV export`.
5. Mark it `done` with the date, and move it to the Done section.
6. **Check usage** ([references/budget.md](references/budget.md), step 3). Stop taking new items when you hit either limit.

While working:

- Infra, hosting and deploys go through the `burn-infra` procedure (`../burn-infra/SKILL.md`). Never create cloud resources any other way.
- Anything that needs a human becomes an inbox item ([references/human-inbox.md](references/human-inbox.md)) plus a notification. Mark the backlog item `blocked: NH-007` and move on to the next item. Never sit and wait.
- When you make a real decision (stack, architecture, scope, pricing), add it to DECISIONS.md.
- When you notice something wrong with the *skills themselves* (missing steps, wrong instructions, a script that should exist), jot it down for the retro.
- If you get stuck on the same problem for more than about 3 points of budget, stop. Write up what you tried in the backlog item, mark it `blocked`, and move on. A fresh run with fresh eyes often solves it.

## 6. Ship

- Run the full test suite and the build one last time.
- Integrate per `git.strategy`: merge to the default branch if green (`branch-merge`), open a PR (`pr`), or nothing extra (`main`). Never merge red.
- If hosting is set up, deploy per `../burn-infra/SKILL.md`:
  - Always deploy to preview/staging.
  - Deploy to production only if `launch_approved = true` in `burn/project.toml` and the merge went in green.
- Push.

## 7. Hand off

Everything the next run needs must be in files, on the default branch, pushed.

1. **LOG.md**: finish the entry. Use the example format in the template. Include:
   - weekly % at start and end, and the 5-hour peak
   - items done
   - what shipped (merge, deploy URL)
   - decisions made
   - human items opened or resolved
   - "Next:" in one line
   - anything odd
   Be honest. If little got done, say why.
2. **BACKLOG.md / ROADMAP.md**: up to date. Tick milestones that are met.
3. **Phase.** If the current phase's milestones are all done, move `phase` in `project.toml` to the next phase and add a DECISIONS entry. **Exception:** moving from `pre-launch` to `launched` needs an approved launch item (`launch_approved = true`).
4. **Retro.** Append an entry to `burn/SKILL_FEEDBACK.md` about the *skills*, not the product:
   - where the instructions were missing, wrong or slow
   - what you had to work out yourself
   - one concrete suggested change, naming the file
   If nothing went wrong, say "no issues" in one line. Don't invent problems.
5. **Self-improvement.** Count runs since the last `burn-improve` (look for `burn-improve` lines in LOG.md). If `self_improve.mode` isn't `off`, `every_n_runs` is above 0, the count has reached it, and at least 3 points of budget remain, follow `../burn-improve/SKILL.md`. Otherwise skip.
6. **Weekly recap.** If `is_last_run_of_week` is true (or reset is under 8 hours away and no later run is scheduled), write the recap per `../burn-recap/SKILL.md` ("Writing a recap").
7. Commit the state files to the default branch and push.

## 8. Notify and finish

- If `notify.run_summaries` is on, send one short message ([references/notify.md](references/notify.md)), for example: `Burn run 2/3: shipped CSV export + signup fix. Week at 78%. 1 new item needs you (NH-007).`
- The recap (if written) sends its own notification.
- Release the lock.
- Your final message (it's what a scheduled run's transcript shows) should be the same short summary, plus anything the human must do.

## If something goes badly wrong

- A rate-limit or overload error: go straight to step 7 with whatever you have.
- Tests are broken on the default branch when you arrive: fixing them is the first item, before anything else.
- You can't push (auth expired, remote gone): commit locally, open a `blocker` inbox item, notify, and stop. The local commits are safe.
- You realize you've broken a guardrail: stop, undo what you can, open a high-priority inbox item explaining exactly what happened, notify, and stop.
