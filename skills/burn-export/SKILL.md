---
name: burn-export
description: Export the active Burn Rate project into one AI-readable HANDOFF.md plus a handoff.json sidecar, for moving to another platform, machine or model. Secrets are never included; credential locations are listed so they can be recreated. Use when the user wants to export, back up, migrate or hand off the project.
---

# burn-export: write a handoff

Compile the active project's state into two files another agent can pick up cold:

- `HANDOFF.md`: for reading. Opens with a "Read this first" section that explains Burn Rate and how to continue.
- `handoff.json`: the same facts, machine-readable, for `burn-import`.

Most of the company's state already lives in the product repo's `burn/` folder ([state.md](../burn/references/state.md)). The export's real job is to capture what is **not** in the repo (the burn home's `config.toml`, `projects.toml`, the schedule) and to give a newcomer a one-file summary.

Paths here are relative to this skill's folder. The template is [../burn/templates/HANDOFF.md](../burn/templates/HANDOFF.md). Follow [../burn/references/guardrails.md](../burn/references/guardrails.md), section 3 in particular: an export is one of the places a secret must never go.

## 1. Preconditions

1. Find the burn home (`$BURN_RATE_HOME` or `~/.burn-rate`). No `config.toml` means nothing to export; say so.
2. If `.lock` in the burn home is under 6 hours old, a run is going. Tell the user and stop. Exporting mid-run captures a half-written state.
3. Read `projects.toml`. Export the active project unless the user names another slug.
4. `cd` into the project's workspace clone. Run `git status` and `git log origin/<default>..HEAD --oneline`.
   - Uncommitted changes or unpushed commits: ask the user whether to commit and push them first. The importer clones from the remote, so anything local-only won't make the trip. If they say no, carry on and list it under "Export notes".
   - Get the default branch (`git symbolic-ref --short refs/remotes/origin/HEAD`), the remote URL, and the HEAD commit.

## 2. Output location

- Default: `<burn home>/exports/<slug>-<YYYY-MM-DD>/HANDOFF.md` and `handoff.json` next to it. Create the folder.
- If the user gives a path, write there too (or only there, if they say so). Never write the export inside the product repo unless the user asks; it would be committed.
- If a folder for today exists, add a suffix: `<slug>-<date>-2`.

## 3. Collect

| From | Take |
|---|---|
| `config.toml` | Everything, then redact (step 4). |
| `projects.toml` | The active entry, plus slug, repo and status of the others. |
| `burn/project.toml` | All of it. |
| `burn/VISION.md` | The one-sentence product, who it's for, how it makes money. |
| `burn/ROADMAP.md` | The current phase's milestones with their ticks. |
| `burn/BACKLOG.md` | Every item, parsed (format below). Up next verbatim for the .md. |
| `burn/NEEDS_HUMAN.md` | Every open item, verbatim, high priority first. |
| `burn/STEERING.md` | The "New" section, verbatim. |
| `burn/LOG.md` | The last 3 entries for the .md, condensed to 2 lines each. |
| `burn/DECISIONS.md` | The last 5 titles with IDs. |
| `burn/INFRA.md` | The resources table, the headroom table. |
| The scheduler | What's scheduled today: Desktop scheduled tasks (`list_scheduled_tasks`, names starting `burn-rate-`), crontab lines or `schtasks /Query /TN "BurnRate\"` entries. Names and times only. |
| Skills version | The top version heading in the skills repo's `CHANGELOG.md` if the installed skills are a git clone or link; otherwise `unknown`. |
| Skills repo URL | `git remote get-url origin` in the skills folder if it's a clone, else `self_improve.upstream_repo`, else "the burn-rate repo you installed from". |

Backlog lines look like `- [todo] B-0042 · M · eng · Add CSV export — notes here` ([../burn/templates/burn/BACKLOG.md](../burn/templates/burn/BACKLOG.md)). Parse each into `{id, status, size, role, title, notes, section}`. Keep `blocked: NH-007` in `notes`. If a line doesn't parse, keep it as `{raw: "<line>", section}` rather than dropping it.

NH items start with `### NH-007 · cost · 2026-10-17 · <title>` ([human-inbox.md](../burn/references/human-inbox.md)). Parse into `{id, type, date, title, priority, body}`. `priority` is `"high"` if the body has `Priority: high`, else `"normal"`.

INFRA rows become `{provider, kind, name, region, tier, monthly_usd, created, by}`.

## 4. Redact

Do this before writing anything, and again on the finished files.

**Config.** Copy it, then:
- Keep every `credential` and `*_from` value. They are locations (`env:NAME`, `cli:gh`), not secrets. They go into the credentials table.
- Replace `notify.ntfy_topic` with `"[redacted]"`. Anyone who knows the topic can read the notifications.
- Replace any value that looks like a secret (below) with `"[redacted]"` and note the key under "Export notes". That value shouldn't be in config at all, so also tell the user to rotate it and fix their config (`burn-configure` can check: `python ../burn/scripts/config_check.py`).

**Everything else.** Scan both output files for secret-looking strings and replace each with `[redacted]`:
- known token shapes: `sk_live_`, `sk_test_`, `rk_live_`, `ghp_`, `gho_`, `github_pat_`, `xoxb-`, `xoxp-`, `AKIA` followed by 16 caps/digits, `-----BEGIN ... PRIVATE KEY-----`
- Discord or Slack webhook URLs; any URL with `user:password@`
- lines like `KEY=value`, `token: value`, `password: value`, `secret: value` where the value is 16+ characters
- long random-looking strings (32+ characters of mixed letters and digits) that aren't a git SHA or a resource ID listed in INFRA.md

If a state file in the repo itself contains a secret, don't just redact it in the export. Follow guardrails section 3: open a high-priority human item telling the user to rotate it.

Never read `.env` files, keychains, or environment variable values to "check" a credential. You only need the location.

## 5. Write HANDOFF.md

Fill the template. Rules:
- Every `{{placeholder}}` gets a real value or `none`. Delete the template comments.
- Credentials table: one row per **enabled** provider, plus GitHub, plus each notify location that's set. "How to set it up" is the login command (`wrangler login`, `az login`, `gh auth login`) or the env var and the scope it needs. Add disabled providers only if they have a non-zero cap.
- Spending caps: one row per provider with a non-zero cap or enabled. For non-zero caps, find the approving NH item in NEEDS_HUMAN.md "Resolved" and cite its ID.
- Keep it readable on its own: an agent with no Burn Rate skills should be able to continue from this file and the repo.

## 6. Write handoff.json

```json
{
  "format": "burn-rate-handoff",
  "format_version": 1,
  "exported_at": "2026-10-18T09:12:00Z",
  "exported_from": {"platform": "claude-desktop", "skills_version": "0.1.0"},
  "skills_repo": "github.com/jdoe/burn-rate",
  "project": {
    "name": "Invoice Snap", "slug": "invoice-snap", "phase": "mvp",
    "created": "2026-10-03", "stack": "SvelteKit + Cloudflare Pages + D1",
    "repos": ["github.com/jdoe/invoice-snap"],
    "urls": {"preview": "https://invoice-snap.pages.dev", "production": ""},
    "launch_approved": false,
    "default_branch": "main", "head_commit": "3f2a9c1"
  },
  "projects_entry": {"slug": "invoice-snap", "name": "Invoice Snap", "repo": "github.com/jdoe/invoice-snap", "created": "2026-10-03", "status": "active"},
  "other_projects": [{"slug": "old-idea", "repo": "github.com/jdoe/old-idea", "status": "archived"}],
  "config": {"version": 1, "platform": "claude-desktop", "budget": {"target_end_pct": 95}, "notify": {"ntfy_topic": "[redacted]"}},
  "platform_specific": ["platform", "budget.usage_source", "notify.channel", "schedule.weekly_reset"],
  "credentials": [
    {"for": "cloudflare", "key": "providers.cloudflare.credential", "location": "cli:wrangler", "setup": "wrangler login"}
  ],
  "schedule": {"hours_before_reset": [36, 20, 6], "timezone": "America/New_York", "weekly_reset": "Sat 13:59 UTC",
               "old_jobs": ["burn-rate-run-1 Thu 22:00", "burn-rate-run-2 Fri 14:00", "burn-rate-run-3 Sat 04:00"]},
  "backlog": [{"id": "B-0024", "status": "todo", "size": "M", "role": "eng", "title": "Cache invoice reads", "notes": "", "section": "Up next"}],
  "needs_human_open": [{"id": "NH-004", "type": "cost", "date": "2026-10-16", "title": "Cloudflare D1 will hit its free row limit in ~2 weeks", "priority": "high", "body": "..."}],
  "infra": [{"provider": "cloudflare", "kind": "D1", "name": "invoice-snap-prod", "region": "auto", "tier": "free", "monthly_usd": 0, "created": "2026-10-12", "by": "run 2026-10-12-1"}],
  "redactions": ["notify.ntfy_topic"]
}
```

The example shows a trimmed `config`; write the whole redacted config. Write valid JSON (UTF-8, 2-space indent). Check it parses: `python -c "import json,sys; json.load(open(sys.argv[1], encoding='utf-8'))" handoff.json`.

## 7. Finish

1. Run the secret scan from step 4 on both files one last time.
2. Tell the user, in a few lines:
   - where the files are
   - what to do on the new machine: install the skills, then run `burn-import` with the HANDOFF.md path
   - the credentials they'll need to set up there
   - to turn off the old schedule once the new one runs (list the jobs)
   - anything under "Export notes"
3. Add a one-line entry to the project's `burn/LOG.md`: `## <date> <time> UTC · export · <platform>` / `Exported to <burn home>/exports/<folder>. No state changed.` Commit it to the default branch and push. Don't commit the export itself.

Exporting changes nothing else. It doesn't stop the schedule or archive the project; the user decides when to switch over.
