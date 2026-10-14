---
name: burn-infra
description: Manage the Burn Rate product's hosting and infrastructure through the provider CLIs the user configured (Cloudflare, Azure, Vercel, Netlify, Fly.io, Supabase, Neon, GitHub, Stripe). Checks logins, picks a provider, provisions with infrastructure-as-code, deploys preview and (after launch approval) production, sets secrets, tracks free-tier headroom, writes cost proposals, checks drift and tears down. Every resource goes in burn/INFRA.md. Used by burn runs, and when the user asks about hosting, deploys, infra, costs or limits.
---

# burn-infra: hosting and infrastructure

You are the company's ops engineer. Everything outside the repo that the product needs (hosting, databases, DNS, CI, payments) goes through this skill, so that it's reproducible, inventoried, free unless approved, and removable.

Paths here are relative to this skill's folder. Read [../burn/references/guardrails.md](../burn/references/guardrails.md) first; sections 2 (money), 3 (secrets) and 4 (human gates) matter most here. The per-provider details (install, auth check, limits, commands, cost hazards) are in `../burn/references/providers/`:

[cloudflare](../burn/references/providers/cloudflare.md) · [azure](../burn/references/providers/azure.md) · [vercel](../burn/references/providers/vercel.md) · [netlify](../burn/references/providers/netlify.md) · [fly](../burn/references/providers/fly.md) · [supabase](../burn/references/providers/supabase.md) · [neon](../burn/references/providers/neon.md) · [github](../burn/references/providers/github.md) · [stripe](../burn/references/providers/stripe.md)

Read the provider file before you touch that provider in a run. Don't work from memory: CLIs and limits change.

**Run lock.** When `burn` calls this skill mid-run, the run already holds the lock. When the user runs it on its own, take the lock per "Run lock" in [../burn/references/state.md](../burn/references/state.md) before changing anything (if a run holds it, tell the user and stop), and release it when you're done.

## Ground rules

- Only use providers with `enabled = true` in `config.toml` **and** a passing auth check this run.
- Every resource you create goes into `burn/INFRA.md` in the same commit as the code that uses it: a row in **Resources** and a line in **Teardown**. If it isn't in INFRA.md, it shouldn't exist.
- Spend stays at or below `providers.<name>.monthly_cap_usd`. `0` means free tier only. If you can't tell whether something costs money, assume it does ([../burn/references/cost-proposals.md](../burn/references/cost-proposals.md)).
- Never create accounts, add payment methods, buy domains, accept terms, or upgrade plans. Those are human items ([../burn/references/human-inbox.md](../burn/references/human-inbox.md)).
- Secrets never touch the repo, state files, logs, commit messages or chat output. Reference env vars (`"$NAME"`, PowerShell `$env:NAME`) and pipe values into the provider's secret store.
- Prefer project-local CLIs (`npm install --save-dev wrangler`, run as `npx wrangler`). Global installs are a human item with the exact install command for their OS. If a global install already exists, use it.
- Name resources `<slug>-<purpose>` (`invoice-snap-db`, `invoice-snap-preview`) and tag them `burn-rate=<slug>` where the provider supports tags.

## 1. Auth check (start of any run that touches infra)

For each enabled provider, run the auth check from its file. All are non-interactive:

| Provider | Check |
|---|---|
| github | `gh auth status` |
| cloudflare | `npx wrangler whoami` |
| azure | `az account show` (and the subscription matches `subscription_id_from`) |
| vercel | `npx vercel whoami` |
| netlify | `npx netlify status` |
| fly | `fly auth whoami` |
| supabase | `npx supabase projects list` |
| neon | `npx neonctl me` |
| stripe | `stripe balance retrieve`, and the key is a test key unless `live_mode_approved` |

For `env:` credentials, check the variable is set without printing it: `test -n "$NAME" && echo set` or PowerShell `if ($env:NAME) { "set" }`.

Results:

- **Pass**: use it this run.
- **CLI missing**: open (or update) one `account` item listing each missing CLI with the install command for the user's OS, copied from the provider file. Carry on with what works.
- **Not logged in or token expired**: open a `secret` item with the exact login command or the env var name and the scopes it needs. Never run an interactive login yourself, and never ask for the token in chat or in a file.
- **Wrong account or subscription**: stop using that provider this run and open a high-priority `blocker` item. Deploying into the wrong account is how real money gets spent.

Notify for each new item ([../burn/references/notify.md](../burn/references/notify.md)). Mark backlog items that need the provider `blocked: NH-0xx` and move on.

## 2. Choosing a provider

When the plan needs something new (hosting, a database, file storage, a cron, email), pick in this order:

1. **Already in use** by this project (in INFRA.md). One more resource on an existing provider beats a new provider.
2. **Enabled and authenticated**, with a free tier that covers the need with room to grow. Check the free-tier table in its provider file and the current pricing page.
3. **Fits the stack** in `burn/project.toml` and the product's monetization. Vercel Hobby is non-commercial; Fly has no free tier; Supabase free projects pause when idle; Netlify's free plan charges credits per production deploy.
4. **Least lock-in** when the rest is a tie: plain Postgres over a proprietary store, static output over a platform-only runtime.

Defaults that work for most products on a $0 cap: Cloudflare Pages or Workers + D1 for the app, Neon or Supabase if it needs Postgres, GitHub for code and CI, Stripe in test mode for payments.

If the best option isn't enabled, don't use it: open a `decision` item recommending it (with why, and what the human would need to set up) and use the best enabled option meanwhile, if one exists.

Record the choice in `burn/DECISIONS.md` (`## D-0012 · 2026-10-17 · Host on Cloudflare Pages + D1`), with the alternatives and the free limits that matter. A choice of database or host is big enough for a meeting if you're unsure ([../burn/references/meetings.md](../burn/references/meetings.md)).

## 3. Provision

1. Write the infrastructure as code first, in the repo: `wrangler.toml`, `infra/main.bicep`, `vercel.json`, `netlify.toml`, `fly.toml`, `supabase/config.toml` and migrations, ORM migrations for Neon, `stripe/fixtures.json`. The provider file names the right one.
2. Check cost before creating: compare SKU/plan against the free tier. For Azure run `what-if`. Read anything an interactive `launch`/`init` command generated before you deploy it.
3. Create the resource with the provider's command, from the IaC where the CLI supports it.
4. Record it in `burn/INFRA.md` immediately:

```markdown
| Provider | Kind | Name / ID | Region | Tier | $/month | Secrets it needs (names only) | Created | By |
|---|---|---|---|---|---|---|---|---|
| cloudflare | D1 | invoice-snap-db / 4b1c...e9 | auto | free | 0 | none | 2026-10-17 | run 2026-10-17-1 |
| cloudflare | Pages | invoice-snap | global | free | 0 | SESSION_SECRET, RESEND_API_KEY | 2026-10-17 | run 2026-10-17-1 |
```

and its teardown line under **Teardown**:

```
npx wrangler d1 delete invoice-snap-db
npx wrangler pages project delete invoice-snap
```

IDs aren't secrets; connection strings and keys are. Put IDs in INFRA.md, never keys.

5. Commit the IaC and INFRA.md together: `B-0031: provision D1 database`.

## 4. Deploy

Called from step 6 of `../burn/SKILL.md`, after tests and build pass.

- **Preview, always.** Deploy every green run to a preview URL (preview branch, draft deploy, preview environment, or a separate preview app; see the provider file). Smoke-test it: fetch the main page and one API route, check the status codes and that the page isn't an error page. Write the URL in LOG.md and `urls.preview` in `burn/project.toml`.
- **Not indexed before launch.** Until `launch_approved = true`, every non-production deploy (and any production-like URL that exists before launch) sends `X-Robots-Tag: noindex` on every response, or serves a `robots.txt` with `Disallow: /`. Set it in the IaC (`_headers`, `vercel.json` headers, `netlify.toml` headers, `staticwebapp.config.json`, or the app itself) and check it in the smoke test (`curl -sI <url>` shows the header, or `curl -s <url>/robots.txt`).
- **Production, only when `launch_approved = true`** in `burn/project.toml` and the merge to the default branch went in green. Before approval, production doesn't exist or isn't announced. Attaching a custom domain, publishing GitHub Pages, or connecting a production branch to auto-deploy all count as launching.
- After a production deploy, smoke-test the production URL the same way. If it's broken, roll back with the provider's rollback or by redeploying the previous commit, then open a `blocker` item if you can't fix it this run.
- Database migrations run against preview first, then production, never edited by hand in a dashboard.
- Watch provider-specific deploy costs: one production deploy per run at most on Netlify's credit plan; Fly preview apps cost money.

## 5. Secrets

Product secrets go into the provider's secret store, from env vars the human set. The commands are in each provider file ("Secrets"). The pattern:

```
printf %s "$STRIPE_SECRET_KEY" | npx wrangler secret put STRIPE_SECRET_KEY
```

On Windows, use this form from Git Bash, not PowerShell. Windows PowerShell 5.1 adds a trailing newline when it pipes a string to a program, and the newline ends up inside the secret, which breaks it in ways that are hard to spot.

- If the env var isn't set, open a `secret` item naming the variable, where to get the value, and the minimum scope. Never invent a placeholder secret in production.
- Preview environments get test or sandbox keys. Live payment keys only after `live_mode_approved = true`, and only set by the human or from an env var they set for that purpose.
- List secret names (never values) in `burn/INFRA.md` under the resource that uses them, so a rebuild knows what to set.
- Local dev values go in a gitignored file (`.dev.vars`, `.env.local`). Check `.gitignore` covers it before writing it.

## 6. Headroom and costs (every run that deploys, and at least once a week)

Follow [../burn/references/cost-proposals.md](../burn/references/cost-proposals.md):

1. Read usage with the commands in each provider file ("Usage and headroom"). Estimate and mark `est.` where there's no API.
2. Update the **Free-tier headroom** table in INFRA.md.
3. At 70% of a free limit (or 100% within ~3 weeks at the trend), or when a block happens, or when planned work needs a paid feature: raise a `cost` item with options, monthly costs, a recommendation and what you'll do meanwhile. Keep working on what doesn't depend on it.
4. Sum `$/month` per provider and compare with `monthly_cap_usd`. At 80% of a cap, re-propose. Never exceed it.

## 7. Drift check (once per usage week, and before teardown)

Compare INFRA.md with what actually exists. Use the list commands from each provider file, for example:

```
gh repo list <github_owner> --limit 100
npx wrangler d1 list ; npx wrangler pages project list ; npx wrangler kv namespace list
az resource list --tag burn-rate=<slug> --output table
npx vercel project ls ; npx netlify sites:list
fly apps list --org <burn-org> ; npx supabase projects list ; npx neonctl projects list
```

- **In reality, not in INFRA.md**, and named for this project or tagged with its slug: you (or a past run) made it without recording it. Add the row with a note `found by drift check`, and figure out from git history and LOG.md why it exists. If it costs money without an approved cap, that's a high-priority item.
- **Not named for this project**: leave it alone. It belongs to the human or another project. Never touch it.
- **In INFRA.md, gone in reality**: mark the row `missing (drift check <date>)`, note it in LOG.md, and if the product depended on it, make restoring it the top backlog item.
- **Settings drift** (plan, SKU, region, scale) where the provider shows them: if it differs from the IaC, the IaC wins unless a DECISIONS entry says otherwise. Fix with an IaC deploy, not by hand.

## 8. Teardown

This section is for removing **specific** resources, and only with an approved human item (`review` or `decision` type, answered `APPROVED`) that names what to remove. Tearing down a **whole project** (to start over, or to free the infrastructure for another project) is the `burn-teardown` skill's job. The human runs it in person. If a run thinks that's needed, open a `decision` item suggesting it. Never tear down on your own judgment, even to save money: propose it instead.

**Exception: preview and temporary resources a run created itself** (preview deployments, preview database branches, a preview app, a scratch bucket) may be pruned without an approval once they're no longer needed. Never production, never anything holding real user data, and never anything a run didn't create (check the INFRA.md row's "By" column). Record each one in INFRA.md under **Removed** with the date and `pruned by run <id>`.

1. Run the drift check first so the list is complete.
2. Export data that matters (database dump, uploaded files) to a place the human chose. Never commit dumps with personal data.
3. Run the commands in INFRA.md **Teardown**, production last.
4. Confirm each resource is gone with the provider's list command.
5. Move the rows to a **Removed** section in INFRA.md with the date and NH ID. Keep the history.
6. Things you can't remove yourself (repo deletion, domains, the provider account, billing alerts) go in the resolution note as instructions for the human.

## When something fails

- CLI error you don't understand: read `--help` for that subcommand and the provider's docs before retrying. Don't retry a create command blindly; it can make duplicates that bill twice.
- Rate-limited or provider outage: skip infra for this run, note it in LOG.md, carry on with code.
- A command would cost money, accept terms, or needs a browser: stop. That's a human item.
- Anything you created by mistake: remove it if it's yours, free, and has no data; record both steps in INFRA.md and LOG.md. Otherwise open an item.
