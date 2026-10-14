---
name: burn-project
description: Manage Burn Rate projects. new creates a private GitHub repo, sets up the burn/ state folder and starts research; list shows every project; switch changes which project runs use; archive retires one without deleting anything. Use when the user wants a new, different or additional product, asks which projects exist, or wants to switch or shelve one.
---

# burn-project

One install runs one active project at a time. Projects are listed in `projects.toml` in the burn home; each one is a private GitHub repo cloned to `workspace/<slug>`. Formats for both are in [../burn/references/state.md](../burn/references/state.md). Read [../burn/references/guardrails.md](../burn/references/guardrails.md) before changing anything.

Subcommands: `new`, `list`, `switch <slug>`, `archive <slug>`. If the user doesn't name one, work out which from what they said, or show `list`.

**Before any change** (`new`, `switch`, `archive`): find the burn home (`$BURN_RATE_HOME` or `~/.burn-rate`). If `config.toml` isn't there, offer to run `burn-setup` and stop. If a burn run called you, it already holds the run lock. Otherwise, check the lock per "Run lock" in state.md: if a run is going, tell the user and stop.

## new

Called by the user, by a STEERING note asking for a new product, by `burn-setup`, or by a burn run that found no projects.

### 1. Pick a slug

If the product's name is already known (the user gave one), slugify it: lowercase, hyphens, no more than 30 characters. Otherwise use a temporary slug, `project-YYYY-MM-DD` (today's date). Research renames it later. If the slug is already in `projects.toml`, in `workspace/`, or on GitHub, add `-2`, `-3` and so on.

### 2. Create the repo

Needs `autonomy.can_create_repos = true` in config and a logged-in `gh`.

```
gh auth status
gh repo view <owner>/<slug>          # should fail: the name is free
gh repo create <owner>/<slug> --private --description "A Burn Rate project"
gh repo clone <owner>/<slug> <burn home>/workspace/<slug>
```

`<owner>` is `github_owner` from config. If that's empty, use `gh api user --jq .login`, and write it into `github_owner` in config (keep the comments). Always `--private`. Making a repo public is a human gate.

If `can_create_repos` is false or `gh` isn't logged in, don't stop. Create the folder, `git init` it, and do steps 3–5 locally. Open a `blocker` item in `NEEDS_HUMAN.md` ([../burn/references/human-inbox.md](../burn/references/human-inbox.md)) asking the human to create the repo (give the exact `gh repo create` command, or "please run `gh auth login`"). When it's answered, a later run adds the remote with `git remote add origin` and pushes.

### 3. Seed the repo

In the clone:

1. Copy [../burn/templates/burn/](../burn/templates/burn/) to `burn/`, including the empty `meetings/`, `research/` and `recaps/` folders.
2. Fill in `burn/project.toml`: `slug`, `created` (today), `repos = ["github.com/<owner>/<slug>"]`, `phase = "research"`. Leave `name` empty unless known.
3. Add the repo to `burn/INFRA.md`: `| github | repo (private) | <owner>/<slug> | n/a | free | 0 | <date> | burn-project new |`.
4. Write a minimal `README.md`:

   ```markdown
   # <name, or the slug for now>

   A product being built and run by an AI agent with leftover subscription usage, using Burn Rate.
   Plans, decisions and the run log are in `burn/`. Leave notes for the agent in `burn/STEERING.md`.
   Answer its questions in `burn/NEEDS_HUMAN.md`.
   ```

5. Write a `.gitignore` that keeps secrets and build output out:

   ```
   .env
   .env.*
   !.env.example
   node_modules/
   dist/
   build/
   .venv/
   __pycache__/
   .wrangler/
   .vercel/
   *.log
   .DS_Store
   Thumbs.db
   ```

6. Commit and push to `main`:

   ```
   git add -A
   git commit -m "Start project <slug>"
   git branch -M main
   git push -u origin main
   ```

### 4. Register it

Edit `projects.toml` in the burn home (create it with `active = ""` if it doesn't exist). Add a `[[project]]` block with `slug`, `name` (empty if unknown), `repo`, `path = "workspace/<slug>"`, `created` and `status = "active"`. Set the old active project's status to `paused`. Set `active = "<slug>"`.

Scheduled runs start in the burn home and read `active` from `projects.toml`, so no schedule changes are needed ([../burn/references/platforms.md](../burn/references/platforms.md)).

### 5. Start research

Hand over to [../burn-research/SKILL.md](../burn-research/SKILL.md) for idea research.

- From a burn run: carry on with research in the same run, inside its budget.
- From a human: check the budget ([../burn/references/budget.md](../burn/references/budget.md)). Research takes 10–20 points over one or more runs. Tell the user, then start unless they'd rather leave it to the scheduled runs. Either way, the next burn run sees `phase = "research"` and continues it.

### Rename

Once research has named the product (stage 5 in [../burn/references/research.md](../burn/references/research.md)), give the repo a real name if it has a temporary slug.

1. Slugify the name. Check it's free: `gh repo view <owner>/<new-slug>` should fail. If it's taken, try `<new-slug>-app`, then pick something else.
2. Rename on GitHub. GitHub redirects the old URL, but update everything anyway.

   ```
   gh repo rename <new-slug> --repo <owner>/<old-slug> --yes
   git remote set-url origin https://github.com/<owner>/<new-slug>.git
   ```

   Keep the remote's existing form: if `git remote get-url origin` was SSH, use the SSH URL.
3. Update `burn/project.toml` (`name`, `slug`, `repos`) and the repo row in `burn/INFRA.md` (add "renamed from <old-slug>"). Commit `Rename project to <new-slug>` and push.
4. Move the clone: `cd` to the burn home first, then rename `workspace/<old-slug>` to `workspace/<new-slug>`. If the move fails (on Windows, an open editor or dev server can lock the folder), leave it where it is; `path` can point at the old folder name.
5. Update the project's block in `projects.toml` (`slug`, `name`, `repo`, `path`) and `active`. Schedules don't need touching.

If `can_create_repos` is false, don't rename; open a `review` item suggesting the rename command instead.

## list

Read `projects.toml`. For each project, read `phase` from its `burn/project.toml` and the date of the newest entry in its `burn/LOG.md` (skip what isn't cloned). Show a table, active first:

```
   slug                 name           phase      status     last run
*  invoice-snap         Invoice Snap   mvp        active     2026-10-17
   project-2026-09-12   (unnamed)      research   paused     2026-09-12
   tab-tidy             Tab Tidy       launched   archived   2026-08-30
```

Add open `NEEDS_HUMAN.md` counts if they're quick to get. Change nothing.

## switch \<slug\>

Only when the human asks (directly or in a STEERING note). Accept a name or a slug.

1. Find the project in `projects.toml`. If it's `archived`, confirm with the user first (a STEERING note that names it counts as confirmation).
2. Set the current active project's status to `paused`, the new one's to `active`, and `active = "<slug>"`.
3. Make sure the clone exists (`gh repo clone` it if not) and `git pull --rebase`.
4. Add a line to the new project's `burn/LOG.md`: `## <date> · switched to this project from <old-slug>`. Commit and push.
5. Tell the user the project's phase, the top three backlog items and any open human items.

## archive \<slug\>

Only when the human asks. Archiving changes a status line. It never deletes anything.

1. In the project's repo: add a DECISIONS entry (`Archive the project`, with the reason the human gave) and a LOG line. Commit and push.
2. In `projects.toml`, set `status = "archived"`. If it was active, set `active = ""` and tell the user: with no active project, the next burn run starts a new one. Suggest `switch` to another project, or pausing the schedule, if that's not what they want.
3. Read the project's `burn/INFRA.md`. List every resource that still exists and its monthly cost. These keep running. Tearing them down is a separate `burn-infra` action that needs the human's OK ([../burn-infra/SKILL.md](../burn-infra/SKILL.md)).

Never:

- delete or transfer the GitHub repo, or make it public
- delete the workspace clone
- tear down hosting, databases, DNS or anything else in `INFRA.md`

If the user wants the GitHub repo read-only, tell them they can run `gh repo archive <owner>/<slug>` themselves.
