# Azure

Capable, but full of things that bill quietly. Use it when the human already has Azure, or the product needs something only Azure offers. For a plain web app, Cloudflare or Vercel is cheaper to run safely.

**Good for:** static sites with a small API (Static Web Apps), small web apps (App Service F1), event-driven functions (Functions, Consumption plan), and anything that needs Microsoft services (Entra ID, Azure OpenAI). **Not for:** always-on containers or databases on a $0 cap; almost every Azure database costs money outside narrow free offers.

## Set up by the human

Recommend, in the setup item, before any provisioning:

1. A **dedicated subscription** for the burn company, so nothing else can be touched and teardown is clean.
2. A **budget with an email alert** on that subscription, set by the human: Azure portal > Cost Management > Budgets > Add, amount = the approved cap (or $1 while the cap is 0), alerts at 50%, 80% and 100%.
3. The agent's identity gets **Contributor** on that subscription only. Never Owner, never User Access Administrator.

## CLI

`az` (Azure CLI). It's a global install, so it's a human item:

- Windows: `winget install --exact --id Microsoft.AzureCLI`
- macOS: `brew install azure-cli`
- Linux: https://learn.microsoft.com/cli/azure/install-azure-cli

Also useful, installed per project: `npm install --save-dev @azure/static-web-apps-cli` (SWA CLI, run as `npx swa`) and, for Functions, `azure-functions-core-tools` (`func`), which is global, so a human item.

Bicep comes with `az`: `az bicep version` (run `az bicep install` only with the human's OK, it downloads a binary).

## Auth check

```
az account show --output json
```

Pass: JSON with `id` and `name`. Then confirm it's the burn subscription:

```
az account show --query id --output tsv
```

Compare with the value at `subscription_id_from`. If they differ, don't change the CLI's default subscription (other tools on the machine use it). Instead pass `--subscription <id>` on every `az` command this run, and check it once: `az account show --subscription <id> --query id --output tsv`. The commands below leave it out for brevity; add it. If `az account show` fails ("Please run 'az login'"), open a `secret` item:

> Run `az login`. Or create a service principal with Contributor on the burn subscription only and set AZURE_CLIENT_ID, AZURE_TENANT_ID and AZURE_CLIENT_SECRET.

With a service principal in env vars: `az login --service-principal -u "$AZURE_CLIENT_ID" -t "$AZURE_TENANT_ID" --password "$AZURE_CLIENT_SECRET"` (the `--password` flag takes the secret; reference the env var, never paste the value).

## Credentials

| config | Meaning |
|---|---|
| `credential = "cli:az"` | Human ran `az login`. |
| `credential = "env:AZURE_CLIENT_SECRET"` | Service principal; also needs `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`. |
| `subscription_id_from = "env:AZURE_SUBSCRIPTION_ID"` | Always pin the subscription. Never deploy to whatever is default. |

## Free tier

Checked October 2026. Verify current limits at https://azure.microsoft.com/pricing/free-services/ and each service's pricing page.

| Service | Free |
|---|---|
| Static Web Apps, Free plan | 100 GB bandwidth per subscription / month, 2 custom domains per app, 0.5 GB storage, 0.25 GB per deployment. Site stops serving past quota. https://azure.microsoft.com/pricing/details/app-service/static/ |
| App Service F1 | 60 CPU minutes / day, 1 GB RAM, 1 GB storage, up to 10 apps. App is stopped (HTTP 403) past quota. No custom TLS, no deployment slots. https://azure.microsoft.com/pricing/details/app-service/linux/ |
| Functions, Consumption | 1M executions and 400,000 GB-s / month per subscription. Flex Consumption: 250,000 executions and 100,000 GB-s. **The storage account each function app needs is not free.** https://azure.microsoft.com/pricing/details/functions/ |
| Azure free account credit | $200 for 30 days, then 12-month free services. Don't plan around it: it expires. |

Static Web Apps Standard is about $9/app/month; App Service B1 is about $13/month. Those are the usual first proposals.

## Usage and headroom

```
az consumption usage list --start-date 2026-10-01 --end-date 2026-10-17 --output table
az consumption budget list --output table                  # confirms the human's budget exists
az monitor metrics list --resource <swa-or-webapp-id> --metric BytesSent --interval P1D --output table
az webapp show -g <rg> -n <app> --query usageState         # "Exceeded" means F1 quota hit
```

Cost Management data lags up to a day. Record real spend next to your estimate in INFRA.md; if the subscription shows any non-zero spend while every cap is 0, that's a high-priority item ([../cost-proposals.md](../cost-proposals.md)).

## Provision

One resource group per project, everything inside it, tagged:

```
az group create -n rg-<slug> -l eastus2 --tags burn-rate=<slug>
az deployment group what-if -g rg-<slug> -f infra/main.bicep -p infra/main.bicepparam
az deployment group create  -g rg-<slug> -f infra/main.bicep -p infra/main.bicepparam
```

Always run `what-if` first and read it. Any SKU other than `Free`/`F1`/consumption with a 0 cap means stop.

Quick paths when Bicep is overkill (still record them in INFRA.md and port to Bicep later):

```
az staticwebapp create -n <slug> -g rg-<slug> -l eastus2 --sku Free
az appservice plan create -n plan-<slug> -g rg-<slug> --sku F1 --is-linux
az webapp create -n <slug>-app -g rg-<slug> -p plan-<slug> --runtime "NODE:20-lts"
```

## Deploy

Static Web Apps (preview environments are free and named). The deployment token never goes to disk: put it in the `SWA_CLI_DEPLOYMENT_TOKEN` environment variable for this shell, which the SWA CLI reads, and clear it afterwards.

Bash (Git Bash on Windows):

```
export SWA_CLI_DEPLOYMENT_TOKEN="$(az staticwebapp secrets list -n <slug> -g rg-<slug> --query properties.apiKey -o tsv)"
npx swa deploy ./dist --env preview-<run>
npx swa deploy ./dist --env production
unset SWA_CLI_DEPLOYMENT_TOKEN
```

PowerShell:

```
$env:SWA_CLI_DEPLOYMENT_TOKEN = az staticwebapp secrets list -n <slug> -g rg-<slug> --query properties.apiKey -o tsv
npx swa deploy ./dist --env preview-<run>
Remove-Item Env:SWA_CLI_DEPLOYMENT_TOKEN
```

Never print it, and never pass it as `--deployment-token` (it would show in the process list and the transcript).

App Service: `az webapp deploy -g rg-<slug> -n <slug>-app --src-path app.zip --type zip`. F1 has no slots, so the preview is a second F1 app (`<slug>-preview`) in the same plan.

Functions: `func azure functionapp publish <app-name>`.

Production only when `launch_approved = true`.

## Secrets

```
az staticwebapp appsettings set -n <slug> -g rg-<slug> --setting-names STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY"
az webapp config appsettings set -g rg-<slug> -n <slug>-app --settings STRIPE_SECRET_KEY="$STRIPE_SECRET_KEY"
```

PowerShell: `"STRIPE_SECRET_KEY=$env:STRIPE_SECRET_KEY"`. Key Vault is cheap but not free per operation; use app settings unless the product needs Key Vault, and say so in DECISIONS.

## Custom domain

Buying a domain (including App Service Domains) is a human gate. With a domain the human owns:

```
az staticwebapp hostname set -n <slug> -g rg-<slug> --hostname www.example.com
```

The human adds the CNAME/TXT records at their DNS provider unless the DNS zone is one you manage. Free managed certificates come with SWA. F1 App Service can't bind custom TLS; that's a cost proposal.

## Teardown

Only with an approved human item. Because everything lives in one group:

```
az group delete -n rg-<slug> --yes
az group list --tag burn-rate=<slug> --output table     # confirm nothing is left
```

Also check for things that live outside the group: `az ad sp list --display-name <slug>` (service principals), and the budget the human made (theirs to keep or remove).

## IaC

- `infra/main.bicep` + `infra/main.bicepparam`. Set SKUs explicitly in Bicep, never rely on defaults.
- `staticwebapp.config.json` for SWA routes and headers.
- `host.json` for Functions.

## Cost hazards

- **Storage accounts** behind every Function app, and Log Analytics / Application Insights ingestion that function and web app templates turn on by default. Set a daily cap on Log Analytics (`az monitor log-analytics workspace update --quota 0.1`) or don't create it.
- App Service plans bill per hour **whether or not apps are running**. Stopping a B1 app doesn't stop the bill; deleting the plan does.
- `az webapp up` picks a paid SKU (B1 or P1v3) unless you pass `--sku F1`.
- Public IPs, NAT gateways, VMs, AKS, Azure SQL (outside the free offer), Cosmos DB (unless free tier is set at creation, one per subscription), Container Registry (no free SKU), Front Door, API Management.
- Free account: after 30 days or $200, the subscription stops unless upgraded to pay-as-you-go. Upgrading is a human action.
- Bicep `what-if` output with `Microsoft.Web/serverfarms` SKU changes, any `Premium` or `Standard` SKU, or `capacity` above 1.
