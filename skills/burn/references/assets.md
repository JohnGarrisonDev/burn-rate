# Assets: images, icons and illustrations

The product needs real visual assets: a favicon and app icons, a social preview image, illustrations for empty states and the landing page. They have to meet the asset rules in [quality.md](quality.md): made for the product or properly licensed, sized and compressed, with alt text.

There are three ways to get them, in this order of preference:

1. **Draw it in code.** Icons, logos, simple shapes and diagrams are best as hand-written SVG. They're tiny, sharp at every size, easy to recolour from the design tokens, and there's no licensing question. Most UI icons should come from here or from a permissive icon set.
2. **A permissive icon set** (Lucide, Heroicons, Tabler; MIT or ISC). Copy only the icons you use into the repo. Note the set and license in DECISIONS once.
3. **Generate it with Codex**, when the person running Burn Rate also has a Codex (ChatGPT) subscription that's logged in with usage to spare. Use it for things code can't do well: illustrations, textures, a rich social preview background, marketing imagery. This works from any platform, including a Claude run. See below.

Don't use stock photos or images found on the web, unless their license is permissive and recorded.

## Generating with Codex

Codex has a built-in image tool (the `$imagegen` skill). It runs against the person's own Codex subscription, so it doesn't cost Burn Rate's Claude budget, and it needs no API key. The helper script wraps it safely:

```
python <abs path to burn skill>/scripts/codex_image.py --check
python <abs path to burn skill>/scripts/codex_image.py --prompt "<what to draw>" --out <project path>/assets/src/<name>.png
```

`--check` answers whether Codex can be used right now:

- `codex` is installed and `codex login status` succeeds
- `[assets] codex_images` in config.toml isn't `"off"`
- Codex's own weekly usage is under `assets.codex_max_weekly_pct` (default 80)

Exit 0 means go ahead; exit 2 means not available, which is a normal answer. Fall back to options 1 and 2, and if the asset really needs generating, add a backlog item and move on. Don't open an inbox item just because Codex isn't set up.

How the script runs Codex: `codex exec` with a **read-only sandbox**, in an empty temp folder, with stdin closed. Codex's image tool saves the PNG under `~/.codex/generated_images/`; the script only accepts a file from there, checks it's a real PNG, and copies it to `--out`. Never widen this: no `--approve-for-me`, no write access, no network flags. An image request has no reason to touch the repo.

Each image takes about a minute. On Codex's side, an image costs very little of the weekly budget (tested: under 1 point). Log the before and after numbers the script prints anyway.

On a Codex run, the agent can use its own `$imagegen` skill directly. The rules below still apply.

### Prompts

Prompts go to OpenAI. Treat them like anything else that leaves the machine:

- **No user data, secrets, file contents or names of real customers.** Describe the image, nothing else.
- **No real people, no celebrity or public-figure likeness, no "in the style of <living artist>", no brands, logos or trademarks** (ours included: compose the logo yourself in SVG).
- **No text in the image.** Generated lettering is often wrong. Put headlines in HTML over the image, or in the SVG.
- **Say what you need.** Give the purpose, composition, empty space for overlaid text, the palette from the design tokens (with hex values), and the style. Example:
  > A wide social-preview background: soft off-white paper texture with faint deep-green (#1f5c4a) spreadsheet grid lines on the right third, generous empty space on the left for a headline. No text, no logos, no people.
- One image per call. If you need variations, run it again and choose.

### After generating: always

1. **Look at it.** Open the file and check it shows what you asked for, with no artefacts, no accidental text and nothing odd in the corners. Reject and regenerate rather than ship something off.
2. **Resize and crop to the exact size.** The model picks its own dimensions (a "1200×630" request came back 1731×909). Use `sharp` as a project dev dependency and a few lines of Node, e.g. `sharp("assets/src/og.png").resize(1200, 630, { fit: "cover" }).webp({ quality: 80 }).toFile("public/og.webp")`. Keep that script in the repo (`scripts/assets.mjs`) so the next run can redo it.
3. **Compress.** WebP or AVIF for photos and illustrations, PNG only where needed (favicons, some social previews). Aim for under 200 KB for a social preview and under 100 KB for in-page images. A raw generation is around 2 MB.
4. **Keep the source.** Commit the original PNG under `assets/src/` (gitignored if large; note it in the log) and the optimized file where the app serves it.
5. **Alt text.** Every meaningful image gets alt text that says what it shows; decorative ones get `alt=""`.
6. **Log it** in `burn/ASSETS.md` (below).

### burn/ASSETS.md

One row per asset the product ships, however it was made:

```markdown
| File | What | Source | License / terms | Prompt or origin | Made | By |
|---|---|---|---|---|---|---|
| public/og.webp | Social preview background | Codex image tool (gpt-image) | Generated under the person's OpenAI account; OpenAI's terms assign output rights to the user | "A wide social-preview background: …" | 2026-10-15 | run 3 |
| public/favicon.svg | App icon | Hand-written SVG | Ours | n/a | 2026-10-14 | run 2 |
| src/icons/check.svg | Check icon | Lucide | ISC | lucide.dev/icons/check | 2026-10-15 | run 3 |
```

QA uses this file to check that every image in the product has a known source and license.

## What not to generate

- Pictures of people presented as customers, testimonials or team members. (Also a guardrail: no fake founders or reviews.)
- Screenshots of the product. Take real ones with Playwright.
- Anything that imitates another product's look or brand.
- Anything for an excluded category in [guardrails.md](guardrails.md).
