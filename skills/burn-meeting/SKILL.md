---
name: burn-meeting
description: Hold a Burn Rate company meeting. Sub-agents each play one role (product, engineering, design, growth, research, ops, legal) and give positions on a single question; the CEO chair decides and writes minutes, decisions and backlog items. Use when the user asks for a meeting, a second opinion, or a team discussion about the product, or when a burn run hits a big decision.
---

# burn-meeting

Run one meeting for the active Burn Rate project. The procedure, minutes format and example brief are in [../burn/references/meetings.md](../burn/references/meetings.md). The role charters are in [../burn/references/roles.md](../burn/references/roles.md). Read both before you start. The `burn` loop uses the same procedure internally; this skill is the on-demand door to it.

## 1. Set up

- Find the burn home and the active project per [../burn/references/state.md](../burn/references/state.md). No active project means there's nothing to meet about; say so.
- If the run lock is held, a burn run is working in the same repo. Tell the user and offer to hold the meeting after it finishes. Don't write to the repo while it runs.
- If `meetings.enabled = false` in `config.toml`, tell the user. If they still want it, hold it; they asked.
- `cd` into the project's workspace clone and `git pull --rebase`.
- Check usage per [../burn/references/budget.md](../burn/references/budget.md) step 1. A meeting costs about 3–6 points. If weekly % is already above `budget.hard_stop_pct`, don't launch sub-agents; offer the role-play fallback or a later time. When the user asks you directly, their usage is theirs to spend, but tell them the cost.

## 2. Topic and attendees

Use what the user gave you. Fill in what they didn't:

- **Topic but no question:** turn it into one decision with an answer. "Pricing" becomes "What should the free tier include at launch?" Read DECISIONS.md first; if it's already decided, say so and ask whether something has changed.
- **No topic:** pick the most valuable open question. Look at, in order: open `decision` items in NEEDS_HUMAN.md the company could pre-chew, `blocked` backlog items, the next unmet ROADMAP milestone, and choices flagged in recent LOG entries. Propose it in one line.
- **Attendees named:** use them, capped at `meetings.max_attendees`. Use the role keys from roles.md (`product`, `eng`, `design`, `growth`, `research`, `ops`, `legal`). "Marketing" means `growth`, "finance" means `ops`, "lawyer" means `legal`. You always chair as `ceo`.
- **No attendees:** use the topic table in meetings.md.

State the agenda and attendees in one short message, then go. Don't wait for approval unless the topic was unclear. Example:

> Meeting: database choice. Question: D1 or Postgres on Neon for the MVP? Attendees: eng, ops, product. One round unless they split. About 4 points.

## 3. Run it

Follow "Procedure" in meetings.md: agenda in the minutes file first, one self-contained brief per attendee, all attendees launched in parallel, round 2 only if they disagree, then you decide. Platform details (Agent tool, Codex sub-agents, the sequential fallback) are in meetings.md and in "Sub-agents" in [../burn/references/platforms.md](../burn/references/platforms.md).

The user is in the room. After round 1 (and round 2 if any), show them a short summary of the positions before you decide, and let them weigh in. Treat what they say like a STEERING note: it outranks your own view, never the guardrails. Record it in the minutes under the round as `### human`.

## 4. Write it down

Per "Write it down" in meetings.md: finish the minutes at `burn/meetings/YYYY-MM-DD-<topic>.md`, add a DECISIONS entry if the decision warrants one, add action items to BACKLOG.md, open human items if needed. Add a one-line entry to `burn/LOG.md` so the next run knows a meeting happened outside a run:

```
## 2026-10-15 19:40 UTC · meeting (on demand) · claude-desktop
Meeting: database-choice → D-0006 (D1). Added B-0031..B-0033. Usage 41% → 45%.
```

Commit to the default branch (`meeting: database-choice (D-0006)`) and push.

## 5. Report back

Tell the user the decision in one or two sentences, the new IDs, and the minutes path. Don't repeat the minutes.
