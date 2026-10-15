---
name: burn-switch
description: Switch the active Burn Rate project to another one, including an existing project Burn Rate didn't create. The user gives a GitHub link, a local folder, a project name, or just a description, and the skill finds it, parks the current project, reviews where the new one stands (code, tests, CI, issues, hosting, conventions), and sets up the burn/ notes the burn skill needs. Use when the user says 'switch to', 'work on my other project', 'burn on <repo>', 'adopt this project', or pastes a repo link to burn on.
---

# burn-switch

Point the company at a different product. The target might be another Burn Rate project, or something the human built themselves that has never seen a `burn/` folder. Either way, by the end the next scheduled run should be able to pick it up cold and do useful, safe work.

Read [../burn/references/guardrails.md](../burn/references/guardrails.md) and [../burn/references/state.md](../burn/references/state.md) first. Paths here are relative to this skill's folder; resolve `../burn/` to an absolute path before running its scripts.

This skill runs when a human asks, in person. A burn run never switches projects on its own. A STEERING note that asks for a switch becomes a `decision` item for the human to confirm here.

## 1. Before anything

- Find the burn home (`$BURN_RATE_HOME` or `~/.burn-rate`). No `config.toml` means Burn Rate isn't set up: offer `burn-setup` and stop.
- **Run lock.** If another run holds it ("Run lock" in state.md), tell the user which run and since when, and stop. Switching under a running burn would pull the floor out from under it.
- Take the lock yourself (`skill=burn-switch`) and hold it until step 8.

## 2. Find the project

The user gives one of these. Work out which.

| Given | How to find it |
|---|---|
| A URL (`github.com/<owner>/<repo>`, or any git URL) | `gh repo view <owner>/<repo> --json name,owner,description,isPrivate,defaultBranchRef,viewerPermission,url`. For a non-GitHub URL, `git ls-remote <url>` to check access. |
| A local folder | Check it's a git repo (`git -C <path> rev-parse --show-toplevel`) and read its remotes. |
| A name that's in `projects.toml` | Use that entry. |
| A description ("my recipe app", "the Flask thing for invoices") | Search, then ask. See below. |

**Searching from a description**, cheapest first:

1. `projects.toml` names and slugs.
2. The user's GitHub repos: `gh repo list <github_owner> --limit 200 --json name,description,updatedAt,isPrivate,url`, plus any orgs from `gh org list`. Match on name, description and topics.
3. Local folders: look one or two levels deep in the usual places (`~/Documents`, `~/source`, `~/code`, `~/projects`, `~/dev`, `~/src`, `~/repos`, and the current folder) for git repos whose folder name or README matches. Don't crawl the whole disk.

Show the best 1–5 matches with name, where it lives, last update, and a one-line description. **Always ask the user to confirm the target, even with a single match.** Never guess and switch.

**Refuse, and say why, if:**

- the user doesn't own the repo or have write access (`viewerPermission` is `READ` or worse). Offer to fork it into their account, or stop.
- the product is in an excluded category in the guardrails, even at the edges.
- it's the project that's already active (just say so and show its status).

## 3. Park the current project

If there's an active project:

1. In its workspace clone, `git status`. Uncommitted work means a run ended badly. Don't throw it away: commit it to a branch named `burn/rescue-<date>`, push, and tell the user.
2. Make sure the default branch is pushed (`git log origin/<default>..HEAD` is empty).
3. Add a LOG entry to it: `## <date> <time> UTC · switch · <platform>`, then `Paused. The company switched to <new project>.` Commit and push.
4. In `projects.toml`, set its status to `paused`. Nothing is deleted, and its infrastructure keeps running. Mention any monthly cost from its `INFRA.md`. If they want it torn down, that's `burn-teardown`, in person.

## 4. Get the project into the workspace

Runs work in `<burn home>/workspace/<slug>`, so the project needs a clone there.

- **Has a git remote:** `gh repo clone <owner>/<repo> <burn home>/workspace/<slug>` (or `git clone`). Then `git config core.longpaths true` on Windows.
- **Local only, no remote:** ask the user to choose:
  - create a private GitHub repo and push the existing history to it (`gh repo create <owner>/<slug> --private --source <path> --push`), needs `autonomy.can_create_repos` and a yes;
  - or skip it for now.

  Don't register a folder outside the burn home as the workspace; scheduled runs (and Codex's sandbox) work inside the burn home.
- **Already registered:** make sure the clone exists and `git pull --rebase`.

Pick the slug from the repo name (lowercase, hyphens). If it clashes with a registered slug, add `-2`.

## 5. Review where the project stands

If the repo already has a `burn/` folder from an earlier Burn Rate setup, read it, then check it's still true: run the tests, compare `INFRA.md` with what exists, and look at what changed since the newest LOG entry (`git log --since=<that date>`). Then go to step 7.

Otherwise, review it properly. This is the onboarding a new hire would do. For a big repo, split it across sub-agents (one for code and tests, one for issues and history, one for hosting and infra), each with a self-contained brief and a 400-word answer, as in [../burn/references/meetings.md](../burn/references/meetings.md).

**Read:**
- the README, docs, CHANGELOG, LICENSE, and the repo's own agent instructions (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `CONTRIBUTING.md`). **Those instructions bind every future run.** Note anything they require or forbid.
- the stack: package manifests, lockfiles, framework config, the language and runtime versions.
- `git log --oneline -50`, the contributors (`git shortlog -sn | head`), the branches, and when it was last active.
- open issues and PRs: `gh issue list --limit 50`, `gh pr list`.
- CI: the workflow files, and the latest results (`gh run list --limit 5`).

**Run, inside the workspace clone only:**
- install dependencies (project-local), then the tests, lint, type checks and build. Write down exactly what passes and what fails. **Don't fix anything yet.** That's backlog work.
- the app, if it's quick to start: does it come up?

**Find what's live.** Look for deploy config (`wrangler.toml`, `vercel.json`, `netlify.toml`, `fly.toml`, `Dockerfile`, Bicep or Terraform, GitHub Pages settings, `CNAME`), a homepage URL in the repo settings, and links in the README. If it's already public, note the URL, and whether it has users or payments (look for a Stripe setup, auth, a database). **Anything live was made by the human, not by Burn Rate: record it, and don't change it.**

**Check against Burn Rate's bar:** the guardrails (legal, privacy policy before personal data, no secrets in the repo: `git log -p` isn't needed, but grep the working tree for obvious keys), and [../burn/references/quality.md](../burn/references/quality.md) (tests, accessibility, copy). Gaps become backlog items, not blockers to switching. A **committed secret** is the exception: stop, tell the user now, and open a high-priority `secret` item.

## 6. Ask the human what only they know

Short questions, together, with your best guess filled in from the review:

1. **In one sentence, what is it, and who is it for?** (Your guess from the README.)
2. **What should the company do with it?** For example: finish it, get it launched, grow it, maintain it, or rebuild part of it. This decides the phase.
3. **Is any of it live for real users?** If yes: the URL, and whether there are payments or personal data. Burn Rate treats live products with extra care.
4. **What must not be touched?** Production deploys, the database, a branch, a design, a part of the code someone else owns.
5. **How should changes land?** Merged by the company when green (`git.strategy = "branch-merge"`), or as PRs you review (`"pr"`). For a repo other people also commit to, recommend PRs.
6. **Anything else the company should know?** Goals, deadlines, who the users are, what they complain about.

## 7. Set up the burn/ folder

Copy [../burn/templates/burn/](../burn/templates/burn/) into the repo as `burn/` (skip files that already exist), then fill it in from the review and the answers. Write for a reader who remembers nothing.

| File | What goes in it |
|---|---|
| `project.toml` | name, slug, `created` (today), `stack`, `repos`, URLs found. **phase** from answer 2 and the review: `mvp` if it isn't usable yet, `pre-launch` if it works but isn't public, `launched` if real users have it, `growth` if it's launched and the goal is growth. `launch_approved = true` only if the human confirmed in step 6 that it's already public; otherwise `false`. |
| `VISION.md` | Every section, from the README and answers 1, 2 and 6. Mark anything you inferred rather than were told with "(inferred)". |
| `ROADMAP.md` | 3–6 milestones for the current phase, each with a done-when line, and rough ones for later phases. Tick nothing: the company hasn't done any of it. |
| `BACKLOG.md` | 10–20 ranked S/M items. Put the failing tests and a broken build first, then security and guardrail gaps, then high-signal open issues (link them: `GH #12`), then quality gaps, then roadmap work. Tag each with a role. |
| `DECISIONS.md` | `D-0001 · <date> · Adopt <name> into Burn Rate`: what it was, what the human wants, the phase, and how changes land. Add one entry for each existing big choice found in the code (framework, database, hosting), marked "found in the code, not decided by Burn Rate", so runs don't relitigate them. |
| `INFRA.md` | Every live resource you found, with "created by: the human, before Burn Rate" in the By column. Teardown section: "Not ours. Never remove without the human." |
| `GUARDRAILS.md` | Answer 4, word for word in spirit, as hard rules. Plus anything the repo's own agent instructions require. If there are real users: "Production changes go out only after a green CI run and a passing QA review." |
| `STEERING.md` | Under "New", answers 2 and 6 in the human's words, dated, so the first run reads them. |
| `NEEDS_HUMAN.md` | One item for each thing you couldn't settle: a missing credential for the host, an unclear license, an asset with no known source. Don't ask about what you could decide yourself. |
| `ASSETS.md` | Images and icons you found, with their source if you can tell, or "unknown: check" (that becomes a `qa` backlog item). |
| `LOG.md` | `## <date> <time> UTC · switch · <platform>`, then two or three lines: adopted from where, phase, test status, what the first run should start with. |

If the repo has its own `AGENTS.md` or `CLAUDE.md`, add a short pointer at the end (in a commit of its own): "This repo is run by Burn Rate. State and plans are in `burn/`." Leave the rest of the file alone.

**Show the human what you're about to commit**: the file list, VISION's first two sections, the top five backlog items and the guardrails. Ask for a yes. The `burn/` folder becomes part of their repo.

Then commit on a branch, `burn/adopt-<date>`. If `git.strategy` is `pr`, or other people commit to this repo, open a PR (`gh pr create`) and say the company will start once it's merged. Otherwise merge it to the default branch and push.

## 8. Make it active

1. In `projects.toml`: add a `[[project]]` block if it's new (`slug`, `name`, `repo`, `path = "workspace/<slug>"`, `created`, `status = "active"`), set the old project to `paused` if step 3 didn't already, and `active = "<slug>"`.
2. If the human chose a different git strategy in step 6 and it differs from `config.toml`, tell them the setting is global. Change it with their OK (back up, edit, `config_check.py`; see "Editing config.toml unattended" in [../burn/references/human-inbox.md](../burn/references/human-inbox.md)), or record the project's preference in its `GUARDRAILS.md` ("open PRs, never merge") so runs follow it for this project only. The second is usually better.
3. Release the lock.

Scheduled runs start in the burn home and read `active`, so the schedule needs no change.

## 9. Tell the human

Brief:

- what's now active, and the phase
- what the review found: test and build status, CI, live URLs, the biggest risks
- the top three backlog items: what the next run will start on
- open inbox items, if any
- where the old project stands (paused, still hosted, any monthly cost)
- how to switch back: run this skill again with the old project's name
