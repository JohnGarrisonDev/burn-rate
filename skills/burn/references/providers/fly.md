# Fly.io

Runs real containers (Docker images) close to users, with machines that can stop when idle. **There is no free tier for new organizations.** Every running machine, volume and dedicated IP bills from the first second. With `monthly_cap_usd = 0`, don't create anything on Fly.

**Good for:** apps that need a long-running process, websockets, a background worker, or a language runtime the serverless platforms don't support. **Not for:** anything a static host or Workers can do; the first weeks of an MVP on a $0 cap.

If the product needs Fly, raise a cost proposal first ([../cost-proposals.md](../cost-proposals.md)). The smallest always-on machine is about $2/month; a scale-to-zero app with low traffic is usually under $5.

## CLI

`flyctl` (`fly`). It's a global install, so it's a human item:

- macOS/Linux: `curl -L https://fly.io/install.sh | sh`, or `brew install flyctl`
- Windows (PowerShell): `iwr https://fly.io/install.ps1 -useb | iex`

## Auth check

```
fly auth whoami
```

Pass: prints the email. Fail: open a `secret` item:

> Run `fly auth login`, or create an org-scoped token with `fly tokens create org <burn-org> --expiry 2160h` and set it as `FLY_API_TOKEN`. Use a separate Fly organization for the burn company, with a card on file only after a cost proposal is approved.

Also check the org: `fly orgs list`. Deploy only into the burn org (`--org <burn-org>`).

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:fly"` | Human ran `fly auth login`. |
| `credential = "env:FLY_API_TOKEN"` | flyctl reads it. Prefer an org token or per-app deploy token (`fly tokens create deploy -a <app>`), never a personal full-access token. |

## Pricing (no free tier)

Checked October 2026. Verify at https://fly.io/docs/about/pricing/.

| Item | Cost |
|---|---|
| New orgs | Trial of 2 machine-hours or 7 days, then billing. No monthly free allowance. |
| shared-cpu-1x, 256 MB, always on | about $2.19 / 30 days |
| Machines | billed per second while running; stopped machines bill $0.15/GB-month of rootfs |
| Volumes | $0.15/GB-month provisioned, whether attached or not |
| Dedicated IPv4 | $2/month (shared IPv4 and IPv6 are free) |
| Outbound transfer | from $0.02/GB (NA/EU) up to $0.12/GB |
| TLS certificates | first 10 single-hostname certs free |

## Usage and headroom

There's no free limit to track, only spend against the cap. Each run that touches Fly:

```
fly apps list --org <burn-org>
fly machines list -a <app> --json        # count, size, state
fly volumes list -a <app>
fly ips list -a <app>                    # look for a dedicated "v4"
```

Price what you see with the table above and write the estimate in INFRA.md `$/month`. Ask the human to check the dashboard's billing page in the recap if the estimate passes 80% of the cap.

## Provision

```
fly launch --no-deploy --name <slug> --org <burn-org> --region iad --copy-config --yes
```

`fly launch` may offer Postgres, Redis (Upstash), Tigris storage or Sentry. Decline all of them (each is a separate resource with its own cost); add `--no-db --no-redis --no-object-storage` where your flyctl version supports them, and read the generated `fly.toml` before deploying. Check that it has:

```toml
[http_service]
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0

[[vm]]
  size = "shared-cpu-1x"
  memory = "256mb"
```

## Deploy

```
fly deploy -a <slug>-preview --ha=false     # preview: a separate app
fly deploy -a <slug> --ha=false             # production
```

`--ha=false` stops flyctl from creating two machines per process group. Production only when `launch_approved = true`. The preview app costs money too; scale it to zero when idle and destroy it when it's not needed (it's in the cap).

## Secrets

```
printf 'STRIPE_SECRET_KEY=%s\n' "$STRIPE_SECRET_KEY" | fly secrets import -a <slug>
fly secrets list -a <slug>
```

`fly secrets import` reads `NAME=value` lines from stdin, so the value never appears on the command line. Setting secrets restarts machines.

## Custom domain

Buying the domain is a human gate. With a domain the human owns:

```
fly ips list -a <slug>                     # use the shared IPv4 and IPv6
fly certs add www.example.com -a <slug>    # prints the DNS records to set
fly certs check www.example.com -a <slug>
```

Never run `fly ips allocate-v4` without `--shared`: a dedicated IPv4 is $2/month.

## Teardown

Only with an approved human item:

```
fly apps destroy <slug> --yes
fly apps destroy <slug>-preview --yes
fly volumes list -a <slug>                 # should fail: app gone
```

Volumes are deleted with the app. Snapshots older than the retention window go too. Export data first if there's any.

## IaC

- `fly.toml` per app (`fly.preview.toml` for the preview app, deployed with `-c`).
- `Dockerfile` (or a buildpack), committed.

## Cost hazards

- Anything at all, on a $0 cap.
- `fly launch` add-ons (Postgres, Upstash, Tigris) and `--ha` defaults that create two machines.
- Volumes bill while the app is stopped, and every volume pins its machine to one host.
- Dedicated IPv4 addresses.
- Machines set to `auto_stop_machines = "off"` or `min_machines_running >= 1`.
- Larger VM sizes or `performance` CPUs from `fly scale vm`.
- Bandwidth to India/Africa/South America regions at the higher rates.
