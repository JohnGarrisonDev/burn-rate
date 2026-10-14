# Contributing

Thanks for wanting to help. A few things that make reviews quick.

## Layout

- `skills/<name>/SKILL.md`: one folder per skill. The frontmatter `name` must match the folder.
- `skills/burn/references/`: shared docs every skill uses (guardrails, budget, state, platforms, providers, and so on). Other skills link to them as `../burn/references/...`.
- `skills/burn/templates/`: the files a new company starts with.
- `skills/burn/scripts/`: helper scripts. Python 3.11+, standard library only. They have to run on a fresh machine with nothing installed.
- `tests/`: the linter and unit tests.

## Before you open a PR

```bash
python tests/lint_skills.py
python tests/lint_style.py
python -m unittest discover tests
```

All three have to pass. `lint_skills.py` checks frontmatter and that every relative link resolves. `lint_style.py` checks the public docs against the banned-word list and the other rules in the style guide.

## What makes a good change

- **Small.** One fix or one feature per PR.
- **Works on both Claude and Codex.** If behavior differs by platform, put the difference in `skills/burn/references/platforms.md` or a script, not scattered through the skills.
- **Doesn't loosen the guardrails.** PRs that relax `guardrails.md`, `budget.md`, `cost-proposals.md` or `human-inbox.md` need a very good reason and a discussion first.
- **Written for an agent that remembers nothing.** Skill instructions should say exactly what to do, in order, with real commands.
- **Has a CHANGELOG entry.**

## Adding a hosting provider

Copy an existing file in `skills/burn/references/providers/` and keep the same sections: what it's for, CLI and install, auth check, credentials, free-tier limits (with a link to the official pricing page), usage checks, deploy, secrets, teardown, cost hazards. Add the provider's table to `skills/burn/templates/config.toml`.

## Writing style

Docs and copy follow [skills/burn/references/style.md](skills/burn/references/style.md). Plain words, specific claims, no filler.

## PRs from burn-improve

If you run Burn Rate in `maintainer` mode, the skills open PRs against themselves based on run retros. Those PRs get the same review as anyone else's. Check that the retro behind them actually points to a real problem.
