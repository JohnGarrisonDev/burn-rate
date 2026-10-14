# Neon

Serverless Postgres that scales to zero and branches like git. The free plan is permanent and needs no card, which makes it a good default database when the app runs on Vercel, Netlify, Cloudflare Workers (over HTTP or Hyperdrive) or Fly.

**Good for:** a plain Postgres database, a cheap preview database per branch, apps with idle periods. **Not for:** built-in auth or file storage (use Supabase for that bundle); heavy always-on load on free.

## CLI

`neonctl`, installed per project:

```
npm install --save-dev neonctl
npx neonctl --version
```

## Auth check

```
npx neonctl me --output json
```

Pass: JSON with your user. Fail: open a `secret` item:

> Run `npx neonctl auth`, or create an API key at console.neon.tech > Account settings > API keys (an organization or project-scoped key if available) and set it as `NEON_API_KEY`.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:neonctl"` | Human ran `neonctl auth`. |
| `credential = "env:NEON_API_KEY"` | neonctl reads it (or pass `--api-key "$NEON_API_KEY"`). |

Connection strings contain the database password. They are secrets: pipe them straight into the host's secret store.

## Free tier

Checked October 2026. Verify at https://neon.com/pricing.

| Limit | Free |
|---|---|
| Projects | 100 per account |
| Compute | 100 CU-hours per project / month |
| Storage | 1 GB per project (20 GB across the account) |
| Egress | 5 GB per project / month |
| Branches | 10 per project |
| Autoscaling | up to 2 CU |
| Scale to zero | after 5 minutes idle, always on |

When a free project runs out of compute hours, its compute suspends until the next month. The paid Launch plan is usage-based with no monthly minimum (about $0.106 per CU-hour, $0.35 per GB-month storage at the time of checking).

## Usage and headroom

```
npx neonctl projects get <project-id> --output json
```

Look for compute time, data storage and transfer fields (names like `compute_time_seconds`, `synthetic_storage_size`, `data_transfer_bytes`; they change between API versions). Convert compute seconds to CU-hours (`seconds / 3600 * average CU`). List branches with `npx neonctl branches list --project-id <id>` and count them against the 10 limit.

## Provision

```
npx neonctl projects create --name <slug> --region-id aws-us-east-2 --output json
npx neonctl set-context --project-id <project-id>     # writes .neon (gitignore it)
```

Record the project ID in INFRA.md. The default branch (`main` or `production`) is production.

## Schema and deploy

Neon has no migration format of its own. Use the app's tool and commit the files:

- Drizzle: `npx drizzle-kit generate`, then `npx drizzle-kit migrate`
- Prisma: `npx prisma migrate dev` locally, `npx prisma migrate deploy` against Neon
- Plain SQL: numbered files in `db/migrations/` run by a small script

Preview: a branch per run or per PR, copy-on-write from production, free within the branch limit:

```
npx neonctl branches create --name preview/<run> --parent main --output json
npx neonctl connection-string preview/<run> --pooled | <host secret command for the preview env>
```

Run migrations against the preview branch first, then against production. Production migrations only when `launch_approved = true`, or before launch when there are no real users. Delete preview branches when the run is done. A preview branch a run created needs no approval to delete; record it in INFRA.md under **Removed**. Never delete `main` or any branch a run didn't create:

```
npx neonctl branches delete preview/<run>
```

## Secrets

Never print a connection string. Pipe it:

```
npx neonctl connection-string main --pooled | npx wrangler secret put DATABASE_URL
npx neonctl connection-string main --pooled | npx vercel env add DATABASE_URL production
```

Use `--pooled` for serverless runtimes. On Windows, run these from Git Bash. Windows PowerShell 5.1 adds a trailing newline when it pipes a string to a program, and the newline becomes part of the secret. For local dev, write it into a gitignored `.env` and delete it at the end of the run.

## Custom domain

Not applicable. The database has no public domain of its own.

## Teardown

Only with an approved human item. Dump data first if any exists (`pg_dump "$DATABASE_URL" > backup.sql`, gitignored):

```
npx neonctl projects delete <project-id>
```

## IaC

- Migration files from the ORM or `db/migrations/`.
- A short `db/README.md` noting project ID, region and branch policy (no secrets).

## Cost hazards

- Upgrading to Launch or Scale is a plan change on a card: human gate.
- On a paid plan, branches beyond the included count bill per branch-month. Delete preview branches.
- Raising autoscaling max or disabling scale to zero multiplies compute hours.
- Long-lived connections or frequent cron pings keep compute awake and burn CU-hours. Use the pooled connection and let it sleep.
- Instant restore (history retention) bills per GB-month on paid plans. Keep the default window.
