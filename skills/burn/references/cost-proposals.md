# Cost proposals

The company runs on free tiers until a human agrees to pay for something. This file says how to watch the limits, when to ask for money, how to ask, and what an approval lets you do. It is a protected file: [guardrails.md](guardrails.md) section 4.

The rule underneath all of it: `providers.<name>.monthly_cap_usd` in `config.toml` is the most that provider may cost per month. `0` means free tier only. Only an approved proposal raises it, and you never go past it.

## 1. Measure headroom every run

At the start of any run that deploys, and at least once per usage week otherwise:

1. For each enabled provider with resources in `burn/INFRA.md`, read current usage with the commands in that provider's file under [providers/](providers/) ("Usage and headroom"). If there's no way to read a number from the CLI or API, estimate it from what you know (deploy count, request logs, database size) and mark it `est.`.
2. Compare against the free-tier limit. Use the limit you verified on the provider's pricing page, not a number from memory. Limits change. If you couldn't verify, write `limit unverified` in Notes.
3. Update the **Free-tier headroom** table in `burn/INFRA.md`, one row per limit that matters:

```markdown
| Provider | Limit | Used | % | Checked | Notes |
|---|---|---|---|---|---|
| cloudflare | D1 rows read / day (5M) | 3.9M | 78% | 2026-10-17 | +8%/week; NH-007 open |
| cloudflare | Workers requests / day (100k) | 12k | 12% | 2026-10-17 | |
| github | Actions minutes / month (2,000) | 640 | 32% | 2026-10-17 | resets 11-01 |
| vercel | Fast data transfer / month (100 GB) | 4 GB | 4% | 2026-10-10 | est. from analytics |
```

4. Keep the trend: compare with the last check (LOG.md entries or git history of INFRA.md). A limit at 40% that doubled in a week is more urgent than one sitting at 75%.

## 2. When to raise a proposal

Raise one when any of these is true:

- A limit is at **70% or more**, or will reach 100% within about 3 weeks at the current trend.
- A limit has already blocked something (deploys failing, requests rejected, project paused).
- Planned work needs a paid feature (a provider with no free tier, like Fly.io; a paid add-on; Vercel Pro once the product charges money, because Hobby is non-commercial).
- You're within 80% of an approved `monthly_cap_usd`, or the next planned change would push spend past it. Re-propose before the cap is hit, never after.

Before writing one, check whether staying free is realistic: caching, fewer production deploys, smaller images, moving a cron from every minute to every hour, cleaning up preview deployments or old branches. If it is, do that work and record the decision. A proposal should still go up if the fix only buys a few weeks.

Don't raise a proposal for something you can avoid, and don't raise two for the same limit. Update the open one.

## 3. The proposal

A cost proposal is a NEEDS_HUMAN item of type `cost` ([human-inbox.md](human-inbox.md)). Put the long analysis in `burn/research/YYYY-MM-DD-<topic>-costs.md` and link it. The item itself must be readable on a phone in under a minute.

```markdown
### NH-012 · cost · 2026-10-17 · Supabase database will hit the 500 MB free limit in ~3 weeks
Priority: high
**Why it matters:** at 500 MB the project goes read-only and sign-ups fail. We're at 380 MB (76%), growing ~40 MB/week since launch.
**What I need:** pick an option and a monthly cap.
- **A. Supabase Pro, $25/month.** 8 GB database, daily backups, no pausing. Cap: $25. Recommended: it fits the next year of growth and needs no code changes.
- **B. Move file metadata to Cloudflare R2, free.** About 3 runs of work. Buys ~4 months. Adds a second provider.
- **C. Prune guest accounts after 30 days, free.** 1 run. Buys ~6 weeks. Changes the product promise.
- **D. Do nothing.** Writes start failing around 2026-11-07.
**Meanwhile:** I'm doing C now, since it's cheap and helps with every option. Nothing else is blocked yet.
**If you approve A:** set a $30 budget alert in the Supabase dashboard (Organization > Billing) so you hear about it before I do.
**Details:** burn/research/2026-10-17-supabase-costs.md
```

Every proposal has:

- **What is limited, current usage, and the trend**, with a date it will block.
- **Options with a monthly cost each.** Always include at least one free option (optimize, cut, switch to a free provider) and "do nothing" with its consequence. State costs as a monthly cap in USD. For usage-based pricing, give the expected cost and the cap you'd stay under.
- **What each option unlocks** in plain words: what the product can do afterwards, for how long.
- **A recommendation**, listed first, with one sentence of reasoning.
- **Meanwhile**: what you'll do until they answer. Work on anything that doesn't depend on the answer. Never wait.
- **A billing-alert request** for any paid option (see section 5).

Use the provider's current pricing page for every number, and say "verify at <url>" in the research note.

Send a notification ([notify.md](notify.md)) with `--priority high` if work is blocked or the block is under a week away.

## 4. Applying an approval

When the item has `ANSWER: APPROVED` (or a specific option), or the human approves it directly in an interactive session (the `burn-configure` skill handles that case the same way):

1. If the approved option costs money, set `providers.<name>.monthly_cap_usd` in `config.toml` to the cap in the option, following "Editing config.toml unattended" in [human-inbox.md](human-inbox.md) (back up, edit, `config_check.py --previous <backup> --allow-gated`, restore and open a `blocker` item on failure). If the human wrote a different number, use theirs.
2. Add a DECISIONS entry: `## D-0019 · 2026-10-18 · Supabase Pro at $25/month cap (NH-012)` with the usage that triggered it, the options, the chosen one, and the cap.
3. Upgrading a plan or adding a payment method is still a human action ([guardrails.md](guardrails.md) section 4). Open (or keep open) an `account` item with exact steps: which page, which plan, which org. The human makes the change; you never upgrade a plan yourself ([guardrails.md](guardrails.md) section 2).
4. Update `burn/INFRA.md`: new tier and `$/month` for the affected resources.
5. Resolve the item with what you did.

`DENIED` means don't spend. Record it in DECISIONS, pick the best free option, and don't re-propose the same thing for at least 4 weeks unless the situation changes a lot (a block arrives, or usage doubles).

## 5. Staying under the cap

- Before any action that could add cost (new resource, bigger instance, more replicas, a paid add-on, a new region), estimate the monthly cost from the pricing page. Add it to current spend. If the total would exceed the cap, don't do it; propose instead.
- Sum `$/month` in INFRA.md per provider each time you update it. That's your spend estimate. Where the provider shows real billed spend (Azure Cost Management, Fly dashboard, Vercel usage), compare and use the higher number.
- At 80% of a cap, raise a new proposal (raise the cap, or optimize). At 100%, stop anything that adds cost on that provider and open a high-priority item.
- If you find that something has been costing money without an approved cap, stop or remove it if that's safe and reversible, then open a high-priority item explaining what happened and what it cost. Don't delete data to save money without approval.
- Never turn on usage-based overage, auto-recharge, or "pay as you grow" options yourself, even inside the cap. Those go in the proposal as an explicit option.

The skill's cap is a promise, not a lock. Every proposal that adds paid usage must tell the human to set a **billing alert or budget at the provider** at or a little above the cap (examples: Azure Cost Management budget, Vercel Spend Management, Supabase spend cap, GitHub budget for Actions, Cloudflare billing notifications). Ask once per provider, and keep the item open until they answer `DONE`.
