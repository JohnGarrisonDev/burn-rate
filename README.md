# Burn Rate

Your Claude or Codex subscription resets every week whether you used it or not. Burn Rate spends what's left over on running a small software company.

You install a set of agent skills, answer a few setup questions, and walk away. Near the end of each usage week, scheduled runs check how much quota you have left and spend it on the company. In week one it researches what to build and picks something. After that it writes the code, tests it, deploys it, drafts the landing page, holds meetings with itself, and keeps notes on everything. Nothing merges until a QA review has checked it. On Monday you read a recap of what it did.

If you also have a Codex subscription, runs can use its image tool for illustrations and social images, even when Claude is doing the work.

It's an experiment. The company might never make a dollar. But the quota was going to expire anyway.

## What a week looks like

Say your usage resets Saturday at 10 AM and you've used 35% of it by Thursday night.

- **Thu 10 PM.** First run of the week. It checks usage (35%), works out it can spend about 20 points this run, and holds a planning meeting: a product, an engineering and a growth sub-agent argue about priorities. Then it builds the top two backlog items, merges them, and deploys a preview.
- **Fri 2 PM.** Picks up where it left off. Hits a free-tier limit on the database. It writes you a cost proposal with three options and keeps working on other things. Your phone buzzes.
- **Sat 4 AM.** Last run. Spends the rest down to 95%, writes the weekly recap, and stops.
- **Monday.** You run `burn-recap` and read what happened. You approve option B from your phone by editing one line on GitHub.

## Quick start

You need git, the GitHub CLI (logged in), Python 3.11+, and one of: Claude Desktop, Claude Code, or Codex.

```bash
git clone https://github.com/JohnGarrisonDev/burn-rate.git
cd burn-rate
./install.sh --platform claude     # or: --platform codex
```

On Windows:

```powershell
.\install.ps1 -Platform claude     # or: -Platform codex
```

Then open your agent and say **"set up burn rate"**. The `burn-setup` skill walks you through the rest: it checks your tools, asks about eight questions (most have defaults), sets up notifications and the weekly schedule, and creates the company's private repo.

## Where it runs

| | Claude Desktop | Claude Code CLI | Codex |
|---|---|---|---|
| Reads your usage | exactly, built-in | from a statusline hook | from Codex's session logs |
| Schedules runs with | Desktop scheduled tasks | an hourly cron / Task Scheduler check | an hourly cron / Task Scheduler check |
| Meetings use | sub-agents | sub-agents | sub-agents |
| Notifies you via | Desktop push | ntfy, Discord/Slack, Pushover | ntfy, Discord/Slack, Pushover |

Claude Desktop is the smoothest. It knows your exact usage and has scheduling and push notifications built in. Its scheduled tasks only run while the app is open, so leave it running on burn nights.

## The skills

| Skill | What it's for |
|---|---|
| `burn-setup` | One-time setup. Safe to re-run. |
| `burn` | One work session. This is what the schedule runs. |
| `burn-research` | Picks what to build, or a pivot. |
| `burn-meeting` | A meeting with sub-agents playing company roles. |
| `burn-infra` | Hosting: provision, deploy, track free-tier limits, tear down. |
| `burn-qa` | A quality review, a full QA sweep, or a copy and asset audit, on demand. |
| `burn-recap` | The weekly recap. Run it on Monday. |
| `burn-notes` | What's happening, what needs you, and leaving notes for the next run. |
| `burn-usage` | How much quota is left and what the next run will spend. |
| `burn-configure` | Change settings. |
| `burn-project` | Start a new company, switch, or archive one. |
| `burn-export` / `burn-import` | Move a company to another platform or machine. |
| `burn-teardown` | Manual only. Tear down a project's infrastructure, then reset it to zero or retire it. |
| `burn-improve` | The skills learn from each run's retro and get better. |

## What it won't do

Some things it can't do, and some it's not allowed to:

- **Spend your money.** It starts on free tiers. When it outgrows one, it writes you a cost proposal and waits. If you approve, that becomes a monthly cap the agent stays under. Set a billing alert at the provider too.
- **Touch your subscription.** It never turns on extra usage. It never runs past 97% of your week (you can change that), so you're never locked out on reset morning.
- **Make accounts or sign in with passwords.** If it needs a Cloudflare account or a domain, it asks you.
- **Launch publicly without you.** The first public launch, social posts, and emailing real people all need your OK.
- **Store secrets in files.** Config records where a credential lives (`cli:wrangler`, `env:CLOUDFLARE_API_TOKEN`), never the value.
- **Build anything sketchy.** No gambling, medical or financial advice, adult content, scraping that breaks terms of service, fake reviews, or copying other people's products. The full list is in [skills/burn/references/guardrails.md](skills/burn/references/guardrails.md).

## How you stay in the loop

Everything lives in a `burn/` folder in the company's private repo:

- `NEEDS_HUMAN.md`: questions for you. Answer with a line like `ANSWER: APPROVED B`. Editing on GitHub from your phone works fine.
- `STEERING.md`: notes for the next run. "Stop polishing the settings page, ship the import feature."
- `recaps/`: one recap per week.
- `LOG.md`, `DECISIONS.md`, `meetings/`: the full paper trail.

You get a push notification when something needs you, and when the weekly recap is ready.

## Safety and cost

Read [docs/safety-and-cost.md](docs/safety-and-cost.md) before you turn it on. The short version: use a separate cloud account for the company, set a billing alert at each provider, and don't give it tokens with more access than it needs.

## More

- [How it works](docs/how-it-works.md)
- [Platforms](docs/platforms.md)
- [FAQ](docs/faq.md)
- [Contributing](CONTRIBUTING.md)

## Status

Early. Version 0.1. Expect rough edges. The skills keep a retro of every run and, if you let them, propose fixes to themselves as pull requests.

## License

MIT. See [LICENSE](LICENSE).
