// OWNER: A (potencialbg). The Static Web App itself (resource-group scope, called from main.bicep).
param name string
param location string
param sku string
param tags object

// API 2025-05-01: newest non-preview version listed by `az provider show -n Microsoft.Web` on 21 Oct 2026.
resource swa 'Microsoft.Web/staticSites@2025-05-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
    tier: sku
  }
  properties: {
    allowConfigFileUpdates: true          // staticwebapp.config.json (headers, MIME types) is honoured
    stagingEnvironmentPolicy: 'Disabled'  // no pull-request preview sites: one public URL, nothing to clean up
  }
}

output defaultHostname string = swa.properties.defaultHostname
