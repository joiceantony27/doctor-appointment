#!/bin/bash

# Azure Deployment Configuration for joiceantony27/doctor-appointment
# This script will deploy Azure resources for your Django Doctor Appointment System

set -e

# Configuration
GITHUB_USERNAME="joiceantony27"
REPO_NAME="doctor-appointment"
RESOURCE_GROUP="rg-doctor-appointment-prod"
APP_NAME="doctor-appointment-$(openssl rand -hex 3)"
LOCATION="westus2"

echo "🚀 Deploying Azure Infrastructure for Django Doctor Appointment System"
echo "======================================================================"
echo "GitHub: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}"
echo "Resource Group: ${RESOURCE_GROUP}"
echo "App Name: ${APP_NAME}"
echo "Location: ${LOCATION}"
echo

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI is not installed. Please install it first:"
    echo "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
    exit 1
fi

# Login to Azure
echo "🔐 Please login to your Azure student account..."
az login

# Get subscription details
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "✅ Logged in successfully"
echo "Subscription ID: ${SUBSCRIPTION_ID}"
echo "Tenant ID: ${TENANT_ID}"

# Create resource group
echo "📦 Creating resource group..."
az group create --name ${RESOURCE_GROUP} --location ${LOCATION}

# Deploy ARM template
echo "🏗️  Deploying Azure resources..."
az deployment group create \
    --resource-group ${RESOURCE_GROUP} \
    --template-file azure-deploy.json \
    --parameters \
        webAppName=${APP_NAME} \
        location=${LOCATION} \
        containerRegistryName=$(echo ${APP_NAME} | tr -d '-')registry \
        postgresServerName=${APP_NAME}-db \
        postgresAdminLogin=djangoadmin \
        postgresAdminPassword=DjangoApp123!

# Get deployment outputs
echo "📋 Getting deployment details..."
REGISTRY_NAME=$(echo ${APP_NAME} | tr -d '-')registry
REGISTRY_SERVER=$(az acr show --name ${REGISTRY_NAME} --resource-group ${RESOURCE_GROUP} --query loginServer -o tsv)
REGISTRY_USERNAME=$(az acr credential show --name ${REGISTRY_NAME} --resource-group ${RESOURCE_GROUP} --query username -o tsv)
REGISTRY_PASSWORD=$(az acr credential show --name ${REGISTRY_NAME} --resource-group ${RESOURCE_GROUP} --query passwords[0].value -o tsv)

# Get database connection string
DB_SERVER="${APP_NAME}-db.postgres.database.azure.com"
DB_NAME="doctor_appointment"
DB_USERNAME="djangoadmin"
DB_PASSWORD="DjangoApp123!"
DATABASE_URL="postgresql://${DB_USERNAME}:${DB_PASSWORD}@${DB_SERVER}:5432/${DB_NAME}?sslmode=require"

# Get Redis connection string
REDIS_HOST="${APP_NAME}-redis.redis.cache.windows.net"
REDIS_KEY=$(az redis list-keys --name ${APP_NAME}-redis --resource-group ${RESOURCE_GROUP} --query primaryKey -o tsv)
REDIS_URL="redis://:${REDIS_KEY}@${REDIS_HOST}:6380/0?ssl=True"

# Create service principal for GitHub Actions
echo "🔑 Creating service principal for GitHub Actions..."
SP_JSON=$(az ad sp create-for-rbac --name "sp-${APP_NAME}" --role contributor --scopes /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP} --sdk-auth)

echo
echo "🎉 Azure deployment completed successfully!"
echo
echo "📝 GitHub Secrets Configuration"
echo "================================"
echo "Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/secrets/actions"
echo
echo "Add these secrets:"
echo
echo "AZURE_CREDENTIALS:"
echo "${SP_JSON}"
echo
echo "REGISTRY_LOGIN_SERVER:"
echo "${REGISTRY_SERVER}"
echo
echo "REGISTRY_USERNAME:"
echo "${REGISTRY_USERNAME}"
echo
echo "REGISTRY_PASSWORD:"
echo "${REGISTRY_PASSWORD}"
echo
echo "DATABASE_URL:"
echo "${DATABASE_URL}"
echo
echo "REDIS_URL:"
echo "${REDIS_URL}"
echo
echo "🌐 Your app will be available at:"
echo "https://${APP_NAME}.azurewebsites.net"
echo
echo "✅ Next steps:"
echo "1. Create the repository on GitHub: https://github.com/new"
echo "2. Add the GitHub secrets above"
echo "3. Push your code to trigger deployment"
echo "4. Monitor deployment in GitHub Actions"
