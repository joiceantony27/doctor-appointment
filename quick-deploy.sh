#!/bin/bash

# Quick CI/CD Setup Script for Django Doctor Appointment System
# This script will guide you through the complete setup process

set -e

echo "🚀 Django Doctor Appointment System - CI/CD Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
echo
print_info "Checking prerequisites..."

# Check if git is installed
if ! command -v git &> /dev/null; then
    print_error "Git is not installed. Please install git first."
    exit 1
fi

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    print_warning "Azure CLI is not installed. Installing..."
    curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
fi

print_status "Prerequisites check completed"

# Step 1: GitHub Setup
echo
print_info "Step 1: GitHub Repository Setup"
echo "================================"

read -p "Enter your GitHub username: " GITHUB_USERNAME
read -p "Enter your repository name (or press Enter for 'django-doctor-appointment'): " REPO_NAME
REPO_NAME=${REPO_NAME:-django-doctor-appointment}

echo
print_info "Setting up Git repository..."

# Initialize git if not already done
if [ ! -d ".git" ]; then
    git init
    print_status "Git repository initialized"
fi

# Add all files
git add .
git commit -m "Initial commit - Django Doctor Appointment System with DevOps setup" || true

# Set up remote
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"
git branch -M main

print_status "Git repository configured"

# Step 2: Azure Login
echo
print_info "Step 2: Azure Authentication"
echo "============================="

print_info "Please login to Azure..."
az login

# Get Azure details
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

print_status "Azure authentication completed"
print_info "Subscription ID: $SUBSCRIPTION_ID"
print_info "Tenant ID: $TENANT_ID"

# Step 3: Azure Resource Deployment
echo
print_info "Step 3: Azure Resource Deployment"
echo "=================================="

read -p "Enter Azure region (default: eastus): " AZURE_REGION
AZURE_REGION=${AZURE_REGION:-eastus}

read -p "Enter resource group name (default: rg-doctor-appointment): " RESOURCE_GROUP
RESOURCE_GROUP=${RESOURCE_GROUP:-rg-doctor-appointment}

# Generate unique app name
RANDOM_SUFFIX=$(openssl rand -hex 3)
APP_NAME="doctor-appointment-${RANDOM_SUFFIX}"

print_info "Deploying Azure resources..."
print_info "Resource Group: $RESOURCE_GROUP"
print_info "App Name: $APP_NAME"
print_info "Region: $AZURE_REGION"

# Make deploy script executable and run it
chmod +x deploy-azure.sh

# Set environment variables for the deploy script
export RESOURCE_GROUP_NAME="$RESOURCE_GROUP"
export APP_SERVICE_NAME="$APP_NAME"
export LOCATION="$AZURE_REGION"

# Run the deployment
./deploy-azure.sh

print_status "Azure resources deployed successfully"

# Step 4: Push to GitHub
echo
print_info "Step 4: Push to GitHub"
echo "======================"

print_warning "Please create the repository '$REPO_NAME' on GitHub first if it doesn't exist"
read -p "Press Enter when the repository is created on GitHub..."

print_info "Pushing code to GitHub..."
git push -u origin main

print_status "Code pushed to GitHub successfully"

# Step 5: GitHub Secrets Configuration
echo
print_info "Step 5: GitHub Secrets Configuration"
echo "===================================="

print_warning "You need to manually add the following secrets to your GitHub repository:"
print_info "Go to: https://github.com/${GITHUB_USERNAME}/${REPO_NAME}/settings/secrets/actions"

echo
echo "Required GitHub Secrets:"
echo "========================"
echo "The deploy-azure.sh script has generated the values for these secrets."
echo "Check the output above for the exact values to copy."
echo
echo "Required secrets:"
echo "- AZURE_CREDENTIALS"
echo "- REGISTRY_LOGIN_SERVER"
echo "- REGISTRY_USERNAME" 
echo "- REGISTRY_PASSWORD"
echo "- DATABASE_URL"
echo "- REDIS_URL"

# Step 6: Final Instructions
echo
print_info "Step 6: Deployment Verification"
echo "==============================="

echo
print_status "Setup completed! 🎉"
echo
print_info "Next steps:"
echo "1. Add the GitHub secrets as shown above"
echo "2. The CI/CD pipeline will automatically trigger on your next push"
echo "3. Monitor the deployment in GitHub Actions"
echo "4. Your app will be available at: https://${APP_NAME}.azurewebsites.net"
echo
print_info "To trigger a deployment now:"
echo "git commit --allow-empty -m 'Trigger deployment'"
echo "git push"
echo
print_status "Your Django Doctor Appointment System is ready for production! 🚀"
