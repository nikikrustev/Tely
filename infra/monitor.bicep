// OWNER: A (potencialbg). Stage 5 tracing: a workspace-based Application Insights for the Director workflow's
// OpenTelemetry spans (file 18 §5). The workspace caps ingestion at 1 GB/day (BUILD_PLAN Stage 5) so a runaway
// exporter can't eat the free credit (D6); the first 5 GB/month of Log Analytics ingestion is free (file 21, unverified).
param location string
param tags object
param workspaceName string
param appInsightsName string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: workspaceName
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: 1 }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    IngestionMode: 'LogAnalytics'
  }
}

output appInsightsName string = appInsights.name
output workspaceName string = workspace.name
output connectionString string = appInsights.properties.ConnectionString
