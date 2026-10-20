# 30 — One `azd up` for the whole stack: Bicep with Azure Verified Modules, keyless RBAC, and Container Apps jobs

_Accessed/compiled: 20 Oct 2026 · Priority area: infrastructure as code, deployment, cost and abuse guards (all pipeline stages)_

## TL;DR

- **azd can now deploy Container Apps jobs itself, so we don't need a workaround.** Since azd **1.23.8** (6 Mar 2026, PR #7001), `host: containerapp` also targets a `Microsoft.App/jobs` resource. Bicep creates the job with the `azd-service-name` tag, and `azd deploy` builds and pushes the image, then calls `UpdateContainerAppJobImage`. Latest azd is 1.36.0 (14 Oct 2026). **Recommended:** render and CV are normal azd services pointing at Bicep-made jobs. Pin `requiredVersions.azd: ">= 1.23.8"`. Keep the `az containerapp job update` hook only as a fallback.
- **One `main.bicep`, 16 AVM modules, one user-assigned identity (UAMI), no keys.** The current registry versions are below, read from MCR on 20 Oct 2026. Every data-plane permission is a role assignment, passed through each module's `roleAssignments` parameter. Cosmos uses `sqlRoleAssignments` with data-plane role `…0002`. All role GUIDs were checked against the built-in roles page.
- **Several AVM defaults are WAF-grade, which means expensive or locked down for a hackathon.** Examples: Container App `minReplicas: 3`, ACR `Premium` + zone redundancy, a Cosmos account and Container Apps environment with `publicNetworkAccess: 'Disabled'`, a storage firewall that defaults to `Deny`, Key Vault `premium` + purge protection, and Log Analytics 365-day retention. Override them all explicitly (table below).
- **Foundry model in Bicep:** `kind: 'AIServices'`, a deployment with `sku: { name: 'GlobalStandard', capacity: 10 }`. Capacity 1 = 1,000 TPM, so this is a 10K TPM hard ceiling, which is file 21's abuse guard. Add `versionUpgradeOption: 'NoAutoUpgrade'` so `judge` doesn't drift.
- **Cost knobs are Bicep params fed from `azd env set`** through `main.parameters.json` (`${VAR=default}`). `dev` and `judge` differ only in their `.azure/<env>/.env` files.

## Findings

### 1. AVM module versions (latest tags in `mcr.microsoft.com/v2/bicep/avm/res/<path>/tags/list`, 20 Oct 2026)

| Module (`br/public:avm/res/...`) | Version | Default we must override |
|---|---|---|
| `managed-identity/user-assigned-identity` | 0.6.0 | — |
| `operational-insights/workspace` | 0.16.1 | `dataRetention: 365`, `dailyQuotaGb: '-1'` (no cap) |
| `insights/component` | 0.8.0 | `retentionInDays: 365`; needs `workspaceResourceId` |
| `container-registry/registry` | 0.13.1 | `acrSku: 'Premium'`, `zoneRedundancy: 'Enabled'` |
| `app/managed-environment` | 0.16.0 | `publicNetworkAccess: 'Disabled'`, `zoneRedundant: true` |
| `app/container-app` | 0.23.0 | `scaleSettings: { minReplicas: 3, maxReplicas: 10 }` |
| `app/job` | 0.7.2 | `replicaTimeout: 1800`, `replicaRetryLimit: 0` |
| `event-hub/namespace` | 0.15.2 | `disableLocalAuth: true` (good) |
| `signal-r-service/web-pub-sub` | 0.7.2 | `sku: 'Standard_S1'` (paid); `disableLocalAuth: true` (good) |
| `document-db/database-account` | 0.21.1 | `networkRestrictions.publicNetworkAccess: 'Disabled'`, `zoneRedundant: true`, `enableFreeTier: false`; `disableLocalAuthentication: true` (good) |
| `storage/storage-account` | 0.33.1 | `skuName: 'Standard_GRS'`, `allowSharedKeyAccess: true`, firewall `defaultAction: 'Deny'` when `networkAcls` is empty |
| `cognitive-services/account` | 0.19.1 | `disableLocalAuth: true` (good); `restrictOutboundNetworkAccess: true` |
| `key-vault/vault` | 0.14.2 | `sku: 'premium'`, `enablePurgeProtection: true`, `softDeleteRetentionInDays: 90` |
| `web/static-site` | 0.9.6 | `sku: 'Free'` (fine for dev) |

All parameter names were checked in each module's `main.bicep` at the published tag. Two quirks:
- The Container Apps environment and Cosmos modules describe their zone/network defaults as "WAF compliant" settings. We don't need zones or private networking, so set `zoneRedundant: false` and `publicNetworkAccess: 'Enabled'`.
- `container-app` takes `cpu: json('0.25')` (the module's own test notes that floats aren't supported in Bicep). `app/job` types `cpu` as a **string** (`'2'`, `'1.25'`).

### 2. Role GUIDs (verified on the built-in roles page, 20 Oct 2026)

| Role | GUID | Who / scope in our stack |
|---|---|---|
| Azure Event Hubs Data Sender | `2b629674-e913-4c01-ae53-ef4638d8f975` | UAMI (sim producer) on namespace |
| Azure Event Hubs Data Receiver | `a638d3c7-ab3a-418d-83e6-5f17a39d4fde` | UAMI (worker) on namespace |
| Web PubSub Service Owner | `12cf5a90-567b-43ae-8102-96cf46c7d9b4` | UAMI on Web PubSub (token minting + `send_to_group`) |
| Cognitive Services OpenAI User | `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd` | UAMI on the Foundry account |
| Storage Blob Data Contributor | `ba92f5b4-2d11-453d-a403-e96b0029c9fe` | UAMI (renders, CV output, EH checkpoints) |
| AcrPull | `7f951dda-4ed3-4680-a7ca-43fe172d538d` | UAMI on ACR (worker and jobs pull images) |
| Key Vault Secrets User | `4633458b-17de-408a-b874-0445c86b69e6` | UAMI on vault (only if we ever store a 3rd-party secret) |
| Container Apps Jobs Operator | `b9a307c4-5aa3-4b52-ba60-2b17c136cd7b` | UAMI on each job (worker starts render/CV runs) |
| Cosmos DB Built-in Data Contributor (**data plane**) | `00000000-0000-0000-0000-000000000002` | via `sqlRoleAssignments`, not Azure RBAC |

Cosmos data-plane roles "are distinct from Azure role-based access control role definitions." Owner or Contributor on the account does **not** let the SDK read items. The AVM Cosmos submodule turns a bare GUID into `${account.id}/sqlRoleDefinitions/<guid>`, and it also accepts the role name.

**Pass GUIDs, not role names.** The AVM Web PubSub module's name map uses the old label `'Web PubSub Service Owner (Preview)'`. The current built-in name, "Web PubSub Service Owner", would miss that map, and the module would then try to treat the name as a GUID.

**Gotchas from the RBAC troubleshooting page:**
- Set `principalType: 'ServicePrincipal'` for a newly created identity. This avoids `PrincipalNotFound` caused by replication delay.
- Name raw assignments `guid(scope, principalId, roleId)`.
- Role changes "can take up to 10 minutes" to take effect. Our postprovision hook therefore probes before seeding data.
- The jobs docs warn that anyone who can **start** a job can override its template. They can then read the job's secrets and use its identities. That is one more reason to keep jobs secret-free (keyless).

### 3. Deploying Container Apps jobs: options compared

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Native azd (recommended)** | Bicep creates `Microsoft.App/jobs` tagged `azd-service-name: cv`; `azure.yaml` lists `cv` with `host: containerapp` | One `azd up` / `azd deploy cv`; same build, tag and push path as the worker; GitHub Actions from file 21 needs no changes | Needs azd ≥ 1.23.8. azd changes only the container image (it matches the container by image repository, otherwise the first one) plus the service `env:`. CPU, GPU profile and trigger stay in Bicep. The job must already exist at provision time with a placeholder image |
| B. Bicep-only image ref + hook | Hook runs `az acr build`, sets `CV_IMAGE`, then `azd provision` again | Works on any azd | A full ARM deployment for every image change (slow); easy to forget |
| C. `az containerapp job update --image` in a `postdeploy` hook | `az acr build -r <acr> -t twincast/cv:<sha> jobs/cv` then `az containerapp job update -n … --image …` | Works on any azd; good fallback | Duplicates build logic; needs `az login` as well as `azd auth login` |
| D. Separate GitHub Actions job | Build, push and update in CI only | Clean audit trail | Doesn't help local `azd up`; with A it is unnecessary because CI already runs `azd deploy` |

**What azd does underneath.** It sets `SERVICE_<NAME>_RESOURCE_EXISTS` in a preprovision handler, so the template can keep the deployed image. It sets `SERVICE_<NAME>_IMAGE_NAME` after deploy. It pushes to `AZURE_CONTAINER_REGISTRY_ENDPOINT`. If an `infra/<service>.bicep` module exists, azd deploys that instead. All of this comes from reading `service_target_containerapp.go`. We use the "exists" pattern so that a later `azd provision` (for example, flipping an ops knob on `judge`) doesn't reset a job back to the hello-world image.

**Triggers.**
- **Manual + start from the worker.** Use this for render/CV. The worker UAMI needs Jobs Operator (or a custom role with `Microsoft.App/jobs/start/action`). A start-time template **replaces the whole template**, so copy the container and override only `env`.
- **Event.** This uses KEDA scalers (for example `azure-queue`, which can use `identity` in AVM `rules`) to fan out one execution per message. It polls every 30 s by default.
- **Schedule.** Cron, evaluated in UTC. Fine for a nightly "regenerate replay bundle" job.

**GPU.** Serverless GPUs need a **workload-profiles** environment. Add a profile of type `Consumption-GPU-NC8as-T4` (8 vCPU / 56 GiB, the official tutorial uses `--cpu 8.0 --memory 56.0Gi`) or `Consumption-GPU-NC24-A100`. Point the job at it with `workloadProfileName`. Billing is per second and scales to zero.
- **Regions:** T4 is in Sweden Central, West Europe, East US and others. West Europe needs a new environment for T4.
- **Quota:** "Managed Environment Consumption T4 GPUs". It is on by default for EA and pay-as-you-go. Other offers request it from the environment's Quota page.
- Only the first container gets the GPU.
- Artifact streaming, which reduces cold start, needs a Premium ACR, so we skip it.

### 4. Foundry model deployment with a TPM cap

- `Microsoft.CognitiveServices/accounts/deployments`, `sku.capacity`: "A value of 1 equals 1,000 Tokens per Minute (TPM)".
- For older chat models, 1 unit = 6 RPM. Newer and reasoning models use different ratios (o3/o4-mini: 1 unit = 1 RPM / 1,000 TPM).
- TPM is enforced on an *estimate* (prompt + `max_tokens`), and anything over it gets a 429. So capacity 10 is a hard ceiling. File 21 computed the worst case at 10K TPM as $64.80/day of output.
- The AVM `deployments[]` item takes `model`, `sku`, `raiPolicyName`, `versionUpgradeOption`.
- Use `kind: 'AIServices'` plus a `customSubDomainName`, which keyless Entra tokens need (common practice; not re-checked in this pass).
- Look up the model version per region (`az cognitiveservices model list -l <region>`). Don't hard-code it from memory.

### 5. Per-environment cost parameters

| Param (`azd env set …`) | `dev` | `judge` | Why |
|---|---|---|---|
| `WORKER_MIN_REPLICAS` / `MAX` | 0 / 1 | 1 / 2 | warm hot path on demo day (files 01, 21) |
| `WPS_SKU` | `Free_F1` | `Free_F1` | file 21: judges land on replay; switch to `Standard_S1` only if >20 connections |
| `SWA_SKU` | `Free` | `Standard` | file 21's judge stack |
| `DEPLOY_EVENTHUBS` | `true` | `false` | file 21: leave Event Hubs out of judge mode |
| `COSMOS_FREE_TIER` | `true` | `false` if same subscription | "up to one free tier … account per … subscription", and it can only be set at creation time |
| `ENABLE_GPU` | `true` | as quota allows | consumption GPU has no idle charge (per-second, scale to zero) |
| `LLM_CAPACITY_K` | 10 | 10 | 10K TPM ceiling |

## So what for us

- **Stages:** this sits under all five stages (Ingest, Interpret, Explain, Render, Personalise). It matters most for **A TwinCast**, whose render and CV steps are jobs (render on CPU, CV YOLO+ByteTrack on the T4 profile). It also covers B/C/F, which share the worker + Web PubSub + SWA core.
- **Do this:**
  1. Copy the `azure.yaml` and `main.bicep` below. Run `azd env new dev` and `azd up` on day 1, in **Sweden Central** (T4 + A100 + Foundry in one region; check model availability). Run `azd env new judge` in its own resource group.
  2. Keep render/CV as **Manual** jobs started by the worker. Use the native azd job deploy, and keep option C as a 6-line fallback.
  3. Add zero keys: no connection strings in the Bicep outputs or `.env`.
  4. Put a `NoAutoUpgrade` 10K-TPM deployment in both environments.
  5. Freeze `judge` at the deadline. Thanks to the exists-pattern, `azd provision` there only touches ops knobs.
- **Risks to check early:**
  - Serverless GPU quota on our subscription offer.
  - Whether ACR Tasks (`remoteBuild: true`) are allowed on our subscription type. If not, set `remoteBuild: false` and build locally (unverified whether this applies to us).
  - The SWA region list. The template uses `swaLocation: 'westeurope'`; SWA supports only a few regions (unverified list).

## Reuse: code & links

**`azure.yaml`.** The `web` prepackage hook from file 17 still applies; it isn't repeated here.
```yaml
name: twincast
requiredVersions:
  azd: ">= 1.23.8"          # first release that deploys to Microsoft.App/jobs via host: containerapp
infra: { provider: bicep, path: infra }
services:
  worker: { project: ./worker, language: py, host: containerapp, docker: { path: ./Dockerfile, remoteBuild: true } }
  render: { project: ./jobs/render, language: docker, host: containerapp, docker: { path: ./Dockerfile, remoteBuild: true } }
  cv:     { project: ./jobs/cv, language: docker, host: containerapp, docker: { path: ./Dockerfile, remoteBuild: true } }
  web:    { project: ./web, language: ts, host: staticwebapp, dist: dist }
hooks:
  postprovision:
    posix:   { shell: sh,   run: ./scripts/postprovision.sh,  interactive: false }
    windows: { shell: pwsh, run: ./scripts/postprovision.ps1, interactive: false }
```

**`infra/main.parameters.json`.** These are the cost knobs; azd fills in `${VAR=default}` from `.azure/<env>/.env`.
```json
{ "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "environmentName":   { "value": "${AZURE_ENV_NAME}" },
    "location":          { "value": "${AZURE_LOCATION}" },
    "principalId":       { "value": "${AZURE_PRINCIPAL_ID}" },
    "principalType":     { "value": "${AZURE_PRINCIPAL_TYPE=User}" },
    "workerMinReplicas": { "value": "${WORKER_MIN_REPLICAS=0}" },
    "workerMaxReplicas": { "value": "${WORKER_MAX_REPLICAS=1}" },
    "wpsSku":            { "value": "${WPS_SKU=Free_F1}" },
    "swaSku":            { "value": "${SWA_SKU=Free}" },
    "deployEventHubs":   { "value": "${DEPLOY_EVENTHUBS=true}" },
    "cosmosFreeTier":    { "value": "${COSMOS_FREE_TIER=true}" },
    "enableGpu":         { "value": "${ENABLE_GPU=false}" },
    "llmVersion":        { "value": "${LLM_MODEL_VERSION}" },
    "llmCapacityK":      { "value": "${LLM_CAPACITY_K=10}" },
    "workerExists":      { "value": "${SERVICE_WORKER_RESOURCE_EXISTS=false}" },
    "renderExists":      { "value": "${SERVICE_RENDER_RESOURCE_EXISTS=false}" },
    "cvExists":          { "value": "${SERVICE_CV_RESOURCE_EXISTS=false}" } } }
```

**`infra/main.bicep` skeleton.** Module names and parameters were checked against the AVM sources. The whole file has **not** been compiled (unverified); run `az bicep build` first.
```bicep
targetScope = 'subscription'
param environmentName string
param location string                        // e.g. swedencentral (T4 + A100 serverless GPU)
param swaLocation string = 'westeurope'
param principalId string = ''                // AZURE_PRINCIPAL_ID = the human or CI principal running azd
@allowed(['User', 'ServicePrincipal'])
param principalType string = 'User'
param workerMinReplicas int = 0
param workerMaxReplicas int = 1
@allowed(['Free_F1', 'Standard_S1'])
param wpsSku string = 'Free_F1'
@allowed(['Free', 'Standard'])
param swaSku string = 'Free'
param deployEventHubs bool = true
param cosmosFreeTier bool = true
param enableGpu bool = false
param llmModel string = 'gpt-5.4-mini'
param llmVersion string                      // from `az cognitiveservices model list`
param llmCapacityK int = 10                  // 1 = 1,000 TPM -> 10K TPM hard ceiling
param workerExists bool = false
param renderExists bool = false
param cvExists bool = false

import { roleAssignmentType } from 'br/public:avm/utl/types/avm-common-types:0.7.0'
// app identity always; the developer too when principalId is set (local runs against Azure)
func grant(roleId string, appId string, userId string, userType 'User' | 'ServicePrincipal') roleAssignmentType[] => concat(
  [{ roleDefinitionIdOrName: roleId, principalId: appId, principalType: 'ServicePrincipal' }],
  empty(userId) ? [] : [{ roleDefinitionIdOrName: roleId, principalId: userId, principalType: userType }])

var t = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }
var role = {
  ehSender: '2b629674-e913-4c01-ae53-ef4638d8f975'      // Azure Event Hubs Data Sender
  ehReceiver: 'a638d3c7-ab3a-418d-83e6-5f17a39d4fde'    // Azure Event Hubs Data Receiver
  wpsOwner: '12cf5a90-567b-43ae-8102-96cf46c7d9b4'      // Web PubSub Service Owner
  openAiUser: '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'    // Cognitive Services OpenAI User
  blob: 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'          // Storage Blob Data Contributor
  acrPull: '7f951dda-4ed3-4680-a7ca-43fe172d538d'       // AcrPull
  kvSecrets: '4633458b-17de-408a-b874-0445c86b69e6'     // Key Vault Secrets User
  jobsOperator: 'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b'  // Container Apps Jobs Operator
  cosmosData: '00000000-0000-0000-0000-000000000002'    // Cosmos DB Built-in Data Contributor (data plane)
}
var jobs = [
  { name: 'render', exists: renderExists, gpu: false }
  { name: 'cv', exists: cvExists, gpu: enableGpu }
]

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = { name: 'rg-${environmentName}', location: location, tags: tags }
module id 'br/public:avm/res/managed-identity/user-assigned-identity:0.6.0' = { scope: rg, params: { name: 'id-${t}', location: location } }
module law 'br/public:avm/res/operational-insights/workspace:0.16.1' = { scope: rg, params: { name: 'log-${t}', location: location, dataRetention: 30, dailyQuotaGb: '1' } }
module appi 'br/public:avm/res/insights/component:0.8.0' = { scope: rg, params: { name: 'appi-${t}', location: location, workspaceResourceId: law.outputs.resourceId, retentionInDays: 30 } }
module acr 'br/public:avm/res/container-registry/registry:0.13.1' = {
  scope: rg
  params: { name: 'cr${t}', location: location, acrSku: 'Basic', zoneRedundancy: 'Disabled', roleAssignments: grant(role.acrPull, id.outputs.principalId, '', 'User') }
}
module cae 'br/public:avm/res/app/managed-environment:0.16.0' = {
  scope: rg
  params: {
    name: 'cae-${t}'
    location: location
    zoneRedundant: false
    publicNetworkAccess: 'Enabled'
    appLogsConfiguration: { destination: 'log-analytics', logAnalyticsWorkspaceResourceId: law.outputs.resourceId }
    workloadProfiles: concat([{ name: 'Consumption', workloadProfileType: 'Consumption' }],
      enableGpu ? [{ name: 'gpu-t4', workloadProfileType: 'Consumption-GPU-NC8as-T4' }] : [])
  }
}
module eh 'br/public:avm/res/event-hub/namespace:0.15.2' = if (deployEventHubs) {
  scope: rg
  params: {
    name: 'evh-${t}'
    location: location
    skuName: 'Standard'
    eventhubs: [{ name: 'match-events', partitionCount: 2, messageRetentionInDays: 1, consumergroups: [{ name: 'worker' }] }]
    roleAssignments: concat(grant(role.ehSender, id.outputs.principalId, principalId, principalType),
      grant(role.ehReceiver, id.outputs.principalId, principalId, principalType))
  }
}
module wps 'br/public:avm/res/signal-r-service/web-pub-sub:0.7.2' = {
  scope: rg
  params: { name: 'wps-${t}', location: location, sku: wpsSku, disableLocalAuth: true, roleAssignments: grant(role.wpsOwner, id.outputs.principalId, principalId, principalType) }
}
module cosmos 'br/public:avm/res/document-db/database-account:0.21.1' = {
  scope: rg
  params: {
    name: 'cosmos-${t}'
    location: location
    enableFreeTier: cosmosFreeTier
    zoneRedundant: false
    networkRestrictions: { publicNetworkAccess: 'Enabled', ipRules: [], virtualNetworkRules: [] }
    sqlDatabases: [{ name: 'twincast', containers: [{ name: 'cues', paths: ['/match_id'] }, { name: 'events', paths: ['/match_id'] }] }]
    sqlRoleAssignments: concat([{ principalId: id.outputs.principalId, roleDefinitionId: role.cosmosData }],
      empty(principalId) ? [] : [{ principalId: principalId, roleDefinitionId: role.cosmosData }])
  }
}
module st 'br/public:avm/res/storage/storage-account:0.33.1' = {
  scope: rg
  params: {
    name: 'st${t}'
    location: location
    skuName: 'Standard_LRS'
    allowSharedKeyAccess: false                                  // Entra-only
    networkAcls: { defaultAction: 'Allow', bypass: 'AzureServices' } // AVM default firewall is Deny
    blobServices: { containers: [{ name: 'renders' }, { name: 'replay' }, { name: 'checkpoints' }] }
    roleAssignments: grant(role.blob, id.outputs.principalId, principalId, principalType)
  }
}
module ai 'br/public:avm/res/cognitive-services/account:0.19.1' = {
  scope: rg
  params: {
    name: 'ai-${t}'
    location: location
    kind: 'AIServices'
    customSubDomainName: 'ai-${t}'
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
    deployments: [
      {
        name: 'chat'
        model: { format: 'OpenAI', name: llmModel, version: llmVersion }
        sku: { name: 'GlobalStandard', capacity: llmCapacityK }   // abuse guard (file 21)
        versionUpgradeOption: 'NoAutoUpgrade'
      }
    ]
    roleAssignments: grant(role.openAiUser, id.outputs.principalId, principalId, principalType)
  }
}
module kv 'br/public:avm/res/key-vault/vault:0.14.2' = {
  scope: rg
  params: { name: 'kv-${t}', location: location, sku: 'standard', enablePurgeProtection: false, softDeleteRetentionInDays: 7, roleAssignments: grant(role.kvSecrets, id.outputs.principalId, '', 'User') }
}

var appEnv = [
  { name: 'AZURE_CLIENT_ID', value: id.outputs.clientId }      // makes DefaultAzureCredential pick the UAMI
  { name: 'EVENTHUB_FQDN', value: deployEventHubs ? 'evh-${t}.servicebus.windows.net' : '' }
  { name: 'WEBPUBSUB_ENDPOINT', value: 'https://${wps.outputs.hostName}' }
  { name: 'COSMOS_ENDPOINT', value: cosmos.outputs.endpoint }
  { name: 'AZURE_OPENAI_ENDPOINT', value: ai.outputs.endpoint }
  { name: 'LLM_DEPLOYMENT', value: 'chat' }
  { name: 'BLOB_ENDPOINT', value: st.outputs.primaryBlobEndpoint }
  { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appi.outputs.connectionString }
  { name: 'AZURE_SUBSCRIPTION_ID', value: subscription().subscriptionId }
  { name: 'AZURE_RESOURCE_GROUP', value: rg.name }
]
var registries = [{ server: acr.outputs.loginServer, identity: id.outputs.resourceId }]
// keep the image azd last deployed when re-provisioning (azd sets SERVICE_<NAME>_RESOURCE_EXISTS)
resource workerOld 'Microsoft.App/containerApps@2025-01-01' existing = if (workerExists) { scope: rg, name: 'ca-worker-${t}' }
resource jobOld 'Microsoft.App/jobs@2025-01-01' existing = [for j in jobs: if (j.exists) { scope: rg, name: 'job-${j.name}-${t}' }]

module worker 'br/public:avm/res/app/container-app:0.23.0' = {
  scope: rg
  params: {
    name: 'ca-worker-${t}'
    location: location
    tags: union(tags, { 'azd-service-name': 'worker' })
    environmentResourceId: cae.outputs.resourceId
    managedIdentities: { userAssignedResourceIds: [id.outputs.resourceId] }
    registries: registries
    ingressTargetPort: 8000
    ingressAllowInsecure: false
    scaleSettings: { minReplicas: workerMinReplicas, maxReplicas: workerMaxReplicas }   // AVM default is 3..10
    containers: [
      {
        name: 'main'
        image: workerExists ? workerOld!.properties.template.containers[0].image : 'mcr.microsoft.com/k8se/quickstart:latest'
        resources: { cpu: json('0.25'), memory: '0.5Gi' }
        env: appEnv
      }
    ]
  }
}
module job 'br/public:avm/res/app/job:0.7.2' = [for (j, i) in jobs: {
  scope: rg
  params: {
    name: 'job-${j.name}-${t}'
    location: location
    tags: union(tags, { 'azd-service-name': j.name })         // azd >= 1.23.8 deploys images here
    environmentResourceId: cae.outputs.resourceId
    triggerType: 'Manual'
    manualTriggerConfig: { parallelism: 1, replicaCompletionCount: 1 }
    replicaTimeout: 3600
    replicaRetryLimit: 1
    workloadProfileName: j.gpu ? 'gpu-t4' : null
    managedIdentities: { userAssignedResourceIds: [id.outputs.resourceId] }
    registries: registries
    roleAssignments: grant(role.jobsOperator, id.outputs.principalId, principalId, principalType)  // worker may start it
    containers: [
      {
        name: 'main'
        image: j.exists ? jobOld[i]!.properties.template.containers[0].image : 'mcr.microsoft.com/k8se/quickstart-jobs:latest'
        resources: j.gpu ? { cpu: '8', memory: '56Gi' } : { cpu: '2', memory: '4Gi' }
        env: concat(appEnv, [{ name: 'JOB_KIND', value: j.name }])
      }
    ]
  }
}]
module web 'br/public:avm/res/web/static-site:0.9.6' = { scope: rg, params: { name: 'swa-${t}', location: swaLocation, sku: swaSku, tags: union(tags, { 'azd-service-name': 'web' }) } }

output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acr.outputs.loginServer   // azd pushes images here
output WORKER_URL string = 'https://${worker.outputs.fqdn}'
output WEB_URL string = 'https://${web.outputs.defaultHostname}'
output EVENTHUB_FQDN string = deployEventHubs ? 'evh-${t}.servicebus.windows.net' : ''
output WEBPUBSUB_ENDPOINT string = 'https://${wps.outputs.hostName}'
output COSMOS_ENDPOINT string = cosmos.outputs.endpoint
output AZURE_OPENAI_ENDPOINT string = ai.outputs.endpoint
output BLOB_ENDPOINT string = st.outputs.primaryBlobEndpoint
output STORAGE_ACCOUNT string = st.outputs.name
output RENDER_JOB_NAME string = job[0].outputs.name
output CV_JOB_NAME string = job[1].outputs.name
```
Every `output` becomes an azd env var, and hooks get it preloaded. We deliberately **don't** output `AZURE_CLIENT_ID`: copied into a local `.env`, it would steer `DefaultAzureCredential` toward a managed identity that doesn't exist on a laptop.

**Raw role assignments for anything outside AVM** (same GUIDs):
```bicep
resource ra 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(target.id, principalId, roleId)                 // deterministic, per troubleshooting guide
  scope: target
  properties: { roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', roleId), principalId: principalId, principalType: 'ServicePrincipal' }
}
resource cosmosRa 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2024-11-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, principalId, '00000000-0000-0000-0000-000000000002')
  properties: { roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002', principalId: principalId, scope: cosmosAccount.id }
}
```

**`scripts/postprovision.sh`.** azd preloads the env vars. The script has no keys; it uses `azd auth` through `DefaultAzureCredential`. It needs `pip install azure-identity azure-storage-blob` on the machine or CI runner.
```sh
#!/bin/sh
set -eu
echo "azd env $AZURE_ENV_NAME -> $AZURE_RESOURCE_GROUP"
# 1) endpoints-only config for local runs (keyless: nothing secret in here)
cat > worker/.env.local <<EOF
EVENTHUB_FQDN=${EVENTHUB_FQDN:-}
WEBPUBSUB_ENDPOINT=$WEBPUBSUB_ENDPOINT
COSMOS_ENDPOINT=$COSMOS_ENDPOINT
AZURE_OPENAI_ENDPOINT=$AZURE_OPENAI_ENDPOINT
LLM_DEPLOYMENT=chat
BLOB_ENDPOINT=$BLOB_ENDPOINT
EOF
# 2) seed the replay bundle (file 21). RBAC can take up to 10 min, so retry.
python - <<'PY'
import os, pathlib, time
from azure.identity import DefaultAzureCredential          # includes AzureDeveloperCliCredential
from azure.storage.blob import ContainerClient
c = ContainerClient(os.environ["BLOB_ENDPOINT"], "replay", credential=DefaultAzureCredential())
files = [p for p in pathlib.Path("data/replay").rglob("*") if p.is_file()]
for attempt in range(20):
    try:
        for p in files:
            with open(p, "rb") as fh:
                c.upload_blob(p.relative_to("data/replay").as_posix(), fh, overwrite=True)
        print(f"seeded {len(files)} replay files"); break
    except Exception as e:                                   # 403 until the role propagates
        print(f"waiting for RBAC ({e.__class__.__name__}), attempt {attempt+1}"); time.sleep(30)
else:
    raise SystemExit("RBAC never propagated; rerun: azd hooks run postprovision")
PY
echo "WEB:    $WEB_URL"
echo "WORKER: $WORKER_URL"
```

**Fallback (option C).** Use this as a `postdeploy` hook on `cv` only if azd is older than 1.23.8. A service hook runs from the service directory, here `jobs/cv`. It needs `az login`.
```sh
TAG=$(git rev-parse --short HEAD); ACR=${AZURE_CONTAINER_REGISTRY_ENDPOINT%%.*}
az acr build -r "$ACR" -t "twincast/cv:$TAG" .
az containerapp job update -n "$CV_JOB_NAME" -g "$AZURE_RESOURCE_GROUP" --image "$AZURE_CONTAINER_REGISTRY_ENDPOINT/twincast/cv:$TAG"
```

**Worker starts a CV run** (`pip install azure-mgmt-appcontainers`; `jobs.begin_start(rg, job, template=...)` checked in SDK source):
```python
import os
from azure.identity import DefaultAzureCredential
from azure.mgmt.appcontainers import ContainerAppsAPIClient
from azure.mgmt.appcontainers.models import JobExecutionTemplate, JobExecutionContainer, EnvironmentVar

aca = ContainerAppsAPIClient(DefaultAzureCredential(), os.environ["AZURE_SUBSCRIPTION_ID"])
RG, JOB = os.environ["AZURE_RESOURCE_GROUP"], os.environ["CV_JOB_NAME"]

def start_cv(match_id: str) -> str:
    c = aca.jobs.get(RG, JOB).template.containers[0]           # override replaces the WHOLE template
    env = [e for e in (c.env or []) if e.name != "MATCH_ID"] + [EnvironmentVar(name="MATCH_ID", value=match_id)]
    run = aca.jobs.begin_start(RG, JOB, template=JobExecutionTemplate(containers=[
        JobExecutionContainer(name=c.name, image=c.image, resources=c.resources, env=env)])).result()
    return run.name                                             # poll aca.jobs_executions / logs for status
```

**Day-1 commands**
```bash
azd env new dev   && azd env set AZURE_LOCATION swedencentral && azd env set ENABLE_GPU true
az cognitiveservices model list -l swedencentral --query "[?model.name=='gpt-5.4-mini'].model.version" -o tsv
azd env set LLM_MODEL_VERSION <version-from-above> && azd up
azd env new judge && azd env set AZURE_LOCATION swedencentral && azd env set WORKER_MIN_REPLICAS 1 \
  && azd env set WORKER_MAX_REPLICAS 2 && azd env set SWA_SKU Standard && azd env set DEPLOY_EVENTHUBS false \
  && azd env set COSMOS_FREE_TIER false && azd env set LLM_MODEL_VERSION <same> && azd up
azd deploy cv -e dev                       # rebuild + push only the CV job image
az containerapp job start -n "$(azd env get-value CV_JOB_NAME)" -g "$(azd env get-value AZURE_RESOURCE_GROUP)"
```

Links:
- AVM registry source: https://github.com/Azure/bicep-registry-modules/tree/main/avm/res
- azd job-deploy test sample: https://github.com/Azure/azure-dev/tree/main/cli/azd/test/functional/testdata/samples/containerappjob
- "exists" pattern module: `br/public:avm/ptn/azd/container-app-upsert:0.4.0`

## Sources

- AVM module tags (MCR registry API), e.g. app/job — https://mcr.microsoft.com/v2/bicep/avm/res/app/job/tags/list — accessed 20 Oct 2026
- AVM sources and READMEs (job, container-app, managed-environment, document-db incl. sql-role-assignment, cognitive-services, storage, key-vault, event-hub, web-pub-sub, static-site, registry, workspace, component, UAMI) — https://github.com/Azure/bicep-registry-modules/tree/main/avm/res — accessed 20 Oct 2026
- Azure built-in roles (GUIDs) — https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles — accessed 20 Oct 2026
- Troubleshoot Azure RBAC (principalType, guid naming, up to 10 min) — https://learn.microsoft.com/en-us/azure/role-based-access-control/troubleshooting — accessed 20 Oct 2026
- Cosmos DB data plane security reference — https://learn.microsoft.com/en-us/azure/cosmos-db/reference-data-plane-security — accessed 20 Oct 2026
- Cosmos DB lifetime free tier — https://learn.microsoft.com/en-us/azure/cosmos-db/free-tier — accessed 20 Oct 2026
- azd PR #7001 "support deploying Container App Jobs via host: containerapp" — https://github.com/Azure/azure-dev/pull/7001 — accessed 20 Oct 2026
- azd CHANGELOG (1.23.8, 1.36.0) — https://github.com/Azure/azure-dev/blob/main/cli/azd/CHANGELOG.md — accessed 20 Oct 2026
- azd containerapp service target source (RESOURCE_EXISTS, job image update) — https://github.com/Azure/azure-dev/blob/main/cli/azd/pkg/project/service_target_containerapp.go — accessed 20 Oct 2026
- azure.yaml JSON schema — https://raw.githubusercontent.com/Azure/azure-dev/main/schemas/v1.0/azure.yaml.json — accessed 20 Oct 2026
- azd hooks — https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/azd-extensibility — accessed 20 Oct 2026
- azd environment variables (outputs → .env, `${VAR}`) — https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/manage-environment-variables — accessed 20 Oct 2026
- Jobs in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/jobs — accessed 20 Oct 2026
- `az containerapp job` CLI reference — https://learn.microsoft.com/en-us/cli/azure/containerapp/job — accessed 20 Oct 2026
- Serverless GPUs in Azure Container Apps — https://learn.microsoft.com/en-us/azure/container-apps/gpu-serverless-overview — accessed 20 Oct 2026
- Workload profiles overview — https://learn.microsoft.com/en-us/azure/container-apps/workload-profiles-overview — accessed 20 Oct 2026
- Tutorial: serverless GPU image generation (T4 cpu/memory) — https://learn.microsoft.com/en-us/azure/container-apps/gpu-image-generation — accessed 20 Oct 2026
- Automate Azure OpenAI deployments with quota (capacity = 1,000 TPM) — https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/automate-quota-deployments — accessed 20 Oct 2026
- Manage Azure OpenAI quota (RPM/TPM ratios, 429 behaviour) — https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/quota — accessed 20 Oct 2026
- azure-mgmt-appcontainers `JobsOperations.begin_start` — https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/appcontainers/azure-mgmt-appcontainers — accessed 20 Oct 2026
- openai-chat-app-quickstart (exists-pattern, OpenAI User role) — https://github.com/Azure-Samples/openai-chat-app-quickstart — accessed 20 Oct 2026
