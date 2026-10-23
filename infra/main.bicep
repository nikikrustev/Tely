// OWNER: A (potencialbg). Stage 4 hosting: one Static Web App (Free) for the zero-backend replay.
// Stage 5: a workspace-based Application Insights (1 GB/day cap) for the Director workflow's traces (monitor.bicep).
// azd env "judge" -> resource group rg-as-judge (BUILD_PLAN Stage 4). D6: no money, so the SKU is Free only.
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

var tags = { 'azd-env-name': environmentName }

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

output AZURE_RESOURCE_GROUP string = rg.name
output WEB_URL string = 'https://${web.outputs.defaultHostname}'
output APPLICATIONINSIGHTS_NAME string = monitor.outputs.appInsightsName
// azd keeps outputs in .azure/judge/.env (git-ignored). tracing.py reads it with `azd env get-value`; nothing prints it.
output APPLICATIONINSIGHTS_CONNECTION_STRING string = monitor.outputs.connectionString
