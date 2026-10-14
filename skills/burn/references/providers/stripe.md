# Stripe

Payments, subscriptions and invoices. Burn Rate builds the whole billing integration in **test mode**, where no money moves. Going live is a human gate, and even after that the agent never creates a real charge, refund, payout or transfer by hand.

**Good for:** checkout, subscriptions, customer portal, webhooks. **Not for:** anything that holds customer funds, marketplaces paying out to third parties (Connect) without a human-reviewed plan, or crypto. See [../guardrails.md](../guardrails.md) section 1.

## The two rules

1. **Test mode only** while `providers.stripe.live_mode_approved = false` in `config.toml`. Only an answered `launch` or `account` NH item sets it to true ([../human-inbox.md](../human-inbox.md)).
2. **Never create real charges**, even when live mode is approved. The running product charges its customers through the code you wrote. You never run a CLI or API call with a live key that creates, captures, refunds or pays out anything. Live keys go into the production host's secret store by the human's hand or from an env var they set; you don't use them yourself.

## CLI

`stripe`. It's a global install, so it's a human item:

- macOS: `brew install stripe/stripe-cli/stripe`
- Windows: `scoop bucket add stripe https://github.com/stripe/scoop-stripe-cli.git` then `scoop install stripe`, or the zip from GitHub releases
- Linux: https://docs.stripe.com/stripe-cli/install

## Auth check

The CLI has no "whoami". Check that a key works and that it's a test key:

```
stripe balance retrieve                      # any read call; the CLI defaults to test mode
```

With `STRIPE_API_KEY` set, check the prefix without printing the key:

```
python -c "import os; k=os.environ.get('STRIPE_API_KEY',''); print(k[:8] if k.startswith(('sk_test_','rk_test_')) else 'NOT A TEST KEY')"
```

Anything other than `sk_test_` or `rk_test_` while `live_mode_approved = false`: stop, don't use the key, and open a high-priority `secret` item. Fail: open a `secret` item:

> Run `stripe login` (keys it creates expire after 90 days), or create a restricted test key in a Stripe sandbox (Dashboard > Developers > API keys, in test mode) with write access to Products, Prices, Customers, Checkout Sessions, Subscriptions, Webhook Endpoints, and set it as `STRIPE_API_KEY`.

Creating the Stripe account and activating it for live payments (business details, bank account, identity) are human gates.

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:stripe"` | Human ran `stripe login`; the CLI stores test-mode keys. |
| `credential = "env:STRIPE_API_KEY"` | A test key (`sk_test_` or a restricted `rk_test_`). The CLI reads it. |
| `live_mode_approved` | `false` until a human approves. Never set it yourself except when applying their answer. |

Never pass `--live` to the CLI. Never read, print, or store a live key. Don't run `stripe config --list`: it can print stored keys.

## Pricing

No monthly fee. Stripe charges a fee per successful payment (about 2.9% + 30 cents for US cards at the time of checking), deducted from the payment. Verify at https://stripe.com/pricing. Test mode is free and unlimited for practical purposes (rate limits apply).

Fees are paid by the business out of revenue, so they don't count against `monthly_cap_usd`. Paid products with their own fees (Billing usage-based fees, Tax, Radar for Fraud Teams, Identity, Invoicing) need a cost proposal before they're turned on in live mode.

## Usage and headroom

No free limits to track. Track in INFRA.md: which sandbox, which products and prices exist, which webhook endpoints. `stripe products list --limit 100`, `stripe prices list --limit 100`, `stripe webhook_endpoints list`.

## Provision (test mode)

Prefer a fixture file in the repo so the catalog is reproducible:

```
stripe fixtures stripe/fixtures.json
```

or individual calls:

```
stripe products create --name "Invoice Snap Pro" -d "metadata[burn]=<slug>"
stripe prices create --product <prod_id> --unit-amount 900 --currency usd -d "recurring[interval]=month" --lookup-key pro_monthly
```

Use `lookup_key` in code instead of hard-coding price IDs, so live and test catalogs can differ.

## Develop and test

```
stripe listen --forward-to localhost:3000/api/stripe/webhook     # prints a whsec_ signing secret
stripe trigger checkout.session.completed
stripe trigger customer.subscription.deleted
stripe logs tail
```

The `whsec_` secret from `stripe listen` goes into the local, gitignored `.env`. Don't echo it into the log. Test cards (4242 4242 4242 4242 and the decline cards) are documented at https://docs.stripe.com/testing; they only work in test mode.

## Deploy

- Preview environments use test keys, always.
- Production: before `live_mode_approved = true`, production also uses test keys and shows a "test mode" banner, or has payments switched off. After approval, the human sets the live keys in the production host's secret store (give them the exact command with the env var name), and you create a live webhook endpoint only if they approved that in the same item.

```
stripe webhook_endpoints create --url https://<preview-host>/api/stripe/webhook -d "enabled_events[]=checkout.session.completed"
```

That creates a test-mode endpoint. The signing secret it returns goes straight into the host's secret store.

## Secrets

Set from env vars, never literal:

```
printf %s "$STRIPE_API_KEY" | npx wrangler secret put STRIPE_SECRET_KEY         # Cloudflare
printf %s "$STRIPE_API_KEY" | npx vercel env add STRIPE_SECRET_KEY preview       # Vercel
```

The publishable key (`pk_test_...`) can go in front-end config.

## Custom domain

Not applicable. Branding and the public business details on the checkout page are set by the human during activation.

## Teardown

Only with an approved human item. In test mode:

```
stripe products update <prod_id> --active=false
stripe webhook_endpoints delete <we_id>
```

Deleting all test data is a dashboard action (Developers > Overview > Delete test data) and can't be undone: ask the human. Never delete or archive anything in live mode.

## IaC

- `stripe/fixtures.json` for the product and price catalog.
- Webhook event list in code, next to the handler.

## Cost hazards

- Anything with a live key: charges, refunds, payouts, transfers, Connect accounts, Issuing.
- Stripe Billing, Tax, Radar for Fraud Teams, Identity and Climate have their own fees once live.
- Disputes cost a fee per dispute in live mode. No dark patterns, clear refunds and easy cancellation keep them rare (and are required by the guardrails anyway).
- Settings changed in the test-mode sandbox can also change live settings. Use a general sandbox for new integrations, and don't change account-level settings at all.
