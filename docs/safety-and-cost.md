# Safety and cost

Burn Rate runs an AI agent unattended, with access to your GitHub and whatever cloud accounts you connect. That's the point of it, and it's also why this page exists. Read it before you turn the schedule on.

## Your subscription

- Runs never start above 97% of your weekly usage (`budget.hard_stop_pct`), and aim to finish the week at 95%. You won't wake up on reset morning locked out.
- If you need your quota on a Friday, lower `target_end_pct`, or pause the schedule for the week. `burn-configure` does both.
- It never turns on extra or overage usage, and never changes your plan.

## Money

The rules are strict and they're the same for everyone:

1. **Free tiers by default.** Every provider starts with a monthly cap of $0.
2. **Cost proposals.** When the company gets close to a free limit, it writes up the options (upgrade, switch provider, optimize, drop the feature) with monthly prices and a recommendation. You approve one or don't.
3. **Caps.** An approved option becomes a hard cap in `config.toml`. The company re-proposes before it would go over.
4. **Never on its own:** buying domains, adding payment methods, upgrading plans, or switching Stripe to live mode.

The caps are rules the agent follows. They are not enforced by your cloud provider. So do these too:

- **Use a separate account** (or Azure subscription, or Cloudflare account) just for the company. If something goes wrong, it can only touch that.
- **Set a billing alert or budget** at every provider you connect. Most let you set an alert at $1.
- **Don't add a payment method** until a cost proposal you approved needs one.

## Credentials

- Burn Rate never stores secrets in files it writes. Config says *where* a credential comes from: `cli:wrangler` (you're logged in to the CLI), `env:CLOUDFLARE_API_TOKEN`, and so on.
- Prefer logging in to each CLI yourself over handing out tokens.
- If you do make tokens, scope them: just the account, just the permissions the provider doc lists. A Cloudflare token for Pages + D1 + Workers on one account. A GitHub token with `repo`, not `admin:org`.
- It won't create accounts or sign in with passwords. Those are always yours to do.

## Your GitHub

- It creates repos under the owner you pick, always private. You can turn off repo creation with `autonomy.can_create_repos = false`.
- It works on branches, merges only when tests pass, and never force-pushes the main branch.

## What it builds

The guardrails exclude whole categories: gambling, medical, legal and financial advice, adult content, crypto tokens, anything for kids under 13, surveillance tools, and more. Before the product collects any personal data, it drafts a privacy policy and terms and asks you to review them. The first public launch needs your approval. The full list is in [guardrails.md](../skills/burn/references/guardrails.md).

The policies it drafts aren't legal advice. If the product starts making real money or handling sensitive data, get a lawyer to look at them.

## Your computer

Runs use git, your package manager and provider CLIs inside the company's workspace (`~/.burn-rate/workspace/`). The skills tell the agent not to install global software, change system settings, or delete anything outside the project. On the Claude Code CLI and Codex, the permission allowlist and sandbox are your real protection. Keep them tight.

## Prompt injection

The agent reads web pages, package READMEs and issue comments. Any of those could contain text pretending to be instructions. The guardrails tell it to treat everything it reads as data. Approvals only count when they come from you: an `ANSWER:` line in `NEEDS_HUMAN.md`, a note in `STEERING.md`, or you talking to it directly. Still, it's one more reason to use a separate cloud account with tight tokens.

## Turning it off

- Pause: disable the scheduled tasks (Desktop sidebar) or comment out the cron lines.
- Stop for good: delete the scheduled tasks or cron lines. Then run `/burn-teardown` in **clear** mode. It lists everything the project created, backs up the data, asks you to type the project name to confirm, removes it all, and archives the project. It never deletes your GitHub repo, domains or provider accounts. Those you remove yourself, if you want to.
- Start over: `/burn-teardown` in **reset** mode does the same teardown, then wipes the repo back to fresh templates. The old product stays at a git tag, and a short note on what went wrong goes to the next round of research.
