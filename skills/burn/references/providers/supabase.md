# Supabase

Postgres with auth, storage, edge functions and auto-generated APIs. The free plan is enough for an MVP and an early launch. Its two catches: a 500 MB database limit, and free projects pause after a week without activity.

**Good for:** a product that needs Postgres plus user accounts, row-level security, and file uploads without running a backend. **Not for:** high write volume or big data on free; anything that must never pause before it has traffic.

## CLI

`supabase`, installed per project:

```
npm install --save-dev supabase
npx supabase --version
```

Local development (`npx supabase start`) needs Docker. If Docker isn't installed, skip local stacks and test against a separate free staging project, or open an item asking the human to install Docker Desktop.

## Auth check

```
npx supabase projects list
```

Pass: a table of projects (possibly empty). Fail: "Access token not provided". Open a `secret` item:

> Run `npx supabase login`, or create an access token at supabase.com/dashboard/account/tokens and set it as `SUPABASE_ACCESS_TOKEN`. Use a separate Supabase organization for the burn company.

Also `npx supabase orgs list` to find the burn org ID.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:supabase"` | Human ran `supabase login`. |
| `credential = "env:SUPABASE_ACCESS_TOKEN"` | The CLI reads it. This is a management token for the whole account: treat it as highly sensitive. |

Per project there are more secrets: the database password, the `service_role` key, and the JWT secret. They go to the hosting provider's secret store, never to the repo. The `anon` (publishable) key is safe in front-end code only when row-level security is on for every table.

## Free tier

Checked October 2026. Verify at https://supabase.com/pricing.

| Limit | Free |
|---|---|
| Active projects | 2 per organization |
| Database size | 500 MB per project (read-only beyond) |
| Egress | 5 GB / month |
| File storage | 1 GB |
| Monthly active users (auth) | 50,000 |
| Edge function invocations | 500,000 / month |
| Inactivity | project pauses after 1 week without activity |

Pro is $25/month per organization, with a spend cap on by default.

## Usage and headroom

```
npx supabase inspect db db-stats --linked        # database size, cache hit rates
npx supabase inspect db table-sizes --linked     # where the space goes
npx supabase inspect db outliers --linked        # slow queries worth fixing
```

Egress, storage and MAU numbers are on the dashboard (Organization > Usage). The Management API (`https://api.supabase.com/v1/...`, bearer `SUPABASE_ACCESS_TOKEN`) has project endpoints; if usage isn't available there, estimate and mark `est.`.

Pausing: while there are no real users, a weekly scheduled run touching the database is enough to keep it awake. Never set up a keep-alive ping just to dodge the policy once real users exist; if pausing matters, that's a Pro proposal.

## Provision

Creating a project needs a database password. Ask the human to generate one and set it as `SUPABASE_DB_PASSWORD` (a `secret` item). Don't invent one yourself: a password only you saw is lost at the end of the run.


```
npx supabase projects create <slug> --org-id <org-id> --db-password "$SUPABASE_DB_PASSWORD" --region us-east-1
npx supabase init                                    # creates supabase/ in the repo
npx supabase link --project-ref <ref> --password "$SUPABASE_DB_PASSWORD"
```

Two free projects per org: use one for production. Use the second as staging only if you have no Docker for local testing, and record that in DECISIONS.

## Schema and deploy

Migrations are the source of truth. Never change the remote schema from the dashboard or with ad hoc SQL.

```
npx supabase migration new add_invoices          # supabase/migrations/<timestamp>_add_invoices.sql
npx supabase db reset                            # local: rebuild from migrations + seed.sql (needs Docker)
npx supabase db push --dry-run                   # show what would run on the linked project
npx supabase db push                             # apply to the linked project
npx supabase gen types typescript --linked > src/lib/db.types.ts
```

Every new table gets row-level security enabled in the same migration. Pushing to the production project counts as a production deploy: do it only when `launch_approved = true`, or before launch when the project has no real users.

Edge functions:

```
npx supabase functions deploy <name> --project-ref <ref>
```

Branching (per-PR preview databases) is a paid feature. On free, preview = local stack or the staging project.

## Secrets

```
printf 'STRIPE_SECRET_KEY=%s\n' "$STRIPE_SECRET_KEY" > supabase/.env.functions   # gitignored
npx supabase secrets set --env-file supabase/.env.functions --project-ref <ref>
rm supabase/.env.functions
npx supabase secrets list --project-ref <ref>
```

Get project keys for the hosting provider with `npx supabase projects api-keys --project-ref <ref>` and pipe them straight into the host's secret command. Don't print them in the transcript.

## Custom domain

Custom domains for the Supabase API are a paid add-on. The product's own domain lives on the web host, not here. Auth redirect URLs (Site URL, Additional Redirect URLs) must be updated when the product domain changes: `supabase/config.toml` `[auth] site_url`, then `npx supabase config push`.

## Teardown

Only with an approved human item. Dump the data first if there is any:

```
npx supabase db dump --linked -f backup.sql --data-only     # gitignored; never commit personal data
npx supabase projects delete <ref>
```

## IaC

- `supabase/config.toml`: auth, storage, API settings (`supabase config push`).
- `supabase/migrations/*.sql`, `supabase/seed.sql`.
- `supabase/functions/<name>/`.

## Cost hazards

- **Pro upgrade** is per organization and starts at $25/month. Compute add-ons, PITR, custom domains, IPv4 add-on, and read replicas each add more.
- On Pro, turning the spend cap **off** makes usage open-ended. Never touch it; it's a proposal option.
- A third project in an org on free is refused; on Pro, each extra project adds compute cost.
- Storage of user uploads grows silently. Set file size limits in storage policies.
- Auth SMS (phone login) needs a paid SMS provider. Use email or OAuth.
