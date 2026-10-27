# 44 — Accounts, quotas and setup we will need for Tely (a do-later checklist — nothing signed up yet)

_Accessed/compiled: 20 Oct 2026 · Priority area: day-1 setup, region choice, budget, and team ownership for the Tely hero stack (Foundry, Voice Live, Speech, Container Apps, Web PubSub, GitHub Copilot Agent Mode)_

> **Nothing in this file has been signed up for, logged into or requested.** Each step is written so the team can do it later. Steps tagged **[CARD]**, **[PHONE]**, **[WORK-EMAIL]** or **[SCHOOL-EMAIL]** need that team member's own personal details.

## TL;DR

- **Subscription: Azure free account, then upgrade to Pay-As-You-Go straight away.** The free account needs a card and a phone and gives $200 for 30 days. Microsoft says that *"If you upgrade early, unused credit remains available"* for the full 30 days. Our reasons:
  - Microsoft's own quota table lists **"Azure for Students, free trials"** as **N/A** for batch quota.
  - Community Q&A threads report **0 TPM** model quota and region-locking policies (about 5 regions) on Students subscriptions (unverified).
  - Students is fine as a second, no-card sandbox. Don't make it the one the demo depends on.
- **Region: Sweden Central, with East US 2 as the fallback.** Sweden Central is the only European region that ticks every box. Voice Live has `gpt-realtime-2.1-mini` (Global) and `gpt-5.6-luna` there. You can also deploy Global Standard `gpt-realtime-*` and `gpt-5.4-mini/nano` directly. Speech has real-time STT, neural TTS and **HD voices**. ACA, Web PubSub and Cosmos all have price meters there. **West Europe is a trap:** it has no Voice Live realtime models at all.
- **Voice Live needs a paid (S0) Foundry resource.** It is "Not applicable" on F0. It needs **no model deployment**, because the model is "automatically deployed for you". Default S0 limits are 100 new connections per minute, sessions of at most 60 minutes, and 120,000 tokens per minute (TPM). That is plenty for judging. **The Speech quota-increase form rejects Gmail and Hotmail addresses**, so we must stay inside the defaults.
- **Budget: about $45-87 in total (plan for $100) for the build week (21-27 Oct) plus judging (27 Oct-10 Nov)** at Sweden Central list prices. The arithmetic is below. The free account's $200 covers it. Watch out: the credit expires 30 days after sign-up, and if we haven't upgraded by then, *"your account and services will be disabled"*.
- **GitHub Copilot Free includes Agent Mode in the IDE**, which covers the hero technology at $0. It has a cap of 2,000 completions a month and auto model selection only. The cloud agent needs Pro ($10/month) or the Student plan. **URGENT, separate from this checklist:** hackathon registration closes **today, 20 Oct, 12:00 PT (20:00 London / 22:00 Sofia)**, per research 12.

## Findings

### 1. Which Azure subscription type

| | Free account | Azure for Students | Pay-As-You-Go (upgrade) |
|---|---|---|---|
| Credit | $200 for 30 days | $100 for 12 months | none (free tiers still apply) |
| Needs | **[CARD]** non-prepaid credit/debit card, **[PHONE]**, a Microsoft or GitHub account; $1 temporary hold | **[SCHOOL-EMAIL]**, full-time university student, **no card** | the same card |
| Foundry model quota | Assigned through quota tiers "based on … the subscription's Azure offer". A "Free Tier" exists, and for some models it is **0 TPM** (Grok 4.7 table). | Batch quota is "N/A" for "Azure for Students, free trials" (official). Community threads report 0 TPM and region locks (unverified). | Normal Tier 1 defaults, e.g. `gpt-5.4-mini` GS 1M TPM, `gpt-5.4-nano` GS 5M TPM, `gpt-realtime` GS 100K TPM |
| After the end | Must upgrade, or the account is disabled | Renews yearly while you are a student | — |

Official tier facts:
- There are seven tiers, Free plus Tiers 1-6, and you move up automatically with usage.
- If you request more quota, *"the current tier will remain the same, but with more quota assigned"*. The form is https://aka.ms/oai/stuquotarequest. *"priority goes to customers who actively use their existing quota"*.
- **Since 7 May 2026, quota is a subscription-level pool.** All Global Standard deployments of a model share it across regions, so picking a region no longer gains or loses quota.

### 2. Services we need: what to create, prerequisites, lead time, cost

Prices are USD list prices for Sweden Central from the Retail Prices API. They are identical to East US 2 for the Voice Live meters we checked.

| Service | Create | Needs / lead time | Free tier | List price | Gotchas |
|---|---|---|---|---|---|
| **Foundry resource + project** | `kind: AIServices`, S0. Portal: https://ai.azure.com → Create project | Subscription. `Cognitive Services User` role for keyless Voice Live. Minutes. | — | pay per use | Up to 32 deployments per resource and 250 projects per resource |
| **Text model** | `gpt-5.4-mini` (2026-03-17) GlobalStandard, capacity 10 (= 10K TPM, file 30), plus `gpt-5.4-nano` | Quota must be > 0. Check first: Foundry portal → Quota | Tier 1: 1M TPM (mini) | mini $0.75 in / $0.075 cached / $4.50 out per 1M. nano $0.20 / $0.02 / $1.25 | A new subscription *"can legitimately start at 0 TPM"* (MS moderator, Q&A, unverified). If so, file the form: **days, approval not guaranteed** |
| **Voice Live** (talk to the commentator) | Nothing to deploy. Use `wss://<res>.services.ai.azure.com/voice-live/realtime?...&model=gpt-realtime-2.1-mini` | S0 Foundry resource in a supported region | F0 "Not applicable" | Standard tier: LLM audio in $0.011, LLM audio out $0.022, Azure standard-voice audio out $0.026, text in $0.00066, text out $0.00264, cached $0.00033 (all per 1K tokens) | Audio is about 10 tokens/s in and 20 tokens/s out. S0 limits: 100 new connections/min, sessions of 60 min or less, 120K TPM. **Quota form needs a work email.** |
| **Azure Speech TTS** (pre-rendered SSML commentary) | Use the Foundry resource's Speech endpoint, or a separate `SpeechServices` F0 resource for the free allowance | — | F0: 0.5M neural characters a month. 20 transactions per 60 s, not adjustable. **F0 real-time STT allows 1 concurrent request.** | Neural $15 per 1M characters, **HD $22 per 1M**, real-time STT $1/h | Custom neural voice, personal voice and custom avatar are **Limited Access** (intake form aka.ms/customneural; "Only customers managed by Microsoft", file 27). Plan stock and HD voices only. One F0 per resource type per subscription (community Q&A, unverified). |
| **Translator** (Bulgarian and other languages) | `TextTranslation` F0, or through the Foundry resource (unverified) | — | 2M characters a month (free-account page). F0 rate: 2M characters per hour | S1 $10 per 1M (file 03) | 50,000 characters per request |
| **Web PubSub** (cues to the phone for haptics and crowd mix) | Free_F1 for dev, Standard_S1 for judging | — | Free: 20 concurrent connections, 20,000 messages/day, no overage | Standard: $1.61 per unit-day + $1 per 1M messages | **Changing Free ↔ Standard changes the public IP: expect 30-60 min of downtime.** Create the judge instance as Standard from the start. |
| **Container Apps** (worker / FastAPI) | Consumption environment | — | Per subscription per month: 180,000 vCPU-s, 360,000 GiB-s, 2M requests | vCPU $0.000024/s active, $0.000003/s idle. Memory $0.000003 per GiB-s | Idle rate only applies at `minReplicas` with < 0.01 vCPU in use. AVM default is `minReplicas: 3` (file 30) |
| **Container Registry** | Basic | — | — | $0.1666/day | |
| **Static Web Apps** (replay page) | Free | — | 250 MB per app, 3 staging environments, no SLA | Standard $9/month | The SWA resource region list is short. Content is globally distributed anyway, so use `westeurope` (file 30; exact list unverified) |
| **Cosmos DB** | NoSQL, provisioned, `--enable-free-tier true` | — | 1,000 RU/s + 25 GB for the account's lifetime | 100 RU/s $0.008/h. Serverless $0.305 per 1M RU | **One free-tier account per subscription. You can only set it at creation, and it doesn't apply to serverless.** |
| **Key Vault** | Standard, RBAC mode | — | — | $0.03 per 10K operations | AVM default is `premium` (file 30) |
| **App Insights / Log Analytics** | Workspace-based | — | 5 GB/month ingestion | $2.99/GB after that. Availability test $0.0005 per run (file 21) | Set `dailyQuotaGb: 1` |
| **Fabric trial** (optional) | Trial from the Fabric Account manager | **[WORK-EMAIL]**: Gmail/Hotmail refused (file 34) | 60 days, F4 or F64 | F2 $0.36/h (file 34) | No Copilot or data agents on the trial |

### 3. GitHub, Copilot, Azure MCP, YouTube

- **GitHub repo:** public. *"GitHub Actions usage is free for … public repositories that use standard GitHub-hosted runners."*
- **Codespaces:** GitHub Free includes *"120 hrs of compute time and 15 GB-month of storage"* a month. Older docs counted core-hours, so a 2-core machine may get only 60 h (unverified). Without a payment method, *"usage is blocked once you use up your quota"*, so there are no surprise bills.
- **GitHub Copilot:**
  - **Free:** Agent mode is included in the IDE. 2,000 completions a month, auto model only, no cloud agent.
  - **Pro:** $10/month, 1,500 AI Credits.
  - **Student plan:** free for verified GitHub Education students, and includes agent mode and the cloud agent. Verification goes through github.com/settings/education/benefits, and *"can take several days to finish applying after verification"*. A search snippet says new Student sign-ups were paused on 20 Apr 2026, but the docs page we fetched doesn't mention a pause (unverified). **Don't count on it this week.**
- **Azure MCP Server (2.0 GA), local needs:**
  - Node.js LTS (for `npx`), or .NET 10 / uv.
  - The VS Code extension `ms-azuretools.vscode-azure-mcp-server` plus Copilot Chat.
  - `az login` before starting. It acts with our own RBAC.
  - Docker alternative: `mcr.microsoft.com/azure-sdk/azure-mcp:latest`, which needs a service principal.
- **YouTube:** needs a Google account. *"By default, you can upload videos that are up to 15 minutes long"*. Our video is under 2 minutes, so **no phone verification** is needed. Set it to Public.

### 4. Region decision table

Sources: Speech regions (Voice Live, STT and TTS tabs) and Foundry region availability (Global Standard). For ACA, Web PubSub and Cosmos, the evidence is that a Sweden Central or East US 2 price meter exists in the Retail Prices API. The East US 2 entries for these come from file 21.

| Need | **Sweden Central** | East US 2 | West Europe | UK South |
|---|---|---|---|---|
| Voice Live `gpt-realtime-2.1-mini` | Global | Global | **–** | Global |
| Voice Live `gpt-5.6-luna` / `gpt-4.1-mini` | Data zone / Regional | Data zone / Regional | Data zone | Global |
| Voice Live HD voices | Regional | Data zone | Regional | Global |
| `mai-transcribe-2-streaming` | Global | Data zone | – | – |
| Direct Global Standard `gpt-realtime-2.1(-mini)` | yes | yes | – | – |
| `gpt-5.4-mini/nano` Global Standard | yes | yes | yes | yes |
| `gpt-4o-mini-tts` Global Standard | – | yes | – | – |
| Speech real-time STT / neural TTS / HD voices (standalone) | yes / yes / yes | yes / yes / yes | yes / yes / yes | yes / yes / **–** |
| Multi-talker HD (preview, file 27) | – | – | yes | – |
| ACA (+ T4/A100 GPU meters) | yes | yes | yes (T4 needs a new environment, file 30) | (unverified) |
| Web PubSub / Cosmos | yes / yes | yes / yes | (unverified) | (unverified) |
| Distance to Sofia/London (voice round trip) | **near** | far | near | near |

**Decision: Sweden Central.** It is the only region that ticks every Tely row, and it is close to both team members, which helps barge-in latency. **Fallback: East US 2**, which ticks everything and adds `gpt-4o-mini-tts`. Community threads report that Students subscriptions often offer only *"East US 2" or "Sweden Central"* (unverified). Put SWA in `westeurope`. If we need it, the Fabric trial is offered in all Fabric regions.

### 5. Budget estimate (USD list prices, Sweden Central)

**Assumptions** (ours, not quotes):
- Voice Live audio is 10 tokens/s in and 20 tokens/s out, so a minute is **600 tokens in and 1,200 tokens out**.
- Each Q&A turn sends about 3,000 text tokens of context.
- The commentary script is about 18,000 characters per full match render.
- One moment call on `gpt-5.4-mini` costs about $0.0016: 1,000 cached × $0.075/M, plus 500 input × $0.75/M, plus 250 output × $4.50/M.

**Build week, 21-27 Oct (dev)**

| Item | Arithmetic | $ |
|---|---|---|
| Voice Live testing: 2 people × 7 days × 30 min | 210 min user audio × 600 × $0.011/1K = $1.39. 210 min answers in an Azure voice × 1,200 × $0.026/1K = $6.55. 420 turns × 3,000 × $0.00066/1K = $0.83 | 8.77 |
| HD TTS re-renders: 30 × 18,000 characters | 540,000 × $22/1M | 11.88 |
| `gpt-5.4-mini` moments: 30 runs × 200 | 6,000 × $0.0016 | 9.60 |
| Translator: 2 languages × 18,000 × 30 | 1.08M characters, inside the F0 2M/month (S1 would be $10.80) | 0-10.80 |
| ACA dev worker, 0.25 vCPU / 0.5 GiB, always active | 151,200 vCPU-s and 302,400 GiB-s, both under the free grant | 0 |
| ACR Basic | 7 × $0.1666 | 1.17 |
| SWA Free, Cosmos free tier, Web PubSub Free, Key Vault, LA under 5 GB | — | ~0 |
| **Subtotal** | | **≈ 31-42** |

**Judging, 27 Oct-10 Nov (15 days, `judge` environment)**

| Item | Arithmetic | $ |
|---|---|---|
| Web PubSub Standard, 1 unit (optional: replay can use Free) | 15 × $1.61 | 0-24.15 |
| ACA, 0.25 vCPU / 0.5 GiB, `minReplicas 1`, no free grant | 1,296,000 s. Idle: 324,000 × $0.000003 + 648,000 × $0.000003 = $2.92. All active: $7.78 + $1.94 = $9.72 | 2.92-9.72 |
| ACR Basic | 15 × $0.1666 | 2.50 |
| Availability test: 3 locations every 5 minutes | 3 × 288 × 15 = 12,960 × $0.0005 | 6.48 |
| Judges talking: 20 sessions × 5 min | 50 min × 600 × $0.011/1K = $0.33. 50 min × 1,200 × $0.026/1K = $1.56. 200 turns × 3,000 × $0.00066/1K = $0.40 | 2.29 |
| **Subtotal** | | **≈ 14-45** |

**Total ≈ $45-87.** Plan for about $100. Set a Cost Management budget with alerts at $50 and $100. Budgets *don't stop spending* (file 21), so the real brakes are a low TPM capacity and an in-app daily cap. If the demo must stay up until winners are announced (20 Nov), add about 10 days at the judging rate, roughly $10-30.

### 6. Who owns which account (2 people)

| Owner | Accounts | Why |
|---|---|---|
| **Person A, "Azure owner"** | Azure free account → PAYG **[CARD] [PHONE]**. Billing, budgets, the Foundry resource, model deployments, quota requests, Key Vault, Cosmos, Web PubSub, ACA. Optional Fabric trial if A has a **[WORK-EMAIL]**. | One card and one phone. One person sees every cost alert. |
| **Person B, "GitHub & story owner"** | GitHub repo owner. Actions OIDC (`azd pipeline config`, run with A's consent as Owner). Copilot (Free; Pro only if limits bite). YouTube channel. Innovation Studio submission. | It keeps the public face and the submission off the billing account. |
| Both | Copilot Free each. B is invited to A's subscription as **Contributor** on the resource groups (B uses their own Microsoft account, no card). Both use `az login` for Azure MCP. | Least privilege. Either can deploy. |

## So what for us

- **Tely, all stages: Ingest → Explain → Render (audio and haptics) → Personalise (Q&A).** Everything Tely needs fits in one Sweden Central resource group:
  - Explain uses a `gpt-5.4-mini` deployment.
  - Render pre-renders HD-voice SSML commentary (look-ahead lets us pre-render).
  - Personalise uses Voice Live `gpt-realtime-2.1-mini` for "ask the commentator". There is nothing to deploy, and it runs on the Standard price tier.
  - Render sends haptic and crowd-mix cues over Web PubSub.
- **Do now:** pick Person A and Person B, and make sure A has a card and phone ready. Sign-up waits for the team's go-ahead (no-sign-ups rule).
- **Day 1 risk to kill first: model quota.** Check the Quota page in the first 15 minutes. If it shows 0 TPM, file the form at once and build against replay and pre-rendered audio while you wait.
- **Other ideas:**
  - TwinCast's serverless GPU needs the T4 quota, which is on by default only for PAYG/EA (file 30). That is another reason for PAYG.
  - Chalk Talk uses the same Voice Live setup.
  - Fabric is optional, and only if someone has a work email.

### Day-1 checklist (about 60 minutes; do in order)

- [ ] **0. (today, B)** Check that hackathon registration is done before 20 Oct 12:00 PT (file 12). It needs an Entra work/school sign-in.
- [ ] **1. (5 min, A) [CARD] [PHONE]** Create an Azure free account at https://azure.microsoft.com/pricing/purchase-options/azure-account.
- [ ] **2. (2 min, A) [CARD]** Upgrade to Pay-As-You-Go right away: portal → Subscriptions → Upgrade. The credit stays for its 30 days. Note the expiry date.
- [ ] **3. (3 min, A)** Create a budget of $100 with alerts at 50% and 100%: portal → Cost Management → Budgets.
- [ ] **4. (3 min, A)** Run `az login`, register the resource providers (script below), and create `rg-as-dev` and `rg-as-judge` in `swedencentral`.
- [ ] **5. (5 min, A)** Create the Foundry resource and project in Sweden Central (https://ai.azure.com). Give A and B `Cognitive Services User` and `Azure AI User` (unverified role name).
- [ ] **6. (5 min, A)** Check quota at Foundry → Management → Quota, and check the tier with the `quotaTiers` call below. **If any needed model shows 0 TPM, file https://aka.ms/oai/stuquotarequest now** and ask for a modest amount (10-30K TPM).
- [ ] **7. (5 min, A)** Deploy `gpt-5.4-mini` with GlobalStandard capacity 10 and `NoAutoUpgrade`. Smoke-test it with the `openai` SDK (file 03).
- [ ] **8. (5 min, A)** Open a Voice Live smoke test in the Foundry playground with `gpt-realtime-2.1-mini` and an `en-GB` HD voice, and ask one question.
- [ ] **9. (5 min, A)** Create Cosmos with the free tier (only one per subscription, so use it on `dev` *or* share it), Key Vault (RBAC) and Log Analytics with `dailyQuotaGb 1`. Or just run `azd up` (file 30).
- [ ] **10. (3 min, A)** Create Web PubSub Free_F1 in dev. **Create the judge one as Standard_S1 later**, never by upgrading Free.
- [ ] **11. (3 min, A)** Invite B as Contributor on both resource groups: IAM → Add role assignment.
- [ ] **12. (5 min, B)** Create the public GitHub repo, enable Actions, and run `azd pipeline config` with A present for the OIDC consent.
- [ ] **13. (5 min, A+B)** Turn on Copilot Free in VS Code. Install the Azure MCP Server extension and Node LTS, then `az login`. Try one Agent Mode prompt that lists our resource group.
- [ ] **14. (2 min, B)** Create or choose the YouTube channel. No upload yet.
- [ ] **15. (optional, A or B) [WORK-EMAIL]** Fabric trial, only if we decide to use it (file 34).

## Reuse: code & links

```bash
# Day-1 bootstrap (Person A, after the subscription exists). Verify flags with --help; some are (unverified).
az login && az account set --subscription "<SUB_ID>"
for p in Microsoft.CognitiveServices Microsoft.App Microsoft.OperationalInsights Microsoft.Insights \
         Microsoft.SignalRService Microsoft.DocumentDB Microsoft.KeyVault Microsoft.Web Microsoft.ContainerRegistry; do
  az provider register -n $p; done
az group create -n rg-as-dev -l swedencentral
az cognitiveservices account create -n as-foundry-dev -g rg-as-dev -l swedencentral \
  --kind AIServices --sku S0 --custom-domain as-foundry-dev --yes
az cognitiveservices usage list -l swedencentral -o table          # quota per model; look for 0 limits
az rest --method get --url "https://management.azure.com/subscriptions/<SUB_ID>/providers/Microsoft.CognitiveServices/quotaTiers?api-version=2025-10-01-preview"
az cognitiveservices model list -l swedencentral --query "[?model.name=='gpt-5.4-mini'].model.version" -o tsv
az cognitiveservices account deployment create -n as-foundry-dev -g rg-as-dev \
  --deployment-name gpt-5.4-mini --model-name gpt-5.4-mini --model-version 2026-03-17 \
  --model-format OpenAI --sku-name GlobalStandard --sku-capacity 10
az cosmosdb create -n as-cosmos-dev -g rg-as-dev --enable-free-tier true --default-consistency-level Session
az extension add -n webpubsub && az webpubsub create -n as-wps-dev -g rg-as-dev -l swedencentral --sku Free_F1
```

```bash
# Azure MCP Server for Copilot Agent Mode (local)
node --version            # need LTS
az login
npx -y @azure/mcp@latest server start     # or the VS Code extension ms-azuretools.vscode-azure-mcp-server
```

- Price re-check (no sign-in): `https://prices.azure.com/api/retail/prices?$filter=armRegionName eq 'swedencentral' and contains(meterName,'Voice Live')`
- Bicep/azd for all of the above: file 30. Ops and abuse guards: file 21.

## Sources

- Azure free account — https://azure.microsoft.com/en-us/pricing/purchase-options/azure-account — accessed 20 Oct 2026
- Azure for Students — https://azure.microsoft.com/en-us/free/students — accessed 20 Oct 2026
- Azure OpenAI in Foundry Models quotas and limits (tiers, Tier 1 table, batch quota by offer) — https://learn.microsoft.com/en-us/azure/foundry/openai/quotas-limits — accessed 20 Oct 2026
- Foundry Models quotas and limits (subscription-level quota, Free Tier = 0 example, request form) — https://learn.microsoft.com/en-us/azure/foundry/foundry-models/quotas-limits — accessed 20 Oct 2026
- Region availability for Foundry Models sold by Azure — https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure-region-availability — accessed 20 Oct 2026
- Foundry Models sold by Azure (model versions) — https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure — accessed 20 Oct 2026
- Supported regions for Azure Speech (Voice Live, STT, TTS tabs) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/regions — accessed 20 Oct 2026
- Voice Live API overview (models, pricing tiers, no deployment needed, Limited Access notes) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live — accessed 20 Oct 2026
- Voice Live quickstart (prerequisites, roles) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/voice-live-quickstart — accessed 20 Oct 2026
- Azure Speech quotas and limits (F0/S0, Voice Live limits, quota form rejects personal email) — https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-services-quotas-and-limits — accessed 20 Oct 2026
- Translator service limits — https://learn.microsoft.com/en-us/azure/ai-services/translator/service-limits — accessed 20 Oct 2026
- Azure Retail Prices API (Voice Live, Speech, Foundry Models, ACA, Web PubSub, Cosmos, Key Vault, SWA, ACR, Log Analytics; Sweden Central, East US 2) — https://prices.azure.com/api/retail/prices — accessed 20 Oct 2026
- Container Apps billing (free grant, idle rules) — https://learn.microsoft.com/en-us/azure/container-apps/billing — accessed 20 Oct 2026
- Web PubSub scaling (Free↔Standard downtime) — https://learn.microsoft.com/en-us/azure/azure-web-pubsub/howto-scale-manual-scale — accessed 20 Oct 2026
- Azure subscription and service limits (Web PubSub table) — https://learn.microsoft.com/en-us/azure/azure-resource-manager/management/azure-subscription-service-limits — accessed 20 Oct 2026
- Cosmos DB lifetime free tier — https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier — accessed 20 Oct 2026
- Static Web Apps hosting plans — https://learn.microsoft.com/en-us/azure/static-web-apps/plans — accessed 20 Oct 2026
- Fabric trial capacity — https://learn.microsoft.com/en-us/fabric/fundamentals/fabric-trial — accessed 20 Oct 2026
- GitHub Copilot plans — https://docs.github.com/en/copilot/get-started/plans — accessed 20 Oct 2026
- Copilot for students — https://docs.github.com/en/copilot/how-tos/copilot-on-github/set-up-copilot/enable-copilot/set-up-for-students — accessed 20 Oct 2026
- Student plan news (unverified, third party) — https://roboin.io/article/en/2026/03/13/github-copilot-student-plan-removes-direct-access-to-premium-models/ — accessed 20 Oct 2026
- GitHub Codespaces billing — https://docs.github.com/en/billing/concepts/product-billing/github-codespaces — accessed 20 Oct 2026
- GitHub Actions billing — https://docs.github.com/en/billing/concepts/product-billing/github-actions — accessed 20 Oct 2026
- Azure MCP Server get started — https://learn.microsoft.com/en-us/azure/developer/azure-mcp-server/get-started — accessed 20 Oct 2026
- Azure MCP Server README — https://github.com/microsoft/mcp/blob/main/servers/Azure.Mcp.Server/README.md — accessed 20 Oct 2026
- YouTube: upload videos longer than 15 minutes — https://support.google.com/youtube/answer/71673 — accessed 20 Oct 2026
- Q&A: new subscription shows 0 TPM (community/MS moderator) — https://learn.microsoft.com/en-us/answers/questions/5919307/new-foundry-subscription-shows-0-tpm-quota-for-all — accessed 20 Oct 2026
- Q&A: PAYG 0 quota in East US 2 — https://learn.microsoft.com/en-us/answers/questions/5956615/i-am-unable-to-deploy-model-in-foundry-it-says-i-d — accessed 20 Oct 2026
- Q&A: Azure OpenAI with Azure for Students — https://learn.microsoft.com/en-us/answers/questions/2183197/azure-openai-with-azure-for-students — accessed 20 Oct 2026
- Q&A: Students region policy (RequestDisallowedByAzure) — https://learn.microsoft.com/en-us/answers/questions/5870175/azure-for-students-requestdisallowedbyazure-policy — accessed 20 Oct 2026
- Earlier library files: 01, 03, 12, 21, 27, 30, 34 (this folder)
