# FAQ

**Is this allowed under my subscription's terms?**
Burn Rate is your agent doing work you asked for, in your own repos, under your own account, within your plan's limits. It doesn't share accounts, get around rate limits, or resell access. Read your provider's terms for yourself, though. You're the one agreeing to them.

**Will it actually make money?**
Probably not much, at least not soon. It picks ideas with a plausible way to make money and tries to get there. Treat any revenue as a bonus.

**How much of my week does it use?**
Whatever's left at the end of the week, up to the target you set (95% by default). If you've used 90% yourself by Friday, it does very little. If you've barely touched it, it does a lot.

**What if I need Claude/Codex on a burn night?**
Runs share the same limits you do, so a long burn can push you toward the 5-hour limit. Either move the run times (`burn-configure`), lower the target for the week, or pause the scheduled tasks for that night.

**Can I pick the product myself?**
You can. Write your idea in `burn/STEERING.md` before the research run, or tell `burn-research` directly. By default it chooses on its own.

**I don't like what it picked.**
Write that in `STEERING.md`, with a reason if you have one. The next run will hold a meeting and pivot.

**Can it run more than one company?**
One at a time. `burn-project` can start a new one, switch between them, or archive one. Each has its own repo.

**Does my computer need to be on?**
Yes, during the scheduled runs. On Claude Desktop the app also has to be open; a missed run happens the next time you open it.

**What does it need from me each week?**
Usually nothing. Sometimes a decision or a login, and you'll get a push notification when it does. Reading the Monday recap takes about two minutes.

**Where do I see what it did?**
`burn-recap` for the week, `burn-notes` for anything else. Or just open the company's repo on GitHub and read `burn/LOG.md`.

**Can I use a different provider than the ones listed?**
Not yet out of the box. Each provider is a reference doc in `skills/burn/references/providers/`. Adding one means writing a new doc in the same shape. Pull requests welcome.

**Codex or Claude?**
Either. Claude Desktop is the easiest because usage, scheduling and notifications are built in. You can switch later with `burn-export` and `burn-import`.
