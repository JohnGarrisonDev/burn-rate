---
name: burn-qa
description: Run a quality review of the Burn Rate company's product. Review a branch or recent changes, do a full QA sweep of the live product (flows, Lighthouse, accessibility, links, copy, dependency audit), or audit the product's assets and copy. Use when the user asks for QA, a review, a quality check, or 'is this good enough to launch'.
---

# burn-qa

Quality on demand. The `burn` skill already runs a QA review before every merge and a sweep once a week. This skill is for when the human, or a run, wants one outside that rhythm. The bar and the procedures live in [../burn/references/quality.md](../burn/references/quality.md). Read it first. Don't restate it, apply it.

Find the active project from `projects.toml` in the burn home ([../burn/references/state.md](../burn/references/state.md)), `cd` into its workspace and `git pull`. Check the budget ([../burn/references/budget.md](../burn/references/budget.md)): a review is 2–4 points, a sweep 4–8. Take the run lock if you'll change state ("Run lock" in state.md).

## Pick the mode

If the user doesn't say, pick from context:

| They say | Mode |
|---|---|
| "review this branch", "review the last run", a PR number | **Review** |
| "QA the product", "is it ready to launch", "do a sweep" | **Sweep** |
| "check the copy", "check the images", "how does it look" | **Content audit** |

### Review

The "QA review" procedure in quality.md, for a chosen diff:

- a branch: `git diff <default>...<branch>`
- a PR: `gh pr diff <n>`
- "the last run": the merge commit range from the newest LOG entry

Launch the QA reviewer sub-agent with the brief from quality.md. On Codex without sub-agents, use the fallback in [../burn/references/platforms.md](../burn/references/platforms.md).

Then:
- **Interactive:** show the findings, grouped by severity. Ask before fixing anything that isn't a clear blocker.
- **Called from a run:** fix blockers, file should-fixes as `qa` backlog items.
- **PR:** you may post the findings as a PR review comment with `gh pr review <n> --comment --body-file <file>`. The PR is in the company's own private repo, so this doesn't count as publishing.

### Sweep

The "Weekly QA sweep" procedure in quality.md, against production (or preview if not launched). Write `burn/qa/<YYYY-MM-DD>-sweep.md`, file findings as `qa` backlog items, commit and push. Compare the scores with the previous sweep and call out anything that got worse.

For "is it ready to launch?", answer with a clear yes or no first. Then list exactly what stands between the product and the "Quality before launch" bar in quality.md.

### Content audit

Go through every public page and asset:

- **Copy:** check it against [../burn/references/style.md](../burn/references/style.md). Quote the line, then give the rewrite.
- **Claims:** every claim must be true today.
- **Placeholders:** none left anywhere.
- **Images and icons:** every image in the product is listed in `burn/ASSETS.md` with a source and license; sized and compressed; alt text; no stretching, blur, artefacts or garbled text in generated images.
- **Metadata:** favicon, social preview, titles and descriptions.
- **Brand:** consistent use of colour, type and voice.

Write the result to `burn/qa/<YYYY-MM-DD>-content.md`. Fix what's quick, and file the rest as `qa` backlog items.

## Finish

Add a LOG entry: `## <date> <time> UTC · qa · <platform>`, then a line with the mode and the result. Commit, push, release the lock. If anything rates as a blocker on production, notify the human ([../burn/references/notify.md](../burn/references/notify.md)).
