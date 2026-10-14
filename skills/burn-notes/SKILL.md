---
name: burn-notes
description: Show what the Burn Rate company has been doing (run log, decisions, meetings, open human items), leave steering notes for the next run, or answer inbox items. Use when the user asks what happened, what's pending, what needs them, or wants to tell the company something.
---

# burn-notes

The human's window into the company, and their way of talking back to it. Read files, show them clearly, and write the human's words into the right place. Don't do product work here.

Find the active project from `projects.toml` in the burn home (see [../burn/references/state.md](../burn/references/state.md)). `git pull` first so you show the latest.

## What the user might want

**"What's been happening?"** (the default if they don't say)
- Last 3–5 entries from `burn/LOG.md`, condensed to one or two lines each.
- Phase and the next roadmap milestone from `project.toml` / `ROADMAP.md`.
- Count of open items in `NEEDS_HUMAN.md`, with titles.
- Production / preview URLs if any.

**"What needs me?"**
- Every open item in `NEEDS_HUMAN.md`, high priority first. Show the ID, the title and the options, and say what you recommend.
- If they answer you right here ("approve NH-007 option B", "I made the Cloudflare account"), write their answer into the file as an `ANSWER:` line under that item, exactly per [../burn/references/human-inbox.md](../burn/references/human-inbox.md). Commit (`notes: answer NH-007`) and push. Don't act on the answer yourself; the next burn run applies it. The exception is if they ask you to run a burn now.

**"Tell the company ..." / "Next time, focus on ..."**
- Add their note under "New" in `burn/STEERING.md`, with the date, in their words. Lightly clean up speech-to-text, but don't change the meaning. Commit (`notes: steering`) and push.
- If it contradicts a guardrail, say so and don't write it as an instruction.

**Decisions**
- `burn/DECISIONS.md`: list titles; show one in full on request.

**Meetings**
- List `burn/meetings/`; summarize one on request (attendees, decision, action items).

**The log**
- Full `LOG.md` entries for a date range on request.

## Format

Plain and brief. Lead with what matters most: anything blocked on the human comes first. Dates in the user's timezone (`schedule.timezone` in config). Link files by relative path so they're clickable.
