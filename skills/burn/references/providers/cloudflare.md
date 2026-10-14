# Cloudflare

The best default for a burn company. The free plan covers static sites, serverless APIs, a SQLite database, key-value storage and DNS, and when you hit a free limit, requests fail rather than bill. Nothing costs money until someone subscribes to Workers Paid.

**Good for:** static and SSR sites (Pages, or Workers with static assets), APIs (Workers), SQL (D1), KV, cron triggers, DNS for a domain the human owns. **Not for:** long-running processes, heavy CPU per request (10 ms CPU limit on free), Postgres.

## CLI

`wrangler`, installed per project, not globally:

```
npm install --save-dev wrangler
npx wrangler --version
```

Always run it as `npx wrangler ...` from the project folder. Node.js is required. If Node isn't installed, open an `account` item asking the human to install Node.js LTS (nodejs.org, `winget install OpenJS.NodeJS.LTS`, or `brew install node`).

## Auth check

```
npx wrangler whoami
```

Pass: prints the account email and an account table with IDs. Fail: "You are not authenticated". Then open a `secret` item:

> Run `npx wrangler login` in a terminal in the project folder, or set `CLOUDFLARE_API_TOKEN` (and `CLOUDFLARE_ACCOUNT_ID`) as user environment variables. Token: dash.cloudflare.com > My Profile > API Tokens > Create Token > "Edit Cloudflare Workers" template, plus D1 Edit and Pages Edit if we use them. Limit it to the burn account.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:wrangler"` | The human ran `wrangler login` (OAuth, stored by wrangler). |
| `credential = "env:CLOUDFLARE_API_TOKEN"` | Wrangler reads `CLOUDFLARE_API_TOKEN` itself. Don't pass it on the command line. |
| `account_id_from = "env:CLOUDFLARE_ACCOUNT_ID"` | Needed with a token when the token can see more than one account. Wrangler reads it. |

The account ID isn't a secret and may go in `wrangler.toml`. The token is.

## Free tier (Workers Free plan)

Checked October 2026. Verify current limits at https://developers.cloudflare.com/workers/platform/pricing/ and https://developers.cloudflare.com/pages/platform/limits/ before relying on them.

| Limit | Free |
|---|---|
| Workers requests | 100,000 / day |
| Workers CPU time | 10 ms per invocation |
| D1 rows read | 5 million / day |
| D1 rows written | 100,000 / day |
| D1 storage | 5 GB total |
| KV reads / writes | 100,000 / day reads, 1,000 / day writes |
| R2 | 10 GB-month storage, 1M Class A, 10M Class B ops / month, free egress |
| Pages builds | 500 / month, 1 at a time, 20 min timeout |
| Pages | 100 projects, 20,000 files per site, 25 MiB per file |

Daily limits reset at 00:00 UTC. Static asset requests on Pages are free and unlimited; Pages Functions count as Workers requests.

Workers Paid is $5/month minimum per account (10M requests and 30M CPU-ms included, then usage-based). That's the usual first cost proposal.

## Usage and headroom

- D1: `npx wrangler d1 info <db-name>` shows database size and recent read/write counts. Compare rows read/written per day against the limits.
- D1 query cost while developing: `npx wrangler d1 execute <db> --remote --command "EXPLAIN QUERY PLAN ..."`, and watch `rows_read` in `--json` output of real queries. Missing indexes are the usual cause of D1 limits.
- Workers requests: GraphQL Analytics API (token needs Account Analytics: Read):

```
curl -s https://api.cloudflare.com/client/v4/graphql -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  -d '{"query":"{ viewer { accounts(filter:{accountTag:\"<account-id>\"}) { workersInvocationsAdaptive(limit:100, filter:{date_geq:\"2026-10-16\"}) { sum { requests } dimensions { scriptName date } } } } }"}'
```

  On PowerShell use `$env:CLOUDFLARE_API_TOKEN` and `curl.exe`. If the token lacks analytics scope, estimate from your own logs and mark it `est.`.
- Pages builds: `npx wrangler pages deployment list --project-name <name>` and count this month's.

Record results in the INFRA.md headroom table ([../cost-proposals.md](../cost-proposals.md)).

## Provision

Prefer config in `wrangler.toml` (or `wrangler.jsonc`) and create only what the config references:

```
npx wrangler d1 create <slug>-db                    # prints database_id; put it in wrangler.toml
npx wrangler kv namespace create <slug>-kv           # prints id; put it in wrangler.toml
npx wrangler pages project create <slug> --production-branch main
npx wrangler r2 bucket create <slug>-files           # see cost hazards first
```

Name everything with the project slug as prefix, so the inventory and teardown are obvious. Record each ID in `burn/INFRA.md` right away.

D1 schema changes go through migrations, committed to the repo:

```
npx wrangler d1 migrations create <db> add_users_table   # writes migrations/0001_add_users_table.sql
npx wrangler d1 migrations apply <db> --local            # test locally first
npx wrangler d1 migrations apply <db> --remote           # then the real database
```

## Deploy

Pages (static or framework build output):

```
npx wrangler pages deploy <build-dir> --project-name <slug> --branch preview-<run>   # preview URL
npx wrangler pages deploy <build-dir> --project-name <slug> --branch main            # production
```

Any branch other than the production branch gets a preview URL (`<hash>.<slug>.pages.dev`). The production branch serves `<slug>.pages.dev`.

Workers:

```
npx wrangler versions upload          # new version with a preview URL, no traffic shifted
npx wrangler deploy --env staging     # or a separate staging Worker defined in [env.staging]
npx wrangler deploy                   # production
```

Production only when `launch_approved = true`. Note the preview URL in LOG.md and `urls.preview` in `burn/project.toml`.

## Secrets

```
printf %s "$STRIPE_SECRET_KEY" | npx wrangler secret put STRIPE_SECRET_KEY            # Worker
printf %s "$STRIPE_SECRET_KEY" | npx wrangler pages secret put STRIPE_SECRET_KEY --project-name <slug>
npx wrangler secret list
```

On Windows, run these from Git Bash. Windows PowerShell 5.1 adds a trailing newline when it pipes a string to a program, and the newline becomes part of the secret. The value comes from an env var the human set. Never type it literally. Non-secret config goes in `[vars]` in `wrangler.toml`. Local dev secrets go in `.dev.vars`, which must be in `.gitignore`.

## Custom domain

Buying a domain is a human gate (`domain` item). Once the human owns a domain and its zone is on Cloudflare (adding a zone and changing nameservers is also theirs to do):

- Workers: add to `wrangler.toml` and deploy:
  ```toml
  routes = [{ pattern = "app.example.com", custom_domain = true }]
  ```
- Pages: dashboard > Workers & Pages > project > Custom domains, or the API `POST /accounts/{account_id}/pages/projects/{project}/domains`. If the token can't do it, open a `domain` item with the exact clicks.

Attaching a domain to production counts as the public launch unless `launch_approved = true`.

## Teardown

Only with an approved human item. Add these lines to the INFRA.md teardown section as you create things:

```
npx wrangler delete --name <worker>
npx wrangler pages project delete <slug>
npx wrangler d1 delete <slug>-db
npx wrangler kv namespace delete --namespace-id <id>
npx wrangler r2 bucket delete <slug>-files        # bucket must be empty
```

Export D1 first if there's any real data: `npx wrangler d1 export <db> --remote --output backup.sql` (gitignored, never committed if it holds personal data).

## IaC

- `wrangler.toml` (or `wrangler.jsonc`): Workers, bindings (D1, KV, R2), routes, cron triggers, `[vars]`, environments.
- `migrations/*.sql` for D1.
- `_headers`, `_redirects` for Pages.
- Pin `compatibility_date` and bump it deliberately.

## Cost hazards

- **Workers Paid** subscription ($5/month) and everything usage-based after it. Never subscribe from the dashboard or accept an "upgrade" prompt.
- **R2** needs a payment method on file before the first bucket, even within the free tier. If the account has none, using R2 is an `account` item. Once enabled, storage and operations past the free tier bill automatically.
- Paid products: Images, Stream, Argo, Load Balancing, Logpush, Spectrum. Check the pricing page before using any product not in the table above.
- Cloudflare Registrar purchases and renewals are a human gate.
- Durable Objects and Workers AI have free allowances that change often. Verify before use.
- A Worker deployed with a cron trigger every minute burns 1,440 requests a day. Fine, but count it.
