# State: where everything lives

Burn Rate keeps no memory in the model. Every run starts cold and rebuilds its picture of the world from the files below. If it isn't written down here, the next run won't know it.

There are two places:

1. **Burn home**: settings for this machine and user. Never committed anywhere.
2. **The product repo**: the company's code and its `burn/` folder of state. This is a private GitHub repo, and it's the company's real memory.

## Burn home

Location: the `BURN_RATE_HOME` environment variable if set, otherwise `~/.burn-rate` (on Windows, `%USERPROFILE%\.burn-rate`).

```
~/.burn-rate/
  config.toml            settings: platform, budget, schedule, git, notify, providers, self-improve
  projects.toml          every project this install knows about, and which one is active
  workspace/<slug>/      local clone of each product repo; runs work here
  cache/
    claude-usage.json    last rate-limit snapshot from the Claude statusline hook (optional)
  .lock                  present while a run is going (see "Run lock")
```

`config.toml` starts as a copy of [../templates/config.toml](../templates/config.toml); every key is documented there. Use TOML because Python 3.11+ reads it with the standard library (`tomllib`) and both humans and agents can edit it safely. When you change it, edit the text and keep the comments.

`projects.toml`:

```toml
active = "invoice-snap"

[[project]]
slug = "invoice-snap"
name = "Invoice Snap"
repo = "github.com/jdoe/invoice-snap"
path = "workspace/invoice-snap"
created = "2026-10-17"
status = "active"          # active | paused | archived
```

## The product repo

The repo holds the product code wherever the stack wants it, plus one folder that belongs to Burn Rate:

```
burn/
  project.toml       name, slug, phase, repos, URLs, stack
  VISION.md          what the product is, who it's for, how it makes money, what it won't be
  ROADMAP.md         milestones by phase, each with a done-when line
  BACKLOG.md         ranked tasks with size and status
  LOG.md             one entry per run, newest first
  DECISIONS.md       numbered decisions with reasons; read before changing direction
  NEEDS_HUMAN.md     the human inbox (format in human-inbox.md)
  STEERING.md        notes from the human to the next run
  INFRA.md           every external resource that exists, and free-tier headroom
  SKILL_FEEDBACK.md  retros about the skills themselves (for burn-improve)
  GUARDRAILS.md      project-specific extra rules (can only tighten)
  research/          research notes and the idea scorecard
  meetings/          minutes, one file per meeting: YYYY-MM-DD-<topic>.md
  recaps/            one recap per usage week, named by reset date: YYYY-MM-DD.md
```

Templates for each live in [../templates/](../templates/). `burn-setup` and `burn-project new` copy them in.

### project.toml

```toml
name = "Invoice Snap"
slug = "invoice-snap"
phase = "mvp"              # research | mvp | pre-launch | launched | growth
created = "2026-10-17"
stack = "SvelteKit + Cloudflare Pages + D1"
repos = ["github.com/jdoe/invoice-snap"]
urls = { preview = "", production = "" }
launch_approved = false    # set true only by applying an approved NH item
```

### Rules for each file

| File | Who writes | Rules |
|---|---|---|
| VISION.md | research, meetings | Changing it is a pivot. Pivots need a meeting and a DECISIONS entry. |
| ROADMAP.md | planning meeting, runs | Milestones get ticked, not deleted. |
| BACKLOG.md | runs, meetings | Keep it ranked. Every item has an ID (`B-0042`), a size (S = under 30 min, M = about 1 hour, L = several hours, which must be split before you start it), a status (`todo`/`doing`/`done`/`blocked`), and a role (eng, product, design, growth, ops, research). Move done items to the "Done" section with the run date. |
| LOG.md | every run | Newest first. One entry per run, even a failed or skipped one. |
| DECISIONS.md | runs, meetings | Append only. Format: `## D-0007 · 2026-10-17 · Use D1 instead of Postgres` then context, decision, alternatives, consequences. To reverse a decision, write a new one that supersedes it. |
| NEEDS_HUMAN.md | runs write items; humans answer | See [human-inbox.md](human-inbox.md). |
| STEERING.md | humans | Runs read it at the start, apply it, then move applied notes to the "Applied" section with the date. Never delete a human's words. |
| INFRA.md | burn-infra | Every resource: provider, kind, name/ID, region, tier, monthly cost, created date, created-by run. Plus a free-tier headroom table. |
| SKILL_FEEDBACK.md | every run (retro) | Append only; burn-improve marks entries as handled. |

## Git policy for state

State files always end up on the default branch, even when the code from a run doesn't, so the human can see what's going on from GitHub.

- `git.strategy = "branch-merge"` (default): work on `burn/<YYYY-MM-DD>-<n>`, then merge to the default branch at the end of the run if tests pass. If they don't, leave the branch, write it up in LOG.md, and put a backlog item on top to fix it.
- `git.strategy = "pr"`: open a PR for the code branch and leave it for the human. Commit state-file changes straight to the default branch at the end of the run.
- `git.strategy = "main"`: commit straight to the default branch. Only for throwaway experiments.

Pull before you start (`git pull --rebase`); the human may have answered inbox items or edited steering notes on GitHub. Push at the end of every run.

## Run lock

Only one run at a time per burn home. At the start, if `~/.burn-rate/.lock` exists and is less than 6 hours old, another run is going: log a one-line "skipped, locked" entry and stop. If it's older, it's stale: delete it and carry on. Write the lock with the current UTC time and platform name. Delete it as the very last step.
