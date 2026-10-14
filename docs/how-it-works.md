# How it works

## The pieces

There are three things on your machine and one on GitHub.

1. **The skills.** Folders of instructions (`SKILL.md` files) that Claude or Codex loads when they're relevant. They're installed in `~/.claude/skills/` or `~/.codex/skills/`. `burn` is the main one. It also holds the shared reference docs, templates and helper scripts the other skills use.
2. **The burn home**, `~/.burn-rate/`. Your settings (`config.toml`), the list of companies (`projects.toml`), a local clone of each company's repo, and some caches. Never committed anywhere.
3. **The schedule.** A few jobs that start your agent with a short prompt: check that no other burn is still running, then "use the burn skill to do a scheduled Burn Rate run." On Claude Desktop these are Desktop scheduled tasks. Elsewhere they're cron entries or Windows Task Scheduler tasks.
4. **The company repo**, private, on your GitHub. The product's code, plus a `burn/` folder that is the company's memory.

## Why everything is in files

The agent remembers nothing between runs. Each run starts cold, reads the `burn/` folder, does its work, and writes back what the next run needs to know. It also has upsides:

- You can read exactly what the company knows. There's no hidden state.
- You can switch from Claude to Codex (or back) and nothing is lost. `burn-export` bundles it all into one handoff document.
- You can talk to the company by editing a file, from anywhere, including the GitHub app on your phone.

## A run, step by step

1. **Lock.** Only one run at a time.
2. **Budget.** Read usage. Work out this run's share: whatever's left between now and your target (95% by default), split across the runs still to come this week. If there's nothing worth spending, log it and stop.
3. **Catch up.** Pull the repo. Apply your answers in `NEEDS_HUMAN.md` and your notes in `STEERING.md`. Read the vision, roadmap, backlog, recent log and decisions.
4. **Plan.** On the first run of the week, hold a planning meeting. Otherwise pick the top backlog items that fit the budget, balanced for the company's phase. An early product gets mostly engineering. A launched one gets a lot more marketing.
5. **Work.** One item at a time on a branch: build, test, commit, tick it off, check usage. Anything that needs you becomes an inbox item and a push notification. The run doesn't wait for you; it moves on.
6. **QA, then ship.** A separate QA reviewer (a sub-agent that didn't write the code) reviews the run's work. It runs the tests and the app, checks accessibility and copy, and lists problems by severity. Blockers get fixed or the branch doesn't merge. Once that's clear, merge. Deploy a preview. Deploy to production if you've approved the launch.
7. **Hand off.** Write the log entry, update the backlog and roadmap, and write a short retro about the skills themselves. On the last run of the week, write the recap.
8. **Notify.** One short message, if you want them.

## Meetings

When a decision is big enough, such as picking the product, planning the week, pricing, launching or pivoting, the run calls a meeting. The run chairs it. It launches one sub-agent per role (product, engineering, growth, a legal-risk reviewer, and so on), each with its own brief. They come back with positions, argue once more if they disagree, and the chair decides. Minutes go in `burn/meetings/`, decisions in `DECISIONS.md`, action items in the backlog.

Meetings cost quota, so they're capped (4 attendees and 2 rounds by default) and saved for decisions that deserve them.

## Quality

The company works to a written Definition of Done: tests for new behavior, every check green, the UI actually run and looked at on phone and desktop widths, an accessibility scan, copy that follows the style guide, and images that are real, licensed and sized properly. Every run that touches the product gets an independent QA review before it merges. Once a week there's a full sweep of the live product: core flows end to end, Lighthouse scores, broken links, a dependency audit, a read-through of every page. The scores go in the recap so you can see the trend. Before it asks you to approve a public launch, the product has to clear that bar.

## Research

A new company starts with research. The agent looks for real problems people complain about, writes up 10 to 15 ideas, and cuts them to about 5. It scores each one: is it legal and low-risk, can an agent run it without a human on call, how does it make money, who's the competition, how long will it take to build, and what will it cost to run. Then it holds a meeting and picks one. You don't approve the idea. If you hate it, say so in `STEERING.md` and it will pivot.

## Phases

`research → mvp → pre-launch → launched → growth`

The company moves to the next phase when the roadmap's milestones for the current one are done, with one exception. Going from pre-launch to launched needs your approval, because that's when the product goes public.

## Self-improvement

Every run ends with a short retro about the skills: what was missing, what was wrong, what it had to figure out alone. Every few runs, `burn-improve` reads those retros and turns the common complaints into small edits. Depending on your settings, it only suggests the edits, applies them to your copy, or (for people working on Burn Rate itself) opens a pull request. It can never edit the guardrails, the budget rules or the spending rules.
