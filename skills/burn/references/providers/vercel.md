# Vercel

The easiest place to run a Next.js (or SvelteKit, Nuxt, Astro) app, with a preview URL for every deploy. The catch: the free Hobby plan is for personal, **non-commercial** use. A product that charges money, runs ads, or exists to make money needs Pro.

**Good for:** framework apps with SSR and serverless functions during the MVP phase, preview deployments, quick landing pages. **Not for:** a launched paid product on Hobby; long-running jobs; heavy image optimization on the free quota.

Decide early. If the plan is to charge money, either budget a cost proposal for Pro ($20/month per seat) before launch, or build on Cloudflare from the start. Record the choice in DECISIONS.

## CLI

`vercel`, installed per project:

```
npm install --save-dev vercel
npx vercel --version
```

## Auth check

```
npx vercel whoami
```

Pass: prints the username. With a token, add `--token "$VERCEL_TOKEN"` to every command (PowerShell: `--token $env:VERCEL_TOKEN`). Fail: open a `secret` item:

> Run `npx vercel login` in the project folder, or create a token at vercel.com/account/tokens scoped to the burn team, with an expiry, and set it as `VERCEL_TOKEN`.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:vercel"` | Human ran `vercel login`. |
| `credential = "env:VERCEL_TOKEN"` | Pass `--token` from the env var on every call. `VERCEL_ORG_ID` and `VERCEL_PROJECT_ID` may also be set for CI. |

## Free tier (Hobby)

Checked October 2026. Verify current limits at https://vercel.com/pricing and https://vercel.com/docs/limits.

| Limit | Hobby |
|---|---|
| Function invocations | 1M / month |
| Active CPU (Fluid compute) | 4 hours / month |
| Fast data transfer | 100 GB / month |
| Edge / CDN requests | 1M / month |
| Image optimization | 5,000 transformations / month |
| Commercial use | Not allowed (https://vercel.com/docs/limits/fair-use-guidelines) |

On Hobby, going over a limit pauses the project until the window resets. It doesn't bill. On Pro, usage beyond the included amounts bills unless Spend Management is set.

## Usage and headroom

There's no stable CLI command for plan usage at the time of writing. Try `npx vercel usage` (check `npx vercel --help`; newer CLIs may have it). Otherwise:

- Count deployments: `npx vercel ls <project>`.
- Estimate data transfer and requests from the product's own analytics or logs, mark them `est.`.
- Ask the human once a month in the weekly recap to paste the numbers from the dashboard's Usage page, if a limit is above 50%.

## Provision

```
npx vercel link --yes --project <slug>        # creates the project if it doesn't exist; writes .vercel/ (gitignore it)
```

Databases and storage from the Vercel Marketplace (Neon, Upstash, Supabase, Blob) create accounts or resources with other providers. Prefer provisioning those through their own CLI and provider file (for example [neon.md](neon.md)), so they're under their own cap and inventory row.

## Deploy

```
npx vercel deploy                 # preview: unique URL, prints it on stdout
npx vercel deploy --prod          # production
npx vercel promote <preview-url>  # promote a tested preview to production
```

Prefer `vercel build` then `vercel deploy --prebuilt` when you already ran the build in the same run, to save build minutes. Production only when `launch_approved = true`. Preview deployments sit behind Vercel Authentication by default. Check them with `npx vercel inspect <url>` and `npx vercel logs <url>`, and test the app itself locally (`npx vercel dev`). For automated checks against a preview, ask for a Protection Bypass for Automation secret (`secret` item).

If the project is connected to the GitHub repo, every push to a branch makes a preview and every push to the production branch deploys production. Before launch approval, either don't connect Git, or set the production branch to one you don't push to and note it in DECISIONS.

## Secrets

```
printf %s "$STRIPE_SECRET_KEY" | npx vercel env add STRIPE_SECRET_KEY preview
printf %s "$STRIPE_SECRET_KEY" | npx vercel env add STRIPE_SECRET_KEY production
npx vercel env ls
```

On Windows, run these from Git Bash. Windows PowerShell 5.1 adds a trailing newline when it pipes a string to a program, and the newline becomes part of the secret. Use test keys for preview. `npx vercel env pull .env.local` writes secrets to disk: only into a gitignored file, and delete it at the end of the run.

## Custom domain

`npx vercel domains buy` is a purchase: never run it. With a domain the human owns:

```
npx vercel domains add example.com <slug>
npx vercel domains inspect example.com       # shows the DNS records the human must set
```

Attaching a domain to production is the public launch unless `launch_approved = true`.

## Teardown

Only with an approved human item:

```
npx vercel remove <deployment-url> --yes      # one deployment
npx vercel project rm <slug>                  # whole project and its deployments
npx vercel domains rm example.com             # detaches; doesn't cancel registration
```

Preview deployments that runs created are the exception: prune old ones now and then (`npx vercel ls`, then `npx vercel remove <preview-url> --yes`) without an approval, as long as production isn't touched. Record what you pruned in INFRA.md under **Removed** (see "Teardown" in the burn-infra skill).

## IaC

- `vercel.json`: framework, build command, output, rewrites, headers, crons, function regions and limits.
- Pin `regions` to one region (`["iad1"]`) to keep function costs and latency predictable.

## Cost hazards

- **Commercial use on Hobby** breaks the terms. Plan the Pro cost proposal before monetization ships.
- Pro bills on-demand usage beyond included amounts. If Pro is approved, ask the human to set Spend Management to the cap with "pause projects" on.
- Crons, ISR revalidation every few seconds, and middleware on every request quietly eat function invocations and CPU.
- `next/image` with remote images counts transformations; cache or use `unoptimized` for large galleries.
- Marketplace integrations (databases, KV, blob) can start their own paid plans.
- Adding team seats costs money.
