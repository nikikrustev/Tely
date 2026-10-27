// The Static Web App itself (resource-group scope, called from main.bicep).
param name string
param location string
param sku string
param tags object

// API 2024-11-01: listed by `az provider show -n Microsoft.Web` on 21 Oct 2026. The newer 2025-05-01 has no Bicep
// types yet in Bicep 0.48.1 (BCP081), so its properties could not be checked at compile time.
resource swa 'Microsoft.Web/staticSites@2024-11-01' = {
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
