// OWNER: A (potencialbg). Stage 7: the relay (Voice Live live Ask + B's Stats MCP server) on Container Apps.
// Keyless (file 30): a user-assigned identity pulls the image from ACR and calls Voice Live; no secret or key is set.
// D6, no money: minReplicas 0 (the page wakes the relay on load), 0.25 vCPU / 0.5 GiB, maxReplicas 2, ACR Basic.
param location string
param tags object
@minLength(6)
param token string                       // short unique suffix
param workspaceName string               // monitor.bicep's Log Analytics workspace (console logs, golden turns)
param foundryName string
param siteUrl string                     // the Static Web App, the only page origin allowed to open /voice
param relayImage string = ''             // RELAY_IMAGE from relay/deploy.py (azd predeploy hook); '' before the first push
param ttsVoice string
param voiceLiveModel string
param demoMode string
param dailyQuestionCap int

var appName = 'ca-relay-${token}'

resource id 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-relay-${token}'
  location: location
  tags: tags
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'cras${token}'
  location: location
  tags: tags
  sku: { name: 'Basic' }
  properties: { adminUserEnabled: false }   // pulls use the identity, never an admin password
}

resource acrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: acr
  name: guid(acr.id, id.id, '7f951dda-4ed3-4680-a7ca-43fe172d538d')
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: id.properties.principalId
    principalType: 'ServicePrincipal'      // new identity: avoids PrincipalNotFound on replication delay (file 30)
  }
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: workspaceName
}

resource cae 'Microsoft.App/managedEnvironments@2025-01-01' = {
  name: 'cae-as-${token}'
  location: location
  tags: tags
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: workspace.properties.customerId
        sharedKey: workspace.listKeys().primarySharedKey   // resolved at deploy time, never written to the repo
      }
    }
    workloadProfiles: [ { name: 'Consumption', workloadProfileType: 'Consumption' } ]
  }
}

var fqdn = '${appName}.${cae.properties.defaultDomain}'

resource app 'Microsoft.App/containerApps@2025-01-01' = {
  name: appName
  location: location
  tags: tags
  identity: { type: 'UserAssigned', userAssignedIdentities: { '${id.id}': {} } }
  dependsOn: [ acrPull ]
  properties: {
    environmentId: cae.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8080
        transport: 'auto'                  // HTTP/1.1 upgrade for the /voice WebSocket
        allowInsecure: false
      }
      registries: [ { server: acr.properties.loginServer, identity: id.id } ]
    }
    template: {
      containers: [
        {
          name: 'relay'
          image: empty(relayImage) ? 'mcr.microsoft.com/k8se/quickstart:latest' : relayImage
          resources: { cpu: json('0.25'), memory: '0.5Gi' }
          env: [
            { name: 'FOUNDRY_RESOURCE', value: foundryName }
            { name: 'AZURE_CLIENT_ID', value: id.properties.clientId }   // DefaultAzureCredential picks this identity
            { name: 'TTS_VOICE', value: ttsVoice }
            { name: 'VOICE_LIVE_MODEL', value: voiceLiveModel }
            { name: 'DEMO_MODE', value: demoMode }                       // live | off: the kill switch (file 21)
            { name: 'DAILY_QUESTION_CAP', value: string(dailyQuestionCap) }
            { name: 'ALLOWED_ORIGINS', value: '${siteUrl},http://localhost:5173' }
            { name: 'MCP_ALLOWED_HOSTS', value: '${fqdn},localhost:*,127.0.0.1:*' }   // B's DNS-rebinding allow-list
          ]
        }
      ]
      scale: { minReplicas: 0, maxReplicas: 2 }
    }
  }
}

output url string = 'https://${fqdn}'
output identityPrincipalId string = id.properties.principalId
output registryEndpoint string = acr.properties.loginServer
output registryName string = acr.name
output appName string = app.name
