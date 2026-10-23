// OWNER: A (potencialbg). Lets the relay's identity call Voice Live on the existing Foundry resource (bootstrap made it
// in rg-as-dev, D8), so this module runs at that resource group's scope. Roles from Learn "How to use the Voice Live
// API": Cognitive Services User + Foundry User (GUIDs checked with `az role definition list`, 23 Oct 2026).
param foundryName string
param principalId string

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' existing = {
  name: foundryName
}

var roles = [
  'a97b65f3-24c7-4388-baec-2e87135dc908'   // Cognitive Services User
  '53ca6127-db72-4b80-b1b0-d745d6d5456d'   // Foundry User (was Azure AI User)
]

resource grants 'Microsoft.Authorization/roleAssignments@2022-04-01' = [for r in roles: {
  scope: foundry
  name: guid(foundry.id, principalId, r)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', r)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}]
