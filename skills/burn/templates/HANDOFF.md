# Burn Rate handoff: {{project_name}}

<!--
Template for burn-export. Fill every {{placeholder}}; delete these comments.
Never put a credential value in this file. Locations only (env:NAME, cli:tool).
-->

Exported {{exported_at_utc}} from {{platform}} by burn-export (skills version {{skills_version}}).
Sidecar: `handoff.json` in the same folder has the same data in machine-readable form.

## Read this first

You are picking up a running software company. Please read this section fully before doing anything.

**What Burn Rate is.** Burn Rate is a set of agent skills (`burn`, `burn-setup`, `burn-import`, and others). Near the end of each subscription usage week, a scheduled run spends the usage that would otherwise expire on building and running one small product company. Every run starts with no memory. All state lives in files, mostly in the product repo's `burn/` folder, so any agent that can read files and use git can continue the work.

**Where things are.**
- Product repo: {{repo_url}} (private), default branch `{{default_branch}}`, last commit at export `{{head_commit}}`.
- Company state: the `burn/` folder in that repo. VISION, ROADMAP, BACKLOG, LOG, DECISIONS, NEEDS_HUMAN, STEERING, INFRA, meetings, recaps. The repo is the source of truth. If this file and the repo disagree, the repo wins.
- Machine settings: `config.toml` and `projects.toml` in the burn home (`~/.burn-rate` or `$BURN_RATE_HOME`). They are not in the repo. Their contents are below, minus secrets.
- The skills: {{skills_repo_url}}.

**How to continue.**
1. Install the Burn Rate skills for your platform (`install.sh` or `install.ps1` in the skills repo).
2. Run the `burn-import` skill and point it at this file. It rebuilds the burn home, clones the repo, writes config for your platform, and recreates the schedule with the user's OK.
3. Check the credentials list below. Each one has to be set up again on the new machine. The user does the logging in.
4. Then the next scheduled `burn` run carries on from `burn/LOG.md` and `burn/BACKLOG.md`.

If you can't install the skills, you can still work: clone the repo, read `burn/LOG.md` (newest first), `burn/BACKLOG.md` and `burn/NEEDS_HUMAN.md`, and follow the rules below.

**Rules that always apply.** Never spend money above an approved cap (all caps are listed below). Never create accounts, sign in with a password, accept terms, or publish anything publicly on the user's behalf; those go to `burn/NEEDS_HUMAN.md`. Never write a secret into the repo, a log, or chat. Never build anything in the excluded categories (gambling, medical or legal advice, financial advice, adult content, weapons, drugs, surveillance, anything for children under 13, and others). The full list is `references/guardrails.md` in the `burn` skill.

## Project

| | |
|---|---|
| Name / slug | {{project_name}} / `{{slug}}` |
| Phase | {{phase}} |
| Stack | {{stack}} |
| Repos | {{repos}} |
| Preview URL | {{preview_url}} |
| Production URL | {{production_url}} |
| Launch approved | {{launch_approved}} |
| Created | {{created}} |

**Product in one sentence:** {{vision_one_sentence}}
**Who it's for:** {{vision_audience}}
**How it makes money:** {{vision_money}}

## Where it stands

{{three_to_five_sentences: phase, milestone progress, what the last run did, what's next}}

**Roadmap, current phase:**
{{current_phase_milestones_with_ticks}}

**Last runs** (from `burn/LOG.md`, newest first):
{{last_3_log_entries_condensed}}

**Recent decisions:** {{last_5_decision_titles_with_ids}}

## Backlog: up next

{{up_next_items_verbatim}}

Full backlog: `burn/BACKLOG.md`. Parsed items are in `handoff.json` under `backlog`.

## Needs the human

{{open_nh_items_verbatim_high_priority_first}}

{{or: "Nothing open."}}

## Unapplied steering

{{STEERING.md "New" section verbatim, or "None."}}

## Settings

From `config.toml`, secrets removed. Settings marked *platform* are rewritten by burn-import for the new platform. Everything else should carry over as is.

| Setting | Value | |
|---|---|---|
| platform | {{platform}} | *platform* |
| budget.target_end_pct / hard_stop_pct / five_hour_stop_pct | {{target}} / {{hard_stop}} / {{five_hour}} | |
| budget.usage_source | {{usage_source}} | *platform* |
| schedule.hours_before_reset | {{hours}} | |
| schedule.timezone / weekly_reset | {{timezone}} / {{weekly_reset}} | *platform* (reset) |
| autonomy.mode / can_create_repos | {{autonomy}} / {{can_create_repos}} | |
| git.strategy | {{git_strategy}} | |
| meetings | {{meetings_summary}} | |
| recap | {{recap_summary}} | |
| notify.channel / run_summaries | {{channel}} / {{run_summaries}} | *platform* |
| self_improve.mode / every_n_runs | {{improve_mode}} / {{every_n}} | |
| github_owner | {{github_owner}} | |

## Credentials to recreate

Values are never exported. On the new machine the user sets up each of these; the agent only checks that they work.

| Needed for | Config key | Location | How to set it up |
|---|---|---|---|
| GitHub (repo, PRs) | providers.github.credential | cli:gh | `gh auth login` |
| {{provider}} | providers.{{name}}.credential | {{location}} | {{login command or env var + scope}} |
| Notifications | notify.ntfy_topic | redacted | Copy the topic from the old config by hand, or let burn-import make a new one. |

## Spending caps

| Provider | Enabled | Monthly cap (USD) | Approved by |
|---|---|---|---|
| {{provider}} | {{enabled}} | {{cap}} | {{NH id, or "default (free tier only)"}} |

## Infrastructure

Every external resource, from `burn/INFRA.md`. These keep running after the move; nothing here needs recreating.

{{INFRA.md resources table verbatim}}

**Free-tier headroom:** {{headroom rows above 50%, or "all under 50%"}}

## Schedule on the old platform

{{e.g. "Claude Desktop scheduled tasks burn-rate-run-1..3: Thu 22:00, Fri 14:00, Sat 04:00 America/New_York." }}

Turn these off on the old machine once the new one is running, or two machines will burn the same week. Only one run can hold a burn home's lock, but two machines have two burn homes.

## Other projects on this install

{{projects.toml entries other than the active one: slug, repo, status. Or "None."}}

## Export notes

{{anything redacted and why, unpushed work, warnings. Or "Nothing unusual."}}
