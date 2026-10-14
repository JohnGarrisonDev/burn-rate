# Notifications

The human isn't watching runs. A push notification is how they find out something needs them. Send few, short, useful ones. Every notification should be answerable with "I know what this is and where to look" without opening anything else.

## When to notify

| Event | Priority | Send when |
|---|---|---|
| New NEEDS_HUMAN item | `high` if the item has **Priority: high**, else `default` | Always, once per new item. Not when you only update an existing item. |
| Run summary | `low` | `notify.run_summaries = true`. One per run, at the end. Not for skipped runs. |
| Weekly recap ready | `default` | `recap.notify = true`, after the recap is committed and pushed. |
| Error that stopped the run | `high` | Can't push, tests red on arrival and can't fix, guardrail broken, config missing. |
| Secret found in the repo | `urgent` | Always. Say where, never what. |

Don't notify for skipped runs (except errors), routine progress, or reminders. Unanswered high-priority items get one mention in the weekly recap, not more pushes.

If several items open in one run, send one notification per item up to three. Past three, send one that lists the IDs.

## Message format

- **Title**: under 60 characters. Starts with the thing: the item ID, `Burn run 2/3`, `Weekly recap`, `Burn error`.
- **Message**: one or two sentences, under 200 characters. What happened, and what the human should do.
- **URL**: the file on GitHub when there's a remote, e.g. `https://github.com/<owner>/<repo>/blob/main/burn/NEEDS_HUMAN.md`. Otherwise leave it out.
- No secrets, tokens, connection strings, webhook URLs, customer data or email addresses. Name the env var or the file instead.

Examples:

| Event | Title | Message |
|---|---|---|
| New item | `NH-007 (cost)` | `Cloudflare D1 will hit its free row limit in ~2 weeks. Pick an option in NEEDS_HUMAN.md.` |
| New item | `NH-008 (secret)` | `Need CLOUDFLARE_API_TOKEN with Workers + D1 edit scope to deploy preview.` |
| Run summary | `Burn run 2/3` | `Shipped CSV export + signup fix. Week at 78%. 1 new item needs you (NH-007).` |
| Recap | `Weekly recap` | `3 runs, 9 items done, preview deployed. 2 open items. Next week: billing page.` |
| Error | `Burn error` | `Can't push to github.com/jdoe/invoice-snap (auth expired). Work is committed locally. See NH-009.` |
| Secret | `NH-010 (secret) URGENT` | `A token was committed in src/config.ts at a1b2c3d. Rotate it now. Details in NEEDS_HUMAN.md.` |

## How to send

Read `[notify]` in `config.toml` (burn home: `$BURN_RATE_HOME` or `~/.burn-rate`). The `channel` key picks the adapter.

### claude-push (Claude Desktop)

Used when `channel = "claude-push"`, or `channel = "auto"` and you're on Claude Desktop (see [platforms.md](platforms.md)).

1. Call the `PushNotification` tool with the title and message. If it's deferred, load it first with ToolSearch (`select:PushNotification`).
2. If the tool doesn't exist or fails, fall back to the script with `--no-claude-push`, which tries ntfy, then webhook, then Pushover.

### Everything else: notify.py

```
python ../burn/scripts/notify.py --title "NH-007 (cost)" \
  --message "Cloudflare D1 will hit its free row limit in ~2 weeks. Pick an option in NEEDS_HUMAN.md." \
  --priority high --url https://github.com/jdoe/invoice-snap/blob/main/burn/NEEDS_HUMAN.md
```

The path is relative to the calling skill's folder. From the `burn` skill itself it's `scripts/notify.py`. Use `python`, not `python3`, on Windows. In PowerShell, put the command on one line or use a backtick for line breaks.

| Flag | Meaning |
|---|---|
| `--priority` | `min`, `low`, `default`, `high`, `urgent` |
| `--url` | Link opened when the notification is tapped |
| `--tags` | ntfy tags, comma-separated (`warning`, `money`, `white_check_mark`) |
| `--channel` | Override config for this message |
| `--no-claude-push` | Skip claude-push in `auto` |
| `--dry-run` | Print the request (secrets redacted) without sending |

It prints one JSON line. Act on it:

| Result | Exit | Do |
|---|---|---|
| `"delivered": true` | 0 | Nothing more. |
| `"channel": "claude-push"` | 0 | Call the `PushNotification` tool yourself (above). |
| `"channel": "none"` | 0 | Notifications are off or unconfigured. Mention the event in your final message instead. |
| `refused: ... secret` | 1 | Rewrite the message without the secret. Never work around the check. |
| other error | 1 | Send failed (network, bad URL). Note it in LOG.md and move on. Don't retry more than once. |
| config or credential missing | 2 | Note it in LOG.md. If it was configured before and broke, open one `secret` item naming the env var. |

A failed notification never stops a run.

## Channels

| Channel | Config | Notes |
|---|---|---|
| `ntfy` | `ntfy_server`, `ntfy_topic` | Free, no account, works everywhere. Anyone who knows the topic can read and post to it, so use a long random topic (`burn-` plus 12+ random characters) and don't paste it in public. Self-hosted servers with auth can add `ntfy_token_from = "env:NTFY_TOKEN"`. The human installs the ntfy app and subscribes to the topic. |
| `webhook` | `webhook_url_from` | Discord or Slack incoming webhook. The URL is a secret, so config holds its location (`env:BURN_WEBHOOK_URL` or `file:~/.burn-rate/webhook.txt`), never the URL. |
| `pushover` | `pushover_user_from`, `pushover_token_from` | Paid app (one-time purchase by the human). Both values are locations. |
| `claude-push` | none | Claude Desktop only. Goes to the human's Claude apps. |
| `none` | none | Nothing is sent. |

`auto` picks claude-push on Claude Desktop, else ntfy if `ntfy_topic` is set, else the webhook, else Pushover, else nothing.

To test a setup, send one real message: `python scripts/notify.py --title "Burn Rate test" --message "Notifications work."` and ask the human whether it arrived.
