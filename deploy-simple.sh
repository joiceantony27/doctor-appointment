#!/bin/bash

# Simple Azure Deployment for Django Doctor Appointment System
# This script deploys only Container Registry and App Service to avoid regional restrictions

set -e

# Configuration
GITHUB_USERNAME="joiceantony27"
REPO_NAME="doctor-appointment"
RESOURCE_GROUP="rg-doctor-appointment-prod"
APP_NAME="doctorapp$(openssl rand -hex 3)"
REGISTRY_NAME="$(echo ${APP_NAME} | tr -d '-')registry"
LOCATION="westus2"

echo "🚀 Deploying Simplified Azure Infrastructure"
echo "============================================="
echo "GitHub: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "App Name: ${APP_NAME}"
echo "Registry Name: ${REGISTRY_NAME}"
echo "Location: ${LOCATION}"
echo

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first."
    exit 1
fi

# Login to Azure
echo "🔐 Logging into Azure..."
az login

# Get subscription and tenant info
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "✅ Logged in successfully"
echo "Subscription ID: ${SUBSCRIPTION_ID}"
echo "Tenant ID: ${TENANT_ID}"

# Create resource group
echo "📦 Creating resource group..."
az group create --name ${RESOURCE_GROUP} --location ${LOCATION}

# Deploy simplified ARM template
echo "🏗️  Deploying Azure resources..."
az deployment group create \
    --resource-group ${RESOURCE_GROUP} \
    --template-file azure-simple.json \
    --parameters \
        webAppName=${APP_NAME} \
        location=${LOCATION} \
        containerRegistryName=${REGISTRY_NAME}

# Get deployment outputs
echo "📋 Getting deployment details..."
REGISTRY_SERVER=$(az acr show --name ${REGISTRY_NAME} --resource-group ${RESOURCE_GROUP} --query loginServer -o tsv)
REGISTRY_USERNAME=$(az acr credential show --name ${REGISTRY_NAME} --resource-group ${RESOURCE_GROUP} --query username -o tsv)
REGISTRY_PASSWORD=$(az acr credential show --name ${REGISTRY_NAME} --resource-group ${RESOURCE_GROUP} --query passwords[0].value -o tsv)

# Create service principal for GitHub Actions
echo "🔑 Creating service principal for GitHub Actions..."
SP_JSON=$(az ad sp create-for-rbac --name "sp-${APP_NAME}" \
    --role contributor \
    --scopes /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP} \
    --sdk-auth)

CLIENT_ID=$(echo $SP_JSON | jq -r '.clientId')
CLIENT_SECRET=$(echo $SP_JSON | jq -r '.clientSecret')

echo
echo "🎉 Deployment completed successfully!"
echo "======================================"
echo
echo "📝 Add these secrets to your GitHub repository:"
echo "   Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/secrets/actions"
echo
echo "AZURE_CLIENT_ID=${CLIENT_ID}"
echo "AZURE_TENANT_ID=${TENANT_ID}"
echo "AZURE_SUBSCRIPTION_ID=${SUBSCRIPTION_ID}"
echo "REGISTRY_LOGIN_SERVER=${REGISTRY_SERVER}"
echo "REGISTRY_USERNAME=${REGISTRY_USERNAME}"
echo "REGISTRY_PASSWORD=${REGISTRY_PASSWORD}"
echo "AZURE_WEBAPP_NAME=${APP_NAME}"
echo "AZURE_RESOURCE_GROUP=${RESOURCE_GROUP}"
echo
echo "🌐 Your app will be available at: https://${APP_NAME}.azurewebsites.net"
echo
echo "🚀 After adding the secrets, push any code change to trigger deployment!"
