#!/bin/bash

# Azure Deployment Script for Doctor Appointment System
# This script deploys the Django application to Azure using ARM templates

set -e

# Configuration
RESOURCE_GROUP_NAME="rg-doctor-appointment"
LOCATION="East US"
DEPLOYMENT_NAME="doctor-appointment-deployment-$(date +%Y%m%d-%H%M%S)"
TEMPLATE_FILE="azure-deploy.json"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    print_error "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in to Azure
if ! az account show &> /dev/null; then
    print_error "You are not logged in to Azure. Please run 'az login' first."
    exit 1
fi

print_status "Starting Azure deployment for Doctor Appointment System..."

# Get parameters
read -p "Enter PostgreSQL admin password (will be hidden): " -s POSTGRES_PASSWORD
echo
read -p "Enter web app name (default: doctor-appointment-app): " WEB_APP_NAME
WEB_APP_NAME=${WEB_APP_NAME:-doctor-appointment-app}

read -p "Enter Azure location (default: East US): " AZURE_LOCATION
AZURE_LOCATION=${AZURE_LOCATION:-"East US"}

# Create resource group
print_status "Creating resource group: $RESOURCE_GROUP_NAME"
az group create --name $RESOURCE_GROUP_NAME --location "$AZURE_LOCATION"

# Deploy ARM template
print_status "Deploying Azure resources..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
    --resource-group $RESOURCE_GROUP_NAME \
    --name $DEPLOYMENT_NAME \
    --template-file $TEMPLATE_FILE \
    --parameters webAppName=$WEB_APP_NAME \
                 location="$AZURE_LOCATION" \
                 postgresAdminPassword=$POSTGRES_PASSWORD \
    --output json)

if [ $? -eq 0 ]; then
    print_status "Azure resources deployed successfully!"
    
    # Extract outputs
    WEB_APP_URL=$(echo $DEPLOYMENT_OUTPUT | jq -r '.properties.outputs.webAppUrl.value')
    REGISTRY_SERVER=$(echo $DEPLOYMENT_OUTPUT | jq -r '.properties.outputs.containerRegistryLoginServer.value')
    POSTGRES_FQDN=$(echo $DEPLOYMENT_OUTPUT | jq -r '.properties.outputs.postgresServerFqdn.value')
    
    print_status "Deployment completed successfully!"
    echo "=================================================="
    echo "Web App URL: $WEB_APP_URL"
    echo "Container Registry: $REGISTRY_SERVER"
    echo "PostgreSQL Server: $POSTGRES_FQDN"
    echo "=================================================="
    
    # Save deployment info
    cat > deployment-info.txt << EOF
Deployment Information
======================
Date: $(date)
Resource Group: $RESOURCE_GROUP_NAME
Web App Name: $WEB_APP_NAME
Web App URL: $WEB_APP_URL
Container Registry: $REGISTRY_SERVER
PostgreSQL Server: $POSTGRES_FQDN
Location: $AZURE_LOCATION
EOF
    
    print_status "Deployment information saved to deployment-info.txt"
    
else
    print_error "Deployment failed!"
    exit 1
fi

# Configure GitHub secrets (if .git directory exists)
if [ -d ".git" ]; then
    print_status "Setting up GitHub repository secrets..."
    
    # Get ACR credentials
    ACR_NAME=$(echo $REGISTRY_SERVER | cut -d'.' -f1)
    ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query username -o tsv)
    ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query passwords[0].value -o tsv)
    
    # Create service principal for GitHub Actions
    SP_OUTPUT=$(az ad sp create-for-rbac --name "sp-$WEB_APP_NAME-github" \
        --role contributor \
        --scopes "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/$RESOURCE_GROUP_NAME" \
        --sdk-auth)
    
    echo "=================================================="
    echo "GitHub Secrets to Configure:"
    echo "=================================================="
    echo "AZURE_CREDENTIALS: $SP_OUTPUT"
    echo "AZURE_REGISTRY_LOGIN_SERVER: $REGISTRY_SERVER"
    echo "AZURE_REGISTRY_USERNAME: $ACR_USERNAME"
    echo "AZURE_REGISTRY_PASSWORD: $ACR_PASSWORD"
    echo "AZURE_RESOURCE_GROUP: $RESOURCE_GROUP_NAME"
    echo "=================================================="
    
    # Save GitHub secrets to file
    cat > github-secrets.txt << EOF
GitHub Secrets Configuration
============================

Add these secrets to your GitHub repository:

AZURE_CREDENTIALS:
$SP_OUTPUT

AZURE_REGISTRY_LOGIN_SERVER: $REGISTRY_SERVER
AZURE_REGISTRY_USERNAME: $ACR_USERNAME  
AZURE_REGISTRY_PASSWORD: $ACR_PASSWORD
AZURE_RESOURCE_GROUP: $RESOURCE_GROUP_NAME

To add secrets:
1. Go to your GitHub repository
2. Click Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Add each secret with the name and value above
EOF
    
    print_status "GitHub secrets saved to github-secrets.txt"
fi

print_status "Next steps:"
echo "1. Configure GitHub secrets (see github-secrets.txt)"
echo "2. Push your code to trigger the CI/CD pipeline"
echo "3. Monitor the deployment in GitHub Actions"
echo "4. Access your application at: $WEB_APP_URL"

print_status "Deployment script completed successfully!"
