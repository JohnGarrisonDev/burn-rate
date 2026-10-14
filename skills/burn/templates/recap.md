# Week ending 2026-10-17 · Invoice Snap

<!--
Template for burn/recaps/<reset date>.md. Written by burn-recap. Replace every example line.
Keep it to one screen where you can. Drop a section only if it truly has nothing; say "None" instead when absence is news.
Voice: references/style.md in the burn skill. Plain, specific, honest. No hype.
Link repo files with their GitHub URL when the repo has a remote, so the recap reads well on a phone.
-->

**Headline:** CSV export and the signup flow shipped to preview; Stripe is still waiting on you (NH-004).

Phase: mvp (3 of 5 milestones done). Runs: 3 of 3. Week ended at 94% (target 95).

## Shipped

- CSV export for invoices. [PR #12](https://github.com/jdoe/invoice-snap/pull/12), live on [preview](https://invoice-snap.pages.dev/).
- Email signup with validation. Merged in `burn/2026-10-16-1`.

## Changelog

**Product**
- Invoice list paginates at 50 rows (B-0018).

**Engineering**
- Test suite down from 4 min to 70 s by running in parallel (B-0021).

**Growth**
- Landing page draft in `site/index.html`. Not published.

**Ops / infra**
- Added D1 database `invoice-snap-prod` (free tier).

## Decisions and meetings

- D-0009: SQLite on D1 instead of Postgres. Cheaper to stay free; we can move later.
- [Weekly planning, 2026-10-16](https://github.com/jdoe/invoice-snap/blob/main/burn/meetings/2026-10-16-weekly-planning.md): picked signup and export as the week's goals.

## Budget

| Run | When (UTC) | Weekly % start → end | Points | Notes |
|---|---|---|---|---|
| 1 of 3 | Fri 01:59 | 61 → 72 | 11 | planning meeting + B-0012 |
| 2 of 3 | Fri 17:59 | 72 → 83 | 11 | |
| 3 of 3 | Sat 07:59 | 83 → 94 | 11 | includes retro |
| **Week** | | **61 → 94** | **33** | target was 95 |

## Product metrics

No users yet. Preview had 14 visits, all from the test suite and you.

## Quality

QA reviews: 3 runs, 2 blockers found and fixed before merge, 4 should-fix filed (B-0061 to B-0064).
Sweep (burn/qa/2026-10-17-sweep.md): Performance 94 (was 88), Accessibility 97 (96), Best Practices 100, SEO 92. No broken links. 1 moderate npm advisory, fixed.

## Infra and costs

- New: D1 `invoice-snap-prod`, free tier. Rows read: 3.9M/day of 5M (78%).
- Spend this week: $0. Caps: all providers at $0.

## Needs you

- **NH-004 · cost · Priority: high.** Cloudflare D1 will hit its free row limit in about 2 weeks. Pick option A or B. Opened 2026-10-16; this is the one reminder.
- NH-005 · review · Draft privacy policy is ready to read.

Answer in [NEEDS_HUMAN.md](https://github.com/jdoe/invoice-snap/blob/main/burn/NEEDS_HUMAN.md).

## Retro

**Went well:** small items finished cleanly; every run left main green.
**Went badly:** run 2 spent about 4 points fighting a flaky test before parking it.
**Change:** split any test-infra item into its own S item before starting.
Skill feedback logged: 2 entries in SKILL_FEEDBACK.md.

## Next week

1. Caching for invoice reads (B-0024), whatever you pick for NH-004.
2. Pricing page draft (B-0026).
3. Milestone M4: first paid plan works end to end in Stripe test mode.
