#!/usr/bin/env bash
# Stage 0 Azure bootstrap for Audio Stands (file 44 "Reuse", cut to what BUILD_PLAN.md uses).
# OWNER: A (potencialbg). Person A runs this by hand after `az login`. Claude never runs it.
# Creates: rg-as-dev + rg-as-judge (swedencentral), one AIServices S0 resource with a custom domain,
# a gpt-5.4-mini GlobalStandard deployment (capacity 10, NoAutoUpgrade), and A's own data-plane roles.
# Does NOT create Cosmos DB, Web PubSub or Event Hubs: this plan doesn't use them.
# Does NOT give Nikolay (B) any Azure role: B's lane has no Microsoft (TEAM_SPLIT.md).
#
# Flags checked against the Azure CLI reference on Microsoft Learn (20 Oct 2026), not against `--help` on this
# machine (az isn't installed here). Run `az <cmd> --help` if a step fails; doubtful items say (unverified).
#
# Usage:  az login && bash scripts/bootstrap_azure.sh
# Override names with env vars, e.g.  FOUNDRY_NAME=as-foundry-dev2 bash scripts/bootstrap_azure.sh
set -euo pipefail

LOCATION="${LOCATION:-swedencentral}"
RG_DEV="${RG_DEV:-rg-as-dev}"
RG_JUDGE="${RG_JUDGE:-rg-as-judge}"
FOUNDRY_NAME="${FOUNDRY_NAME:-as-foundry-dev}"   # also the custom domain, so it must be globally unique
MODEL_NAME="${MODEL_NAME:-gpt-5.4-mini}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-gpt-5.4-mini}"
CAPACITY="${CAPACITY:-10}"
ARM_API="2024-10-01"                              # Microsoft.CognitiveServices API version (unverified: newest may differ)

SUB_ID="$(az account show --query id -o tsv)"
echo "Subscription: $(az account show --query name -o tsv)"

echo "== 1. Register resource providers (Foundry/Speech, Container Apps, logs, SWA, ACR)"
for p in Microsoft.CognitiveServices Microsoft.App Microsoft.OperationalInsights Microsoft.Insights \
         Microsoft.Web Microsoft.ContainerRegistry; do
  az provider register -n "$p" --output none
done

echo "== 2. Resource groups in $LOCATION"
az group create -n "$RG_DEV" -l "$LOCATION" --output none
az group create -n "$RG_JUDGE" -l "$LOCATION" --output none

echo "== 3. AIServices S0 resource $FOUNDRY_NAME (custom domain is required for keyless Speech; it can't be changed later)"
if az cognitiveservices account show -n "$FOUNDRY_NAME" -g "$RG_DEV" --output none 2>/dev/null; then
  echo "   exists, skipping"
else
  az cognitiveservices account create -n "$FOUNDRY_NAME" -g "$RG_DEV" -l "$LOCATION" \
    --kind AIServices --sku S0 --custom-domain "$FOUNDRY_NAME" --yes --output none
fi
ACCOUNT_ID="$(az cognitiveservices account show -n "$FOUNDRY_NAME" -g "$RG_DEV" --query id -o tsv)"

echo "== 4. Quota: look for 0 limits on $MODEL_NAME. If 0, file https://aka.ms/oai/stuquotarequest now (file 44)."
az cognitiveservices usage list -l "$LOCATION" -o table
echo "   Quota tier (preview API, unverified):"
az rest --method get \
  --url "https://management.azure.com/subscriptions/$SUB_ID/providers/Microsoft.CognitiveServices/quotaTiers?api-version=2025-10-01-preview" \
  || echo "   quotaTiers call failed; check Foundry -> Quota in the portal instead"

echo "== 5. Deploy $MODEL_NAME as $DEPLOYMENT_NAME (GlobalStandard, capacity $CAPACITY, NoAutoUpgrade)"
MODEL_VERSION="${MODEL_VERSION:-$(az cognitiveservices model list -l "$LOCATION" \
  --query "[?model.name=='$MODEL_NAME'].model.version" -o tsv | sort -u | tail -n 1)}"
if [ -z "$MODEL_VERSION" ]; then
  echo "   $MODEL_NAME not listed in $LOCATION. Stage 5 falls back to the rules Director." >&2
else
  echo "   version $MODEL_VERSION (file 44 saw 2026-03-17)"
  # `az cognitiveservices account deployment create` has no upgrade-option flag (Learn CLI reference, Sep 2026),
  # so the deployment is a plain ARM PUT. versionUpgradeOption=NoAutoUpgrade keeps the model fixed for judging.
  az rest --method put \
    --url "https://management.azure.com${ACCOUNT_ID}/deployments/${DEPLOYMENT_NAME}?api-version=${ARM_API}" \
    --body "{\"sku\":{\"name\":\"GlobalStandard\",\"capacity\":${CAPACITY}},
             \"properties\":{\"model\":{\"format\":\"OpenAI\",\"name\":\"${MODEL_NAME}\",\"version\":\"${MODEL_VERSION}\"},
                             \"versionUpgradeOption\":\"NoAutoUpgrade\"}}" \
    --output none \
    || echo "   deployment failed (quota?): smoke_azure.py will say 'model quota missing'" >&2
fi

echo "== 6. Data-plane roles for you (A) so keyless auth works in smoke_azure.py"
ME="$(az ad signed-in-user show --query id -o tsv)"
for role in "Cognitive Services Speech User" "Cognitive Services OpenAI User"; do   # 2nd: unverified for the v1 endpoint
  az role assignment create --assignee-object-id "$ME" --assignee-principal-type User \
    --role "$role" --scope "$ACCOUNT_ID" --output none \
    || echo "   could not assign '$role' (may already exist)"
done

ENDPOINT="$(az cognitiveservices account show -n "$FOUNDRY_NAME" -g "$RG_DEV" --query properties.endpoint -o tsv)"
cat <<EOF

Done. Put these in .env (no keys needed):
  FOUNDRY_RESOURCE=$FOUNDRY_NAME
  SPEECH_ENDPOINT=$ENDPOINT
Role assignments can take a few minutes to apply. Then run:  python scripts/smoke_azure.py
Still manual (file 44): create the Foundry project in https://ai.azure.com, and the \$100 budget in Cost Management.
EOF
