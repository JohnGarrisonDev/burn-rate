# Netlify

Simple static and Jamstack hosting with deploy previews and serverless functions. New accounts are on a credit-based plan where **every production deploy costs credits**, so the free plan suits a site that changes a few times a week, not one that deploys every run.

**Good for:** marketing sites, docs, static front ends with a few functions, form handling. **Not for:** apps that deploy to production many times a month on the free plan; heavy server-side work.

## CLI

`netlify`, installed per project:

```
npm install --save-dev netlify-cli
npx netlify --version
```

## Auth check

```
npx netlify status
```

Pass: shows "Current Netlify User" with an email (and the linked site, if any). Fail: "Not logged in". Open a `secret` item:

> Run `npx netlify login` in the project folder, or create a personal access token at app.netlify.com > User settings > Applications > Personal access tokens, with an expiry, and set it as `NETLIFY_AUTH_TOKEN`.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:netlify"` | Human ran `netlify login`. |
| `credential = "env:NETLIFY_AUTH_TOKEN"` | The CLI reads it. `NETLIFY_SITE_ID` selects the site without `netlify link`. |

## Free tier

Checked October 2026. Verify at https://www.netlify.com/pricing/ and https://docs.netlify.com/manage/accounts-and-billing/billing/billing-for-credit-based-plans/credit-based-pricing-plans/.

Credit-based Free plan (accounts created since September 2025): **300 credits / month, hard limit, no auto-recharge.**

| Uses credits | Rate |
|---|---|
| Production deploy | 15 credits each |
| Bandwidth | 20 credits per GB |
| Web requests | 2 credits per 10,000 |
| Compute (functions, preview servers) | 10 credits per GB-hour |

So 300 credits is at most 20 production deploys a month with no traffic, or 15 GB of bandwidth with no deploys. Deploy previews and draft deploys don't count as production deploys, but their compute does. When credits run out, expect the site to stop serving until the next cycle.

Older accounts may still be on the legacy plan (bandwidth and build minutes instead of credits). `npx netlify api listAccountsForUser` (look at the plan type) or the dashboard's Billing page tells you which. Record which one in INFRA.md.

Personal plan: $9/month for 1,000 credits.

## Usage and headroom

- Production deploy count this month: `npx netlify api listSiteDeploys --data '{"site_id":"<id>","production":true}'` and count by date.
- Credit balance and bandwidth: dashboard > Billing > Usage. There's no stable CLI command for credits. Estimate from deploys and traffic, mark `est.`, and ask the human for the real number in the recap if you're above 50%.

Rule of thumb on the credit plan: **at most one production deploy per run**, and only when something user-visible changed. Use draft deploys for everything else.

## Provision

```
npx netlify sites:create --name <slug> --disable-linking   # prints the site ID
npx netlify link --id <site-id>                            # writes .netlify/ (gitignore it)
```

## Deploy

```
npx netlify deploy --dir <build-dir>                      # draft deploy with a unique preview URL
npx netlify deploy --dir <build-dir> --alias preview-<run>
npx netlify deploy --dir <build-dir> --prod               # production: costs credits
```

Add `--json` to get the URL in machine-readable form. Production only when `launch_approved = true`. If the site is linked to the GitHub repo for continuous deployment, every push to the production branch is a production deploy (and costs credits); prefer CLI deploys and leave auto-publishing off until launch.

## Secrets

```
npx netlify env:set STRIPE_SECRET_KEY "$STRIPE_SECRET_KEY" --secret --context production
npx netlify env:set STRIPE_SECRET_KEY "$STRIPE_TEST_SECRET_KEY" --secret --context deploy-preview
npx netlify env:list
```

PowerShell: `$env:STRIPE_SECRET_KEY`. Reference the env var, never the literal value. Use test keys for preview contexts.

## Custom domain

Buying a domain through Netlify is a human gate. With a domain the human owns, set it on the site:

```
npx netlify api updateSite --data '{"site_id":"<id>","body":{"custom_domain":"www.example.com"}}'
```

Then the human points DNS at Netlify (shown in the dashboard's Domain management). HTTPS certificates are free. Attaching a domain is the public launch unless `launch_approved = true`.

## Teardown

Only with an approved human item:

```
npx netlify sites:delete <site-id> --force
```

## IaC

- `netlify.toml`: build command, publish dir, functions dir, redirects, headers, per-context env (`[context.deploy-preview]`).
- `netlify/functions/` for functions.

## Cost hazards

- Production deploys spend credits. Ten deploys a week runs out the free plan in two weeks.
- Turning on auto-recharge on a paid plan makes spend open-ended. Never enable it; put it in a proposal.
- Large media served from the site eats bandwidth credits fast. Put big files on a CDN with a free egress tier (Cloudflare R2) if needed.
- Paid add-ons: extra team members, analytics, high-performance builds.
