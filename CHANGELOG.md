# Changelog

Versions follow semver. Patch for fixes, minor for new behavior, major for anything that changes the state file format or config in a way that needs migrating.

## 0.2.1 · 2026-10-15

- platforms.md, Windows notes: put code with backslashes in files, not heredocs (seen in three runs); git worktree cautions for ports, junctioned node_modules and merging (three runs).

## 0.2.0 · 2026-10-14

- Scheduled runs check the run lock before loading any skill, and skip with one line if another run is still going. The hourly gate does the same before starting an agent. The lock format is defined once in state.md.
- Budget (approved by the maintainer, NH-002): runs also stop taking new work when the session's context passes about 70%; measured Max-plan costs per item added next to the rough-cost table.
- Quality: the Definition of Done now asks for e2e tests under the same security headers production sends. A `<meta>` CSP doesn't reach workers, so a meta-only preview can pass code that production blocks.
- Cloudflare: note that recent wrangler versions may route Pages commands to Workers, and that `--force` at project creation keeps a classic Pages project.
- Research: Reddit, Capterra and GetApp often refuse agent page fetches; find the same signal on a site that opens, and never count a search snippet as an opened page.

## 0.1.0 · unreleased

First version.

- Skills: `burn`, `burn-qa`, `burn-teardown`, `burn-setup`, `burn-research`, `burn-meeting`, `burn-infra`, `burn-recap`, `burn-notes`, `burn-usage`, `burn-configure`, `burn-project`, `burn-export`, `burn-import`, `burn-improve`.
- Platforms: Claude Desktop, Claude Code CLI, Codex.
- Usage from Claude Desktop's usage tool, a Claude Code statusline hook, or Codex session logs, with a time-boxed fallback.
- Hosting provider guides: Cloudflare, Azure, Vercel, Netlify, Fly.io, Supabase, Neon, GitHub, Stripe (test mode).
- Notifications: Claude Desktop push, ntfy, Discord/Slack webhooks, Pushover.
- Quality gate: Definition of Done, an independent QA reviewer before every merge, and a weekly QA sweep (Lighthouse, accessibility, links, dependency audit).
- Install scripts for macOS/Linux and Windows.
- Hourly scheduling gate (`usage.py gate` + `run_burn.sh` / `run_burn.ps1`) for the Claude Code CLI and Codex. It follows Codex's moving weekly window and costs nothing in hours when no burn is due.
- Tested end to end on Claude and on Codex (codex-cli 0.162).
- Asset generation: runs on any platform can use the person's Codex subscription for images (`scripts/codex_image.py`: read-only sandbox, checks login and Codex's own weekly budget). Every asset is logged in `burn/ASSETS.md` with its source and license.
