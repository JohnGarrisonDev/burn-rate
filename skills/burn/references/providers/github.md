# GitHub

Where the company's code and state live. Always enabled. Product repos are private, CI runs on Actions, and the human reads and answers `burn/NEEDS_HUMAN.md` from the GitHub web editor.

**Good for:** private repos, CI (Actions), issues as a public feedback channel after launch, secrets for CI, GitHub Pages for a public docs or marketing site (with limits below). **Not for:** hosting the product itself on Pages (not allowed for commercial SaaS, and Pages sites are always public).

## CLI

`gh`. It's a global install, so it's a human item:

- Windows: `winget install --id GitHub.cli`
- macOS: `brew install gh`
- Linux: https://github.com/cli/cli/blob/trunk/docs/install_linux.md

## Auth check

```
gh auth status
```

Pass: "Logged in to github.com account <user>" and the token scopes. Need at least `repo` and `workflow`. Check that the account matches `github_owner` in config (or has access to that org). Fail or missing scopes: open a `secret` item:

> Run `gh auth login` (GitHub.com, HTTPS, browser), then `gh auth refresh -s workflow`. Or set `GH_TOKEN` to a fine-grained token with Contents, Workflows, Secrets, Actions and Administration (for repo creation) read/write on the burn repos.

`gh auth setup-git` makes git use the same login. Run it once if `git push` asks for credentials.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:gh"` | Human ran `gh auth login`. |
| `credential = "env:GH_TOKEN"` | gh reads `GH_TOKEN` (or `GITHUB_TOKEN`). |

Never add the `delete_repo` scope yourself. Deleting a repo is a human action.

## Free tier (GitHub Free, personal account)

Checked October 2026. Verify at https://github.com/pricing and https://docs.github.com/en/billing/concepts/product-billing/github-actions.

| Limit | Free |
|---|---|
| Private repos | unlimited |
| Actions, private repos | 2,000 minutes / month on standard runners. Windows minutes count 2x, macOS 10x. |
| Actions, public repos | free on standard runners |
| Artifact and cache storage | 500 MB (artifacts); caches 10 GB per repo |
| Packages storage | 500 MB |
| Pages | public repos only on Free (private repos need Pro); 1 GB site, 100 GB/month soft bandwidth, 10 builds/hour soft. https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits |
| Codespaces | 120 core-hours / month |

With no payment method on file, Actions stops when the minutes run out. With one, GitHub may bill overage up to the account's budget, so check.

## Usage and headroom

```
gh api /users/<user>/settings/billing/usage --jq '.usageItems[] | select(.product=="actions") | {date, quantity, unitType, netAmount}'
```

This is the enhanced billing API; it needs the `user` scope. `gh auth refresh -s user` is interactive (it opens a browser), so an unattended run never runs it: open a `secret` item asking the human to run it, and use the fallbacks below meanwhile. Older accounts may use `gh api /users/<user>/settings/billing/actions` (`total_minutes_used`, `included_minutes`). If neither works, estimate from `gh run list --limit 100 --json durationMs,createdAt` (newer gh) or from workflow durations, and mark `est.`. Org-owned repos use `/orgs/<org>/settings/billing/...`.

Keep CI small: Linux runners only, cache dependencies, `concurrency` with `cancel-in-progress: true`, and `paths-ignore` for `burn/**` so state-file commits don't trigger builds.

## Provision

```
gh repo create <github_owner>/<slug> --private --description "<one line>" --source . --remote origin --push
gh repo edit <github_owner>/<slug> --enable-wiki=false --delete-branch-on-merge
```

Always `--private`. Making a repo public is a human gate. Only create repos when `autonomy.can_create_repos = true`, and record each one in INFRA.md and `repos` in `burn/project.toml`.

Branch protection on the default branch (free for public repos; on private repos it needs Pro or a paid org, so skip it if the API refuses):

```
gh api -X PUT repos/<owner>/<slug>/branches/main/protection --input protection.json
```

## CI and deploy

- Workflows in `.github/workflows/`. A `ci.yml` that runs tests and build on every push and PR.
- Deploy workflows can call the provider CLIs with tokens from repo secrets. Prefer deploying from the run itself (the agent already has the CLI login) unless the project's DECISIONS chose CI deploys.
- Production deploy jobs use a GitHub environment named `production`. Only add or enable the production job after `launch_approved = true`.

```
gh workflow list
gh run list --limit 5
gh run watch <run-id> --exit-status
gh run view <run-id> --log-failed
```

Pages (public marketing or docs site only, from a public repo, and only after the launch is approved, because a Pages site is public the moment it's published):

```
gh api -X POST repos/<owner>/<site-repo>/pages -f build_type=workflow
```

Then deploy with the official `actions/upload-pages-artifact` and `actions/deploy-pages` actions.

## Secrets

```
printf %s "$CLOUDFLARE_API_TOKEN" | gh secret set CLOUDFLARE_API_TOKEN --repo <owner>/<slug>
printf %s "$STRIPE_TEST_KEY" | gh secret set STRIPE_SECRET_KEY --repo <owner>/<slug> --env preview
gh secret list --repo <owner>/<slug>
```

`gh secret set` reads the value from stdin when `--body` is omitted. On Windows, run these from Git Bash. Windows PowerShell 5.1 adds a trailing newline when it pipes a string to a program, and the newline becomes part of the secret. Non-secret settings go in `gh variable set`.

## Custom domain

For Pages only. Buying the domain is a human gate. With a domain the human owns, add a `CNAME` file or `gh api -X PUT repos/<owner>/<site-repo>/pages -f cname=www.example.com`, and the human sets the DNS records.

## Teardown

Only with an approved human item. Prefer archiving to deleting:

```
gh repo archive <owner>/<slug> --yes
```

Deleting (`gh repo delete <owner>/<slug> --yes`) needs the `delete_repo` scope, which only the human grants. Ask them to do it themselves from Settings > Danger zone.

## IaC

- `.github/workflows/*.yml`, `.github/dependabot.yml`.
- Pin third-party actions to a full commit SHA, and first-party ones to a major version.
- Set `permissions:` at the top of every workflow to the minimum (`contents: read` by default).

## Cost hazards

- macOS (10x) and Windows (2x) runners, and larger runners (always billed, never included).
- Scheduled workflows (`on: schedule`) every few minutes, and workflows triggered by state-file commits.
- Artifacts with the default 90-day retention. Set `retention-days: 3`.
- Codespaces and Copilot are separate products; don't turn them on.
- Packages and LFS storage past 500 MB / 1 GB.
- Making a repo public changes Actions billing (free) but is a human gate, for a different reason.
