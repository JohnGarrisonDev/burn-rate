# Quality

The company's work is judged by people who will never see the backlog. They see the product, the landing page, the docs and the emails. Shipping less, but shipping it well, beats shipping a lot of half-finished work. When budget is tight, cut scope, never quality.

Quality is checked three ways:

1. **Definition of Done.** The person doing the work checks it against the list below before calling an item done.
2. **QA review.** An independent reviewer (a sub-agent in the QA role) checks the run's work before it merges. Its blockers stop the merge.
3. **Weekly QA sweep.** Once a week, someone tests the whole product the way a user would, not just what changed.

## Definition of Done

An item isn't `done` until all of these that apply are true.

### Code
- It does what the backlog item says, including the edge cases a user would hit: empty states, errors, slow network, long text, mobile width.
- **Tests:** new behavior has tests. Bug fixes have a test that failed before the fix. Tests check behavior, not implementation details.
- **Checks:** the project's full test suite, linter, formatter and type checker pass. No new warnings. Don't disable a rule or skip a test to get green. If a rule is wrong, change it on purpose and record a decision.
- **Cleanup:** no dead code, commented-out blocks, stray `console.log`/`print`, or TODOs without a backlog ID (`TODO(B-0051)`).
- **Errors:** handled where they can happen. Users see a useful message, not a stack trace.
- **Security:** inputs validated at the boundary. Queries parameterized. Auth checked on every protected route. No secrets in code or client bundles.
- **Fits the code around it:** same patterns, naming and structure. Shared logic lives in one place.
- **Dependencies:** pinned, maintained, with a license that's allowed (see [guardrails.md](guardrails.md)), and needed. Don't pull in a package for something that takes ten lines.

### UI
- **Run it and look.** Build it, start it, open the page, use the feature. On Claude, use a browser tool if one is available. Otherwise use Playwright headless to take screenshots at 375px and 1280px wide, and look at them.
- **Accessibility:** keyboard reachable, visible focus, labels on inputs, alt text on meaningful images, colour contrast at least 4.5:1 for text. Run axe (via `@axe-core/playwright` or `pa11y`) on changed pages: zero serious or critical issues.
- **States:** loading, empty, error and success all designed, not left to defaults.
- **Consistency:** spacing, type and colour from the project's design tokens, not one-off values.

### Copy and content
- Follows [style.md](style.md). Specific, true, short.
- Spelling and grammar checked.
- No placeholder text (`Lorem ipsum`, `TODO`, `Your Company`, `example.com`) anywhere a user could see it.

### Assets
- **Images and icons:** made for the product or properly licensed. Record the source and license in `burn/DECISIONS.md` unless it's the project's own icon set or a permissive set (e.g. Lucide, Heroicons). No watermarked, low-resolution or stretched images. No AI-generated pictures of people presented as real customers.
- **Formats:** compressed and sized for their use (WebP/AVIF for photos, SVG for icons and logos). Each has explicit dimensions so the layout doesn't jump.
- **Metadata:** a favicon, social preview image (1200×630) and page titles/descriptions exist before launch.

### Docs
- README explains how to run, test and deploy the product, and it's accurate. Try the commands.

## QA review (every run that changes the product)

Before integrating the run branch (step 6 of the `burn` skill), launch a **QA reviewer**: one sub-agent in the `qa` role from [roles.md](roles.md). It's separate from you on purpose. You wrote the code and you're biased toward thinking it works.

**Brief it with:**
- the backlog items done this run, with their acceptance notes
- the diff: `git diff <default-branch>...HEAD`, or for a large diff, `--stat` plus the most important files
- how to run the tests and the app
- this file's Definition of Done
- these instructions: "Review only. Don't edit files or commit. Return findings as a list, each with: severity (blocker / should-fix / nit), file:line, what's wrong, and why it matters to a user or maintainer. Cite line numbers from the working tree, not from the diff. Run the tests and the app yourself where you can. Don't report style preferences the linter would catch. If it's good, say so in one line."

**What counts as a blocker:**
- broken behavior
- failing or missing tests for new behavior
- a security problem
- an accessibility failure at serious or critical level
- a guardrail violation
- placeholder content a user could see
- a visible layout break
- a claim in copy that isn't true

**Then:**
- Fix every blocker, re-run the checks, and if the fix was more than trivial, ask the reviewer to look again (once).
- `should-fix` items: fix them now if they're small. Otherwise add them to BACKLOG.md near the top, tagged `qa`.
- Ignore nits unless they're free to fix.
- Save the findings, as returned, to `burn/qa/<YYYY-MM-DD>-review-run-<n>.md`, with a line under each saying what you did about it.
- Record the outcome in the run's LOG entry: `QA: 2 blockers fixed, 1 should-fix → B-0061`.
- If blockers can't be fixed this run, **don't merge**. Leave the branch, put the fix at the top of the backlog, and say so in the log.

**Budget:** a QA review costs roughly 2–4 points. It is not optional. If the run is nearly out of budget, finish fewer items so there's room for review. The only exception is a run that changed nothing in the product: state files only, research or meetings. That run skips the review.

**Without sub-agents:** Codex supports sub-agents, so use one there too. Only if this setup can't spawn any, follow the fallback in [platforms.md](platforms.md). Take the QA role yourself, re-read the diff from the top as if someone else wrote it, and run every check. Note `QA: self-review (no sub-agent)` in the log.

## Weekly QA sweep

Once per usage week, on the first run (after the planning meeting) or the last, if budget allows, hold a sweep of the whole product, not just the latest changes. Skip it while the phase is `research`.

The QA reviewer (sub-agent) gets the production URL (or preview if not launched) and does:

1. **Core flows**, end to end, as a new user: land, sign up, do the main thing, pay (test mode), cancel. Playwright scripts for these should live in the repo (`e2e/`) and grow over time. Run them, then also click through by hand.
2. **Lighthouse** on the home page and the main app page (`npx lighthouse <url> --output=json --quiet --chrome-flags="--headless"`). Targets: Performance ≥ 90, Accessibility ≥ 95, Best Practices ≥ 95, SEO ≥ 90. Below target is a should-fix. Below 70 is a blocker for the next run.
3. **Broken links and assets** (`npx linkinator <url> --recurse`).
4. **Mobile** check at 375px wide.
5. **Copy read-through** of every public page, against style.md.
6. **Dependency audit** (`npm audit --omit=dev`, `pip-audit`, or the ecosystem's equivalent). High or critical findings are blockers.
7. **Error tracking and logs**, if set up: new errors since last week.

Write results to `burn/qa/<YYYY-MM-DD>-sweep.md`:
- a scores table
- findings by severity
- what changed since last sweep

New findings go into the backlog tagged `qa`. The weekly recap includes a "Quality" section with the scores and their trend.

## Small or early projects

The checks above still apply on day one; some just look different.

- **No linter, formatter or type checker yet?** Adding them is part of the scaffold item, not a later nice-to-have.
- **No hosting yet?** Serve the build locally (e.g. `npx serve .`) and run the sweep against localhost.
- **No dependencies?** Record `audit: no dependencies` instead of running an audit.
- **Playwright and axe** are project-local dev dependencies. It's fine to add them with the first real UI, not before. Until then, say what wasn't checked in the QA line: `QA: self-review; no axe yet (no UI)`.

## Quality before launch

The first public launch item in NEEDS_HUMAN.md must include the latest sweep results. Don't ask for launch approval with open blockers, Lighthouse scores under target, or missing legal pages, favicon or social preview.

## Keep the bar where it is

- Don't lower a threshold, skip a check or delete a failing test to make a run look productive. If a threshold is genuinely wrong for this product, open a `review` item ([human-inbox.md](human-inbox.md)) that says which threshold, why, and the value you propose. Keep the current threshold until the human answers. Then record the outcome in DECISIONS.
- If the same kind of problem shows up in QA review twice, make it impossible the third time: a lint rule, a test, a checklist line here (via SKILL_FEEDBACK and burn-improve), or a shared component.
