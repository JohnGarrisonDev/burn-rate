# Changelog

Versions follow semver. Patch for fixes, minor for new behavior, major for anything that changes the state file format or config in a way that needs migrating.

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
