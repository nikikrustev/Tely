// Stage 4 hosting: one Static Web App (Free) for the zero-backend replay.
// Stage 5: a workspace-based Application Insights (1 GB/day cap) for the Director workflow's traces (monitor.bicep).
// Stage 7: the relay on Container Apps (relay.bicep) and its Voice Live roles on the Foundry resource (foundry-roles.bicep).
// azd env "judge" -> resource group rg-as-judge. D6: no money, so the SKU is Free only.
targetScope = 'subscription'

@description('azd environment name, for example judge')
param environmentName string

@description('Region of the resource group. rg-as-judge already exists in swedencentral (bootstrap), so keep it there.')
param location string

// Verified 21 Oct 2026 with `az provider show -n Microsoft.Web` (staticSites): Central US, East US 2, West US 2,
// West Europe, East Asia. Sweden Central is not offered. West Europe refused our subscription on 22 Oct 2026
// (RequestDisallowedByAzure: "not accepting new customers"), so the site lives in East US 2 (docs/DECISIONS.md D12).
@allowed(['westeurope', 'eastus2', 'centralus', 'westus2', 'eastasia'])
param swaLocation string = 'eastus2'

@allowed(['Free'])
param swaSku string = 'Free'

param resourceGroupName string = 'rg-as-${environmentName}'

@description('Existing Foundry (AIServices S0) resource that serves Voice Live: FOUNDRY_RESOURCE from .env (D8)')
param foundryName string

@description('Its resource group (the bootstrap made it in rg-as-dev)')
param foundryResourceGroup string = 'rg-as-dev'

@description('Relay image, saved by relay/deploy.py (azd predeploy hook) so re-provisioning keeps it; empty before the first push')
param relayImage string = ''

@description('Answer voice: the commentary voice (D13)')
param ttsVoice string = 'en-US-Brian:DragonHDLatestNeural'

@description('Voice Live model, Standard tier (D8)')
param voiceLiveModel string = 'gpt-realtime-2.1-mini'

@allowed(['live', 'off'])
@description('Kill switch for the live Ask (file 21). The presets keep working either way.')
param demoMode string = 'live'

@description('Live questions per day across all fans (about $0.02 each, file 40 section 6)')
param dailyQuestionCap int = 200

@description('Live questions per day from one IP address (ours), so one visitor cannot use up the daily cap')
param ipDailyQuestionCap int = 20

@description('Who gets the monthly cost-budget alerts (BUDGET_EMAIL). Empty: no budget is created.')
param budgetEmail string = ''

@description('Monthly cost budget, in the billing currency of the subscription. An alert only: it never stops anything.')
param budgetAmount int = 5

@description('First day of the budget period: the current month (a budget may not start in an earlier month).')
param budgetStartDate string = utcNow('yyyy-MM-01')

var tags = { 'azd-env-name': environmentName }

// Subscription scope, like this file: the relay's spending lands in this resource group, but Voice Live is billed on
// the Foundry resource in foundryResourceGroup (rg-as-dev), so a resource-group budget would miss most of the cost.
// Budgets alert, they don't stop spending (file 21); the brakes are relay/caps.py and the free account's limit (D6).
resource budget 'Microsoft.Consumption/budgets@2023-05-01' = if (!empty(budgetEmail)) {
  name: 'budget-tely-${environmentName}'
  properties: {
    category: 'Cost'
    amount: budgetAmount
    timeGrain: 'Monthly'
    timePeriod: { startDate: budgetStartDate }
    notifications: {
      actual50: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 50, thresholdType: 'Actual', contactEmails: [ budgetEmail ] }
      actual100: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 100, thresholdType: 'Actual', contactEmails: [ budgetEmail ] }
      forecast100: { enabled: true, operator: 'GreaterThan', threshold: 100, thresholdType: 'Forecasted', contactEmails: [ budgetEmail ] }
    }
  }
}

resource rg 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module web 'web.bicep' = {
  name: 'web'
  scope: rg
  params: {
    name: 'swa-as-${environmentName}-${take(uniqueString(subscription().id, environmentName), 6)}'
    location: swaLocation
    sku: swaSku
    tags: union(tags, { 'azd-service-name': 'web' }) // azd finds the deploy target by this tag
  }
}

module monitor 'monitor.bicep' = {
  name: 'monitor'
  scope: rg
  params: {
    location: location
    tags: tags
    workspaceName: 'log-as-${environmentName}'
    appInsightsName: 'appi-as-${environmentName}'
  }
}

module relay 'relay.bicep' = {
  name: 'relay'
  scope: rg
  params: {
    location: location
    tags: tags
    token: take(uniqueString(subscription().id, environmentName), 6)
    workspaceName: monitor.outputs.workspaceName
    foundryName: foundryName
    siteUrl: 'https://${web.outputs.defaultHostname}'
    relayImage: relayImage
    ttsVoice: ttsVoice
    voiceLiveModel: voiceLiveModel
    demoMode: demoMode
    dailyQuestionCap: dailyQuestionCap
    ipDailyQuestionCap: ipDailyQuestionCap
    appInsightsConnectionString: monitor.outputs.connectionString   // D19: tester feedback events
  }
}

module foundryRoles 'foundry-roles.bicep' = {
  name: 'foundry-roles'
  scope: resourceGroup(foundryResourceGroup)
  params: {
    foundryName: foundryName
    principalId: relay.outputs.identityPrincipalId
  }
}

output AZURE_RESOURCE_GROUP string = rg.name
output WEB_URL string = 'https://${web.outputs.defaultHostname}'
output APPLICATIONINSIGHTS_NAME string = monitor.outputs.appInsightsName
// azd keeps outputs in .azure/judge/.env (git-ignored). tracing.py reads it with `azd env get-value`; nothing prints it.
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitor.outputs.connectionString
// relay/deploy.py pushes the relay image here; the web predeploy hook writes RELAY_URL into dist/live.json.
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = relay.outputs.registryEndpoint
output RELAY_APP_NAME string = relay.outputs.appName
output RELAY_URL string = relay.outputs.url
